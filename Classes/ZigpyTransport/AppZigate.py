

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
import zigpy.types as t
import zigpy.util
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_zigate
import zigpy_zigate.zigbee.application
from Modules.zigateCommands import (zigate_blueled,
                                    zigate_get_time, zigate_set_certificate,
                                    zigate_set_time, zigate_set_tx_power)
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)
from Zigbee.plugin_encoders import build_plugin_004D_frame_content, build_plugin_8002_frame_content

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
        Domoticz.Log("add_device %s" %str(nwk))
        
    def device_initialized(self, device):
        Domoticz.Log("device_initialized")
        
    async def remove(self, ieee: t.EUI64) -> None:
        Domoticz.Log("remove")
        
    def get_device(self, ieee=None, nwk=None):
        Domoticz.Log("get_device")
        return zigpy.device.Device(self, ieee, nwk)
        
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

    async def set_tx_power (self,power):
        pass

    async def set_led (self, mode):
        pass

    async def set_certification (self, mode):
        pass

    async def get_time_server (self):
        pass

    async def set_time_server (self):
        pass

    async def get_firmware_version (self):
        pass
