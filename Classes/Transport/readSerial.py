# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import time

import Domoticz
import serial
from Classes.Transport.readDecoder import decode_and_split_message
from Classes.Transport.tools import handle_thread_error, stop_waiting_on_queues


# Manage Serial Line
def open_serial(self):
    if self._connection:
        self._connection.close()
        del self._connection
        self._connection = None

    try:
        self._connection = serial.Serial(self._serialPort, baudrate=115200, rtscts=False, dsrdtr=False, timeout=None)

    except serial.SerialException as e:
        self.logging_receive("Error", "Cannot open Zigate port %s error: %s" % (self._serialPort, e))
        return False

    time.sleep(0.5)  # wait fro 100 ms for pyserial port to actually be ready
    self.logging_receive("Status", "ZigateTransport: Serial Connection open: %s" % self._connection)
    return True


def serial_reset_line_in(self):
    if not self.force_dz_communication:
        self.logging_receive("Debug", "Reset Serial Line IN")
        self._connection.reset_input_buffer()


def close_serial(self):
    self.logging_receive("Status", "ZigateTransport: Serial Connection closing: %s" % self._connection)
    try:
        self._connection.reset_input_buffer()
        self._connection.reset_output_buffer()
        self._connection.close()
        del self._connection
        self._connection = None
        self.logging_receive("Status", "ZigateTransport: Serial Connection closed: %s" % self._connection)
    except Exception as e:
        self.logging_receive("Log", "ZigateTransport: Error while Serial Connection closing: %s - %s" % (self._connection, e))

    time.sleep(0.5)


def serial_read_write_from_zigate(self):

    self.logging_receive("Debug", "serial_read_from_zigate - listening")
    serial_reset_line_in(self)
    while self.running:

        # Check if we need to upgrade to HW flow control (case of DIN Zigate, or USB Zigate+)
        self.logging_receive(
            "Debug",
            "RTSCTS: %s ZiGateHWVersion: %s Transp: %s" % (self._connection.rtscts, self.ZiGateHWVersion, self._transp),
        )
        if (
            self._serialPort.find("COM") == -1
            and not self._connection.rtscts
            and (
                (self.ZiGateHWVersion == 2 and self._transp in ("V2-USB", "V2-DIN"))
                or (self.ZiGateHWVersion == 1 and self._transp in ("DIN"))
            )
        ):
            self.logging_receive("Status", "Upgrade Serial line to RTS/CTS HW flow control")
            self._connection.rtscts = True

        # We loop until self.running is set to False,
        # which indicate plugin shutdown
        if not (self._connection and self._connection.is_open):
            time.sleep(0.5)
            continue

        # Reading (prio to read)
        serial_read_from_zigate(self)

        # Writing
        serial_write_to_zigate(self)

        time.sleep(0.05)

    stop_waiting_on_queues(self)
    self.logging_receive("Status", "ZigateTransport: ZiGateSerialListen Thread stop.")


def serial_read_from_zigate(self):

    while self._connection.in_waiting:
        try:
            data = self._connection.read(self._connection.in_waiting)
        except serial.SerialException as e:
            data = None
            self.logging_receive("Error", "serial_read_from_zigate - error while reading %s" % (e))
            # Might try to reconnect
        except Exception as e:
            # probably some I/O problem such as disconnected USB serial
            # adapters -> exit
            self.logging_receive("Error", "Error while receiving a ZiGate command: %s" % e)
            handle_thread_error(self, e, 0, 0, data)
            self._connection = None
            break

        if data:
            decode_and_split_message(self, data)


def serial_write_to_zigate(self):

    try:
        if not self._connection or not self._connection.is_open:
            _context = {
                "Error code": "TRANS-WRTZGTE-02",
                "serialConnection": str(self._connection),
            }
            self.logging_send_error("write_to_zigate port is closed!", context=_context)
            return "PortClosed"

        if self.serial_send_queue.qsize() > 0:
            encode_data = self.serial_send_queue.get()
            nb_write = self._connection.write(encode_data)
            if nb_write != len(encode_data):
                _context = {
                    "Error code": "TRANS-WRTZGTE-01",
                    "EncodedData": str(encode_data),
                    "serialConnection": str(self._connection),
                    "NbWrite": nb_write,
                }
                self.logging_send_error("write_to_zigate", context=_context)
            else:
                self._connection.flush()

    except TypeError as e:
        # Disconnect of USB->UART occured
        self.logging_send("Error", "write_to_zigate - error while writing %s" % (e))
        return False
