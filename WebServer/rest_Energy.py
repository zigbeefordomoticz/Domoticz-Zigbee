#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
from time import time

from WebServer.headerResponse import setupHeadersResponse

def rest_req_nwk_inter( self, verb, data, parameters):

    _response = setupHeadersResponse()
    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    if not self.pluginconf.pluginConf['enableCache']:
        _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
        _response["Headers"]["Pragma"] = "no-cache"
        _response["Headers"]["Expires"] = "0"
        _response["Headers"]["Accept"] = "*/*"

    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if verb == 'GET':
        action = {'Name': 'Nwk-Interferences', 'TimeStamp': int(time())}
        _response["Data"] = json.dumps( action, sort_keys=True )

        if self.pluginparameters['Mode1'] != 'None' and self.networkenergy:
            self.networkenergy.start_scan()

    return _response

def rest_req_nwk_full( self, verb, data, parameters):

    _response = setupHeadersResponse()
    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    if not self.pluginconf.pluginConf['enableCache']:
        _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
        _response["Headers"]["Pragma"] = "no-cache"
        _response["Headers"]["Expires"] = "0"
        _response["Headers"]["Accept"] = "*/*"

    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if verb == 'GET':
        action = {'Name': 'Nwk-Energy-Full', 'TimeStamp': int(time())}
        _response["Data"] = json.dumps( action, sort_keys=True )

        if self.pluginparameters['Mode1'] != 'None' and self.networkenergy:
            self.networkenergy.start_scan( root='0000', target='0000')

    return _response