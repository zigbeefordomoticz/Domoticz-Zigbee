#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import gzip
import json
import zlib

from Classes.WebServer.tools import MAX_KB_TO_SEND, DumpHTTPResponseToLog

http_status_codes = {
    100: "HTTP/1.1 100 Continue\r\n",
    101: "HTTP/1.1 101 Switching Protocols\r\n",
    200: "HTTP/1.1 200 OK\r\n",
    201: "HTTP/1.1 201 Created\r\n",
    202: "HTTP/1.1 202 Accepted\r\n",
    204: "HTTP/1.1 204 No Content\r\n",
    301: "HTTP/1.1 301 Moved Permanently\r\n",
    302: "HTTP/1.1 302 Found\r\n",
    304: "HTTP/1.1 304 Not Modified\r\n",
    400: "HTTP/1.1 400 Bad Request\r\n",
    401: "HTTP/1.1 401 Unauthorized\r\n",
    403: "HTTP/1.1 403 Forbidden\r\n",
    404: "HTTP/1.1 404 Not Found\r\n",
    405: "HTTP/1.1 405 Method Not Allowed\r\n",
    500: "HTTP/1.1 500 Internal Server Error\r\n",
    501: "HTTP/1.1 501 Not Implemented\r\n",
    503: "HTTP/1.1 503 Service Unavailable\r\n",
    505: "HTTP/1.1 505 HTTP Version Not Supported\r\n"
}

HTTP_HEADERS = {
    "Server", 
    "User-Agent", 
    "Access-Control-Allow-Headers", 
    "Access-Control-Allow-Methods",
    "Access-Control-Allow-Origin",
    "Referrer-Policy",
    "Cookie",
    "Connection",
    "Cache-Control",
    "Pragma",
    "Expires",
    "Accept",
    "Last-Modified",
    "Content-Type",
    "Content-Encoding",
}

def send_chunk(self, socket, data):
    if not data:
        return

    for i in range(0, len(data), MAX_KB_TO_SEND):
        chunck_data = data[ i : i + MAX_KB_TO_SEND]
        chunk_size = f"{len(chunck_data):X}\r\n".encode('utf-8')
        socket.sendall(chunk_size + chunck_data + b"\r\n")

    socket.sendall(b"0\r\n\r\n")

def send_http_message( self, socket, http_message, chunked=False):
    if chunked:
        send_chunk(self, socket, http_message)
    else:
        socket.sendall( http_message )


def convert_response_to_utf8( response ):
    response_body = ""

    if "Data" in response and response["Data"]:
        response_data = response["Data"]

        if isinstance(response_data, dict):
            response_body = json.dumps(response)

        elif isinstance(response_data, bytes):
            try:
                response_body = response_data.decode('utf-8')
            except UnicodeDecodeError:
                response_body = response_data.decode('latin-1')

        else:
            response_body = str(response_data)

    return response_body.encode('utf-8')


def prepare_http_response( self, response_dict, gziped, deflated , chunked):
    
    response_body = convert_response_to_utf8( response_dict )

    if 'Status' in response_dict:
        status = response_dict[ "Status"].split(' ')
        status_code = 500 if len(status) < 1 else int(status[0])
        if status_code in http_status_codes: 
            http_response = http_status_codes[ status_code ].encode('utf-8')

    if 'Headers' in response_dict:
        headers = response_dict['Headers']
        for x in HTTP_HEADERS:
            if x in headers and headers[x]:
                http_response += f"{x}: {headers[x]}\r\n".encode('utf-8')

    http_response += f"Content-Length: {len(response_body)}\r\n".encode('utf-8')

    if chunked:
        http_response += "Transfer-Encoding: chunked\r\n".encode('utf-8')

    if gziped:
        http_response += "Content-Encoding: gzip\r\n".encode('utf-8')
        response_body = gzip.compress(response_body)
    elif deflated:
        http_response += "Content-Encoding: deflate\r\n".encode('utf-8')
        response_body = zlib.compress(response_body)
        
    http_response += "\r\n".encode('utf-8')

    self.logging("Log", f"{http_response}")
    http_response += response_body

    return http_response


def sendResponse(self, client_socket, Response, AcceptEncoding=None):

    # No data   
    if "Data" not in Response:
        send_http_message( self, client_socket, prepare_http_response( self, Response ))
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
        return

    # Empty Data
    if Response["Data"] is None:
        send_http_message( self, client_socket, prepare_http_response( self, Response ))
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
        return

    # Compression
    allowgzip = self.pluginconf.pluginConf["enableGzip"] and AcceptEncoding.find("gzip")
    allowdeflate = self.pluginconf.pluginConf["enableDeflate"] and AcceptEncoding.find("deflate")
    allowchunked = self.pluginconf.pluginConf["enableChunk"] and len(Response["Data"]) > MAX_KB_TO_SEND
    
    allowdeflate = False
    allowgzip = False
    allowchunked = False
    
    send_http_message( self, client_socket, prepare_http_response( self, Response, allowgzip, allowdeflate, allowchunked ))
    
    if not self.pluginconf.pluginConf["enableKeepalive"]:
        client_socket.close()
