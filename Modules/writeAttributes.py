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
from Modules.basicOutputs import sendZigateCmd
from Modules.logging import loggingWriteAttributes, loggingBasicOutput

def write_attribute_when_awake( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):
    
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

    loggingWriteAttributes( self, 'Debug', "write_attribute_when_awake for %s/%s - >%s<" %(key, EPout, data), key)


















