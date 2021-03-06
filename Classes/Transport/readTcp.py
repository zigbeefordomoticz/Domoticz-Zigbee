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

    except Exception as e:
        self.logging_receive('Error',"Cannot open Zigate Wifi %s Port %s error: %s" %(self._wifiAddress, self._serialPort, e))
        return False

    self.logging_receive('Status',"ZigateTransport: TCPIP Connection open: %s" %self._connection)
    set_keepalive( self, self._connection)
    return True

def set_keepalive( self, sock):
    self.logging_receive('Status',"Set Keepalive option on the connection") 
    set_keepalive_linux( sock )

#def set_keepalive_windows( sock, after_idle_sec=1, interval_sec=3, max_fails=20):
#    sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 3000))
    
def set_keepalive_linux( sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    """Set TCP keepalive on an open socket.
    It activates after 5 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 5 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 secondes
    re: https://stackoverflow.com/questions/5686490/detect-socket-hangup-without-sending-or-receiving/14780814
    """
     
    sock.setsockopt(socket.SOL_SOCKET,  socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


def tcpip_read_from_zigate( self ):
    
    while self.running:

        if self.pluginconf.pluginConf['ZiGateReactTime']:
            # Start
            self.reading_thread_timing = 1000 * time.time()

        data = None
        try:
            if self._connection is None:
                # Connection not yet ready !
                if self._connection_break:
                    self.re_conn()
                time.sleep(1.0)
                continue

            data = self._connection.recv(1024)

        except socket.timeout:
            # No data after 0.5 seconds
            pass

        except Exception as e:
            if e.errno == 110:
                # Connection timeout. Might trigger a reconnect
                self.logging_receive('Error',"Looks like we have lost the TCP-ZiGate connection")
                self._connection_break = True
                self.re_conn()
            else:
                self.logging_receive('Error',"Error while receiving a ZiGate command: %s" %e)
                handle_thread_error( self, e, 0, 0, data)

        if data: 
            decode_and_split_message(self, data)


    stop_waiting_on_queues( self )
    self.logging_receive('Status',"ZigateTransport: ZiGateTcpIpListen Thread stop.")