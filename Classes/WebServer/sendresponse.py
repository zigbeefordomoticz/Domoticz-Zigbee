#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import gzip
import zlib

from Classes.WebServer.tools import MAX_KB_TO_SEND, DumpHTTPResponseToLog

def sendResponse(self, Connection, Response, AcceptEncoding=None):

    if "Data" not in Response or Response["Data"] is None:
        DumpHTTPResponseToLog(Response)
        Connection.Send(Response)
        if not self.pluginconf.pluginConf["enableKeepalive"]:
            Connection.Disconnect()
        return

    self.logging("Debug", "Sending Response to : %s" % Connection.Name)

    # Compression
    allowgzip = self.pluginconf.pluginConf["enableGzip"]
    allowdeflate = self.pluginconf.pluginConf["enableDeflate"]

    if (allowgzip or allowdeflate) and "Data" in Response and AcceptEncoding:
        self.logging(
            "Debug",
            "sendResponse - Accept-Encoding: %s, Chunk: %s, Deflate: %s , Gzip: %s"
            % (AcceptEncoding, self.pluginconf.pluginConf["enableChunk"], allowdeflate, allowgzip),
        )
        if len(Response["Data"]) > MAX_KB_TO_SEND:
            orig_size = len(Response["Data"])
            if allowdeflate and "deflate" in AcceptEncoding:
                Response["Headers"]["Content-Encoding"] = "deflate"
                Response["Data"] = deflate_response_data(self, Response)
                
            elif allowgzip and "gzip" in AcceptEncoding:
                self.logging("Debug", "Compressing - gzip")
                Response["Data"] = gzip.compress(Response["Data"])
                Response["Headers"]["Content-Encoding"] = "gzip"

            self.logging(
                "Debug",
                "Compression from %s to %s (%s %%)"
                % (orig_size, len(Response["Data"]), int(100 - (len(Response["Data"]) / orig_size) * 100)),
            )

    # Chunking, Follow the Domoticz Python Plugin Framework
    if self.pluginconf.pluginConf["enableChunk"] and len(Response["Data"]) > MAX_KB_TO_SEND:
        chunk_size = MAX_KB_TO_SEND
        num_chunks = (len(Response["Data"]) + chunk_size - 1) // chunk_size
        for idx in range(num_chunks):
            start = idx * chunk_size
            end = min((idx + 1) * chunk_size, len(Response["Data"]))
            chunk_data = Response["Data"][start:end]

            tosend = {"Chunk": True, "Data": chunk_data}
            self.logging("Debug", "Sending Chunk: %s out of %s" % (idx + 1, num_chunks))
            Connection.Send(tosend)

        # Closing Chunk
        tosend = {"Chunk": True}
        Connection.Send(tosend)

    else:
        DumpHTTPResponseToLog(Response)
        Connection.Send(Response)
    if not self.pluginconf.pluginConf["enableKeepalive"]:
        Connection.Disconnect()


# TODO Rename this here and in `sendResponse`
def deflate_response_data(self, Response):
    self.logging("Debug", "Compressing - deflate")
    zlib_compress = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 2)
    deflated = zlib_compress.compress(Response["Data"])
    deflated += zlib_compress.flush()
 
    return deflated
