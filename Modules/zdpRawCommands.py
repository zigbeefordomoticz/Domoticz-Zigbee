#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: zdpRawCommands

    Description: ZDP commands via raw mode

"""
import struct
from Modules.zigateConsts import ZIGATE_EP
from Modules.sendZigateCommand import (raw_APS_request)
from Modules.tools import get_and_inc_ZDP_SQM


def zdp_raw_IEEE_address_request(self, nwkid, u8RequestType , u8StartIndex):
    Cluster = "0001"
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0] + u8RequestType + u8StartIndex
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep="00", groupaddrmode=False, ackIsDisabled=False, )   
    
    
def zdp_raw_node_descriptor_request(self, nwkid):
    self.log.logging( "zdpCommand", "Log","zdp_raw_node_descriptor_request %s" %(nwkid, ))
    Cluster = "0002"
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep="00", groupaddrmode=False, ackIsDisabled=False, )   

def zdp_power_descriptor_request(self, nwkid):
    self.log.logging( "zdpCommand", "Log","zdp_power_descriptor_request %s" %(nwkid, ))
    Cluster = "0003"
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep="00", groupaddrmode=False, ackIsDisabled=False, )   
    
def zdp_raw_simple_descriptor_request(self, nwkid, endpoint):
    self.log.logging( "zdpCommand", "Log","zdp_raw_simple_descriptor_request %s %s" %(nwkid, endpoint))
    Cluster = "0004" 
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0] + endpoint
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep="00", groupaddrmode=False, ackIsDisabled=False, )   

def zdp_raw_active_endpoint_request(self, nwkid,):
    self.log.logging( "zdpCommand", "Log","zdp_raw_active_endpoint_request %s" %(nwkid, ))
    Cluster = "0005"
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep="00", groupaddrmode=False, ackIsDisabled=False, )   
  
def zdp_raw_complex_descriptor_request(self, nwkid,):
    self.log.logging( "zdpCommand", "Log","zdp_raw_active_endpoint_request %s" %(nwkid, ))

    Cluster = "0010"
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep="00", groupaddrmode=False, ackIsDisabled=False, )   

def zdp_raw_user_descriptor_request(self, nwkid,):
    self.log.logging( "zdpCommand", "Log","zdp_raw_active_endpoint_request %s" %(nwkid, ))

    Cluster = "0011"
    payload = get_and_inc_ZDP_SQM(self, nwkid) + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0] 
    return raw_APS_request( self, nwkid, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )   

def zdp_management_routing_table_request(self, nwkid, payload):
    return raw_APS_request( self, nwkid, "00", "0032", "0000", payload, zigate_ep="00", highpriority=False, ackIsDisabled=False,)


def zdp_management_binding_table_request(self, nwkid, payload):
    return raw_APS_request( self, nwkid, "00", "0033", "0000", payload, zigate_ep="00", highpriority=False, ackIsDisabled=False,)
