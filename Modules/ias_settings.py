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
from Modules.zigateConsts import ZIGATE_EP

IAS_CLUSTER_ID = "0500"

ONOFF_CONFIG_SET = {
    "IAS_CIE_Address": ( "0010", "f0"),
    "ZoneID": ( "0011", "20"),
    "NumberOfZoneSensitivityLevelsSupported": ( "0012", "20"),
    "CurrentZoneSensitivityLevel": ( "0013", "20")
}


def ias_CurrentZoneSensitivityLevel(self, nwkid, ep, value):
    """ Allows an IAS Zone client to query and configure the IAS Zone server’s sensitivity level. """
    
    # The default value 0x00 is the device’s default sensitivity level as configured by the manufacturer. It MAY
    # correspond to the same sensitivity as another value in the NumberOfZoneSensitivityLevelsSupported, but this
    # is the default sensitivity to be used if the CurrentZoneSensitivityLevel attribute is not otherwise configured
    # by an IAS Zone client.

    self.log.logging( "onoffSettings", "Debug", f"ias_CurrentZoneSensitivityLevel for {nwkid}/{ep} - value: {value}", nwkid )
    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        IAS_CLUSTER_ID, 
        "0000", 
        "00", 
        ONOFF_CONFIG_SET[ "CurrentZoneSensitivityLevel"][0], 
        ONOFF_CONFIG_SET[ "CurrentZoneSensitivityLevel"][1], 
        "%02x" %value, 
        ackIsDisabled=False, )


IAS_DEVICE_PARAMETERS = {
    "CurrentZoneSensitivityLevel": ias_CurrentZoneSensitivityLevel
}
