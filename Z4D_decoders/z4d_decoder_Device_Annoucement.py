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

from Modules.deviceAnnoucement import device_annoucementv2

def Decode004D(self, Devices, MsgData, MsgLQI):
    device_annoucementv2(self, Devices, MsgData, MsgLQI)