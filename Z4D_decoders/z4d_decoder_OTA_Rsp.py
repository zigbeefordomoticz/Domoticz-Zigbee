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

def Decode8501(self, Devices, MsgData, MsgLQI):
    """BLOCK_REQUEST  0x8501  ZiGate will receive this command when device asks OTA firmware"""
    if self.OTA:
        self.OTA.ota_image_block_request(MsgData)
        
        
def Decode8502(self, Devices, MsgData, MsgLQI):
    if self.OTA:
        self.OTA.ota_image_page_request(MsgData)
        
        
def Decode8503(self, Devices, MsgData, MsgLQI):
    if self.OTA:
        self.OTA.ota_upgrade_end_request(MsgData)