#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#   French translation: @martial83
#
"""
    Module: writeAttributes.py

    Description: 

"""

from time import time
from Modules.basicOutputs import sendZigateCmd, write_attribute, write_attributeNoResponse
from Modules.logging import loggingWriteAttributes, loggingBasicOutput

def write_attributeNoResponse_when_awake( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled = False):
    write_attribute_when_awake ( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled = True)

def write_attribute_when_awake( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled = False):
    
    if 'WriteAttribute' not in self.ListOfDevices[key]:
        self.ListOfDevices[key]['WriteAttribute'] = {} 
    if  EPout not in self.ListOfDevices[key]['WriteAttribute']:
        self.ListOfDevices[key]['WriteAttribute'][EPout] = {} 
    if  clusterID not in self.ListOfDevices[key]['WriteAttribute'][EPout]:
        self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID] = {} 
    if  attribute not in self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID]:
        self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute] = {} 
    
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Phase'] = 'waiting'
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Stamp'] = int(time())
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Status'] = ''
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['DataType'] = data_type
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPin'] = EPin
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPout'] = EPout
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_id'] = manuf_id
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_spec'] = manuf_spec
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['data'] = data
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['ackIsDisabled'] = ackIsDisabled

    loggingWriteAttributes( self, 'Debug', "write_attribute_when_awake for %s/%s - >%s<" %(key, EPout, data), key)



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
                ackIsDisabled = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['ackIsDisabled']
                #if ackIsDisabled:
                i_sqn = write_attribute (self,key,EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data)
                #else:
                #    i_sqn = write_attributeNoResponse (self,key,EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data)
                self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['i_sqn'] = i_sqn
















