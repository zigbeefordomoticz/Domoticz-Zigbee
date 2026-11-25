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
lostCommands.py — Warn about the commands dropped while the Zigbee stack restarts.

What is in the writer queue when the stack (re)starts is never sent: an old order may no longer be wanted.
The user is told which device did not receive its order.

  report_lost_commands — empty the writer queue, before it is replaced
  report_lost_command  — one command taken from the writer queue and not sent
"""

import contextlib
import json
import queue

from Modules.tools_fcf import fcf_direction, frame_type, retreive_cmd_payload_from_8002

ZDP_PROFILE = 0x0000
GLOBAL_FRAME = 0
CLUSTER_SPECIFIC_FRAME = 1
CLIENT_TO_SERVER = 0

# Global commands which change the device: Write Attributes, Undivided, No Response
WRITE_ATTRIBUTES_COMMANDS = ("02", "03", "05")

# Cluster commands which only read, as the polling does: Tuya data query, Tuya MCU version
READ_ONLY_CLUSTER_COMMANDS = {0xEF00: ("03", "10")}

GROUP_ADDRESS_MODE = 0x01


def report_lost_commands(self):
    """Empty the writer queue, with one Warning per order to a device or to a group."""
    if self.writer_queue is None:
        return

    while not self.writer_queue.empty():
        try:
            command = self.writer_queue.get_nowait()
        except queue.Empty:
            return
        report_lost_command(self, command)


def report_lost_command(self, command):
    """
    Log a Warning if this entry of the writer queue is an order to a device or to a group.

    Nothing is logged for what the plugin sends on its own (reads, replies, network management), nor when the
    plugin stops. Never raises: it must not prevent the stack from restarting.
    """
    if self._zigpy_stop_requested or command == "STOP":
        return

    try:
        message = json.loads(command)
        if message["cmd"] != "RAW-COMMAND" or not is_an_order(message["datas"]):
            return
        _log_lost_order(self, message["datas"])

    except Exception as e:
        with contextlib.suppress(Exception):
            self.log.logging("TransportZigpy", "Debug", f"report_lost_command: cannot read {command}: {e!r}")


def is_an_order(datas):
    """True for a ZCL frame which acts on the device: cluster command or write attributes, client to server."""
    if datas["Profile"] == ZDP_PROFILE:
        return False

    payload = datas["payload"]
    fcf = payload[:2]
    if fcf_direction(fcf) != CLIENT_TO_SERVER:
        return False

    zcl_command = (retreive_cmd_payload_from_8002(payload)[4] or "").lower()

    if frame_type(fcf) == GLOBAL_FRAME:
        return zcl_command in WRITE_ATTRIBUTES_COMMANDS

    if frame_type(fcf) == CLUSTER_SPECIFIC_FRAME:
        return zcl_command not in READ_ONLY_CLUSTER_COMMANDS.get(datas["Cluster"], ())

    return False


def _log_lost_order(self, datas):
    nwkid = "%04x" % datas["TargetNwk"]
    if datas["AddressMode"] == GROUP_ADDRESS_MODE:
        destination = f"group {nwkid}"
    else:
        destination = f"{self.ZigpyGetDeviceName(nwkid)} ({nwkid}/{datas['TargetEp']:02x})"

    self.log.logging(
        "TransportZigpy", "Warning",
        f"Command lost, not sent to {destination}: the Zigbee stack was restarting "
        f"({datas['Function']}, Cluster: {datas['Cluster']:04x})",
        nwkid,
    )
