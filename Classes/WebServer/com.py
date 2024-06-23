#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import os
import socket
import ssl
import threading
import traceback

from Modules.domoticzAbstractLayer import domoticz_connection

MAX_BYTES = 1024

def startWebServer(self):

    self.logging("Status", "WebUI thread started")
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
    """
    Parse an HTTP request string into its components.

    This function splits the HTTP request data into the request line, headers, and body. It assumes that
    the data follows the standard HTTP request format.

    Args:
        data (str): The HTTP request data as a string.

    Returns:
        tuple: A tuple containing:
            - method (str): The HTTP method (e.g., 'GET', 'POST').
            - path (str): The requested path (e.g., '/index.html').
            - headers (dict): A dictionary of headers where keys are header names and values are header values.
            - body (bytes): The body of the request as a bytes object.

    Raises:
        ValueError: If the request line is malformed or the headers cannot be parsed correctly.
    """
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
    """
    Receive data from the client socket.

    This method reads data from the given client socket in chunks until the connection is closed
    or no more data is available. It handles socket errors gracefully and ensures all received
    data is returned as a single bytes object.

    Args:
        client_socket (socket.socket): The socket object representing the client connection.

    Returns:
        bytes: The complete data received from the client. If a socket error occurs, an empty bytes object is returned.

    Steps:
        1. Initialize an empty list to hold the chunks of data.
        2. Enter a loop to receive data from the client socket.
        3. Read a chunk of data up to MAX_BYTES in size.
        4. If no data is received (connection closed), break the loop.
        5. Append the received chunk to the list of chunks.
        6. If the received chunk is smaller than MAX_BYTES, break the loop (indicates end of data).
        7. Handle any socket errors by logging the error and returning an empty bytes object.
        8. Join all chunks into a single bytes object and return it.

    Exceptions:
        socket.error: Logs the error and returns an empty bytes object.
    """
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
    """
    Handle an individual client connection.

    This method manages the interaction with a client, including receiving data,
    parsing HTTP requests, decoding the data, and invoking the appropriate message
    handler. It handles timeouts, socket errors, and unexpected exceptions gracefully,
    ensuring the client connection is closed properly.

    Args:
        client_socket (socket.socket): The socket object representing the client connection.
        client_addr (tuple): The address of the client.

    Steps:
        1. Log the connection and add the client socket to the clients dictionary.
        2. Set a timeout on the client socket.
        3. Enter a loop to handle incoming data while the server is running.
        4. Receive data from the client, decode it, and parse the HTTP request.
        5. Decode the HTTP data and call the onMessage handler.
        6. Handle socket timeouts, errors, and unexpected exceptions.
        7. Remove the client from the clients dictionary and close the socket on exit.

    Exceptions:
        socket.timeout: Logs and continues on socket timeout.
        socket.error: Logs and breaks the loop on socket error.
        Exception: Logs and breaks the loop on any other unexpected error.
    """

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


def check_cert_and_key(self, cert_dir, cert_filename="server.crt", key_filename="server.key"):
    """
    Check for the existence and validity of the SSL certificate and key files.

    This method verifies that the specified certificate and key files exist and are
    correctly formatted for use in an SSL context. If the certificate or key files
    are missing or invalid, SSL will not be enabled.

    Args:
        cert_dir (str): The directory where the certificate and key files are located.
        cert_filename (str): The filename of the certificate file. Defaults to "server.crt".
        key_filename (str): The filename of the key file. Defaults to "server.key".

    Returns:
        ssl.SSLContext or None: An SSL context if the certificate and key files are valid,
                                None otherwise.

    Steps:
        1. Construct full paths to the certificate and key files.
        2. Check if the certificate directory exists.
        3. Check if the certificate and key files exist.
        4. Attempt to load the certificate and key files into an SSL context to verify correctness.
        5. Log appropriate messages at each step for missing or invalid files.
        6. Return the SSL context if successful, or None if there are errors.

    Exceptions:
        ssl.SSLError: Logs SSL-specific errors encountered during certificate and key loading.
        Exception: Logs any other general errors encountered during the process.
    """
    cert_path = os.path.join(cert_dir, cert_filename)
    key_path = os.path.join(cert_dir, key_filename)

    # Check if cert directory exists
    if not os.path.exists(cert_dir):
        self.logging( "Log",f"Warning directory '{cert_dir}' does not exist. WebUI SSL connection will not be available")
        return None

    # Check if cert and key files exist
    if not os.path.exists(cert_path):
        self.logging( "Error",f"Certificate file '{cert_path}' does not exist.")
        return None

    if not os.path.exists(key_path):
        self.logging( "Error",f"Key file '{key_path}' does not exist.")
        return None

    try:
        # Attempt to load cert and key to verify correctness
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    except ssl.SSLError as e:
        self.logging( "Error",f"SSL error: {e}")
        return None

    except Exception as e:
        self.logging( "Error",f"Error: {e}")
        return None

    self.logging( "Debug", "Certificate and key files exist and are correct.")
    return context


def run_server(self, host='0.0.0.0', port=9440):
    """
    Start the web server by creating and binding a socket on the specified IP and port.

    This method initializes the web server, optionally setting up SSL if the required 
    certificate and key files are found. The server listens for incoming connections 
    and handles them in separate threads.

    Args:
        host (str): The IP address to bind the server to. Defaults to '0.0.0.0'.
        port (int): The port number to bind the server to. Defaults to 9440.

    Steps:
        1. Logs the server start message.
        2. Uses configured IP and port if available.
        3. Creates a socket for the server.
        4. Checks for SSL certificates and sets up SSL context if available.
        5. Sets socket options and binds it to the specified host and port.
        6. Sets the socket to listen for incoming connections.
        7. Logs the status message indicating whether SSL is enabled.
        8. Starts the server loop to accept and handle client connections.

    Exceptions:
        Exception: Logs any errors encountered during the server setup and startup process.
    """

    self.logging( "Log","WebUI - server started on {host} {port}")

    try:
        # Set up the server
        if self.httpPort:
            port = int(self.httpPort)
        if self.httpIp:
            host = self.httpIp

        self.logging( "Log", "++ WebUI - create socket")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Check certificate and key
        context = check_cert_and_key(self, self.homedirectory + "certs", "server.crt", "server.key")

        if context:
            self.server = context.wrap_socket( self.server, server_side=True, )

        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.logging( "Log", f"++ WebUI - bin socket on {host}:{port}")
        self.server.bind((host, port))
        self.server.listen(5)
        self.server.settimeout(5)

        if context:
            self.logging("Status", f"WebUI Server started on SSL https://{host}:{port}")
        else:
            self.logging("Status", f"WebUI Server started on {host}:{port}")

        server_loop(self, )

        self.logging( "Debug", "webui_thread - ended")

    except Exception as error:
        self.logging( "Error", f"webui_thread - error in run_server {host} {port}")
        self.logging( "Error", f"               {error}")
        self.logging( "Error", f"               {str(traceback.format_exc())}")


def server_loop(self, ):
    """
    Main server loop for handling incoming client connections.

    This method runs the main server loop that accepts incoming client connections, 
    starts a new thread to handle each client, and manages exceptions and errors 
    that occur during the process. The server continues to run as long as the `self.running` 
    attribute is set to True.

    The method performs the following tasks:
    1. Sets the `self.running` attribute to True to start the server loop.
    2. Accepts incoming client connections using `self.server.accept()`.
    3. Logs the accepted connection and starts a new thread for each client using the `handle_client` method.
    4. Appends each client thread to `self.client_threads` for tracking.
    5. Handles `socket.timeout` exceptions by continuing the loop.
    6. Handles `ssl.SSLError` exceptions by logging an error message and continuing the loop.
    7. Handles generic exceptions by logging an error message and breaking the loop.
    8. On termination, calls `close_all_clients` to close all client connections and shuts down the server socket.

    Exceptions:
        socket.timeout: Logs a debug message and continues the loop.
        ssl.SSLError: Logs an SSL error message and continues the loop.
        Exception: Logs a generic error message and breaks the loop.

    """

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

            except (socket.timeout, TimeoutError):
                self.logging("Debug", "server_loop timeout")
                continue

            except ssl.SSLError as e:
                self.logging("Error", f"server_loop - SSL Error {e}, make sure to use https !!!")
                continue

            except (ConnectionError, OSError) as e:
                self.logging("Debug", f"server_loop - Socket error {e}")
                continue

            except Exception as e:
                self.logging("Error", f"server_loop - Unexpected error: {e}")
                break
    finally:
        close_all_clients(self)
        self.server.close()
        self.logging("Debug", "Server shut down")


def decode_http_data(self, method, path, headers, body):
    return {
        "Verb": method,
        "URL": path,
        "Headers": headers,
        "Data": body
    }

            
def onConnect(self, Connection, Status, Description):

    self.logging("Error", "Connection: %s, description: %s onConnect for WebUI deprecated" % (Connection, Description))


def onDisconnect(self, Connection):

    self.logging("Error", "onDisconnect %s on WebUI deprecated" % (Connection))


def onStop(self):

    # Make sure that all remaining open connections are closed
    
    self.running = False

    for client_thread in self.client_threads:
        client_thread.join()
    
    self.server_thread.join()
    self.logging("Status", "WebUI shutdown completed")
    
