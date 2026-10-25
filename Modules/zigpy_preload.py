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
    Module: zigpy_preload.py

    Description: Which of the plugin's devices are handed to zigpy's device
    table when the plugin starts.

    A device the plugin has recorded as gone from the network has no business
    in that table: zigpy would carry it for the lifetime of the process and ask
    it for its neighbour and routing tables in every topology scan, paying the
    full retry cost each time for a device nobody expects to answer.

    The decision is kept free of any plugin dependency so that it can be unit
    tested on its own: the device record is passed in by zigpy_get_all_devices().
"""

# Lifecycle states in which the plugin has recorded that the device is no longer
# part of the network.
#
# "Leave"   the device announced its departure (0x8048) and has not come back.
#           zigpy_get_device() already refuses to resolve such a device, so
#           leaving it out of the pre-load is the same answer given earlier.
# "Removed" the device was removed from the plugin, down to its last widget
#           (see Modules/tools_device_lifecycle.py).
#
# Every other state is left alone, including the ones a half-finished pairing
# leaves behind: an incomplete record is not evidence that the device is gone,
# and a device absent from zigpy's table is one the plugin cannot talk to.
DEPARTED_STATUSES = ("Leave", "Removed")


def device_has_left_the_network(device_record):
    """Return True when the plugin has this device recorded as gone.

    device_record is one ListOfDevices entry. Anything that is not a mapping,
    or that carries no usable Status, reads as still present: the pre-load is
    not the place to decide that a malformed record means a departed device.
    """

    try:
        status = device_record.get("Status")
    except AttributeError:
        return False

    return status in DEPARTED_STATUSES
