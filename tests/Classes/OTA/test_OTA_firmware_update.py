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

Several tests pin today's single-device behaviour on purpose
(restapi_firmware_update drops a list of more than one device, a second
request is refused while one is active). Issue #2169 changes that
behaviour: those tests are expected to be rewritten with it.

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_firmware_update.py -v
"""

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, make_ota_image, query_next_image

IMAGE_VERSION = 0x01020304
FORCED_VERSION = IMAGE_VERSION + 0x10100000


@pytest.fixture
def ikea_image(install_image):
    return install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))


def _request(nwkid=DEVICE_NWKID, ep=DEVICE_EP, brand="Ikea", file_name="bulb.ota", force=False):
    return {"NwkId": nwkid, "Ep": ep, "Brand": brand, "FileName": file_name, "ForceUpdate": force}


# ─── firmware_update ──────────────────────────────────────────────────────────

def test_firmware_update_authorizes_and_notifies_the_device(ota_module, ota, radio, ikea_image):
    assert ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP) is True

    assert ota.ListInUpdate["NwkId"] == DEVICE_NWKID
    assert ota.ListInUpdate["Ep"] == DEVICE_EP
    assert ota.ListInUpdate["AuthorizedForUpdate"] == [DEVICE_NWKID]
    # Image Notify, payload type 3, jitter 100 (ZCL8 11.13.3)
    radio.zcl_raw_ota_image_notify.assert_called_once_with(ota, DEVICE_NWKID, "01", DEVICE_EP, "03", "64", "117c", "2203", "01020304")
    assert ota.ImageLoaded["NotifiedTimeStamp"] > 0
    assert ota.ImageLoaded["LoadedTimeStamp"] > 0
    assert ota.ImageLoaded["image_type"] == 0x2203


def test_forced_update_advertises_a_bumped_version(ota_module, ota, radio, ikea_image):
    ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP, force_update=True)

    radio.zcl_raw_ota_image_notify.assert_called_once_with(ota, DEVICE_NWKID, "01", DEVICE_EP, "03", "64", "117c", "2203", "%08X" % FORCED_VERSION)


@pytest.mark.parametrize(
    "brand, file_name, nwkid, ep",
    [
        ("NoSuchBrand", "bulb.ota", DEVICE_NWKID, DEVICE_EP),
        ("Ikea", "missing.ota", DEVICE_NWKID, DEVICE_EP),
        ("Ikea", "bulb.ota", "ffff", DEVICE_EP),
        ("Ikea", "bulb.ota", DEVICE_NWKID, "0b"),
    ],
)
def test_firmware_update_rejects_unknown_targets(ota_module, ota, radio, ikea_image, brand, file_name, nwkid, ep):
    assert ota_module.firmware_update(ota, brand, file_name, nwkid, ep) is False

    assert ota.ListInUpdate["NwkId"] is None
    radio.zcl_raw_ota_image_notify.assert_not_called()


def test_firmware_update_refused_while_another_is_active(ota_module, ota, radio, ikea_image):
    """Single-device behaviour, changed by #2169."""
    ota.ListInUpdate["NwkId"] = "abcd"

    assert ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP) is False

    radio.zcl_raw_ota_image_notify.assert_not_called()
    assert DEVICE_NWKID not in ota.ListInUpdate["AuthorizedForUpdate"]


# ─── restapi_firmware_update ──────────────────────────────────────────────────

def test_restapi_single_device(ota, radio, ikea_image):
    assert ota.restapi_firmware_update([_request()]) == [{"NwkId": DEVICE_NWKID, "Status": "Started", "Reason": None}]

    assert ota.ListInUpdate["NwkId"] == DEVICE_NWKID
    radio.zcl_raw_ota_image_notify.assert_called_once()
    assert ota.authorized_device_downgrade == {}


def test_restapi_forced_update_authorizes_a_downgrade(ota, radio, ikea_image):
    ota.restapi_firmware_update([_request(force=True)])

    assert ota.authorized_device_downgrade == {DEVICE_NWKID: True}


def test_restapi_several_devices_are_rejected(ota, radio, ikea_image):
    """Single-device behaviour, changed by #2169: a list of more than one device starts nothing,
    and every device of the list is reported as rejected."""
    ota.ListOfDevices["5678"] = {"IEEE": "00158d0000000002", "Ep": {"01": {"0019": {}}}}

    results = ota.restapi_firmware_update([_request(), _request(nwkid="5678")])

    assert [(result["NwkId"], result["Status"]) for result in results] == [(DEVICE_NWKID, "Rejected"), ("5678", "Rejected")]
    assert ota.ListInUpdate["NwkId"] is None
    assert ota.ListInUpdate["AuthorizedForUpdate"] == []
    radio.zcl_raw_ota_image_notify.assert_not_called()


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


def test_restapi_reports_a_request_refused_while_another_is_active(ota, radio, ikea_image):
    ota.ListInUpdate["NwkId"] = "abcd"

    [result] = ota.restapi_firmware_update([_request()])

    assert result == {"NwkId": DEVICE_NWKID, "Status": "Rejected", "Reason": "Another firmware update is in progress"}


def test_refused_forced_update_does_not_authorize_a_downgrade(ota, radio, ikea_image):
    ota.ListInUpdate["NwkId"] = "abcd"

    ota.restapi_firmware_update([_request(force=True)])

    assert DEVICE_NWKID not in ota.authorized_device_downgrade


# ─── after the notification: the heartbeat ────────────────────────────────────

def test_heartbeat_re_notifies_then_gives_up(ota_module, ota, radio, ikea_image):
    ota.restapi_firmware_update([_request()])
    radio.zcl_raw_ota_image_notify.reset_mock()

    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY):
        ota.heartbeat()

    assert radio.zcl_raw_ota_image_notify.call_count == ota_module.OTA_MAX_NOTIFY_RETRY
    assert ota.ListInUpdate["NwkId"] is None
    assert ota.ListInUpdate["AuthorizedForUpdate"] == []


def test_device_asking_after_the_notify_window_is_turned_away(ota_module, ota, radio, ikea_image):
    """Pins today's behaviour (see the OTA review of 2026-10-25).

    The heartbeat runs every HEARTBEAT (5 s), so the device has about
    OTA_MAX_NOTIFY_RETRY x 5 s = 50 s to react to the Image Notify. A sleepy
    device that queries later, on its own schedule (ZCL8 11.8.2), has lost
    its authorization and gets NO_IMAGE_AVAILABLE unless autoServeOTA is on.
    """
    ota.restapi_firmware_update([_request()])
    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY):
        ota.heartbeat()

    ota.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "2a", query_next_image(0x117C, 0x2203, 0x01000000))

    assert radio.zcl_raw_ota_query_next_image_response.call_args.args[5:] == (0x98,)
