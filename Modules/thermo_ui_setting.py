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
from Modules.readAttributes import ReadAttributeReq
from Modules.tools import getListOfEpForCluster
from Modules.zigateConsts import ZIGATE_EP

THERMOSTAT_UI_CLUSTER = "0204"

THERMOSTAT_UI_CONFIG_SET = {
    "TemperatureDisplayMode": ( "0000", "30"),
    "KeybadLockout": ( "0001", "30"),
    "ScheduleProgrammingVisibility": ( "0002", "30"),
}

def thermo_ui_keypad_lockout(self, nwkid, value):
    """ The KeypadLockout attribute specifies the level of functionality that is available to the user via the keypad."""
    self.log.logging( "thermoUISettings", "Debug", f"thermo_ui_keypad_lockout for {nwkid} - value: {value}", nwkid )
    for ep in getListOfEpForCluster(self, nwkid, THERMOSTAT_UI_CLUSTER):
        write_attribute( 
            self, 
            nwkid,
            ZIGATE_EP, 
            ep, 
            THERMOSTAT_UI_CLUSTER, 
            "0000", 
            "00", 
            THERMOSTAT_UI_CONFIG_SET[ "KeybadLockout"][0], 
            THERMOSTAT_UI_CONFIG_SET[ "KeybadLockout"][1], 
            "%02x" %value, 
            ackIsDisabled=False, )
        ReadAttributeReq( self, nwkid, ZIGATE_EP, ep, THERMOSTAT_UI_CLUSTER, [ int(THERMOSTAT_UI_CONFIG_SET[ "KeybadLockout"][0],16) ], ackIsDisabled=False, checkTime=False, )


THERMOSTAT_UI_DEVICE_PARAMETERS = {
    "KeybadLockout": { "callable": thermo_ui_keypad_lockout, "description": "KeypadLockout attribute to be set to one of the non-reserved values 0x00 to 0x05"},
}
