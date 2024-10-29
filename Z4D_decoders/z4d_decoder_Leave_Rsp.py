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

from Modules.errorCodes import DisplayStatusCode

def Decode8047(self, Devices, MsgData, MsgLQI):
    MsgDataStatus = MsgData[2:4]
    self.log.logging('Input', 'Status', 'Decode8047 - Leave response, LQI: %s Status: %s - %s' % (int(MsgLQI, 16), MsgDataStatus, DisplayStatusCode(MsgDataStatus)))