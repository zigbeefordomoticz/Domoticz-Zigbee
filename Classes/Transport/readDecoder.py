# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import struct
import binascii

from Classes.Transport.handleProtocol import process_frame


def decode_and_split_message(self, raw_message):

    # Process/Decode raw_message
    # self.logging_receive( 'Log', "onMessage - %s" %(raw_message))
    if raw_message is not None:
        self._ReqRcv += raw_message  # Add the incoming data
        # Domoticz.Debug("onMessage incoming data : '" + str(binascii.hexlify(self._ReqRcv).decode('utf-8')) + "'")

    self._last_raw_message += raw_message

    while 1:  # Loop, detect frame and process, until there is no more frame.
        if len(self._ReqRcv) == 0:
            return
        BinMsg = decode_frame(get_raw_frame_from_raw_message(self))
        if BinMsg is None:
            return
        if not check_frame_lenght(self, BinMsg) or not check_frame_crc(self, BinMsg):
            self.logging_receive("Error", "on_message Frame error Crc/len %s" % (BinMsg))
            continue

        AsciiMsg = binascii.hexlify(BinMsg).decode("utf-8")

        # if self.pluginconf.pluginConf["debugzigateCmd"]:
        #    self.logging_send('Log', "on_message AsciiMsg: %s , Remaining buffer: %s" %(AsciiMsg,  self._ReqRcv ))

        self.statistics._received += 1
        process_frame(self, AsciiMsg)

        self._last_raw_message = bytearray()


def get_raw_frame_from_raw_message(self):

    frame = bytearray()
    # Search the 1st occurance of 0x03 (end Frame)
    zero3_position = self._ReqRcv.find(b"\x03")

    # Search the 1st position of 0x01 until the position of 0x03
    frame_start = self._ReqRcv.rfind(b"\x01", 0, zero3_position)

    if frame_start == -1 or zero3_position == -1:
        # no start and end frame found (missing one of the two)
        return None

    if frame_start > zero3_position:
        self.logging_receive(
            "Error",
            "Frame error we will drop the buffer!! start: %s zero3: %s buffer: %s"
            % (
                frame_start,
                zero3_position,
                self._ReqRcv,
            ),
        )
        return None

    # Remove the frame from the buffer (new buffer start at frame +1)
    frame = self._ReqRcv[frame_start : zero3_position + 1]
    self._ReqRcv = self._ReqRcv[zero3_position + 1 :]
    return frame


# def decode_frame( frame ):
#    if frame is None or frame == b'':
#        return None
#    BinMsg = bytearray()
#    iterReqRcv = iter(frame)
#    for iByte in iterReqRcv:  # for each received byte
#        if iByte == 0x02:  # Coded flag ?
#            # then uncode the next value
#            iByte = next(iterReqRcv) ^ 0x10
#        BinMsg.append(iByte)  # copy
#    if len(BinMsg) <= 6:
#        return None
#    return BinMsg


def decode_frame(frame):
    if frame is None or frame == b"":
        return None
    BinMsg = bytearray()
    iterReqRcv = iter(frame)
    bInEsc = False
    for iByte in iterReqRcv:  # for each received byte
        if iByte == 0x02:
            # Take the next byte and OR with 0x10
            bInEsc = True
            continue
        if bInEsc:
            bInEsc = False
            iByte = iByte ^ 0x10
        BinMsg.append(iByte)  # copy
    if len(BinMsg) <= 6:
        return None
    return BinMsg


def check_frame_crc(self, BinMsg):
    ComputedChecksum = 0
    if len(BinMsg) < 6:
        self.statistics._crcErrors += 1
        _context = {
            "Error code": "TRANS-CHKCRC-02",
            "BinMsg": str(BinMsg),
            "AsciiMsg": str(binascii.hexlify(BinMsg).decode("utf-8")),
            "LastRawMsg": str(binascii.hexlify(self._last_raw_message).decode("utf-8")),
            "len": len(BinMsg),
        }
        self.logging_receive_error("check_frame_crc", context=_context)
        return False
    Zero1, MsgType, Length, ReceivedChecksum = struct.unpack(">BHHB", BinMsg[0:6])

    for idx, val in enumerate(BinMsg[1:-1]):
        if idx != 4:  # Jump the checksum itself
            ComputedChecksum ^= val
    if ComputedChecksum != ReceivedChecksum:
        self.statistics._crcErrors += 1
        _context = {
            "Error code": "TRANS-CHKCRC-01",
            "BinMsg": str(BinMsg),
            "AsciiMsg": str(binascii.hexlify(BinMsg).decode("utf-8")),
            "LastRawMsg": str(binascii.hexlify(self._last_raw_message).decode("utf-8")),
            "len": len(BinMsg),
            "MsgType": "%04x" % MsgType,
            "Length": Length,
            "ComputedChecksum": ComputedChecksum,
            "ReceivedChecksum": ReceivedChecksum,
        }
        self.logging_receive_error("check_frame_crc", context=_context)
        return False
    return True


def check_frame_lenght(self, BinMsg):
    # Check length
    Zero1, MsgType, Length, ReceivedChecksum = struct.unpack(">BHHB", BinMsg[0:6])
    ComputedLength = Length + 7
    ReceveidLength = len(BinMsg)
    if ComputedLength != ReceveidLength:
        self.statistics._frameErrors += 1
        _context = {
            "Error code": "TRANS-CHKLEN-01",
            "Zero1": Zero1,
            "BinMsg": str(BinMsg),
            "AsciiMsg": str(binascii.hexlify(BinMsg).decode("utf-8")),
            "LastRawMsg": str(binascii.hexlify(self._last_raw_message).decode("utf-8")),
            "len": len(BinMsg),
            "MsgType": "%04x" % MsgType,
            "Length": Length,
            "ReceivedChecksum": ReceivedChecksum,
            "ComputedLength": ComputedLength,
            "ReceveidLength": ReceveidLength,
        }
        self.logging_receive_error("check_frame_lenght", context=_context)
        return False
    return True
