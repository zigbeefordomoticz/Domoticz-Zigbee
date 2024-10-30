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

def Decode804B(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgServerMask = MsgData[4:8]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 804B - System Server Discovery response, Sequence number: ' + MsgSequenceNumber + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Server Mask: ' + MsgServerMask)