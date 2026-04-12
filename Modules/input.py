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
Module: input.py

Manages incoming messages from the Zigate coordinator.

Entry point is :func:`zigbee_receive_message`, which:

1. Validates the raw Zigate frame envelope (``01`` … ``03``).
2. Extracts ``MsgType``, ``MsgData``, and ``MsgLQI`` from the frame.
3. Optionally decodes a ``0x8002`` data-indication wrapper and re-extracts
   the inner application message.
4. Dispatches to the appropriate decoder via :data:`DECODERS` or the
   specialised handler for ``0x8011``.

All decoder calls are wrapped in a ``try/except`` block so that a single
malformed message never takes down the whole receive loop.
"""

from Z4D_decoders.z4d_decoder_Active_Ep_Rsp import Decode8045
from Z4D_decoders.z4d_decoder_Attr_Discovery_Rsp import Decode8140
from Z4D_decoders.z4d_decoder_bindings import Decode8030, Decode8031
from Z4D_decoders.z4d_decoder_Complex_Descriptor_Rsp import Decode8034
from Z4D_decoders.z4d_decoder_config_reporting import Decode8120, Decode8122
from Z4D_decoders.z4d_decoder_Data_Indication import Decode8002
from Z4D_decoders.z4d_decoder_Default_Req import Decode7000
from Z4D_decoders.z4d_decoder_Default_Rsp import Decode8101
from Z4D_decoders.z4d_decoder_Device_Annoucement import Decode004D
from Z4D_decoders.z4d_decoder_Discovery_Rsp import Decode804B
from Z4D_decoders.z4d_decoder_groups import (Decode8060, Decode8061,
                                             Decode8062, Decode8063)
from Z4D_decoders.z4d_decoder_helpers import extract_message_infos
from Z4D_decoders.z4d_decoder_IAS import (Decode0400, Decode8046, Decode8400,
                                          Decode8401)
from Z4D_decoders.z4d_decoder_IEEE_addr_req import Decode0041
from Z4D_decoders.z4d_decoder_IEEE_Addr_Rsp import Decode8041
from Z4D_decoders.z4d_decoder_Leave_Notification import Decode8048
from Z4D_decoders.z4d_decoder_Leave_Rsp import Decode8047
from Z4D_decoders.z4d_decoder_Node_Desc_req import Decode0042
from Z4D_decoders.z4d_decoder_Node_Desc_Rsp import Decode8042
from Z4D_decoders.z4d_decoder_NWK_addr_req import Decode0040
from Z4D_decoders.z4d_decoder_Nwk_Addr_Rsp import Decode8040
from Z4D_decoders.z4d_decoder_Nwk_Map_Rsp import Decode804E
from Z4D_decoders.z4d_decoder_Nwk_Scan_Rsp import Decode804A
from Z4D_decoders.z4d_decoder_Nwk_Status import Decode8009, Decode8024
from Z4D_decoders.z4d_decoder_OTA_Rsp import Decode8501, Decode8502, Decode8503
from Z4D_decoders.z4d_decoder_Power_Descriptor_Rsp import Decode8044
from Z4D_decoders.z4d_decoder_Pwr_Mgt_Rsp import Decode8806, Decode8807
from Z4D_decoders.z4d_decoder_Read_Attribute_Request import Decode0100
from Z4D_decoders.z4d_decoder_Read_Attribute_Rsp import Decode8100
from Z4D_decoders.z4d_decoder_Read_Report_Attribute_Rsp import Decode8102
from Z4D_decoders.z4d_decoder_Remotes import Decode80A7, Decode8085, Decode8095
from Z4D_decoders.z4d_decoder_Rte_Discovery_Performed import Decode8701
from Z4D_decoders.z4d_decoder_Scenes import Decode80A5, Decode80A6
from Z4D_decoders.z4d_decoder_Simple_Descriptor_Rsp import Decode8043
from Z4D_decoders.z4d_decoder_User_Desc_Notify import Decode802B, Decode802C
from Z4D_decoders.z4d_decoder_Write_Attribute_Request import Decode0110
from Z4D_decoders.z4d_decoder_Wrt_Attribute_Rsp import Decode8110
from Z4D_decoders.z4d_decoder_Zigate_Active_Devices_List import Decode8015
from Z4D_decoders.z4d_decoder_Zigate_Authenticate_Rsp import Decode8028
from Z4D_decoders.z4d_decoder_Zigate_Clusters import (Decode8003, Decode8004,
                                                      Decode8005)
from Z4D_decoders.z4d_decoder_Zigate_Cmd_Rsp import Decode8000_v2, Decode8011
from Z4D_decoders.z4d_decoder_Zigate_Firmware_Version import Decode8010
from Z4D_decoders.z4d_decoder_Zigate_Heartbeat import Decode8008
from Z4D_decoders.z4d_decoder_Zigate_Pairing import Decode8014, Decode8049
from Z4D_decoders.z4d_decoder_Zigate_PDM import (Decode0302, Decode8006,
                                                 Decode8007)
from Z4D_decoders.z4d_decoder_Zigate_Time_Srv import Decode8017
from Zigbee.decode8002 import decode8002_and_process

# ---------------------------------------------------------------------------
# Decoder dispatch table
#
# Maps lower-case hex MsgType strings to their decoder callables.
#
# Notes:
#   "8002" is intentionally absent – raw Data Indication frames that survive
#   the decode8002_and_process unwrapping stage fall through to the explicit
#   elif in _decode_message so that the original *full* Data argument can be
#   forwarded to Decode8002 (which needs it).
#
#   "8011" is also absent for the same reason: its decoder signature differs
#   from the standard (self, Devices, MsgData, MsgLQI) convention.
#
#   "8139" is intentionally aliased to Decode8140 because the firmware emits
#   two type codes (0x8139 and 0x8140) for what is logically the same
#   Attribute Discovery Response payload.  If this ever diverges, introduce
#   a dedicated Decode8139.
# ---------------------------------------------------------------------------
DECODERS: dict = {
    "004d": Decode004D,
    "0040": Decode0040,
    "0041": Decode0041,
    "0042": Decode0042,
    "0100": Decode0100,
    "0110": Decode0110,
    "0302": Decode0302,
    "0400": Decode0400,
    "8000": Decode8000_v2,
    "8003": Decode8003,
    "8004": Decode8004,
    "8005": Decode8005,
    "8006": Decode8006,
    "8007": Decode8007,
    "8008": Decode8008,
    "8009": Decode8009,
    "8010": Decode8010,
    "8014": Decode8014,
    "8015": Decode8015,
    "8017": Decode8017,
    "8024": Decode8024,
    "8028": Decode8028,
    "802b": Decode802B,
    "802c": Decode802C,
    "8030": Decode8030,
    "8031": Decode8031,
    "8034": Decode8034,
    "8040": Decode8040,
    "8041": Decode8041,
    "8042": Decode8042,
    "8043": Decode8043,
    "8044": Decode8044,
    "8045": Decode8045,
    "8046": Decode8046,
    "8047": Decode8047,
    "8048": Decode8048,
    "8049": Decode8049,
    "804a": Decode804A,
    "804b": Decode804B,
    "804e": Decode804E,
    "8060": Decode8060,
    "8061": Decode8061,
    "8062": Decode8062,
    "8063": Decode8063,
    "8085": Decode8085,
    "8095": Decode8095,
    "80a5": Decode80A5,
    "80a6": Decode80A6,
    "80a7": Decode80A7,
    "8100": Decode8100,
    "8101": Decode8101,
    "8102": Decode8102,
    "8110": Decode8110,
    "8120": Decode8120,
    "8122": Decode8122,
    # 0x8139 and 0x8140 share the same payload format – see note above.
    "8139": Decode8140,
    "8140": Decode8140,
    "8400": Decode8400,
    "8401": Decode8401,
    "8501": Decode8501,
    "8502": Decode8502,
    "8503": Decode8503,
    "8701": Decode8701,
    "8806": Decode8806,
    "8807": Decode8807,
    "7000": Decode7000,
}

# Expected Zigate frame delimiters (lower-case hex pairs).
_FRAME_START = "01"
_FRAME_STOP = "03"


def zigbee_receive_message(self, Devices, Data):
    """Process a raw Zigate serial frame and dispatch it to a decoder.

    This is the single entry point for all data arriving from the Zigate
    coordinator.  It performs three tasks:

    1. **Envelope validation** – checks that the frame is bracketed by the
       expected ``01`` / ``03`` sentinel bytes.  Malformed frames are logged
       and discarded.
    2. **Header extraction** – delegates to :func:`extract_message_infos` to
       obtain the *MsgType*, *MsgData*, and *MsgLQI* fields.
    3. **8002 unwrapping** – when the outer MsgType is ``8002`` (a Zigate
       Data Indication wrapper), :func:`decode8002_and_process` is called to
       extract the inner application frame before dispatching.

    Args:
        self:     Plugin instance (carries ``self.log``, ``self.Ping``, etc.).
        Devices:  Domoticz ``Devices`` dictionary.
        Data:     Raw frame string as a continuous lower-case hex sequence,
                  e.g. ``"0100...03"``.  ``None`` is silently ignored.
    """
    if Data is None:
        return

    FrameStart = Data[:2]
    FrameStop = Data[-2:]

    # BUG FIX: original used 'and' so a bad FrameStart was ignored when
    # FrameStop was also wrong.  The correct guard rejects either mismatch.
    if FrameStart != _FRAME_START or FrameStop != _FRAME_STOP:
        self.log.logging(
            "Input", "Error",
            f"zigbee_receive_message - received a non-zigate frame "
            f"Data: {Data} FS/FE = {FrameStart}/{FrameStop}",
        )
        return

    MsgType, MsgData, MsgLQI = extract_message_infos(self, Data)
    self.Ping["Nb Ticks"] = 0  # Reset watchdog – we received a valid packet.

    self.log.logging(
        "Input", "Debug",
        f"zigbee_receive_message - MsgType: {MsgType}, Data: {MsgData}, "
        f"LQI: {int(MsgLQI, 16)}",
    )

    if MsgType == "8002":
        # Attempt to unwrap the Data Indication envelope and obtain the inner
        # application MsgType.  If unwrapping fails (returns None) we discard
        # the frame – decode8002_and_process already logs the reason.
        decoded_frame = decode8002_and_process(self, Data)
        if decoded_frame is None:
            return
        MsgType, MsgData, MsgLQI = extract_message_infos(self, decoded_frame)

    _decode_message(self, MsgType, Devices, Data, MsgData, MsgLQI)


def _decode_message(self, MsgType, Devices, Data, MsgData, MsgLQI):
    """Dispatch a parsed Zigate message to the appropriate decoder.

    The majority of message types are handled via a simple :data:`DECODERS`
    dict look-up.  Two types are handled outside the table:

    * ``"8002"`` – Raw (un-unwrapped) Data Indication.  The full *Data*
      argument is passed because :func:`Decode8002` needs the complete
      frame, not just the payload slice.
    * ``"8011"`` – Zigate command response with a non-standard decoder
      signature; kept separate to avoid polluting the dispatch table.

    All decoder calls are wrapped in a ``try/except`` block.  A single
    malformed or unexpected payload therefore never silences subsequent
    messages.

    Args:
        self:     Plugin instance.
        MsgType:  Four-character lower-case hex string, e.g. ``"8045"``.
        Devices:  Domoticz ``Devices`` dictionary.
        Data:     Full raw frame string (needed only by ``Decode8002``).
        MsgData:  Payload slice extracted from the frame.
        MsgLQI:   Link-quality indicator as a two-character hex string.
    """
    try:
        if MsgType in DECODERS:
            DECODERS[MsgType](self, Devices, MsgData, MsgLQI)

        elif MsgType == "8002":
            # Reaches here only when decode8002_and_process returned None in
            # zigbee_receive_message and the caller bypassed the early-return
            # (should not happen in normal flow, but kept as a safety net).
            Decode8002(self, Devices, MsgData, MsgLQI)

        elif MsgType == "8011":
            # Decode8011 has a non-standard signature – it does not accept
            # the MsgLQI argument.
            Decode8011(self, Devices, MsgData, MsgLQI)

        else:
            self.log.logging(
                "Input", "Error",
                f"_decode_message - no decoder registered for MsgType {MsgType}",
            )

    except Exception as exc:  # noqa: BLE001
        self.log.logging(
            "Input", "Error",
            f"_decode_message - unhandled exception while processing "
            f"MsgType {MsgType}: {exc}",
        )