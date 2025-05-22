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

from Modules.basicOutputs import write_attribute
from Modules.casaia import casaia_check_irPairing
from Modules.tools import is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP

FAN_MODE = {
    "Off": 0x00,
    "Low": 0x01,
    "Medium": 0x02,
    "High": 0x03,
    "On": 0x04,
    "Auto": 0x05,
    "Smart": 0x06,
}


def change_fan_mode(self, NwkId, Ep, fan_mode):
    """
    Changes the fan mode for a device.
    Supported modes: Off, Low, Medium, High, On, Auto, Smart
    """

    mode_code = FAN_MODE.get(fan_mode)
    if mode_code is None:
        self.log.logging("FanControl", "Error", f"Invalid fan mode '{fan_mode}' for device {NwkId}")
        return

    model = self.ListOfDevices.get(NwkId, {}).get("Model")
    if model in ("AC211", "AC221", "CAC221"):
        casaia_check_irPairing(self, NwkId)

    ack = is_ack_tobe_disabled(self, NwkId)

    # Step 1: Set Fan Mode Sequence to 0x02
    write_attribute(
        self,
        NwkId,
        ZIGATE_EP,
        Ep,
        "0202",        # Fan Control Cluster
        "0000",        # Manufacturer ID
        "00",          # Manufacturer Specific
        "0001",        # Fan Mode Sequence Attribute
        "30",          # Data type: 0x30 = enum8
        "02",          # Value: 0x02
        ackIsDisabled=ack,
    )

    # Step 2: Set Fan Mode
    write_attribute(
        self,
        NwkId,
        ZIGATE_EP,
        Ep,
        "0202",
        "0000",
        "00",
        "0000",        # Fan Mode Attribute
        "30",
        f"{mode_code:02x}",
        ackIsDisabled=ack,
    )
