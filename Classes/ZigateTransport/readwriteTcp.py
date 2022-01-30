# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import select
import socket
import time

from Classes.ZigateTransport.readDecoder import decode_and_split_message
from Classes.ZigateTransport.tools import (handle_thread_error,
                                           stop_waiting_on_queues)
from Modules.zigateConsts import MAX_SIMULTANEOUS_ZIGATE_COMMANDS


# Manage TCP connection
def open_tcpip(self):
    try:
        self._connection = None
        self._connection = socket.create_connection((self._wifiAddress, self._wifiPort))

    except Exception as e:
        self.logging_tcpip(
            "Error", "Cannot open Zigate Wifi %s Port %s error: %s" % (self._wifiAddress, self._serialPort, e)
        )
        return False

    set_keepalive(self, self._connection)
    self.logging_tcpip("Status", "ZigateTransport: TCPIP Connection open: %s" % self._connection)
    time.sleep(1.0)
    return True


def set_keepalive(self, sock):
    set_keepalive_linux(sock)


# def set_keepalive_windows( sock, after_idle_sec=1, interval_sec=3, max_fails=20):
#    sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 3000))


def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    """Set TCP keepalive on an open socket.
    It activates after 5 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 5 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 secondes
    re: https://stackoverflow.com/questions/5686490/detect-socket-hangup-without-sending-or-receiving/14780814
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


def tcp_re_connect(self):
    self.logging_tcpip("Debug", "tcp_re_connect - Trying to reconnect the TCP connection !!!! %s" % self._connection)
    if self._connection:
        try:
            self._connection.shutdown(socket.SHUT_RDWR)
            self.logging_tcpip("Debug", "tcp_re_connect - TCP connection nicely shutdown")
        except Exception as e:
            pass

    if not open_tcpip(self):
        return False
    self.logging_tcpip("Log", "tcp_re_connect - TCP connection successfuly re-established :-) %s" % self._connection)
    return True


def tcpip_read_from_zigate(self):
    # Does Read and Write , as python is not socket thread-safe
    while self.running:
        if self._connection is None:
            # Connection not yet ready !
            self.logging_tcpip("Error", "tcpip_read_from_zigate Connection not yet ready !")
            if tcp_re_connect(self):
                continue
            return "SocketClosed"

        socket_list = [self._connection]
        if self._connection.fileno() == -1:
            self.logging_tcpip("Error", "tcpip_read_from_zigate Socket seems to be closed!!!! ")
            if tcp_re_connect(self):
                continue
            return "SocketClosed"

        readable, writable, exceptional = select.select(socket_list, socket_list, [], 5)
        # Read data if any
        data = None
        if readable:
            if self.pluginconf.pluginConf["ZiGateReactTime"]:
                # Start
                self.reading_thread_timing = 1000 * time.time()
            try:
                data = self._connection.recv(1024)
                self.logging_tcpip("Debug", "Receiving: %s" %str(data))
                if data:
                    decode_and_split_message(self, data)

            except Exception as e:
                self.logging_tcpip(
                    "Error",
                    "tcpip_read_from_zigate: Connection error while receiving data %s on %s" % (e, self._connection),
                )
                if tcp_re_connect(self):
                    continue
                return "WifiError"

        # Write data if any
        if self.tcp_send_queue.qsize() > 0 and writable:
            encode_data = self.tcp_send_queue.get()
            self.logging_tcpip("Debug", "Sending: %s" %str(encode_data))
            
            try:
                len_data_sent = self._connection.send(encode_data)
                if len_data_sent != len(encode_data):
                    self.logging_tcpip(
                        "Error", "tcpip_read_from_zigate - Not all data have been sent !!! Please report !!!!%s "
                    )
                continue

            except Exception as e:
                self.logging_tcpip(
                    "Error",
                    "tcpip_read_from_zigate: Connection error while sending data %s on %s" % (e, self._connection),
                )
                if tcp_re_connect(self):
                    continue
                return "WifiError"

        elif exceptional:
            self.logging_tcpip("Error", "native_write_to_zigate We have detected an error .... on %s" % self._connection)
            if tcp_re_connect(self):
                continue
            return "WifiError"

        time.sleep(0.05)

    stop_waiting_on_queues(self)
    self.logging_tcpip("Status", "ZigateTransport: ZiGateTcpIpListen Thread stop.")
