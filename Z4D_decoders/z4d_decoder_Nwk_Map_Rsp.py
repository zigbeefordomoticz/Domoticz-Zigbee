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

def Decode804E(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode804E - Receive message')
    if self.networkmap:
        self.networkmap.LQIresp(MsgData)