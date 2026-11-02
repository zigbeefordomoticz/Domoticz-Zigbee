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
Green Power device store: the plugin's record of the Green Power devices
(GPD) commissioned by zigpy, kept apart from ListOfDevices.

A GPD is not a Zigbee node: no ZDO, no endpoints to interview, no ZCL
attributes. zigpy runs with an in-memory database, so the plugin is what
remembers a GPD across restarts, and hands it back to zigpy at startup.

PluginStore "GreenPowerDevices" (Classes/PluginStore.py), declared in
Modules/database.py PLUGIN_STORES:

    key     synthetic IEEE of the GPD, 16 lowercase hex digits
    record  the zigpy GreenPowerDevice fields carried by the 9e00 frame
            (GP_DEVICE_FIELDS; the columns of zigpy's gp_devices table),
            plus plugin fields:
              Commissioned  time of the first commissioning (epoch seconds)
              LastSeen      time of the last frame (epoch seconds)
              LQI           LQI of the last frame

The record holds the GPD security key ("security_key", hex): never log a
record or the store content.

Write cadence: a commissioning or a removal asks for a flush at the next
heartbeat; frame counter, LastSeen and LQI follow the periodic flush
(DATABASE_FLUSH_PERIOD). A frame counter lost on a crash only widens the
replay window back to the last flush.
"""

GP_STORE_NAME = "GreenPowerDevices"
GP_STORE_VERSION = 1

# zigpy GreenPowerDevice fields, as named in the 9e00 record
GP_DEVICE_FIELDS = (
    "ieee",
    "nwk",
    "application_id",
    "src_id",
    "device_id",
    "manufacturer_id",
    "model_id",
    "commands",
    "server_clusters",
    "client_clusters",
    "switch_configuration",
    "mac_seq_num_capability",
    "rx_on_capability",
    "fixed_location",
    "security_level",
    "security_key_type",
    "security_key",
    "frame_counter",
)


def gp_store(self):
    """The Green Power device store, or None before load_plugin_stores()."""
    return getattr(self, "PluginStores", {}).get(GP_STORE_NAME)


def gp_devices_for_zigpy(self):
    """Copies of the stored GPD records, handed to the zigpy transport at startup."""
    store = gp_store(self)
    if store is None:
        return []
    return list(store.snapshot().values())


def request_gp_store_flush(self):
    """
    Have the store written at the next heartbeat, with the device list.

    Same flag as Modules.database.request_flush_plugin_listofdevices(), set
    here so that the Green Power decoder does not import Modules.database.
    """
    self.flush_list_of_devices = True


def gp_device_record(frame_record, now, lqi, previous=None):
    """
    Store record for a GPD commissioned (or commissioned again).

    Args:
        frame_record: The decoded 9e00 record.
        now:          Epoch seconds.
        lqi:          LQI of the 9e00 frame.
        previous:     The stored record when the GPD is commissioned again:
                      its commissioning time is kept, everything zigpy
                      reports (key, frame counter, ...) is replaced.
    """
    record = {field: frame_record.get(field) for field in GP_DEVICE_FIELDS}
    record["Commissioned"] = previous.get("Commissioned", now) if previous else now
    record["LastSeen"] = now
    record["LQI"] = lqi
    return record


def gp_command_fields(frame_counter, now, lqi):
    """Fields of the stored record updated by a GPD command (9e01)."""
    return {"frame_counter": frame_counter, "LastSeen": now, "LQI": lqi}
