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
Green Power devices (GPD) on the Domoticz side: removal, commands and the
start-up consistency check. A GPD is identified by its synthetic IEEE, the
key of the Green Power device store (Modules/greenPowerStore.py) and the
DeviceID of its Domoticz widgets. It is never in ListOfDevices / IEEE2NWK.

Removal goes through zigpy (REMOVE-DEVICE → app.remove()), which unpairs
the GPD from the proxies. Never a ZDO Leave: a GPD is not a Zigbee node.
"""

from Modules.domoticzAbstractLayer import domo_other_units, domo_read_Name
from Modules.greenPowerStore import gp_store, request_gp_store_flush


def is_green_power_device_id(self, DeviceID):
    store = gp_store(self)
    return store is not None and DeviceID in store


def remove_green_power_device(self, ieee):
    """
    Forget a GPD: drop it from the store (written at the next heartbeat) and
    have zigpy remove it, which unpairs it from the proxies.

    The record is dropped here rather than on the 9e02 zigpy sends back, so
    that a GPD zigpy no longer knows (restore failed) is forgotten all the same.
    """
    store = gp_store(self)
    if store is None or ieee not in store:
        return False

    nwk = (store.get(ieee) or {}).get("nwk")
    store.delete(ieee)
    request_gp_store_flush(self)

    if self.zigbee_communication == "zigpy" and self.ControllerLink is not None:
        self.ControllerLink.sendData("REMOVE-DEVICE", {"Param1": int(ieee, 16)})

    self.log.logging("GreenPower", "Status", "Green Power device %s removed" % ieee, nwk)
    return True


def green_power_widget_removed(self, Devices, DeviceID, Unit):
    """onDeviceRemoved() for a GPD widget: the GPD goes with its last widget."""
    remaining = domo_other_units(self, Devices, DeviceID, Unit)
    if remaining:
        self.log.logging("GreenPower", "Log", "Green Power device %s: widget %s removed, %s left" % (DeviceID, Unit, sorted(remaining)))
        return

    self.log.logging("GreenPower", "Status", "Green Power device %s: last widget removed (%s)" % (
        DeviceID, domo_read_Name(self, Devices, DeviceID, Unit)))
    remove_green_power_device(self, DeviceID)


def green_power_widget_command(self, DeviceID, Unit, Command):
    """onCommand() for a GPD widget: a GPD only sends, it cannot be commanded."""
    self.log.logging("GreenPower", "Log", "Green Power device %s: command %s on widget %s ignored, Green Power devices only send" % (
        DeviceID, Command, Unit))
