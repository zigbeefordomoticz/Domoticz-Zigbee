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
from Modules.readAttributes import ReadAttributeRequest_0406_sonoff_0022
from Modules.zigateConsts import ZIGATE_EP

MANUFACTURER_CODE = "1286"
MAUFACTURER_NAME = "SONOFF"

def is_sonoff_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == MANUFACTURER_CODE or self.ListOfDevices[nwkid]["Manufacturer Name"] == MAUFACTURER_NAME


def sonoff_set_ultrasonic_occupancySensibility(self, nwkid, level):

    if level not in (1, 2, 3):
        return
    write_attribute( self, nwkid, ZIGATE_EP, "01", "0406", MANUFACTURER_CODE, "01", "0022", "20", "%02x" % level, ackIsDisabled=False)
    ReadAttributeRequest_0406_sonoff_0022(self, nwkid)
