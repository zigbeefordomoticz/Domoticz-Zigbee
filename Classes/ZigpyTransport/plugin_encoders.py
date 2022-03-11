# coding: utf-8 -*-
#
# Author: pipiche38
#

import binascii
import time

import zigpy.types as t
from Zigbee.encoder_tools import encapsulate_plugin_frame


def build_plugin_004D_frame_content(self, nwk, ieee, parent_nwk):  # join indication
    # No endian decoding as it will go directly to Decode004d
    self.log.logging("TransportPluginEncoder", "Debug", "build_plugin_004D_frame_content %s %s %s" % (nwk, ieee, parent_nwk))

    nwk = "%04x" % nwk
    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
    frame_payload = nwk + ieee + "00"

    return encapsulate_plugin_frame("004d", frame_payload, "%02x" % 0x00)


def build_plugin_0302_frame_content(self,):
    # That correspond to PDM loaded on ZiGate (after a restart or a power Off/On)
    return encapsulate_plugin_frame("0302", "", "%02x" % 0x00)


def build_plugin_8002_frame_content(
    self,
    address,
    profile,
    cluster,
    src_ep,
    dst_ep,
    message,
    lqi=0x00,
    receiver=0x0000,
    src_addrmode=0x02,
    dst_addrmode=0x02,
):
    self.log.logging(
        "TransportPluginEncoder",
        "Debug",
        "build_plugin_8002_frame_content %s %s %s %s %s %s %s %s %s %s" % (address, profile, cluster, src_ep, dst_ep, message, lqi, receiver, src_addrmode, dst_addrmode),
    )

    payload = binascii.hexlify(message).decode("utf-8")
    ProfilID = "%04x" % profile
    ClusterID = "%04x" % cluster
    SourcePoint = "%02x" % src_ep
    DestPoint = "%02x" % dst_ep
    SourceAddressMode = "%02x" % src_addrmode
    if src_addrmode in (0x02, 0x01):
        SourceAddress = address
    elif src_addrmode == 0x03:
        SourceAddress = address
    DestinationAddressMode = "%02x" % dst_addrmode
    DestinationAddress = "%04x" % 0x0000
    Payload = payload

    self.log.logging(
        "TransportPluginEncoder",
        "Debug",
        "==> build_plugin_8002_frame_content - SourceAddr: %s message: %s" % (SourceAddress, message),
    )
    frame_payload = "00" + ProfilID + ClusterID + SourcePoint + DestPoint + SourceAddressMode + SourceAddress
    frame_payload += DestinationAddressMode + DestinationAddress + Payload

    return encapsulate_plugin_frame("8002", frame_payload, "%02x" % lqi)


def build_plugin_8009_frame_content(self, radiomodule):
    # addr = MsgData[0:4]
    # extaddr = MsgData[4:20]
    # PanID = MsgData[20:24]
    # extPanID = MsgData[24:40]
    # Channel = MsgData[40:42]

    # Get Network State
    self.log.logging(
        "TransportPluginEncoder",
        "Debug",
        "build_plugin_8009_frame_content %s %s %s %s %s" % (self.app.nwk, self.app.ieee, self.app.extended_pan_id, self.app.pan_id, self.app.channel),
    )
    ieee = "%016x" % t.uint64_t.deserialize(self.app.ieee.serialize())[0]
    ext_panid = "%016x" % t.uint64_t.deserialize(self.app.extended_pan_id.serialize())[0]

    frame_payload = "%04x" % self.app.nwk
    frame_payload += ieee
    frame_payload += "%04x" % self.app.pan_id
    frame_payload += ext_panid
    frame_payload += "%02x" % self.app.channel
    return encapsulate_plugin_frame("8009", frame_payload, "00")


def build_plugin_8010_frame_content(Branch, Major, Version):
    # Version
    return encapsulate_plugin_frame("8010", Branch + Major + Version, "00")


def build_plugin_8011_frame_content(self, nwkid, status, lqi):
    # MsgStatus = MsgData[0:2]
    # MsgSrcAddr = MsgData[2:6]
    # MsgSEQ = MsgData[12:14] if MsgLen > 12 else None
    
    lqi = lqi or 0x00
    frame_payload = "%02x" % status + nwkid
    return encapsulate_plugin_frame("8011", frame_payload, "%02x" % lqi)

def build_plugin_8014_frame_content(self, nwkid, payload):
    # Return status = 0x00 if not in pairing mode
    #        status = 0x01 if in pairing mode
    status = payload[2:4]
    if status != "00":
        buildPayload = status
    else:
        self.log.logging( "TransportPluginEncoder", "Debug", "build_plugin_8014_frame_content Nwkid: %s Timer: %s" %( nwkid, self.permit_to_join_timer))
        buildPayload = "00"
        if ( 
            self.permit_to_join_timer["Timer"] 
            and self.permit_to_join_timer["Duration"]
            and (self.permit_to_join_timer["Timer"] + self.permit_to_join_timer["Duration"]) > time.time()
        ):
            buildPayload = "01"
    return encapsulate_plugin_frame("8014", buildPayload, "00")
    
def build_plugin_8015_frame_content( self, network_info):
    # Get list of active devices
    self.log.logging( "TransportPluginEncoder", "Debug", "build_plugin_8015_frame_content key_table %s" %str(network_info))
    buildPayload = ""
    id = 0
    for ieee, nwk in network_info.nwk_addresses.items():
            self.log.logging( "TransportPluginEncoder", "Debug", "build_plugin_8015_frame_content nwk_addresses : ieee: %s nwk_addr: %s" %(
                ieee.serialize()[::-1].hex(),
                nwk.serialize()[::-1].hex(),
            ))
            buildPayload += "%02x" %id + "%04x" %int(nwk.serialize()[::-1].hex(),16 ) + "%016x" %int( ieee.serialize()[::-1].hex(), 16) + "ff" + "00"
    return encapsulate_plugin_frame("8015", buildPayload, "00")


def build_plugin_8043_frame_list_node_descriptor( self, epid, simpledescriptor):
    self.log.logging( "TransportPluginEncoder", "Debug", "build_plugin_8043_frame_list_node_descriptor %s %s" % ( epid, simpledescriptor))

    buildPayload = "00" + "00" + "0000" + "01"
    buildPayload += "%02x" %epid
    buildPayload += "%04x" %simpledescriptor.profile_id
    buildPayload += "%04x" %simpledescriptor.device_type
    buildPayload += "00"

    buildPayload += "%02x" %len(simpledescriptor.in_clusters)
    for in_cluster in simpledescriptor.in_clusters:
        buildPayload += "%04x" %in_cluster

    buildPayload += "%02x" %len(simpledescriptor.out_clusters)   
    for out_clusters in simpledescriptor.out_clusters:
        buildPayload += "%04x" %out_clusters
    return encapsulate_plugin_frame("8043", buildPayload, "00")


def build_plugin_8045_frame_list_controller_ep( self, ):
    nbEp = "%02x" %len((self.app.get_device(nwk=t.NWK(0x0000)).endpoints.keys()))
    self.log.logging( "TransportPluginEncoder", "Debug", "build_plugin_8045_frame_list_controller_ep %s %s" % ( nbEp, type(nbEp)))
    ep_list = "".join(
        "%02x" % ep_id
        for ep_id in self.app.get_device(nwk=t.NWK(0x0000)).endpoints.keys()
    )

    self.log.logging(
        "TransportPluginEncoder",
        "Debug",
        "build_plugin_8045_frame_list_controller_ep %s %s" % (
            nbEp, ep_list)  )

    buildPayload = "00" + "00" + "0000" + nbEp + ep_list
    return encapsulate_plugin_frame("8045", buildPayload, "00")   


def build_plugin_8047_frame_content(self, nwkid, payload):  # leave response
    self.log.logging("TransportPluginEncoder", "Debug", "build_plugin_8047_frame_content %s leave response %s" % ( nwkid, payload))
    frame_payload = payload
    return encapsulate_plugin_frame("8047", frame_payload, "%02x" %0x00 )


def build_plugin_8048_frame_content(self, ieee):  # leave indication
    
    self.log.logging("TransportPluginEncoder", "Debug", "build_plugin_8048_frame_content %s leave_indication" % ( ieee))

    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
    frame_payload = ieee
    frame_payload += "00"  # rejoin
    frame_payload += "00"  # remove children

    return encapsulate_plugin_frame("8048", frame_payload, "%02x" % 0x00)    
