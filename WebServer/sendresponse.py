#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz


try:
    import zlib
except Exception as Err:
    Domoticz.Error("zlib import error: '"+str(Err)+"'")
try:
    import gzip
except Exception as Err:
    Domoticz.Error("gzip import error: '"+str(Err)+"'")


from WebServer.tools import  DumpHTTPResponseToLog, MAX_KB_TO_SEND


def sendResponse( self, Connection, Response, AcceptEncoding=None ):

    if 'Data' not in Response:
        DumpHTTPResponseToLog( Response )
        Connection.Send( Response )
        if not self.pluginconf.pluginConf['enableKeepalive']:
            Connection.Disconnect()
        return

    if Response['Data'] is None:
        DumpHTTPResponseToLog( Response )
        Connection.Send( Response )
        if not self.pluginconf.pluginConf['enableKeepalive']:
            Connection.Disconnect()
        return

    self.logging( 'Debug', "Sending Response to : %s" %(Connection.Name))

    # Compression
    allowgzip = self.pluginconf.pluginConf['enableGzip']
    allowdeflate = self.pluginconf.pluginConf['enableDeflate']

    if (allowgzip or allowdeflate ) and 'Data' in Response and AcceptEncoding:
        self.logging( 'Debug', "sendResponse - Accept-Encoding: %s, Chunk: %s, Deflate: %s , Gzip: %s" %(AcceptEncoding, self.pluginconf.pluginConf['enableChunk'], allowdeflate, allowgzip))
        if len(Response["Data"]) > MAX_KB_TO_SEND:
            orig_size = len(Response["Data"])
            if allowdeflate and AcceptEncoding.find('deflate') != -1:
                self.logging( 'Debug', "Compressing - deflate")
                zlib_compress = zlib.compressobj( 9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 2)
                deflated = zlib_compress.compress(Response["Data"])
                deflated += zlib_compress.flush()
                Response["Headers"]['Content-Encoding'] = 'deflate'
                Response["Data"] = deflated

            elif allowgzip and AcceptEncoding.find('gzip') != -1:
                self.logging( 'Debug', "Compressing - gzip")
                Response["Data"] = gzip.compress( Response["Data"] )
                Response["Headers"]['Content-Encoding'] = 'gzip'

            self.logging( 'Debug', "Compression from %s to %s (%s %%)" %( orig_size, len(Response["Data"]), int(100-(len(Response["Data"])/orig_size)*100)))

    # Chunking, Follow the Domoticz Python Plugin Framework

    if self.pluginconf.pluginConf['enableChunk'] and len(Response['Data']) > MAX_KB_TO_SEND:
        idx = 0
        HTTPchunk = {}
        HTTPchunk['Status'] = Response['Status']
        HTTPchunk['Chunk'] = True
        HTTPchunk['Headers'] = {}
        HTTPchunk['Headers'] = dict(Response['Headers'])
        HTTPchunk['Data'] = Response['Data'][0:MAX_KB_TO_SEND]
        self.logging( 'Debug', "Sending: %s out of %s" %(idx, len((Response['Data']))))

        # Firs Chunk
        DumpHTTPResponseToLog( HTTPchunk )
        Connection.Send( HTTPchunk )

        idx = MAX_KB_TO_SEND
        while idx != -1:
            tosend={}
            tosend['Chunk'] = True
            if idx + MAX_KB_TO_SEND < len(Response['Data']):
                # we have to send one chunk and then continue
                tosend['Data'] = Response['Data'][idx:idx+MAX_KB_TO_SEND]        
                idx += MAX_KB_TO_SEND
            else:
                # Last Chunk with Data
                tosend['Data'] = Response['Data'][idx:]        
                idx = -1

            self.logging( 'Debug', "Sending Chunk: %s out of %s" %(idx, len((Response['Data']))))
            Connection.Send( tosend )

        # Closing Chunk
        tosend={}
        tosend['Chunk'] = True
        Connection.Send( tosend )
        if not self.pluginconf.pluginConf['enableKeepalive']:
            Connection.Disconnect()
    else:
        #Response['Headers']['Content-Length'] = len( Response['Data'] )
        DumpHTTPResponseToLog( Response )
        Connection.Send( Response )
        if not self.pluginconf.pluginConf['enableKeepalive']:
            Connection.Disconnect()



