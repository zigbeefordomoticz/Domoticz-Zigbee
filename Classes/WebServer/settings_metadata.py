#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Presentation metadata of the plugin settings, as sent by GET /settings, and the
check of a numeric value received by PUT /settings.

A setting definition in Classes/PluginConf.py SETTINGS may carry, on top of
type / default / restart / hidden / Advanced:

    Group      card the setting belongs to, inside its section
    Unit       unit of a numeric value ("s", "h", "ds" = tenth of a second, "dBm")
    Min, Max   accepted range of a numeric value
    Step       increment the WebUI offers
    DependsOn  name of a bool setting; the WebUI hides this one while it is off
    Danger     the WebUI shows it in a folded warning card
    OneShot    the plugin switches it off once it has been applied

All of them are optional. A WebUI that does not know them ignores them.
"""

SETTING_METADATA_KEYS = ("Group", "Unit", "Min", "Max", "Step", "DependsOn", "Danger", "OneShot")

NUMERIC_TYPES = ("int", "float")


def setting_metadata(definition):
    """Return the optional presentation keys present in a SETTINGS definition."""
    return {key: definition[key] for key in SETTING_METADATA_KEYS if key in definition}


def check_numeric_setting(definition, value):
    """
    Convert a value received for an "int" or "float" setting and check its range.

    Returns (True, converted value) when it is acceptable, (False, reason) otherwise.
    Settings of any other type are returned unchanged. A WebUI that does not know
    the "float" type sends its value as text, hence the conversion.
    """
    data_type = definition.get("type")
    if data_type not in NUMERIC_TYPES or isinstance(value, bool):
        return True, value

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, f"{value!r} is not a number"

    if number != number or number in (float("inf"), float("-inf")):
        return False, f"{value!r} is not a number"

    if data_type == "int":
        if not number.is_integer():
            return False, f"{value!r} is not a whole number"
        number = int(number)

    minimum = definition.get("Min")
    maximum = definition.get("Max")
    if minimum is not None and number < minimum:
        return False, f"{number} is below the minimum {minimum}"
    if maximum is not None and number > maximum:
        return False, f"{number} is above the maximum {maximum}"

    return True, number
