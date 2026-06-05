#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# SPDX-License-Identifier:    GPL-3.0 license

import string
import struct


HEX_DIGIT = string.hexdigits  # '0123456789abcdefABCDEF'
INT_DIGIT = string.digits     # '0123456789'


def to_little_endian(value: str) -> str:
    """
    Converts a hexadecimal string to little endian format, depending on its length.

    Args:
        value (str): A hex string (e.g., "1234", "123456", "12345678", "1234567890abcdef").

    Returns:
        str: The hex string in little endian byte order.
    """

    value = value.lower()
    length = len(value)

    if length == 4:  # 16-bit (2 bytes)
        return struct.pack("<H", int(value, 16)).hex()

    if length == 6:  # 24-bit (3 bytes)
        return bytes.fromhex(value)[::-1].hex()  # Reverse byte order manually

    if length == 8:  # 32-bit (4 bytes)
        return struct.pack("<I", int(value, 16)).hex()

    if length == 16:  # 64-bit (8 bytes)
        return struct.pack("<Q", int(value, 16)).hex()

    # Treat as raw bytes (possibly 8-bit)
    return value  # Assuming `value` is already hex


def twos_complement(value: int, bits: int) -> int:
    """
    Convert a signed integer to its two's complement representation as an integer.

    :param value: The signed integer to convert.
    :param bits: The number of bits to use in the representation.
    :return: The two's complement integer.
    """
    if value < 0:
        value = (1 << bits) + value  # Compute two's complement
    return value & ((1 << bits) - 1)


def is_hex(s):
    """Checks if a string contains only hexadecimal characters."""
    return isinstance(s, str) and all(char in HEX_DIGIT for char in s)


def is_int(s):
    """Checks if a string contains only decimal digits."""
    return isinstance(s, str) and all(char in INT_DIGIT for char in s)


def returnlen(taille, value):
    """Pads the string `value` with leading zeroes until it reaches `taille` length."""
    while len(value) < taille:
        value = "0" + value
    return str(value)


def Hex_Format(taille, value):
    """
    Converts an integer to a hex string padded to `taille` length.
    If the result exceeds `taille`, returns a string of 'f' * `taille`.
    """
    value = hex(int(value))[2:]
    if len(value) > taille:
        return "f" * taille
    while len(value) < taille:
        value = "0" + value
    return str(value)


def str_round(value, n):
    """Rounds a float to `n` decimal places and returns it as a string."""
    return "{:.{n}f}".format(value, n=int(n))


def voltage2batteryP(voltage, volt_max, volt_min):
    """
    Converts a voltage reading to a battery percentage.

    Args:
        voltage (int or str): The measured voltage (e.g., 2900).
        volt_max (int): The voltage considered 100% battery (e.g., 3000).
        volt_min (int): The voltage considered 0% battery (e.g., 2100).

    Returns:
        int: Battery percentage in the range [0, 100].
    """
    try:
        voltage = int(voltage)
    except (ValueError, TypeError):
        return 0

    if volt_max <= volt_min:
        raise ValueError("volt_max must be greater than volt_min")

    if voltage >= volt_max:
        return 100

    if voltage <= volt_min:
        return 0

    percent = 100 * (voltage - volt_min) / (volt_max - volt_min)
    return round(percent)


def hex_to_rgb(value):
    """Return (red, green, blue) for the color given as #rrggbb."""
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


def hex_to_xy(h):
    """ convert hex color to xy tuple """
    return rgb_to_xy(hex_to_rgb(h))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def rgb_to_xy(rgb):
    """ convert rgb tuple to xy tuple """
    red, green, blue = rgb
    r = ((red + 0.055) / (1.0 + 0.055)) ** 2.4 if (red > 0.04045) else (red / 12.92)
    g = ((green + 0.055) / (1.0 + 0.055)) ** 2.4 if (green > 0.04045) else (green / 12.92)
    b = ((blue + 0.055) / (1.0 + 0.055)) ** 2.4 if (blue > 0.04045) else (blue / 12.92)
    X = r * 0.664511 + g * 0.154324 + b * 0.162028
    Y = r * 0.283881 + g * 0.668433 + b * 0.047685
    Z = r * 0.000088 + g * 0.072310 + b * 0.986039
    cx = 0
    cy = 0
    if (X + Y + Z) != 0:
        cx = X / (X + Y + Z)
        cy = Y / (X + Y + Z)
    return (cx, cy)


def xy_to_rgb(x, y, brightness=1):
    """
    Convert CIE 1931 xy chromaticity coordinates to RGB values.

    This function converts color values from the CIE 1931 color space (x, y)
    into standard sRGB values, applying a brightness scaling factor and
    gamma correction.

    The conversion follows a standard matrix transformation from XYZ to RGB,
    followed by sRGB gamma correction.

    Args:
        x (float): The x chromaticity coordinate (0.0 - 1.0).
        y (float): The y chromaticity coordinate (0.0 - 1.0).
        brightness (float, optional): Brightness scaling factor applied to Y.
            Typically ranges from 0.0 (off) to 1.0 (full brightness).
            Defaults to 1.

    Returns:
        dict: A dictionary containing RGB values scaled to 0-255 range:
            {
                "r": float,  # Red channel
                "g": float,  # Green channel
                "b": float   # Blue channel
            }

    Notes:
        - If y is zero, the function may be undefined; behavior should be
          handled by the caller.
        - Values may temporarily fall outside the [0, 1] range during
          conversion and are expected to be clamped externally if needed.
        - Output is gamma-corrected to sRGB standard.

    Example:
        >>> xy_to_rgb(0.5, 0.4, brightness=0.8)
        {'r': 123.45, 'g': 200.12, 'b': 98.76}
    """
    x = float(x)
    y = float(y)

    if y == 0:
        return {"r": 0, "g": 0, "b": 0}

    z = 1.0 - x - y

    Y = brightness
    X = (Y / y) * x
    Z = (Y / y) * z

    # Convert to linear RGB
    r = X * 1.656492 - Y * 0.354851 - Z * 0.255038
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    b = X * 0.051713 - Y * 0.121364 + Z * 1.011530

    def gamma_correct(c):
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055

    r = gamma_correct(r)
    g = gamma_correct(g)
    b = gamma_correct(b)

    # Clamp to [0, 1]
    r = max(0, min(r, 1))
    g = max(0, min(g, 1))
    b = max(0, min(b, 1))

    return {
        "r": round(r * 255, 3),
        "g": round(g * 255, 3),
        "b": round(b * 255, 3),
    }

def rgb_to_hsl(rgb):
    """ convert rgb tuple to hls tuple """
    r, g, b = rgb
    r = float(r / 255)
    g = float(g / 255)
    b = float(b / 255)
    high = max(r, g, b)
    low = min(r, g, b)
    var_h, var_s, var_l = ((high + low) / 2,) * 3

    if high == low:
        var_h = 0.0
        var_s = 0.0
    else:
        d = high - low
        var_s = d / (2 - high - low) if var_l > 0.5 else d / (high + low)
        var_h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        var_h /= 6

    return var_h, var_s, var_l