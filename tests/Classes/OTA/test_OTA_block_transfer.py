"""
test_OTA_block_transfer.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for serving the image: OTAManagement.ota_image_block_request,
ota_image_page_request, prepare_and_send_block, ota_send_block and
build_ota_data_block, in zigpy (raw) mode.

Reference: Zigbee Cluster Library rev 8 (07-5123-08)
    11.13.6    Image Block Request; the server SHALL NOT send more than the
               client's maximum data size
    11.13.6.5  an invalid file offset is answered by a Default Response
               MALFORMED_COMMAND, not by an Image Block Response
    11.13.7    Image Page Request: one request, several Image Block
               Responses with increasing ZCL sequence numbers, no APS ack,
               file offset incremented, until the page size is reached
    11.13.8.2.1  an Image Block Response status is SUCCESS, ABORT or
               WAIT_FOR_DATA only

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_block_transfer.py -v
"""

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, block_request, make_ota_image, page_request

IMAGE_VERSION = 0x01020304
OTHER_NWKID = "5678"


@pytest.fixture
def ikea_image(install_image):
    # 56-byte header + 200-byte payload = 256 bytes
    return install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))


@pytest.fixture
def notified(ota_module, ota, radio, ikea_image):
    """The device was picked in the WebUI and notified; no block requested yet."""
    assert ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP)
    return ikea_image


def _blocks(radio):
    """Every Image Block Response sent, as dicts."""
    sent = []
    for call in radio.zcl_raw_ota_image_block_response_success.call_args_list:
        (_, sqn, nwkid, _, ep, status, manuf, itype, version, offset, size, data) = call.args
        sent.append({
            "sqn": sqn, "nwkid": nwkid, "ep": ep, "status": status, "manuf": manuf, "type": itype,
            "version": version, "offset": int(offset, 16), "size": int(size, 16), "data": bytes.fromhex(data),
            "no_ack": call.kwargs["ackIsDisabled"], "delay": call.kwargs["min_block_delay"],
        })
    return sent


# ─── Image Block Request ──────────────────────────────────────────────────────

def test_first_block_starts_the_transfer(ota, radio, notified):
    ota.ota_image_block_request(block_request(offset=0, max_size=0x30, sqn=0x10))

    [block] = _blocks(radio)
    assert block == {
        "sqn": "10", "nwkid": DEVICE_NWKID, "ep": DEVICE_EP, "status": "00", "manuf": "117c", "type": "2203",
        "version": "01020304", "offset": 0, "size": 0x30, "data": notified["OtaImage"][:0x30],
        "no_ack": False, "delay": 0.25,   # IKEA vendor profile min_delay
    }
    assert ota.ListInUpdate["Process"] == "Started"
    assert ota.ListInUpdate["Status"] == "Transfer Progress"
    assert ota.ListInUpdate["StartTime"] > 0
    assert ota.PluginHealth["Firmware Update"] == {"Progress": "0%", "Device": DEVICE_NWKID}
    ota.adminWidgets.updateNotificationWidget.assert_called_once()


def test_following_blocks_serve_the_requested_offset(ota, radio, notified):
    ota.ota_image_block_request(block_request(offset=0, max_size=0x30))
    ota.ota_image_block_request(block_request(offset=0x30, max_size=0x30, sqn=0x11))

    second = _blocks(radio)[1]
    assert (second["offset"], second["size"], second["sqn"]) == (0x30, 0x30, "11")
    assert second["data"] == notified["OtaImage"][0x30:0x60]
    assert ota.ListInUpdate["Process"] == "OnGoing"


@pytest.mark.parametrize("max_size, expected", [(0x20, 0x20), (0x64, 64)])
def test_block_size_never_exceeds_client_maximum_nor_vendor_profile(ota, radio, notified, max_size, expected):
    """ZCL8 11.13.6.2.6: never more than the client's maximum data size (IKEA profile caps at 64)."""
    ota.ota_image_block_request(block_request(max_size=max_size))

    assert _blocks(radio)[0]["size"] == expected


def test_last_block_is_shorter(ota, radio, notified):
    ota.ota_image_block_request(block_request(offset=240, max_size=0x30))

    block = _blocks(radio)[0]
    assert (block["status"], block["size"]) == ("00", 16)
    assert block["data"] == notified["OtaImage"][240:]


def test_requested_block_delay_is_honoured_when_above_the_vendor_minimum(ota, radio, notified):
    ota.ota_image_block_request(block_request(delay=1500))

    assert _blocks(radio)[0]["delay"] == 1.5


def test_badly_sized_frame_is_ignored(ota, radio, notified):
    ota.ota_image_block_request(block_request()[:-4])

    radio.zcl_raw_ota_image_block_response_success.assert_not_called()


def test_offset_past_the_image_is_not_answered_with_a_malformed_block(ota, radio, notified):
    ota.ota_image_block_request(block_request(offset=300))

    assert all(block["status"] in ("00", "95", "97") for block in _blocks(radio))


def test_offset_past_the_image_gets_a_malformed_default_response(ota, radio, notified):
    """ZCL8 11.13.6.5.1: Default Response MALFORMED_COMMAND to the Image Block Request (0x03)."""
    ota.ota_image_block_request(block_request(offset=300, sqn=0x10))

    radio.zcl_raw_default_response.assert_called_once_with(ota, DEVICE_NWKID, "01", DEVICE_EP, "0019", "03", "10", command_status="80")
    radio.zcl_raw_ota_image_block_response_abort.assert_not_called()


def test_second_offset_past_the_image_aborts_with_a_status_only_response(ota, radio, notified):
    """Two invalid requests in a row: Image Block Response ABORT, status only (ZCL8 11.13.8.2.1)."""
    ota.ota_image_block_request(block_request(offset=300, sqn=0x10))
    ota.ota_image_block_request(block_request(offset=300, sqn=0x11))

    radio.zcl_raw_ota_image_block_response_abort.assert_called_once_with(ota, DEVICE_NWKID, "01", DEVICE_EP, "95", sqn="11")
    radio.zcl_raw_ota_image_block_response_success.assert_not_called()


def test_a_valid_block_resets_the_invalid_offset_count(ota, radio, notified):
    ota.ota_image_block_request(block_request(offset=300, sqn=0x10))
    ota.ota_image_block_request(block_request(offset=0, sqn=0x11))
    ota.ota_image_block_request(block_request(offset=300, sqn=0x12))

    assert radio.zcl_raw_default_response.call_count == 2
    radio.zcl_raw_ota_image_block_response_abort.assert_not_called()


# ─── requests from a device that was not picked ───────────────────────────────

def test_unauthorized_device_gets_nothing(ota, radio, ikea_image):
    ota.ota_image_block_request(block_request())

    radio.zcl_raw_ota_image_block_response_success.assert_not_called()
    assert ota.ListInUpdate["NwkId"] is None


def test_authorized_device_without_a_session_starts_one(ota, radio, ikea_image):
    """autoServeOTA path: the device was authorized by its Query Next Image Request."""
    ota.ListInUpdate["AuthorizedForUpdate"].append(DEVICE_NWKID)

    ota.ota_image_block_request(block_request())

    assert len(_blocks(radio)) == 1
    assert ota.ListInUpdate["NwkId"] == DEVICE_NWKID


def test_other_device_is_not_served_during_a_transfer(ota, radio, notified):
    ota.ListOfDevices[OTHER_NWKID] = {"IEEE": "00158d0000000002", "Ep": {"01": {"0019": {}}}}
    ota.ota_image_block_request(block_request(offset=0x30))

    ota.ota_image_block_request(block_request(nwkid=OTHER_NWKID, offset=0))

    assert [block["nwkid"] for block in _blocks(radio)] == [DEVICE_NWKID]
    assert ota.ListInUpdate["intFileOffset"] == 0x30
    error = next(call for call in ota.log.logging.call_args_list if call.args[1] == "Error")
    assert error.args[3] == OTHER_NWKID
    assert error.args[4]["Error code"] == "OTA0202"
    assert error.args[4]["InProgressNwkId"] == DEVICE_NWKID


# ─── Image Page Request ───────────────────────────────────────────────────────

def test_page_request_sends_increasing_blocks_without_aps_ack(ota, radio, notified):
    ota.ota_image_page_request(page_request(offset=0, max_size=0x30, page_size=0x90, spacing=100, sqn=0xFE))

    blocks = _blocks(radio)
    assert [block["offset"] for block in blocks] == [0x00, 0x30, 0x60]
    assert [block["sqn"] for block in blocks] == ["fe", "ff", "00"]   # 8-bit, wraps (ZCL8 11.13.7.4)
    assert all(block["no_ack"] for block in blocks)
    assert b"".join(block["data"] for block in blocks) == notified["OtaImage"][:0x90]


def test_page_request_without_a_transfer_is_ignored(ota, radio, ikea_image):
    ota.ota_image_page_request(page_request())

    radio.zcl_raw_ota_image_block_response_success.assert_not_called()


def test_page_request_covers_the_whole_page(ota, radio, notified):
    ota.ota_image_page_request(page_request(offset=0, max_size=0x30, page_size=0x80))

    assert sum(block["size"] for block in _blocks(radio)) == 0x80


def test_last_page_does_not_abort_the_upgrade(ota, radio, notified):
    ota.ota_image_page_request(page_request(offset=192, max_size=0x30, page_size=0x100))

    blocks = _blocks(radio)
    assert all(block["status"] == "00" for block in blocks)
    assert b"".join(block["data"] for block in blocks) == notified["OtaImage"][192:]
    radio.zcl_raw_ota_image_block_response_abort.assert_not_called()
    radio.zcl_raw_default_response.assert_not_called()


def test_page_blocks_are_contiguous_when_the_vendor_caps_the_block_size(ota, radio, notified):
    """The device accepts 100-byte blocks, the IKEA profile sends 64: no hole between blocks."""
    ota.ota_image_page_request(page_request(offset=0, max_size=100, page_size=0x100))

    blocks = _blocks(radio)
    assert [(block["offset"], block["size"]) for block in blocks] == [(0, 64), (64, 64), (128, 64), (192, 64)]
    assert b"".join(block["data"] for block in blocks) == notified["OtaImage"][:0x100]


def test_page_request_past_the_image_sends_nothing(ota, radio, notified):
    ota.ota_image_page_request(page_request(offset=256, max_size=0x30, page_size=0x100))

    radio.zcl_raw_ota_image_block_response_success.assert_not_called()


def test_blocks_come_from_the_requesting_manufacturer_image(ota, radio, install_image):
    """Two manufacturers use image type 0x2203: the Philips device gets the Philips file."""
    install_image("Ikea", "ikea.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, payload=b"\x11" * 200))
    hue = install_image("Philips", "hue.ota", make_ota_image(manuf_code=0x100B, image_type=0x2203, payload=b"\x22" * 200))
    ota.ListInUpdate["AuthorizedForUpdate"].append(DEVICE_NWKID)

    ota.ota_image_block_request(block_request(manuf_code=0x100B, offset=0x40, max_size=0x30))

    [block] = _blocks(radio)
    assert block["manuf"] == "100b"
    assert block["data"] == hue["OtaImage"][0x40:0x70]


def test_pages_come_from_the_requesting_manufacturer_image(ota_module, ota, radio, install_image):
    """Two manufacturers use image type 0x2203, with different sizes: the Philips device's
    page past the end of the 256-byte IKEA file is served from the 456-byte Philips file."""
    install_image("Ikea", "ikea.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, payload=b"\x11" * 200))
    hue = install_image("Philips", "hue.ota", make_ota_image(manuf_code=0x100B, image_type=0x2203, payload=b"\x22" * 400))
    ota_module.firmware_update(ota, "Philips", "hue.ota", DEVICE_NWKID, DEVICE_EP)

    ota.ota_image_page_request(page_request(manuf_code=0x100B, offset=0x100, max_size=0x40, page_size=0x100))

    blocks = _blocks(radio)
    assert {block["manuf"] for block in blocks} == {"100b"}
    assert b"".join(block["data"] for block in blocks) == hue["OtaImage"][0x100:]


# ─── build_ota_data_block ─────────────────────────────────────────────────────

def test_build_ota_data_block(ota_module, ota):
    ota.ListInUpdate["OtaImage"] = bytes(range(100))

    assert ota_module.build_ota_data_block(ota, {"Sequence": "05", "Offset": "00000010"}, 8) == (5, 16, 8, bytes(range(16, 24)))
    assert ota_module.build_ota_data_block(ota, {"Sequence": "06", "Offset": "0000005e"}, 8) == (6, 94, 6, bytes(range(94, 100)))
    assert ota_module.build_ota_data_block(ota, {"Sequence": "07", "Offset": "00000064"}, 8) == (7, 100, 0, b"")


def test_page_request_for_an_unknown_image_logs_an_error_with_context(ota, radio, notified):
    ota.ota_image_page_request(page_request(image_type=0x4204))

    radio.zcl_raw_ota_image_block_response_success.assert_not_called()
    error = next(call for call in ota.log.logging.call_args_list if call.args[1] == "Error")
    assert error.args[3] == DEVICE_NWKID
    assert error.args[4]["Error code"] == "OTA0201"
    assert error.args[4]["ImageType"] == "0x4204"
