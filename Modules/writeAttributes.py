#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#  
#
"""
    Module: writeAttributes.py

    Description: 

"""

from time import time
from Modules.basicOutputs import write_attribute
from Modules.logging import loggingWriteAttributes, loggingBasicOutput
from Modules.tools import set_request_datastruct, get_list_waiting_request_datastruct

def write_attribute_when_awake( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled = False):
    # Put on waiting list a Write Attribute to be trigger when we get the device awake

    set_request_datastruct( self, 
        'WriteAttributes', key, endpoint, clusterId, AttributeId, data_type, EPin, EPout, manuf_id, manuf_spec, data, ackIsDisabled, 'waiting' )
    loggingWriteAttributes( self, 'Debug', "write_attribute_when_awake for %s/%s - >%s<" %(key, EPout, data), key)

def callBackForWriteAttributeIfNeeded(self, key):
    # Scan for this device if there are any pending Write Attributes needed.

    for attribute in list(get_list_waiting_request_datastruct( self, 'WriteAttributes', key, endpoint, clusterId )):
        loggingWriteAttributes( self, 'Debug', "device awake let's write attribute for %s/%s" %(key, EPout), key)
        request = get_request_datastruct( self, 
            'WriteAttributes', key, endpoint, clusterId, AttributeId )
        if request is None:
            continue
        data_type, EPin, EPout, manuf_id, manuf_spec, data, ackIsDisabled = request
        write_attribute (self,key,EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled)