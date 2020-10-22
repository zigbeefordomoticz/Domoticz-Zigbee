#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

from datetime import datetime
from time import time

from Modules.basicOutputs import set_poweron_afteroffon
from Modules.readAttributes import ReadAttributeRequest_0006_0000, ReadAttributeRequest_0008_0000, ReadAttributeRequest_0006_400x
from Modules.tools import retreive_cmd_payload_from_8002

from Classes.LoggingManagement import LoggingManagement



def enki_set_poweron_after_offon( self, mode):
    # call from WebServer

    ENKI_POWERON_MODE = { 
        0x00:'Off', # Off
        0x01:'On', # On
        0xff:'Previous state' # Previous state
    }

    if mode not in ENKI_POWERON_MODE:
        Domoticz.Error("enki_set_poweron_after_offon - Unknown mode: %s" %mode)

    for nwkid in self.ListOfDevices:
        if 'Manufacturer' not in self.ListOfDevices[ nwkid ]:
            continue
        if self.ListOfDevices[ nwkid ]['Manufacturer'] != '1277':
            continue
        # We have a Enki device
        if '01' not in self.ListOfDevices[ nwkid ]['Ep']:
            continue
        if '0006' not in self.ListOfDevices[ nwkid ]['Ep']['01']:
            continue
        if '4003' not in self.ListOfDevices[ nwkid ]['Ep']['01']['0006']:
            Domoticz.Log("enki_set_poweron_after_offon Device: %s do not have a Set Power Attribute !" %nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)
            continue

        # At that stage, we have a Philips device with Cluster 0006 and the right attribute
        Domoticz.Log("enki_set_poweron_after_offon - Set PowerOn after OffOn of %s to %s" %(nwkid,ENKI_POWERON_MODE[ mode]))
        set_poweron_afteroffon( self, nwkid, OnOffMode = mode)
        ReadAttributeRequest_0006_400x(self, nwkid)