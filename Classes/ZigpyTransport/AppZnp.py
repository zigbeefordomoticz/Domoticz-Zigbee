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
import zigpy_znp.commands as c
import zigpy_znp.commands.util
import zigpy_znp.config as znp_conf
import zigpy_znp.types as t
import zigpy_znp.zigbee.application

import Classes.ZigpyTransport.AppGeneric
from Classes.ZigpyTransport.firmwareversionHelper import \
    znp_extract_versioning_for_plugin
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8010_frame_content, build_plugin_8015_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL

# Green Power endpoint and Green Power group (GP spec A.3.3.2.2, A.3.5.2.1). zigpy
# only has them from 2.4 on (zigpy.zgp.types), so they are repeated here.
GP_ENDPOINT = 0xF2
GP_GROUP_ID = 0x0B84

LOGGER = logging.getLogger(__name__)

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")


    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)


    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)


    async def startup(self, statistics, HardwareID, pluginconf, use_of_zigpy_persistent_db, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackGetAllDevices=None, callBackBackup=None, callBackRestartPlugin=None, callBackHeartbeat=None, captureRxFrame=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
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
        self.callBackGetAllDevices = callBackGetAllDevices
        self.callBackBackup = callBackBackup
        self.callBackRestartPlugin = callBackRestartPlugin
        self.callBackHeartbeat = callBackHeartbeat
        self.HardwareID = HardwareID
        self.captureRxFrame = captureRxFrame
        self.use_of_zigpy_persistent_db = use_of_zigpy_persistent_db

        self.start_time = time.time()

        self.shutting_down = False
        self.restarting = False
        self.current_error = None

        await asyncio.sleep( 3 )
        
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
        LOGGER.info("AppZnp shutdown called")
        await Classes.ZigpyTransport.AppGeneric.shutdown(self, db=db)


    def connection_lost(self, exc: Exception) -> None:
        """Handle connection lost event."""
        Classes.ZigpyTransport.AppGeneric.connection_lost(self, exc)


    async def watchdog_feed(self) -> None:
        await Classes.ZigpyTransport.AppGeneric.watchdog_feed(self)


    async def register_endpoints(self):
        self.log.logging("TransportZigpy", "Status", "++ ZNP Radio register default Ep")
        await super().register_endpoints()

        self.log.logging("TransportZigpy", "Status", "++ ZNP Radio register any additional/specific Ep")
        await Classes.ZigpyTransport.AppGeneric.register_specific_endpoints(self)

        await register_green_power_group(self)


    async def _subscribe_to_multicast_group(self, group_id, endpoint_id):
        """
        Ask Z-Stack to put a coordinator endpoint in a group.

        zigpy-znp does not implement this hook of ControllerApplication (zigpy >
        2.3.0), so zigpy's Green Power manager, which joins the Green Power group
        at startup and after each commissioning, did nothing on ZNP.
        """
        await znp_add_endpoint_to_group(self, endpoint_id, group_id)


    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)


    def handle_join(self, nwk: t.NWK, ieee: t.EUI64, parent_nwk: t.NWK, *, handle_rejoin: bool = True,) -> None:
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


    async def set_extended_pan_id(self, extended_pan_ip):
        """Set the extended PAN ID and re-form the network."""
        self.config[zigpy_conf.CONF_NWK][zigpy_conf.CONF_NWK_EXTENDED_PAN_ID] = extended_pan_ip
        await self.startup(
            self.statistics,
            self.HardwareID,
            self.pluginconf,
            self.use_of_zigpy_persistent_db,
            self.callBackFunction,
            callBackUpdDevice=self.callBackUpdDevice,
            callBackGetDevice=self.callBackGetDevice,
            callBackBackup=self.callBackBackup,
            callBackRestartPlugin=self.callBackRestartPlugin,
            callBackHeartbeat=self.callBackHeartbeat,
            captureRxFrame=self.captureRxFrame,
            auto_form=True,
            force_form=True,
            log=self.log,
            permit_to_join_timer=self.permit_to_join_timer,
        )


    async def set_channel(self, channel):
        """Migrate the network to a new channel via zigpy channel migration."""
        await self.move_network_to_channel(channel)


    async def remove_ieee(self, ieee):
        await self.remove( ieee )


    async def coordinator_backup( self ):
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=True))


    async def network_interference_scan(self):
        self.manual_interference_scan_task = await Classes.ZigpyTransport.AppGeneric.network_interference_scan(self)


    def get_topology(self):
        return self.topology.neighbors, self.topology.routes


    def is_zigpy_topology_in_progress(self):
        return Classes.ZigpyTransport.AppGeneric.is_zigpy_topology_in_progress(self)


    async def start_topology_scan(self):
        self.manual_topology_scan_task = await self.topology.scan()


    def get_device_rssi(self, z4d_ieee=None, z4d_nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device_rssi(self, z4d_ieee, z4d_nwk)


    def is_bellows(self):
        return False


    def is_znp(self):
        return True


    def is_deconz(self):
        return False


async def register_green_power_group(self):
    """
    Put the Green Power endpoint (0xF2) in the Green Power group (0x0B84), at
    every startup, as zigbee-herdsman does on Z-Stack.

    The Green Power notifications that the proxies forward, the coordinator's
    own proxy included, reach the coordinator on that group. zigpy only joins
    it once a Green Power device is commissioned, so on ZNP the first Green
    Power device could never be commissioned. Nothing to do with a zigpy
    without Green Power, which registers no Green Power endpoint.
    """
    if getattr(self, "green_power", None) is None:
        return

    self.log.logging("TransportZigpy", "Status", "++ ZNP Radio join the Green Power group 0x%04x on Ep 0x%02x" % (GP_GROUP_ID, GP_ENDPOINT))
    await znp_add_endpoint_to_group(self, GP_ENDPOINT, GP_GROUP_ID)


async def znp_add_endpoint_to_group(self, endpoint, group_id):
    """
    Add a coordinator endpoint to a group of Z-Stack's APS group table, unless
    it is already there (the table is kept in NV across restarts).

    ZDO.ExtFindGroup answers status, group id, name length and name: status 0
    means the endpoint is already in the group.
    """
    try:
        found = await self._znp.request(c.ZDO.ExtFindGroup.Req(Endpoint=endpoint, GroupId=group_id))
        if found.Group[:1] == bytes([t.Status.SUCCESS]):
            self.log.logging("TransportZigpy", "Debug", "ZNP Ep 0x%02x already in group 0x%04x" % (endpoint, group_id))
            return

        await self._znp.request(
            c.ZDO.ExtAddGroup.Req(Endpoint=endpoint, GroupId=group_id, GroupName=t.CharacterString("")),
            RspStatus=t.Status.SUCCESS,
        )
        self.log.logging("TransportZigpy", "Status", "++ ZNP Ep 0x%02x added to group 0x%04x" % (endpoint, group_id))

    except Exception as e:
        self.log.logging("TransportZigpy", "Error", "ZNP: unable to add Ep 0x%02x to group 0x%04x: %s" % (endpoint, group_id, e),
                         None, {"Error code": "ZNPGRP-ADD-01", "Endpoint": "0x%02x" % endpoint, "Group": "0x%04x" % group_id})
