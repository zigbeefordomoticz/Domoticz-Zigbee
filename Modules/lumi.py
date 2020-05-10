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

    if 'Model' not in self.ListOfDevices[nwkid]:
        return

    if ( self.ListOfDevices[nwkid]['Model'] in ('lumi.remote.b686opcn01-bulb','lumi.remote.b486opcn01-bulb','lumi.remote.b286opcn01-bulb' )
                                                and 'Lumi' not in self.ListOfDevices[nwkid] ):
        self.ListOfDevices[nwkid]['Lumi'] = {}
        self.ListOfDevices[nwkid]['Lumi']['AqaraOppleBulbMode'] = True
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

    loggingLumi( self, 'Debug', "lumiReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), srcNWKID)

    if 'Model' not in self.ListOfDevices[srcNWKID]:
        return
    
    _ModelName = self.ListOfDevices[srcNWKID]['Model']

    if _ModelName in ( 'lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01'):
        # Recompute Data in order to match with a similar content with 0x8085/0x8095

        fcf = MsgPayload[0:2] # uint8
        sqn = MsgPayload[2:4] # uint8
        cmd = MsgPayload[4:6] # uint8
        data = MsgPayload[6:] # all the rest

        if ClusterID in ( '0006', '0008', '0300'):
            Data = '00000000000000'
            Data += data
            AqaraOppleDecoding( self, Devices, srcNWKID , srcEp, ClusterID, _ModelName, Data)

        elif ClusterID == '0001':
            # 18780a2000201e
            # fcf: 18
            # sqn: 78
            # cmd: 0a
            # DataType: 20
            # Attribute: 0020
            # Value: 1e

            loggingLumi( self, 'Log', "lumiReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
                %(srcNWKID,srcEp , ClusterID, cmd, data ))


def AqaraOppleDecoding( self, Devices, nwkid, Ep, ClusterId, ModelName, payload):

    if 'Model' not in self.ListOfDevices[nwkid]:
        return

#    if not self.pluginconf.pluginConf['AqaraOppleBulbMode']:
#       if 'Model' in self.ListOfDevices:
#            _model = self.ListOfDevices[ 'Model' ]
#            loggingLumi( self, 'Log', "Miss Configuration of Device - Nwkid: %s Model: %s, try to delete and redo the pairing" \
#                %(nwkid, _model ))  
#            return

    _ModelName = self.ListOfDevices[nwkid]['Model']

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
        action = ''

        if EnhancedStepSize == '4500': 
            if StepMode == '01':
                action = 'click_left'
            elif StepMode == '03':
                action = 'click_right'

        elif EnhancedStepSize == '0f00': 
            if StepMode == '01':
                action = 'long_left'
            elif StepMode == '03':
                action = 'long_right'
            elif StepMode == '00':
                action = 'release'

        if _ModelName == 'lumi.remote.b686opcn01': # Ok
            OPPLE_MAPPING_4_6_BUTTONS = {
                'click_left': '00','click_right': '01',
                'long_left': '02','long_right': '03',
                'release': '04'
            }
        elif _ModelName == 'lumi.remote.b486opcn01': # Not seen, just assumption
            OPPLE_MAPPING_4_6_BUTTONS = {
                'click_left': '02','click_right': '03',
            }            
        elif _ModelName == 'lumi.remote.b286opcn01': # Ok
            OPPLE_MAPPING_4_6_BUTTONS = {
                'click_left': '02','click_right': '03',
            }            

        loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s, ColorControl, StepMode: %s, EnhancedStepSize: %s, TransitionTime: %s, ColorTempMinimumMired: %s, ColorTempMaximumMired: %s action: %s" \
            %(nwkid, Ep,StepMode,EnhancedStepSize,TransitionTime,ColorTempMinimumMired, ColorTempMaximumMired, action), nwkid)
        
        if action in OPPLE_MAPPING_4_6_BUTTONS:
            MajDomoDevice( self, Devices, nwkid, '03', "0006", OPPLE_MAPPING_4_6_BUTTONS[ action ])

    return
 

def AqaraOppleDecoding0012(self, Devices, nwkid, Ep, ClusterId, AttributeId, Value):

    # Ep : 01 (left)
    # Value: 0x0001 - click
    #        0x0002 - Double click
    #        0x0003 - Tripple click
    #        0x0000 - Long Click
    #        0x00ff - Release

    OPPLE_MAPPING = {
        '0001': '01',
        '0002': '02',
        '0003': '03',
        '0000': '04',
        '00ff': '05'
    }
    if Value in OPPLE_MAPPING:
        MajDomoDevice( self, Devices, nwkid, Ep, "0006", OPPLE_MAPPING[ Value ])  

    return