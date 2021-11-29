#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands ZDP

    Description: 

"""


from Modules.basicOutputs import sendZigateCmd

def zdp_node_descriptor_request(self, nwkid):
    sendZigateCmd(self, "0042", nwkid)
    
def zdp_simple_descriptor_request(self, nwkid ):
    sendZigateCmd(self, "0045", nwkid) 
    
    
def zdp_active_endpoint_request(self, nwkid, endpoint):
    sendZigateCmd(self, "0043", nwkid + endpoint)