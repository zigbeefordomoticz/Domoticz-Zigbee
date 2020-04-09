#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: pluzzy.py

    Description: handle specific Pluzzy devices

"""

import Domoticz
from Modules.logging import loggingPairing, loggingInput


def pluzzyDecode004D( self, MsgSrcAddr, MsgIEEE, MsgMacCapa, decodedMacCapa, RSSI):

    self.logging( 'Debug',  "Pluzzy-Decode004D - Device Annoucement %s %s %s" %(MsgSrcAddr, MsgIEEE, decodedMacCapa))

    return

def pluzzyDecode8102( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, MsgRSSI):

    """
    Receiving a 8102 message and we are using the pluzzy Firmware.
    (1) let's check that MsgSrcAddr is known
    (2) if we are in the pairing/widget creation process, let's specify Model Name for Pluzzy devices.
    """

    loggingInput( self, 'Debug',  "Pluzzy-Decode8102 - Individual Attribute response : [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" \
            %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData ))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("Pluzzy-Decode8102 - Unknown Device %s" %MsgSrcAddr)
        return

    if self.ListOfDevices[MsgSrcAddr]['Status'] == 'UNKNOWN':
        Domoticz.Error("Pluzzy-Decode8102 - Device %s in UNKNOWN state" %MsgSrcAddr)
        return

    if 'Model' in self.ListOfDevices[MsgSrcAddr]:
        if  self.ListOfDevices[MsgSrcAddr]['Model'] != {}:
            # Model alreday defined, so we assumed everything is in order.
            return

    # Let's force the Model name based on Cluster receive
    if MsgClusterId == '0702': 
        # Metering
        self.ListOfDevices[MsgSrcAddr]['ProfileID'] = '0104'
        self.ListOfDevices[MsgSrcAddr]['ZDeviceID'] = '0002'
        self.ListOfDevices[MsgSrcAddr]['Model'] = 'Pluzzy-Plug'

    if MsgClusterId == '0402' or MsgClusterId == '0405':
        # Pluzzy Temp+Humi
        self.ListOfDevices[MsgSrcAddr]['ProfileID'] = '0104'
        self.ListOfDevices[MsgSrcAddr]['ZDeviceID'] = '0302'
        self.ListOfDevices[MsgSrcAddr]['Model'] = 'Pluzzy-TH'

