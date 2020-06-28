#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

from datetime import datetime
from time import time

from Modules.basicOutputs import raw_APS_request, write_attribute, set_poweron_afteroffon
from Modules.readAttributes import ReadAttributeRequest_0006_0000, ReadAttributeRequest_0008_0000, ReadAttributeRequest_0006_400x
from Modules.logging import loggingPhilips


def pollingPhilips( self, key ):
    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    #if  ( self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE):
    #    return True

    ReadAttributeRequest_0006_0000( self, key)
    ReadAttributeRequest_0008_0000( self, key)

    return False

def callbackDeviceAwake_Philips(self, NwkId, EndPoint, cluster):
    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    Domoticz.Log("callbackDeviceAwake_Legrand - Nwkid: %s, EndPoint: %s cluster: %s" \
            %(NwkId, EndPoint, cluster))

    return

def philipsReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    # Zigbee Command:
    # 0x00: Read Attributes
    # 0x01: Read Attributes Response
    # 0x02: Write Attributes
    # 0x03:
    # 0x04: Write Attributes Response
    # 0x06: Configure Reporting
    # 0x0A: Report Attributes
    # 0x0C: Discover Attributes
    # 0x0D: Discover Attributes Response
    
    if srcNWKID not in self.ListOfDevices:
        return

    loggingPhilips( self, 'Log', "philipsReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), srcNWKID)

    # Motion
    # Nwkid: 329c/02 Cluster: 0001, Command: 07 Payload: 00
    # Nwkid: 329c/02 Cluster: 0001, Command: 0a Payload: 21002050


    if 'Model' not in self.ListOfDevices[srcNWKID]:
        return
    
    _ModelName = self.ListOfDevices[srcNWKID]['Model']

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8
    data = MsgPayload[6:] # all the rest

    loggingPhilips( self, 'Log', "philipsReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
        %(srcNWKID,srcEp , ClusterID, cmd, data ))

def philips_set_poweron_after_offon( self, mode):
    # call from WebServer

    PHILIPS_POWERON_MODE = { 
        0x00:'Off', # Off
        0x01:'On', # On
        0xff:'Previous state' # Previous state
    }

    if mode not in PHILIPS_POWERON_MODE:
        Domoticz.Error("philips_set_poweron_after_offon - Unknown mode: %s" %mode)

    for nwkid in self.ListOfDevices:
        if 'Manufacturer' not in self.ListOfDevices[ nwkid ]:
            continue
        if self.ListOfDevices[ nwkid ]['Manufacturer'] != '100b':
            continue
        # We have a Philips device
        if '0b' not in self.ListOfDevices[ nwkid ]['Ep']:
            continue
        if '0006' not in self.ListOfDevices[ nwkid ]['Ep']['0b']:
            continue
        if '4003' not in self.ListOfDevices[ nwkid ]['Ep']['0b']['0006']:
            Domoticz.Log("philips_set_poweron_after_offon Device: %s do not have a Set Power Attribute !" %nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)
            continue

        # At that stage, we have a Philips device with Cluster 0006 and the right attribute
        Domoticz.Log("philips_set_poweron_after_offon - Set PowerOn after OffOn of %s to %s" %(nwkid,PHILIPS_POWERON_MODE[ mode]))
        set_poweron_afteroffon( self, nwkid, OnOffMode = mode)
        ReadAttributeRequest_0006_400x(self, nwkid)