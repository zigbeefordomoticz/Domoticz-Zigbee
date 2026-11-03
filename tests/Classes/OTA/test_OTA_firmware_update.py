"""
test_OTA_firmware_update.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for starting an OTA from the WebUI: OTAManagement.restapi_firmware_update,
firmware_update and ota_image_advertize, and what the heartbeat does with
the device afterwards.

Reference: Zigbee Cluster Library rev 8 (07-5123-08)
    11.13.3  Image Notify: payload type 0x03 carries query jitter,
             manufacturer code, image type and file version
    11.8.2   sleepy devices cannot be reliably notified; they query the
             server on their own schedule

The queue itself (several devices, transfer slots) is covered by
test_OTA_queue.py.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_firmware_update.py -v
"""

import time

import pytest
from ota_builders import DEVICE_EP, DEVICE_IEEE, DEVICE_NWKID, make_ota_image, query_next_image

IMAGE_VERSION = 0x01020304
FORCED_VERSION = IMAGE_VERSION + 0x10100000


@pytest.fixture
def ikea_image(install_image):
    return install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))


def _request(nwkid=DEVICE_NWKID, ep=DEVICE_EP, brand="Ikea", file_name="bulb.ota", force=False):
    return {"NwkId": nwkid, "Ep": ep, "Brand": brand, "FileName": file_name, "ForceUpdate": force}


# ─── firmware_update ──────────────────────────────────────────────────────────

def test_firmware_update_queues_and_notifies_the_device(ota_module, ota, radio, ikea_image, request_of):
    assert ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP) == {"NwkId": DEVICE_NWKID, "Status": "Queued", "Reason": None}

    request = request_of(DEVICE_NWKID)
    assert (request["IEEE"], request["NwkId"], request["Ep"]) == (DEVICE_IEEE, DEVICE_NWKID, DEVICE_EP)
    assert request["State"] == ota_module.OTA_NOTIFYING
    assert request["NotifiedTimeStamp"] > 0
    # Image Notify, payload type 3, jitter 100 (ZCL8 11.13.3)
    radio.zcl_raw_ota_image_notify.assert_called_once_with(ota, DEVICE_NWKID, "01", DEVICE_EP, "03", "64", "117c", "2203", "01020304")
    assert ota.ImageLoaded["image_type"] == 0x2203


def test_forced_update_advertises_a_bumped_version(ota_module, ota, radio, ikea_image, request_of):
    ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP, force_update=True)

    radio.zcl_raw_ota_image_notify.assert_called_once_with(ota, DEVICE_NWKID, "01", DEVICE_EP, "03", "64", "117c", "2203", "%08X" % FORCED_VERSION)
    assert request_of(DEVICE_NWKID)["ImageVersion"] == FORCED_VERSION


def test_forced_update_leaves_the_image_untouched(ota_module, ota, radio, ikea_image):
    """The bumped version belongs to the request: other devices are offered the real one."""
    ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP, force_update=True)

    assert (ikea_image["originalVersion"], ikea_image["intImageVersion"]) == (IMAGE_VERSION, IMAGE_VERSION)


@pytest.mark.parametrize(
    "brand, file_name, nwkid, ep, reason",
    [
        ("NoSuchBrand", "bulb.ota", DEVICE_NWKID, DEVICE_EP, "Unknown brand"),
        ("Ikea", "missing.ota", DEVICE_NWKID, DEVICE_EP, "Unknown firmware file"),
        ("Ikea", "bulb.ota", "ffff", DEVICE_EP, "Unknown device"),
        ("Ikea", "bulb.ota", DEVICE_NWKID, "0b", "Unknown endpoint"),
    ],
)
def test_firmware_update_rejects_unknown_targets(ota_module, ota, radio, ikea_image, brand, file_name, nwkid, ep, reason):
    assert ota_module.firmware_update(ota, brand, file_name, nwkid, ep) == {"NwkId": nwkid, "Status": "Rejected", "Reason": reason}

    assert ota.ota_requests == {}
    radio.zcl_raw_ota_image_notify.assert_not_called()


def test_firmware_update_rejects_a_device_already_queued(ota_module, ota, radio, ikea_image):
    ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP)

    result = ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP, force_update=True)

    assert result["Status"] == "Rejected"
    assert result["Reason"] == "A firmware update is already queued or in progress for this device"
    radio.zcl_raw_ota_image_notify.assert_called_once()


# ─── restapi_firmware_update ──────────────────────────────────────────────────

def test_restapi_single_device(ota, radio, ikea_image, request_of):
    assert ota.restapi_firmware_update([_request()]) == [{"NwkId": DEVICE_NWKID, "Status": "Queued", "Reason": None}]

    radio.zcl_raw_ota_image_notify.assert_called_once()
    assert request_of(DEVICE_NWKID)["ForceUpdate"] is False


def test_restapi_forced_update_is_kept_with_the_request(ota, radio, ikea_image, request_of):
    ota.restapi_firmware_update([_request(force=True)])

    assert request_of(DEVICE_NWKID)["ForceUpdate"] is True


def test_restapi_several_devices_are_queued(ota, radio, ikea_image, add_device):
    """#2169: every device of the list is queued."""
    add_device("5678", "00158d0000000002")

    results = ota.restapi_firmware_update([_request(), _request(nwkid="5678")])

    assert [(result["NwkId"], result["Status"]) for result in results] == [(DEVICE_NWKID, "Queued"), ("5678", "Queued")]
    assert list(ota.ota_requests) == [DEVICE_IEEE, "00158d0000000002"]


def test_restapi_empty_request(ota, radio, ikea_image):
    assert ota.restapi_firmware_update([]) == []

    radio.zcl_raw_ota_image_notify.assert_not_called()


@pytest.mark.parametrize(
    "request_fields, reason",
    [
        ({"brand": "NoSuchBrand"}, "Unknown brand"),
        ({"file_name": "missing.ota"}, "Unknown firmware file"),
        ({"nwkid": "ffff"}, "Unknown device"),
        ({"ep": "0b"}, "Unknown endpoint"),
    ],
)
def test_restapi_reports_why_a_request_is_rejected(ota, radio, ikea_image, request_fields, reason):
    [result] = ota.restapi_firmware_update([_request(**request_fields)])

    assert (result["Status"], result["Reason"]) == ("Rejected", reason)
    radio.zcl_raw_ota_image_notify.assert_not_called()


def test_restapi_rejects_one_device_and_queues_the_others(ota, radio, ikea_image, add_device):
    add_device("5678", "00158d0000000002")

    results = ota.restapi_firmware_update([_request(nwkid="ffff"), _request(nwkid="5678")])

    assert [(result["NwkId"], result["Status"]) for result in results] == [("ffff", "Rejected"), ("5678", "Queued")]


# ─── after the notification: the heartbeat ────────────────────────────────────

def test_heartbeat_re_notifies_then_gives_the_slot_back(ota_module, ota, radio, ikea_image, request_of):
    ota.restapi_firmware_update([_request()])
    radio.zcl_raw_ota_image_notify.reset_mock()

    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY):
        ota.heartbeat()

    assert radio.zcl_raw_ota_image_notify.call_count == ota_module.OTA_MAX_NOTIFY_RETRY
    # No more notifications, but the device keeps its authorization
    assert request_of(DEVICE_NWKID)["State"] == ota_module.OTA_WAITING
    ota.heartbeat()
    assert radio.zcl_raw_ota_image_notify.call_count == ota_module.OTA_MAX_NOTIFY_RETRY


def test_device_asking_after_the_notify_window_gets_the_image(ota_module, ota, radio, ikea_image, request_of):
    """OTA review H1: a sleepy device asks on its own schedule (ZCL8 11.8.2), long after
    the ~50 s of notifications. It is still authorized, and gets the image."""
    ota.restapi_firmware_update([_request()])
    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY):
        ota.heartbeat()

    ota.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "2a", query_next_image(0x117C, 0x2203, 0x01000000))

    assert radio.zcl_raw_ota_query_next_image_response.call_args.args[5:] == (0x00, 0x117C, 0x2203, IMAGE_VERSION, ikea_image["intSize"])
    assert request_of(DEVICE_NWKID)["State"] == ota_module.OTA_TRANSFER


def test_queued_device_that_never_asks_is_dropped_after_the_queue_wait(ota_module, ota, radio, ikea_image, request_of):
    ota.restapi_firmware_update([_request()])
    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY):
        ota.heartbeat()
    request_of(DEVICE_NWKID)["QueuedTime"] = time.time() - ota_module.OTA_QUEUE_WAIT - 1

    ota.heartbeat()

    assert ota.ota_requests == {}
    assert "did not ask for bulb.ota within 24 hours" in ota.adminWidgets.updateNotificationWidget.call_args.args[1]
    assert ota.PluginHealth["Firmware Update"]["Progress"] == "Dropped"


def test_device_already_up_to_date_is_dropped_when_it_asks(ota, radio, ikea_image):
    ota.restapi_firmware_update([_request()])

    ota.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "2a", query_next_image(0x117C, 0x2203, IMAGE_VERSION))

    assert radio.zcl_raw_ota_query_next_image_response.call_args.args[5:] == (0x98,)
    assert ota.ota_requests == {}
    assert "already runs version 0x01020304" in ota.adminWidgets.updateNotificationWidget.call_args.args[1]


def test_cancel_drops_the_request(ota, radio, ikea_image):
    ota.restapi_firmware_update([_request()])

    ota.cancel_current_firmware_update(DEVICE_NWKID)

    assert ota.ota_requests == {}
    assert ota.PluginHealth["Firmware Update"]["Progress"] == "Cancelled"
