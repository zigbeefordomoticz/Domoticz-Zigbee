# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import serial
import socket
import time

from threading import Thread

from Classes.Transport.readSerial import open_serial, serial_read_from_zigate
from Classes.Transport.readTcp import open_tcpip, tcpip_read_from_zigate


def open_zigate_and_start_reader( self, zigate_mode ):

    self.logging_receive( 'Debug', "open_zigate_and_start_reader")

    if zigate_mode == 'serial':
        if open_serial( self ):
            start_serial_reader_thread( self )
    elif zigate_mode == 'tcpip':
        
        if open_tcpip( self ):
            start_tcpip_reader_thread( self )
    else:
        self.logging_receive('Error',"open_zigate_channel - Unknown mode: %s" %zigate_mode)


def start_serial_reader_thread( self ):
    self.logging_receive( 'Debug', "start_serial_reader_thread")
    if self.reader_thread is None:
        self.reader_thread = Thread( name="ZiGateSerial_%s" %self.hardwareid,  target=serial_read_from_zigate,  args=(self,))
        self.reader_thread.start()

def start_tcpip_reader_thread( self ):
    self.logging_receive( 'Debug', "start_tcpip_reader_thread")
    if self.reader_thread is None:
        self.reader_thread = Thread( name="ZiGateTCPIP_%s" %self.hardwareid,  target=tcpip_read_from_zigate,  args=(self,))
        self.reader_thread.start()

def shutdown_reader_thread( self):
    self.logging_receive( 'Debug', "shutdown_reader_thread %s" %self.running)
    
    if self._connection:
        if isinstance(self._connection, serial.serialposix.Serial):
            self.logging_receive( 'Log', "cancel_read")
            self._connection.cancel_read()

        elif isinstance(self._connection, socket.socket):
            self.logging_receive( 'Log', "shutdown socket")
            self._connection.shutdown( socket.SHUT_RDWR )
        self.logging_receive( 'Log', "close connection")
        self._connection.close()
