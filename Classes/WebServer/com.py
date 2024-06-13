#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import socket
import threading
import traceback

from Modules.domoticzAbstractLayer import domoticz_connection

MAX_BYTES = 1024

def startWebServer(self):

    self.logging("Status", "start_logging_thread")
    if self.server_thread:
        self.logging("Error", "start_logging_thread - Looks like logging_thread already started !!!")
        return

    # Create and start the server thread
    self.server_thread = threading.Thread( name="ZigbeeWebUI_%s" % self.hardwareID, target=run_server, args=(self,) )
    self.server_thread.daemon = True  # This makes the thread exit when the main program exits
    self.server_thread.start()


def close_all_clients(self):
    self.logging("Log", "Closing all client connections...")
    for client_addr, client_socket in self.clients.items():
        self.logging("Log", f"  - Closing {client_addr}")
        client_socket.close()
    self.clients.clear()


def parse_http_request(data):
    lines = data.split("\r\n")
    request_line = lines[0].strip()
    method, path, _ = request_line.split(" ", 2)

    headers = {}
    body = ""

    # Parse headers
    for line in lines[1:]:
        if line.strip():
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        else:
            break

    # Parse body if present
    if "Content-Length" in headers:
        content_length = int(headers["Content-Length"])
        body = lines[-1] if content_length > 0 else ""

    return method, path, headers, body.encode('utf-8')


def receive_data(self, client_socket):
    chunks = []
    try:
        while True:
            chunk = client_socket.recv(MAX_BYTES)
            if not chunk:
                break
            chunks.append(chunk)
            if len(chunk) < MAX_BYTES:
                break

    except socket.error as e:
        # This most likely will happen when connection is closed.
        self.logging("Debug", f"receive_data - Socket error with: {e}")
        return b""

    return b"".join(chunks)


def handle_client(self, client_socket, client_addr):
    # Handle client connection
    self.logging("Debug", f"handle_client from {client_addr} {client_socket}")
    self.clients[ str(client_addr) ] = client_socket

    client_socket.settimeout(1)
    try:
        while self.running:
            try:
                data = receive_data(self, client_socket).decode('utf-8')

                if not data:
                    self.logging("Debug", f"no data from {client_addr}")
                    break

                method, path, headers, body = parse_http_request(data)

                Data = decode_http_data(self, method, path, headers, body)
                self.onMessage(client_socket, Data)

            except socket.timeout:
                self.logging("Debug", f"Socket timedout {client_addr}")
                continue

            except socket.error as e:
                self.logging("Debug", f"Socket error with {client_addr}: {e}")
                break

            except Exception as e:
                self.logging("Log", f"Unexpected error with {client_addr}: {e}")
                self.logging("Log", f"{traceback.format_exc() }")
                break

    finally:
        self.logging("Debug", f"Closing connection to {client_addr}.")
        if str(client_addr) in self.clients:
            del self.clients[ str(client_addr) ]
        client_socket.close()


def run_server(self, host='0.0.0.0', port=9440):

    self.logging( "Debug","webui_thread - listening")

    # Set up the server
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if self.httpPort:
        port = int(self.httpPort)
    if self.httpIp:
        host = self.httpIp
    
    self.logging( "Debug", f"webui_thread - listening on {host}:{port}")
    self.server.bind((host, port))
    self.server.listen(5)
    self.server.settimeout(1)

    self.logging("Status", f"WebUI Server started on {host}:{port}")

    try:
        self.running = True
        while self.running:
            try:
                client_socket, client_addr = self.server.accept()

                self.logging("Debug", f"Accepted connection from {client_addr} {client_socket}")
                client_thread = threading.Thread(target=handle_client, args=(self, client_socket, client_addr))
                client_thread.daemon = True
                client_thread.start()
                self.client_threads.append(client_thread)
                
            except socket.timeout:
                    continue
    
            except Exception as e:
                self.logging("Debug", f"Error: {e}")
                break
    finally:
        close_all_clients(self)
        self.server.close()
        self.logging("Debug", "Server shut down")

    self.logging( "Debug", "webui_thread - ended")


def decode_http_data(self, method, path, headers, body):
    return {
        "Verb": method,
        "URL": path,
        "Headers": headers,
        "Data": body
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

    for client_thread in self.client_threads:
        client_thread.join()
    
    self.server_thread.join()

    # Search for Protocol
    for connection in self.httpServerConns:
        self.logging("Log", "Closing %s" % connection)
        self.httpServerConns[connection.Name].close()

    for connection in self.httpsServerConns:
        self.logging("Log", "Closing %s" % connection)
        self.httpServerConns[connection.Name].close()
