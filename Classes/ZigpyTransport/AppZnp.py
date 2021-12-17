
import logging
import binascii
from typing import Any, Optional

import Domoticz
import zigpy.appdb
import zigpy.config
import zigpy.device
import zigpy.exceptions
import zigpy.group
import zigpy.ota
import zigpy.quirks
import zigpy.state
import zigpy.topology
import zigpy.types as t
import zigpy.util
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_zigate
import zigpy_zigate.zigbee.application
import zigpy_znp.zigbee.application
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)
    


class App_znp(zigpy_znp.zigbee.application.ControllerApplication):


    async def startup(self, callBackFunction, auto_form=False):
        self.callBackFunction = callBackFunction
        await super().startup(auto_form)

    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:
        
        
        #Domoticz.Log("handle_message %s" %(str(profile)))
        if sender.nwk is not None or sender.ieee is not None:
            Domoticz.Log("handle_message device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))
            Domoticz.Log("=====> Sender %s - %s" %(sender.nwk, sender.ieee))
            if sender.nwk:
                addr_mode = 0x02
                addr = sender.nwk
            elif sender.ieee:
                addr = str(sender.ieee).replace(':','')
                addr_mode = 0x03
            if sender.lqi == None:
                sender.lqi = 0x00
            plugin_frame = build_plugin_8002_frame_content( addr, profile, cluster, src_ep, dst_ep, message, sender.lqi,src_addrmode=addr_mode)
            Domoticz.Log("handle_message Sender: %s frame for plugin: %s" %( addr, plugin_frame))
            self.callBackFunction (plugin_frame)
        else:
            Domoticz.Log("handle_message Sender unkown device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))

        return None



#  handle_message Sender: 0x6A1D frame for plugin: 0180020016ff00010404020201021d6a02000018090a000029cd089c03
#  ZigateRead - MsgType: 8002,  Data: 00/0104/0402/02/01/02-1d6a/02000018090a000029cd08, LQI: 156
#  Decode8102 - Attribute Reports: [1d6a:02] MsgSQN: 09 ClusterID: 0402 AttributeID: 0000 Status: 00 Type: 29 Size: 0002 ClusterData: >08cd<
#  scan_attribute_reponse - 8102 idx: 28 Read Attribute Response: [1d6a:02] ClusterID: 0402 MsgSQN: 09, i_sqn: None, AttributeID: 0000 Status: 00 Type: 29 Size: 0002 ClusterData: >08cd<
#  Decode8102 - Receiving a message from unknown device: [1d6a:02] ClusterID: 0402 AttributeID: 0000 Status: 00 Type: 29 Size: 0002 ClusterData: >08cd< 

def build_plugin_8002_frame_content(address, profile, cluster, src_ep, dst_ep, message, lqi=0x00, receiver=0x0000, src_addrmode=0x02, dst_addrmode=0x02):

        
        payload = binascii.hexlify(message).decode('utf-8')
        ProfilID = "%04x" %profile
        ClusterID = "%04x" %cluster
        SourcePoint = "%02x" %src_ep
        DestPoint = "%02x" %dst_ep
        SourceAddressMode = "%02x" %src_addrmode
        if src_addrmode in ( 0x02, 0x01 ):
            SourceAddress = address
        elif src_addrmode == 0x03:
            SourceAddress = address
        DestinationAddressMode = "%02x" %dst_addrmode   
        DestinationAddress = "%04x" %0x0000
        Payload = payload

        Domoticz.Log("==> build_plugin_8002_frame_content - SourceAddr: %s message: %s" %( SourceAddress, message))
        frame_payload = "00" + ProfilID + ClusterID + SourcePoint + DestPoint + SourceAddressMode + SourceAddress
        frame_payload += DestinationAddressMode + DestinationAddress + Payload
        
        plugin_frame = "01"                                  # 0:2
        plugin_frame += "8002"                               # 2:4 MsgType 0x8002
        plugin_frame += "%04x" % ((len(frame_payload)//2)+1) # 6:10 lenght
        plugin_frame += "%02x" % 0xff                        # 10:12 CRC set to ff but would be great to  compute it
        plugin_frame += frame_payload
        plugin_frame += "%02x" %lqi
        plugin_frame += "03"
        return plugin_frame