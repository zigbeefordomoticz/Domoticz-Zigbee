#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
from time import time

from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage

def rest_req_nwk_inter( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    if verb == 'GET':
        action = {'Name': 'Nwk-Interferences', 'TimeStamp': int(time())}
        _response["Data"] = json.dumps( action, sort_keys=True )

        if self.pluginparameters['Mode1'] != 'None' and self.networkenergy:
            self.networkenergy.start_scan()

    return _response

def rest_req_nwk_full( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    
    if verb == 'GET':
        action = {'Name': 'Nwk-Energy-Full', 'TimeStamp': int(time())}
        _response["Data"] = json.dumps( action, sort_keys=True )

        if self.pluginparameters['Mode1'] != 'None' and self.networkenergy:
            self.networkenergy.start_scan( root='0000', target='0000')

    return _response