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


def is_develco_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == "1015" or self.ListOfDevices[nwkid]["Manufacturer Name"] == "frient A/S"
