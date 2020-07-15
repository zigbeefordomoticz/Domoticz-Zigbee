#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: cmdsDoorLock.py

    Description: Implement Door Lock cluster command

"""

import Domoticz
from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import raw_APS_request


def cluster0101_lock_door( self, NwkId):

    cmd = '00'
    # determine which Endpoint
    EPout = '01'
    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['SQN'] != {} and self.ListOfDevices[NwkId]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[NwkId]['SQN'],16) + 1)

    # Cluster Frame:
    #  Frame Type: Cluster Command (1)
    #  Manufacturer Specific True
    #  Command Direction: Client to Server (0)
    #  Disable default response: false
    #  Reserved : 0x00
    cluster_frame = '00'
    
    payload = cluster_frame + sqn + cmd
    raw_APS_request( self, NwkId, '01', '0008', '0104', payload, zigate_ep=ZIGATE_EP)


def cluster0101_unlock_door( self, NwkId):

    cmd = '01'
    # determine which Endpoint
    EPout = '01'
    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['SQN'] != {} and self.ListOfDevices[NwkId]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[NwkId]['SQN'],16) + 1)

    # Cluster Frame:
    #  Frame Type: Cluster Command (1)
    #  Manufacturer Specific True
    #  Command Direction: Client to Server (0)
    #  Disable default response: false
    #  Reserved : 0x00
    cluster_frame = '00'
    
    payload = cluster_frame + sqn + cmd
    raw_APS_request( self, NwkId, '01', '0008', '0104', payload, zigate_ep=ZIGATE_EP)

def cluster0101_toggle_door( self, NwkId):

    cmd = '02'
    # determine which Endpoint
    EPout = '01'
    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['SQN'] != {} and self.ListOfDevices[NwkId]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[NwkId]['SQN'],16) + 1)

    # Cluster Frame:
    #  Frame Type: Cluster Command (1)
    #  Manufacturer Specific True
    #  Command Direction: Client to Server (0)
    #  Disable default response: false
    #  Reserved : 0x00
    cluster_frame = '00'

    payload = cluster_frame + sqn + cmd
    raw_APS_request( self, NwkId, '01', '0008', '0104', payload, zigate_ep=ZIGATE_EP)