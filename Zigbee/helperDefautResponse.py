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

from typing import Dict, Set

# ----------------------------------------------------------
# Zigbee ZCL: Commands that REQUIRE a specific response
# ----------------------------------------------------------
# Format:
#   response_required_commands[cluster_id] = {command_ids...}
#
# IMPORTANT:
# Only *client→server* commands that require a response are listed here.
# Default Response must NOT be sent for these commands unless an error occurs.
#
# You can extend this dictionary with manufacturer-specific clusters.
# ----------------------------------------------------------
response_required_commands = {
    # ------------------------------------------------------
    # ZCL General Cluster (0x0000)
    # ------------------------------------------------------
    0x0000: {
        0x00,  # Read Attributes
        0x02,  # Read Reporting Config
        0x0C,  # Discover Commands Received
        0x0E,  # Discover Commands Generated
    },

    # ------------------------------------------------------
    # Groups Cluster (0x0004)
    # ------------------------------------------------------
    0x0004: {
        0x00,  # Add Group
        0x01,  # View Group
        0x02,  # Get Group Membership
        0x03,  # Remove Group
    },

    # ------------------------------------------------------
    # Scenes Cluster (0x0005)
    # ------------------------------------------------------
    0x0005: {
        0x00, 0x01, 0x02, 0x03, 0x04,
        0x06,
    },

    # ------------------------------------------------------
    # Poll Control (0x0020)
    # ------------------------------------------------------
    0x0020: {
        0x01,  # Fast Poll Stop
        0x02,  # Set Long Poll Interval
        0x03,  # Set Short Poll Interval
    },

    # ------------------------------------------------------
    # Thermostat Cluster (0x0201)
    # ------------------------------------------------------
    0x0201: {
        0x02,  # Get Weekly Schedule
        0x04,  # Get Relay Status Log
    },

    # ------------------------------------------------------
    # Smart Energy Metering (0x0702)
    # ------------------------------------------------------
    0x0702: {
        0x00, 0x01, 0x02, 0x03,
        0x04, 0x05, 0x07, 0x08,
    },

    # ------------------------------------------------------
    # Electrical Measurement (0x0B04)
    # ------------------------------------------------------
    0x0B04: {
        0x00,  # Get Profile Info
        0x01,  # Get Measurement Profile
    },

    # ------------------------------------------------------
    # OTA Cluster (0x0019) – special handling
    # ------------------------------------------------------
    0x0019: {
        0x00, 0x01, 0x02, 0x04, 0x06
    },
}


def must_send_default_response(
    frame_control: int,
    command_id: int,
    cluster_id: int,
    status: int = 0x00
) -> bool:
    """
    Determine whether a Zigbee Default Response must be sent.

    This follows ZCL 3.3.2.4:
    - A Default Response is sent only if:
        1. Disable Default Response bit is not set
        2. The command does not expect a specific response
        3. OR: The command expects a specific response but an error occurred

    Args:
        frame_control (int): ZCL Frame Control byte.
        command_id (int): The received ZCL command ID.
        cluster_id (int): Cluster ID.
        status (int): Execution status (0x00 = SUCCESS).

    Returns:
        bool: True if a Default Response must be sent.
    """

    # ------------------------------------------------------
    # 1) Check Disable Default Response bit in Frame Control
    # ------------------------------------------------------
    disable_default_response = bool(frame_control & 0x10)
    if disable_default_response:
        return False

    # ------------------------------------------------------
    # 2) Special handling for OTA cluster (0x0019)
    # ------------------------------------------------------
    if cluster_id == 0x0019:
        if status != 0x00:      # On error → Respond with DR
            return True
        return False            # Otherwise OTA uses dedicated responses

    # ------------------------------------------------------
    # 3) Command expects a dedicated response?
    # ------------------------------------------------------
    commands_for_cluster = response_required_commands.get(cluster_id)

    if commands_for_cluster is not None:
        if command_id in commands_for_cluster:
            if status != 0x00:   # If error → default response must be sent
                return True
            return False         # Success → dedicated response will be sent

    # ------------------------------------------------------
    # 4) No dedicated response → Must send Default Response
    # ------------------------------------------------------
    return True
