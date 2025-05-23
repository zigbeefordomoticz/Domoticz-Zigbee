#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
    Module: manufacturer_code.py
 
    Description: 

"""

import Modules.tools


MANUFACTURER_NAME_TO_CODE = {
    "EMBER": "1002",
    "PHILIPS": "100b",
    "frient A/S": "1015",
    "LEGRAND": "1021",
    "VANTAGE": "1021",
    "LUMI": "1037",
    "SCHNEIDER ELECTRIC": "105e",
    "COMPUTIME": "1078",
    "PROFALUX": "1110",
    "DANALOCK": "115c",
    "OSRAM": "110c",
    "OWON": "113c",
    "XIAOMI": "115f",
    "INNR": "1166",
    "IKEA OF SWEDEN": "117c",
    "LEDVANCE": "1189",
    "HEIMAN": "120b",
    "DANFOSS": "1246",
    "KONKE": "1268",
    "OSRAM-2": "bbaa",
    "Develco": "1015",
}

TUYA_PREFIX = (
    "_TZ",
    "_TY",
)
TUYA_MANUF_CODE= [ '1002', '1141' ]

# Tuya devices Mac Address with a specific prefix
PREFIX_MAC_LEN = 6
PREFIX_MACADDR_IKEA_TRADFRI = ( "000d6f", "14b457")
PREFIX_MACADDR_DEVELCO = ( "0015bc", )
PREFIX_MACADDR_TUYA = ( 
    "04cd15",
    "588e81",
    "60a423",
    "70ac08",
    "842e14",
    "847127",
    "84fd27",
    "a4c138",
    "4c97a1",  # Found on a Tuya device _TZE200_lvkk0hdg @nico21311
    "b4e3f9",
    "bc33ac",
    )
PREFIX_MACADDR_LEGRAND = ( "000474", )
PREFIX_MACADDR_PROFALUX = ( "20918a", )
PREFIX_MACADDR_WIZER_LEGACY = ( "00124b", )
PREFIX_MACADDR_WIZER_HOME = ( "588E81", )
PREFIX_MACADDR_LIVOLO = ( "00124b", )
PREFIX_MACADDR_XIAOMI = ( "00158d", )  # Seems to be also INR
PREFIX_MACADDR_OPPLE = ( "04cf8c", )
PREFIX_MACADDR_CASAIA = ( "90fd9f", "3c6a2c")


def check_and_update_manufcode(self):
    """
    Validates and updates the 'Manufacturer' code for each device in self.ListOfDevices.

    For each device:
    - If the 'Manufacturer Name' matches a known entry in MANUFACTURER_NAME_TO_CODE,
      update the 'Manufacturer' field to the corresponding code if it's different.
    - If the device appears to be a Tuya device (based on the prefix of the name)
      and its current 'Manufacturer' code is not recognized as a Tuya code,
      set its 'Manufacturer' code to the default Tuya code '1002'.

    Assumptions:
    - self.ListOfDevices is a dictionary keyed by network IDs (nwkid), each value being
      a dictionary containing at least the keys 'Manufacturer Name' and 'Manufacturer'.
    - MANUFACTURER_NAME_TO_CODE is a dict mapping uppercased manufacturer names to codes.
    - TUYA_PREFIX is a list or set of string prefixes indicating Tuya manufacturers.
    - TUYA_MANUF_CODE is a list or set of valid Tuya manufacturer codes.
    """
    for nwkid, device in self.ListOfDevices.items():
        manuf_name = device.get("Manufacturer Name")
        if not manuf_name:
            continue

        upper_name = str(manuf_name).upper()
        if upper_name in MANUFACTURER_NAME_TO_CODE:
            correct_code = MANUFACTURER_NAME_TO_CODE[upper_name]
            if device.get("Manufacturer") != correct_code:
                device["Manufacturer"] = correct_code

        elif manuf_name[:3] in TUYA_PREFIX:
            # Tuya devices
            if device.get("Manufacturer") not in TUYA_MANUF_CODE:
                device["Manufacturer"] = "1002"


def is_tuya_magic_packet_required(self, device_model, device_ieee):
    """
    Determines whether a Tuya 'magic packet' is required for the given device.

    A magic packet is considered required if:
    - The device's IEEE address has a prefix indicating it is a Tuya device.
    - The device configuration (via tools module) specifies TUYA_MAGIC_READ_ATTRIBUTES.
    - The device model string starts with a known Tuya prefix.

    Args:
        device_model (str): The model identifier of the device.
        device_ieee (str): The IEEE address of the device.

    Returns:
        bool: True if the Tuya magic packet is required, False otherwise.
    """
    if device_ieee and device_ieee[:PREFIX_MAC_LEN] in PREFIX_MACADDR_TUYA:
        return True

    if Modules.tools.get_deviceconf_parameter_value(
        self, device_model, "TUYA_MAGIC_READ_ATTRIBUTES", return_default=False
    ):
        return True

    if device_model and device_model[:3] in TUYA_PREFIX:
        return True

    return False
