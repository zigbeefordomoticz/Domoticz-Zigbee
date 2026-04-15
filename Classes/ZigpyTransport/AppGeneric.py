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
"""
AppGeneric.py — Radio-agnostic Zigpy application layer overrides.

Part of the Zigbee for Domoticz plugin.
https://github.com/zigbeefordomoticz/Domoticz-Zigbee

Overview
--------
This module defines a set of standalone functions that override or extend
methods of zigpy's ControllerApplication class. Rather than subclassing
ControllerApplication directly, these functions are injected into
radio-specific application classes at runtime (zigpy-znp, bellows/EZSP,
zigpy-zigate, zigpy-deconz, etc.) via the ZigpyTransport layer. Each
function receives the application instance as its first argument (self),
following the same calling convention as bound methods.

This design allows a single set of plugin-specific behaviours to be shared
across all supported radio backends without duplicating code in each
radio-specific module.

Relationship to Zigpy
---------------------
The functions here override the following ControllerApplication methods:

    _load_db()                  — adds error handling around DB restore
    initialize()                — adds watchdog setup, backup restore,
                                  TX power clamping and topology scan start
    watchdog_feed()             — thin delegation to _watchdog_feed()
    _watchdog_loop()            — overrides period to 5s (upstream: 30s)
    shutdown()                  — adds coordinator backup before teardown
    connection_lost()           — adds radio-specific recovery and restart logic
    get_device()                — adds plugin DB fallback on zigpy cache miss
    handle_join()               — adds NWK sync and invalid IEEE filtering
    handle_leave()              — adds plugin 0x8048 frame delivery
    handle_relays()             — adds debug logging
    packet_received()           — full routing override for plugin frame delivery

The following are plugin-only additions with no upstream equivalent:

    connection_lost_error()     — shared fatal-error handler
    get_device_ieee()           — NWK-to-IEEE lookup for the plugin layer
    get_device_with_address()   — AddrModeAddress convenience wrapper
    get_device_rssi()           — RSSI retrieval by NWK address
    get_zigpy_version()         — transport version for the plugin layer
    register_specific_endpoints() — vendor-specific endpoint registration
    is_zigpy_topology_in_progress() — topology scan state query
    network_interference_scan() — channel energy scan with report persistence
    build_json_to_store()       — energy report formatter for WebUI
    scan_channel()              — per-channel energy level formatter
    _retrieve_previous_backup() — backup retrieval and auto-restore setup
    _create_backup()            — backup persistence via plugin callback
    do_retreive_backup()        — deferred delegate to Modules.zigpyBackup
    _update_nkdids_if_needed()  — NWK address sync between zigpy and plugin DB
    measure_execution_time()    — decorator for packet handler timing

Packet Routing
--------------
The central function in this module is packet_received(), which intercepts
every incoming Zigbee frame before (and sometimes instead of) passing it to
the upstream zigpy stack. The routing logic separates:

    - ZDO frames (coordinator or ZDO endpoint) → upstream zigpy
    - Mgmt_Permit_Join_rsp (0x8036)            → plugin frame 0x8014
    - Mgmt_Leave_rsp (0x8034)                  → plugin frame 0x8047
    - ZCL frames from devices (profile 0x0104) → plugin frame 0x8002,
                                                  upstream skipped so the
                                                  plugin owns ZCL responses
    - All other frames                          → plugin frame 0x8002
                                                  + upstream zigpy

Connection Recovery
-------------------
connection_lost() implements a grace-period mechanism to tolerate NCP
resets that occur within GRACE_PERIOD_AFTER_START (60) seconds of plugin
startup. Outside that window, any fatal radio error sets self.restarting
and triggers a full plugin restart via self.callBackRestartPlugin().

Note that connection_lost() imports bellows-specific types inline
(NcpFailure, NcpResetCode). On non-bellows radios these imports will
fail if bellows is not installed; this is a known limitation of the
current implementation.

Coordinator Backup and Restore
-------------------------------
On shutdown, a full coordinator backup (including the device list) is
created via zigpy's backup API and handed to the plugin layer through
self.callBackBackup(). On startup, if 'autoRestore' is set in plugin
config, the most recent backup is retrieved and passed to
self.backups.restore_backup() before network formation, allowing the
coordinator's PAN ID, extended PAN ID, network key and device list to
survive a coordinator replacement.

The 'OverWriteCoordinatorIEEEOnlyOnce' config key injects the EZSP-specific
one-time EUI64 overwrite flag into the backup metadata when restoring to a
new bellows/EZSP coordinator.

Module-level Constants
----------------------
ENERGY_SCAN_WARN_THRESHOLD : float
    Energy level (0–255 scale) above which a channel is considered
    heavily congested. Set to 75% of the maximum (0.75 * 255 = 191.25).
    Currently defined but not yet used in scan reporting logic.

GRACE_PERIOD_AFTER_START : int
    Number of seconds after plugin startup during which an NCP ACK-timeout
    reset is tolerated without triggering a plugin restart. Default: 60.

Dependencies
------------
External:
    zigpy               — core Zigbee stack and type system
    zigpy.backups       — NetworkBackup for coordinator state persistence
    serial              — SerialException detection in connection_lost()
    bellows             — NcpFailure / NcpResetCode (inline import,
                          bellows-only radios)

Internal:
    Classes.ZigpyTransport.Transport        — ZigpyTransport (isinstance guard)
    Classes.ZigpyTransport.instrumentation  — write_capture_rx_frames()
    Classes.ZigpyTransport.plugin_encoders  — build_plugin_80xx_frame_content()
    Modules.zigpyBackup                     — handle_zigpy_retreive_last_backup()
                                              (deferred import in do_retreive_backup)

Known Limitations
-----------------
- The inline bellows imports in connection_lost() couple this generic module
  to a specific radio backend. Non-bellows deployments should ensure these
  imports are guarded or that the bellows package is present in the
  environment.

- super(type(self), self) is used throughout in place of super() because
  these are module-level functions rather than class methods. This pattern
  is fragile in deep inheritance chains and may cause infinite recursion if
  a subclass of the injected class calls these functions. This is a known
  architectural trade-off of the monkey-patching approach.

- do_retreive_backup() retains its misspelled name for backwards
  compatibility with callers in other modules. The public-facing wrapper
  _retrieve_previous_backup() uses the correct spelling.

- The z4d_ieee parameter of get_device_rssi() is accepted for API symmetry
  but is not currently used in the device lookup.
"""

import asyncio
import binascii
import contextlib
import json
import logging
import os.path
import time
from datetime import UTC, datetime
from pathlib import Path

import serial
import zigpy.config as zigpy_conf
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
GRACE_PERIOD_AFTER_START = 60  # 60 seconds of period after plugin start to allow NCP to recover


async def _load_db(self) -> None:
    """
    Restore the Zigpy persistent device database from disk.

    Wraps the upstream ControllerApplication._load_db() with error handling so
    that a corrupted or missing database file does not silently swallow the
    exception — it is logged and re-raised to let the caller decide how to
    proceed.
    """
    try:
        await super(type(self),self)._load_db()
    except Exception as e:
        LOGGER.error("error loading Zigpy Persistent Db", exc_info=e)
        raise


async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
    """
    Start the Zigbee network on the connected radio.

    Overrides ControllerApplication.initialize() to add plugin-specific
    behaviour around network startup:

    - Starts the firmware watchdog at a 5-second period (overriding the
      upstream default of 30 seconds) if watchdog is enabled in config.
    - Optionally restores the most recent coordinator backup before forming
      the network, controlled by the 'autoRestore' plugin configuration key.
    - If force_form is True, re-forms the network (or restores a backup if
      one exists) before loading network info.
    - If auto_form is True and no network exists, forms a new network or
      restores from the most recent backup.
    - Validates that the current radio state is compatible with the stored
      backup when CONF_NWK_VALIDATE_SETTINGS is enabled.
    - Adjusts TX power to stay within the regulatory domain maximum.
    - Starts periodic topology scans if enabled in config.

    Args:
        auto_form:  If True, automatically form a new network when none is
                    found on the radio.
        force_form: If True, unconditionally re-form (or restore) the network
                    before loading network info, regardless of current state.

    Raises:
        zigpy.exceptions.NetworkNotFormed: If no network exists and
            auto_form is False.
        zigpy.exceptions.NetworkSettingsInconsistent: If the current radio
            state is incompatible with the most recent backup and
            CONF_NWK_VALIDATE_SETTINGS is enabled.
    """
    self.log.logging("TransportZigpy", "Log", "AppGeneric:initialize auto_form: %s force_form: %s Class: %s Logger: %s" %( auto_form, force_form, type(self), LOGGER))
    # Make sure the first thing we do is feed the watchdog
    if self.config[zigpy_conf.CONF_WATCHDOG_ENABLED]:
        await self.watchdog_feed()
        self._watchdog_task = asyncio.create_task(self._watchdog_loop(), name="watchdog_loop")
        await asyncio.sleep(1)
        self.log.logging("TransportZigpy", "Log", "AppGeneric:initialize - Watchdog loop started watchdog_task: {}".format(self._watchdog_task))

    # Retreive Last Backup
    _retrieved_backup = _retrieve_previous_backup(self)

    # If We need to Create a new Zigbee network annd restore the last backup
    if force_form:
        with contextlib.suppress(Exception):
            if _retrieved_backup is None:
                await super(type(self),self).form_network()
            else:
                self.log.logging( "Zigpy", "Status","++ Force Form: Restoring the most recent network backup")
                await self.backups.restore_backup(  _retrieved_backup ) 

    # Load Network Information
    try:
        await self.load_network_info(load_devices=False)

    except zigpy.exceptions.NetworkNotFormed:
        self.log.logging("TransportZigpy", "Log", "Network is not formed")

        if not auto_form:
            raise

        self.log.logging( "Zigpy", "Status","++ Forming a new network")
        await super(type(self),self).form_network()

        if _retrieved_backup is None:
            # Form a new network if we have no backup
            self.log.logging( "Zigpy", "Status","++ Forming a new network with no backup")
            await self.form_network()
        else:
            # Otherwise, restore the most recent backup
            self.log.logging( "Zigpy", "Status","++ Restoring the most recent network backup")
            await self.backups.restore_backup( _retrieved_backup )

        await self.load_network_info(load_devices=True)

    new_state = self.backups.from_network_state()
    if (
        self.config[zigpy_conf.CONF_NWK_VALIDATE_SETTINGS]
        and _retrieved_backup is not None
        and not new_state.is_compatible_with(self.backups)
    ):
        raise zigpy.exceptions.NetworkSettingsInconsistent(
            f"Radio network settings are not compatible with most recent backup!\n"
            f"Current settings: {new_state!r}\n"
            f"Last backup: {_retrieved_backup!r}",
            old_state=_retrieved_backup,
            new_state=new_state,
        )

    self.log.logging("TransportZigpy", "Debug", f"Network info: {self.state.network_info}")
    self.log.logging("TransportZigpy", "Debug", f"Node info   : {self.state.node_info}")

    # Start Network
    await self.start_network()

    # Networks can move between RF domains so we need to be able to adjust the TX
    # power on startup
    tx_power = await self._get_effective_tx_power()
    max_tx_power = await self._get_effective_maximum_tx_power()
    self.log.logging("TransportZigpy", "Status", f"Effective TxPower: {tx_power}, Max TxPower: {max_tx_power}")

    if max_tx_power is not None and tx_power is not None:
        if tx_power > max_tx_power:
            LOGGER.warning(
                "Requested TX power %0.2f dBm exceeds maximum %0.2f dBm for"
                " regulatory domain, limiting",
                tx_power,
                max_tx_power,
            )
            tx_power = max_tx_power

    if tx_power is not None:
        await self.set_tx_power(tx_power)

    self._persist_coordinator_model_strings_in_db()

    # Config Top Scan
    if self.config[zigpy_conf.CONF_TOPO_SCAN_ENABLED]:
        # Config specifies the period in minutes, not seconds
        self.topology.start_periodic_scans( period=(60 * self.config[zigpy.config.CONF_TOPO_SCAN_PERIOD]) )



async def shutdown(self, *, db: bool = True) -> None:
    """
    Shut down the controller application cleanly.

    Overrides ControllerApplication.shutdown() to add plugin-specific teardown:

    - Guards against duplicate shutdown calls via self.shutting_down.
    - Skips coordinator backup if the current error is 'connection lost',
      since the radio state may be unreliable.
    - Creates and persists a full coordinator backup (including device list)
      before shutting down, if CONF_NWK_BACKUP_ENABLED is set.
    - Waits 3 seconds after calling the upstream shutdown to allow in-flight
      operations to complete.

    Args:
        db: Whether to persist the Zigpy device database on shutdown.
            Passed through to the upstream implementation.
    """
    if self.shutting_down:
        LOGGER.warning("Ignoring duplicate shutdown event")
        return

    LOGGER.info("AppGeneric shutdown")

    if self.current_error == "connection lost":
        LOGGER.warning("AppGeneric shutdown called while connection lost, not backup-ing the coordinator state")

    elif self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED] and self.backups is not None:
        try:
            backup_coordinator = await self.backups.create_backup(load_devices=True)
            if backup_coordinator is None:
                LOGGER.warning("AppGeneric backup not created, no coordinator state to backup")
            else:
                await _create_backup(self, backup_coordinator)
                LOGGER.info("Backup completed")
        except Exception as e:
            LOGGER.error("AppGeneric backup failed", exc_info=e)

    LOGGER.info("AppGeneric application shutdown")
    self.shutting_down = True 

    try:
        # await ControllerApplication.shutdown(self, db=db)
        await super(type(self),self).shutdown( db=db)
    except Exception as e:
        LOGGER.error("AppGeneric shutdown failed", exc_info=e)
    
    await asyncio.sleep(3)


async def _create_backup(self, backup) -> None:
    """ Create a coordinator backup"""
    try:
        self.callBackBackup(backup)

    except Exception:
        LOGGER.warning("Failed to create backup", exc_info=False)


def connection_lost(self, exc: Exception) -> None:
    """
    Handle an unexpected loss of connection to the radio.

    Overrides ControllerApplication.connection_lost() to implement
    plugin-specific recovery logic:

    - No-ops if a shutdown or restart is already in progress.
    - For bellows NcpFailure with ERROR_EXCEEDED_MAXIMUM_ACK_TIMEOUT_COUNT,
      allows a grace period of GRACE_PERIOD_AFTER_START seconds after plugin
      startup before treating it as fatal, to accommodate NCP recovery on
      restart.
    - Treats SerialException, CancelledError, TimeoutError, and
      asyncio.TimeoutError as fatal connection errors requiring a plugin
      restart.

    Note:
        Bellows-specific types (NcpFailure, NcpResetCode) are imported inline.
        On non-bellows radios these imports will fail at runtime if bellows is
        not installed. Callers on non-bellows stacks should ensure this code
        path is not reached, or the imports should be guarded with a
        try/except ImportError.

    Args:
        exc: The exception that caused the connection loss.
    """

    try:
        from bellows.ash import \
            NcpFailure  # pylint: disable=import-outside-toplevel
        from bellows.types.named import \
            NcpResetCode  # pylint: disable=import-outside-toplevel
        is_ncp_failure = isinstance(exc, NcpFailure) and exc.code == NcpResetCode.ERROR_EXCEEDED_MAXIMUM_ACK_TIMEOUT_COUNT
    except ImportError:
        is_ncp_failure = False

    LOGGER.warning("+ Connection to the radio was lost: %s %r", type(exc), exc)

    if self.shutting_down or self.restarting:
        LOGGER.warning("+ shutdown or restart in progress")
        return

    if is_ncp_failure:
        # it seems that the NCP is stuck, but during a plugin restart, it usally recovery, so let's give a grace period
        if time.time() < (self.start_time + GRACE_PERIOD_AFTER_START):
            LOGGER.warning("+ Connection to the radio was lost, give time for recover ...")
            return

        connection_lost_error( self, "NCP reset due to exceeded maximum ACK timeout count, plugin restart required" )

    elif isinstance(exc, (serial.serialutil.SerialException, asyncio.CancelledError)):
        connection_lost_error( self, "Connection to coordinator lost, SerialError or CancelledError, plugin restart required" )

    elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        connection_lost_error( self, "Connection to coordinator lost, TimeOut, plugin restart required" )


def connection_lost_error(self, message: str) -> None:
    """
    Mark the controller as restarting and trigger a plugin restart.

    Sets self.restarting = True and self.current_error = 'connection lost',
    logs the provided message at ERROR level, then calls
    self.callBackRestartPlugin() to request a full plugin restart from the
    Domoticz layer.

    This is a shared helper called by connection_lost() for all fatal
    error conditions.

    Args:
        message: A human-readable description of the error condition,
                 included in the ERROR log entry.
    """
    self.restarting = True
    self.current_error = "connection lost"
    LOGGER.error(message)
    #self.callBackRestartPlugin()


def _retrieve_previous_backup(self):
    _retrieved_backup = None
    if "autoRestore" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoRestore"]:
        # In case of a fresh coordinator, let's load the latest backup
        _retrieved_backup = do_retrieve_backup( self )
        if _retrieved_backup:
            _retrieved_backup = NetworkBackup.from_dict( _retrieved_backup )

        if _retrieved_backup:
            if self.pluginconf.pluginConf[ "OverWriteCoordinatorIEEEOnlyOnce"]:
                self.log.logging("TransportZigpy", "Log", "Allow eui64 overwrite only once !!!")
                _retrieved_backup.network_info.stack_specific.setdefault("ezsp", {})[ "i_understand_i_can_update_eui64_only_once_and_i_still_want_to_do_it"] = True

            self.log.logging("TransportZigpy", "Debug", "Last backup retreived: %s" % _retrieved_backup )
            self.backups.add_backup( backup=_retrieved_backup )
    return _retrieved_backup
   

def get_device(self, ieee=None, nwk=None):
    """
    Look up a zigpy Device by IEEE address or NWK address.

    Overrides ControllerApplication.get_device() to add a two-stage lookup:

    1. Attempts the standard zigpy lookup. On success, calls
       _update_nkdids_if_needed() to ensure the plugin database is in sync
       with zigpy's view of the device's NWK address.
    2. On KeyError (device not in zigpy's database), falls back to
       self.callBackGetDevice() to query the plugin database. If found,
       registers the device in zigpy via add_device() so future lookups
       succeed without the fallback.

    Args:
        ieee: The IEEE (EUI64) address of the device, or None.
        nwk:  The 16-bit NWK address of the device, or None.

    Returns:
        A zigpy Device object.

    Raises:
        KeyError: If the device is not found in either the zigpy database
                  or the plugin database.
    """
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


def handle_join( self, nwk: zigpy_t.NWK, ieee: zigpy_t.EUI64, parent_nwk: zigpy_t.NWK, handle_rejoin: bool = True, ) -> None:
    """
    Handle a device join or rejoin announcement on the Zigbee network.

    Overrides ControllerApplication.handle_join() to add plugin-specific
    behaviour:

    - Drops joins from invalid IEEE addresses (all-zeros or all-ones).
    - On first join, registers the device via add_device().
    - On rejoin, updates last_seen, cancels any pending requests that were
      waiting on the old session, and logs the event.
    - If the device's NWK address has changed, updates it on the device
      object and notifies the plugin database via _update_nkdids_if_needed().
    - Delegates to the upstream handle_join() after local processing.

    Args:
        nwk:          The new 16-bit NWK address assigned to the device.
        ieee:         The device's IEEE (EUI64) address.
        parent_nwk:   The NWK address of the device's parent router.
        handle_rejoin: If True, log and process the event as a rejoin.
                       Passed through to the upstream implementation.
    """
    self.log.logging("TransportZigpy", "Debug","handle_join (0x%04x %s)" %(nwk, ieee))

    if str(ieee) in {"00:00:00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff:ff:ff"}:
        # invalid ieee, drop
        self.log.logging("TransportZigpy", "Log", "ignoring invalid neighbor: %s" %ieee)
        return

    ieee = zigpy_t.EUI64(ieee)

    try:
        dev = self.get_device(ieee)
        self.log.logging("TransportZigpy", "Debug", "Device 0x%04x (%s) joined the network" %(nwk, ieee))

    except KeyError:
        dev = self.add_device(ieee, nwk)

    else:
        if handle_rejoin:
            LOGGER.info("Device 0x%04x (%s) joined the network", nwk, ieee)

        self.log.logging("TransportZigpy", "Debug", "New device 0x%04x (%s) joined the network" %(nwk, ieee))

        # Not all stacks send a ZDO command when a device joins so the last_seen should
        # be updated
        dev.last_seen = datetime.now(UTC)

        # Cancel all pending requests for the device
        dev._concurrent_requests_semaphore.cancel_waiting(
            zigpy.exceptions.DeliveryError("Device has re-joined the network")
        )

    if dev.nwk != nwk:
        dev.nwk = nwk
        _update_nkdids_if_needed(self, ieee, dev.nwk )
        self.log.logging("TransportZigpy", "Debug", "Device %s changed id (0x%04x => 0x%04x)" %(ieee, dev.nwk, nwk))

    super(type(self),self).handle_join(nwk, ieee, parent_nwk, handle_rejoin=handle_rejoin)


def get_device_ieee(self, nwk):
    """
    Return the IEEE address for a device identified by its NWK address.

    Intended to be called from the plugin layer, which passes NWK addresses
    as hex strings (e.g. '1a2b').

    Args:
        nwk: A hex string representing the 16-bit NWK address.

    Returns:
        A 16-character lowercase hex string representing the IEEE (EUI64)
        address (e.g. '0123456789abcdef'), or None if the device is not
        found in the zigpy database.
    """
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
    """
    Handle a device leave event.

    Overrides ControllerApplication.handle_leave() to notify the plugin layer
    in addition to the standard zigpy processing.

    get it handled by plugin and do the cleanup first (via 0x8048), then 
    calls the upstream handle_leave().

    Args:
        nwk: The 16-bit NWK address of the departing device.
        ieee: The IEEE (EUI64) address of the departing device.
    """
    self.log.logging("TransportZigpy", "Debug","handle_leave (0x%04x %s)" %(nwk, ieee))
    plugin_frame = build_plugin_8048_frame_content(self, ieee)
    self.callBackFunction(plugin_frame)

    super(type(self),self).handle_leave(nwk, ieee)
    

def handle_relays(self, nwk, relays) -> None:
    """
    Handle receipt of a source-routing relay list for a device.

    Overrides ControllerApplication.handle_relays() with logging, then
    delegates to the upstream implementation unchanged.

    Args:
        nwk:    The 16-bit NWK address of the device whose relay list was
                received.
        relays: The list of NWK addresses of intermediate relay devices.
    """
    self.log.logging("TransportZigpy", "Debug","handle_relays (0x%04x %s)" %(nwk, str(relays)))
    super(type(self),self).handle_relays(nwk, relays)


def measure_execution_time(func):
    def wrapper(self, packet):
        t_start = None
        if self.pluginconf.pluginConf.get("ZigpyReactTime", False):
            t_start = int(1000 * time.time())

        try:
            func(self, packet)

        finally:
            try:
                if t_start:
                    t_end = int(1000 * time.time())
                    t_elapse = t_end - t_start
                    self.statistics.add_rxTiming(t_elapse)  
                    self.log.logging("TransportZigpy", "Log", f"| (packet_received) | {t_elapse} | {packet.src.address.serialize()[::-1].hex()} | {packet.profile_id} | {packet.lqi} | {packet.rssi} |")
            except Exception as e:
                self.log.logging("TransportZigpy", "Error", f"Error in measure_execution_time: {e}") 
            
    return wrapper

    
@measure_execution_time
def packet_received(
    self, 
    packet: zigpy_t.ZigbeePacket
    ) -> None:
    """
    Process an incoming Zigbee packet and route it to the plugin and/or zigpy.

    Overrides ControllerApplication.packet_received() to implement
    plugin-specific frame routing before (and sometimes instead of) passing
    the packet to the upstream zigpy stack. Decorated with
    @measure_execution_time.

    Routing logic (in order):

    1. If the sender is the coordinator ('0000') or the packet involves the
       ZDO endpoint, the packet is forwarded to the upstream
       packet_received() for zigpy's internal ZDO handling.

    2. If cluster is 0x8036 (Mgmt_Permit_Join_rsp), a plugin 0x8014 frame is
       built and delivered, the upstream is also notified, and the function
       returns early.

    3. If cluster is 0x8034 (Mgmt_Leave_rsp), a plugin 0x8047 frame is built
       and delivered, the upstream is also notified, and the function
       returns early.

    4. For all other packets, a plugin 0x8002 frame is built from the message
       payload and delivered via self.callBackFunction().

    5. If the packet is a ZCL message (profile 0x0104) from a non-coordinator
       device, the function returns early without calling the upstream, so
       that the plugin (not zigpy) owns the ZCL response.

    6. Otherwise the upstream packet_received() is called so zigpy can
       process the packet normally.

    All received frames are also written to the capture log via
    write_capture_rx_frames() for debugging.

    Args:
        packet: The incoming ZigbeePacket as provided by the radio layer.
    """
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

    write_capture_rx_frames( self, packet.src, profile, cluster, src_ep, dst_ep, message, hex_message, dst_addressing)

    if sender == "0000" or ( zigpy.zdo.ZDO_ENDPOINT in (packet.src_ep, packet.dst_ep)): 
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

    if profile == 0x0104 and sender != "0000":
        # ZCL Message sent by a device to the coordinator. 
        # Leave the answer to the plugin and not zigpy layer
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
    LOGGER.debug("get_zigpy_version fake version number. !!")
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


def do_retrieve_backup( self ):
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
