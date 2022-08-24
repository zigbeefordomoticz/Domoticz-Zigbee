#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: low level commands ZDP

    Description: 

"""

from Modules.sendZigateCommand import raw_APS_request, send_zigatecmd_raw

from Zigbee.zdpRawCommands import (zdp_raw_active_endpoint_request,
                                   zdp_raw_binding_device,
                                   zdp_raw_IEEE_address_request,
                                   zdp_raw_leave_request,
                                   zdp_raw_node_descriptor_request,
                                   zdp_raw_NWK_address_request,
                                   zdp_raw_nwk_lqi_request,
                                   zdp_raw_nwk_update_request,
                                   zdp_raw_permit_joining_request,
                                   zdp_raw_simple_descriptor_request,
                                   zdp_raw_unbinding_device)


def zdp_NWK_address_request(self, router_nwkid, lookup_ieee, u8RequestType="00", u8StartIndex="00"):
    # sourcery skip: replace-interpolation-with-fstring, use-fstring-for-concatenation
    # zdp_raw_NWK_address_request(self, router, ieee, u8RequestType, u8StartIndex)
    # The NWK_addr_req is generated from a Local Device wishing to inquire as to the 16-bit address of
    # the Remote De- vice based on its known IEEE address. 
    # The destination addressing on this command shall be unicast or broadcast to all devices 
    # for which macRxOnWhenIdle = TRUE.
    self.log.logging("zdpCommand", "Log", "zdp_NWK_address_request %s %s %s %s" % (router_nwkid, lookup_ieee, u8RequestType, u8StartIndex))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_NWK_address_request(self, router_nwkid, lookup_ieee, u8RequestType, u8StartIndex)
    return send_zigatecmd_raw(self, "0040", "02" + router_nwkid + lookup_ieee + u8RequestType + u8StartIndex)


def zdp_IEEE_address_request(self, router_nwkid, lookup_nwkid, u8RequestType="00", u8StartIndex="00"):
    # sourcery skip: replace-interpolation-with-fstring, use-fstring-for-concatenation
    # zdp_raw_IEEE_address_request(self, router, nwkid, u8RequestType, u8StartIndex):
    # The Node_Desc_req command is generated from a local device wishing to inquire as to the node descriptor of a remote device. 
    # This command shall be unicast either to the remote device itself or 
    # to an alternative device that contains the discovery information of the remote device.

    self.log.logging("zdpCommand", "Log", "zdp_IEEE_address_request %s %s %s" % (lookup_nwkid, u8RequestType, u8StartIndex))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_IEEE_address_request(self, router_nwkid, lookup_nwkid, u8RequestType, u8StartIndex)
    return send_zigatecmd_raw(self, "0041", "02" + router_nwkid + lookup_nwkid + u8RequestType + u8StartIndex)

def zdp_node_descriptor_request(self, nwkid):
    self.log.logging("zdpCommand", "Debug", "zdp_node_descriptor_request %s" % (nwkid,))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_node_descriptor_request(self, nwkid)
    return send_zigatecmd_raw(self, "0042", nwkid)


def zdp_permit_joining_request(self, tgtnwkid, duration, significance):
    self.log.logging("zdpCommand", "Debug", "zdp_permit_joining_request %s %s %s" % (tgtnwkid, duration, significance))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_permit_joining_request(self, tgtnwkid, duration, significance)
    return send_zigatecmd_raw(self, "0049", tgtnwkid + duration + significance)


def zdp_get_permit_joint_status(self):
    self.log.logging("zigateCommand", "Debug", "zigate_get_permit_joint_status")
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return
    return send_zigatecmd_raw(self, "0014", "")  # Request Permit to Join status


def zdp_simple_descriptor_request(self, nwkid, endpoint):
    self.log.logging("zdpCommand", "Debug", "zdp_active_endpoint_request %s %s" % (nwkid, endpoint))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_simple_descriptor_request(self, nwkid, endpoint)
    return send_zigatecmd_raw(self, "0043", nwkid + endpoint)


def zdp_active_endpoint_request(self, nwkid):
    self.log.logging("zdpCommand", "Debug", "zdp_simple_descriptor_request %s" % (nwkid))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_active_endpoint_request(
            self,
            nwkid,
        )
    return send_zigatecmd_raw(self, "0045", nwkid)


def zdp_management_leave_request(self, nwkid, ieee, rejoin="01", remove_children="00"):
    self.log.logging("zdpCommand", "Debug", "zdp_management_leave_request %s %s %s %s" % (nwkid, ieee, rejoin, remove_children))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_leave_request(self, nwkid, ieee, rejoin="01", remove_children="00")
    return send_zigatecmd_raw(self, "0047", nwkid + ieee + rejoin + remove_children)


def zdp_reset_device(self, nwkid, epin, epout):
    self.log.logging("zdpCommand", "Debug", "zdp_reset_device %s %s %s" % (nwkid, epin, epout))
    return send_zigatecmd_raw(self, "0050", "02" + nwkid + epin + epout)


def zdp_management_network_update_request(self, target_address, channel_mask, scanDuration, scan_repeat="00", nwk_updateid="00", nwk_manager="0000"):
    self.log.logging("zdpCommand", "Debug", "zdp_management_network_update_request %s %s %s %s %s %s" % (target_address, channel_mask, scanDuration, scan_repeat, nwk_updateid, nwk_manager))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_nwk_update_request(self, target_address, channel_mask, scanDuration, scan_repeat, nwk_updateid, nwk_manager)
    datas = target_address + channel_mask + scanDuration + scan_repeat + nwk_updateid + nwk_manager
    return send_zigatecmd_raw(self, "004A", datas)


def zdp_many_to_one_route_request(self, bCacheRoute, u8Radius):
    self.log.logging("zdpCommand", "Debug", "zdp_many_to_one_route_request %s %s" % (bCacheRoute, u8Radius))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return
    return send_zigatecmd_raw(self, "004F", bCacheRoute + u8Radius)


def zdp_binding_device(self, ieee, ep, cluster, addrmode, destaddr, destep):
    self.log.logging("zdpCommand", "Debug", "zdp_binding_device %s %s %s %s %s %s" % (ieee, ep, cluster, addrmode, destaddr, destep))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_binding_device(self, ieee, ep, cluster, addrmode, destaddr, destep)
    return send_zigatecmd_raw(self, "0030", ieee + ep + cluster + addrmode + destaddr + destep)


def zdp_unbinding_device(self, ieee, ep, cluster, addrmode, destaddr, destep):
    self.log.logging("zdpCommand", "Debug", "zdp_unbinding_device %s %s %s %s %s %s" % (ieee, ep, cluster, addrmode, destaddr, destep))
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_unbinding_device(self, ieee, ep, cluster, addrmode, destaddr, destep)
    return send_zigatecmd_raw(self, "0031", ieee + ep + cluster + addrmode + destaddr + destep)


def zdp_nwk_lqi_request( self, nwkid, start):
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zdp_raw_nwk_lqi_request(self, nwkid, start)
    return send_zigatecmd_raw(self, "004E", nwkid + start)
