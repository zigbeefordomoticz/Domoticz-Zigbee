#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license


import struct

from Modules.basicOutputs import raw_APS_request
from Modules.zigateConsts import SIZE_DATA_TYPE, ZIGATE_EP


def encode_endian_data(data, datatype):
    if datatype in ("10", "18", "20", "28", "30"):
        return data

    elif datatype in ("09", "19", "21", "29", "31"):
        return "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]

    elif datatype in ("22", "2a"):
        return "%06x" % struct.unpack(">I", struct.pack("I", int(data, 16)))[0]

    elif datatype in ("23", "2b", "39", "e2"):
        return "%08x" % struct.unpack(">I", struct.pack("I", int(data, 16)))[0]

    elif datatype in ("00", "41", "42", "4c"):
        return data
    return data


def read_attribute_response(self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code="0000"):
    # self.log.logging( None, 'Log', "Nwkid: %s Ep: %s Sqn: %s Cluster: %s Status: %s Data_Type: %s Attribute: %s Value: %s" \
    #    %( nwkid, ep, sqn, cluster, status, data_type, attribute, value))

    cmd = "01"  # Attribute Response

    attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(attribute, 16)))[0]
    
    if manuf_code == "0000":
        cluster_frame = "18"  # Profile-wide, Server to Client, Disable default Response
        payload = cluster_frame + sqn + cmd
    else:
        manuf_code = "%04x" % struct.unpack("H", struct.pack(">H", int(manuf_code, 16)))[0]
        cluster_frame = "1C"  # Profile-wide, Manufacturer Specific , Server to Client, Disable default Response
        payload = cluster_frame + manuf_code + sqn + cmd

    payload += attribute + status
    if status == "00":
        payload += data_type + encode_endian_data(value, data_type)

    self.log.logging( "Input", 'Debug', "read_attribute_response - %s/%s Cluster: %s Payload: %s" %(nwkid, ep, cluster, payload))
    raw_APS_request(self, nwkid, ep, cluster, "0104", payload, zigate_ep=ZIGATE_EP)
