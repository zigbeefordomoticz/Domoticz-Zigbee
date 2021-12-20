

import logging

from typing import Any, Optional
import datetime
import binascii
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
from Zigbee.plugin_encoders import build_plugin_004D_frame_content, build_plugin_8002_frame_content

LOGGER = logging.getLogger(__name__)
    

class App_zigate(zigpy_zigate.zigbee.application.ControllerApplication):
    
    async def new(
    cls, config: dict, auto_form: bool = False, start_radio: bool = True
    ) -> zigpy.application.ControllerApplication:
        logging.debug("new" )

    async def _load_db(self) -> None:
        logging.debug("_load_db" )
        
    async def startup(self, auto_form=False):
        await super().startup(auto_form)

    #async def startup(self, callBackFunction , auto_form=False):
    #    self.callBackFunction = callBackFunction
    #    await super().startup(auto_form)

    async def startup(self, callBackHandleMessage, callBackGetDevice=None, auto_form=False):
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        await super().startup(auto_form)

        
    def get_zigpy_version(self):
        return self.version

    def add_device(self, ieee, nwk):
        logging.debug("add_device %s" %str(nwk))
        
    def device_initialized(self, device):
        logging.debug("device_initialized")
        
    async def remove(self, ieee: t.EUI64) -> None:
        logging.debug("remove")
        
    def get_device(self, ieee=None, nwk=None):
        logging.debug("get_device")
        return zigpy.device.Device(self, ieee, nwk)
        
    def handle_leave(self, nwk, ieee):
        #super().handle_leave(nwk,ieee) 
        logging.debug("handle_leave %s" %str(nwk))

    def handle_join(self, nwk, ieee, parent_nwk, rejoin=None):
        #super().handle_join(nwk,ieee) 
        logging.debug("handle_join nwkid: %04x ieee: %s parent_nwk: %04x rejoin: %s" %(
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
        if sender.nwk or sender.ieee:
            logging.debug("=====> Sender %s - %s" %(sender.nwk, sender.ieee))
            if sender.nwk:
                addr_mode = 0x02
                addr = sender.nwk.serialize()[::-1].hex()
                logging.debug("=====> sender.nwk %s - %s" %(sender.nwk, addr))

            elif sender.ieee:
                addr = "%016x" %t.uint64_t.deserialize(self.app.ieee.serialize())[0]
                addr_mode = 0x03
                logging.debug("=====> sender.ieee %s - %s" %(sender.ieee, addr))
                
            if addr:
                logging.debug(" handle_message addr: %s profile: %s cluster: %04x src_ep: %02x dst_ep: %02x message: %s lqi: %02x" %(
                    addr, profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode('utf-8'), sender.lqi
                ))
                plugin_frame = build_plugin_8002_frame_content( addr, profile, cluster, src_ep, dst_ep, message, sender.lqi)
                logging.debug("handle_message Sender: %s frame for plugin: %s" %( addr, plugin_frame))
                self.callBackFunction (plugin_frame)
            else:
                logging.error("handle_message - Issue with addr: %s while sender is %s %s" %(addr, sender.nwk, sender.ieee))
        else:
            logging.error("handle_message Sender unkown device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))

        return None

    async def set_tx_power (self,power):
        await self._api.set_tx_power( power )

    async def set_led (self, mode):
        await self._api.set_led( mode )

    async def set_certification (self, mode):
        await self._api.set_certification( mode)

    async def get_time_server (self):
        await self._api.get_time_server()

    async def set_time_server (self, newtime):
        await self._api.set_time()
        
    async def get_firmware_version (self):
        pass
    
    async def erase_pdm(self):
        await self._api.erase_persistent_data()
        
    async def soft_reset(self):
        await self._api.reset()
