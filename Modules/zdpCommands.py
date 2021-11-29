#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands ZDP

    Description: 

"""

from Modules.sendZigateCommand import (raw_APS_request, send_zigatecmd_raw,
                                       send_zigatecmd_zcl_noack, sendZigateCmd)


def zdp_IEEE_address_request(self, nwkid, u8RequestType , u8StartIndex):
    self.log.logging( "zdpCommand", "Log","zdp_IEEE_address_request %s %s %s" %(nwkid, u8RequestType , u8StartIndex ))
    return send_zigatecmd_raw(self, "0041", "02" + nwkid + u8RequestType + u8StartIndex)


def zdp_node_descriptor_request(self, nwkid):
    self.log.logging( "zdpCommand", "Log","zdp_node_descriptor_request %s" %(nwkid, ))
    return send_zigatecmd_raw(self, "0042", nwkid)


def zdp_active_endpoint_request(self, nwkid, endpoint):
    self.log.logging( "zdpCommand", "Log","zdp_active_endpoint_request %s %s" %(nwkid, endpoint))
    return send_zigatecmd_raw(self, "0043", nwkid + endpoint)
    
    
def zdp_simple_descriptor_request(self, nwkid ):
    self.log.logging( "zdpCommand", "Log","zdp_simple_descriptor_request %s" %(nwkid))
    return send_zigatecmd_raw(self, "0045", nwkid) 


def zdp_management_leave_request(self, nwkid, ieee, rejoin="01", remove_children="00"):
    self.log.logging( "zdpCommand", "Log","zdp_management_leave_request %s %s %s %s" %(nwkid, ieee, rejoin, remove_children))
    return send_zigatecmd_raw(self, "0047", nwkid + ieee + rejoin + remove_children)


def zdp_permit_joining_request(self, tgtnwkid , duration , significance):
    self.log.logging( "zdpCommand", "Log","zdp_permit_joining_request %s %s %s" %(tgtnwkid , duration , significance))
    return send_zigatecmd_raw(self, "0049", tgtnwkid + duration + significance)


def zdp_reset_device(self, nwkid, epin, epout):
    self.log.logging( "zdpCommand", "Log","zdp_reset_device %s %s %s" %(nwkid, epin, epout))
    return send_zigatecmd_raw(self, "0050", "02" + nwkid + epin + epout)


def zdp_management_network_update_request(self, target_address , channel_mask , scanDuration , scan_repeat="00" , nwk_updateid="00", nwk_manager="0000"):
    self.log.logging( "zdpCommand", "Log","zdp_management_network_update_request %s %s %s %s %s %s" %(
        target_address , channel_mask , scanDuration , scan_repeat , nwk_updateid, nwk_manager))
    datas = target_address + channel_mask + scanDuration + scan_repeat + nwk_updateid + nwk_manager
    return send_zigatecmd_raw(self, "004A", datas)


def zdp_many_to_one_route_request(self, bCacheRoute, u8Radius):
    self.log.logging( "zdpCommand", "Log","zdp_many_to_one_route_request %s %s" %(bCacheRoute, u8Radius))
    return send_zigatecmd_raw(self, "004F", bCacheRoute + u8Radius)
    

def zdp_attribute_discovery_request(self, nwkid, EpIn, EpOut, cluster, start_attribute="0000", manuf_specific="00", manuf_code="0000"):
    self.log.logging( "zdpCommand", "Log","zdp_attribute_discovery_request %s %s %s %s %s %s %s" %(
        nwkid, EpIn, EpOut, cluster, start_attribute, manuf_specific, manuf_code))
    return send_zigatecmd_raw(self, nwkid, "0140", EpIn + EpOut + cluster + start_attribute + "00" + manuf_specific + manuf_code + "01")


def zdp_get_list_attribute_extended_infos(self, nwkid, EpIn, EpOut, cluster, start_attribute="0000", manuf_specific="00", manuf_code="0000"):
    self.log.logging( "zdpCommand", "Log","zdp_get_list_attribute_extended_infos %s %s %s %s %s %s %s" %(
        nwkid, EpIn, EpOut, cluster, start_attribute, manuf_specific, manuf_code))
    return send_zigatecmd_raw(self, nwkid, "0141", EpIn + EpOut + cluster + start_attribute + "00" + manuf_specific + manuf_code + "01")


def zdp_binding_device(self, ieee , ep , cluster , addrmode , destaddr , destep):
    self.log.logging( "zdpCommand", "Log","zdp_binding_device %s %s %s %s %s %s" %(ieee , ep , cluster , addrmode , destaddr , destep))
    return send_zigatecmd_raw(self, "0030", ieee + ep + cluster + addrmode + destaddr + destep)


def zdp_unbinding_device(self, ieee , ep , cluster , addrmode , destaddr , destep):
    self.log.logging( "zdpCommand", "Log","zdp_unbinding_device %s %s %s %s %s %s" %(ieee , ep , cluster , addrmode , destaddr , destep))
    return send_zigatecmd_raw(self, "0031", ieee + ep + cluster + addrmode + destaddr + destep)


# Unavailable under ZiGate
def zdp_management_routing_table_request(self, nwkid, payload):
    return raw_APS_request( self, nwkid, "00", "0032", "0000", payload, zigate_ep="00", highpriority=False, ackIsDisabled=False,)


def zdp_management_binding_table_request(self, nwkid, payload):
    return raw_APS_request( self, nwkid, "00", "0033", "0000", payload, zigate_ep="00", highpriority=False, ackIsDisabled=False,)
