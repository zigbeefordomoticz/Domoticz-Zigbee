"""
test_OTA_queue.py
~~~~~~~~~~~~~~~~~
Unit tests for the OTA queue (#2169): several devices per firmware update
request, upgraded at the same time within the transfer slots.

Rules under test:
    - OTA_MAX_TRANSFERS (2) devices hold a slot at the same time: notified
      and waiting for the device, or being served;
    - a battery-powered device that asks on its own takes one more slot, up
      to OTA_MAX_TRANSFERS_WITH_BATTERY (3): it may not ask again for hours;
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
from ota_builders import DEVICE_EP, DEVICE_NWKID, block_request, make_ota_image, query_next_image, upgrade_end

IMAGE_VERSION = 0x01020304
NO_IMAGE_AVAILABLE = 0x98

MAINS_2 = "2222"
MAINS_3 = "3333"
BATTERY_4 = "4444"
BATTERY_5 = "5555"


@pytest.fixture
def ikea_image(install_image):
    return install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))


@pytest.fixture
def devices(add_device):
    """1234 (fixture device), 2222 and 3333 are mains-powered, 4444 and 5555 battery-powered."""
    add_device(MAINS_2, "00158d0000002222")
    add_device(MAINS_3, "00158d0000003333")
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


# ─── several devices, two slots ───────────────────────────────────────────────

def test_two_devices_are_notified_the_others_wait(ota_module, ota, radio, ikea_image, devices):
    results = _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)

    assert [result["Status"] for result in results] == ["Queued"] * 3
    assert _notified(radio) == [DEVICE_NWKID, MAINS_2]
    assert _states(ota) == {DEVICE_NWKID: ota_module.OTA_NOTIFYING, MAINS_2: ota_module.OTA_NOTIFYING, MAINS_3: ota_module.OTA_QUEUED}


def test_both_notified_devices_are_served_at_the_same_time(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2)

    assert _query(ota, radio, DEVICE_NWKID) == 0x00
    assert _query(ota, radio, MAINS_2) == 0x00
    assert _states(ota) == {DEVICE_NWKID: ota_module.OTA_TRANSFER, MAINS_2: ota_module.OTA_TRANSFER}


def test_queued_mains_device_asking_while_both_slots_are_taken_waits(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)

    assert _query(ota, radio, MAINS_3) == NO_IMAGE_AVAILABLE
    assert _states(ota)[MAINS_3] == ota_module.OTA_QUEUED


def test_battery_device_asking_takes_the_extra_slot(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, BATTERY_4)

    assert _query(ota, radio, BATTERY_4) == 0x00
    assert _states(ota)[BATTERY_4] == ota_module.OTA_TRANSFER
    assert len(ota_module.active_ota_requests(ota)) == 3


def test_three_transfers_is_the_hard_limit(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, BATTERY_4, BATTERY_5)
    assert _query(ota, radio, BATTERY_4) == 0x00

    assert _query(ota, radio, BATTERY_5) == NO_IMAGE_AVAILABLE
    assert _states(ota)[BATTERY_5] == ota_module.OTA_QUEUED


def test_the_extra_slot_is_never_used_to_notify(ota, radio, ikea_image, devices):
    """The third slot is for a battery device that asks on its own, not for a notification."""
    _pick(ota, DEVICE_NWKID, MAINS_2, BATTERY_4)

    ota.heartbeat()

    assert BATTERY_4 not in _notified(radio)


def test_battery_device_takes_a_regular_slot_too(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, BATTERY_4, MAINS_2)

    assert _notified(radio) == [BATTERY_4, MAINS_2]


# ─── the queue moves on ───────────────────────────────────────────────────────

def test_upgrade_end_frees_the_slot_for_the_next_device(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))
    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="00"))
    radio.zcl_raw_ota_image_notify.reset_mock()

    ota.heartbeat()

    assert DEVICE_NWKID not in _states(ota)
    assert MAINS_3 in _notified(radio)
    assert _states(ota)[MAINS_3] == ota_module.OTA_NOTIFYING


def test_failed_upgrade_frees_the_slot_too(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="96"))
    ota.heartbeat()

    assert _states(ota)[MAINS_3] == ota_module.OTA_NOTIFYING


def test_stalled_transfer_frees_the_slot(ota_module, ota, radio, ikea_image, devices, request_of):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    _query(ota, radio, DEVICE_NWKID)
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - ota_module.OTA_BLOCK_TIMEOUT - 1

    ota.heartbeat()

    assert DEVICE_NWKID not in _states(ota)
    assert _states(ota)[MAINS_3] == ota_module.OTA_NOTIFYING


def test_silent_devices_give_their_slot_back_and_stay_authorized(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)

    _end_notify_window(ota_module, ota)

    assert _states(ota) == {DEVICE_NWKID: ota_module.OTA_WAITING, MAINS_2: ota_module.OTA_WAITING, MAINS_3: ota_module.OTA_NOTIFYING}
    # A sleepy device asks hours later: it gets the image
    assert _query(ota, radio, DEVICE_NWKID) == 0x00


def test_waiting_device_turned_away_is_notified_again_when_its_turn_comes(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    _end_notify_window(ota_module, ota)              # 1234 and 2222 waiting, 3333 notified
    _query(ota, radio, MAINS_3)                      # 3333 transferring
    _pick(ota, BATTERY_4)                            # 4444 notified into the second slot

    assert _query(ota, radio, DEVICE_NWKID) == NO_IMAGE_AVAILABLE   # mains, both slots taken
    assert _states(ota)[DEVICE_NWKID] == ota_module.OTA_QUEUED

    ota.ota_image_block_request(block_request(nwkid=MAINS_3))
    ota.ota_upgrade_end_request(upgrade_end(nwkid=MAINS_3, status="00"))
    radio.zcl_raw_ota_image_notify.reset_mock()
    ota.heartbeat()

    assert _notified(radio) == [BATTERY_4, DEVICE_NWKID]       # 4444 re-notified, 1234 has the free slot
    assert _states(ota)[DEVICE_NWKID] == ota_module.OTA_NOTIFYING


def test_queue_is_served_oldest_request_first(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2)
    _pick(ota, MAINS_3)
    _pick(ota, BATTERY_4)
    radio.zcl_raw_ota_image_notify.reset_mock()

    _end_notify_window(ota_module, ota)

    # The last heartbeat of the window: retries of 1234 and 2222, then 3333 and 4444, in that order
    assert _notified(radio)[-4:] == [DEVICE_NWKID, MAINS_2, MAINS_3, BATTERY_4]
    assert (_states(ota)[MAINS_3], _states(ota)[BATTERY_4]) == (ota_module.OTA_NOTIFYING, ota_module.OTA_NOTIFYING)


# ─── autoServeOTA ─────────────────────────────────────────────────────────────

def test_auto_serve_device_asking_while_the_slots_are_taken_is_queued(ota_module, ota, radio, ikea_image, devices):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _pick(ota, DEVICE_NWKID, MAINS_2)

    assert _query(ota, radio, MAINS_3) == NO_IMAGE_AVAILABLE
    assert _states(ota)[MAINS_3] == ota_module.OTA_QUEUED

    _end_notify_window(ota_module, ota)
    assert _states(ota)[MAINS_3] == ota_module.OTA_NOTIFYING


def test_auto_serve_battery_device_takes_the_extra_slot(ota_module, ota, radio, ikea_image, devices):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _pick(ota, DEVICE_NWKID, MAINS_2)

    assert _query(ota, radio, BATTERY_4) == 0x00


# ─── requests kept by IEEE ────────────────────────────────────────────────────

def test_device_that_rejoined_with_a_new_short_address_keeps_its_request(ota_module, ota, radio, ikea_image, devices):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    ota.ListOfDevices["3a3a"] = ota.ListOfDevices.pop(MAINS_3)
    ota.IEEE2NWK["00158d0000003333"] = "3a3a"

    _end_notify_window(ota_module, ota)

    assert _states(ota)["3a3a"] == ota_module.OTA_NOTIFYING
    assert _notified(radio)[-1] == "3a3a"


def test_device_removed_from_the_network_is_dropped_from_the_queue(ota, radio, ikea_image, devices, ota_module):
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    del ota.ListOfDevices[MAINS_3]
    del ota.IEEE2NWK["00158d0000003333"]

    _end_notify_window(ota_module, ota)

    assert MAINS_3 not in _states(ota)


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
    _pick(ota, DEVICE_NWKID, MAINS_2, MAINS_3)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    health = ota.PluginHealth["Firmware Update"]

    assert health["Device"] == f"{DEVICE_NWKID}, {MAINS_2}"
    assert health["Progress"] == "0%, Notified"
    assert [(request["NwkId"], request["Status"], request["State"]) for request in health["Requests"]] == [
        (DEVICE_NWKID, "Active", "Transfer"),
        (MAINS_2, "Active", "Notifying"),
        (MAINS_3, "Not Active", "Queued"),
    ]
    assert health["Requests"][0]["FileName"] == "bulb.ota"


def test_health_keeps_the_outcome_of_the_last_transfer(ota, radio, ikea_image):
    _pick(ota, DEVICE_NWKID)
    _query(ota, radio, DEVICE_NWKID)
    ota.ota_image_block_request(block_request(nwkid=DEVICE_NWKID))

    ota.ota_upgrade_end_request(upgrade_end(nwkid=DEVICE_NWKID, status="00"))

    health = ota.PluginHealth["Firmware Update"]
    assert (health["Device"], health["Progress"], health["Requests"]) == (DEVICE_NWKID, "Success", [])


# ─── ZiGate (native mode) ─────────────────────────────────────────────────────

def test_zigate_serves_one_device_at_a_time(ota, radio, ikea_image, devices):
    ota.pluginconf.pluginConf["ControllerInRawMode"] = False

    _pick(ota, DEVICE_NWKID, MAINS_2, BATTERY_4)

    # One Image Notify (0505), after its image was loaded into the ZiGate (0500)
    assert [call.args[0] for call in ota.ControllerLink.sendData.call_args_list] == ["0500", "0505"]
    assert _query(ota, radio, BATTERY_4) == NO_IMAGE_AVAILABLE
