"""
test_OTA_client_images.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the versions a device reports for each of its images:
OTAClient["Images"], written by query_next_image_request and read by
known_version_of_image (firmware_update rejects a device already up to date).

Field case: NodOn SIN-4-FP-21 (manufacturer code 0x128B) holds an image 0x0006
for its radio (EFR32) and an image 0x0106 for its power board (STM32), and asks
for both in turn. The top-level OTAClient fields only hold the last query.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_client_images.py -v
"""

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, make_ota_image, query_next_image

NODON = 0x128B
RADIO, POWER = 0x0006, 0x0106
RADIO_VERSION, POWER_VERSION = 0x0000030C, 0x00030103
UP_TO_DATE = "The device already runs this firmware version or a newer one"


@pytest.fixture
def nodon(ota, install_image):
    install_image("Nodon", "radio.zigbee", make_ota_image(manuf_code=NODON, image_type=RADIO, version=RADIO_VERSION))
    install_image("Nodon", "power.zigbee", make_ota_image(manuf_code=NODON, image_type=POWER, version=POWER_VERSION))
    return ota


def _asks(ota, image_type, version, manuf_code=NODON):
    ota.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "2a", query_next_image(manuf_code, image_type, version))


def _ota_client(ota):
    return ota.ListOfDevices[DEVICE_NWKID]["OTAClient"]


def test_each_image_keeps_its_version(nodon):
    _asks(nodon, RADIO, RADIO_VERSION)
    _asks(nodon, POWER, POWER_VERSION)

    assert _ota_client(nodon)["Images"] == {
        "0006": {"ManufacturerCode": NODON, "CurrentImageVersion": RADIO_VERSION},
        "0106": {"ManufacturerCode": NODON, "CurrentImageVersion": POWER_VERSION},
    }
    # The top-level fields stay the last query
    assert (_ota_client(nodon)["ImageType"], _ota_client(nodon)["CurrentImageVersion"]) == (POWER, POWER_VERSION)


def test_a_new_query_updates_the_version_of_its_image(nodon):
    _asks(nodon, RADIO, RADIO_VERSION - 1)
    _asks(nodon, POWER, POWER_VERSION)
    _asks(nodon, RADIO, RADIO_VERSION)

    assert _ota_client(nodon)["Images"]["0006"]["CurrentImageVersion"] == RADIO_VERSION


@pytest.mark.parametrize("file_name", ["radio.zigbee", "power.zigbee"])
def test_up_to_date_is_known_for_both_images(ota_module, nodon, file_name):
    _asks(nodon, RADIO, RADIO_VERSION)
    _asks(nodon, POWER, POWER_VERSION)

    result = ota_module.firmware_update(nodon, "Nodon", file_name, DEVICE_NWKID, DEVICE_EP)

    assert (result["Status"], result["Reason"]) == ("Rejected", UP_TO_DATE)


def test_older_image_not_asked_last_is_queued(ota_module, nodon):
    _asks(nodon, RADIO, RADIO_VERSION - 1)
    _asks(nodon, POWER, POWER_VERSION)

    assert ota_module.firmware_update(nodon, "Nodon", "radio.zigbee", DEVICE_NWKID, DEVICE_EP)["Status"] == "Queued"


def test_entry_without_images_still_gives_the_last_query(ota_module, nodon):
    """Device entry written before OTAClient had Images: its top-level fields are still used."""
    nodon.ListOfDevices[DEVICE_NWKID]["OTAClient"] = {"ManufacturerCode": NODON, "ImageType": RADIO, "CurrentImageVersion": RADIO_VERSION}
    image = nodon.ListOfImages["Brands"]["Nodon"]

    assert ota_module.known_version_of_image(nodon, DEVICE_NWKID, image["radio.zigbee"]) == RADIO_VERSION
    assert ota_module.known_version_of_image(nodon, DEVICE_NWKID, image["power.zigbee"]) is None


def test_same_image_type_of_another_manufacturer_is_not_known(ota_module, nodon):
    _asks(nodon, RADIO, RADIO_VERSION, manuf_code=0x117C)

    assert ota_module.known_version_of_image(nodon, DEVICE_NWKID, nodon.ListOfImages["Brands"]["Nodon"]["radio.zigbee"]) is None
