#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38 & badz
#
# SPDX-License-Identifier:    GPL-3.0 license

import serial
import asyncio
import binascii
import contextlib
import json
import logging
import os.path
import time
from pathlib import Path

from zigpy.application import ControllerApplication
import zigpy.application
import zigpy.backups
import zigpy.config as zigpy_conf
import zigpy.const as const
import zigpy.device
import zigpy.exceptions
import zigpy.types as zigpy_t
import zigpy.zdo
import zigpy.zdo.types as zdo_types
from zigpy.backups import NetworkBackup

from Classes.ZigpyTransport.instrumentation import write_capture_rx_frames
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8014_frame_content,
    build_plugin_8047_frame_content, build_plugin_8048_frame_content)
from Classes.ZigpyTransport.Transport import ZigpyTransport

LOGGER = logging.getLogger(__name__)

ENERGY_SCAN_WARN_THRESHOLD = 0.75 * 255


async def _load_db(self) -> None:
    """Restore save state."""
    await super(type(self),self)._load_db()


async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
    """
    Starts the network on a connected radio, optionally forming one with random
    settings if necessary.
    """
    self.log.logging("TransportZigpy", "Log", "AppGeneric:initialize auto_form: %s force_form: %s Class: %s Logger: %s" %( auto_form, force_form, type(self), LOGGER))

    # Make sure the first thing we do is feed the watchdog
    if self.config[zigpy_conf.CONF_WATCHDOG_ENABLED]:
        await self.watchdog_feed()
        self._watchdog_task = asyncio.create_task(self._watchdog_loop(), name="watchdog_loop")
        await asyncio.sleep(1)

    # Retreive Last Backup
    _retreived_backup = _retreive_previous_backup(self)

    # If We need to Create a new Zigbee network annd restore the last backup
    if force_form:
        with contextlib.suppress(Exception):
            if _retreived_backup is None:
                await super(type(self),self).form_network()
            else:
                self.log.logging( "Zigpy", "Status","++ Force Form: Restoring the most recent network backup")
                await self.backups.restore_backup(  _retreived_backup ) 

    # Load Network Information
    try:
        await self.load_network_info(load_devices=False)

    except zigpy.exceptions.NetworkNotFormed:
        self.log.logging("TransportZigpy", "Log", "Network is not formed")

        if not auto_form:
            raise

        self.log.logging( "Zigpy", "Status","++ Forming a new network")
        await super(type(self),self).form_network()

        if _retreived_backup is None:
            # Form a new network if we have no backup
            self.log.logging( "Zigpy", "Status","++ Forming a new network with no backup")
            await self.form_network()
        else:
            # Otherwise, restore the most recent backup
            self.log.logging( "Zigpy", "Status","++ Restoring the most recent network backup")
            await self.backups.restore_backup( _retreived_backup )

        await self.load_network_info(load_devices=True)

    new_state = self.backups.from_network_state()
    if (
        self.config[zigpy_conf.CONF_NWK_VALIDATE_SETTINGS]
        and _retreived_backup is not None
        and not new_state.is_compatible_with(self.backups)
    ):
        raise zigpy.exceptions.NetworkSettingsInconsistent(
            f"Radio network settings are not compatible with most recent backup!\n"
            f"Current settings: {new_state!r}\n"
            f"Last backup: {_retreived_backup!r}",
            old_state=_retreived_backup,
            new_state=new_state,
        )

    self.log.logging("TransportZigpy", "Debug", f"Network info: {self.state.network_info}")
    self.log.logging("TransportZigpy", "Debug", f"Node info   : {self.state.node_info}")

    # Start Network
    await self.start_network()
    self._persist_coordinator_model_strings_in_db()

    # Network interference scan
    # if self.config[zigpy_conf.CONF_STARTUP_ENERGY_SCAN]:
    #     # Each scan period is 15.36ms. Scan for at least 200ms (2^4 + 1 periods) to
    #     # pick up WiFi beacon frames.
    #     results = await self.energy_scan( channels=zigpy_t.Channels.ALL_CHANNELS, duration_exp=4, count=1 )

    #     if results[self.state.network_info.channel] > ENERGY_SCAN_WARN_THRESHOLD:
    #         self.log.logging("TransportZigpy", "Error", "WARNING - Zigbee channel %s utilization is %0.2f%%!" %(
    #             self.state.network_info.channel, 100 * results[self.state.network_info.channel] / 255, ))
    #         self.log.logging("TransportZigpy", "Error", const.INTERFERENCE_MESSAGE)
    #         self.log.logging("TransportZigpy", "Log", "Energy scan result:")
    #         for _chnl in results:
    #             self.log.logging("TransportZigpy", "Log", f"  [{_chnl}] : %0.2f%%" % (100 * results[_chnl] / 255) )

    # Config Top Scan
    if self.config[zigpy_conf.CONF_TOPO_SCAN_ENABLED]:
        # Config specifies the period in minutes, not seconds
        self.topology.start_periodic_scans( period=(60 * self.config[zigpy.config.CONF_TOPO_SCAN_PERIOD]) )


async def shutdown(self, *, db: bool = True) -> None:
    """Shutdown controller."""
    LOGGER.info("Zigpy shutdown")
    self.shutting_down = True

    await _create_backup(self)

    await ControllerApplication.shutdown(self, db=db)


async def _create_backup(self) -> None:
    """ Create a coordinator backup"""
    try:
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=True))
    except Exception:
        LOGGER.warning("Failed to create backup", exc_info=False)


def connection_lost(self, exc: Exception) -> None:
    """Handle connection lost event."""
    LOGGER.warning( "+ Connection to the radio was lost (trying to recover): %s %r" %(type(exc), exc) )
    self.radio_lost_cnt += 1

    super(type(self),self).connection_lost(exc)

    if self.radio_lost_cnt > 8:
        LOGGER.error( "++++++++++++++++++++++ Connection to coordinator failed too many errors, let's restart the plugin")
        self.callBackRestartPlugin()
    
    elif not self.shutting_down and not self.restarting and isinstance( exc, serial.serialutil.SerialException):
        LOGGER.error( "++++++++++++++++++++++ Connection to coordinator failed on Serial, let's restart the plugin")
        LOGGER.warning( f"--> : self.shutting_down: {self.shutting_down}, {self.restarting}")

        self.restarting = True
        self.callBackRestartPlugin()


def _retreive_previous_backup(self):
    _retreived_backup = None
    if "autoRestore" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoRestore"]:
        # In case of a fresh coordinator, let's load the latest backup
        _retreived_backup = do_retreive_backup( self )
        if _retreived_backup:
            _retreived_backup = NetworkBackup.from_dict( _retreived_backup )

        if _retreived_backup:
            if self.pluginconf.pluginConf[ "OverWriteCoordinatorIEEEOnlyOnce"]:
                self.log.logging("TransportZigpy", "Log", "Allow eui64 overwrite only once !!!")
                _retreived_backup.network_info.stack_specific.setdefault("ezsp", {})[ "i_understand_i_can_update_eui64_only_once_and_i_still_want_to_do_it"] = True

            self.log.logging("TransportZigpy", "Debug", "Last backup retreived: %s" % _retreived_backup )
            self.backups.add_backup( backup=_retreived_backup )
    return _retreived_backup
   

def get_device(self, ieee=None, nwk=None):
    # LOGGER.debug("get_device nwk %s ieee %s" % (nwk, ieee))
    # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
    # will return None if not found
    # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
    dev = None
    try:
        dev = super(type(self),self).get_device(ieee, nwk)
        # We have found in Zigpy db.
        # We might have to check that the plugin and zigpy Dbs are in sync
        # Let's check if the tupple (dev.ieee, dev.nwk ) are aligned with plugin Db
        _update_nkdids_if_needed(self, dev.ieee, dev.nwk )

    except KeyError:
        # Not found in zigpy Db, let see if we can get it into the Plugin Db
        if self.callBackGetDevice:
            if nwk is not None:
                nwk = nwk.serialize()[::-1].hex()
            if ieee is not None:
                ieee = "%016x" % zigpy_t.uint64_t.deserialize(ieee.serialize())[0]
            zfd_dev = self.callBackGetDevice(ieee, nwk)
            if zfd_dev is not None:
                (nwk, ieee) = zfd_dev
                dev = self.add_device(zigpy_t.EUI64(zigpy_t.uint64_t(ieee).serialize()),nwk)

    if dev is not None:
        return dev

    LOGGER.debug("AppZnp get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
    raise KeyError


def handle_join(self, nwk: zigpy_t.NWK, ieee: zigpy_t.EUI64, parent_nwk: zigpy_t.NWK) -> None:
    """
    Called when a device joins or announces itself on the network.
    """
    self.log.logging("TransportZigpy", "Debug","handle_join (0x%04x %s)" %(nwk, ieee))
    
    if str(ieee) in {"00:00:00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff:ff:ff"}:
        # invalid ieee, drop
        self.log.logging("TransportZigpy", "Log", "ignoring invalid neighbor: %s" %ieee)
        return

    ieee = zigpy_t.EUI64(ieee)
    try:
        dev = self.get_device(ieee)
        time.sleep(1.0)
        self.log.logging("TransportZigpy", "Debug", "Device 0x%04x (%s) joined the network" %(nwk, ieee))

    except KeyError:
        dev = self.add_device(ieee, nwk)
        dev.update_last_seen()
        time.sleep(1.0)
        self.log.logging("TransportZigpy", "Debug", "New device 0x%04x (%s) joined the network" %(nwk, ieee))

    if dev.nwk != nwk:
        dev.nwk = nwk
        _update_nkdids_if_needed(self, ieee, dev.nwk )
        self.log.logging("TransportZigpy", "Debug", "Device %s changed id (0x%04x => 0x%04x)" %(ieee, dev.nwk, nwk))

    super(type(self),self).handle_join(nwk, ieee, parent_nwk) 


def get_device_ieee(self, nwk):
    # Call from the plugin to retreive the ieee
    # we assumed nwk as an hex string
    try:
        dev = super(type(self),self).get_device( nwk=int(nwk,16))
        LOGGER.debug("AppZnp get_device  nwk: %s returned %s" %( nwk, dev))
        
    except KeyError:
        LOGGER.debug("AppZnp get_device raise KeyError nwk: %s !!" %( nwk))
        return None
    
    if dev.ieee:
        return "%016x" % zigpy_t.uint64_t.deserialize(dev.ieee.serialize())[0]
    return None


def handle_leave(self, nwk, ieee):
    self.log.logging("TransportZigpy", "Debug","handle_leave (0x%04x %s)" %(nwk, ieee))
    super(type(self),self).handle_leave(nwk, ieee)
    plugin_frame = build_plugin_8048_frame_content(self, ieee)
    self.callBackFunction(plugin_frame)
    

def handle_relays(self, nwk, relays) -> None:
    self.log.logging("TransportZigpy", "Debug","handle_relays (0x%04x %s)" %(nwk, str(relays)))
    """Called when a list of relaying devices is received."""
    super(type(self),self).handle_relays(nwk, relays)


def measure_execution_time(func):
    def wrapper(self, packet):
        t_start = None
        if self.pluginconf.pluginConf.get("ZigpyReactTime", False):
            t_start = int(1000 * time.time())

        try:
            func(self, packet)

        finally:
            if t_start:
                t_end = int(1000 * time.time())
                t_elapse = t_end - t_start
                self.statistics.add_rxTiming(t_elapse)  
                self.log.logging("TransportZigpy", "Log", f"| (packet_received) | {t_elapse} | {packet.src.address.serialize()[::-1].hex()} | {packet.profile_id} | {packet.lqi} | {packet.rssi} |")
    return wrapper

    
@measure_execution_time
def packet_received(
    self, 
    packet: zigpy_t.ZigbeePacket
    ) -> None:

    """Notify zigpy of a received Zigbee packet.""" 
    self.log.logging("TransportZigpy", "Debug", "packet_received %s" %(packet))

    sender = packet.src.address.serialize()[::-1].hex()
    addr_mode = int(packet.src.addr_mode) if packet.src.addr_mode is not None else None
    profile = int(packet.profile_id) if packet.profile_id is not None else None
    cluster = int(packet.cluster_id) if packet.cluster_id is not None else None
    src_ep = int(packet.src_ep) if packet.src_ep is not None else None
    dst_ep = int(packet.dst_ep) if packet.dst_ep is not None else None
    source_route = packet.source_route

    if source_route:
        self.log.logging("trackReceivedRoute", "Log", f"packet_received from {sender} via {source_route}")

    message = packet.data.serialize()
    hex_message = binascii.hexlify(message).decode("utf-8")
    dst_addressing = packet.dst.addr_mode if packet.dst else None
    
    self.log.logging("TransportZigpy", "Debug", "packet_received - %s %s %s %s %s %s %s %s" %(
        packet.src, profile, cluster, src_ep, dst_ep, message, hex_message, dst_addressing))

    hex_message = binascii.hexlify(message).decode("utf-8")
    write_capture_rx_frames( self, packet.src, profile, cluster, src_ep, dst_ep, message, hex_message, dst_addressing)

    if sender == 0x0000 or ( zigpy.zdo.ZDO_ENDPOINT in (packet.src_ep, packet.dst_ep)): 
        self.log.logging("TransportZigpy", "Debug", "packet_received from Controller Sender: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
            sender, profile, cluster, src_ep, dst_ep, hex_message))
        super(type(self),self).packet_received(packet)

    if cluster == 0x8036:
        # This has been handle via on_zdo_mgmt_permitjoin_rsp()
        self.log.logging("TransportZigpy", "Debug", "packet_received 0x8036: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
            sender, profile, cluster, src_ep, dst_ep, hex_message))
        self.callBackFunction( build_plugin_8014_frame_content(self, sender, hex_message ) )
        super(type(self),self).packet_received(packet)
        return

    if cluster == 0x8034:
        # This has been handle via on_zdo_mgmt_leave_rsp()
        self.log.logging("TransportZigpy", "Debug", "packet_received 0x8036: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
            sender, profile, cluster, src_ep, dst_ep, hex_message))
        self.callBackFunction( build_plugin_8047_frame_content(self, sender, hex_message) )
        super(type(self),self).packet_received(packet)
        return

    packet.lqi = 0x00 if packet.lqi is None else packet.lqi
    profile = 0x0000 if src_ep == dst_ep == 0x00 else profile

    if profile and cluster:
        self.log.logging( "TransportZigpy", "Debug", "packet_received device: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" %( 
            sender, profile, cluster, src_ep, dst_ep, hex_message, packet.lqi), )

    plugin_frame = build_plugin_8002_frame_content(self, sender, profile, cluster, src_ep, dst_ep, message, packet.lqi, src_addrmode=addr_mode)
    self.log.logging("TransportZigpy", "Debug", "packet_received Sender: %s frame for plugin: %s" % (sender, plugin_frame))
    self.callBackFunction(plugin_frame)

    if cluster == 0x0019:
        # Do not forward message to zigpy, it will be managed by Z4D plugin
        return

    super(type(self),self).packet_received(packet)
    

def _update_nkdids_if_needed( self, ieee, new_nwkid ):
    if not isinstance(self, ZigpyTransport):
        return
    _ieee = "%016x" % zigpy_t.uint64_t.deserialize(ieee.serialize())[0]
    _nwk = new_nwkid.serialize()[::-1].hex()
    self.callBackUpdDevice(_ieee, _nwk)


def get_zigpy_version(self):
    # This is a fake version number. This is just to inform the plugin that we are using ZNP over Zigpy
    LOGGER.debug("get_zigpy_version ake version number. !!")
    return self.version


def get_device_with_address( self, address: zigpy_t.AddrModeAddress ) -> zigpy.device.Device:
        """Gets a `Device` object using the provided address mode address."""

        if address.addr_mode == zigpy_t.AddrMode.NWK:
            return self.get_device(nwk=address.address)

        elif address.addr_mode == zigpy_t.AddrMode.IEEE:
            return self.get_device(ieee=address.address)

        else:
            raise ValueError(f"Invalid address: {address!r}")


async def register_specific_endpoints(self):
    """
    Registers all necessary endpoints.
    The exact order in which this method is called depends on the radio module.
    """

    # Endpoint configurations
    endpoint_configs = {
        "Wiser2": (0x03, [zigpy.zcl.clusters.general.Basic.cluster_id, zigpy.zcl.clusters.hvac.Thermostat.cluster_id], []),
        "Livolo": (0x08, [zigpy.zcl.clusters.general.Basic.cluster_id, zigpy.zcl.clusters.general.OnOff.cluster_id], [zigpy.zcl.clusters.security.IasZone.cluster_id]),
        "Orvibo": (0x0a, [zigpy.zcl.clusters.general.Basic.cluster_id], []),
        "Wiser": (0x0b, [zigpy.zcl.clusters.general.Basic.cluster_id, zigpy.zcl.clusters.hvac.Thermostat.cluster_id], []),
        "Terncy": (0x6e, [zigpy.zcl.clusters.general.Basic.cluster_id], []),
        "Konke": (0x15, [zigpy.zcl.clusters.general.Basic.cluster_id, zigpy.zcl.clusters.general.OnOff.cluster_id], [zigpy.zcl.clusters.security.IasZone.cluster_id]),
    }

    # Iterate through endpoint configurations
    for plugin, (endpoint, input_clusters, output_clusters) in endpoint_configs.items():
        if plugin in self.pluginconf.pluginConf and self.pluginconf.pluginConf[plugin]:
            self.log.logging("TransportZigpy", "Status", f"++ Adding {plugin} Endpoint 0x{endpoint:x}")
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=endpoint,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=input_clusters,
                    output_clusters=output_clusters,
                )
            )


def do_retreive_backup( self ):
    from Modules.zigpyBackup import handle_zigpy_retreive_last_backup
    
    LOGGER.debug("Retreiving last backup")
    return handle_zigpy_retreive_last_backup( self )


async def network_interference_scan(self):

    self.log.logging( "NetworkEnergy", "Debug", "network_interference_scan")
    
    # Each scan period is 15.36ms. Scan for at least 200ms (2^4 + 1 periods) to
    # pick up WiFi beacon frames.
    results = await self.energy_scan( channels=zigpy_t.Channels.ALL_CHANNELS, duration_exp=4, count=1 )
    
    self.log.logging( "NetworkEnergy", "Debug", "Network Energly Level Report: %s" % results)

    _filename = Path( self.pluginconf.pluginConf["pluginReports"] ) / ("NetworkEnergy-v3-" + "%02d.json" % self.HardwareID)
    if os.path.isdir( Path(self.pluginconf.pluginConf["pluginReports"]) ):

        nbentries = 0
        if os.path.isfile(_filename):
            with open(_filename, "r") as fin:
                data = fin.read().splitlines(True)
                nbentries = len(data)

        with open(_filename, "w") as fout:
            # we need to short the list by todayNumReports - todayNumReports - 1
            maxNumReports = self.pluginconf.pluginConf["numTopologyReports"]
            start = (nbentries - maxNumReports) + 1 if nbentries >= maxNumReports else 0
            self.log.logging( "NetworkEnergy", "Log", "Rpt max: %s , New Start: %s, Len:%s " % (maxNumReports, start, nbentries))

            if nbentries != 0:
                fout.write("\n")
                fout.writelines(data[start:])
            fout.write("\n")
            json.dump(build_json_to_store(self, results), fout)
    else:
        self.log.logging( "NetworkEnergy", "Error", "Unable to get access to directory %s, please check PluginConf.txt" % (
            self.pluginconf.pluginConf["pluginReports"]) )


def build_json_to_store(self, scan_result):
    """Build the energy report in a format to be stored and used by WebUI"""

    timestamp = int(time.time())

    self.log.logging("TransportZigpy", "Log", "Energy scan result:")

    router = {
        "_NwkId": "0000",
        "MeshRouters": [ {
            "_NwkId": "0000",
            "ZDeviceName": "Zigbee Coordinator",
            "Tx": 0,
            "Fx": 0,
            "Channels": scan_channel( self, scan_result )
        }]
    }
    return {timestamp: [ router, ] }


def scan_channel( self, scan_result ):
    list_channels = []
    for channel, value in scan_result.items():
        percentage = 100 * value / 255
        self.log.logging("TransportZigpy", "Log", f"  [{channel}] : {percentage:.2f}%")
        list_channels.append(  { "Channel": str(channel), "Level": int(value)} )
        
    return list_channels


def is_zigpy_topology_in_progress(self):
    zigpy_topology = self.topology
    return zigpy_topology._scan_task is not None and not zigpy_topology._scan_task.done()


def get_device_rssi(self, z4d_ieee=None, z4d_nwk=None):
    """ retreive RSSI of the device nwk or ieee """

    try:
        nwk = zigpy_t.NWK.convert(z4d_nwk)
        dev = super(type(self),self).get_device(None, nwk)
        return dev.rssi
    except KeyError:
        return None
