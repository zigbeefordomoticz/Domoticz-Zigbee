# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import serial
import socket
import time
import struct
import binascii

from threading import Thread, Lock, Event

from Classes.Transport.readSerial import open_serial, serial_read_from_zigate
from Classes.Transport.readTcp import open_tcpip, tcpip_read_from_zigate

def open_zigate_and_start_reader( self, zigate_mode ):

    if zigate_mode == 'serial':
        if open_serial():
            start_serial_reader_thread( self )
    elif zigate_mode == 'tcpip':
        
        if open_tcpip():
            start_tcpip_reader_thread( self )
    else:
        Domoticz.Error("open_zigate_channel - Unknown mode: %s" %zigate_mode)


def start_serial_reader_thread( self ):

    if self.reader_thread is None:
        self.reader_thread = Thread( name="ZiGateSerial",  target=serial_read_from_zigate,  args=(self,))
        self.reader_thread.start()

def start_tcpip_reader_thread( self ):

    if self.Thread_listen_and_read is None:
        self.reader_thread = Thread( name="ZiGateTCPIP",  target=tcpip_read_from_zigate,  args=(self,))
        self.reader_thread.start()

def shutdown_reader_thread( self):

    if self._connection:
        if isinstance(self._connection, serial.serialposix.Serial):
            self._connection.cancel_read()

        elif isinstance(self._connection, socket.socket):
            self._connection.shutdown( socket.SHUT_RDWR )

        self._connection.close()
        self.Thread_listen_and_read.join()


def decode_and_split_message(self, raw_message):

    # Process/Decode raw_message
    #self.logging_receive( 'Log', "onMessage - %s" %(raw_message))
    if raw_message is not None:
        self._ReqRcv += raw_message  # Add the incoming data
        #Domoticz.Debug("onMessage incoming data : '" + str(binascii.hexlify(self._ReqRcv).decode('utf-8')) + "'")

    while 1:  # Loop, detect frame and process, until there is no more frame.
        if len(self._ReqRcv) == 0:
            return

        BinMsg = decode_frame( get_raw_frame_from_raw_message( self ))
        if BinMsg is None:
            return

        if not check_frame_lenght( self, BinMsg) or not check_frame_crc(self, BinMsg):
            Domoticz.Error("on_message Frame error Crc/len %s" %(BinMsg))
            continue           

        AsciiMsg = binascii.hexlify(BinMsg).decode('utf-8')

        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_send('Log', "on_message AsciiMsg: %s , Remaining buffer: %s" %(AsciiMsg,  self._ReqRcv ))

        self.statistics._received += 1

        process_frame(self, AsciiMsg)

def get_raw_frame_from_raw_message( self ):

    frame = bytearray()
    # Search the 1st occurance of 0x03 (end Frame)
    zero3_position = self._ReqRcv.find(b'\x03')

    # Search the 1st position of 0x01 until the position of 0x03
    frame_start = self._ReqRcv.rfind(b'\x01', 0, zero3_position)

    if frame_start == -1 or zero3_position == -1:
        # no start and end frame found (missing one of the two)
        return None
    
    if frame_start > zero3_position:
        Domoticz.Error("Frame error we will drop the buffer!! start: %s zero3: %s buffer: %s" %( frame_start,  zero3_position, self._ReqRcv, )   ) 
        return None
            
    # Remove the frame from the buffer (new buffer start at frame +1)
    frame = self._ReqRcv[frame_start:zero3_position + 1]
    self._ReqRcv = self._ReqRcv[zero3_position + 1:]
    return frame

def decode_frame( frame ):
    if frame is None or frame == b'':
        return None
    BinMsg = bytearray()
    iterReqRcv = iter(frame)
    for iByte in iterReqRcv:  # for each received byte
        if iByte == 0x02:  # Coded flag ?
            # then uncode the next value
            iByte = next(iterReqRcv) ^ 0x10
        BinMsg.append(iByte)  # copy
    if len(BinMsg) <= 6:
        Domoticz.Log("Error: %s/%s" %(frame,BinMsg))
        return None
    return BinMsg
          
def check_frame_crc(self, BinMsg):
    ComputedChecksum = 0
    Zero1, MsgType, Length, ReceivedChecksum = struct.unpack('>BHHB', BinMsg[0:6])
    for idx, val in enumerate(BinMsg[1:-1]):
        if idx != 4:  # Jump the checksum itself
            ComputedChecksum ^= val
    if ComputedChecksum != ReceivedChecksum:
        self.statistics._crcErrors += 1
        _context = {
            'Error code': 'TRANS-onMESS-04',
            'BinMsg': str(BinMsg),
            'len': len(BinMsg),
            'MsgType': MsgType,
            'Length': Length,
            'ComputedChecksum': ComputedChecksum,
            'ReceivedChecksum': ReceivedChecksum,
        }
        self.logging_send_error( "on_message", context=_context)
        return False
    return True

def check_frame_lenght( self, BinMsg):
    # Check length
    Zero1, MsgType, Length, ReceivedChecksum = struct.unpack('>BHHB', BinMsg[0:6])
    ComputedLength = Length + 7
    ReceveidLength = len(BinMsg)
    if ComputedLength != ReceveidLength:
        self.statistics._frameErrors += 1
        _context = {
            'Error code': 'TRANS-onMESS-03',
            'Zero1': Zero1,
            'BinMsg': str(BinMsg),
            'len': len(BinMsg),
            'MsgType': MsgType,
            'Length': Length,
            'ReceivedChecksum': ReceivedChecksum,
            'ComputedLength': ComputedLength,
            'ReceveidLength': ReceveidLength,
        }
        self.logging_send_error( "on_message", context=_context)
        Domoticz.Log("BinMsg: %s ExpectedLen: %s ComputedLen: %s" %(BinMsg, ReceveidLength,ComputedLength ))
        return False
    return True

def process_frame(self, decode_frame):

    # Sanity Check
    if decode_frame == '' or decode_frame is None or len(decode_frame) < 12:
        return

    i_sqn = None
    MsgType = decode_frame[2:6]
    MsgLength = decode_frame[6:10]
    MsgCRC = decode_frame[10:12]

    if MsgType == '8701':
        # Route Discovery, we don't handle it
        return

    # We receive an async message, just forward it to plugin
    if int(MsgType, 16) in STANDALONE_MESSAGE:
        self.logging_receive( 'Debug', "process_frame - STANDALONE_MESSAGE MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))    
        # Send to Queue for F_OUT()
        return

    # Payload
    MsgData = None
    if len(decode_frame) < 18:
        return

    MsgData = decode_frame[12:len(decode_frame) - 4]

    if MsgType in ( '8000', '8012', '8702', '8011'):
        # Protocol Management with 31d and 31e
        pass


    if MsgData and MsgType == "8002":
        # Data indication
        self.logging_receive( 'Debug', "process_frame - 8002 MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))  
        self.Thread_proc_recvQueue_and_process.put( process8002( self, frame ) )
        return


    # We reach that stage: Got a message not 0x8000/0x8011/0x8701/0x8202 an not a standolone message
    # But might be a 0x8102 ( as firmware 3.1c and below are reporting Read Attribute response and Report Attribute with the same MsgType)
    if not self.firmware_with_aps_sqn:
        MsgZclSqn = MsgData[0:2]
        MsgNwkId = MsgData[2:6]
        MsgEp = MsgData[6:8]
        MsgClusterId = MsgData[8:12]
        # Old Fashion Protocol Managemet. We are waiting for a Command Response before sending the next command

        return

    # Forward the message to plugin for further processing

# Extended Error Code:
def handle_9999( self, MsgData):

    StatusMsg = ''
    if  MsgData in ZCL_EXTENDED_ERROR_CODES:
        StatusMsg = ZCL_EXTENDED_ERROR_CODES[MsgData]

    if self.pluginconf.pluginConf['trackError']:
        self.logging_send( 'Log', "handle_9999 - Last PDUs infos ( n: %s a: %s) Extended Error Code: [%s] %s" %(self.npdu, self.apdu, MsgData, StatusMsg))