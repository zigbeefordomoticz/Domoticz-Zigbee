#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
radioStart.py — Radio configuration and Zigpy application lifecycle.

Covers everything from opening a serial port to having a running network
that is ready to process commands via the worker queue:

  start_zigpy_task           — top-level asyncio task (called by supervisor)
  radio_start                — build config, instantiate App, call _radio_startup
  *_configuration_setup      — per-radio config dict builders (EZSP, ZNP, deCONZ, BLZ)
  optional_configuration_setup — cross-radio zigpy settings (channel, OTA, db, …)
  _radio_startup             — app.startup(), backup, network info display
  post_coordinator_startup   — push 0x8009 / 0x8045 / 0x8043 / 0x0302 frames
  display_network_infos      — log PAN ID, channel, keys, …
  specific_endpoints         — detect whether vendor-specific EPs are needed
  _import_class              — dotted-path class importer
"""

import asyncio
import contextlib
import importlib
import queue
import traceback
from pathlib import Path

import zigpy.config
import zigpy.types as t

from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_0302_frame_content, build_plugin_8009_frame_content,
    build_plugin_8043_frame_list_node_descriptor,
    build_plugin_8045_frame_list_controller_ep)
from Classes.ZigpyTransport.workerLoop import worker_loop

def _transport_heartbeat(transport) -> None:
    """Update supervisor liveness timestamp from the coordinator watchdog tick."""
    if getattr(transport, 'zigpy_loop', None) is not None:
        transport._last_heartbeat = transport.zigpy_loop.time()


# ---------------------------------------------------------------------------
# Top-level asyncio task (entry point called by the supervisor)
# ---------------------------------------------------------------------------

async def start_zigpy_task(self, channel, extended_pan_id):
    """
    Asynchronous task that starts the radio and runs the worker loop.

    Reads channel and extended PAN ID from plugin config, calls radio_start
    (with a 60 s timeout), then drives worker_loop until zigpy_running is
    False or a STOP sentinel is received.  On exit, shuts the app down
    cleanly before returning to the supervisor.
    """
    self.log.logging("TransportZigpy", "Debug",
                     "start_zigpy_task - Starting zigpy stack with channel %s and "
                     "extended PAN ID 0x%016x" % (channel, extended_pan_id))
    self.zigpy_running = True

    if "channel" in self.pluginconf.pluginConf:
        channel = int(self.pluginconf.pluginConf["channel"])

    if "extendedPANID" in self.pluginconf.pluginConf:
        if isinstance(self.pluginconf.pluginConf["extendedPANID"], str):
            extended_pan_id = int(self.pluginconf.pluginConf["extendedPANID"], 16)
        else:
            extended_pan_id = self.pluginconf.pluginConf["extendedPANID"]

    self.log.logging("TransportZigpy", "Debug",
                     f"start_zigpy_task -extendedPANID "
                     f"{self.pluginconf.pluginConf['extendedPANID']} {extended_pan_id}")

    try:
        await asyncio.wait_for(
            radio_start(self, self.statistics, self.pluginconf,
                        self.use_of_zigpy_persistent_db, self._radiomodule,
                        self._serialPort, set_channel=channel,
                        set_extendedPanId=extended_pan_id),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        self.log.logging("TransportZigpy", "Error",
                         "radio_start timed out after 60s — triggering supervised restart")
        if self.app is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self.app.disconnect(), timeout=5.0)
            self.app = None
        return  # supervisor restarts

    except Exception as e:
        self.log.logging("TransportZigpy", "Error",
                         f"start_zigpy_task error in radio_start: {e}")

    self.log.logging(
        "TransportZigpyStack", "Debug",
        f"start_zigpy_task: radio_start finished, "
        f"app={'set' if self.app else 'None'}, zigpy_running={self.zigpy_running}"
    )

    # We MUST use queue.Queue (not asyncio.Queue) — Domoticz uses a plain thread
    self.writer_queue = queue.Queue()

    try:
        await worker_loop(self)

    except asyncio.CancelledError:
        self.log.logging("TransportZigpy", "Error",
                         "start_zigpy_task worker_loop(self) was cancelled.")

    except RuntimeError as e:
        self.log.logging("TransportZigpy", "Error",
                         f"start_zigpy_task worker_loop(self) encountered a runtime error: {e}")

    except Exception as e:
        self.log.logging("TransportZigpy", "Error",
                         f"start_zigpy_task worker_loop(self) error: {e}")

    # worker_loop has exited — clear the supervisor flag before shutdown
    self.log.logging("TransportZigpyStack", "Debug",
                     f"start_zigpy_task: worker_loop exited, zigpy_running={self.zigpy_running}")
    if self.app:
        self.app._supervisor_running = False
        self.log.logging("TransportZigpyStack", "Debug",
                         "start_zigpy_task: _supervisor_running cleared on app")

    try:
        self.log.logging("TransportZigpy", "Debug", "Shutting down zigpy thread...")
        if self.app:
            await self.app.shutdown()

    except Exception as e:
        self.log.logging("TransportZigpy", "Error",
                         f"start_zigpy_task shutdown(self) error: {e}")
        self.log.logging("TransportZigpy", "Error", f" {str(traceback.format_exc())}")
        self.log.logging("TransportZigpy", "Log", "Disconnecting communication")
        if self.app:
            await self.app.disconnect()

    await asyncio.sleep(1)

    self.log.logging(["TransportZigpy", "StopProcess"], "Debug",
                     "start_zigpy_task - exiting zigpy task.")


# ---------------------------------------------------------------------------
# Radio initialisation
# ---------------------------------------------------------------------------

async def radio_start(self, statistics, pluginconf, use_of_zigpy_persistent_db,
                      radiomodule, serialPort, auto_form=False,
                      set_channel=0, set_extendedPanId=0):
    """
    Instantiates the radio-specific App object, applies configuration, and
    calls _radio_startup to bring the network up.
    """
    self.log.logging("TransportZigpy", "Debug", "In radio_start %s" % radiomodule)

    serial_specifics = self._serialPort_communication_specifics or {}

    _RADIO_REGISTRY = {
        "ezsp":   ("bellows.config",       "Classes.ZigpyTransport.AppBellows.App_bellows", ezsp_configuration_setup),
        "znp":    ("zigpy_znp.config",     "Classes.ZigpyTransport.AppZnp.App_znp",         znp_configuration_setup),
        "deCONZ": ("zigpy_deconz.config",  "Classes.ZigpyTransport.AppDeconz.App_deconz",   deconz_configuration_setup),
        "blz":    (None,                   "Classes.ZigpyTransport.AppBlz.App_blz",          blz_configuration_setup),
    }

    entry = _RADIO_REGISTRY.get(radiomodule)
    if entry is None:
        self.log.logging("TransportZigpy", "Error", f"Wrong radiomodule: {radiomodule}")
        return

    conf_module_path, app_class_path, setup_fn = entry
    radio_specific_conf = importlib.import_module(conf_module_path) if conf_module_path else {}
    App = _import_class(app_class_path)
    config = setup_fn(self, radio_specific_conf, serialPort, serial_specifics)

    self.log.logging("TransportZigpy", "Status",
                     "++ Started radio %s port: %s config %s" % (radiomodule, serialPort, config))

    try:
        optional_configuration_setup(self, config, radio_specific_conf,
                                     set_extendedPanId, set_channel)
    except Exception as e:
        self.log.logging("TransportZigpy", "Error",
                         "Error while applying optional configuration to Radio: %s on port %s with %s"
                         % (radiomodule, serialPort, e))
        self.log.logging("TransportZigpy", "Error", "%s" % traceback.format_exc())
        return

    try:
        if radiomodule in ["znp", "deCONZ", "ezsp", "blz"]:
            self.app = App(config)
        else:
            self.log.logging("TransportZigpy", "Error", "Wrong radiomode: %s" % radiomodule)
            return
    except Exception as e:
        self.log.logging("TransportZigpy", "Error",
                         "Error while starting radio %s on port: %s - Error: %s"
                         % (radiomodule, serialPort, e))
        return

    if self.pluginParameters["Mode3"] == "True":
        self.log.logging("TransportZigpy", "Status",
                         "++ Coordinator initialisation requested Channel %s(0x%02x) "
                         "ExtendedPanId: 0x%016x" % (set_channel, set_channel, set_extendedPanId))
        new_network = True
    else:
        new_network = False

    if self.app and self.use_of_zigpy_persistent_db:
        self.log.logging("TransportZigpy", "Status", "++ Use of Zigpy Persistent Db")
        try:
            await self.app._load_db()
        except Exception as e:
            self.log.logging("TransportZigpy", "Error",
                             "++ Error loading Zigpy Persistent Db: %s" % e)

    try:
        await _radio_startup(self, statistics, pluginconf,
                             use_of_zigpy_persistent_db, new_network, radiomodule)
    except Exception as e:
        self.log.logging("TransportZigpy", "Error", "Error during radio startup: %s" % e)

    self.log.logging("TransportZigpy", "Debug", "Exiting co-rounting radio_start")


# ---------------------------------------------------------------------------
# Per-radio configuration builders
# ---------------------------------------------------------------------------

def ezsp_configuration_setup(self, bellows_conf, serialPort, serial_specifics):
    """Returns the configuration dict for an EZSP (Bellows/Silicon Labs) coordinator."""
    flow_control = serial_specifics.get("FlowControl", None)
    if flow_control == "software":
        flow_control = None

    config = {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH:         serialPort,
            zigpy.config.CONF_DEVICE_BAUDRATE:     serial_specifics.get("Baudrate", 115200),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: flow_control,
        },
        zigpy.config.CONF_NWK: {},
        bellows_conf.CONF_EZSP_CONFIG:    {},
        bellows_conf.CONF_EZSP_POLICIES:  {},
        zigpy.config.CONF_OTA:            {},
        "handle_unknown_devices": True,
    }

    if self.pluginconf.pluginConf.get("EzspAllowUnsecuredRejoins"):
        self.log.logging("TransportZigpy", "Status",
                         "++ Allow Unsecure Rejoins for Aqara devices ...")
        config[bellows_conf.CONF_EZSP_POLICIES]["TRUST_CENTER_POLICY"] = 0x0003

    if self.pluginconf.pluginConf.get("BellowsNoMoreEndDeviceChildren"):
        self.log.logging("TransportZigpy", "Status",
                         "++ Set The maximum number of end device children that "
                         "Coordinater will support to 0")
        config[bellows_conf.CONF_EZSP_CONFIG]["CONFIG_MAX_END_DEVICE_CHILDREN"] = 0

    if self.pluginconf.pluginConf.get("TXpower_set") is not None:
        tx_power = int(self.pluginconf.pluginConf["TXpower_set"])
        self.log.logging("TransportZigpy", "Status", f"++ Setting TX Power to {tx_power} dBm")
        config[bellows_conf.CONF_EZSP_CONFIG]["CONFIG_TX_POWER_MODE"] = 0x3
        self.log.logging("TransportZigpy", "Status",
                         "++ Setting mode of transmission power adjustment 'TX_POWER_MODE_BOOST' dBm")
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_TX_POWER] = tx_power

    return config


def znp_configuration_setup(self, znp_conf, serialPort, serial_specifics):
    """Returns the configuration dict for a ZNP (TI CC2531 / CC2652) coordinator."""
    config = {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH:         serialPort,
            zigpy.config.CONF_DEVICE_BAUDRATE:     serial_specifics.get("Baudrate", 115200),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None),
        },
        zigpy.config.CONF_NWK:          {},
        znp_conf.CONF_ZNP_CONFIG:       {},
        zigpy.config.CONF_OTA:          {},
    }

    if self.pluginconf.pluginConf.get("TXpower_set") is not None:
        tx_power = int(self.pluginconf.pluginConf["TXpower_set"])
        config[znp_conf.CONF_ZNP_CONFIG]["tx_power"] = tx_power
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_TX_POWER] = tx_power

    if specific_endpoints(self):
        config[znp_conf.CONF_ZNP_CONFIG]["prefer_endpoint_1"] = False

    return config


def deconz_configuration_setup(self, deconz_conf, serialPort, serial_specifics):
    """Returns the configuration dict for a deCONZ (Dresden Elektronik) coordinator."""
    return {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH:         serialPort,
            zigpy.config.CONF_DEVICE_BAUDRATE:     serial_specifics.get("Baudrate", 115200),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None),
        },
        zigpy.config.CONF_NWK: {},
        zigpy.config.CONF_OTA: {},
    }


def blz_configuration_setup(self, blz_conf, serialPort, serial_specifics):
    """Returns the configuration dict for a BLZ coordinator (default baudrate 2 Mbps)."""
    return {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH:         serialPort,
            zigpy.config.CONF_DEVICE_BAUDRATE:     serial_specifics.get("Baudrate", 2000000),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None),
        },
        zigpy.config.CONF_NWK: {},
        zigpy.config.CONF_OTA: {},
    }


def optional_configuration_setup(self, config, radio_conf, set_extendedPanId, set_channel):
    """
    Applies cross-radio zigpy settings to the config dict in-place.

    Sets extended PAN ID, channel, source routing, OTA disable, topology scan,
    watchdog, persistent DB, network backup and startup energy scan.
    """
    if set_extendedPanId != 0:
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_EXTENDED_PAN_ID] = (
            "%s" % (t.EUI64(t.uint64_t(set_extendedPanId).serialize()))
        )

    if radio_conf and set_channel != 0:
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_CHANNEL] = set_channel

    if self.pluginconf.pluginConf.get("TXpower_set") is not None:
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_TX_POWER] = int(
            self.pluginconf.pluginConf["TXpower_set"]
        )

    config[zigpy.config.CONF_SOURCE_ROUTING] = bool(self.pluginconf.pluginConf["zigpySourceRouting"])
    config[zigpy.config.CONF_OTA][zigpy.config.CONF_OTA_ENABLED] = False
    config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = False
    config[zigpy.config.CONF_WATCHDOG_ENABLED] = True
    config[zigpy.config.CONF_MAX_CONCURRENT_REQUESTS] = 4

    if self.pluginconf.pluginConf.get("enableZigpyPersistentInFile"):
        data_folder = Path(self.pluginconf.pluginConf["pluginData"])
        config[zigpy.config.CONF_DATABASE] = str(
            data_folder / ("zigpy_persistent_%02d.db" % self.hardwareid)
        )
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = bool(
            self.pluginconf.pluginConf["ZigpyAutoTopology"]
        )
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 12 * 60

    elif self.pluginconf.pluginConf.get("enableZigpyPersistentInMemory"):
        config[zigpy.config.CONF_DATABASE] = ":memory:"
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = bool(
            self.pluginconf.pluginConf["ZigpyAutoTopology"]
        )
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 12 * 60

    if self.pluginconf.pluginConf.get("autoBackup"):
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = True
        config[zigpy.config.CONF_NWK_BACKUP_PERIOD] = self.pluginconf.pluginConf["autoBackup"]
    else:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = False

    if ("EnergyScanAtStatup" in self.pluginconf.pluginConf
            and not self.pluginconf.pluginConf["EnergyScanAtStatup"]):
        config[zigpy.config.CONF_STARTUP_ENERGY_SCAN] = False


# ---------------------------------------------------------------------------
# Post-instantiation startup
# ---------------------------------------------------------------------------

async def _radio_startup(self, statistics, pluginconf, use_of_zigpy_persistent_db,
                         new_network, radiomodule):
    """
    Calls app.startup(), builds network frames, and injects supervisor refs.

    After this function returns, the app is fully initialised and the worker
    loop is ready to accept commands.
    """
    if not self.app:
        self.log.logging("TransportZigpy", "Error",
                         "Error at startup - self.app not initialized")
        return

    try:
        await self.app.startup(
            self.statistics,
            self.hardwareid,
            pluginconf,
            use_of_zigpy_persistent_db,
            callBackHandleMessage=self.receiveData,
            callBackUpdDevice=self.ZigpyUpdDevice,
            callBackGetDevice=self.ZigpyGetDevice,
            callBackBackup=self.ZigpyBackupAvailable,
            callBackRestartPlugin=self.restart_plugin,
            callBackHeartbeat=lambda: _transport_heartbeat(self),
            captureRxFrame=self.captureRxFrame,
            auto_form=True,
            force_form=new_network,
            log=self.log,
            permit_to_join_timer=self.permit_to_join_timer,
        )
    except Exception as e:
        self.log.logging("TransportZigpy", "Error", "Error at startup %s" % e)
        return

    if new_network:
        self.log.logging("TransportZigpy", "Status", "++ Assuming new network formed")
        self.ErasePDMDone = True

    display_network_infos(self)
    self.ControllerData["Network key"] = ":".join(
        f"{c:02x}" for c in self.app.state.network_information.network_key.key
    )

    post_coordinator_startup(self, radiomodule)

    # Inject back-references so AppGeneric can reach the supervisor
    if self.app:
        self.app._supervisor_running = True
        self.app.zigpy_running_ref = self
        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"_radio_startup: supervisor refs injected onto app "
            f"(_supervisor_running=True, zigpy_running_ref={id(self):#x})"
        )


def post_coordinator_startup(self, radiomodule):
    """
    Pushes initial plugin frames after the coordinator is up.

    Sends 0x8009 (network info), 0x8045 (endpoint list), 0x8043 (node
    descriptor per EP), and 0x0302 (simulated off/on) to the forwarder queue.
    """
    self.forwarder_queue.put(build_plugin_8009_frame_content(self, radiomodule))
    self.forwarder_queue.put(build_plugin_8045_frame_list_controller_ep(self))

    self.log.logging("TransportZigpy", "Debug",
                     "Active Endpoint List:  %s"
                     % str(self.app.get_device(nwk=t.NWK(0x0000)).endpoints.keys()))
    for epid, ep in self.app.get_device(nwk=t.NWK(0x0000)).endpoints.items():
        if epid != 0 and ep.status == 0x00:
            self.log.logging("TransportZigpy", "Debug", "Simple Descriptor:  %s" % ep)
            self.forwarder_queue.put(
                build_plugin_8043_frame_list_node_descriptor(self, epid, ep)
            )

    self.log.logging("TransportZigpy", "Debug",
                     "Controller Model %s"
                     % self.app.get_device(nwk=t.NWK(0x0000)).model)
    self.log.logging("TransportZigpy", "Debug",
                     "Controller Manufacturer %s"
                     % self.app.get_device(nwk=t.NWK(0x0000)).manufacturer)
    self.forwarder_queue.put(build_plugin_0302_frame_content(self))


def display_network_infos(self):
    """Logs all key network parameters at Status level."""
    self.log.logging("TransportZigpy", "Status", "++ Network settings")
    self.log.logging("TransportZigpy", "Status",
                     f"  PAN ID:                0x{self.app.state.network_info.pan_id:04X}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Extended PAN ID:       {self.app.state.network_info.extended_pan_id}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Channel:               {self.app.state.network_info.channel}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Channel mask:          {list(self.app.state.network_info.channel_mask)}")
    self.log.logging("TransportZigpy", "Status",
                     f"  NWK update ID:         {self.app.state.network_info.nwk_update_id}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Device IEEE:           {self.app.state.node_info.ieee}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Device NWK:            0x{self.app.state.node_info.nwk:04X}")
    self.log.logging("TransportZigpy", "Status",
                     "  Network key:           "
                     + ":".join(f"{c:02x}"
                                for c in self.app.state.network_information.network_key.key))
    self.log.logging("TransportZigpy", "Status",
                     f"  Network key sequence:  {self.app.state.network_info.network_key.seq}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Network key counter:   {self.app.state.network_info.network_key.tx_counter}")
    self.log.logging("TransportZigpy", "Status",
                     f"  TX Power:             {self.app.state.network_information.tx_power}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Security Level:       {self.app.state.network_information.security_level}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Children:             {self.app.state.network_information.children}")
    self.log.logging("TransportZigpy", "Status",
                     f"  Routers:              {self.app.state.network_information.route_table}")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def specific_endpoints(self):
    """Returns True if any vendor-specific endpoint plugin is enabled."""
    supported_plugins = ["Terncy", "Konke", "Wiser", "Orvibo", "Livolo", "Wiser2"]
    return any(
        plugin in self.pluginconf.pluginConf and self.pluginconf.pluginConf[plugin]
        for plugin in supported_plugins
    )


def _import_class(dotted_path: str):
    """
    Imports and returns a class from a dotted module path string.

    Example: 'Classes.ZigpyTransport.AppBellows.App_bellows'
    """
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
