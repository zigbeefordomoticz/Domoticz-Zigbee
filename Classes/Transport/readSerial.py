# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import serial
import time


BAUDS = 115200
# Manage Serial Line
def open_serial( self ):

    try:
        self._connection = serial.Serial(self._serialPort, baudrate = BAUDS, rtscts = False, dsrdtr = False, timeout = None)
        if self._transp in ('DIN', 'V2' ):
            self._connection.rtscts = True

    except serial.SerialException as e:
        Domoticz.Error("Cannot open Zigate port %s error: %s" %(self._serialPort, e))
        return False

    Domoticz.Status("ZigateTransport: Serial Connection open: %s" %self._connection)
    return True

def serial_read_from_zigate( self ):

    serialConnection = self._connection

    while self.running:
        # We loop until self.running is set to False, 
        # which indicate plugin shutdown   
        data = None
        nb_in = serialConnection.in_waiting
        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_send('Log', "before Read")
        try:
            data = serialConnection.read( serialConnection.in_waiting or 1)  # Blocking Read
        except serial.SerialTimeoutException:
            data = None
        except serial.SerialException as e:
            Domoticz.Error("serial_read_from_zigate - error while reading %s" %(e))
            data = None
        if data is None:
            continue

        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_send('Log', "serial_read_from_zigate %s" %str(data))

        if self.pluginconf.pluginConf['ZiGateReactTime']:
            # Start
            self.reading_thread_timing = 1000 * time.time()

        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_send('Log', "Before decode_and_split_message")

        self.decode_and_split_message(data)

        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_send('Log', "After decode_and_split_message")

        if self.pluginconf.pluginConf['ZiGateReactTime']:
            # Stop
            timing = int( ( 1000 * time.time()) - self.reading_thread_timing )

            self.statistics.add_timing_thread( timing)
            if timing > 1000:
                self.logging_send('Log', "serial_read_from_zigate %s ms spent in decode_and_split_message()" %timing)


    self.Thread_proc_recvQueue_and_process.put("STOP") # In order to unblock the Blocking get()
    self.Thread_process_and_sendQueue.put("STOP")
    Domoticz.Status("ZigateTransport: ZiGateSerialListen Thread stop.")
    self.Thread_proc_zigate_frame.join()
    self.Thread_process_and_send.join()