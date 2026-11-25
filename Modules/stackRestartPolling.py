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
Read the state of the devices after a restart of the Zigbee stack.

While the stack restarts (coordinator unplugged, connection lost), the commands and the polling that follows
them are dropped with the writer queue, and nothing is received. The widget of a device commanded from
Domoticz or by hand meanwhile would be wrong until the device reports by itself.

No plugin dependency: the heartbeat hands over which devices to read and how.
"""

DEVICES_PER_HEARTBEAT = 5  # the heartbeat is every 5 seconds


def poll_devices_after_stack_restart(self, has_status_to_poll, poll_device):
    """
    Called at each heartbeat. After a restart of the stack, poll a few devices at a time.

    Same devices and same setting (forcePollingAfterAction) as the polling after an action. The first start
    of the stack is not a restart.

    Args:
        has_status_to_poll: (self, nwkid) -> bool, is this device one to poll
        poll_device: (self, nwkid) -> bool, True when the system is too busy and nothing was sent
    """
    stack_starts = getattr(self.ControllerLink, "stack_starts", 0)
    if stack_starts != self.stack_starts_seen:
        restarted = self.stack_starts_seen != 0
        self.stack_starts_seen = stack_starts
        if restarted and self.pluginconf.pluginConf["forcePollingAfterAction"]:
            _list_devices_to_poll(self, has_status_to_poll)

    polled = 0
    for nwkid in list(self.devices_to_poll_after_restart):
        if polled >= DEVICES_PER_HEARTBEAT:
            return

        device = self.ListOfDevices.get(nwkid, {})
        if device.get("Health") == "Not Reachable":
            # Never polled: it stays in the list until it announces itself or sends a message
            continue

        # Out of the list first: an exception must not bring the same device back at each heartbeat
        self.devices_to_poll_after_restart.remove(nwkid)

        if device.get("Status") != "inDB" or device.get("Health") == "Disabled":
            # Removed, renumbered or disabled since the restart
            continue

        if poll_device(self, nwkid):
            # Too busy, next heartbeat
            self.devices_to_poll_after_restart.insert(0, nwkid)
            return

        polled += 1


def _list_devices_to_poll(self, has_status_to_poll):
    self.devices_to_poll_after_restart = [
        nwkid for nwkid in list(self.ListOfDevices.keys())
        if nwkid not in ("ffff", "0000") and has_status_to_poll(self, nwkid)
    ]
    reachable = sum(
        self.ListOfDevices[nwkid].get("Health") != "Not Reachable" for nwkid in self.devices_to_poll_after_restart
    )
    self.log.logging("Heartbeat", "Status", f"Zigbee stack restarted, reading the state of {reachable} device(s)")
