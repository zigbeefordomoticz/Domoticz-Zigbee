#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: zdpRawCommands

    Description: ZDP commands via raw mode

"""
import struct

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZDP_SQN
from Modules.zigateConsts import ZIGATE_EP

# ZDP Commands


def zdp_raw_NWK_address_request(self, router, ieee, u8RequestType, u8StartIndex):
    # sourcery skip: replace-interpolation-with-fstring, use-fstring-for-concatenation
    
    Cluster = "0000"
    zdp_command_formated_logging( self, "NWK_addr_req (raw)", router, Cluster, ieee, u8RequestType, u8StartIndex)
    sqn = get_and_inc_ZDP_SQN(self, router)
    payload = sqn + "%016x" % struct.unpack("Q", struct.pack(">Q", int(ieee, 16)))[0] + u8RequestType + u8StartIndex
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_NWK_address_request  - [%s] %s Queue Length: %s" % (
            sqn, router, self.ControllerLink.loadTransmit()), )
    else:
        self.log.logging( "zdpCommand", "Debug", "zdp_raw_NWK_address_request  - [%s] %s Queue Length: %s" % (
            sqn, router, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        router,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_IEEE_address_request(self, router, nwkid, u8RequestType, u8StartIndex):
    # sourcery skip: replace-interpolation-with-fstring, use-fstring-for-concatenation
    
    Cluster = "0001"
    zdp_command_formated_logging( self, "IEEE_addr_req (raw)", router, Cluster, nwkid, u8RequestType, u8StartIndex)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0] + u8RequestType + u8StartIndex
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_IEEE_address_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )
    else:
        self.log.logging( "zdpCommand", "Debug", "zdp_raw_IEEE_address_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        router,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_node_descriptor_request(self, nwkid):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_node_descriptor_request %s" % (nwkid,))
    Cluster = "0002"
    zdp_command_formated_logging( self, "Node_Descriptor_req (raw)", nwkid, Cluster)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_node_descriptor_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )
    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_power_descriptor_request(self, nwkid):
    self.log.logging("zdpCommand", "Debug", "zdp_power_descriptor_request %s" % (nwkid,))
    Cluster = "0003"
    zdp_command_formated_logging( self, "Power_Descriptor_req (raw)", nwkid, Cluster)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_power_descriptor_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_simple_descriptor_request(self, nwkid, endpoint):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_simple_descriptor_request %s %s" % (nwkid, endpoint))
    Cluster = "0004"
    zdp_command_formated_logging( self, "Simple_Descriptor_req (raw)", nwkid, Cluster, endpoint)

    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0] + endpoint
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_simple_descriptor_request  - [%s] %s %s Queue Length: %s" % (
            sqn, nwkid, endpoint, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_active_endpoint_request(
    self,
    nwkid,
):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_active_endpoint_request %s" % (nwkid,))
    Cluster = "0005"
    zdp_command_formated_logging( self, "Active_Endpoint_req (raw)", nwkid, Cluster)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_active_endpoint_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_match_desc_req_0500(self, nwkid):
    
    cluster = "0006"
    zdp_command_formated_logging( self, "Match_Descriptor_req (raw)", nwkid, cluster)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    nwkid_of_interest = "%04x" %struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    profileid = "%04x" %struct.unpack(">H", struct.pack("H", int("0104", 16)))[0]
    numInClusters = "01"
    InClusterList = "%04x" %struct.unpack(">H", struct.pack("H", int("0500", 16)))[0]
    NumOutClusters = "00"
    payload = sqn + nwkid_of_interest + profileid + numInClusters + InClusterList + NumOutClusters
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_match_desc_req  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()),)
    else:
        self.log.logging( "zdpCommand", "Debug", "zdp_raw_NWK_address_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()),)
 
    raw_APS_request(
        self,
        nwkid,
        "00",
        cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_complex_descriptor_request(
    self,
    nwkid,
):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_active_endpoint_request %s" % (nwkid,))
    Cluster = "0010"
    zdp_command_formated_logging( self, "Active_Endpoint_req (raw)", nwkid, Cluster)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_complex_descriptor_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_user_descriptor_request(
    self,
    nwkid,
):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_user_descriptor_request %s" % (nwkid,))
    Cluster = "0011"
    zdp_command_formated_logging( self, "User_Descriptor_req (raw)", nwkid, Cluster)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + "%04x" % struct.unpack(">H", struct.pack("H", int(nwkid, 16)))[0]
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_user_descriptor_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigpyzqn=sqn,
        zigate_ep=ZIGATE_EP,
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_discovery_cache_req(self, nwkid):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_discovery_cache_req %s" % ("NOT IMPLEMENTED",))
    cluster = "0012"
    sqn = get_and_inc_ZDP_SQN(self, nwkid)


# Bindings primitive


def zdp_raw_binding_device(self, source, src_ep, cluster, addrmode, destination, dst_ep):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_binding_device %s %s %s %s %s %s" % (source, src_ep, cluster, addrmode, destination, dst_ep))

    if source in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[source]
    else:
        self.log.logging("zdpCommand", "Debug", "zdp_raw_unbinding_device %s not found in IEEE2NWK" % (source))
        return
    Cluster = "0021"
    zdp_command_formated_logging( self, "Bind_Req (raw)", nwkid, Cluster, src_ep, cluster, addrmode, destination, dst_ep)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn
    payload += "%016x" % struct.unpack("Q", struct.pack(">Q", int(source, 16)))[0]
    payload += src_ep
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(cluster, 16)))[0]
    payload += "03"  # Unicast
    payload += "%016x" % struct.unpack("Q", struct.pack(">Q", int(destination, 16)))[0]
    payload += dst_ep
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_binding_device  - [%s] %s Queue Length: %s" % (
            sqn, source, self.ControllerLink.loadTransmit()),)

    delayAfterSent=self.pluginconf.pluginConf.get("bindingDelay", False)
 
    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        groupaddrmode=False,
        ackIsDisabled=False,
        delayAfterSent=delayAfterSent
    )
    self.log.logging("zdpCommand", "Debug", "zdp_raw_binding_device returning ZDP SQN: %s" % sqn)
    return sqn


def zdp_raw_unbinding_device(self, source, src_ep, cluster, addrmode, destination, dst_ep):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_unbinding_device %s %s %s %s %s %s" % (source, src_ep, cluster, addrmode, destination, dst_ep))

    if source in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[source]
    else:
        self.log.logging("zdpCommand", "Debug", "zdp_raw_unbinding_device %s not found in IEEE2NWK" % (source))
        return
    Cluster = "0022"
    zdp_command_formated_logging( self, "Unbind_Req (raw)", nwkid, Cluster, src_ep, cluster, addrmode, destination, dst_ep)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn
    payload += "%016x" % struct.unpack("Q", struct.pack(">Q", int(source, 16)))[0]
    payload += src_ep
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(cluster, 16)))[0]
    payload += "03"  # Unicast
    payload += "%016x" % struct.unpack("Q", struct.pack(">Q", int(destination, 16)))[0]
    payload += dst_ep
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_unbinding_device  - [%s] %s Queue Length: %s" % (
            sqn, source, self.ControllerLink.loadTransmit()), )

    delayAfterSent=self.pluginconf.pluginConf.get("bindingDelay", False)

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigpyzqn=sqn,
        zigate_ep="00",
        groupaddrmode=False,
        ackIsDisabled=False,
        delayAfterSent=delayAfterSent
    )
    self.log.logging("zdpCommand", "Debug", "zdp_raw_unbinding_device returning sqn: %s" % sqn)
    return sqn


# Network Management Client Services


def zdp_raw_nwk_lqi_request(self, nwkid, start_index):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_nwk_lqi_request %s" % (start_index,))
    Cluster = "0031"
    zdp_command_formated_logging( self, "LQI_Req (raw)", nwkid, Cluster, start_index)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + start_index
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_nwk_lqi_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        highpriority=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_management_routing_table_request(self, nwkid, payload):
    self.log.logging("zdpCommand", "Debug", "zdp_management_routing_table_request %s" % (payload,))
    Cluster = "0032"
    zdp_command_formated_logging( self, "Routing_Table_Req (raw)", nwkid, Cluster, payload)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_management_routing_table_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        highpriority=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_management_binding_table_request(self, nwkid, payload):
    self.log.logging("zdpCommand", "Debug", "zdp_management_binding_table_request %s" % (payload,))
    Cluster = "0033"
    zdp_command_formated_logging( self, "Binding_Table_Req (raw)", nwkid, Cluster, payload)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_management_binding_table_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigate_ep="00",
        zigpyzqn=sqn,
        highpriority=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_permit_joining_request(self, tgtnwkid, duration, significance):
    self.log.logging( "zdpCommand", "Debug", "zdp_raw_permit_joining_request %s %s %s" % ( 
        tgtnwkid, duration, significance, ), )
    if self.zigbee_communication == "zigpy":
        if (
            tgtnwkid not in ('FFFC', 'fffc')
            and tgtnwkid in self.ListOfDevices
            and 'IEEE' in self.ListOfDevices[tgtnwkid]
        ):
            tgtnwkid = int(self.ListOfDevices[ tgtnwkid ]['IEEE'],16)
        data = {"Duration": int(duration, 16), "targetRouter": tgtnwkid}
        
        return self.ControllerLink.sendData("PERMIT-TO-JOIN", data)


def zdp_raw_management_permit_joining_req(self, nwkid, duration, significance):
    self.log.logging( "zdpCommand", "Debug", "zdp_raw_management_permit_joining_req %s %s %s" % ( 
        nwkid, duration, significance, ), )


def zdp_raw_leave_request(self, nwkid, ieee, rejoin="01", remove_children="00"):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_leave_request %s %s" % (nwkid, ieee))
    Cluster = "0034"
    zdp_command_formated_logging( self, "Leave_Req (raw)", nwkid, Cluster, ieee, rejoin, remove_children)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)

    if rejoin == "00" and remove_children == "00":
        flag = "00"
    elif rejoin == "00" and remove_children == "01":
        flag = "01"
    elif rejoin == "01" and remove_children == "00":
        flag = "02"
    if rejoin == "01" and remove_children == "01":
        flag = "03"
    payload = sqn + "%016x" % struct.unpack("Q", struct.pack(">Q", int(ieee, 16)))[0] + flag
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_leave_request  - [%s] %s Queue Length: %s" % (
            sqn, nwkid, self.ControllerLink.loadTransmit()), )

    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigpyzqn=sqn,
        zigate_ep="00",
        groupaddrmode=False,
        ackIsDisabled=False,
    )
    return sqn


def zdp_raw_nwk_update_request(self, nwkid, scanchannel, scanduration, scancount="", nwkupdateid="", nwkmanageraddr=""):
    self.log.logging("zdpCommand", "Debug", "zdp_raw_nwk_update_request %s %s %s %s %s %s" % (
        nwkid, scanchannel, scanduration, scancount, nwkupdateid, nwkmanageraddr))

    Cluster = "0038"
    zdp_command_formated_logging( self, "NWK_Update_Req (raw)", nwkid, Cluster, scanchannel, scanduration, scancount, nwkupdateid, nwkmanageraddr)
    
    sqn = get_and_inc_ZDP_SQN(self, nwkid)
    payload = sqn + scanchannel + scanduration 
    
    if 0x01 < int(scanduration,16) < 0x05:
        payload += scancount
        
    if scanduration in ( "fe", "ff"):
        payload += nwkupdateid
        
    if scanduration == "ff":
        payload += nwkmanageraddr
        
    self.log.logging("zdpCommand", "Debug", "zdp_raw_nwk_update_request Payload: %s" % ( payload))
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging( "zdpCommand", "Log", "zdp_raw_nwk_update_request  - [%s] %s %s Queue Length: %s" % (
            sqn, nwkid, payload, self.ControllerLink.loadTransmit()), )
       
    raw_APS_request(
        self,
        nwkid,
        "00",
        Cluster,
        "0000",
        payload,
        zigpyzqn=sqn,
        zigate_ep="00",
    )
    if scanduration == "fe":
        raw_APS_request(
            self,
            "0000",
            "00",
            Cluster,
            "0000",
            payload,
            zigpyzqn=sqn,
            zigate_ep="00",
        )

    return sqn


def zdp_command_formated_logging( self, command, nwkid, cluster, *args):

    if not self.pluginconf.pluginConf["trackZdpClustersOut"]:
        return

    formatted_message = "Zdp Command | %s | %s | %s " %(
        command, nwkid, cluster)
    if args:
        for arg in args:
            formatted_message += "| %s" %arg
        
    self.log.logging( "zdpCommand", "Log", formatted_message)
