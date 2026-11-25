#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Copies of a ZCL frame: the same frame sent again by the device.

A copy is a frame from the same device, endpoint and cluster, with an identical ZCL payload
(frame control, sequence number, command and data), received within DUPLICATE_WINDOW seconds
of the first one.

A device usually sends a copy because it did not get the answer to the first frame. A copy
must therefore be answered like the first frame:
 - it gets the same Default Response, if the first frame got one,
 - a frame the plugin answers with a command of its own is never considered as a copy.

The frames are kept in memory only, in plugin.zcl_recent_frames.
"""

import time

from Zigbee.helperDefautResponse import (
    response_required_commands, server_to_client_response_required_commands)

# Seconds. Copies have been seen from 200 ms to 2.9 s after the first frame.
DUPLICATE_WINDOW = 3.0

OTA_CLUSTER = "0019"

# General commands which are requests: the answer is a response command, not a Default Response.
GENERAL_REQUESTS = {
    "00",  # Read Attributes
    "02",  # Write Attributes
    "03",  # Write Attributes Undivided
    "06",  # Configure Reporting
    "08",  # Read Reporting Configuration
    "0c",  # Discover Attributes
    "0e",  # Read Attributes Structured
    "0f",  # Write Attributes Structured
    "11",  # Discover Commands Received
    "13",  # Discover Commands Generated
    "15",  # Discover Attributes Extended
}

# Cluster-specific commands answered by the plugin, in addition to helperDefautResponse:
# cluster -> commands, None for all of them
ANSWERED_CLUSTER_COMMANDS = {
    "0501": {"00", "01", "05", "06", "07", "08", "09"},  # IAS ACE: Arm, Bypass, Get ...
    "ed00": None,          # Zosung IR code transfer, each command is answered by the next one
    "ef00": {"24", "25"},  # Tuya: time synchronisation, gateway status
    "fc01": None,          # Legrand: group membership of the remotes
}


class _RecentFrame:
    """Last frame received for a (device, endpoint, cluster, sequence number, command)."""

    __slots__ = ("payload", "received", "default_response")

    def __init__(self, payload, received):
        self.payload = payload
        self.received = received
        self.default_response = None  # arguments of the Default Response sent for this frame


def has_own_response(fcf, cluster_id, command):
    """True when the plugin answers this frame with something else than a Default Response."""
    if cluster_id == OTA_CLUSTER:
        return True

    frame_control = int(fcf, 16)
    if frame_control & 0x03 == 0x00:
        return command in GENERAL_REQUESTS

    if cluster_id in ANSWERED_CLUSTER_COMMANDS:
        commands = ANSWERED_CLUSTER_COMMANDS[cluster_id]
        return commands is None or command in commands

    server_to_client = frame_control & 0x08
    answered = server_to_client_response_required_commands if server_to_client else response_required_commands
    return int(command, 16) in answered.get(int(cluster_id, 16), ())


def find_first_frame(self, nwkid, endpoint, cluster_id, payload, sqn, command):
    """Return the _RecentFrame this frame is a copy of.

    Return None when this frame is not a copy, after recording it as a first frame.
    """
    if not is_filter_enabled(self) or nwkid not in self.ListOfDevices:
        return None

    # A sequence number which is always 00 says nothing: such a device would lose real frames.
    if not sqn or sqn == "00" or not command or has_own_response(payload[:2], cluster_id, command):
        return None

    now = time.monotonic()
    recent_frames = self.zcl_recent_frames
    _forget_old_frames(recent_frames, now)

    key = (nwkid, endpoint, cluster_id, sqn, command)
    first_frame = recent_frames.get(key)
    if first_frame is not None and first_frame.payload == payload:
        return first_frame

    # pop, so that the dictionary stays ordered by reception time
    recent_frames.pop(key, None)
    recent_frames[key] = _RecentFrame(payload, now)
    return None


def remember_default_response(self, nwkid, endpoint, cluster_id, sqn, command, arguments):
    """Record the Default Response sent for a frame, so that it can be sent again for a copy."""
    frame = getattr(self, "zcl_recent_frames", {}).get((nwkid, endpoint, cluster_id, sqn, command))
    if frame is not None:
        frame.default_response = arguments


def is_filter_enabled(self):
    return self.zigbee_communication == "zigpy" and self.pluginconf.pluginConf.get("enableZclDuplicatecheck", False)


def _forget_old_frames(recent_frames, now):
    while recent_frames:
        oldest = next(iter(recent_frames))
        if now - recent_frames[oldest].received <= DUPLICATE_WINDOW:
            return
        del recent_frames[oldest]
