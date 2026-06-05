#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_fcf.py

Coverage:
  - decode_fcf                   – frame type, manufacturer specific, direction, disable default response
  - fcf_direction                – client→server, server→client, invalid input
  - disable_default_response     – bit set, bit clear
  - is_direction_to_client       – True/False
  - is_direction_to_server       – True/False
  - is_globalcommand             – global (bits 00), cluster-specific (bits 01), invalid
  - frame_type                   – bits 00, 01, 10, 11
  - is_manufspecific_8002_payload – bit set, bit clear
  - build_fcf                    – round-trip with decode_fcf
  - retreive_cmd_payload_from_8002 – non-manuf-specific, manuf-specific, short payload
  - extract_info_from_8085       – full data, partial data
"""

import pytest
from Modules.tools_fcf import (
    build_fcf,
    decode_fcf,
    disable_default_response,
    extract_info_from_8085,
    fcf_direction,
    frame_type,
    is_direction_to_client,
    is_direction_to_server,
    is_globalcommand,
    is_manufspecific_8002_payload,
    retreive_cmd_payload_from_8002,
)


# ---------------------------------------------------------------------------
# decode_fcf
# ---------------------------------------------------------------------------

class TestDecodeFcf:
    def test_profile_wide_client_to_server(self):
        # 0x00 → frame type 0 (Profile-wide), no manuf, dir 0, no disable
        result = decode_fcf("00")
        assert result["Frame Type"] == "Profile-wide"
        assert result["Manufacturer Specific"] is False
        assert result["Direction"] == "Client→Server"
        assert result["Disable Default Response"] is False

    def test_cluster_specific(self):
        # bits 0-1 = 01 → Cluster-specific
        result = decode_fcf("01")
        assert result["Frame Type"] == "Cluster-specific"

    def test_manufacturer_specific_bit(self):
        # bit 2 set → 0x04
        result = decode_fcf("04")
        assert result["Manufacturer Specific"] is True

    def test_direction_server_to_client(self):
        # bit 3 set → 0x08
        result = decode_fcf("08")
        assert result["Direction"] == "Server→Client"

    def test_disable_default_response(self):
        # bit 4 set → 0x10
        result = decode_fcf("10")
        assert result["Disable Default Response"] is True


# ---------------------------------------------------------------------------
# fcf_direction
# ---------------------------------------------------------------------------

class TestFcfDirection:
    def test_client_to_server(self):
        assert fcf_direction("00") == 0

    def test_server_to_client(self):
        # bit 3 set
        assert fcf_direction("08") == 1

    def test_invalid_returns_none(self):
        assert fcf_direction("zz") is None

    def test_wrong_length_returns_none(self):
        assert fcf_direction("0") is None


# ---------------------------------------------------------------------------
# disable_default_response
# ---------------------------------------------------------------------------

class TestDisableDefaultResponse:
    def test_bit_clear(self):
        assert disable_default_response("00") == 0

    def test_bit_set(self):
        assert disable_default_response("10") == 1

    def test_other_bits_ignored(self):
        # 0x0F → bit 4 is 0
        assert disable_default_response("0f") == 0


# ---------------------------------------------------------------------------
# is_direction_to_client / is_direction_to_server
# ---------------------------------------------------------------------------

class TestDirectionHelpers:
    def test_to_client_when_bit3_set(self):
        assert is_direction_to_client("08") is True
        assert is_direction_to_server("08") is False

    def test_to_server_when_bit3_clear(self):
        assert is_direction_to_server("00") is True
        assert is_direction_to_client("00") is False


# ---------------------------------------------------------------------------
# is_globalcommand
# ---------------------------------------------------------------------------

class TestIsGlobalCommand:
    def test_global_command(self):
        assert is_globalcommand("00") is True

    def test_cluster_specific_not_global(self):
        assert is_globalcommand("01") is False

    def test_invalid_returns_none(self):
        assert is_globalcommand("xx") is None

    def test_wrong_length_returns_none(self):
        assert is_globalcommand("0") is None


# ---------------------------------------------------------------------------
# frame_type
# ---------------------------------------------------------------------------

class TestFrameType:
    def test_profile_wide(self):
        assert frame_type("00") == 0

    def test_cluster_specific(self):
        assert frame_type("01") == 1

    def test_reserved_2(self):
        assert frame_type("02") == 2

    def test_reserved_3(self):
        assert frame_type("03") == 3

    def test_other_bits_masked(self):
        # 0xFC → bits 0-1 are 00
        assert frame_type("fc") == 0


# ---------------------------------------------------------------------------
# is_manufspecific_8002_payload
# ---------------------------------------------------------------------------

class TestIsManufSpecific:
    def test_bit_clear(self):
        assert is_manufspecific_8002_payload("00") is False

    def test_bit_set(self):
        # bit 2 set → 0x04
        assert is_manufspecific_8002_payload("04") is True

    def test_other_bits_do_not_affect(self):
        # 0x03 → bit 2 clear
        assert is_manufspecific_8002_payload("03") is False


# ---------------------------------------------------------------------------
# build_fcf
# ---------------------------------------------------------------------------

class TestBuildFcf:
    def test_all_zeros(self):
        assert build_fcf("0", "0", "0", "0") == "00"

    def test_cluster_specific(self):
        result = build_fcf("1", "0", "0", "0")
        assert frame_type(result) == 1

    def test_direction_set(self):
        result = build_fcf("0", "0", "1", "0")
        assert is_direction_to_client(result) is True

    def test_disable_default_response_set(self):
        result = build_fcf("0", "0", "0", "1")
        assert disable_default_response(result) == 1

    def test_manuf_specific_set(self):
        result = build_fcf("0", "1", "0", "0")
        assert is_manufspecific_8002_payload(result) is True

    def test_round_trip(self):
        original = "19"  # 0b00011001 → cluster-specific, manuf, dir client→server, disable
        rebuilt = build_fcf(
            "%x" % (int(original, 16) & 0x03),
            "%x" % ((int(original, 16) >> 2) & 0x01),
            "%x" % ((int(original, 16) >> 3) & 0x01),
            "%x" % ((int(original, 16) >> 4) & 0x01),
        )
        assert rebuilt == original


# ---------------------------------------------------------------------------
# retreive_cmd_payload_from_8002
# ---------------------------------------------------------------------------

class TestRetrieveCmdPayload:
    def test_short_payload_returns_nones(self):
        result = retreive_cmd_payload_from_8002("00")
        assert result == (None, None, None, None, None, None)

    def test_too_short_for_command(self):
        result = retreive_cmd_payload_from_8002("0001")
        assert result == (None, None, None, None, None, None)

    def test_non_manuf_specific(self):
        # FCF=00 (global, no manuf), SQN=01, Cmd=0a, Data=1122
        payload = "00" + "01" + "0a" + "1122"
        ddr, global_cmd, sqn, manuf, cmd, data = retreive_cmd_payload_from_8002(payload)
        assert global_cmd is True
        assert manuf is None
        assert sqn == "01"
        assert cmd == "0a"
        assert data == "1122"

    def test_manuf_specific(self):
        # FCF=04 (manuf specific), manuf=1234 (stored as 3412 in payload bytes [2:6]), SQN=ff, Cmd=05, Data=aabb
        # Manuf bytes in payload: [2:4]=34, [4:6]=12 → reconstructed as 1234
        payload = "04" + "34" + "12" + "ff" + "05" + "aabb"
        ddr, global_cmd, sqn, manuf, cmd, data = retreive_cmd_payload_from_8002(payload)
        assert manuf == "1234"
        assert sqn == "ff"
        assert cmd == "05"
        assert data == "aabb"

    def test_invalid_fcf_returns_nones(self):
        result = retreive_cmd_payload_from_8002("zz0102030405")
        assert result == (None, None, None, None, None, None)


# ---------------------------------------------------------------------------
# extract_info_from_8085
# ---------------------------------------------------------------------------

class TestExtractInfoFrom8085:
    def _pad(self, data, length):
        return data.ljust(length, "0")

    def test_full_data(self):
        # MsgData needs at least 22 chars; indices 14-21
        msg = self._pad("00000000000000" + "01" + "02" + "03" + "04", 22)
        step_mod, up_down, step_size, transition = extract_info_from_8085(msg)
        assert step_mod == "01"
        assert up_down == "02"
        assert step_size == "03"
        assert transition == "04"

    def test_partial_data_returns_none(self):
        # Only 16 chars → up_down present but step_size and transition absent
        msg = self._pad("00000000000000" + "01" + "02", 16)
        step_mod, up_down, step_size, transition = extract_info_from_8085(msg)
        assert step_mod == "01"
        assert up_down == "02"
        assert step_size is None
        assert transition is None

    def test_very_short_data(self):
        msg = "00000000000000aa"  # exactly 16 chars
        step_mod, up_down, step_size, transition = extract_info_from_8085(msg)
        assert step_mod == "aa"
        assert step_size is None
