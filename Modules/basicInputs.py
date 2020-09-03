#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import struct

from Modules.basicOutputs import raw_APS_request 
from Modules.zigateConsts import SIZE_DATA_TYPE, ZIGATE_EP


def read_attribute_response( self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code='0000'):

    cmd = '01' # Attribute Response
    if manuf_code == '0000':
        manuf_specific = '00'

    cluster_frame = "18"    # Profile-wide, Server to Client, Disable default Response

    attribute = '%04x' %struct.unpack('H',struct.pack('>H',int(attribute)))[0]       

    if manuf_code == '0000':
        payload = cluster_frame + sqn + cmd 
    else:
        payload = cluster_frame + manuf_code + sqn + cmd 

    if status != '00':
        payload += attribute + status
    else:
        payload += attribute + status + data_type + '%04x' %SIZE_DATA_TYPE[ data_type ] + value

    raw_APS_request( self, nwkid, ep, cluster, '0104', payload, zigate_ep=ZIGATE_EP)
