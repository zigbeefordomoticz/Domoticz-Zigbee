#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from time import time

import Domoticz

from Modules.schneider_wiser import callbackDeviceAwake_Schneider
from Modules.legrand_netatmo import callbackDeviceAwake_Legrand
from Modules.basicOutputs import write_attribute
from Modules.writeAttributes import callBackForWriteAttributeIfNeeded
from Modules.bindings import webBind, callBackForBindIfNeeded, callBackForWebBindIfNeeded
from Modules.zigateConsts import MAX_LOAD_ZIGATE

CALLBACK_TABLE = {
    # Manuf : ( callbackDeviceAwake_xxxxx function )
    '105e' : callbackDeviceAwake_Schneider ,
    '1021' : callbackDeviceAwake_Legrand ,
    }

def callbackDeviceAwake(self, NwkId, endpoint, cluster):

    # This is fonction is call when receiving a message from a Manufacturer battery based device.
    # The function is called after processing the readCluster part
    # 
    # and will call the manufacturer specific one if needed and if existing


    if NwkId not in self.ListOfDevices:
        return

    # 09/11/2020: Let's check if we are not in pairing mode for this device, or if the Zigate is not overloaded
    if 'PairingInProgress' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['PairingInProgress']:
        return
    if self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE:
        return
    # Let's check if any WebBind have to be established

    # callBackForBindIfNeeded(self, NwkId)
    callBackForWebBindIfNeeded( self, NwkId )

    callBackForWriteAttributeIfNeeded( self, NwkId )

    # Let's checkfor the Manuf Specific callBacks
    if 'Manufacturer' not in self.ListOfDevices[NwkId]:
        return

    if self.ListOfDevices[NwkId]['Manufacturer'] in CALLBACK_TABLE:
        manuf = self.ListOfDevices[NwkId]['Manufacturer']
        func = CALLBACK_TABLE[ manuf ]
        func( self, NwkId , endpoint, cluster)
