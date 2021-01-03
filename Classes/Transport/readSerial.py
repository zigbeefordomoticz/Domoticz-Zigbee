# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import serial

from Classes.Transport.tools import stop_waiting_on_queues, handle_thread_error
from Classes.Transport.readDecoder import decode_and_split_message, logging_reader

# Manage Serial Line
def open_serial( self ):

    try:
        self._connection = serial.Serial(self._serialPort, baudrate = 115200, rtscts = False, dsrdtr = False, timeout = None)
        if self._transp in ('DIN', 'V2' ):
            self._connection.rtscts = True

    except serial.SerialException as e:
        logging_reader( self,'Error',"Cannot open Zigate port %s error: %s" %(self._serialPort, e))
        return False

    logging_reader( self, 'Debug', "ZigateTransport: Serial Connection open: %s" %self._connection)
    return True

def serial_read_from_zigate( self ):

    logging_reader( self, 'Debug', "serial_read_from_zigate - listening")
    while self.running:
        # We loop until self.running is set to False, 
        # which indicate plugin shutdown   
        data = None

        try:
            nb_inwaiting = self._connection.in_waiting
            logging_reader( self, 'Debug', "serial_read_from_zigate - reading %s bytes" %nb_inwaiting)
            data = self._connection.read( nb_inwaiting or 1)  # Blocking Read

        except serial.SerialException as e:
            logging_reader( self,'Error',"serial_read_from_zigate - error while reading %s" %(e))
            data = None

        except Exception as e:
            logging_reader( self,'Error',"Error while receiving a ZiGate command: %s" %e)
            handle_thread_error( self, e, 0, 0, data)

        if data:
            decode_and_split_message(self, data)

    stop_waiting_on_queues( self )
    logging_reader( self,'Status', "ZigateTransport: ZiGateSerialListen Thread stop.")