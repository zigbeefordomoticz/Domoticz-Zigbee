"""
test_OTA_scan_folder.py
~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for loading the firmware folders: ota_scan_folder,
check_image_valid_version, retrieve_image, retrieve_image_in_a_brand and
OTAManagement.restapi_list_of_firmware.

Reference: Zigbee Cluster Library rev 8 (07-5123-08). The server
identifies an image by manufacturer code, image type AND file version
(11.13.6.4); image types are manufacturer specific (11.4.2.6), so two
manufacturers may use the same image type value.

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_scan_folder.py -v
"""

import pytest
from ota_builders import make_ota_image


def test_empty_firmware_folder(ota):
    assert ota.ListOfImages["ImageType"] == {}
    assert all(images == {} for images in ota.ListOfImages["Brands"].values())


def test_image_is_indexed_by_brand_and_image_type(ota, install_image):
    image = make_ota_image(manuf_code=0x117C, image_type=0x2203, version=0x01020304)

    entry = install_image("Ikea", "bulb.ota", image)

    assert ota.ListOfImages["ImageType"][(0x117C, 0x2203)] == "Ikea"
    assert entry["ImageType"] == 0x2203
    assert entry["intManufCode"] == 0x117C
    assert entry["originalVersion"] == 0x01020304
    assert entry["intImageVersion"] == 0x01020304
    assert entry["intSize"] == len(image)
    assert entry["OtaImage"] == image


def test_readme_files_are_skipped(ota, install_image):
    install_image("Ikea", "README.md", make_ota_image())

    assert "README.md" not in ota.ListOfImages["Brands"]["Ikea"]
    assert ota.ListOfImages["ImageType"] == {}


@pytest.mark.parametrize("order", [("old.ota", "new.ota"), ("new.ota", "old.ota")])
def test_only_the_highest_version_of_an_image_type_is_kept(ota, install_image, tmp_path, order):
    """ZCL8 11.13.4.4: the recommended policy serves the highest available file version."""
    versions = {"old.ota": 0x01000000, "new.ota": 0x02000000}
    for name in order:
        install_image("Ikea", name, make_ota_image(version=versions[name]))

    assert list(ota.ListOfImages["Brands"]["Ikea"]) == ["new.ota"]
    assert ota.ListOfImages["Brands"]["Ikea"]["new.ota"]["originalVersion"] == 0x02000000


def test_same_image_type_from_two_manufacturers(ota, install_image):
    install_image("Ikea", "ikea.ota", make_ota_image(manuf_code=0x117C, image_type=0x0001))

    install_image("Philips", "hue.ota", make_ota_image(manuf_code=0x100B, image_type=0x0001))

    assert "ikea.ota" in ota.ListOfImages["Brands"]["Ikea"]
    assert "hue.ota" in ota.ListOfImages["Brands"]["Philips"]


def test_a_truncated_file_does_not_stop_the_scan(ota, install_image):
    install_image("Ikea", "good.ota", make_ota_image())

    install_image("Ikea", "truncated.ota", b"\x00" * 80 + make_ota_image()[:20])

    assert "good.ota" in ota.ListOfImages["Brands"]["Ikea"]
    assert "truncated.ota" not in ota.ListOfImages["Brands"]["Ikea"]


def test_retrieve_image_picks_the_requesting_manufacturer(ota_module, ota, install_image):
    install_image("Ikea", "ikea.ota", make_ota_image(manuf_code=0x117C, image_type=0x0001))
    install_image("Philips", "hue.ota", make_ota_image(manuf_code=0x100B, image_type=0x0001))

    assert ota_module.retrieve_image(ota, 0x0001, 0x117C) == ("Ikea", "ikea.ota")
    assert ota_module.retrieve_image(ota, 0x0001, 0x100B) == ("Philips", "hue.ota")
    # Several manufacturers use this type, none of them is the requester
    assert ota_module.retrieve_image(ota, 0x0001, 0x1021) is None


def test_retrieve_image_keeps_the_only_image_of_a_type(ota_module, ota, install_image):
    """Legacy: a single image of that type is still found for another manufacturer code
    (the Legrand 0x00C8 requests patched in initialize_block_request rely on it)."""
    install_image("Legrand", "nlv.ota", make_ota_image(manuf_code=0x1021, image_type=0x0013))

    assert ota_module.retrieve_image(ota, 0x0013, 0x00C8) == ("Legrand", "nlv.ota")
    assert ota_module.retrieve_image(ota, 0x0013, 0x00C8, exact=True) is None


def test_two_manufacturers_sharing_a_folder_keep_their_images(ota, install_image):
    """XIAOMI/ holds Xiaomi, devbis and z03mmc images: same image type, different manufacturers."""
    install_image("Xiaomi", "xiaomi.ota", make_ota_image(manuf_code=0x115F, image_type=0x0203, version=0x00000020))
    install_image("Xiaomi", "devbis.ota", make_ota_image(manuf_code=0xDB15, image_type=0x0203, version=0x00000030))

    assert {"xiaomi.ota", "devbis.ota"} <= set(ota.ListOfImages["Brands"]["Xiaomi"])


def test_retrieve_image(ota_module, ota, install_image):
    install_image("Ikea", "bulb.ota", make_ota_image(image_type=0x2203))

    assert ota_module.retrieve_image(ota, 0x2203) == ("Ikea", "bulb.ota")
    assert ota_module.retrieve_image(ota, 0x9999) is None
    assert ota_module.retrieve_image_in_a_brand(ota, 0x2203, "Ikea") == "bulb.ota"
    assert ota_module.retrieve_image_in_a_brand(ota, 0x2203, "Philips") is None
    assert ota_module.retrieve_image_in_a_brand(ota, 0x2203, "NoSuchBrand") is None


def test_restapi_list_of_firmware_splits_the_file_version(ota, install_image):
    """ZCL8 table 11-5: application release, application build, stack release, stack build."""
    install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=0x01020304))

    listing = ota.restapi_list_of_firmware()

    assert listing[0]["Ikea"] == [
        {
            "FileName": "bulb.ota",
            "ImageType": "2203",
            "ManufCode": "117c",
            "Version": "01020304",
            "ApplicationRelease": "01",
            "ApplicationBuild": "02",
            "StackRelease": "03",
            "StackBuild": "04",
        }
    ]
    assert listing[0]["Philips"] == []
