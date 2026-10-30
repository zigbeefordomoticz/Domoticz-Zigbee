"""
test_OTA_query_next_image.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for OTAManagement.query_next_image_request and
is_image_for_query_next_image_request: the server-side answer to a
Query Next Image Request (ZCL command 0x01 of cluster 0x0019).

Reference: Zigbee Cluster Library rev 8 (07-5123-08)
    11.13.4    Query Next Image Request: field control, manufacturer code,
               image type, current file version, optional hardware version
               (little-endian on the air)
    11.13.4.4  the server SHALL check the hardware version, when present,
               against the image's minimum / maximum hardware version
    11.13.5    Query Next Image Response: SUCCESS with manufacturer code,
               image type, file version and image size, or a status only
               (NO_IMAGE_AVAILABLE 0x98)
    11.13.5.2.4  reinstalling the same file version is not supported

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_query_next_image.py -v
"""

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, make_ota_image, query_next_image

IMAGE_VERSION = 0x01020304
NO_IMAGE_AVAILABLE = 0x98


@pytest.fixture
def ikea_image(install_image):
    return install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=IMAGE_VERSION))


def _response(radio):
    """(status, manuf, image type, file version, image size) of the single Query Next Image Response sent."""
    radio.zcl_raw_ota_query_next_image_response.assert_called_once()
    args = radio.zcl_raw_ota_query_next_image_response.call_args.args
    # (self, sqn, nwkid, zigate_ep, dest_ep, status, [manuf, type, version, size])
    assert args[1:5] == ("2a", DEVICE_NWKID, "01", DEVICE_EP)
    return args[5:]


def _queue(ota_module, ota, force=False):
    """The device is picked in the WebUI for bulb.ota."""
    assert ota_module.firmware_update(ota, "Ikea", "bulb.ota", DEVICE_NWKID, DEVICE_EP, force_update=force)["Status"] == "Queued"


def _query(ota, version=0x01000000, image_type=0x2203, manuf_code=0x117C, nwkid=DEVICE_NWKID, hw_version=None):
    ota.query_next_image_request(nwkid, DEVICE_EP, "2a", query_next_image(manuf_code, image_type, version, hw_version))


# ─── request decoding ─────────────────────────────────────────────────────────

def test_request_is_decoded_little_endian_and_stored(ota, radio):
    _query(ota, version=0x01000000, image_type=0x2203, manuf_code=0x117C)

    assert ota.ListOfDevices[DEVICE_NWKID]["OTAClient"] == {
        "ManufacturerCode": 0x117C,
        "ImageType": 0x2203,
        "CurrentImageVersion": 0x01000000,
        "Images": {"2203": {"ManufacturerCode": 0x117C, "CurrentImageVersion": 0x01000000}},
    }


# ─── no image to offer ────────────────────────────────────────────────────────

def test_no_image_for_this_type(ota, radio, ikea_image):
    _query(ota, image_type=0x4204)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)


def test_no_image_for_this_manufacturer(ota, radio, ikea_image):
    _query(ota, manuf_code=0x100B)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)


@pytest.mark.parametrize("device_version", [IMAGE_VERSION, IMAGE_VERSION + 1])
def test_device_already_on_this_version_or_newer(ota, radio, ikea_image, device_version):
    """ZCL8 11.13.5.2.4: the same version is never offered again."""
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    _query(ota, version=device_version)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)


def test_newer_image_but_device_not_authorized(ota, radio, ikea_image):
    """Server policy: without autoServeOTA, only a device picked in the WebUI is served."""
    _query(ota)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)


def test_device_not_picked_while_another_is_being_upgraded(ota_module, ota, radio, ikea_image, add_device):
    add_device("abcd", "00158d00000000ab")
    ota_module.firmware_update(ota, "Ikea", "bulb.ota", "abcd", DEVICE_EP)

    _query(ota)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)


# ─── image offered ────────────────────────────────────────────────────────────

def test_authorized_device_gets_the_image(ota_module, ota, radio, ikea_image):
    _queue(ota_module, ota)

    _query(ota)

    assert _response(radio) == (0x00, 0x117C, 0x2203, IMAGE_VERSION, ikea_image["intSize"])


def test_auto_serve_offers_the_image_and_authorizes_the_device(ota_module, ota, radio, ikea_image, request_of):
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    _query(ota)

    assert _response(radio) == (0x00, 0x117C, 0x2203, IMAGE_VERSION, ikea_image["intSize"])
    request = request_of(DEVICE_NWKID)
    assert (request["State"], request["FileName"], request["AutoServe"]) == (ota_module.OTA_TRANSFER, "bulb.ota", True)


def test_auto_serve_authorizes_a_device_once(ota, radio, ikea_image):
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    for _ in range(3):
        _query(ota)

    assert len(ota.ota_requests) == 1


def test_forced_update_offers_a_bumped_version(ota_module, ota, radio, ikea_image):
    """ForceUpdate serves the image even to a newer device, as version + 0x10100000."""
    _queue(ota_module, ota, force=True)

    _query(ota, version=0x05000000)

    assert _response(radio) == (0x00, 0x117C, 0x2203, IMAGE_VERSION + 0x10100000, ikea_image["intSize"])


def test_hardware_version_outside_the_image_range(ota, radio, install_image):
    install_image("Ikea", "bulb.ota", make_ota_image(version=IMAGE_VERSION, field_control=0x04, min_hw=0x0200, max_hw=0x0300))
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    _query(ota, hw_version=0x0100)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)


# ─── is_image_for_query_next_image_request ────────────────────────────────────

def test_image_lookup(ota_module, ota, ikea_image):
    lookup = ota_module.is_image_for_query_next_image_request

    assert lookup(ota, DEVICE_NWKID, 0x117C, 0x2203, 0x01000000, False) is ikea_image
    assert lookup(ota, DEVICE_NWKID, 0x117C, 0x2203, IMAGE_VERSION, False) is None
    assert lookup(ota, DEVICE_NWKID, 0x117C, 0x2203, 0x09000000, True) is ikea_image
    assert lookup(ota, DEVICE_NWKID, 0x117C, 0x4204, 0x01000000, True) is None
    assert lookup(ota, DEVICE_NWKID, 0x100B, 0x2203, 0x01000000, True) is None


# ─── online firmware index (checkFirmwareAgainstZigbeeOTARepository) ──────────

def test_online_index_hit_is_reported_once(ota, radio):
    ota.pluginconf.pluginConf["checkFirmwareAgainstZigbeeOTARepository"] = True
    ota.zigbee_ota_index = [
        {"manufacturerCode": 0x117C, "imageType": 0x2203, "fileVersion": 0x02000000, "url": "https://example.invalid/bulb.ota"},
    ]

    _query(ota, version=0x01000000)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)
    assert ota.ListOfDevices[DEVICE_NWKID]["OTAUpdate"] == {
        0x2203: {"currentversion": str(0x01000000), "newestversion": str(0x02000000), "url": "https://example.invalid/bulb.ota"}
    }
    assert ota.zigbee_ota_found_in_index == [(0x117C, 0x2203, 0x01000000)]


@pytest.mark.parametrize("hw_version", [0x0200, 0x0250, 0x0300, None])
def test_hardware_version_inside_the_range_or_not_sent(ota, radio, install_image, hw_version):
    """The range is inclusive; a client that does not send its hardware version is not refused."""
    image = install_image("Ikea", "bulb.ota", make_ota_image(version=IMAGE_VERSION, field_control=0x04, min_hw=0x0200, max_hw=0x0300))
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    _query(ota, hw_version=hw_version)

    assert _response(radio) == (0x00, 0x117C, 0x2203, IMAGE_VERSION, image["intSize"])


def test_hardware_version_is_checked_on_a_forced_update_too(ota_module, ota, radio, install_image):
    install_image("Ikea", "bulb.ota", make_ota_image(version=IMAGE_VERSION, field_control=0x04, min_hw=0x0200, max_hw=0x0300))
    _queue(ota_module, ota, force=True)

    _query(ota, hw_version=0x0400)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)
    # Nothing will ever be offered to it: its request is dropped, and the user told why
    assert ota.ota_requests == {}
    assert "hardware version 0x0400" in ota.adminWidgets.updateNotificationWidget.call_args.args[1]


def test_picked_device_asking_for_another_image_type_keeps_its_request(ota_module, ota, radio, ikea_image, install_image, request_of):
    install_image("Ikea", "remote.ota", make_ota_image(manuf_code=0x117C, image_type=0x4204, version=IMAGE_VERSION))
    _queue(ota_module, ota)

    _query(ota, image_type=0x4204)

    assert _response(radio) == (NO_IMAGE_AVAILABLE,)
    assert request_of(DEVICE_NWKID)["FileName"] == "bulb.ota"


def test_image_without_a_hardware_range_accepts_any_hardware(ota, radio, ikea_image):
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    _query(ota, hw_version=0x0F00)

    assert _response(radio)[0] == 0x00
