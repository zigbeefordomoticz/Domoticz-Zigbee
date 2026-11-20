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

FIRMWARE_BRANCH = {
    # Zigate
    "00": "Production",
    "01": "Beta",
    "11": "ZiGate (znp)",

    # Znp
    "20": "CC1352/CC2652, Z-Stack 3.30+ (znp)",
    "21": "CC2531, Z-Stack 3.0.x (znp)",
    "22": "CC2531, Z-Stack Home 1.2 (znp)",

    # Ezsp
    "30": "Elelabs, ELR02x",
    "31": "Elelabs, ELU01x",
    "32": "ZBDongle-E (ezsp)",
    "33": "Dongle Plus MG24 (ezsp)",

    # deCONZ
    "40": "ConBee II",
    "41": "RaspBee II",
    "42": "RaspBee",
    "43": "Conbee III",

    # BLZ
    "50": "Bouffalo Lab Zigbee (BLZ)",
    
    "97": "Unknown deConz",
    "98": "Unknown Silicon Labs",
    "99": "Unknown ZNP"
}

ZNP_MODEL = {
    "CC1352/CC2652, Z-Stack 3.30+": "20",
    "CC2531, Z-Stack 3.0.x": "21",
    "CC2531, Z-Stack Home 1.2": "22",
    "CC2652": "20",
    "CC2531": "21",
    "CC2538": "23",
    "ConBee II": "40",
    "Conbee II": "40",
    "Raspbee II": "41",
    "RaspBee II": "41",
    "RaspBee": "42",
    "Raspbee": "42",
    "Conbee III": "43",
    "Elelabs, ELR02x": "30",
    "Elelabs, ELU01x": "31",
}

# Firmware family by "Branch Version" range (see FIRMWARE_BRANCH above).
FIRMWARE_FAMILY_RANGES = (
    (0, 20, "Zigate"),
    (20, 30, "Znp"),
    (30, 40, "Ezsp"),
    (40, 50, "deCONZ"),
    (50, 60, "BLZ"),
)

# Firmware family from the "Coordinator Model" plugin parameter (Mode1), used
# when the branch does not name one: the "Unknown deConz / Silicon Labs / ZNP"
# branches (97, 98, 99) or a branch that cannot be read.
MODE1_FIRMWARE_FAMILY = {
    "V1": "Zigate",
    "V2": "Zigate",
    "ZigpyZiGate": "Zigate",
    "ZigpyZNP": "Znp",
    "ZigpyEZSP": "Ezsp",
    "ZigpydeCONZ": "deCONZ",
    "ZigpyBLZ": "BLZ",
}


def firmware_family(branch_version, mode1):
    """Return the firmware family label ("Znp", "Ezsp", ...) for the coordinator.

    The branch reported by the radio wins. When it names no family, the
    coordinator model the user selected (Mode1) is used, and "UNK" only when
    neither is known.
    """
    try:
        branch = int(branch_version)
    except (TypeError, ValueError):
        branch = None

    if branch is not None:
        for low, high, family in FIRMWARE_FAMILY_RANGES:
            if low <= branch < high:
                return family

    return MODE1_FIRMWARE_FAMILY.get(mode1, "UNK")


def set_display_firmware_version( self ):
    family = firmware_family(self.ControllerData.get("Branch Version"), self.pluginParameters.get("Mode1"))
    self.pluginParameters["DisplayFirmwareVersion"] = "%s - %s" % (family, self.ControllerData["Minor Version"])
