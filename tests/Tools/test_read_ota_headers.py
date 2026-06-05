#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tools/read_ota_headers.py

Coverage:
  - find_header_offset   – found at start, found mid-file, not found
  - parse_vendor_tlv     – valid TLV, malformed TLV truncation, empty
  - unpack_headers       – minimal valid header, optional fields (hw version, upgrade dest, sec cred),
                           vendor data, unknown manufacturer code
  - hexdump              – basic formatting
  - VENDOR_MAP           – spot-checks known codes
"""

import importlib.util
import struct
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "Tools" / "read_ota_headers.py"

spec = importlib.util.spec_from_file_location("read_ota_headers", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

find_header_offset = mod.find_header_offset
parse_vendor_tlv   = mod.parse_vendor_tlv
unpack_headers     = mod.unpack_headers
hexdump            = mod.hexdump
VENDOR_MAP         = mod.VENDOR_MAP
FILE_IDENTIFIER    = mod.FILE_IDENTIFIER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_ota_blob(
    manufacturer_code=0x1185,
    image_type=0x0000,
    file_version=0x00000001,
    stack_version=0x0002,
    header_string=b"Test OTA Header\x00",
    image_size=None,
    field_ctrl=0,
    extra_optional=b"",
    vendor_data=b"",
    payload=b"\xAB" * 64,
    prefix=b"",
):
    """Build a minimal valid OTA firmware blob."""
    header_string_padded = header_string[:32].ljust(32, b"\x00")

    # header_length = base (56) + optional + vendor_data
    base_size = struct.calcsize("<L H H H H H L H 32s L")  # 56
    header_length = base_size + len(extra_optional) + len(vendor_data)

    total_image_size = header_length + len(payload)
    if image_size is None:
        image_size = total_image_size

    header = struct.pack(
        "<L H H H H H L H 32s L",
        FILE_IDENTIFIER,  # file_id
        0x0100,           # header_version
        header_length,
        field_ctrl,
        manufacturer_code,
        image_type,
        file_version,
        stack_version,
        header_string_padded,
        image_size,
    )
    return prefix + header + extra_optional + vendor_data + payload


# ---------------------------------------------------------------------------
# find_header_offset
# ---------------------------------------------------------------------------

class TestFindHeaderOffset:
    def test_found_at_start(self):
        data = struct.pack("<I", FILE_IDENTIFIER) + b"\x00" * 100
        assert find_header_offset(data) == 0

    def test_found_mid_file(self):
        data = b"\xFF" * 16 + struct.pack("<I", FILE_IDENTIFIER) + b"\x00" * 100
        assert find_header_offset(data) == 16

    def test_not_found_returns_none(self):
        assert find_header_offset(b"\x00" * 64) is None


# ---------------------------------------------------------------------------
# parse_vendor_tlv
# ---------------------------------------------------------------------------

class TestParseVendorTlv:
    def test_empty_input(self):
        assert parse_vendor_tlv(b"") == []

    def test_single_tlv(self):
        tlv = bytes([0x01, 0x03, 0xAA, 0xBB, 0xCC])
        result = parse_vendor_tlv(tlv)
        assert len(result) == 1
        assert result[0] == (0x01, 3, bytes([0xAA, 0xBB, 0xCC]))

    def test_multiple_tlv(self):
        tlv = bytes([0x01, 0x02, 0x11, 0x22, 0x02, 0x01, 0xFF])
        result = parse_vendor_tlv(tlv)
        assert len(result) == 2

    def test_malformed_truncated(self):
        # length says 10 bytes but only 2 remain → stops early
        tlv = bytes([0x01, 0x0A, 0x11, 0x22])
        result = parse_vendor_tlv(tlv)
        assert result == []


# ---------------------------------------------------------------------------
# unpack_headers
# ---------------------------------------------------------------------------

class TestUnpackHeaders:
    def test_minimal_header_parsed(self):
        blob = _build_ota_blob(manufacturer_code=0x1185)
        h = unpack_headers(blob)
        assert h["file_id"] == FILE_IDENTIFIER
        assert h["manufacturer_code"] == 0x1185
        assert h["vendor_name"] == "IKEA"

    def test_unknown_manufacturer_unknown(self):
        blob = _build_ota_blob(manufacturer_code=0xDEAD)
        h = unpack_headers(blob)
        assert h["vendor_name"] == "Unknown"

    def test_header_not_found_raises(self):
        with pytest.raises(ValueError, match="OTA header ID"):
            unpack_headers(b"\x00" * 128)

    def test_hardware_version_optional_field(self):
        extra = struct.pack("<H H", 0x0001, 0x00FF)  # min/max hw version
        blob = _build_ota_blob(field_ctrl=0x01, extra_optional=extra)
        h = unpack_headers(blob)
        assert h["min_hw_version"] == 0x0001
        assert h["max_hw_version"] == 0x00FF

    def test_upgrade_destination_optional_field(self):
        dest = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        blob = _build_ota_blob(field_ctrl=0x02, extra_optional=dest)
        h = unpack_headers(blob)
        assert h["upgrade_file_destination"] == dest.hex()

    def test_security_cred_optional_field(self):
        extra = bytes([0x03])
        blob = _build_ota_blob(field_ctrl=0x04, extra_optional=extra)
        h = unpack_headers(blob)
        assert h["security_cred_version"] == 0x03

    def test_vendor_data_present(self):
        vendor = bytes([0x01, 0x02, 0xAA, 0xBB])
        blob = _build_ota_blob(vendor_data=vendor)
        h = unpack_headers(blob)
        assert h["vendor_data_length"] == len(vendor)
        assert h["vendor_data"] == vendor

    def test_header_with_prefix_bytes(self):
        blob = _build_ota_blob(prefix=b"\xFF" * 32)
        h = unpack_headers(blob)
        assert h["file_id"] == FILE_IDENTIFIER

    def test_payload_offset_points_past_header(self):
        blob = _build_ota_blob()
        h = unpack_headers(blob)
        # payload_offset must be beyond the mandatory header (56 bytes)
        assert h["payload_offset"] >= 56

    def test_image_version_stored(self):
        blob = _build_ota_blob(file_version=0xDEADBEEF)
        h = unpack_headers(blob)
        assert h["image_version"] == 0xDEADBEEF


# ---------------------------------------------------------------------------
# hexdump
# ---------------------------------------------------------------------------

class TestHexdump:
    def test_single_line(self):
        result = hexdump(bytes(range(4)))
        assert "00 01 02 03" in result

    def test_multiline(self):
        result = hexdump(bytes(range(32)), width=16)
        lines = result.strip().splitlines()
        assert len(lines) == 2

    def test_offset_labels(self):
        result = hexdump(bytes(32), width=16)
        assert "0000:" in result
        assert "0010:" in result


# ---------------------------------------------------------------------------
# VENDOR_MAP spot-checks
# ---------------------------------------------------------------------------

class TestVendorMap:
    @pytest.mark.parametrize("code,name", [
        (0x1185, "IKEA"),
        (0x100B, "PHILIPS"),
        (0x1021, "Legrand"),
        (0x115F, "XIAOMI"),
        (0x110C, "OSRAM"),
    ])
    def test_known_vendor(self, code, name):
        assert VENDOR_MAP[code] == name
