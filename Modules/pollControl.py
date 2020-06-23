#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#
"""
    Module: pollControl.py

    Description: Implement the Poll Control commands

"""

import Domoticz
from Modules.basicOutputs import raw_APS_request


def PollControlCheckin( self, nwkid):

    """
    Poll Control: Check-in Response
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Error("Fast Poll Stop - nwkid: %s do not exist" %nwkid)
        return

    cluster_id = '0020' # Poll Control Cluster
    cmd = '00' # Check-in Response
    startFastPolling = '00'  # False
    fastPollTimeout = '0000' # 0 qyarterseconds
    ep = '01' #Legrand Endpoint

    cluster_frame = '11'
    sqn = '00'

    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    payload = cluster_frame + sqn + cmd + startFastPolling + fastPollTimeout
    raw_APS_request( self, nwkid, ep, '0020', '0104', payload)
    Domoticz.Log("send Fast Poll Stop command 0x%s for %s/%s with payload: %s" %(cmd, nwkid, ep, payload))

def FastPollStop( self, nwkid):

    """
    Fast Poll Stop to be called for Remote Devices
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Error("Fast Poll Stop - nwkid: %s do not exist" %nwkid)
        return

    cluster_id = '0020' # Poll Control Cluster
    cmd = '01' # Fast Poll Stop ( no data)
    ep = '01' #Legrand Endpoint

    cluster_frame = '11'
    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    payload = cluster_frame + sqn + cmd
    raw_APS_request( self, nwkid, ep, '0020', '0104', payload)
    Domoticz.Log("send Fast Poll Stop command 0x%s for %s/%s with payload: %s" %(cmd, nwkid, ep, payload))