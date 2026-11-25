#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Keep the Zigbee keys out of the logs.

Users post their logs on GitHub and on the forums, and whoever has the network key can read and
command the network.
"""

import re

MASKED_KEY = "**masked**"

# A 128 bits key as zigpy renders it (16 octets separated by colons), or as 32 hexadecimal digits.
# An IEEE address has 8 octets and is left alone.
_KEY_PATTERN = re.compile(
    r"(?<![0-9a-fA-F:])(?:[0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}(?![0-9a-fA-F:])"
    r"|(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])"
)


def mask_keys(value):
    """Return value as a string, with every 128 bits key masked."""
    return _KEY_PATTERN.sub(MASKED_KEY, str(value))
