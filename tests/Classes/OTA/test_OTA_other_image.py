"""
test_OTA_other_image.py
~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for a device that holds two images and asks for both in turn, while
it is being updated with one of them: request_for_another_image, called by the
Query Next Image, Image Block, Image Page and Upgrade End Request handlers.

Field case: NodOn SIN-4-FP-21 (manufacturer code 0x128B) has an image 0x0006
for its radio (EFR32) and an image 0x0106 for its power board (STM32). A device
is served one firmware at a time: the messages about the other image leave the
request alone, and are logged once per request.

Reference: Zigbee Cluster Library rev 8 (07-5123-08)
    11.13.6.4  an image is identified by manufacturer code, image type and
               file version

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_other_image.py -v
"""

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, block_request, make_ota_image, page_request, query_next_image, upgrade_end

NODON = 0x128B
RADIO, POWER = 0x0006, 0x0106
RADIO_VERSION, POWER_VERSION = 0x0000030C, 0x00030103
NO_IMAGE_AVAILABLE = 0x98


@pytest.fixture
def nodon(ota_module, ota, install_image):
    """Both NodOn images loaded, the device picked in the WebUI for the radio image."""
    install_image("Nodon", "radio.zigbee", make_ota_image(manuf_code=NODON, image_type=RADIO, version=RADIO_VERSION))
    install_image("Nodon", "power.zigbee", make_ota_image(manuf_code=NODON, image_type=POWER, version=POWER_VERSION))
    ota.ListOfDevices[DEVICE_NWKID]["Manufacturer"] = "128b"
    assert ota_module.firmware_update(ota, "Nodon", "radio.zigbee", DEVICE_NWKID, DEVICE_EP)["Status"] == "Queued"
    return ota


@pytest.fixture
def transferring(nodon):
    """The device has fetched the first block of the radio image."""
    nodon.ota_image_block_request(block_request(offset=0, version=0x0300, image_type=RADIO, manuf_code=NODON))
    nodon.adminWidgets.updateNotificationWidget.reset_mock()
    return nodon


def _request(ota):
    (request,) = ota.ota_requests.values()
    return request


def _other_image_logs(ota):
    return [call.args[1] for call in ota.log.logging.call_args_list if "ignored: the device is being updated with radio.zigbee" in call.args[2]]


def test_second_firmware_for_the_same_device_is_rejected(ota_module, nodon):
    result = ota_module.firmware_update(nodon, "Nodon", "power.zigbee", DEVICE_NWKID, DEVICE_EP)

    assert result["Status"] == "Rejected"
    assert _request(nodon)["FileName"] == "radio.zigbee"


def test_query_for_the_other_image_gets_no_image(nodon, radio):
    radio.zcl_raw_ota_query_next_image_response.reset_mock()

    nodon.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "01", query_next_image(NODON, POWER, 0x00030100))

    assert radio.zcl_raw_ota_query_next_image_response.call_args.args[5] == NO_IMAGE_AVAILABLE
    assert _request(nodon)["FileName"] == "radio.zigbee"


def test_query_for_the_image_of_the_request_is_served(nodon, radio):
    nodon.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "01", query_next_image(NODON, RADIO, 0x0300))

    args = radio.zcl_raw_ota_query_next_image_response.call_args.args
    assert args[5:9] == (0x00, NODON, RADIO, RADIO_VERSION)


def test_block_request_for_the_other_image_leaves_the_transfer_alone(transferring, radio):
    transferring.ota_image_block_request(block_request(offset=4096, version=0x0300, image_type=RADIO, manuf_code=NODON))
    request = _request(transferring)
    before = {key: request[key] for key in ("State", "intFileOffset", "Process", "Progress")}
    radio.zcl_raw_ota_image_block_response_success.reset_mock()

    transferring.ota_image_block_request(block_request(offset=100, version=0x00030100, image_type=POWER, manuf_code=NODON))

    assert {key: request[key] for key in before} == before
    radio.zcl_raw_ota_image_block_response_success.assert_not_called()


def test_block_request_for_the_other_image_does_not_start_a_queued_request(nodon):
    nodon.ota_requests[nodon.ListOfDevices[DEVICE_NWKID]["IEEE"]]["State"] = "Queued"

    nodon.ota_image_block_request(block_request(offset=0, version=0x00030100, image_type=POWER, manuf_code=NODON))

    assert _request(nodon)["State"] == "Queued"


def test_page_request_for_the_other_image_leaves_the_transfer_alone(transferring, radio):
    request = _request(transferring)
    before = {key: request[key] for key in ("State", "intFileOffset", "Process", "Progress")}
    radio.zcl_raw_ota_image_block_response_success.reset_mock()

    transferring.ota_image_page_request(page_request(offset=0, version=0x00030100, image_type=POWER, manuf_code=NODON))

    assert {key: request[key] for key in before} == before
    radio.zcl_raw_ota_image_block_response_success.assert_not_called()


@pytest.mark.parametrize("status", ["00", "95", "96"])
def test_upgrade_end_for_the_other_image_does_not_end_the_transfer(transferring, radio, status):
    transferring.ota_upgrade_end_request(upgrade_end(version=POWER_VERSION, image_type=POWER, manuf_code=NODON, status=status))

    assert _request(transferring)["State"] == "Transfer"
    radio.zcl_raw_ota_upgrade_end_response.assert_not_called()
    transferring.adminWidgets.updateNotificationWidget.assert_not_called()


def test_upgrade_end_for_the_image_of_the_request_ends_it(transferring, radio):
    transferring.ota_upgrade_end_request(upgrade_end(version=RADIO_VERSION, image_type=RADIO, manuf_code=NODON, status="00"))

    assert transferring.ota_requests == {}
    radio.zcl_raw_ota_upgrade_end_response.assert_called_once()


def test_other_image_is_logged_once_per_request(transferring):
    for _ in range(3):
        transferring.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "01", query_next_image(NODON, POWER, 0x00030100))

    assert _other_image_logs(transferring) == ["Log", "Debug", "Debug"]


def test_legrand_0x00c8_block_request_is_still_served(ota_module, ota, radio, install_image):
    """Legrand block requests carry manufacturer code 0x00C8, patched by initialize_block_request."""
    install_image("Legrand", "nlv.ota", make_ota_image(manuf_code=0x1021, image_type=0x0011, version=0x00420000))
    assert ota_module.firmware_update(ota, "Legrand", "nlv.ota", DEVICE_NWKID, DEVICE_EP)["Status"] == "Queued"

    ota.ota_image_block_request(block_request(offset=0, version=0x00410000, image_type=0x0011, manuf_code=0x00C8))

    radio.zcl_raw_ota_image_block_response_success.assert_called()
