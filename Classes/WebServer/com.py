#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from Modules.domoticzAbstractLayer import domoticz_connection
import threading
import socket


def startWebServer(self):

    self.logging("Status", "start_logging_thread")
    if self.server_thread:
        self.logging("Error", "start_logging_thread - Looks like logging_thread already started !!!")
        return

    # Create and start the server thread
    self.server_thread = threading.Thread( name="ZigbeeWebUI_%s" % self.hardwareID, target=run_server, args=(self,) )
    self.server_thread.daemon = True  # This makes the thread exit when the main program exits
    self.server_thread.start()


def handle_client(self, client_socket):
    # Handle client connection
    with client_socket:
        self.logging("Log", "Client connected")
        while self.running:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            
            Data = decode_http_data(self, data)
            self.onMessage(client_socket, Data)


def run_server(self, host='0.0.0.0', port=9440):

    self.logging( "Log","webui_thread - listening")
    # Set up the server
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if self.httpPort:
        port = int(self.httpPort)
    if self.httpIp:
        host = self.httpIp
    
    self.logging( "Log", f"webui_thread - listening on {host}:{port}")
    self.server.bind((host, port))
    self.server.listen(5)
    self.server.settimeout(1)
    self.logging("Log", f"Server started on {host}:{port}")

    self.running = True

    try:
        while self.running:
            try:
                client_socket, addr = self.server.accept()
                self.logging("Log", f"Accepted connection from {addr}")
                client_handler = threading.Thread(target=handle_client, args=(self, client_socket,))
                client_handler.daemon = True
                client_handler.start()
            except socket.timeout:
                    continue
    finally:
        self.server.close()
        self.logging("Log", "Server shut down")

    self.logging( "Log", "webui_thread - ended")


def decode_http_data(self, raw_data):
    # Split request into lines
    request_lines = raw_data.split('\r\n')
    
    # Request line is the first line
    request_line = request_lines[0]
    method, path, version = request_line.split()
    # Headers are the following lines until an empty line
    headers = {}
    for line in request_lines[1:]:
        if line == '':
            break
        key, value = line.split(': ', 1)
        headers[key] = value
    
    return {
        "Verb": method,
        "URL": path,
        "Headers": headers
    }

            
def onConnect(self, Connection, Status, Description):

    self.logging("Debug", "Connection: %s, description: %s" % (Connection, Description))
    if Status != 0:
        self.logging("Error", f"onConnect - Failed to connect ({str(Status)} to: {Connection.Address} : {Connection.Port} with error: {Description}")
        return

    if Connection is None:
        self.logging("Error", "onConnect - Uninitialized Connection !!! %s %s %s" % (Connection, Status, Description))
        return

    # Search for Protocol
    for item in str(Connection).split(","):
        if item.find("Protocol") != -1:
            label, protocol = item.split(":")
            protocol = protocol.strip().strip("'")
            self.logging("Debug", "%s:>%s" % (label, protocol))

    if protocol == "HTTP":
        # http connection
        if Connection.Name not in self.httpServerConns:
            self.logging("Debug", "New Connection: %s" % (Connection.Name))
            self.httpServerConns[Connection.Name] = Connection
    elif protocol == "HTTPS":
        # https connection
        if Connection.Name not in self.httpsServerConns:
            self.logging("Debug", "New Connection: %s" % (Connection.Name))
            self.httpServerConns[Connection.Name] = Connection
    else:
        self.logging("Error","onConnect - unexpected protocol for connection: %s" % (Connection))

    self.logging("Debug", "Number of http  Connections : %s" % len(self.httpServerConns))
    self.logging("Debug", "Number of https Connections : %s" % len(self.httpsServerConns))


def onDisconnect(self, Connection):

    self.logging("Debug", "onDisconnect %s" % (Connection))

    if Connection.Name in self.httpServerConns:
        self.logging("Debug", "onDisconnect - removing from list : %s" % Connection.Name)
        del self.httpServerConns[Connection.Name]
    elif Connection.Name in self.httpsServerConns:
        self.logging("Debug", "onDisconnect - removing from list : %s" % Connection.Name)
        del self.httpsServerConns[Connection.Name]
    else:
        # Most likely it is about closing the Server
        self.logging("Log", "onDisconnect - Closing %s" % Connection)


def onStop(self):

    # Make sure that all remaining open connections are closed
    self.logging("Debug", "onStop()")
    
    self.running = False
    self.server_thread.join()

    # Search for Protocol
    for connection in self.httpServerConns:
        self.logging("Log", "Closing %s" % connection)
        self.httpServerConns[connection.Name].close()

    for connection in self.httpsServerConns:
        self.logging("Log", "Closing %s" % connection)
        self.httpServerConns[connection.Name].close()
