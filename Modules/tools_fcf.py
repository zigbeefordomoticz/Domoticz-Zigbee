#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""FCF (Frame Control Field) helpers extracted from tools.py"""

from typing import Optional

from Modules.tools_primitives import is_hex


# Function to manage 0x8002 payloads
def retreive_cmd_payload_from_8002(Payload):

    ManufacturerCode = None
    if len(Payload) < 2:
        return (None, None, None, None, None, None)
    
    fcf = Payload[:2]

    try:
        GlobalCommand = is_globalcommand(fcf)
        zbee_zcl_ddr = disable_default_response(fcf)
    except Exception as e:
        return (None, None, None, None, None, None)
                  
    if GlobalCommand is None:
        return (None, None, None, None, None, None)

    if len(Payload) < 6:
        return (None, None, None, None, None, None)

    if is_manufspecific_8002_payload(fcf):
        ManufacturerCode = Payload[4:6] + Payload[2:4]
        Sqn = Payload[6:8]
        Command = Payload[8:10]
        Data = Payload[10:]
    else:
        Sqn = Payload[2:4]
        Command = Payload[4:6]
        Data = Payload[6:]

    return (zbee_zcl_ddr, GlobalCommand, Sqn, ManufacturerCode, Command, Data)


def decode_fcf(fcf: str) -> Optional[dict]:
    fcf = int(fcf,16)

    frame_type = fcf & 0b00000011
    manuf_spec = (fcf >> 2) & 0b1
    direction = (fcf >> 3) & 0b1
    disable_def_resp = (fcf >> 4) & 0b1

    frame_types = {0: "Profile-wide", 1: "Cluster-specific", 2: "Reserved", 3: "Reserved"}
    directions = {0: "Client→Server", 1: "Server→Client"}

    return {
        "Frame Type": frame_types[frame_type],
        "Manufacturer Specific": bool(manuf_spec),
        "Direction": directions[direction],
        "Disable Default Response": bool(disable_def_resp),
    }


def fcf_direction(fcf: str) -> Optional[int]:
    """
    Extract the direction bit from the Frame Control Field (FCF).

    Direction bit:
      - 0: Client to Server
      - 1: Server to Client

    Args:
        fcf (str): A 2-character hex string representing the FCF byte.

    Returns:
        int: 0 or 1 depending on direction.
        None: If input is invalid.
    """
    if not is_hex(fcf) or len(fcf) != 2:
        return None
    return (int(fcf, 16) & 0x08) >> 3


def disable_default_response(fcf):
    """
    Returns the 'Disable Default Response' bit from the FCF.

    Args:
        fcf (str): 2-char hex string representing the FCF byte.

    Returns:
        int: 0 or 1 (bit value)
        None: if input invalid
    """
    return (int(fcf,16) & 0x10) >> 4


def is_direction_to_client(fcf):
    return fcf_direction(fcf) == 0x1


def is_direction_to_server(fcf):
    return fcf_direction(fcf) == 0x0


def is_globalcommand(fcf):
    """
    Returns True if frame type is Global Command (bits 0-1 == 0).

    Args:
        fcf (str): 2-char hex string representing the FCF byte.

    Returns:
        bool: True if frame type is Global Command, False otherwise
        None: if input invalid
    """
    return None if not is_hex(fcf) or len(fcf) != 2 else (int(fcf, 16) & 0b00000011) == 0


def frame_type(fcf):
    """
    Returns the frame type bits (bits 0-1) of the FCF.

    Args:
        fcf (str): 2-char hex string representing the FCF byte.

    Returns:
        int: frame type (0-3)
        None: if input invalid
    """
    return (int(fcf, 16) & 0b00000011)


def is_manufspecific_8002_payload(fcf):
    """
    Returns True if the manufacturer specific bit (bit 2) is set.

    Args:
        fcf (str): 2-char hex string representing the FCF byte.

    Returns:
        bool: True if manufacturer specific bit is 1, False otherwise
        None: if input invalid
    """
    return ((int(fcf, 16) & 0b00000100) >> 2) == 1


def build_fcf(frame_type_in, manuf_spec, direction, disabled_default="0"):
    fcf = 0b00000000 | int(frame_type_in, 16)
    if int(manuf_spec, 16):
        fcf |= 0b100
    if int(direction, 16):
        fcf |= 0b1000
    if int(disabled_default, 16):
        fcf |= 0b10000
    return "%02x" % fcf


def extract_info_from_8085(MsgData):
    step_mod = MsgData[14:16]
    up_down = MsgData[16:18] if len(MsgData) >= 18 else None
    step_size = MsgData[18:20] if len(MsgData) >= 20 else None
    transition = MsgData[20:22] if len(MsgData) >= 22 else None

    return (step_mod, up_down, step_size, transition)