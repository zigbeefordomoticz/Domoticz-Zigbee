"""
test_OTA_queue.py
~~~~~~~~~~~~~~~~~
Unit tests for the OTA queue (#2169): several devices per firmware update
request, upgraded at the same time within the transfer slots.

Rules under test:
    - OTA_MAX_TRANSFERS (3) devices hold a slot at the same time: notified
      and waiting for the device, or being served;
    - a battery-powered device that asks on its own takes one more slot, up
      to OTA_MAX_TRANSFERS_WITH_BATTERY (4): it may not ask again for hours;
    - the other devices wait in the queue (NO_IMAGE_AVAILABLE when they ask),
      oldest request first, and are notified when a slot frees;
    - a device that does not answer its notifications gives its slot back
      and stays authorized for OTA_QUEUE_WAIT (sleepy devices, ZCL8 11.8.2);
    - with autoServeOTA, a device asking while the slots are taken is queued;
    - requests are kept by IEEE: a device that rejoined with another short
      address keeps its place;
    - a ZiGate (native mode) holds one image: one transfer at a time.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_queue.py -v
"""

import time

import pytest
from ota_builders import DEVICE_EP, DEVICE_IEEE, DEVICE_NWKID, block_request, make_ota_image, page_request, query_next_image, upgrade_end

IMAGE_VERSION = 0x01020304
NO_IMAGE_AVAILABLE = 0x98

MAINS_2 = "2222"
MAINS_3 = "3333"
MAINS_6 = "6666"
BATTERY_4 = "4444"
BATTERY_5 = "5555"

# The devices that fill the OTA_MAX_TRANSFERS regular slots
SLOTS_FULL = (DEVICE_NWKID, MAINS_2, MAINS_3)


@pytest.fixture
def ikea_image(install_image):
    return install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))


@pytest.fixture
def devices(add_device):
    """1234 (fixture device), 2222, 3333 and 6666 are mains-powered, 4444 and 5555 battery-powered."""
    add_device(MAINS_2, "00158d0000002222")
    add_device(MAINS_3, "00158d0000003333")
    add_device(MAINS_6, "00158d0000006666")
    add_device(BATTERY_4, "00158d0000004444", battery=True)
    add_device(BATTERY_5, "00158d0000005555", battery=True)


def _pick(ota, *nwkids, force=False):
    """The devices are picked in the WebUI, in that order."""
    return ota.restapi_firmware_update([
        {"NwkId": nwkid, "Ep": DEVICE_EP, "Brand": "Ikea", "FileName": "bulb.ota", "ForceUpdate": force} for nwkid in nwkids
    ])


def _query(ota, radio, nwkid, version=0x01000000):
    """Query Next Image Request from the device; returns the status of the response."""
    radio.zcl_raw_ota_query_next_image_response.reset_mock()
    ota.query_next_image_request(nwkid, DEVICE_EP, "2a", query_next_image(0x117C, 0x2203, version))
    return radio.zcl_raw_ota_query_next_image_response.call_args.args[5]


def _states(ota):
    return {request["NwkId"]: request["State"] for request in ota.ota_requests.values()}


def _notified(radio):
    return [call.args[1] for call in radio.zcl_raw_ota_image_notify.call_args_list]


def _end_notify_window(ota_module, ota):
    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY):
        ota.heartbeat()


def test_slot_numbers(ota_module):
    """3 transfers, plus 1 for a battery device that asks: 4 keep the block delay scaling under its cap."""
    assert (ota_module.OTA_MAX_TRANSFERS, ota_module.OTA_MAX_TRANSFERS_WITH_BATTERY) == (3, 4)


# ─── several devices, three slots ─────────────────────────────────────────────

def test_three_devices_are_notified_the_others_wait(ota_module, ota, radio, ikea_image, devices):
    results = _pick(ota, *SLOTS_FULL, MAINS_6)

    assert [result["Status"] for result in results] == ["Queued"] * 4
    assert _notified(radio) == list(SLOTS_FULL)
    assert _states(ota) == {**{nwkid: ota_module.OTA_NOTIFYING for nwkid in SLOTS_FULL}, MAINS_6: ota_module.OTA_QUEUED}


def test_notified_devices_are_served_at_the_same_time(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL)

    for nwkid in SLOTS_FULL:
        assert _query(ota, radio, nwkid) == 0x00
    assert _states(ota) == {nwkid: ota_module.OTA_TRANSFER for nwkid in SLOTS_FULL}


def test_queued_mains_device_asking_while_the_slots_are_taken_waits(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)

    assert _query(ota, radio, MAINS_6) == NO_IMAGE_AVAILABLE
    assert _states(ota)[MAINS_6] == ota_module.OTA_QUEUED


def test_battery_device_asking_takes_the_extra_slot(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, BATTERY_4)
    assert _states(ota)[BATTERY_4] == ota_module.OTA_QUEUED

    assert _query(ota, radio, BATTERY_4) == 0x00
    assert _states(ota)[BATTERY_4] == ota_module.OTA_TRANSFER
    assert len(ota_module.active_ota_requests(ota)) == 4


def test_four_transfers_is_the_hard_limit(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, BATTERY_4, BATTERY_5)
    assert _query(ota, radio, BATTERY_4) == 0x00

    assert _query(ota, radio, BATTERY_5) == NO_IMAGE_AVAILABLE
    assert _states(ota)[BATTERY_5] == ota_module.OTA_QUEUED


def test_the_extra_slot_is_never_used_to_notify(ota, radio, ikea_image, devices):
    """The fourth slot is for a battery device that asks on its own, not for a notification."""
    _pick(ota, *SLOTS_FULL, BATTERY_4)

    ota.heartbeat()

    assert BATTERY_4 not in _notified(radio)


def test_battery_device_takes_a_regular_slot_too(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, BATTERY_4, MAINS_2)

    assert _notified(radio) == [BATTERY_4, MAINS_2]


# ─── the queue moves on ───────────────────────────────────────────────────────

def test_upgrade_end_frees_the_slot_for_the_next_device(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))
    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="00"))
    radio.zcl_raw_ota_image_notify.reset_mock()

    ota.heartbeat()

    assert DEVICE_NWKID not in _states(ota)
    assert MAINS_6 in _notified(radio)
    assert _states(ota)[MAINS_6] == ota_module.OTA_NOTIFYING


def test_failed_upgrade_frees_the_slot_too(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="96"))
    ota.heartbeat()

    assert _states(ota)[MAINS_6] == ota_module.OTA_NOTIFYING


def test_stalled_transfer_frees_the_slot(ota_module, ota, radio, ikea_image, devices, request_of):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _query(ota, radio, DEVICE_NWKID)
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - ota_module.OTA_BLOCK_TIMEOUT - 1

    ota.heartbeat()

    assert _states(ota)[DEVICE_NWKID] == ota_module.OTA_STALLED
    assert _states(ota)[MAINS_6] == ota_module.OTA_NOTIFYING


def test_stalled_device_that_asks_while_the_slots_are_full_is_queued(ota_module, ota, radio, ikea_image, devices, request_of):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _query(ota, radio, DEVICE_NWKID)
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - ota_module.OTA_BLOCK_TIMEOUT - 1
    ota.heartbeat()                                  # 1234 stalled, 6666 notified into its slot

    assert _query(ota, radio, DEVICE_NWKID) == NO_IMAGE_AVAILABLE
    assert _states(ota)[DEVICE_NWKID] == ota_module.OTA_QUEUED


def test_silent_devices_give_their_slot_back_and_stay_authorized(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)

    _end_notify_window(ota_module, ota)

    assert _states(ota) == {**{nwkid: ota_module.OTA_WAITING for nwkid in SLOTS_FULL}, MAINS_6: ota_module.OTA_NOTIFYING}
    # A sleepy device asks hours later: it gets the image
    assert _query(ota, radio, DEVICE_NWKID) == 0x00


def test_waiting_device_turned_away_is_notified_again_when_its_turn_comes(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _end_notify_window(ota_module, ota)              # 1234, 2222 and 3333 waiting, 6666 notified
    _query(ota, radio, MAINS_6)                      # 6666 transferring
    _pick(ota, BATTERY_4, BATTERY_5)                 # 4444 and 5555 notified into the other two slots

    assert _query(ota, radio, DEVICE_NWKID) == NO_IMAGE_AVAILABLE   # mains, the three slots taken
    assert _states(ota)[DEVICE_NWKID] == ota_module.OTA_QUEUED

    ota.ota_image_block_request(block_request(nwkid=MAINS_6))
    ota.ota_upgrade_end_request(upgrade_end(nwkid=MAINS_6, status="00"))
    radio.zcl_raw_ota_image_notify.reset_mock()
    ota.heartbeat()

    # 4444 and 5555 re-notified, 1234 has the free slot
    assert _notified(radio) == [BATTERY_4, BATTERY_5, DEVICE_NWKID]
    assert _states(ota)[DEVICE_NWKID] == ota_module.OTA_NOTIFYING


def test_queue_is_served_oldest_request_first(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL)
    _pick(ota, MAINS_6)
    _pick(ota, BATTERY_4)
    radio.zcl_raw_ota_image_notify.reset_mock()

    _end_notify_window(ota_module, ota)

    # The last heartbeat of the window: retries of 1234, 2222 and 3333, then 6666 and 4444, in that order
    assert _notified(radio)[-5:] == [*SLOTS_FULL, MAINS_6, BATTERY_4]
    assert (_states(ota)[MAINS_6], _states(ota)[BATTERY_4]) == (ota_module.OTA_NOTIFYING, ota_module.OTA_NOTIFYING)


# ─── autoServeOTA ─────────────────────────────────────────────────────────────

def test_auto_serve_device_asking_while_the_slots_are_taken_is_queued(ota_module, ota, radio, ikea_image, devices):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _pick(ota, *SLOTS_FULL)

    assert _query(ota, radio, MAINS_6) == NO_IMAGE_AVAILABLE
    assert _states(ota)[MAINS_6] == ota_module.OTA_QUEUED

    _end_notify_window(ota_module, ota)
    assert _states(ota)[MAINS_6] == ota_module.OTA_NOTIFYING


def test_auto_serve_battery_device_takes_the_extra_slot(ota_module, ota, radio, ikea_image, devices):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _pick(ota, *SLOTS_FULL)

    assert _query(ota, radio, BATTERY_4) == 0x00
    assert len(ota_module.active_ota_requests(ota)) == 4


# ─── requests kept by IEEE ────────────────────────────────────────────────────

def test_device_that_rejoined_with_a_new_short_address_keeps_its_request(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    ota.ListOfDevices["6a6a"] = ota.ListOfDevices.pop(MAINS_6)
    ota.IEEE2NWK["00158d0000006666"] = "6a6a"

    _end_notify_window(ota_module, ota)

    assert _states(ota)["6a6a"] == ota_module.OTA_NOTIFYING
    assert _notified(radio)[-1] == "6a6a"


def test_device_removed_from_the_network_is_dropped_from_the_queue(ota, radio, ikea_image, devices, ota_module):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    del ota.ListOfDevices[MAINS_6]
    del ota.IEEE2NWK["00158d0000006666"]

    _end_notify_window(ota_module, ota)

    assert MAINS_6 not in _states(ota)


# ─── forced update, per request ───────────────────────────────────────────────

def test_forced_update_of_one_device_does_not_force_the_others(ota, radio, ikea_image, devices, request_of):
    ota.restapi_firmware_update([
        {"NwkId": DEVICE_NWKID, "Ep": DEVICE_EP, "Brand": "Ikea", "FileName": "bulb.ota", "ForceUpdate": True},
        {"NwkId": MAINS_2, "Ep": DEVICE_EP, "Brand": "Ikea", "FileName": "bulb.ota", "ForceUpdate": False},
    ])

    assert request_of(DEVICE_NWKID)["ImageVersion"] == IMAGE_VERSION + 0x10100000
    assert request_of(MAINS_2)["ImageVersion"] == IMAGE_VERSION


# ─── WebUI footer and request list ────────────────────────────────────────────

def test_health_lists_the_active_transfers_and_every_request(ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    health = ota.PluginHealth["Firmware Update"]

    assert health["Device"] == f"{DEVICE_NWKID}, {MAINS_2}, {MAINS_3}"
    assert health["Progress"] == "0%, Notified, Notified"
    assert [(request["NwkId"], request["Status"], request["State"]) for request in health["Requests"]] == [
        (DEVICE_NWKID, "Active", "Transfer"),
        (MAINS_2, "Active", "Notifying"),
        (MAINS_3, "Active", "Notifying"),
        (MAINS_6, "Not Active", "Queued"),
    ]
    assert health["Requests"][0]["FileName"] == "bulb.ota"


def test_health_keeps_the_outcome_of_the_last_transfer(ota, radio, ikea_image):
    _pick(ota, DEVICE_NWKID)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="00"))

    health = ota.PluginHealth["Firmware Update"]
    assert (health["Device"], health["Progress"], health["Requests"]) == (DEVICE_NWKID, "Success", [])


@pytest.mark.parametrize("name, expected", [("Bulb", "Bulb"), ("", DEVICE_IEEE), (None, DEVICE_IEEE)])
def test_request_list_names_the_device_or_falls_back_to_its_ieee(ota, radio, ikea_image, name, expected):
    """Field test 2026-10-26: a device never named in the WebUI has ZDeviceName "", which was shown as is."""
    if name is None:
        del ota.ListOfDevices[DEVICE_NWKID]["ZDeviceName"]
    else:
        ota.ListOfDevices[DEVICE_NWKID]["ZDeviceName"] = name

    _pick(ota, DEVICE_NWKID)
    assert ota.PluginHealth["Firmware Update"]["Requests"][0]["Name"] == expected

    _query(ota, radio, DEVICE_NWKID, version=IMAGE_VERSION)   # already up to date: dropped, the widget says so
    assert ota.adminWidgets.updateNotificationWidget.call_args.args[1].startswith(f"Firmware update not needed for Device: {expected} - ")


# ─── Cancel from the WebUI ────────────────────────────────────────────────────

def test_cancel_a_queued_request(ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)

    assert ota.cancel_current_firmware_update(MAINS_6) == [MAINS_6]

    assert MAINS_6 not in _states(ota)
    assert _query(ota, radio, MAINS_6) == NO_IMAGE_AVAILABLE


def test_cancel_a_transfer_frees_its_slot_for_the_next_device(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, *SLOTS_FULL, MAINS_6)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    ota.cancel_current_firmware_update(DEVICE_NWKID)
    ota.heartbeat()

    assert DEVICE_NWKID not in _states(ota)
    assert _states(ota)[MAINS_6] == ota_module.OTA_NOTIFYING


@pytest.mark.parametrize("request_frame, handler", [(block_request, "ota_image_block_request"), (page_request, "ota_image_page_request")])
def test_cancelled_transfer_gets_abort_at_its_next_request(ota, radio, ikea_image, request_frame, handler):
    """ZCL rev 8 11.13.8.2.1: ABORT makes the client stop the download and keep its firmware."""
    _pick(ota, DEVICE_NWKID)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))
    ota.cancel_current_firmware_update(DEVICE_NWKID)
    radio.zcl_raw_ota_image_block_response_success.reset_mock()

    getattr(ota, handler)(request_frame(nwkid=DEVICE_NWKID, offset=0x30, sqn=0x42))

    radio.zcl_raw_ota_image_block_response_success.assert_not_called()
    call = radio.zcl_raw_ota_image_block_response_abort.call_args
    assert (call.args[1], call.args[3], call.args[4], call.kwargs["sqn"]) == (DEVICE_NWKID, DEVICE_EP, "95", "42")


def test_upgrade_end_after_the_abort_is_expected_not_a_duplicate(ota, radio, ikea_image):
    """Field test 2026-10-26 (Legrand NLV, NLF): after the ABORT the device sends Upgrade End
    status 0x96 (INVALID_IMAGE). It was logged as a Warning "most likely a duplicated packet"."""
    _pick(ota, DEVICE_NWKID)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))
    ota.cancel_current_firmware_update(DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID, offset=0x30))
    ota.log.logging.reset_mock()

    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="96"))

    levels = [call.args[1] for call in ota.log.logging.call_args_list]
    assert "Warning" not in levels
    assert any(call.args[1] == "Status" and "stopped after the cancel" in call.args[2] for call in ota.log.logging.call_args_list)
    radio.zcl_raw_ota_upgrade_end_response.assert_not_called()


def test_abort_only_within_the_window_after_the_cancel(ota_module, ota, radio, ikea_image):
    _pick(ota, DEVICE_NWKID)
    ota.cancel_current_firmware_update(DEVICE_NWKID)
    ota.ota_cancelled[DEVICE_IEEE] -= ota_module.OTA_CANCEL_ABORT_WINDOW + 1

    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    radio.zcl_raw_ota_image_block_response_abort.assert_not_called()


def test_auto_serve_does_not_queue_a_cancelled_device_again(ota, radio, ikea_image):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _pick(ota, DEVICE_NWKID)
    ota.cancel_current_firmware_update(DEVICE_NWKID)

    assert _query(ota, radio, DEVICE_NWKID) == NO_IMAGE_AVAILABLE
    assert _states(ota) == {}


def test_a_cancelled_device_picked_again_is_served(ota_module, ota, radio, ikea_image):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _pick(ota, DEVICE_NWKID)
    ota.cancel_current_firmware_update(DEVICE_NWKID)

    assert _pick(ota, DEVICE_NWKID)[0]["Status"] == "Queued"
    assert DEVICE_IEEE not in ota.ota_cancelled
    assert _query(ota, radio, DEVICE_NWKID) == 0x00
    radio.zcl_raw_ota_image_block_response_abort.reset_mock()
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))
    radio.zcl_raw_ota_image_block_response_abort.assert_not_called()


def test_cancel_a_device_without_request(ota, radio, ikea_image):
    assert ota.cancel_current_firmware_update(DEVICE_NWKID) == []
    assert ota.ota_cancelled == {}


# ─── ZiGate (native mode) ─────────────────────────────────────────────────────

def test_zigate_serves_one_device_at_a_time(ota, radio, ikea_image, devices):
    ota.pluginconf.pluginConf["ControllerInRawMode"] = False

    _pick(ota, DEVICE_NWKID, MAINS_2, BATTERY_4)

    # One Image Notify (0505), after its image was loaded into the ZiGate (0500)
    assert [call.args[0] for call in ota.ControllerLink.sendData.call_args_list] == ["0500", "0505"]
    assert _query(ota, radio, BATTERY_4) == NO_IMAGE_AVAILABLE
