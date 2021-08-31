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
        self.logging_receive(
            "Log", "ZigateTransport: Error while Serial Connection closing: %s - %s" % (self._connection, e)
        )
        pass
    time.sleep(0.5)


def serial_read_from_zigate(self):

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
        self.logging_receive("Debug", "serial_read_from_zigate - reading %s bytes" % 1)
        data = None
        try:
            if self._connection:
                data = self._connection.read(1)  # Blocking Read
                if len(data) > 1:
                    # We did a blocking read for 1 and we received more !!!
                    self.logging_receive(
                        "Error",
                        "serial_read_from_zigate - while serial read for 1 we got more !!! %s %s" % (data, len(data)),
                    )

        except serial.SerialException as e:
            self.logging_receive("Error", "serial_read_from_zigate - error while reading %s" % (e))
            data = None
            self._connection = None
            break

        except Exception as e:
            # probably some I/O problem such as disconnected USB serial
            # adapters -> exit
            self.logging_receive("Error", "Error while receiving a ZiGate command: %s" % e)
            handle_thread_error(self, e, 0, 0, data)
            self._connection = None
            break

        if data:
            decode_and_split_message(self, data)

    stop_waiting_on_queues(self)
    self.logging_receive("Status", "ZigateTransport: ZiGateSerialListen Thread stop.")
