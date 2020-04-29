#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: lumi.py

    Description: Lumi specifics handling

"""

import Domoticz

from Modules.domoticz import MajDomoDevice
from Modules.output import write_attribute
from Modules.zigateConsts import ZIGATE_EP
from Modules.logging import loggingLumi

def enableOppleSwitch( self, nwkid ):

    if nwkid not in self.ListOfDevices:
        return

    manuf_id = '115F'
    manuf_spec = "01"
    cluster_id = 'FCC0'
    Hattribute = '0009'
    data_type = '20'
    Hdata = '01'

    loggingLumi( self, 'Debug', "Write Attributes LUMI Magic Word Nwkid: %s" %nwkid, nwkid)
    write_attribute( self, nwkid, ZIGATE_EP, '01', cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def lumiReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    if srcNWKID not in self.ListOfDevices:
        return

    Domoticz.Log("lumiReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload))

    if 'Model' not in self.ListOfDevices[srcNWKID]:
        return
    
    _ModelName = self.ListOfDevices[srcNWKID]['Model']

    if _ModelName in ( 'lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01'):
        # Recompute Data in order to match with a similar content with 0x8085/0x8095

        fcf = MsgPayload[0:2] # uint8
        sqn = MsgPayload[2:4] # uint8
        cmd = MsgPayload[4:6] # uint8
        data = MsgPayload[6:] # all the rest

        Data = '00000000000000'
        Data += data

        AqaraOppleDecoding( self, Devices, srcNWKID , srcEp, ClusterID, _ModelName, Data)


def AqaraOppleDecoding( self, Devices, nwkid, Ep, ClusterId, ModelName, payload):

    if ClusterId == '0006': # Top row
        Command =  payload[14:16]    

        loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s,  ON/OFF, Cmd: %s" \
            %(nwkid, Ep, Command), nwkid)

        OnOff = Command
        MajDomoDevice( self, Devices, nwkid, '01', "0006", Command)

    elif ClusterId == '0008': # Middle row

        StepMode = payload[14:16]
        StepSize = payload[16:18]
        TransitionTime = payload[18:22]
        unknown = payload[22:26]

        # Action
        if StepMode == '02': # 1 Click
            action = 'click_'
        elif StepMode == '01': # Long Click
            action = 'long_'
        elif StepMode == '03': # Release
            action = 'release'

        # Button
        if StepSize == '00': # Right
            action += 'right'            
        elif StepSize == '01': # Left
            action += 'left'

        OPPLE_MAPPING_4_6_BUTTONS = {
            'click_left': '00',
            'click_right': '01',
            'long_left': '02',
            'long_right': '03',
            'release': '04'
        }
        loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s, LvlControl, StepMode: %s, StepSize: %s, TransitionTime: %s, unknown: %s action: %s" \
            %(nwkid, Ep,StepMode,StepSize,TransitionTime,unknown, action), nwkid)
        if action in OPPLE_MAPPING_4_6_BUTTONS:
            MajDomoDevice( self, Devices, nwkid, '02', "0006", OPPLE_MAPPING_4_6_BUTTONS[ action ])

    elif ClusterId == '0300': # Botton row (need firmware)
        StepMode = payload[14:16]
        EnhancedStepSize = payload[16:20]
        TransitionTime = payload[20:24]
        ColorTempMinimumMired = payload[24:28]
        ColorTempMaximumMired = payload[28:32]
        unknown = payload[32:36]

        if EnhancedStepSize == '4500': 
            if StepMode == '01':
                action = 'click_gauche'
            elif StepMode == '03':
                action = 'click_droite'

        elif EnhancedStepSize == '0f00': 
            if StepMode == '01':
                action = 'long_gauche'
            elif StepMode == '03':
                action = 'long_droite'
            elif StepMode == '00':
                action = 'release'

        OPPLE_MAPPING_4_6_BUTTONS = {
            'click_left': '00','click_right': '01',
            'long_left': '02','long_right': '03',
            'release': '04'
        }

    loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s, LvlControl, StepMode: %s, StepSize: %s, TransitionTime: %s, unknown: %s action: %s" \
        %(nwkid, Ep,StepMode,StepSize,TransitionTime,unknown, action), nwkid)
        
    if action in OPPLE_MAPPING_4_6_BUTTONS:
        MajDomoDevice( self, Devices, nwkid, '03', "0006", OPPLE_MAPPING_4_6_BUTTONS[ action ])

 
    return