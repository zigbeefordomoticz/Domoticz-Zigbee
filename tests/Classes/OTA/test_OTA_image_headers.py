"""
test_OTA_image_headers.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for reading Zigbee OTA files: _open_image_file,
offset_start_firmware, unpack_headers and ota_extract_image_headers.

Reference: Zigbee Cluster Library rev 8 (07-5123-08), 11.4.2 OTA Header
Format. Optional header fields follow the 56-byte base header, in this
order, when their Field Control bit (table 11-3) is set:

    bit 0  Security Credential Version   1 byte
    bit 1  Upgrade File Destination      8 bytes (IEEE)
    bit 2  Minimum / Maximum HW Version  2 + 2 bytes

zigpy's OTAImageHeader follows the same table and is used as a second
opinion where it is installed.

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25; they start passing (and must then lose the marker) once the
defect is fixed.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_image_headers.py -v
"""

import pytest
from ota_builders import make_ota_image


def _write(tmp_path, ota, name, data, folder="IKEA-TRADFRI"):
    directory = tmp_path / "OTAFirmware" / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(data)
    return folder


# ─── mandatory header ─────────────────────────────────────────────────────────

def test_mandatory_header_fields(ota_module, ota):
    image = make_ota_image(manuf_code=0x117C, image_type=0x2203, version=0x01020304, stack_version=0x0002)

    headers = ota_module.unpack_headers(ota, image)

    assert headers["file_id"] == 0x0BEEF11E
    assert headers["header_length"] == 56
    assert headers["manufacturer_code"] == 0x117C
    assert headers["image_type"] == 0x2203
    assert headers["image_version"] == 0x01020304
    assert headers["stack_version"] == 0x0002
    assert headers["header_str"] == "Z4D unit test image"
    assert headers["image_size"] == len(image)
    assert headers["payload_offset"] == 56
    assert headers["min_hw_version"] is None
    assert headers["max_hw_version"] is None
    assert headers["security_cred_version"] is None


def test_vendor_data_is_kept_and_payload_offset_skips_it(ota_module, ota):
    image = make_ota_image(vendor_data=b"\x01\x02\x03\x04")

    headers = ota_module.unpack_headers(ota, image)

    assert headers["header_length"] == 60
    assert headers["vendor_data"] == b"\x01\x02\x03\x04"
    assert headers["payload_offset"] == 60


def test_magic_not_found_raises(ota_module, ota):
    with pytest.raises(ValueError):
        ota_module.unpack_headers(ota, b"\x00" * 100)


# ─── optional header fields (ZCL8 11.4.2.4, table 11-3) ──────────────────────

def test_hardware_versions_are_read_from_bit_2(ota_module, ota):
    image = make_ota_image(field_control=0x04, min_hw=0x0102, max_hw=0x0304)

    headers = ota_module.unpack_headers(ota, image)

    assert headers["min_hw_version"] == 0x0102
    assert headers["max_hw_version"] == 0x0304
    assert headers["security_cred_version"] is None


def test_security_credential_version_is_read_from_bit_0(ota_module, ota):
    image = make_ota_image(field_control=0x01, security_credential=0x02)

    headers = ota_module.unpack_headers(ota, image)

    assert headers["security_cred_version"] == 0x02
    assert headers["min_hw_version"] is None


def test_all_optional_fields_in_spec_order(ota_module, ota):
    image = make_ota_image(field_control=0x07, security_credential=0x03, destination=0x00158D0000000001,
                           min_hw=0x0100, max_hw=0x02FF)

    headers = ota_module.unpack_headers(ota, image)

    assert headers["header_length"] == 56 + 1 + 8 + 4
    assert headers["security_cred_version"] == 0x03
    assert headers["upgrade_file_destination"] == 0x00158D0000000001
    assert (headers["min_hw_version"], headers["max_hw_version"]) == (0x0100, 0x02FF)


@pytest.mark.parametrize("field_control", [0x00, 0x01, 0x02, 0x04, 0x07])
def test_matches_zigpy_header_parser(ota_module, ota, field_control):
    zigpy_image = pytest.importorskip("zigpy.ota.image")
    image = make_ota_image(field_control=field_control, security_credential=0x02, destination=0x00158D0000000001,
                           min_hw=0x0102, max_hw=0x0304)

    ours = ota_module.unpack_headers(ota, image)
    theirs, _ = zigpy_image.OTAImageHeader.deserialize(image)

    assert ours["manufacturer_code"] == theirs.manufacturer_id
    assert ours["image_type"] == theirs.image_type
    assert ours["image_version"] == theirs.file_version
    assert ours["image_size"] == theirs.image_size
    assert ours["header_length"] == theirs.header_length
    assert ours["security_cred_version"] == theirs.security_credential_version
    assert ours["min_hw_version"] == (int(theirs.minimum_hardware_version) if theirs.minimum_hardware_version is not None else None)
    assert ours["max_hw_version"] == (int(theirs.maximum_hardware_version) if theirs.maximum_hardware_version is not None else None)


# ─── locating the header inside a wrapped file ────────────────────────────────

def test_offset_start_firmware_finds_magic_after_a_prefix(ota_module, ota):
    image = make_ota_image(prefix=b"\x55" * 37)

    assert ota_module.offset_start_firmware(ota, image) == 37


def test_offset_start_firmware_without_magic(ota_module, ota):
    assert ota_module.offset_start_firmware(ota, b"\x00" * 200) is None


def test_extract_headers_trims_the_wrapper(ota_module, ota, tmp_path):
    image = make_ota_image(prefix=b"\x55" * 37)
    folder = _write(tmp_path, ota, "wrapped.ota", image)

    image_type, headers, ota_image = ota_module.ota_extract_image_headers(ota, folder, "wrapped.ota")

    assert image_type == 0x2203
    assert headers["image_version"] == 0x01020304
    assert ota_image == image[37:]
    assert len(ota_image) == headers["image_size"]


def test_extract_headers_of_a_file_without_magic(ota_module, ota, tmp_path):
    folder = _write(tmp_path, ota, "garbage.bin", b"\x00" * 200)

    assert ota_module.ota_extract_image_headers(ota, folder, "garbage.bin") is None


def test_extract_headers_of_a_truncated_header(ota_module, ota, tmp_path):
    # 80 bytes of padding, then the first 20 bytes of a header: the magic is found
    # but the 56-byte base header does not fit.
    data = b"\x00" * 80 + make_ota_image()[:20]
    folder = _write(tmp_path, ota, "truncated.ota", data)

    assert ota_module.ota_extract_image_headers(ota, folder, "truncated.ota") is None
    error = next(call for call in ota.log.logging.call_args_list if call.args[1] == "Error")
    assert error.args[4]["Error code"] == "OTA0004"
    assert error.args[4]["File"] == "truncated.ota"


def test_open_image_file_rejects_short_and_missing_files(ota_module, ota, tmp_path):
    short = tmp_path / "short.ota"
    short.write_bytes(b"\x1e\xf1\xee\x0b" + b"\x00" * 60)

    assert ota_module._open_image_file(ota, short) is None
    assert ota_module._open_image_file(ota, tmp_path / "missing.ota") is None
