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

    if fan_mode not in FAN_MODE:
        return

    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] in ("AC211", "AC221", "CAC221"):
        casaia_check_irPairing(self, NwkId)

    # Fan Mode Sequence
    data = "%02x" % 0x02
    write_attribute(
        self,
        NwkId,
        ZIGATE_EP,
        Ep,
        "0202",
        "0000",
        "00",
        "0001",
        "30",
        data,
        ackIsDisabled=is_ack_tobe_disabled(self, NwkId),
    )

    data = "%02x" % FAN_MODE[fan_mode]
    write_attribute(
        self,
        NwkId,
        ZIGATE_EP,
        Ep,
        "0202",
        "0000",
        "00",
        "0000",
        "30",
        data,
        ackIsDisabled=is_ack_tobe_disabled(self, NwkId),
    )
