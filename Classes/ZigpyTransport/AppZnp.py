import binascii
import logging
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
import zigpy_znp.types as t
import zigpy.util
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_zigate.zigbee.application
import zigpy_znp.commands.util
import zigpy_znp.config as conf
import zigpy_znp.commands as c
import zigpy_znp.zigbee.application

from zigpy.zcl import clusters
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8010_frame_content)
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        logging.debug("new")

    async def _load_db(self) -> None:
        logging.debug("_load_db")

    async def startup(self, callBackHandleMessage, callBackGetDevice=None, auto_form=False, force_form=False, log=None, set_channel=0, set_extendedPanId=0):
        # If set to != 0 (default) extended PanId will be use when forming the network.
        # If set to !=0 (default) channel will be use when formin the network
        self.log = log
        self.callBackHandleMessage = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        await super().startup(auto_form=auto_form,force_form=force_form)

        # Trigger Version payload to plugin
        Model = "10"  # Zigpy
        FirmwareMajorVersion = "10"
        FirmwareVersion = "0400"
        self.callBackHandleMessage(build_plugin_8010_frame_content(Model, FirmwareMajorVersion, FirmwareVersion))


    async def _register_endpoints(self) -> None:
        LIST_ENDPOINT = [0x0b , 0x0a , 0x6e, 0x15, 0x08, 0x03] # WISER, ORVIBO , TERNCY, KONKE, LIVOLO, WISER2
        await super()._register_endpoints()

        for endpoint in LIST_ENDPOINT:
            await self._znp.request(
                c.AF.Register.Req(
                    Endpoint=endpoint,
                    ProfileId=zigpy.profiles.zha.PROFILE_ID,
                    DeviceId=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    DeviceVersion=0b0000,
                    LatencyReq=c.af.LatencyReq.NoLatencyReqs,
                    InputClusters=[clusters.general.Basic.cluster_id],
                    OutputClusters=[],
                ),
                RspStatus=t.Status.SUCCESS,
            )



    def get_device(self, ieee=None, nwk=None):
        # logging.debug("get_device nwk %s ieee %s" % (nwk, ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)

        dev = None
        try:
            dev = super().get_device(ieee, nwk)
            
        except KeyError:
            if self.callBackGetDevice:
                if nwk is not None:
                    nwk = nwk.serialize()[::-1].hex()
                if ieee is not None:
                    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
                self.log.logging("TransportZigpy", "Debug", "get_device calling  callBackGetDevice %s (%s) %s (%s)" % (ieee,type(ieee),nwk, type(nwk)))
                zfd_dev = self.callBackGetDevice(ieee, nwk)
                if zfd_dev is not None:
                    (nwk, ieee) = zfd_dev
                    dev = zigpy.device.Device(self, t.EUI64(t.uint64_t(ieee).serialize()), nwk) 
                    self.log.logging("TransportZigpy", "Debug", "get_device %s" % dev)

        if dev is not None:
            # logging.debug("found device dev: %s" % (str(dev)))
            return dev
        
        logging.debug("get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
        raise KeyError

    def get_zigpy_version(self):
        # This is a fake version number. This is just to inform the plugin that we are using ZNP over Zigpy
        logging.debug("get_zigpy_version ake version number. !!")
        return self.version

    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:
        if sender.nwk == 0x0000:
            self.log.logging("TransportZigpy", "Error", "handle_message from Controller Sender: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
                str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
            #if cluster != 0x8031: # why 8031 ??
            super().handle_message(sender, profile, cluster, src_ep, dst_ep, message)

        if sender.nwk  or sender.ieee:
            self.log.logging(
                "TransportZigpy",
                "Debug",
                "handle_message device 1: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                    str(sender), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi)),

            if sender.nwk:
                addr_mode = 0x02
                addr = sender.nwk.serialize()[::-1].hex()
                
            elif sender.ieee:
                addr = "%016x" % t.uint64_t.deserialize(sender.ieee.serialize())[0]
                addr_mode = 0x03
                
            if sender.lqi is None:
                sender.lqi = 0x00
            if src_ep == dst_ep == 0x00:
                profile = 0x0000

            self.log.logging(
                "TransportZigpy",
                "Debug",
                "handle_message device 2: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                    str(addr),  profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi),
            )
            plugin_frame = build_plugin_8002_frame_content(self, addr, profile, cluster, src_ep, dst_ep, message, sender.lqi, src_addrmode=addr_mode)
            self.log.logging("TransportZigpy", "Debug", "handle_message Sender: %s frame for plugin: %s" % (addr, plugin_frame))
            self.callBackHandleMessage(plugin_frame)
        else:
            self.log.logging(
                "TransportZigpy",
                "Error",
                "handle_message Sender unkown device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" % (
                    str(sender), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")),
            )

        return

    async def set_tx_power(self, power):
        self.log.logging("TransportZigpy", "Debug", "set_tx_power not implemented yet")
        # something to fix here
        # await self.set_tx_power(dbm=power)

    async def set_led(self, mode):
        if mode == 1:
            await self._set_led_mode(led=0xFF, mode=zigpy_znp.commands.util.LEDMode.ON)
        else:
            await self._set_led_mode(led=0xFF, mode=zigpy_znp.commands.util.LEDMode.OFF)

    async def set_certification(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_certification not implemented yet")

    async def get_time_server(self):
        self.log.logging("TransportZigpy", "Debug", "get_time_server not implemented yet")

    async def set_time_server(self, newtime):
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")

    async def get_firmware_version(self):
        return self.znp.version

    async def erase_pdm(self):
        pass
        
    async def set_extended_pan_id (self,extended_pan_ip):
        self.confif[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = extended_pan_ip
        self.startup(self.callBackHandleMessage,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)

    async def set_channel (self,channel):
        self.confif[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] =  channel
        self.startup(self.callBackHandleMessage,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)


