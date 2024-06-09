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

def send_http_message( self, client_socket, http_message):
    
    client_socket.sendall( http_message )


def prepare_http_response( self, response_dict ):
    
    if "Data" in response_dict and response_dict["Data"]:
        response_data = response_dict["Data"]

        if isinstance( response_data, dict ):
            response_body = json.dumps(response_dict)

        elif isinstance( response_data, bytes ):
            try:
                response_body = response_data.decode('utf-8')

            except UnicodeDecodeError:
                response_body = response_data.decode('latin-1')

        else:
            response_body = response_data

    else:
        response_body = "".decode('utf-8')

    response_body = response_body.encode('utf-8')

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
    http_response += "\r\n".encode('utf-8')

    http_response += response_body

    return http_response


def sendResponse(self, client_socket, Response, AcceptEncoding=None):

    #self.logging( "Log", f"sendResponse - Response: {Response}")

                
    if "Data" not in Response:
        send_http_message( self, client_socket, prepare_http_response( self, Response ))
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
        return

    if Response["Data"] is None:
        send_http_message( self, client_socket, prepare_http_response( self, Response ))
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
        return

    # Compression
    allowgzip = self.pluginconf.pluginConf["enableGzip"]
    allowdeflate = self.pluginconf.pluginConf["enableDeflate"]

    if (allowgzip or allowdeflate) and "Data" in Response and AcceptEncoding and len(Response["Data"]) > MAX_KB_TO_SEND:
        orig_size = len(Response["Data"])
        if allowdeflate and AcceptEncoding.find("deflate") != -1:
            #self.logging("Debug", "Compressing - deflate")
            zlib_compress = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 2)
            deflated = zlib_compress.compress(Response["Data"])
            deflated += zlib_compress.flush()
            Response["Headers"]["Content-Encoding"] = "deflate"
            Response["Data"] = deflated
    
        elif allowgzip and AcceptEncoding.find("gzip") != -1:
            #self.logging("Debug", "Compressing - gzip")
            Response["Data"] = gzip.compress(Response["Data"])
            Response["Headers"]["Content-Encoding"] = "gzip"

    # Chunking, Follow the Domoticz Python Plugin Framework
    if self.pluginconf.pluginConf["enableChunk"] and len(Response["Data"]) > MAX_KB_TO_SEND:
        idx = 0
        HTTPchunk = {
            "Status": Response["Status"],
            "Chunk": True,
            "Headers": dict(Response["Headers"]),
            "Data": Response["Data"][0:MAX_KB_TO_SEND]
        }

        # Firs Chunk
        send_http_message( self, client_socket, prepare_http_response( self, HTTPchunk ))

        idx = MAX_KB_TO_SEND
        while idx != -1:
            tosend = {}
            tosend["Chunk"] = True
            if idx + MAX_KB_TO_SEND < len(Response["Data"]):
                # we have to sumbit one chunk and then continue
                tosend["Data"] = Response["Data"][idx : idx + MAX_KB_TO_SEND]
                idx += MAX_KB_TO_SEND
            else:
                # Last Chunk with Data
                tosend["Data"] = Response["Data"][idx:]
                idx = -1

            send_http_message( self, client_socket, prepare_http_response( self, tosend ))

        # Closing Chunk
        tosend = {}
        tosend["Chunk"] = True
        send_http_message( self, client_socket, prepare_http_response( self, tosend ))
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
    else:
        send_http_message( self, client_socket, prepare_http_response( self, Response ))
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            client_socket.close()
