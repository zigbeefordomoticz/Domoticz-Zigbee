# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import socket
import time



# Manage TCP connection
def open_tcpip( self ):
    try:
        self._connection = socket.create_connection( (self._wifiAddress, self._wifiPort) )

    except socket.Exception as e:
        Domoticz.Error("Cannot open Zigate Wifi %s Port %s error: %s" %(self._wifiAddress, self._serialPort, e))
        return False

    Domoticz.Status("ZigateTransport: TCPIP Connection open: %s" %self._connection)
    return True


def tcpip_read_from_zigate( self ):
    
    tcpipConnection = self._connection
    while self.running:

        if self.pluginconf.pluginConf['ZiGateReactTime']:
            # Start
            self.reading_thread_timing = 1000 * time.time()

        data = None
        try:
            data = tcpipConnection.recv(1024)
        except socket.timeout:
            # No data after 0.5 seconds
            pass

        if data: 
            self.decode_and_split_message(data)

        if self.pluginconf.pluginConf['ZiGateReactTime']:
            # Stop
            timing = int( ( 1000 * time.time()) - self.reading_thread_timing )

            self.statistics.add_timing_thread( timing)
            if timing > 1000:
                self.logging_send('Log', "tcpip_listen_and_send %s ms spent in decode_and_split_message()" %timing)

    self.frame_queue.put("STOP") # In order to unblock the Blocking get()
    self.Thread_process_and_sendQueue.put("STOP")
    Domoticz.Status("ZigateTransport: ZiGateTcpIpListen Thread stop.")
