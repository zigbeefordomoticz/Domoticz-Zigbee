# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import time

import serial
from Classes.ZigateTransport.readDecoder import decode_and_split_message
from Classes.ZigateTransport.tools import (handle_thread_error,
                                           stop_waiting_on_queues)


# Manage Serial Line
def open_serial(self):
    if self._connection:
        self._connection.close()
        del self._connection
        self._connection = None

    try:
        self._connection = serial.Serial(self._serialPort, baudrate=115200, rtscts=False, dsrdtr=False, timeout=None)

    except serial.SerialException as e:
        self.logging_serial("Error", "Cannot open Zigate port %s error: %s" % (self._serialPort, e))
        return False

    time.sleep(0.5)  # wait fro 100 ms for pyserial port to actually be ready
    self.logging_serial("Status", "ZigateTransport: Serial Connection open: %s" % self._connection)
    return True

def reconnect(self):
    self.logging_serial("Error", "ZigateTransport: reconnect: %s" % self._connection)
    delay = 1
    while self.running:
        try:
            if self._connection:
                self.self._connection.close()
            if open_serial(self):
                return
        except serial.SerialException:
            pass
        self.logging_serial("Error", "ZigateTransport: reconnect: %s delay: %s" % (self._connection, delay))
        time.sleep( float(delay))
        if delay < 30:
            delay *= 1.5
        else:
            return


def serial_reset_line_in(self):
    if not self.force_dz_communication:
        self.logging_serial("Debug", "Reset Serial Line IN")
        try:
            self._connection.reset_input_buffer()
        except serial.SerialException:
            pass

def serial_reset_line_out(self):
    if not self.force_dz_communication:
        self.logging_serial("Debug", "Reset Serial Line Out")
        try:
            self._connection.reset_output_buffer()
        except serial.SerialException:
            pass

def close_serial(self):
    self.logging_serial("Status", "ZigateTransport: Serial Connection closing: %s" % self._connection)
    try:
        serial_reset_line_out(self)
        serial_reset_line_in(self)
        self._connection.close()
        del self._connection
        self._connection = None
        self.logging_serial("Status", "ZigateTransport: Serial Connection closed: %s" % self._connection)
    except Exception as e:
        self.logging_serial("Log", "ZigateTransport: Error while Serial Connection closing: %s - %s" % (self._connection, e))

    time.sleep(0.5)

def check_hw_flow_control(self):

    self.logging_serial("Debug", "check_hw_flow_control ")

    if self._connection is None:
        return 

    try:
        if (
            self._serialPort.find("COM") == -1
            and not self._connection.rtscts
            and (
                (self.ZiGateHWVersion == 2 and self._transp in ("V2-USB", "V2-DIN"))
                or (self.ZiGateHWVersion == 1 and self._transp in ("DIN"))
            )
        ):
            self.logging_serial("Status", "Upgrade Serial line to RTS/CTS HW flow control")
            self._connection.rtscts = True

    except serial.SerialException:
        pass

def serial_read_write_from_zigate(self):

    self.logging_serial("Debug", "serial_read_write_from_zigate - listening")
    serial_reset_line_in(self)
    while self.running:

        # We loop until self.running is set to False,
        # which indicate plugin shutdown
        if not self._connection or not self._connection.is_open:
            time.sleep(0.5)
            continue

        self.logging_serial("Debug", "serial_read_write_from_zigate - check HW Flow")
        check_hw_flow_control(self)

        # Reading (prio to read)
        self.logging_serial("Debug", "serial_read_write_from_zigate - Read if any")
        if not serial_read_from_zigate(self):
            reconnect(self)

        # Writing
        self.logging_serial("Debug", "serial_read_write_from_zigate - Write if any")
        if not serial_write_to_zigate(self):
            reconnect(self)

        time.sleep(0.05)

    stop_waiting_on_queues(self)
    self.logging_serial("Status", "ZigateTransport: ZiGateSerialListen Thread stop.")

def serial_read_from_zigate(self):

    data = None
    try:
        while self._connection.in_waiting:
            data = self._connection.read(self._connection.in_waiting)
            self.logging_serial("Debug", "Receiving: %s" %str(data))
            if data:
                decode_and_split_message(self, data)
        self.logging_serial("Debug", "serial_read_from_zigate - read data: %s" %data)
        return True

    except serial.SerialException as e:
        self.logging_serial("Error", "serial_read_from_zigate - error while reading %s" % (e))
        # Might try to reconnect
        return False

    except Exception as e:
        # probably some I/O problem such as disconnected USB serial
        # adapters -> exit
        self.logging_serial("Error", "Error while receiving a ZiGate command: %s" % e)
        handle_thread_error(self, e, 0, 0, data)
        self._connection = None
        return False
            
def serial_write_to_zigate(self):

    try:
        if not self._connection or not self._connection.is_open:
            context = {
                "Error code": "TRANS-WRTZGTE-02",
                "serialConnection": str(self._connection),
            }
            self.logging_serial("Error", "write_to_zigate port is closed!", _context=context)
            return False

        if self.serial_send_queue.qsize() > 0:
            encode_data = self.serial_send_queue.get()
            self.logging_serial("Debug", "serial_write_to_zigate Sending: %s" %str(encode_data))
            nb_write = self._connection.write(encode_data)
            if nb_write == len(encode_data):
                self._connection.flush()
            else:
                # Error, missing 
                context = {
                    "Error code": "TRANS-WRTZGTE-01",
                    "EncodedData": str(encode_data),
                    "serialConnection": str(self._connection),
                    "NbWrite": nb_write,
                }
                self.logging_serial("Error", "write_to_zigate", _context=context)

        return True
                
                

    except TypeError as e:
        # Disconnect of USB->UART occured
        self.logging_serial("Error", "write_to_zigate - error while writing %s" % (e))
        return False
