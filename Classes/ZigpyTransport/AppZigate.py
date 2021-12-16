
import binascii
import logging
from typing import Any, Optional
import struct

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
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)
    

class App_zigate(zigpy_zigate.zigbee.application.ControllerApplication):
    
    async def new(
    cls, config: dict, auto_form: bool = False, start_radio: bool = True
    ) -> zigpy.application.ControllerApplication:
        Domoticz.Log("new" )

    async def _load_db(self) -> None:
        Domoticz.Log("_load_db" )
        
    async def startup(self, auto_form=False):
        await super().startup(auto_form)
        
    def get_zigpy_version(self):
        return self.version

    def add_device(self, ieee, nwk):
        Domoticz.Log("add_device %s" %str(nwk))
        
    def device_initialized(self, device):
        Domoticz.Log("device_initialized")
        
    async def remove(self, ieee: t.EUI64) -> None:
        Domoticz.Log("remove")
        
    def get_device(self, ieee=None, nwk=None):
        Domoticz.Log("get_device")
        return zigpy.device.Device(self, ieee, nwk)
        
    #def zigate_callback_handler(self, msg, response, lqi):
    #    Domoticz.Log("zigate_callback_handler %04x %s" %(msg, response))
    

    def handle_leave(self, nwk, ieee):
        #super().handle_leave(nwk,ieee) 
        Domoticz.Log("handle_leave %s" %str(nwk))

    def handle_join(self, nwk, ieee, parent_nwk, rejoin=None):
        #super().handle_join(nwk,ieee) 
        Domoticz.Log("handle_join nwkid: %04x ieee: %s parent_nwk: %04x rejoin: %s" %(
            nwk, ieee, parent_nwk, rejoin))
        plugin_frame = build_plugin_004D_frame_content(nwk, ieee, parent_nwk)
        self.callBackFunction (plugin_frame)

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
            Domoticz.Log("=====> Sender %s - %s" %(sender.nwk, sender.ieee))
            if sender.nwk:
                addr_mode = 0x02
                addr = sender.nwk
            elif sender.ieee:
                addr = str(sender.ieee).replace(':','')
                addr_mode = 0x03
            
            plugin_frame = build_plugin_8002_frame_content( addr, profile, cluster, src_ep, dst_ep, message, sender.lqi)
            Domoticz.Log("handle_message Sender: %s frame for plugin: %s" %( addr, plugin_frame))
            self.callBackFunction (plugin_frame)
        else:
            Domoticz.Log("handle_message Sender unkown device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))

        return None

    def set_callback_message (self, callBackFunction):
        self.callBackFunction = callBackFunction


def build_plugin_004D_frame_content(nwk, ieee, parent_nwk):
    # No endian decoding as it will go directly to Decode004d
    nwk = "%04x" %nwk
    ieee = str(ieee).replace(':','')
    ieee = "%016x" %int(ieee,16)
    frame_payload = nwk + ieee + '00'
    
    plugin_frame = "01"                                  # 0:2
    plugin_frame += "004d"                               # 2:4 MsgType 0x8002
    plugin_frame += "%04x" % ((len(frame_payload)//2)+1) # 6:10 lenghts
    plugin_frame += "%02x" % 0xff                        # 10:12 CRC set to ff but would be great to  compute it
    plugin_frame += frame_payload
    plugin_frame += "%02x" %0x00
    plugin_frame += "03"
    return plugin_frame

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
            SourceAddress = "%04x" % address
        elif src_addrmode == 0x03:
            SourceAddress = "%016x" % address
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

