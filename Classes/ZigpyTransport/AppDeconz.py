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

import zigpy.config as zigpy_conf
import zigpy.device
import zigpy.types as t
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_deconz
import zigpy_deconz.zigbee.application

import Classes.ZigpyTransport.AppGeneric
from Classes.ZigpyTransport.firmwareversionHelper import \
    deconz_extract_versioning_for_plugin
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)

LOGGER = logging.getLogger(__name__)

class App_deconz(zigpy_deconz.zigbee.application.ControllerApplication):
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")


    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)


    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)


    async def startup(self, statistics, HardwareID, pluginconf, use_of_zigpy_persistent_db, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, callBackRestartPlugin=None, captureRxFrame=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        """Starts a network, optionally forming one with random settings if necessary."""

        self.log = log
        self.statistics = statistics
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackBackup = callBackBackup
        self.callBackRestartPlugin = callBackRestartPlugin
        self.HardwareID = HardwareID
        self.captureRxFrame = captureRxFrame
        self.use_of_zigpy_persistent_db = use_of_zigpy_persistent_db

        self.shutting_down = False
        self.restarting = False
        self.radio_lost_cnt = 0

        await asyncio.sleep( 3 )

        try:
            await self.connect()
            await asyncio.sleep( 1 )
            await self.initialize(auto_form=True, force_form=force_form)

        except Exception as e:
            LOGGER.error("Couldn't start application", exc_info=e)
            await self.shutdown()
            raise

        self.log.logging("TransportZigpy", "Status", "++ deConz Configuration %s" %self.config)
        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self.state.network_info

        # deConz doesn't have such capabilities to provided list of paired devices.
        LOGGER.info("startup Network Info: %s" %str(network_info))
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))

        version = int(self.state.node_info.version,16)

        # Trigger Version payload to plugin
        deconz_model = self.get_device(nwk=t.NWK(0x0000)).model
        deconz_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer
        
        self.log.logging("TransportZigpy", "Status", "++ deConz Board Information" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio manufacturer : {deconz_manuf}" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio board model  : {deconz_model}" )
        self.log.logging("TransportZigpy", "Status", f"++   Radio version      : {version}" )

        branch, version = deconz_extract_versioning_for_plugin( self, deconz_model, deconz_manuf, version)

        self.callBackFunction(build_plugin_8010_frame_content( branch, "00", "0000", version))


    async def shutdown(self, *, db: bool = True) -> None:
        """Shutdown controller."""
        await Classes.ZigpyTransport.AppGeneric.shutdown(self, db=db)


    def connection_lost(self, exc: Exception) -> None:
        """Handle connection lost event."""
        Classes.ZigpyTransport.AppGeneric.connection_lost(self, exc)


    async def register_endpoints(self):
        self.log.logging("TransportZigpy", "Status", "++ deConz Radio register default Ep")
        await super().register_endpoints()

        LOGGER.info("Adding any additional and specific Endpoints ")
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


    def packet_received(self, packet: t.ZigbeePacket) -> None:
        return Classes.ZigpyTransport.AppGeneric.packet_received(self,packet)


    async def set_zigpy_tx_power(self, power):
        pass
        #await self._api.set_tx_power(power)


    async def set_led(self, mode):
        pass
        #await self._api.set_led(mode)


    async def set_certification(self, mode):
        pass
        #await self._api.set_certification(mode)


    async def get_time_server(self):
        pass
        #await self._api.get_time_server()


    async def set_time_server(self, newtime):
        pass
        #await self._api.set_time()


    async def get_firmware_version(self):
        pass


    async def erase_pdm(self):
        pass


    async def soft_reset(self):
        pass


    async def set_extended_pan_id(self, extended_pan_ip): 
        pass 


    async def set_channel(self):
        pass        


    async def remove_ieee(self, ieee):
        pass


    async def coordinator_backup( self ):
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))


    async def network_interference_scan(self):
        await Classes.ZigpyTransport.AppGeneric.network_interference_scan(self)


    def get_topology(self):
        return self.topology.neighbors, self.topology.routes


    def is_zigpy_topology_in_progress(self):
        return Classes.ZigpyTransport.AppGeneric.is_zigpy_topology_in_progress(self)


    def get_device_rssi(self, z4d_ieee=None, z4d_nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device_rssi(self, z4d_ieee, z4d_nwk)


    async def start_topology_scan(self):
        await self.topology.scan()


    def is_bellows(self):
        return False

    
    def is_znp(self):
        return False

    
    def is_deconz(self):
        return True
