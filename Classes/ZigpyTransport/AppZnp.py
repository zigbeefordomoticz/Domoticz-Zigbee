#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#

import logging

import Classes.ZigpyTransport.AppGeneric
import zigpy.config as zigpy_conf
import zigpy.device
import zigpy.profiles
import zigpy.zdo.types as zdo_types
import zigpy_znp.commands.util
import zigpy_znp.config as znp_conf
import zigpy_znp.types as t
import zigpy_znp.zigbee.application
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL
from zigpy.zcl import clusters

LOGGER = logging.getLogger(__name__)

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")

    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)

    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)
        LOGGER.info("ZNP Configuration: %s", self.config)

    async def startup(self, HardwareID, pluginconf, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        # If set to != 0 (default) extended PanId will be use when forming the network.
        # If set to !=0 (default) channel will be use when formin the network
        self.log = log
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackGetDevice = callBackGetDevice
        self.callBackBackup = callBackBackup
        self.HardwareID = HardwareID
        self.znp_config[znp_conf.CONF_MAX_CONCURRENT_REQUESTS] = 2

        """
        Starts a network, optionally forming one with random settings if necessary.
        """

        try:
            await self.connect()
            await self.initialize(auto_form=True, force_form=force_form)
        except Exception as e:
            LOGGER.error("Couldn't start application", exc_info=e)
            await self.shutdown()
            raise

        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self.state.network_info
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))
        
        # Trigger Version payload to plugin
        znp_model = self.get_device(nwk=t.NWK(0x0000)).model
        znp_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer
        FirmwareBranch, FirmwareMajorVersion, FirmwareVersion = extract_versioning_for_plugin( znp_model, znp_manuf)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion))
        
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup( await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))


    async def shutdown(self) -> None:
        """Shutdown controller."""
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=True))
        await self.disconnect()


    async def register_endpoints(self):
        await super().register_endpoints()  

        LIST_ENDPOINT = [0x0b , 0x0a , 0x6e, 0x15, 0x08, 0x03]  # WISER, ORVIBO , TERNCY, KONKE, LIVOLO, WISER2
        for controller_ep in LIST_ENDPOINT:
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=controller_ep,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[clusters.general.Basic.cluster_id,],
                    output_clusters=[],
                )
            )

    def device_initialized(self, device):
            self.log.logging("TransportZigpy", "Log","device_initialized (0x%04x %s)" %(device.nwk, device.ieee))
            super().device_initialized(device)
     
        
    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)

    def handle_join(self, nwk: t.NWK, ieee: t.EUI64, parent_nwk: t.NWK) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_join(self, nwk, ieee, parent_nwk)

    def get_device_ieee(self, nwk):
        return Classes.ZigpyTransport.AppGeneric.get_device_ieee(self, nwk)
                  
    def handle_leave(self, nwk, ieee):
        Classes.ZigpyTransport.AppGeneric.handle_leave(self, nwk, ieee)

    def get_zigpy_version(self):
        return Classes.ZigpyTransport.AppGeneric.get_zigpy_version(self)

    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_message(self,sender,profile,cluster,src_ep,dst_ep,message)

    async def set_zigpy_tx_power(self, power):
        self.log.logging("TransportZigpy", "Debug", "set_tx_power %s" %power)
        await self.set_tx_power(dbm=power)

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

    async def set_extended_pan_id(self,extended_pan_ip):
        self.config[znp_conf.CONF_NWK][znp_conf.CONF_NWK_EXTENDED_PAN_ID] = extended_pan_ip
        self.startup(self.callBackFunction,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)

    async def set_channel(self,channel):
        self.config[znp_conf.CONF_NWK][znp_conf.CONF_NWK_EXTENDED_PAN_ID] = channel
        self.startup(self.callBackFunction,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)

    async def remove_ieee(self, ieee):
        await self.remove( ieee )

    async def coordinator_backup( self ):
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))

    def is_bellows(self):
        return False
    def is_znp(self):
        return True
    def is_deconz(self):
        return False
            
        
def extract_versioning_for_plugin( znp_model, znp_manuf):
    
    ZNP_330 = "CC1352/CC2652, Z-Stack 3.30+"
    ZNP_30X = "CC2531, Z-Stack 3.0.x"

    FirmwareBranch = next((ZNP_MODEL[x] for x in ZNP_MODEL if znp_model[: len(x)] == x), "99")

    year = znp_model[ znp_model.find("build") + 6 : -5 ]
    FirmwareMajorVersion = "%02d" %int(znp_model[ znp_model.find("build") + 8 : -5 ])
    FirmwareVersion = "%04d" %int(znp_model[ znp_model.find("build") + 10: -1])

    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion
