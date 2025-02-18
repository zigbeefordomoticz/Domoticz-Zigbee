# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import contextlib
import select
import socket
import time
import errno

from Classes.ZigateTransport.readDecoder import decode_and_split_message
from Classes.ZigateTransport.tools import (handle_thread_error,
                                           stop_waiting_on_queues)
from Modules.zigateConsts import MAX_SIMULTANEOUS_ZIGATE_COMMANDS

MAX_RETRY = 5
WAITING_TIME = 10.0

# Manage TCP connection

def open_tcpip(self):
    """ Open TCTIP connection to the ZiGate"""
    try:
        self._connection = socket.create_connection((self._wifiAddress, self._wifiPort))

        # Set socket options: allow address reuse
        self._connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        set_keepalive(self, self._connection)

        self.logging_tcpip("Status", f"ZigateTransport: TCPIP Connection open: {self._connection}")
        time.sleep(1.0)  # Optional
        return True

    except Exception as e:
        self.logging_tcpip("Error", f"Cannot open Zigate Wifi {self._wifiAddress} Port {self._wifiPort} error: {e}")
        return False

def set_keepalive(self, sock):
    set_keepalive_linux(sock)


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
    """ Reconnect the TCP connection to the ZiGate"""
    self.logging_tcpip("Error", f"tcp_re_connect - Trying to reconnect the TCP connection !!!! {self._connection}")

    if self._connection:
        with contextlib.suppress(Exception):
            self._connection.shutdown(socket.SHUT_RDWR)
            self.logging_tcpip("Debug", "tcp_re_connect - TCP connection nicely shutdown")

    for attempt in range(1, MAX_RETRY + 1):
        if open_tcpip(self):
            self.logging_tcpip("Error", f"tcp_re_connect - TCP connection successfully re-established :-) {self._connection}")
            return True
        self.logging_tcpip("Error", f"tcp_re_connect - reconnection attempt {attempt}")
        time.sleep(WAITING_TIME)

    return False


def tcpip_read_from_zigate(self):
    """Handles both reading from and writing to the TCP socket."""

    # Does Read and Write , as python is not socket thread-safe
    while self.running:
        # Check if the connection is valid
        if not self._connection or self._connection.fileno() == -1:
            self.logging_tcpip("Error", "tcpip_read_from_zigate: Connection is not available.")
            if not tcp_re_connect(self):
                return "SocketClosed"
            continue  # Retry after reconnection

        try:
            readable, writable, exceptional = select.select([self._connection], [self._connection], [], 5)
        except socket.error as e:
            self.logging_tcpip("Error", f"tcpip_read_from_zigate: Select error: {e}")
            if not tcp_re_connect(self):
                return "WifiError"
            continue

        # Read data if any
        if readable:
            if self.pluginconf.pluginConf["ZiGateReactTime"]:
                # Start
                self.reading_thread_timing = 1000 * time.time()

            try:
                data = self._connection.recv(1024)

                if data:
                    self.logging_tcpip("Debug", "Receiving: %s" %str(data))
                    decode_and_split_message(self, data)
                else:
                    self.logging_tcpip("Error", "tcpip_read_from_zigate: Received empty data (socket closed by remote).")
                    if not tcp_re_connect(self):
                        return "WifiError"
                    continue

            except socket.error as e:
                self.logging_tcpip("Error", f"tcpip_read_from_zigate: Error while receiving data: {e}")
                if not tcp_re_connect(self):
                    return "WifiError"
                continue

            except Exception as e:
                self.logging_tcpip( "Error", f"tcpip_read_from_zigate: Connection error while receiving data {e} on {self._connection}" % (e, self._connection), )
                if tcp_re_connect(self):
                    continue
                return "WifiError"

        # Write data if available
        if writable:
            try:
                encode_data = self.tcp_send_queue.get_nowait()
                self.logging_tcpip("Debug", f"Sending: {encode_data}")

                len_data_sent = self._connection.send(encode_data)
                if len_data_sent != len(encode_data):
                    self.logging_tcpip("Error", "tcpip_read_from_zigate - Not all data was sent. Please report!")

            except socket.error as e:
                self.logging_tcpip("Error", f"tcpip_read_from_zigate: Error while sending data: {e}")
                if not tcp_re_connect(self):
                    return "WifiError"
                continue

            except Exception:
                pass  # No data to send

        if exceptional:
            self.logging_tcpip("Error", f"tcpip_read_from_zigate: Socket error detected on {self._connection}")
            if not tcp_re_connect(self):
                return "WifiError"

    self.logging_tcpip("Status", "ZigateTransport: ZiGateTcpIpListen Thread stopped.")
    stop_waiting_on_queues(self)