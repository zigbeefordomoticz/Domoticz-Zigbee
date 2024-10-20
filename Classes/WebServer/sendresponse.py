#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import gzip
import json
import zlib

from Classes.WebServer.tools import MAX_BLOCK_SIZE, DumpHTTPResponseToLog

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

def send_by_chunk(self, socket, http_response, response_body):
    """ send and chunk the response_body already bytes encoded """

    if not response_body:
        return

    # send the HTTP headers
    socket.sendall( http_response.encode('utf-8'))

    for i in range(0, len(response_body), MAX_BLOCK_SIZE):
        chunck_data = response_body[ i : i + MAX_BLOCK_SIZE]

        socket.sendall(f"{len(chunck_data):X}\r\n".encode("utf-8"))
        socket.sendall(chunck_data)
        socket.sendall(b"\r\n")

        self.logging("Debug", "Sending Chunk: %s out of %s" % (i, len(response_body) / MAX_BLOCK_SIZE))

    # Closing Chunk
    socket.sendall(b"0\r\n\r\n")


def send_http_message( self, socket, http_response, response_body, chunked=False):
    if chunked:
        send_by_chunk(self, socket, http_response, response_body)
    else:
        socket.sendall( http_response.encode('utf-8') + response_body )


def encode_body_to_bytes(response):
    """Convert data payload into an HTTP response body encoded bytes."""
    if "Data" not in response:
        return b''
 
    response_data = response["Data"]

    if isinstance(response_data, dict):
        return json.dumps(response_data).encode('utf-8')

    elif isinstance(response_data, bytes):
        # If response_data is already bytes, return it as is
        return response_data

    elif response_data is not None:
        return str(response_data).encode('utf-8')

    # Default to an empty response if no valid Data is present
    return b''

 
def prepare_http_response( self, response_dict, gziped=False, deflated=False , chunked=False):

    # Prepare body (data converted to byte)
    response_body = encode_body_to_bytes( response_dict )

    if 'Status' in response_dict:
        status = response_dict[ "Status"].split(' ')
        status_code = 500 if len(status) < 1 else int(status[0])
        if status_code in http_status_codes: 
            http_response = http_status_codes[ status_code ]

    if 'Headers' in response_dict:
        headers = response_dict['Headers']
        for x in HTTP_HEADERS:
            if x in headers and headers[x]:
                http_response += f"{x}: {headers[x]}\r\n"

    # Determine if Compression, Deflate or Chunk to be used.
    orig_size = len(response_body)

    # prefer gzip for better compatibility, consistent behavior, and improved compression. If the two are accepted by the client
    if gziped:
        self.logging("Debug", "Compressing - gzip")
        http_response += "Content-Encoding: gzip\r\n"
        response_body = gzip.compress(response_body)
        self.logging( "Debug", "Compression from %s to %s (%s %%)" % (orig_size, len(response_body), int(100 - (len(response_body) / orig_size) * 100)), )

    elif deflated:
        self.logging("Debug", "Compressing - deflate")
        http_response += "Content-Encoding: deflate\r\n"
        zlib_compress = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 2)
        response_body = zlib_compress.compress(response_body)
        response_body += zlib_compress.flush()
        self.logging( "Debug", "Compression from %s to %s (%s %%)" % (orig_size, len(response_body), int(100 - (len(response_body) / orig_size) * 100)), )

    # Content-Length set to the body sent. If compressed this has to be the 
    http_response += f"Content-Length: {len(response_body)}\r\n"

    if chunked:
        http_response += "Transfer-Encoding: chunked\r\n"

    http_response += "\r\n"
    self.logging("Debug", f"{http_response}")

    return http_response, response_body


def sendResponse(self, client_socket, Response, AcceptEncoding=None):

    # No data   
    if "Data" not in Response:
        http_response, response_body = prepare_http_response( self, Response )
        send_http_message( self, client_socket, http_response, response_body)
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
        return

    # Empty Data
    if Response["Data"] is None:
        http_response, response_body = prepare_http_response( self, Response )
        send_http_message( self, client_socket, http_response, response_body)
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
        return

    # Compression
    request_gzip = self.pluginconf.pluginConf["enableGzip"] and AcceptEncoding and (AcceptEncoding.find("gzip") != -1)
    request_deflate = self.pluginconf.pluginConf["enableDeflate"] and AcceptEncoding and (AcceptEncoding.find("deflate") != -1)
    request_chunked = self.pluginconf.pluginConf["enableChunk"] and len(Response["Data"]) > MAX_BLOCK_SIZE
    
    self.logging("Debug", f"request_gzip {request_gzip} - request_deflate {request_deflate} request_chunked {request_chunked}")
    http_response, response_body = prepare_http_response( self, Response, request_gzip, request_deflate, request_chunked )
    send_http_message( self, client_socket, http_response, response_body ,request_chunked)
    
    if not self.pluginconf.pluginConf["enableKeepalive"]:
        client_socket.close()
