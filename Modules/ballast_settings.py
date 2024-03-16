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



from Modules.basicOutputs import read_attribute, write_attribute
from Modules.tools import (get_deviceconf_parameter_value,
                           getListOfEpForCluster, is_int)
from Modules.zigateConsts import ZIGATE_EP

BALLAST_CLUSTERID = "0301"

BALLAST_CONFIG_SET = {
    "PhysicalMinLevel": ( "0000", "21"),
    "PhysicalMaxLevel": ( "0001", "21"),
    "BallastStatus": ( "0002", "30"),
    "MinLevel": ( "0010", "20"),
    "MaxLevel": ( "0011", "20"),
    "PowerOnLevel": ( "0012", "20"),
    "PowerOnFadeTime": ( "0013", ""),
    "IntrinsicBallastFactor": ("0014", "20"),
    "BallastFactorAdjustment": ( "0015", "20")
}


def Ballast_max_level(self, nwkid, max_level):
    ballast_Configuration_max_level(self, nwkid, max_level)


def Ballast_min_level(self, nwkid, min_level):
    ballast_Configuration_min_level(self, nwkid, min_level)

def ballast_Configuration_max_level(self, nwkid, value):
    ListOfEp = getListOfEpForCluster(self, nwkid, BALLAST_CLUSTERID)
    if ListOfEp:
        for EPout in ListOfEp:
            write_attribute(
                self, nwkid, ZIGATE_EP, EPout, BALLAST_CLUSTERID, "0000", "00", BALLAST_CONFIG_SET["MaxLevel"][0], BALLAST_CONFIG_SET["MaxLevel"][1], "%02x" % value, ackIsDisabled=False
            )
            read_attribute(self, nwkid, ZIGATE_EP, EPout, BALLAST_CLUSTERID, "00", "00", "0000", 1, BALLAST_CONFIG_SET["MaxLevel"][0], ackIsDisabled=False)


def ballast_Configuration_min_level(self, nwkid, value):
    ListOfEp = getListOfEpForCluster(self, nwkid, BALLAST_CLUSTERID)
    if ListOfEp:
        for EPout in ListOfEp:
            write_attribute( self, nwkid, ZIGATE_EP, EPout, BALLAST_CLUSTERID, "0000", "00", BALLAST_CONFIG_SET["MinLevel"][0], BALLAST_CONFIG_SET["MaxLevel"][1], "%02x" % value, ackIsDisabled=False)
            read_attribute(self, nwkid, ZIGATE_EP, EPout, BALLAST_CLUSTERID, "00", "00", "0000", 1, BALLAST_CONFIG_SET["MinLevel"][0], ackIsDisabled=False)


BALLAST_DEVICE_PARAMETERS = {
    "BallastMaxLevel": { "callable": Ballast_max_level, "description": "The MinLevel attribute is 8 bits in length and specifies the light output of the ballast according to the dimming light curve"},
    "BallastMinLevel": { "callable": Ballast_min_level, "description": "The MaxLevel attribute is 8 bits in length and specifies the light output of the ballast according to the dimming light curve"},
}