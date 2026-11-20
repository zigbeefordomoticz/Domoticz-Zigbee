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
"""
greenPower.py — zigpy Green Power events to plugin frames.

zigpy (> 2.3.0, #1848) commissions Green Power devices (GPD) itself and
reports them as application events, and each accepted GPDF as a
`gp_command_received` event on the device. A GPD sends no Device_annce and
no ZCL, so packet_received() never sees one: this listener is the only way
the plugin learns about them.

Events are turned into 9exx plugin frames and handed to callBackFunction
(Transport.receiveData), which only queues them for the forwarder thread:
nothing here blocks the event loop.

    device_initialized(dev)    new GPD                → 9e00
    device_reinterviewed(dev)  GPD commissioned again → 9e00 (recommissioned)
    device_removed(dev)        GPD removed            → 9e02
    gp_command_received        GPD command            → 9e01

The pairing feed (report_gp_packet / report_gp_window, below) adds 9e03 and
9e04.

The application events also fire for Zigbee devices; they are ignored here.
device_joined is not used: it fires before zigpy finalises the device, and
device_initialized follows immediately with the final object.

zigpy logs listener exceptions at DEBUG only, so every handler logs its own.
"""

import traceback

import zigpy.device

from Classes.ZigpyTransport.plugin_encoders import (
    GP_HEARD_ENCRYPTED, GP_HEARD_KNOWN, GP_HEARD_RSSI, GP_HEARD_VIA_PROXY,
    GP_HEARD_WINDOW_OPEN, build_plugin_9e00_frame_content,
    build_plugin_9e01_frame_content, build_plugin_9e02_frame_content,
    build_plugin_9e03_frame_content, build_plugin_9e04_frame_content)

# Absent from zigpy before 2.3.0
GREEN_POWER_DEVICE = getattr(zigpy.device, "GreenPowerDevice", None)
GP_COMMAND_EVENT = "gp_command_received"


def is_green_power_device(device):
    return GREEN_POWER_DEVICE is not None and isinstance(device, GREEN_POWER_DEVICE)


class GreenPowerListener:
    """zigpy application listener for Green Power devices."""

    def __init__(self, app):
        self._app = app
        # ieee -> unsubscribe callable of the device's gp_command_received handler
        self._unsubscribe = {}

    def attach(self, device):
        """Forward the device's commands. Also used for GPDs restored at startup."""
        self.detach(device.ieee)
        self._unsubscribe[device.ieee] = device.on_event(GP_COMMAND_EVENT, lambda event: self._on_command(device, event))

    def detach(self, ieee):
        unsubscribe = self._unsubscribe.pop(ieee, None)
        if unsubscribe is not None:
            unsubscribe()

    def device_initialized(self, device):
        if not is_green_power_device(device):
            return
        try:
            self._app.log.logging("GreenPower", "Status", "Green Power device commissioned %s" % (device,))
            self.attach(device)
            self._app.callBackFunction(build_plugin_9e00_frame_content(self._app, device, recommissioned=False))
        except Exception as e:
            self._log_error("device_initialized", device, e)

    def device_reinterviewed(self, device):
        if not is_green_power_device(device):
            return
        try:
            self._app.log.logging("GreenPower", "Status", "Green Power device commissioned again %s" % (device,))
            # Replaces the handler of the previous device object
            self.attach(device)
            self._app.callBackFunction(build_plugin_9e00_frame_content(self._app, device, recommissioned=True))
        except Exception as e:
            self._log_error("device_reinterviewed", device, e)

    def device_removed(self, device):
        if not is_green_power_device(device):
            return
        try:
            self._app.log.logging("GreenPower", "Status", "Green Power device removed %s" % (device,))
            self.detach(device.ieee)
            self._app.callBackFunction(build_plugin_9e02_frame_content(self._app, device))
        except Exception as e:
            self._log_error("device_removed", device, e)

    def _on_command(self, device, event):
        try:
            self._app.log.logging("GreenPower", "Debug", "Green Power command 0x%02x from %s" % (event.command_id, device))
            self._app.callBackFunction(
                build_plugin_9e01_frame_content(self._app, device, event.endpoint_id, event.command_id, event.command)
            )
        except Exception as e:
            self._log_error("gp_command_received", device, e)

    def _log_error(self, event_name, device, error):
        self._app.log.logging("GreenPower", "Error", "Green Power %s for %s failed: %s\n%s" % (
            event_name, device, error, traceback.format_exc()))


# ─── Pairing feed (Admin → Provisioning) ─────────────────────────────────────
#
# What the user cannot see without the logs while pairing a GPD: which GPDFs
# reach the network, and whether the commissioning window is open.
#
#   report_gp_packet()  a GPDF, from AppGeneric.gp_packet_received()  → 9e03
#   report_gp_window()  the window, from AppGeneric.permit_gp()       → 9e04
#
# A GPDF is reported only while the window is open, or when its GPD is not
# commissioned: the commands of a paired GPD in daily use are not.


def _gp_packet_ieee(packet):
    """The EUI64 zigpy registers the GPD of a GPDF under (synthetic for a SrcID GPD)."""
    import zigpy.zgp.types as zgp_t
    import zigpy.zgp.util as zgp_util

    if packet.application_id is zgp_t.ApplicationID.SrcID:
        return None if packet.src_id is None else zgp_util.synthetic_ieee(packet.src_id)
    return packet.ieee


def report_gp_packet(app, packet):
    """Report a GPDF zigpy received to the pairing feed. Never raises: zigpy must still get it."""
    try:
        import zigpy.types as t
        import zigpy.zgp.types as zgp_t

        ieee = _gp_packet_ieee(packet)
        if ieee is None or packet.command_id is None:
            return

        known = is_green_power_device(app.devices.get(ieee))
        green_power = getattr(app, "green_power", None)
        window_open = bool(green_power is not None and green_power.is_commissioning)
        if known and not window_open:
            return

        flags = GP_HEARD_KNOWN if known else 0
        if window_open:
            flags |= GP_HEARD_WINDOW_OPEN
        if packet.security_status is zgp_t.SecurityStatus.Unprocessed and packet.security_level is zgp_t.SecurityLevel.Encrypted:
            flags |= GP_HEARD_ENCRYPTED
        if packet.gpp_short_addr is not None:
            flags |= GP_HEARD_VIA_PROXY
        if packet.rssi is not None:
            flags |= GP_HEARD_RSSI

        app.callBackFunction(build_plugin_9e03_frame_content(
            app, t.uint64_t.deserialize(ieee.serialize())[0], int(packet.command_id), flags,
            None if packet.gpp_short_addr is None else int(packet.gpp_short_addr), packet.rssi, packet.lqi))
    except Exception as e:
        app.log.logging("GreenPower", "Error", "Green Power pairing feed: GPDF not reported: %s\n%s" % (e, traceback.format_exc()))


def report_gp_window(app, state, seconds=0):
    """Report the commissioning window (GP_WINDOW_*) to the pairing feed."""
    try:
        app.callBackFunction(build_plugin_9e04_frame_content(app, state, seconds))
    except Exception as e:
        app.log.logging("GreenPower", "Error", "Green Power pairing feed: window not reported: %s\n%s" % (e, traceback.format_exc()))


def register_green_power_listener(app):
    """Register the listener once, when zigpy supports Green Power."""
    if getattr(app, "green_power", None) is None or getattr(app, "z4d_gp_listener", None) is not None:
        return
    app.z4d_gp_listener = GreenPowerListener(app)
    app.add_listener(app.z4d_gp_listener)


# ─── Restore at startup ──────────────────────────────────────────────────────
#
# zigpy runs with an in-memory database, so after a restart it knows no GPD.
# The plugin keeps them in its Green Power device store (Modules/greenPowerStore.py)
# and hands them back here, from initialize(), after the Zigbee devices are
# pre-loaded and before green_power.startup().
#
# There is no public zigpy API to add a known GPD: gp_device_from_record()
# replicates zigpy.appdb.PersistingListener._load_gp_devices() and
# restore_green_power_devices() its listener registration. Re-check both on
# every zigpy bump.


def _eui64_from_hex(ieee_hex):
    import zigpy.types as t
    return t.EUI64(t.uint64_t(int(ieee_hex, 16)).serialize())


def gp_device_from_record(app, record):
    """Build a zigpy GreenPowerDevice from a Green Power device store record."""
    import zigpy.types as t
    from zigpy.zgp.commands import GPGenericSwitchConfiguration
    from zigpy.zgp.types import (ApplicationID, DeviceID, GPDCommandID,
                                 SecurityKeyType, SecurityLevel, SrcID)

    def optional(cast, value):
        return None if value is None else cast(value)

    device = GREEN_POWER_DEVICE(
        app,
        application_id=ApplicationID(record["application_id"]),
        src_id=optional(SrcID, record.get("src_id")),
        ieee=_eui64_from_hex(record["ieee"]),
    )
    device.device_id = optional(DeviceID, record.get("device_id"))
    device.gpd_manufacturer_id = optional(t.uint16_t, record.get("manufacturer_id"))
    device.gpd_model_id = optional(t.uint16_t, record.get("model_id"))
    device.commands = [GPDCommandID(c) for c in record.get("commands") or []]
    device.server_cluster_ids = [t.uint16_t(c) for c in record.get("server_clusters") or []]
    device.client_cluster_ids = [t.uint16_t(c) for c in record.get("client_clusters") or []]
    device.switch_configuration = optional(GPGenericSwitchConfiguration, record.get("switch_configuration"))
    device.mac_seq_num_capability = bool(record.get("mac_seq_num_capability"))
    device.rx_on_capability = bool(record.get("rx_on_capability"))
    device.fixed_location = bool(record.get("fixed_location"))
    device.security_key = optional(lambda key: t.KeyData(bytes.fromhex(key)), record.get("security_key"))
    device.security_key_type = optional(SecurityKeyType, record.get("security_key_type"))
    device.security_level = optional(SecurityLevel, record.get("security_level"))
    device.frame_counter = optional(t.uint32_t, record.get("frame_counter"))
    if record.get("LastSeen"):
        device.last_seen = record["LastSeen"]
    return device


def _register_restored_device(app, device):
    """Register a restored GPD as zigpy's database load does, without commissioning events."""
    app.devices[device.ieee] = device
    dblistener = getattr(app, "_dblistener", None)
    if dblistener is not None:
        device.add_context_listener(dblistener)
        dblistener.register_gp_device_events(device)

    listener = getattr(app, "z4d_gp_listener", None)
    if listener is not None:
        listener.attach(device)


def _raise_frame_counter(app, device, record):
    """A GPD zigpy already knows (file database): only ever raise its frame counter."""
    import zigpy.types as t

    stored = record.get("frame_counter")
    if stored is not None and (device.frame_counter is None or stored > device.frame_counter):
        device.frame_counter = t.uint32_t(stored)
        return True
    return False


async def restore_green_power_devices(app):
    """
    Hand the GPDs of the plugin store back to zigpy, then start zigpy's Green
    Power manager (joins the GP group when it knows a GPD).

    Never raises: a failure is logged and startup goes on without the GPDs.
    """
    if getattr(app, "green_power", None) is None or GREEN_POWER_DEVICE is None:
        return

    get_records = getattr(app, "callBackGetAllGpDevices", None)
    try:
        records = get_records() if get_records is not None else []
    except Exception as e:
        app.log.logging("GreenPower", "Error", "Green Power devices not restored, plugin store not readable: %s" % type(e).__name__,
                        None, {"Error code": "GPSTORE-RESTORE-04"})
        records = []

    restored = kept = 0
    for record in records:
        ieee_hex = record.get("ieee")
        try:
            ieee = _eui64_from_hex(ieee_hex)
            existing = app.devices.get(ieee)
            if existing is None:
                _register_restored_device(app, gp_device_from_record(app, record))
                restored += 1
            elif is_green_power_device(existing):
                if _raise_frame_counter(app, existing, record):
                    app.log.logging("GreenPower", "Debug", "Green Power device %s known to zigpy, frame counter raised from the plugin store" % ieee_hex, record.get("nwk"))
                kept += 1
            else:
                app.log.logging("GreenPower", "Error", "Green Power device %s not restored: zigpy has a Zigbee device with that IEEE" % ieee_hex,
                                record.get("nwk"), {"Error code": "GPSTORE-RESTORE-02"})
        except Exception as e:
            # Never log the record: it holds the security key
            app.log.logging("GreenPower", "Error", "Green Power device %s not restored: %s" % (ieee_hex, type(e).__name__),
                            record.get("nwk"), {"Error code": "GPSTORE-RESTORE-01"})

    if records:
        app.log.logging("GreenPower", "Status", "Green Power: %d device(s) restored into zigpy, %d already known" % (restored, kept))

    try:
        await app.green_power.startup()
    except Exception as e:
        app.log.logging("GreenPower", "Error", "Green Power startup failed: %s\n%s" % (e, traceback.format_exc()),
                        None, {"Error code": "GPSTORE-RESTORE-03"})
