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

THERMOSTAT_CLUSTER = "0201"

THERMOSTAT_CONFIG_SET = {
    "MinHeatingSetpoint": ( "0015", "29"),
    "MaxHeatingSetpoint": ( "0016", "29"),
}


def max_heating_setpoint(self, nwkid, value):
    self.log.logging( "thermoSettings", "Debug", f"max_heating_setpoint for {nwkid} - value: {value}", nwkid )
    for ep in getListOfEpForCluster(self, nwkid, THERMOSTAT_CLUSTER):
        write_attribute( 
            self, 
            nwkid,
            ZIGATE_EP, 
            ep, 
            THERMOSTAT_CLUSTER, 
            "0000", 
            "00", 
            THERMOSTAT_CONFIG_SET[ "MaxHeatingSetpoint"][0], 
            THERMOSTAT_CONFIG_SET[ "MaxHeatingSetpoint"][1], 
            "%04x" %value, 
            ackIsDisabled=False, )
        ReadAttributeReq( self, nwkid, ZIGATE_EP, ep, THERMOSTAT_CLUSTER, [ int(THERMOSTAT_CONFIG_SET[ "MaxHeatingSetpoint"][0],16) ], ackIsDisabled=False, checkTime=False, )
    


def min_heating_setpoint(self, nwkid, value):
    self.log.logging( "thermoSettings", "Debug", f"mix_heating_setpoint for {nwkid} - value: {value}", nwkid )
    
    for ep in getListOfEpForCluster(self, nwkid, THERMOSTAT_CLUSTER):
        write_attribute( 
            self, 
            nwkid,
            ZIGATE_EP, 
            ep, 
            THERMOSTAT_CLUSTER, 
            "0000", 
            "00", 
            THERMOSTAT_CONFIG_SET[ "MinHeatingSetpoint"][0], 
            THERMOSTAT_CONFIG_SET[ "MinHeatingSetpoint"][1], 
            "%04x" %value, 
            ackIsDisabled=False, )
        ReadAttributeReq( self, nwkid, ZIGATE_EP, ep, THERMOSTAT_CLUSTER, [ int(THERMOSTAT_CONFIG_SET[ "MinHeatingSetpoint"][0],16) ], ackIsDisabled=False, checkTime=False, )

 
THERMOSTAT_DEVICE_PARAMETERS = {
    "MaxHeatingSetpoint": { "callable": max_heating_setpoint, "description": "Specifies the maximum level that the heating setpoint may be set to, in range of 8° - 28.5"},
    "MinHeatingSetpoint": { "callable": min_heating_setpoint, "description": "Specifies the minimum level that the heating setpoint may be set to, in range of 7.5° - 28°"}
}