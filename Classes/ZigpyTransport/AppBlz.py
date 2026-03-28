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

import asyncio
import logging
import time

import zigpy.application
import zigpy.config as zigpy_conf
import zigpy.types as zigpy_t
import zigpy_blz.zigbee.application

import Classes.ZigpyTransport.AppGeneric
from Classes.ZigpyTransport.firmwareversionHelper import \
    blz_extract_versioning_for_plugin
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)

LOGGER = logging.getLogger(__name__)

class App_blz(zigpy_blz.zigbee.application.ControllerApplication):
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

        self.start_time = time.time()

        self.shutting_down = False
        self.restarting = False
        self.current_error = None

        await asyncio.sleep( 3 )
        
        # Pipiche : 24-Oct-2022 Disabling CONF_MAX_CONCURRENT_REQUESTS so the default will be used ( 16 )
        # self.blz_config[blz_conf.CONF_MAX_CONCURRENT_REQUESTS] = 2

        try:
            await self.connect()
            await self.initialize(auto_form=True, force_form=force_form)

        except Exception as e:
            LOGGER.error("Couldn't start application", exc_info=e)
            await self.shutdown()
            raise

        self.log.logging("TransportZigpy", "Status", "++ BLZ Configuration %s" %self.config)
        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self.state.network_info
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))
        
        # Trigger Version payload to plugin
        
        version = self.state.node_info.version
        blz_model = self.state.node_info.model  # "BL706"
        blz_manuf = self.state.node_info.manufacturer  # "Bouffalo Lab"

        branch, version = blz_extract_versioning_for_plugin( self, blz_model, blz_manuf, version)
        self.callBackFunction(build_plugin_8010_frame_content( branch, "00", "0000", version))


        self.log.logging("TransportZigpy", "Status", "++ BLZ Board Information" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio manufacturer : {blz_manuf}" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio board model  : {blz_model}" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio version      : {version}" )
  

    async def shutdown(self, *, db: bool = True) -> None:
        """Shutdown controller."""
        LOGGER.info("AppBlz shutdown called")
        await Classes.ZigpyTransport.AppGeneric.shutdown(self, db=db)


    def connection_lost(self, exc: Exception) -> None:
        """Handle connection lost event."""
        Classes.ZigpyTransport.AppGeneric.connection_lost(self, exc)


    async def register_endpoints(self):
        self.log.logging("TransportZigpy", "Status", "++ BLZ Radio register default Ep")
        await super().register_endpoints()

        self.log.logging("TransportZigpy", "Status", "++ BLZ Radio register any additional/specific Ep")
        await Classes.ZigpyTransport.AppGeneric.register_specific_endpoints(self)

        
    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)


    def handle_join(self, nwk: zigpy_t.NWK, ieee: zigpy_t.EUI64, parent_nwk: zigpy_t.NWK, *, handle_rejoin: bool = True,) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_join(self, nwk, ieee, parent_nwk, handle_rejoin=handle_rejoin)


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
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")


    async def set_led(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")


    async def set_certification(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_certification not implemented yet")


    async def get_time_server(self):
        self.log.logging("TransportZigpy", "Debug", "get_time_server not implemented yet")


    async def set_time_server(self, newtime):
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")


    async def get_firmware_version(self):
        return self.blz.version


    async def erase_pdm(self):
        pass

    
    async def set_extended_pan_id(self,extended_pan_ip):
        """Set the extended PAN ID for the network."""
        self.config[zigpy_conf.CONF_NWK][zigpy_conf.CONF_NWK_EXTENDED_PAN_ID] = extended_pan_ip
        self.startup(self.callBackFunction,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)


    async def set_channel(self,channel):
        """Set the channel for the network."""
        self.config[zigpy_conf.CONF_NWK][zigpy_conf.CONF_NWK_EXTENDED_PAN_ID] = channel
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
        return False


    def is_deconz(self):
        return False


    def is_blz(self):
        return True
