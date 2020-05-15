#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

def prepResponseMessage( self , _response ):


    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    _response["Data"] = {}
    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if not self.pluginconf.pluginConf['enableCache']:
        _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
        _response["Headers"]["Pragma"] = "no-cache"
        _response["Headers"]["Expires"] = "0"
        _response["Headers"]["Accept"] = "*/*"
    else:
        _response["Headers"]["Cache-Control"] = "private"

    return _response

def setupHeadersResponse( cookie = None ):
    
    _response = {}
    _response["Headers"] = {}
    _response["Headers"]["Server"] = "Domoticz"
    _response["Headers"]["User-Agent"] = "Plugin-Zigate/v1"

    _response["Headers"]['Access-Control-Allow-Headers'] = 'Cache-Control, Pragma, Origin, Authorization,   Content-Type, X-Requested-With'
    _response["Headers"]['Access-Control-Allow-Methods'] = 'GET, POST, DELETE'
    _response["Headers"]['Access-Control-Allow-Origin'] = '*'

    _response["Headers"]["Referrer-Policy"] = "no-referrer"

    if cookie:
        _response["Headers"]["Cookie"] = cookie

    #_response["Headers"]["Accept-Ranges"] = "bytes"
    # allow users of a web application to include images from any origin in their own conten
    # and all scripts only to a specific server that hosts trusted code.
    #_response["Headers"]["Content-Security-Policy"] = "default-src 'self'; img-src *"
    #_response["Headers"]["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval'"

    return _response