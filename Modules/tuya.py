#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: tuya.py

    Description: Tuya specific

"""

import Domoticz

import struct

from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import sendZigateCmd, raw_APS_request

from Modules.logging import loggingTuya


# Tuya TRV Commands
# https://medium.com/@dzegarra/zigbee2mqtt-how-to-add-support-for-a-new-tuya-based-device-part-2-5492707e882d

# Cluster 0xef00
# Commands 
#   Direction: Coordinator -> Device 0x00 SetPoint 
#   Direction: Device -> Coordinator 0x01 
#   Direction: Device -> Coordinator 0x02 Setpoint command response


def tuya_setpoint( self, nwkid, setpoint_value):

    # determine which Endpoint
    EPout = '01'

    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cluster_frame = '11'
    cmd = '00' # Setpoint
    action = '0202'
    data = '%08x' %setpoint_value
    tuya_cmd( self, cluster_frame, sqn, cmd, action, data)


def tuya_cmd( self, cluster_frame, sqn, cmd, action, data ):

    if 'Tuya' not in self.ListOfDevices['nwkid']:
        self.ListOfDevices['nwkid']['Tuya'] = {}

    if 'TuyaTransactionId' not in self.ListOfDevices['nwkid']:
        self.ListOfDevices['nwkid']['TuyaTransactionId'] = 0x00
    self.ListOfDevices['nwkid']['TuyaTransactionId'] += 1

    if self.ListOfDevices['nwkid']['TuyaTransactionId'] > 0xff:
        self.ListOfDevices['nwkid']['TuyaTransactionId'] = 0x00
    
    transid = '%02x' %self.ListOfDevices['nwkid']['TuyaTransactionId']
    payload = cluster_frame + sqn + cmd + '00' + transid + action + '00' + '%02x' %len(data) + data
    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingTuya( self, 'Debug', "tuya_cmd - %s/%s cmd: %s payload: %s" %(nwkid, ep , cmd, payload))