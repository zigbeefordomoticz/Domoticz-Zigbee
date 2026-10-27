"""
test_OTA_upgrade_end.py
~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the end of a transfer: OTAManagement.ota_upgrade_end_request,
ota_upgrade_end_response, notify_upgrade_end, cleanup_after_completed_upgrade,
and the heartbeat timeout of a stalled transfer.

Reference: Zigbee Cluster Library rev 8 (07-5123-08)
    11.13.9    Upgrade End Request status: SUCCESS, INVALID_IMAGE (0x96),
               REQUIRE_MORE_IMAGE (0x99) or ABORT (0x95)
    11.13.9.4  only SUCCESS gets an Upgrade End Response (manufacturer code,
               image type and file version of the request, current time,
               upgrade time); other statuses get none

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_upgrade_end.py -v
"""

import time

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, block_request, make_ota_image, upgrade_end

IMAGE_VERSION = 0x01020304


@pytest.fixture
def transferring(ota_module, ota, radio, install_image):
    """The device was notified and has fetched its first block."""
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))
    assert ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP)["Status"] == "Queued"
    ota.ota_image_block_request(block_request())
    ota.adminWidgets.updateNotificationWidget.reset_mock()
    return ota


def _session_closed(ota):
    return ota.ota_requests == {}


# ─── SUCCESS ──────────────────────────────────────────────────────────────────

def test_success_is_answered_and_recorded(ota, radio, transferring):
    ota.ota_upgrade_end_request(upgrade_end(status="00", sqn=0x20))

    radio.zcl_raw_ota_upgrade_end_response.assert_called_once_with(
        ota, "20", DEVICE_NWKID, "01", DEVICE_EP, 0x117C, 0x2203, IMAGE_VERSION, 0, 0
    )
    [record] = ota.ListOfDevices[DEVICE_NWKID]["OTAUpgrade"].values()
    assert (record["Version"], record["Type"]) == ("01020304", "2203")
    assert ota.PluginHealth["Firmware Update"]["Progress"] == "Success"
    assert "has been updated" in ota.adminWidgets.updateNotificationWidget.call_args.args[1]


def test_success_closes_the_session(ota, radio, transferring):
    ota.ota_upgrade_end_request(upgrade_end(status="00"))

    assert _session_closed(ota)
    # Basic and OTA clusters re-read 120 s later, to pick up the new version
    assert ota.ListOfDevices[DEVICE_NWKID]["DelayReadAttributes"]["Clusters"] == ["0000", "0019"]
    radio.sendZigateCmd.assert_not_called()


def test_success_clears_the_firmware_available_flag(ota_module, ota, radio, transferring):
    ota_module.notify_ota_firmware_available(
        ota, DEVICE_NWKID, 0x117C, 0x2203, 0x01000000, {"fileVersion": IMAGE_VERSION, "imageType": 0x2203, "url": "https://example.invalid"}
    )
    assert ota.ListOfDevices[DEVICE_NWKID]["OTAUpdate"]

    ota.ota_upgrade_end_request(upgrade_end(status="00"))

    assert ota.ListOfDevices[DEVICE_NWKID]["OTAUpdate"] == {}


def test_success_clears_the_firmware_available_flag_after_a_reload(ota, radio, transferring):
    """Once the device list went through JSON, the int key is a decimal string."""
    ota.ListOfDevices[DEVICE_NWKID]["OTAUpdate"] = {str(0x2203): {"currentversion": "1", "newestversion": "2", "url": "u"}, "4204": {"url": "v"}}

    ota.ota_upgrade_end_request(upgrade_end(status="00"))

    assert ota.ListOfDevices[DEVICE_NWKID]["OTAUpdate"] == {"4204": {"url": "v"}}


# ─── other statuses ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("status, progress", [("95", "Aborted"), ("96", "Failed"), ("99", "More"), ("42", "Aborted")])
def test_non_success_gets_no_upgrade_end_response(ota, radio, transferring, status, progress):
    ota.ota_upgrade_end_request(upgrade_end(status=status))

    radio.zcl_raw_ota_upgrade_end_response.assert_not_called()
    assert ota.PluginHealth["Firmware Update"]["Progress"] == progress
    # The slot goes to the next device: one that failed asks again on its own (autoServeOTA)
    assert _session_closed(ota)


def test_wait_for_data_status_keeps_the_session(ota, radio, transferring, request_of):
    ota.ota_upgrade_end_request(upgrade_end(status="97"))

    radio.zcl_raw_ota_upgrade_end_response.assert_not_called()
    assert request_of(DEVICE_NWKID) is not None


# ─── requests that do not belong to the session ──────────────────────────────

def test_upgrade_end_without_a_session_is_ignored(ota, radio):
    ota.ota_upgrade_end_request(upgrade_end(status="00"))

    radio.zcl_raw_ota_upgrade_end_response.assert_not_called()


def test_upgrade_end_from_another_device_is_ignored(ota, radio, transferring, add_device, request_of):
    add_device("5678", "00158d0000000002")

    ota.ota_upgrade_end_request(upgrade_end(nwkid="5678", status="00"))

    radio.zcl_raw_ota_upgrade_end_response.assert_not_called()
    assert request_of(DEVICE_NWKID) is not None


# ─── stalled transfer ─────────────────────────────────────────────────────────

def test_stalled_transfer_stays_listed_after_300_seconds(ota_module, ota, radio, transferring, request_of):
    """A stalled transfer is not finished: the device usually resumes (production 2026-10-27, Philips motion sensor 11 times)."""
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - 301

    ota.heartbeat()

    request = request_of(DEVICE_NWKID)
    assert request["State"] == ota_module.OTA_STALLED
    assert request["QueuedTime"] >= time.time() - 1
    assert ota.PluginHealth["Firmware Update"]["Requests"][0]["State"] == "Stalled"
    assert "no block requested for 300 sec" in ota.adminWidgets.updateNotificationWidget.call_args.args[1]


def test_stalled_transfer_resumes_at_its_next_block_request(ota_module, ota, radio, transferring, request_of):
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - 301
    ota.heartbeat()

    ota.ota_image_block_request(block_request(offset=0x60))

    request = request_of(DEVICE_NWKID)
    assert (request["State"], request["intFileOffset"]) == (ota_module.OTA_TRANSFER, 0x60)


def test_stalled_transfer_not_resumed_within_24_hours_is_finished(ota_module, ota, radio, transferring, request_of):
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - 301
    ota.heartbeat()
    request_of(DEVICE_NWKID)["QueuedTime"] = time.time() - ota_module.OTA_QUEUE_WAIT - 1

    ota.heartbeat()

    assert _session_closed(ota)
    assert ota.PluginHealth["Firmware Update"]["Progress"] == "Timeout"
    assert "did not resume bulb.ota within 24 hours" in ota.adminWidgets.updateNotificationWidget.call_args.args[1]


def test_stalled_transfer_can_be_cancelled(ota_module, ota, radio, transferring, request_of):
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - 301
    ota.heartbeat()

    assert ota.cancel_current_firmware_update(DEVICE_NWKID) == [DEVICE_NWKID]
    assert _session_closed(ota)


def test_transfer_in_progress_is_kept(ota, radio, transferring, request_of):
    request_of(DEVICE_NWKID)["LastBlockSent"] = time.time() - 200

    ota.heartbeat()

    assert request_of(DEVICE_NWKID) is not None
