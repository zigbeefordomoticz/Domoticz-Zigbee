#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# # Initial authors: pipiche38
#
# SPDX-License-Identifier: GPL-3.0 license

"""
    Module: zosungIR.py

    Zosung IR protocol handler for TS1201 / Moes UFO-R11 universal IR remote.

    Two custom ZCL clusters:
        0xed00  zosungIRTransmit  5-step command handshake for IR learn/send
        0xe004  zosungIRControl   single JSON command to trigger learn mode

    Learn flow  (device -> coordinator):
        Coordinator  ->  Device   e004 cmd00  {study:0}  enter learn mode
        Device       ->  Coord    ed00 cmd00  announce IR payload length
        Coord        ->  Device   ed00 cmd01  ack
        Coord        ->  Device   ed00 cmd02  request chunk at pos=0
        Device       ->  Coord    ed00 cmd03  chunk data + sum-mod-256 crc
        ... repeat cmd02 / cmd03 until all received ...
        Coord        ->  Device   ed00 cmd04  transfer complete
        Device       ->  Coord    ed00 cmd05  final ack
        Coord reconstructs buffer -> base64 -> MajDomoDevice (Text widget)

    Send flow  (coordinator -> device):
        Coord        ->  Device   ed00 cmd00  announce JSON payload length  (cmd=0x02)
        Device       ->  Coord    ed00 cmd01  ack
        Device       ->  Coord    ed00 cmd02  request chunk at pos=0
        Coord        ->  Device   ed00 cmd03  chunk data + sum-mod-256 crc
        ... repeat cmd02 / cmd03 until all sent ...
        Device       ->  Coord    ed00 cmd04  transfer complete
        Coord        ->  Device   ed00 cmd05  final ack
        Device fires IR signal

    Send payload format (JSON string, NOT raw bytes):
        {"key_num":1,"delay":300,"key1":{"num":1,"freq":38000,"type":1,"key_code":"<base64>"}}

    Frame byte order: little-endian throughout (ZCL/Zigbee convention).
    msgpart is encoded as a ZCL OCTET_STR: length(uint8) + data bytes.
    msgpartcrc = sum(msgpart bytes) % 256.

    Protocol reference: zigbee-herdsman-converters src/lib/zosung.ts
        https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/lib/zosung.ts

    Public API:
        zosung_ir_read_raw_aps()    called from tuyaReadRawAPS for ed00 / e004
        zosung_e004_learn_mode()    send learn-mode trigger to device
        zosung_ed00_send_ir_code()  initiate send of a stored base64 IR code
"""

import base64
import json
import struct

from Modules.basicOutputs import raw_APS_request
from Modules.domoMaj import MajDomoDevice
from Modules.tools import get_and_inc_ZCL_SQN
from Modules.tuyaTools import store_tuya_attribute
from Modules.zigateConsts import ZIGATE_EP

ZOSUNG_IR_TRANSMIT_CLUSTER = "ed00"
ZOSUNG_IR_CONTROL_CLUSTER = "e004"
ZOSUNG_CHUNK_SIZE = 0x38  # max 56 bytes per chunk


# ─── State helpers ─────────────────────────────────────────────────────

def _get_ir_state(self, nwkid):
    return self.ListOfDevices[nwkid].setdefault("ZosungIR", {
        "seq": 0,
        "rx_buffer": None,
        "rx_length": 0,
        "rx_seq": 0,
        "tx_data": None,   # bytes: JSON-wrapped IR payload during send
        "tx_seq": 0,
    })


# ─── Entry point ────────────────────────────────────────────────────────────

def zosung_ir_read_raw_aps(self, Devices, NwkId, srcEp, ClusterID, MsgPayload):
    """
    Main entry for raw APS frames on clusters ed00 and e004.
    Called from tuyaReadRawAPS when ClusterID is 'ed00' or 'e004'.

    ZCL frame layout (cluster-specific, little-endian):
        MsgPayload[0:2]  FCF  (frame control field)
        MsgPayload[2:4]  SQN  (sequence number)
        MsgPayload[4:6]  CMD  (command id, hex string)
        MsgPayload[6:]   DATA (command payload, hex string)
    """
    if len(MsgPayload) < 6:
        self.log.logging("ZosungIR", "Debug",
            "zosung_ir_read_raw_aps - payload too short: %s" % MsgPayload, NwkId)
        return

    cmd = MsgPayload[4:6]
    data_hex = MsgPayload[6:]

    self.log.logging("ZosungIR", "Debug", "zosung_ir_read_raw_aps - NwkId: %s Ep: %s Cluster: %s Cmd: %s Data: %s" % (
        NwkId, srcEp, ClusterID, cmd, data_hex), NwkId)

    if ClusterID == ZOSUNG_IR_CONTROL_CLUSTER:
        _handle_e004_cmd(self, Devices, NwkId, srcEp, cmd, data_hex)
        return

    if ClusterID == ZOSUNG_IR_TRANSMIT_CLUSTER:
        _handle_ed00_cmd(self, Devices, NwkId, srcEp, cmd, data_hex)


# ─── e004 handler ────────────────────────────────────────────────────────────

def _handle_e004_cmd(self, Devices, NwkId, srcEp, cmd, data_hex):
    self.log.logging("ZosungIR", "Debug", "_handle_e004_cmd - NwkId: %s cmd: %s data: %s" % (NwkId, cmd, data_hex), NwkId)
    store_tuya_attribute(self, NwkId, "ZosungIRControl_raw", data_hex)


# ─── ed00 dispatcher ───────────────────────────────────────────────────────────

def _handle_ed00_cmd(self, Devices, NwkId, srcEp, cmd, data_hex):
    _ED00_HANDLERS = {
        "00": _ed00_cmd00_init,
        "01": _ed00_cmd01_init_ack,
        "02": _ed00_cmd02_chunk_request,
        "03": _ed00_cmd03_chunk,
        "04": _ed00_cmd04_done,
        "05": _ed00_cmd05_final,
    }
    handler = _ED00_HANDLERS.get(cmd)
    if handler:
        handler(self, Devices, NwkId, srcEp, data_hex)
    else:
        self.log.logging("ZosungIR", "Debug", "_handle_ed00_cmd - unknown cmd: %s data: %s" % (cmd, data_hex), NwkId)


# ─── ed00 incoming command handlers ───────────────────────────────────────────────────

def _ed00_cmd00_init(self, Devices, NwkId, srcEp, data_hex):
    """
    Device -> Coordinator: Transfer init (learn mode).
    Fields (little-endian): seq(uint16), length(uint32), unk1(uint32),
        unk2(uint16), unk3(uint8), cmd_flag(uint8), unk4(uint16) -- 16 bytes.
    Coordinator responds with cmd01 (ack) then cmd02 (request first chunk).
    """
    if len(data_hex) < 32:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd00_init - data too short: %s" % data_hex, NwkId)
        return

    data_bytes = bytes.fromhex(data_hex[:32])
    seq, length, unk1, unk2, unk3, cmd_flag, unk4 = struct.unpack("<HIIHBBH", data_bytes)

    self.log.logging("ZosungIR", "Debug", "_ed00_cmd00_init - NwkId: %s seq:%04x length:%d cmd_flag:%02x" % (
        NwkId, seq, length, cmd_flag), NwkId)

    store_tuya_attribute(self, NwkId, "ZosungIR_rx_seq", "%04x" % seq)
    store_tuya_attribute(self, NwkId, "ZosungIR_rx_length", str(length))

    state = _get_ir_state(self, NwkId)
    state["rx_seq"] = seq
    state["rx_length"] = length
    state["rx_buffer"] = bytearray(length)

    _send_ed00_cmd01_ack(self, NwkId, srcEp, seq, length, unk1, unk2, unk3, cmd_flag, unk4)
    _send_ed00_cmd02_request(self, NwkId, srcEp, seq, position=0)


def _ed00_cmd01_init_ack(self, Devices, NwkId, srcEp, data_hex):
    """
    Device -> Coordinator: Init ack (send mode: device acks our cmd00).
    Nothing to do; device will follow with cmd02 requesting chunks.
    """
    self.log.logging("ZosungIR", "Debug", "_ed00_cmd01_init_ack - NwkId: %s data: %s" % (NwkId, data_hex), NwkId)


def _ed00_cmd02_chunk_request(self, Devices, NwkId, srcEp, data_hex):
    """
    Device -> Coordinator: Chunk request (send mode).
    Fields (little-endian): seq(uint16), position(uint32), maxlen(uint8) -- 7 bytes.
    Coordinator responds with cmd03 carrying the requested chunk.
    tx_data holds the JSON-encoded IR payload as raw bytes.
    """
    if len(data_hex) < 14:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd02_chunk_request - data too short: %s" % data_hex, NwkId)
        return

    data_bytes = bytes.fromhex(data_hex[:14])
    seq, position, maxlen = struct.unpack("<HIB", data_bytes)

    self.log.logging("ZosungIR", "Debug", "_ed00_cmd02_chunk_request - NwkId: %s seq:%04x pos:%d maxlen:%d" % (
        NwkId, seq, position, maxlen), NwkId)

    state = _get_ir_state(self, NwkId)
    tx_data = state.get("tx_data")   # bytes: JSON payload, set by zosung_ed00_send_ir_code
    if not tx_data:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd02_chunk_request - no tx_data pending for %s" % NwkId, NwkId)
        return

    chunk_len = min(maxlen, ZOSUNG_CHUNK_SIZE)
    chunk = bytes(tx_data[position: position + chunk_len])
    crc = _sum_crc(chunk)
    _send_ed00_cmd03_chunk(self, NwkId, srcEp, seq, position, chunk, crc)


def _ed00_cmd03_chunk(self, Devices, NwkId, srcEp, data_hex):
    """
    Device -> Coordinator: Chunk data (learn mode).
    Fields (little-endian):
        zero(uint8), seq(uint16), position(uint32),
        msgpart_len(uint8), msgpart(msgpart_len bytes), msgpartcrc(uint8).
    msgpart is a ZCL OCTET_STR (length-prefixed).
    msgpartcrc = sum(msgpart) % 256.
    Stores chunk in rx_buffer; requests next chunk or signals done.
    """
    if len(data_hex) < 18:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd03_chunk - data too short: %s" % data_hex, NwkId)
        return

    data_bytes = bytes.fromhex(data_hex)
    seq = struct.unpack_from("<H", data_bytes, 1)[0]
    position = struct.unpack_from("<I", data_bytes, 3)[0]
    msgpart_len = data_bytes[7]

    if len(data_bytes) < 8 + msgpart_len + 1:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd03_chunk - truncated msgpart NwkId: %s len=%d" % (NwkId, msgpart_len), NwkId)
        return

    msgpart = data_bytes[8:8 + msgpart_len]
    msgpartcrc = data_bytes[8 + msgpart_len]

    computed_crc = _sum_crc(msgpart)
    if computed_crc != msgpartcrc:
        self.log.logging("ZosungIR", "Error", "_ed00_cmd03_chunk - CRC mismatch NwkId: %s seq:%04x pos:%d computed:%02x received:%02x" % ( 
            NwkId, seq, position, computed_crc, msgpartcrc), NwkId)
        return

    self.log.logging("ZosungIR", "Debug", "_ed00_cmd03_chunk - NwkId: %s seq:%04x pos:%d len:%d crc:ok" % (
        NwkId, seq, position, len(msgpart)), NwkId)

    state = _get_ir_state(self, NwkId)
    rx_buffer = state.get("rx_buffer")
    rx_length = state.get("rx_length", 0)

    if rx_buffer is None:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd03_chunk - no rx_buffer for %s, ignoring" % NwkId, NwkId)
        return

    end = position + len(msgpart)
    rx_buffer[position:end] = msgpart

    if end >= rx_length:
        _send_ed00_cmd04_done(self, NwkId, srcEp, seq)
    else:
        _send_ed00_cmd02_request(self, NwkId, srcEp, seq, position=end)


def _ed00_cmd04_done(self, Devices, NwkId, srcEp, data_hex):
    """
    Device -> Coordinator: Transfer complete (send mode).
    Fields (little-endian): zero0(uint8), seq(uint16), zero1(uint16) -- 5 bytes.
    Coordinator responds with cmd05 final ack and clears tx_data.
    """
    if len(data_hex) < 10:
        return
    seq = struct.unpack_from("<H", bytes.fromhex(data_hex[:10]), 1)[0]
    self.log.logging("ZosungIR", "Debug", "_ed00_cmd04_done - NwkId: %s seq:%04x" % (NwkId, seq), NwkId)

    state = _get_ir_state(self, NwkId)
    state["tx_data"] = None

    _send_ed00_cmd05_final(self, NwkId, srcEp, seq)


def _ed00_cmd05_final(self, Devices, NwkId, srcEp, data_hex):
    """
    Device -> Coordinator: Final ack (learn mode: device acks our cmd04).
    Reconstruct rx_buffer -> base64 string -> update Text/SwitchIRCode widget.
    """
    if len(data_hex) < 8:
        return
    seq = struct.unpack_from("<H", bytes.fromhex(data_hex[:4]))[0]
    self.log.logging("ZosungIR", "Debug", "_ed00_cmd05_final - NwkId: %s seq:%04x" % (NwkId, seq), NwkId)

    state = _get_ir_state(self, NwkId)
    rx_buffer = state.get("rx_buffer")
    if not rx_buffer:
        self.log.logging("ZosungIR", "Debug", "_ed00_cmd05_final - no rx_buffer for %s" % NwkId, NwkId)
        return

    learned_code = base64.b64encode(bytes(rx_buffer)).decode("ascii")
    self.log.logging("ZosungIR", "Status", "zosung IR Code received - NwkId: %s learned IR code len=%d '%s'" % (
        NwkId, len(learned_code), learned_code), NwkId)

    store_tuya_attribute(self, NwkId, "ZosungIR_learned_code", learned_code)
    MajDomoDevice(self, Devices, NwkId, srcEp, "IRCode", learned_code)

    state["rx_buffer"] = None
    state["rx_length"] = 0
    state["rx_seq"] = 0


# ─── Outgoing ZCL command builders ─────────────────────────────────────────────────────

def _send_zcl_cluster_cmd(self, NwkId, ep, cluster, cmd_id, payload_bytes):
    """Build and send a ZCL cluster-specific command frame."""
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    fcf = "11"
    zcl_payload = fcf + sqn + cmd_id + payload_bytes.hex()
    raw_APS_request(
        self, NwkId, ep, cluster, "0104", zcl_payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=False,  # always Force Ack for ZosungIR commands (device expects it and may retry if not received
    )


def _send_ed00_cmd01_ack(self, NwkId, ep, seq, length, unk1, unk2, unk3, cmd_flag, unk4):
    """Ack device cmd00: mirrors cmd00 fields prefixed with a zero byte (little-endian)."""
    payload = struct.pack("<BHIIHBBH", 0, seq, length, unk1, unk2, unk3, cmd_flag, unk4)
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_TRANSMIT_CLUSTER, "01", payload)


def _send_ed00_cmd02_request(self, NwkId, ep, seq, position):
    """Request a chunk from device at given position (little-endian)."""
    payload = struct.pack("<HIB", seq, position, ZOSUNG_CHUNK_SIZE)
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_TRANSMIT_CLUSTER, "02", payload)


def _send_ed00_cmd03_chunk(self, NwkId, ep, seq, position, chunk_bytes, crc):
    """Send a chunk to device (send mode). msgpart encoded as ZCL OCTET_STR."""
    header = struct.pack("<BHI", 0, seq, position)
    # OCTET_STR: length byte followed by data
    msgpart_octet = bytes([len(chunk_bytes)]) + chunk_bytes
    payload = header + msgpart_octet + bytes([crc])
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_TRANSMIT_CLUSTER, "03", payload)


def _send_ed00_cmd04_done(self, NwkId, ep, seq):
    """Signal all chunks received (learn mode complete), little-endian."""
    payload = struct.pack("<BHH", 0, seq, 0)
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_TRANSMIT_CLUSTER, "04", payload)


def _send_ed00_cmd05_final(self, NwkId, ep, seq):
    """Final ack to device (send mode complete), little-endian."""
    payload = struct.pack("<HH", seq, 0)
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_TRANSMIT_CLUSTER, "05", payload)


# ─── Public API ────────────────────────────────────────────────────────────────

def zosung_e004_learn_mode(self, NwkId, ep, on_off=None):
    """
    Trigger IR learn mode: sends {"study": 0} JSON to cluster e004 cmd00.
    Call this before the user presses the IR remote button.
    on_off="On"  -> start learning  {"study": 0}
    on_off other -> stop  learning  {"study": 1}
    """
    study_mode = {"study": 0} if on_off == "On" else {"study": 1}
    data = json.dumps(study_mode, separators=(",", ":")).encode("utf-8")
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_CONTROL_CLUSTER, "00", data)


def zosung_ed00_send_ir_code(self, NwkId, ep, ir_code_b64):
    """
    Send a stored IR code to the device for playback.

    The base64 IR code (as returned by learn mode) is wrapped in a JSON
    envelope matching the format used by zigbee-herdsman-converters zosung.ts:
        {"key_num":1,"delay":300,"key1":{"num":1,"freq":38000,"type":1,"key_code":"<b64>"}}

    This JSON string (UTF-8 bytes) is then chunked and transferred via the
    ed00 protocol with cmd=0x02 in the cmd00 header.

    Args:
        ir_code_b64: base64-encoded IR payload string (as stored by learn mode).
    """
    ir_json = json.dumps({
        "key_num": 1,
        "delay": 300,
        "key1": {
            "num": 1,
            "freq": 38000,
            "type": 1,
            "key_code": ir_code_b64,
        },
    }, separators=(",", ":"))
    ir_bytes = ir_json.encode("utf-8")

    state = _get_ir_state(self, NwkId)
    state["tx_data"] = ir_bytes
    state["tx_seq"] = state.get("seq", 0)
    state["seq"] = (state["tx_seq"] + 1) & 0xFFFF

    length = len(ir_bytes)
    seq = state["tx_seq"]

    self.log.logging("ZosungIR", "Debug", "zosung_ed00_send_ir_code - NwkId: %s seq:%04x length:%d json:%s" % (
        NwkId, seq, length, ir_json), NwkId)

    # cmd00: seq(2), length(4), unk1(4), unk2=0xe004(2), unk3=0x01(1), cmd=0x02(1), unk4(2) - little-endian
    # cmd=0x02 matches zosung.ts; device will ack with cmd01 then request chunks via cmd02
    payload = struct.pack("<HIIHBBH", seq, length, 0, 0xe004, 0x01, 0x02, 0)
    _send_zcl_cluster_cmd(self, NwkId, ep, ZOSUNG_IR_TRANSMIT_CLUSTER, "00", payload)


# ─── CRC helper ──────────────────────────────────────────────────────────────────

def _sum_crc(data):
    """Byte-sum checksum mod 256 (Zosung msgpartcrc)."""
    return sum(data) % 256
