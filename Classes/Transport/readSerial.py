# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import serial
import time

from Classes.Transport.tools import stop_waiting_on_queues, handle_thread_error
from Classes.Transport.readDecoder import decode_and_split_message

# Manage Serial Line
def open_serial( self ):
    try:
        if self._connection:
            self._connection.close()
            del self._connection
            self._connection = None

        self._connection = serial.Serial(self._serialPort, baudrate = 115200, rtscts = False, dsrdtr = False, timeout = None)
        if self._transp in ('DIN', 'V2' ):
            self._connection.rtscts = True
        time.sleep(0.5)     # wait fro 100 ms for pyserial port to actually be ready

    except serial.SerialException as e:
        self.logging_receive('Error',"Cannot open Zigate port %s error: %s" %(self._serialPort, e))
        return False

    self.logging_receive( 'Status', "ZigateTransport: Serial Connection open: %s" %self._connection)
    return True

def serial_reset_line_in(self):
    self.logging_receive('Debug',"Reset Serial Line IN")
    self._connection.reset_input_buffer()
    

def close_serial( self):
    self.logging_receive( 'Status', "ZigateTransport: Serial Connection closing: %s" %self._connection)
    try:
        self._connection.close()
        del self._connection
        self._connection = None
    except:
        pass
    time.sleep(0.5)

def serial_read_from_zigate( self ):

    self.logging_receive( 'Debug', "serial_read_from_zigate - listening")
    serial_reset_line_in(self)
    while self.running:
        # We loop until self.running is set to False, 
        # which indicate plugin shutdown  
        if not (self._connection and self._connection.is_open):
            time.sleep(0.5)
            continue
        self.logging_receive( 'Debug', "serial_read_from_zigate - reading %s bytes" %1)
        data = None
        try:
            if self._connection:
                data = self._connection.read( 1)  # Blocking Read

        except serial.SerialException as e:
            self.logging_receive('Error',"serial_read_from_zigate - error while reading %s" %(e))
            data = None
            self._connection= None
            break

        except Exception as e:
            # probably some I/O problem such as disconnected USB serial
            # adapters -> exit
            self.logging_receive('Error',"Error while receiving a ZiGate command: %s" %e)
            handle_thread_error( self, e, 0, 0, data)
            self._connection = None
            break

        if data:
            decode_and_split_message(self, data)

    stop_waiting_on_queues( self )
    self.logging_receive('Status', "ZigateTransport: ZiGateSerialListen Thread stop.")