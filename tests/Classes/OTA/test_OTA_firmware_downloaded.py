"""
test_OTA_firmware_downloaded.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for OTAManagement.restapi_firmware_downloaded: a firmware found in an
online index is no longer listed as "to download" once its file is in OTAFirmware/.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_firmware_downloaded.py -v
"""

import pytest
from ota_builders import DEVICE_NWKID, make_ota_image

IKEA = 0x117C
TYPE = 0x2203
NEWEST = 0x02000000


def _downloaded(ota, image_type=str(TYPE), version=str(NEWEST)):
    return ota.restapi_firmware_downloaded(DEVICE_NWKID, image_type, version)


def test_no_file(ota):
    assert not _downloaded(ota)


@pytest.mark.parametrize("version, downloaded", [(NEWEST - 1, False), (NEWEST, True), (NEWEST + 1, True)])
def test_version_of_the_file(ota, install_image, version, downloaded):
    """An older file does not hide the newest firmware (LCA001: 2E00 on disk, 2F00 online)."""
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=IKEA, image_type=TYPE, version=version))

    assert _downloaded(ota) is downloaded


def test_file_of_another_image_type(ota, install_image):
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=IKEA, image_type=0x4204, version=NEWEST))

    assert not _downloaded(ota)


def test_file_of_another_manufacturer(ota, install_image):
    """Image types are manufacturer specific."""
    install_image("Schneider", "other.zigbee", make_ota_image(manuf_code=0x105E, image_type=TYPE, version=NEWEST))

    assert not _downloaded(ota)


@pytest.mark.parametrize("ota_client", [
    {"Images": {"2203": {"ManufacturerCode": IKEA, "CurrentImageVersion": 1}}},
    {"ManufacturerCode": IKEA, "ImageType": TYPE, "CurrentImageVersion": 1},   # written before OTAClient had Images
])
def test_manufacturer_code_of_the_query_wins(ota, install_image, ota_client):
    """The code the device asks its firmware with, not the one of its node descriptor."""
    ota.ListOfDevices[DEVICE_NWKID].update(Manufacturer="1037", OTAClient=ota_client)
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=IKEA, image_type=TYPE, version=NEWEST))

    assert _downloaded(ota)


@pytest.mark.parametrize("manufacturer", ["", None, "not hex"])
def test_unknown_manufacturer_code(ota, install_image, manufacturer):
    ota.ListOfDevices[DEVICE_NWKID]["Manufacturer"] = manufacturer
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=IKEA, image_type=TYPE, version=NEWEST))

    assert not _downloaded(ota)


@pytest.mark.parametrize("image_type, version", [("N/A", str(NEWEST)), (str(TYPE), "N/A"), (None, None)])
def test_unreadable_record(ota, install_image, image_type, version):
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=IKEA, image_type=TYPE, version=NEWEST))

    assert not _downloaded(ota, image_type, version)


def test_file_the_device_never_gets(ota, install_image):
    """A Wiser Heat legacy file does not count for a current Wiser device."""
    ota.ListOfDevices[DEVICE_NWKID].update(Manufacturer="105e", Model="Wiser2-Thermostat")
    install_image("Schneider", "EH_HAC_R_04_01_02.zigbee", make_ota_image(manuf_code=0x105E, image_type=TYPE, version=NEWEST))

    assert not _downloaded(ota)


def test_removed_file(ota, install_image, tmp_path):
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=IKEA, image_type=TYPE, version=NEWEST))
    assert _downloaded(ota)

    next((tmp_path / "OTAFirmware").rglob("bulb.ota")).unlink()
    ota.rescan_firmware_folders()

    assert not _downloaded(ota)
