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

def Decode8060(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.add_group_member_ship_response(MsgData)
        
        
def Decode8061(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.check_group_member_ship_response(MsgData)
        
        
def Decode8062(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.look_for_group_member_ship_response(MsgData)
        
        
def Decode8063(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.remove_group_member_ship_response(MsgData)