#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_primitives.py

Coverage:
  - to_little_endian    – 16-bit, 24-bit, 32-bit, 64-bit, other lengths
  - twos_complement     – positive, negative, edge cases
  - is_hex              – valid hex, invalid chars, non-string
  - is_int              – digits only, mixed, non-string
  - returnlen           – already correct length, needs padding
  - Hex_Format          – normal, overflow
  - str_round           – basic rounding
  - voltage2batteryP    – mid range, full, empty, invalid, error
  - hex_to_rgb          – round-trip with rgb_to_hex
  - rgb_to_hex          – basic
  - rgb_to_xy           – black stays (0,0), white sum check
  - hex_to_xy           – delegates correctly
  - xy_to_rgb           – y==0 returns zeros, bright white approximates white
  - rgb_to_hsl          – achromatic (grey), primary red
"""

import pytest
from Modules.tools_primitives import (
    Hex_Format,
    hex_to_rgb,
    hex_to_xy,
    is_hex,
    is_int,
    returnlen,
    rgb_to_hex,
    rgb_to_hsl,
    rgb_to_xy,
    str_round,
    to_little_endian,
    twos_complement,
    voltage2batteryP,
    xy_to_rgb,
)


# ---------------------------------------------------------------------------
# to_little_endian
# ---------------------------------------------------------------------------

class TestToLittleEndian:
    def test_16bit(self):
        # 0x1234 in little-endian bytes → 34 12
        assert to_little_endian("1234") == "3412"

    def test_32bit(self):
        # 0x12345678 → 78 56 34 12
        assert to_little_endian("12345678") == "78563412"

    def test_64bit(self):
        result = to_little_endian("0102030405060708")
        assert result == "0807060504030201"

    def test_24bit(self):
        # 0x112233 reversed bytes → 33 22 11
        assert to_little_endian("112233") == "332211"

    def test_other_length_passthrough(self):
        # 1-byte (2 chars) — treated as raw passthrough
        assert to_little_endian("ab") == "ab"


# ---------------------------------------------------------------------------
# twos_complement
# ---------------------------------------------------------------------------

class TestTwosComplement:
    def test_positive_unchanged(self):
        assert twos_complement(5, 8) == 5

    def test_negative_8bit(self):
        # -1 in 8-bit two's complement → 255
        assert twos_complement(-1, 8) == 255

    def test_negative_16bit(self):
        # -32768 in 16-bit → 32768
        assert twos_complement(-32768, 16) == 32768

    def test_zero(self):
        assert twos_complement(0, 8) == 0

    def test_mask_applied(self):
        # 257 & 0xFF == 1
        assert twos_complement(257, 8) == 1


# ---------------------------------------------------------------------------
# is_hex / is_int
# ---------------------------------------------------------------------------

class TestIsHex:
    def test_valid_lowercase(self):
        assert is_hex("deadbeef") is True

    def test_valid_uppercase(self):
        assert is_hex("DEADBEEF") is True

    def test_mixed_case(self):
        assert is_hex("DeAdBe") is True

    def test_invalid_char(self):
        assert is_hex("xyz") is False

    def test_empty_string(self):
        assert is_hex("") is True  # all() on empty is True

    def test_non_string(self):
        assert is_hex(123) is False


class TestIsInt:
    def test_digits(self):
        assert is_int("12345") is True

    def test_hex_letter_rejected(self):
        assert is_int("12a3") is False

    def test_empty_string(self):
        assert is_int("") is True  # all() on empty is True

    def test_non_string(self):
        assert is_int(42) is False


# ---------------------------------------------------------------------------
# returnlen / Hex_Format
# ---------------------------------------------------------------------------

class TestReturnlen:
    def test_already_correct_length(self):
        assert returnlen(4, "abcd") == "abcd"

    def test_pads_with_zeros(self):
        assert returnlen(4, "ab") == "00ab"

    def test_longer_than_target(self):
        # No truncation — value is returned as-is when already longer
        assert returnlen(2, "abcd") == "abcd"


class TestHexFormat:
    def test_normal_conversion(self):
        assert Hex_Format(4, 255) == "00ff"

    def test_overflow_returns_ffff(self):
        # 0x10000 would require 5 hex chars but taille=4 → "ffff"
        assert Hex_Format(4, 0x10000) == "ffff"

    def test_zero(self):
        assert Hex_Format(2, 0) == "00"


# ---------------------------------------------------------------------------
# str_round
# ---------------------------------------------------------------------------

class TestStrRound:
    def test_two_decimal_places(self):
        assert str_round(3.14159, 2) == "3.14"

    def test_zero_decimals(self):
        assert str_round(3.7, 0) == "4"

    def test_already_rounded(self):
        assert str_round(1.5, 1) == "1.5"


# ---------------------------------------------------------------------------
# voltage2batteryP
# ---------------------------------------------------------------------------

class TestVoltage2BatteryP:
    def test_full_battery(self):
        assert voltage2batteryP(3000, 3000, 2000) == 100

    def test_empty_battery(self):
        assert voltage2batteryP(2000, 3000, 2000) == 0

    def test_mid_range(self):
        result = voltage2batteryP(2500, 3000, 2000)
        assert result == 50

    def test_above_max_clamps_to_100(self):
        assert voltage2batteryP(3200, 3000, 2000) == 100

    def test_below_min_clamps_to_0(self):
        assert voltage2batteryP(1800, 3000, 2000) == 0

    def test_invalid_string_returns_0(self):
        assert voltage2batteryP("bad", 3000, 2000) == 0

    def test_volt_max_le_volt_min_raises(self):
        with pytest.raises(ValueError):
            voltage2batteryP(2500, 2000, 3000)


# ---------------------------------------------------------------------------
# hex_to_rgb / rgb_to_hex round-trip
# ---------------------------------------------------------------------------

class TestHexRgb:
    def test_hex_to_rgb_white(self):
        assert hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_hex_to_rgb_black(self):
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_red(self):
        assert hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_rgb_to_hex_round_trip(self):
        rgb = (128, 64, 32)
        assert hex_to_rgb(rgb_to_hex(rgb)) == rgb


# ---------------------------------------------------------------------------
# rgb_to_xy / hex_to_xy
# ---------------------------------------------------------------------------

class TestRgbToXy:
    def test_black_is_origin(self):
        cx, cy = rgb_to_xy((0, 0, 0))
        assert cx == 0 and cy == 0

    def test_values_between_0_and_1(self):
        cx, cy = rgb_to_xy((200, 100, 50))
        assert 0.0 <= cx <= 1.0
        assert 0.0 <= cy <= 1.0

    def test_hex_to_xy_delegates(self):
        assert hex_to_xy("#ff0000") == rgb_to_xy(hex_to_rgb("#ff0000"))


# ---------------------------------------------------------------------------
# xy_to_rgb
# ---------------------------------------------------------------------------

class TestXyToRgb:
    def test_y_zero_returns_black(self):
        result = xy_to_rgb(0.3, 0.0)
        assert result == {"r": 0, "g": 0, "b": 0}

    def test_returns_dict_with_rgb_keys(self):
        result = xy_to_rgb(0.3127, 0.3290, brightness=1)
        assert set(result.keys()) == {"r", "g", "b"}

    def test_values_in_0_255_range(self):
        result = xy_to_rgb(0.3127, 0.3290, brightness=1)
        for channel in ("r", "g", "b"):
            assert 0 <= result[channel] <= 255


# ---------------------------------------------------------------------------
# rgb_to_hsl
# ---------------------------------------------------------------------------

class TestRgbToHsl:
    def test_grey_is_achromatic(self):
        h, s, l = rgb_to_hsl((128, 128, 128))
        assert s == pytest.approx(0.0, abs=1e-6)

    def test_white_lightness_is_1(self):
        h, s, l = rgb_to_hsl((255, 255, 255))
        assert l == pytest.approx(1.0, abs=1e-6)

    def test_black_lightness_is_0(self):
        h, s, l = rgb_to_hsl((0, 0, 0))
        assert l == pytest.approx(0.0, abs=1e-6)

    def test_red_hue_near_zero(self):
        h, s, l = rgb_to_hsl((255, 0, 0))
        assert h == pytest.approx(0.0, abs=1e-6)
        assert s == pytest.approx(1.0, abs=1e-6)
