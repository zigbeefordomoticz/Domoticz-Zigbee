#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz

from Modules.basicInputs import read_attribute_response
from datetime import datetime


def timeserver_read_attribute_request( self, sqn, nwkid, ep, cluster, manuf_spec, manuf_code , attribute):
    
    self.log.logging(  "Input", "Debug", "timeserver_read_attribute_request [%s] %s/%s Cluster: %s Attribute: %s" %(sqn, nwkid, ep, cluster,attribute))
    data_type = value = None
    status = '86'

    if attribute == '0000': # Time (should be probded by ZiGate)
        self.log.logging(  "Input", "Debug", "-->Local Time: %s" %datetime.now())
        EPOCTime = datetime(2000,1,1)
        UTCTime = int((datetime.now() - EPOCTime).total_seconds())
        value = "%08x" %UTCTime
        data_type = 'e2' # UTC Type
        status = '00'

    elif attribute == '0001': # Time status
        self.log.logging(  "Input", "Debug", "-->Time Status: %s" %0b00001100)
        value = "%08x" %0b00001100
        data_type = '18' # map8
        status = '00'        

    elif attribute == '0002': # Timezone
        self.log.logging(  "Input", "Debug", "--> TimeZone %0x" %0x00000000)
        value = "%08x" %0x00000000
        data_type = '23' # unint32
        status = '00'

    elif attribute == '0007': # LocalTime
        self.log.logging(  "Input", "Debug", "-->Local Time: %s" %datetime.now())
        EPOCTime = datetime(2000,1,1)
        UTCTime = int((datetime.now() - EPOCTime).total_seconds())
        value = "%08x" %UTCTime
        data_type = '23' # uint32
        status = '00'

    self.log.logging(  "Input", "Debug", "timeserver_read_attribute_request Response: status: %s attribute: %s value: %s" %(status, attribute, value))
    read_attribute_response( self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code='0000')