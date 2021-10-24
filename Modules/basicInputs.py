#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import struct

from Modules.basicOutputs import raw_APS_request
from Modules.zigateConsts import SIZE_DATA_TYPE, ZIGATE_EP


def encode_endian_data(data, datatype):
    if datatype in ("10", "18", "20", "28", "30"):
        value = data

    elif datatype in ("09", "19", "21", "29", "31"):
        value = "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]

    elif datatype in ("22", "2a"):
        value = "%06x" % struct.unpack(">I", struct.pack("I", int(data, 16)))[0]

    elif datatype in ("23", "2b", "39", "e2"):
        value = "%08x" % struct.unpack(">I", struct.pack("I", int(data, 16)))[0]

    elif datatype in ("00", "41", "42", "4c"):
        value = data

    else:
        value = data
        Domoticz.Log("-------> Data not decoded Type: %s Value: %s " % (datatype, value))

    # self.log.logging( None, 'Log', "encode_endian %s -> %s" %(data, value))
    return value


def read_attribute_response(self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code="0000"):
    # self.log.logging( None, 'Log', "Nwkid: %s Ep: %s Sqn: %s Cluster: %s Status: %s Data_Type: %s Attribute: %s Value: %s" \
    #    %( nwkid, ep, sqn, cluster, status, data_type, attribute, value))

    cmd = "01"  # Attribute Response
    if manuf_code == "0000":
        manuf_specific = "00"

    attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(attribute, 16)))[0]

    if manuf_code == "0000":
        cluster_frame = "18"  # Profile-wide, Server to Client, Disable default Response
        payload = cluster_frame + sqn + cmd
    else:
        cluster_frame = "28"  # Manufacturer Specific , Server to Client, Disable default Response
        payload = cluster_frame + manuf_code + sqn + cmd

    payload += attribute + status
    if status == "00":
        payload += data_type + encode_endian_data(value, data_type)

    # self.log.logging( None, 'Log', "read_attribute_response - %s/%s Cluster: %s Payload: %s" %(nwkid, ep, cluster, payload))
    raw_APS_request(self, nwkid, ep, cluster, "0104", payload, zigate_ep=ZIGATE_EP)
