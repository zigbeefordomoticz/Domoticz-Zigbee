# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import socket
from threading import Thread

import Domoticz
import serial
from Classes.ZigateTransport.readSerial import (open_serial,
                                                serial_read_write_from_zigate,
                                                serial_reset_line_in,
                                                serial_reset_line_out)
from Classes.ZigateTransport.readwriteTcp import (open_tcpip,
                                                  tcpip_read_from_zigate)


def open_zigate_and_start_reader(self, zigate_mode):

    self.logging_reader("Debug", "open_zigate_and_start_reader")
    if zigate_mode == "serial":
        if open_serial(self):
            start_serial_reader_thread(self)
            return True

    elif zigate_mode == "tcpip":
        if open_tcpip(self):
            start_tcpip_reader_thread(self)
            return True
    else:
        self.logging_reader("Error", "open_zigate_channel - Unknown mode: %s" % zigate_mode)

    self.logging_reader("Error", "open_zigate_and_start_reader - failed. Unable to open connection with ZiGate")
    return False


def start_serial_reader_thread(self):
    self.logging_reader("Debug", "start_serial_reader_thread")
    if self.reader_thread is None:
        self.reader_thread = Thread(name="ZiGateSerial_%s" % self.hardwareid, target=serial_read_write_from_zigate, args=(self,))
        self.reader_thread.start()


def start_tcpip_reader_thread(self):
    self.logging_reader("Debug", "start_tcpip_reader_thread")
    if self.reader_thread is None:
        self.reader_thread = Thread(name="ZiGateTCPIP_%s" % self.hardwareid, target=tcpip_read_from_zigate, args=(self,))
        self.reader_thread.start()


def shutdown_reader_thread(self):
    self.logging_reader("Debug", "shutdown_reader_thread %s" % self.running)

    if self._connection:
        if isinstance(self._connection, serial.serialposix.Serial):
            self.logging_reader("Log", "Flush and cancel_read")
            serial_reset_line_in(self)
            serial_reset_line_out(self)
            self._connection.cancel_read()

        elif isinstance(self._connection, socket.socket):
            self.logging_reader("Log", "shutdown socket")
            if self._connection:
                try:
                    self._connection.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass

        else:
            self.logging_reader("Log", "unknown connection: %s" % str(self._connection))

        self.logging_reader("Log", "close connection")
        if self._connection:
            self._connection.close()
        Domoticz.Log("Connection closed")
