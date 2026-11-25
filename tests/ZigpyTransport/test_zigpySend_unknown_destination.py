#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
process_raw_command to a short address zigpy does not know.

The Error used to read "unknown destination: None", and the error history had no device.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

PAYLOAD = "11fa00abcdef"


def send_to_unknown_device():
    from Classes.ZigpyTransport.zigpySend import process_raw_command

    lines = []
    transport = MagicMock()
    transport.log = SimpleNamespace(
        logging=lambda module, level, message, nwkid=None, context=None: lines.append(
            (level, message, nwkid, context)))
    transport.app.get_device = MagicMock(side_effect=KeyError("unknown"))
    data = {
        "Function": "zcl_onoff_off_noeffect",
        "timestamp": 0,
        "Profile": 0x0104,
        "Cluster": 0x0006,
        "TargetNwk": 0x0A1B,
        "TargetEp": 0x01,
        "SrcEp": 0x01,
        "payload": PAYLOAD,
        "AddressMode": 0x02,
    }
    asyncio.run(process_raw_command(transport, data, Sqn=250))
    (error,) = [line for line in lines if line[0] == "Error"]
    return error


def test_message_names_the_device_and_the_request():
    _, message, _, _ = send_to_unknown_device()
    assert "0a1b/01" in message
    assert "zcl_onoff_off_noeffect" in message
    assert "0006" in message
    assert "None" not in message


def test_error_carries_the_device_and_a_code():
    _, _, nwkid, context = send_to_unknown_device()
    assert nwkid == "0a1b"
    assert context["Error code"] == "ZIGPY-SEND-02"
    assert context["NwkId"] == "0a1b"


def test_payload_is_not_recorded():
    # The history is shared by users, and a payload can hold a secret (a lock PIN code)
    _, message, _, context = send_to_unknown_device()
    assert PAYLOAD not in message
    assert PAYLOAD not in str(context)
