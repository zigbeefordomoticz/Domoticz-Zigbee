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

from Modules.basicOutputs import set_poweron_afteroffon
from Modules.readAttributes import ReadAttributeRequest_0006_400x

ENKI_POWERON_MODE = {0x00: "Off", 0x01: "On", 0xFF: "Previous state"}  # Off  # On  # Previous state

def is_enky_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == "1277"
