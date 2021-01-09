# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import socket
import time

from Classes.Transport.tools import stop_waiting_on_queues, handle_thread_error
from Classes.Transport.readDecoder import decode_and_split_message

# Manage TCP connection
def open_tcpip( self ):
    try:
        self._connection = socket.create_connection( (self._wifiAddress, self._wifiPort) )

    except socket.Exception as e:
        self.logging_receive('Error',"Cannot open Zigate Wifi %s Port %s error: %s" %(self._wifiAddress, self._serialPort, e))
        return False

    self.logging_receive('Status',"ZigateTransport: TCPIP Connection open: %s" %self._connection)
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

        except Exception as e:
            self.logging_receive('Error',"Error while receiving a ZiGate command: %s" %e)
            handle_thread_error( self, e, 0, 0, data)

        if data: 
            decode_and_split_message(self, data)


    stop_waiting_on_queues( self )
    self.logging_receive('Status',"ZigateTransport: ZiGateTcpIpListen Thread stop.")