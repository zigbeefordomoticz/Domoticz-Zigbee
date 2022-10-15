#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: deufo, badz & pipiche38
#

import logging

import bellows.config as bellows_conf
import bellows.types as t
import bellows.zigbee.application
import Classes.ZigpyTransport.AppGeneric
import zigpy.config as zigpy_conf
import zigpy.device
from bellows.exception import EzspError
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL
from zigpy.types import Addressing

LOGGER = logging.getLogger(__name__)

class App_bellows(bellows.zigbee.application.ControllerApplication):
    
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")


    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)


    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)
        LOGGER.info("EZSP Configuration: %s", self.config)

    async def startup(self, HardwareID, pluginconf, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        # If set to != 0 (default) extended PanId will be use when forming the network.
        # If set to !=0 (default) channel will be use when formin the network
        self.log = log
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackBackup = callBackBackup
        self.HardwareID = HardwareID

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
        # await self.load_network_info( load_devices=False )   # load_devices shows nothing for now
        self.callBackFunction(build_plugin_8015_frame_content( self, self.state.network_info))
        
        # Trigger Version payload to plugin
        try:
            brd_manuf, brd_name, version = await self._ezsp.get_board_info()
            LOGGER.debug("EZSP Radio manufacturer: %s", brd_manuf)
            LOGGER.debug("EZSP Radio board name: %s", brd_name)
            LOGGER.debug("EmberZNet version: %s" %version)
            LOGGER.info("EZSP Configuration %s", self.config)
            
        except EzspError as exc:
            LOGGER.error("EZSP Radio does not support getMfgToken command: %s" %str(exc))

        FirmwareBranch, FirmwareMajorVersion, FirmwareVersion = extract_versioning_for_plugin(brd_manuf, brd_name, version)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion))
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup( await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))


    async def shutdown(self) -> None:
        """Shutdown controller."""
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=True))
        await self.disconnect()

    # Only needed if the device require simple node descriptor from the coordinator
    async def register_endpoint(self, endpoint=1):
        await super().add_endpoint(endpoint)


    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)

    def handle_join(self, nwk: t.EmberNodeId, ieee: t.EmberEUI64, parent_nwk: t.EmberNodeId) -> None:
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
        dst_addressing: Addressing,
    ) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_message(self,sender,profile,cluster,src_ep,dst_ep,message)

    async def set_zigpy_tx_power(self, power):
        # EmberConfigTxPowerMode - EZSP_CONFIG_TX_POWER_MODE in EzspConfigId
        # 0x00: Normal mode
        # 0x01: Enable boost power mode
        # 0x02: Enable the alternate transmitter output.
        # 0x03: Both 0x01 & 0x02
        if power > 0:
            await self._ezsp.setConfigurationValue(t.EzspConfigId.CONFIG_TX_POWER_MODE,1)    
            self.log.logging("TransportZigpy", "Debug", "set_tx_power: boost power mode")
        else:
            await self._ezsp.setConfigurationValue(t.EzspConfigId.CONFIG_TX_POWER_MODE,0)
            self.log.logging("TransportZigpy", "Debug", "set_tx_power: normal mode")

    async def set_led(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_led not available on EZSP")

    async def set_certification(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_certification not implemented yet")

    async def get_time_server(self):
        self.log.logging("TransportZigpy", "Debug", "get_time_server not implemented yet")

    async def set_time_server(self, newtime):
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")

    async def get_firmware_version(self):
        return self.bellows.version

    async def erase_pdm(self):
        pass

    async def set_extended_pan_id(self,extended_pan_ip):
        self.config[bellows_conf.CONF_NWK][bellows_conf.CONF_NWK_EXTENDED_PAN_ID] = extended_pan_ip
        await self._ezsp.leaveNetwork()
        await super().form_network()

    async def set_channel(self,channel):   # BE CAREFUL - NEW network formed 
        self.config[bellows_conf.CONF_NWK][bellows_conf.CONF_NWK_CHANNEL] = channel
        await self._ezsp.leaveNetwork()
        await super().form_network()
            
    async def remove_ieee(self, ieee):
        await self.remove( ieee )

    async def coordinator_backup( self ):
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))

    def is_bellows(self):
        return True
    def is_znp(self):
        return False
    def is_deconz(self):
        return False
    
def extract_versioning_for_plugin( brd_manuf, brd_name, version):
    FirmwareBranch = "98"   # Not found in the Table.
    if brd_manuf == 'Elelabs':
        if 'ELU01' in brd_name:
            FirmwareBranch = "31"
        elif 'ELR02' in brd_name:
            FirmwareBranch = "30" 
            
    # 6.10.3.0 build 297    
    FirmwareMajorVersion = (version[: 2])
    FirmwareMajorVersion = "%02d" %int(FirmwareMajorVersion.replace('.',''))
    FirmwareVersion = version[ 2:8]
    FirmwareVersion = FirmwareVersion.replace(' ','')
    FirmwareVersion = "%04d" %int(FirmwareVersion.replace('.',''))
        
    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion
