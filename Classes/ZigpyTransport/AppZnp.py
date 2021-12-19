
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
import zigpy_znp.commands.util
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)
    


class App_znp(zigpy_znp.zigbee.application.ControllerApplication):

    async def new(
    cls, config: dict, auto_form: bool = False, start_radio: bool = True
    ) -> zigpy.application.ControllerApplication:
        Domoticz.Log("new" )

    async def _load_db(self) -> None:
        Domoticz.Log("_load_db" )
        
    #async def startup(self, auto_form=False):
    #    await super().startup(auto_form)


    async def startup(self, callBackHandleMessage, callBackGetDevice=None, auto_form=False):
        self.callBackHandleMessage = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        await super().startup(auto_form)


    def get_device(self, ieee=None, nwk=None):

        Domoticz.Log("get_device nwk %s ieee %s" %(nwk,ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return nwkid, ieee if found ( nwkid and ieee are numbers)
        
        dev = None
        try :
            dev = super().get_device(ieee,nwk)
        except KeyError:
            if self.callBackGetDevice:
                dev = self.callBackGetDevice (ieee , nwk)

        if dev is not None:
            Domoticz.Log("found device dev: %s" %(str(dev)))
            return dev 

        raise KeyError

#    def handle_join(self, nwk, ieee, parent_nwk):
#        super().handle_join(nwk,ieee) 
#        Domoticz.Log("handle_join nwkid: %04x ieee: %s parent_nwk: %s" %(
#            nwk, ieee, parent_nwk))
#        plugin_frame = build_plugin_004D_frame_content(nwk, ieee, parent_nwk)
#        self.callBackFunction (plugin_frame)


        
    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:
        if sender.nwk is not None and sender.nwk == 0x0000 :
            return super().handle_message (sender, profile,cluster,src_ep,dst_ep,message)

        #Domoticz.Log("handle_message %s" %(str(profile)))
        if sender.nwk is not None or sender.ieee is not None:
            Domoticz.Log("handle_message device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))
            Domoticz.Log("=====> Sender %s - %s" %(sender.nwk, sender.ieee))
            if sender.nwk is not None:
                addr_mode = 0x02
                addr = sender.nwk.serialize()[::-1].hex()
                Domoticz.Log("=====> sender.nwk %s - %s" %(sender.nwk, addr))

            elif sender.ieee is not None:
                addr = str(sender.ieee).replace(':','')
                addr_mode = 0x03
            if sender.lqi is None:
                sender.lqi = 0x00
            if src_ep == dst_ep == 0x00:
                profile = 0x0000
            Domoticz.Log("handle_message device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(addr), profile, cluster, src_ep, dst_ep, str(message)))                
            plugin_frame = build_plugin_8002_frame_content( addr, profile, cluster, src_ep, dst_ep, message, sender.lqi,src_addrmode=addr_mode)
            Domoticz.Log("handle_message Sender: %s frame for plugin: %s" %( addr, plugin_frame))
            self.callBackHandleMessage (plugin_frame)
        else:
            Domoticz.Log("handle_message Sender unkown device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))

        return None

    async def set_tx_power (self,power):
        pass
        # something to fix here
        # await self.set_tx_power(dbm=power)

    async def set_led (self, mode):
        if mode == 1:
            await self._set_led_mode(led=0xFF, mode= zigpy_znp.commands.util.LEDMode.ON)
        else :
            await self._set_led_mode(led=0xFF, mode= zigpy_znp.commands.util.LEDMode.OFF)

    async def set_certification (self, mode):
        Domoticz.Log ("set_certification not implemented yet") 
        pass

    async def get_time_server (self):
        Domoticz.Log ("get_time_server not implemented yet")         
        pass

    async def set_time_server (self):
        Domoticz.Log ("set_time_server not implemented yet") 
        pass

    async def get_firmware_version (self):
        return self.znp.version


def build_plugin_004D_frame_content(nwk, ieee, parent_nwk):
    # No endian decoding as it will go directly to Decode004d
    nwk = "%04x" %nwk
    #ieee = str(ieee).replace(':','')
    #ieee = "%016x" %int(ieee,16)
    ieee = "%016x" %t.uint64_t.deserialize(ieee.serialize())[0]
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
            SourceAddress = address
        elif src_addrmode == 0x03:
            SourceAddress = address
        DestinationAddressMode = "%02x" %dst_addrmode   
        DestinationAddress = "%04x" %0x0000
        Payload = payload

        Domoticz.Log("==> build_plugin_8002_frame_content - SourceAddr: %s message: %s" %( SourceAddress, binascii.hexlify(message).decode('utf-8')))
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
