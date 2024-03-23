#!/usr/bin/env python3btt.
# coding: utf-8 -*-
#
# Author: deufo, badz & pipiche38
#

import collections
import logging

import bellows.config as bellows_conf
import bellows.types as t
import bellows.zigbee.application
import zigpy.config as zigpy_conf
import zigpy.device
import zigpy.types as zigpy_t
import zigpy.zdo.types as zdo_types
from bellows.exception import EzspError

import Classes.ZigpyTransport.AppGeneric
from Classes.ZigpyTransport.firmwareversionHelper import \
    bellows_extract_versioning_for_plugin
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL

LOGGER = logging.getLogger(__name__)

class App_bellows(bellows.zigbee.application.ControllerApplication):
    
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")


    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)


    def _add_db_listeners(self):
        Classes.ZigpyTransport.AppGeneric._add_db_listeners(self)


    def _remove_db_listeners(self):
        Classes.ZigpyTransport.AppGeneric._remove_db_listeners(self)


    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)
        LOGGER.info("EZSP Configuration: %s", self.config)


    async def startup(self, HardwareID, pluginconf, use_of_zigpy_persistent_db, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, captureRxFrame=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
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
        self.captureRxFrame = captureRxFrame
        self.use_of_zigpy_persistent_db = use_of_zigpy_persistent_db

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

        self.log.logging("TransportZigpy", "Log", "EZSP Configuration %s" %self.config)
        
        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        # await self.load_network_info( load_devices=False )   # load_devices shows nothing for now
        self.callBackFunction(build_plugin_8015_frame_content( self, self.state.network_info))
        
        # Trigger Version payload to plugin
        try:
            brd_manuf, brd_name, version = await self._ezsp.get_board_info()
            self.log.logging("TransportZigpy", "Status", "EZSP Radio manufacturer: %s" %brd_manuf)
            self.log.logging("TransportZigpy", "Status", "EZSP Radio board name: %s" %brd_name)
            self.log.logging("TransportZigpy", "Status", "EmberZNet version: %s" %version)
            
        except EzspError as exc:
            LOGGER.error("EZSP Radio does not support getMfgToken command: %s" %str(exc))

        FirmwareBranch, FirmwareMajorVersion, FirmwareVersion = bellows_extract_versioning_for_plugin(self, brd_manuf, brd_name, version)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion,version))
        
        #if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
        #    self.callBackBackup( await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))

        # Makes 0x0000 default Lightlink group , used by Ikea
        coordinator = self.get_device(self.state.node_info.ieee)
        if self.pluginconf.pluginConf["zigatePartOfGroup0000"]:
            # Add Zigate NwkId 0x0000 Ep 0x01 to GroupId 0x0000
            status = await coordinator.add_to_group( 0x0000, name="Default Lightlink Group", )

        if self.pluginconf.pluginConf["zigatePartOfGroupTint"]:
            # Tint Remote manage 4 groups and we will create with ZiGate attached.
            status = await coordinator.add_to_group( 0x4003, name="Default Tint Group 4003", )
            status = await coordinator.add_to_group( 0x4004, name="Default Tint Group 4004", )
            status = await coordinator.add_to_group( 0x4005, name="Default Tint Group 4005", )
            status = await coordinator.add_to_group( 0x4006, name="Default Tint Group 4006", )

            
    async def shutdown(self) -> None:
        """Shutdown controller."""
        await Classes.ZigpyTransport.AppGeneric.shutdown(self)


    async def register_endpoints(self, endpoint=1):
        # Only needed if the device require simple node descriptor from the coordinator
        self.log.logging("TransportZigpy", "Status", "Bellows Radio register default Ep")
        await self.add_endpoint(
            zdo_types.SimpleDescriptor(
                endpoint=1,
                profile=zigpy.profiles.zha.PROFILE_ID,
                device_type=zigpy.profiles.zha.DeviceType.IAS_CONTROL,
                device_version=0b0000,
                input_clusters=[
                    zigpy.zcl.clusters.general.Basic.cluster_id,
                    zigpy.zcl.clusters.general.OnOff.cluster_id,
                    zigpy.zcl.clusters.general.Groups.cluster_id,
                    zigpy.zcl.clusters.general.Scenes.cluster_id,
                    zigpy.zcl.clusters.general.Time.cluster_id,
                    zigpy.zcl.clusters.general.Ota.cluster_id,
                    zigpy.zcl.clusters.security.IasAce.cluster_id,
                ],
                output_clusters=[
                    zigpy.zcl.clusters.general.PowerConfiguration.cluster_id,
                    zigpy.zcl.clusters.general.PollControl.cluster_id,
                    zigpy.zcl.clusters.security.IasZone.cluster_id,
                    zigpy.zcl.clusters.security.IasWd.cluster_id,
                ],
            )
        )


    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)


    def handle_join(self, nwk: t.EmberNodeId, ieee: t.EmberEUI64, parent_nwk: t.EmberNodeId, *, handle_rejoin: bool = True,) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_join(self, nwk, ieee, parent_nwk)

            
    def get_device_ieee(self, nwk):
        return Classes.ZigpyTransport.AppGeneric.get_device_ieee(self, nwk)


    def handle_leave(self, nwk, ieee):
        Classes.ZigpyTransport.AppGeneric.handle_leave(self, nwk, ieee)


    def handle_relays(self, nwk, relays) -> None:
        Classes.ZigpyTransport.AppGeneric.handle_relays(self, nwk, relays)


    def get_zigpy_version(self):
        return Classes.ZigpyTransport.AppGeneric.get_zigpy_version(self)


    def packet_received(self, packet: zigpy_t.ZigbeePacket) -> None:
        return Classes.ZigpyTransport.AppGeneric.packet_received(self,packet)


    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
        * ,
        dst_addressing=None,
    )->None:
        return Classes.ZigpyTransport.AppGeneric.handle_message(self,sender,profile,cluster,src_ep,dst_ep,message, dst_addressing=dst_addressing)


    async def set_zigpy_tx_power(self, power):
        # EmberConfigTxPowerMode - EZSP_CONFIG_TX_POWER_MODE in EzspConfigId
        # 0x00: Normal mode
        # 0x01: Enable boost power mode
        # 0x02: Enable the alternate transmitter output.
        # 0x03: Both 0x01 & 0x02
        if power > 0:
            await self._ezsp.setConfigurationValue(0x17,0x03)    
            self.log.logging("TransportZigpy", "Debug", "set_tx_power: boost power mode")
        else:
            await self._ezsp.setConfigurationValue(0x17,0)
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


    async def network_interference_scan(self):
        await Classes.ZigpyTransport.AppGeneric.network_interference_scan(self)


    def get_topology(self):
        return self.topology.neighbors, self.topology.routes


    def is_bellows(self):
        return True


    def is_znp(self):
        return False


    def is_deconz(self):
        return False
