# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import serial


from Classes.Transport.tools import stop_waiting_on_queues
from Classes.Transport.tools import waiting_for_end_thread
from Classes.Transport.readDecoder import decode_and_split_message


# Manage Serial Line
def open_serial( self ):

    try:
        self._connection = serial.Serial(self._serialPort, baudrate = 115200, rtscts = False, dsrdtr = False, timeout = None)
        if self._transp in ('DIN', 'V2' ):
            self._connection.rtscts = True

    except serial.SerialException as e:
        Domoticz.Error("Cannot open Zigate port %s error: %s" %(self._serialPort, e))
        return False

    self.logging_receive( 'Log', "ZigateTransport: Serial Connection open: %s" %self._connection)
    return True

def serial_read_from_zigate( self ):

    self.logging_receive( 'Log', "serial_read_from_zigate - listening")

    while self.running:
        # We loop until self.running is set to False, 
        # which indicate plugin shutdown   
        data = None

        try:
            data = self._connection.read( )  # Blocking Read

        except serial.SerialException as e:
            Domoticz.Error("serial_read_from_zigate - error while reading %s" %(e))
            data = None

        if data:
            decode_and_split_message(self, data)

    stop_waiting_on_queues( self )
    Domoticz.Status("ZigateTransport: ZiGateSerialListen Thread stop.")

