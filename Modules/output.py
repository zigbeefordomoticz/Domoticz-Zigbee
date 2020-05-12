#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate

"""

import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Modules.zigateConsts import ZLL_DEVICES, MAX_LOAD_ZIGATE, CLUSTERS_LIST, MAX_READATTRIBUTES_REQ, LEGRAND_REMOTES, ADDRESS_MODE, CFG_RPT_ATTRIBUTESbyCLUSTERS, SIZE_DATA_TYPE, ZIGATE_EP
from Modules.tools import getClusterListforEP, mainPoweredDevice
from Modules.logging import loggingOutput

from Modules.basicOutputs import write_attribute



def setPIRoccupancyTiming( self, key ):

    manuf_spec = "00"
    manuf_id = "0000"

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0406" in self.ListOfDevices[key]['Ep'][tmpEp]: 
            EPout=tmpEp
            cluster_id = "0406"

            for attribute, dataint in ( ( '0010', 5), ('0011', 10) ):
                data_type = "21" # uint16
                data = '%04x' %dataint

                loggingOutput( self, 'Debug', "setPIRoccupancyTiming for %s/%s - Attribute %s: %s" %(key, EPout, attribute, data), key)
                write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

            ReadAttributeRequest_0406(self, key)
