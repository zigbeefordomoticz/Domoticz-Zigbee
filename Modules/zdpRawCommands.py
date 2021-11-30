#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: zdpRawCommands

    Description: ZDP commands via raw mode

"""

from Modules.zigateConsts import ZIGATE_EP
from Modules.sendZigateCommand import (raw_APS_request)


def zdp_raw_IEEE_address_request(self, nwkid, u8RequestType , u8StartIndex):
    Cluster = "0001"
    payload = nwkid + u8RequestType + u8StartIndex
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )
    
    
def zdp_raw_node_descriptor_request(self, nwkid):
    self.log.logging( "zdpCommand", "Debug","zdp_raw_node_descriptor_request %s" %(nwkid, ))
    Cluster = "0002"
    payload = nwkid
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )

def zdp_power_descriptor_request(self, nwkid):
    self.log.logging( "zdpCommand", "Debug","zdp_power_descriptor_request %s" %(nwkid, ))
    Cluster = "0003"
    payload = nwkid
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )
    
def zdp_raw_simple_descriptor_request(self, nwkid, endpoint):
    self.log.logging( "zdpCommand", "Debug","zdp_raw_simple_descriptor_request %s" %(nwkid, endpoint))

    Cluster = "0004" # 
    payload = nwkid + endpoint
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, ) 

def zdp_raw_active_endpoint_request(self, nwkid,):
    self.log.logging( "zdpCommand", "Debug","zdp_raw_active_endpoint_request %s" %(nwkid, ))

    Cluster = "0005" # 
    payload = nwkid 
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )   
  
def zdp_raw_complex_descriptor_request(self, nwkid,):
    self.log.logging( "zdpCommand", "Debug","zdp_raw_active_endpoint_request %s" %(nwkid, ))

    Cluster = "0010" # 
    payload = nwkid 
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )   

def zdp_raw_user_descriptor_request(self, nwkid,):
    self.log.logging( "zdpCommand", "Debug","zdp_raw_active_endpoint_request %s" %(nwkid, ))

    Cluster = "0011" # 
    payload = nwkid 
    return raw_APS_request( self, payload, "00", Cluster, "0000", payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, ackIsDisabled=False, )   

def zdp_management_routing_table_request(self, nwkid, payload):
    return raw_APS_request( self, nwkid, "00", "0032", "0000", payload, zigate_ep="00", highpriority=False, ackIsDisabled=False,)


def zdp_management_binding_table_request(self, nwkid, payload):
    return raw_APS_request( self, nwkid, "00", "0033", "0000", payload, zigate_ep="00", highpriority=False, ackIsDisabled=False,)
