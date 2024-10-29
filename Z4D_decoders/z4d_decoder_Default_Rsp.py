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

def Decode8101(self, Devices, MsgData, MsgLQI):
    MsgDataSQN = MsgData[:2]
    MsgDataEp = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgDataCommand = MsgData[8:10]
    MsgDataStatus = MsgData[10:12]
    self.log.logging('Input', 'Debug', 'Decode8101 - Default response - SQN: %s, EP: %s, ClusterID: %s , DataCommand: %s, - Status: [%s] %s' % (MsgDataSQN, MsgDataEp, MsgClusterId, MsgDataCommand, MsgDataStatus, DisplayStatusCode(MsgDataStatus)))