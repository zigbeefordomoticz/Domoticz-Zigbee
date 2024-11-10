#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import logging

import zigpy.config as zigpy_conf
import zigpy.device
import zigpy.profiles
import zigpy.types as zigpy_t
import zigpy.zdo.types as zdo_types
import zigpy_znp.commands.util
import zigpy_znp.config as znp_conf
import zigpy_znp.types as t
import zigpy_znp.zigbee.application
from zigpy.zcl import clusters

import Classes.ZigpyTransport.AppGeneric
from Classes.ZigpyTransport.firmwareversionHelper import \
    znp_extract_versioning_for_plugin
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL

LOGGER = logging.getLogger(__name__)

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")


    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)


    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)


    async def startup(self, statistics, HardwareID, pluginconf, use_of_zigpy_persistent_db, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, callBackRestartPlugin=None, captureRxFrame=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        """Starts a network, optionally forming one with random settings if necessary."""

        # If set to != 0 (default) extended PanId will be use when forming the network.
        # If set to !=0 (default) channel will be use when formin the network
        self.log = log
        self.statistics = statistics
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackGetDevice = callBackGetDevice
        self.callBackBackup = callBackBackup
        self.callBackRestartPlugin = callBackRestartPlugin
        self.HardwareID = HardwareID
        self.captureRxFrame = captureRxFrame
        self.use_of_zigpy_persistent_db = use_of_zigpy_persistent_db

        self.shutting_down = False
        self.restarting = False

        # Pipiche : 24-Oct-2022 Disabling CONF_MAX_CONCURRENT_REQUESTS so the default will be used ( 16 )
        # self.znp_config[znp_conf.CONF_MAX_CONCURRENT_REQUESTS] = 2

        try:
            await self.connect()
            await self.initialize(auto_form=True, force_form=force_form)
        except Exception as e:
            LOGGER.error("Couldn't start application", exc_info=e)
            await self.shutdown()
            raise

        self.log.logging("TransportZigpy", "Status", "++ ZNP Configuration %s" %self.config)
        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self.state.network_info
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))
        
        # Trigger Version payload to plugin
        
        version = self.state.node_info.version
        znp_model = self.state.node_info.model
        znp_manuf = self.state.node_info.manufacturer
        FirmwareBranch, FirmwareVersion, build = znp_extract_versioning_for_plugin( self, znp_model, znp_manuf, version)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, "000000", FirmwareVersion, "" ))

        self.log.logging("TransportZigpy", "Status", "++ ZNP Board Information" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio manufacturer : {znp_manuf}" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio board model  : {znp_model}" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio version      : {version}" )
       

    async def shutdown(self, *, db: bool = True) -> None:
        """Shutdown controller."""
        await Classes.ZigpyTransport.AppGeneric.shutdown(self, db=db)


    def connection_lost(self, exc: Exception) -> None:
        """Handle connection lost event."""
        Classes.ZigpyTransport.AppGeneric.connection_lost(self, exc)


    async def register_endpoints(self):
        self.log.logging("TransportZigpy", "Status", "++ ZNP Radio register default Ep")
        await super().register_endpoints()

        self.log.logging("TransportZigpy", "Status", "++ ZNP Radio register any additional/specific Ep")
        await Classes.ZigpyTransport.AppGeneric.register_specific_endpoints(self)

        
    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)


    def handle_join(self, nwk: t.NWK, ieee: t.EUI64, parent_nwk: t.NWK, *, handle_rejoin: bool = True,) -> None:
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


    async def network_interference_scan(self):
        await Classes.ZigpyTransport.AppGeneric.network_interference_scan(self)


    def get_topology(self):
        return self.topology.neighbors, self.topology.routes


    def is_zigpy_topology_in_progress(self):
        return Classes.ZigpyTransport.AppGeneric.is_zigpy_topology_in_progress(self)


    async def start_topology_scan(self):
        await self.topology.scan()


    def get_device_rssi(self, z4d_ieee=None, z4d_nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device_rssi(self, z4d_ieee, z4d_nwk)


    def is_bellows(self):
        return False


    def is_znp(self):
        return True


    def is_deconz(self):
        return False