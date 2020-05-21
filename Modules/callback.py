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
from Modules.bindings import webBind
from Modules.logging import loggingWriteAttributes, loggingBinding


def callbackDeviceAwake(self, nwkid, endpoint, cluster):
    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part

    and will call the manufacturer specific one if needed and if existing
    """

    CALLBACK_TABLE = {
        # Manuf : ( callbackDeviceAwake_xxxxx function )
        '105e' : callbackDeviceAwake_Schneider ,
        '1021' : callbackDeviceAwake_Legrand ,
        }

    if nwkid not in self.ListOfDevices:
        return

    # Let's check if any WebBind have to be established
    callBackForWebBindIfNeeded( self, nwkid )

    callBackForWriteAttributeIfNeeded( self, nwkid )

    # Let's checkfor the Manuf Specific callBacks
    if 'Manufacturer' not in self.ListOfDevices[nwkid]:
        return

    if self.ListOfDevices[nwkid]['Manufacturer'] in CALLBACK_TABLE:
        manuf = self.ListOfDevices[nwkid]['Manufacturer']
        func = CALLBACK_TABLE[ manuf ]
        func( self, nwkid , endpoint, cluster)

def callBackForWriteAttributeIfNeeded(self, key):
    
    if 'WriteAttribute' not in self.ListOfDevices[key]:
        return
        
    for EPout in list (self.ListOfDevices[key]['WriteAttribute']):
        for clusterID in list (self.ListOfDevices[key]['WriteAttribute'][EPout]):
            for attribute in list (self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID]):
                if self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Phase'] != 'waiting':
                    continue

                loggingWriteAttributes( self, 'Debug', "device awake let's write attribute for %s/%s" %(key, EPout), key)
                self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Phase'] = 'requested'
                self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Stamp'] = int(time())
                data_type = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['DataType'] 
                EPin = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPin']
                EPout = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPout']
                manuf_id = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_id']
                manuf_spec = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_spec']
                data = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['data']
                write_attribute (self,key,EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data)

def callBackForWebBindIfNeeded( self , srcNWKID ):
    
    """
    Check that WebBind are well set
    """

    if srcNWKID not in self.ListOfDevices:
        return
    if 'WebBind' not in self.ListOfDevices[srcNWKID]:
        return

    for Ep in list(self.ListOfDevices[srcNWKID]['WebBind']):
        for ClusterId in list(self.ListOfDevices[srcNWKID]['WebBind'][ Ep ]):
            for destNwkid in list(self.ListOfDevices[srcNWKID]['WebBind'][ Ep ][ClusterId]):
                if destNwkid in ('Stamp','Target','TargetIEEE','SourceIEEE','TargetEp','Phase','Status'):
                    Domoticz.Error("---> delete  destNwkid: %s" %( destNwkid))
                    del self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]
                elif ('Phase' in self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid] and \
                                 self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]['Phase'] == 'requested'):
                    if ('Stamp' in self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid] and time() < self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]['Stamp']+ 5):    # Let's wait 5s before trying again
                        continue
                    loggingBinding( self, 'Log', "Redo a WebBind for device %s" %(srcNWKID))
                    sourceIeee = self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]['SourceIEEE']
                    destIeee = self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]['TargetIEEE']
                    destEp = self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]['TargetEp']
                    # Perforning the bind
                    webBind(self, sourceIeee, Ep, destIeee, destEp, ClusterId)

                    self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId][destNwkid]['Stamp'] = int(time())
