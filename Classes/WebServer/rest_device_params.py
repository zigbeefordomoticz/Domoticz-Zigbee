#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import json
from time import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.paramDevice import sanity_check_of_param


def rest_device_param(self, verb, data, parameters):

    self.logging("Log", "rest_update_device_param -->Verb: %s Data: %s Parameters: %s" % (verb, data, parameters))
    if verb == "GET":
        return rest_get_device_param(self, parameters)

    elif verb == "PUT":
        return rest_update_device_param(self, data)

    return prepResponseMessage(self, setupHeadersResponse())


def rest_get_device_param( self, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())

    if len(parameters) != 1:
        return _log_and_return_with_error(self, "rest_get_device_param - unexpected parameter: %s", parameters, "unexpected parameter %s ", _response, )

    nwkid = parameters[0]
    if len(nwkid) == 16:
        # We are assuming that is an ieee instead of nwkid
        nwkid = self.IEEE2NWK.get( nwkid )

    if nwkid not in self.ListOfDevices:
        return _log_and_return_with_error(self, "rest_get_device_param - Unknown device %s ", nwkid, "unknown device %s ", _response, )
    device_info = self.ListOfDevices.get( nwkid )
    device_param = device_info.get("Param", "{}")

    _response["Data"] = json.dumps(device_param, sort_keys=False)
    return _response


def rest_update_device_param(self, data):

    # curl -X PUT -d '{
    #   "Param": {'Disabled': 0, 'resetMotiondelay': 0, 'ConfigurationReportChunk': 3, 'ReadAttributeChunk': 4},
    #   "NWKID": "1234"
    # }' http://127.0.0.1:9441/rest-z4d/1/device-param

    _response = prepResponseMessage(self, setupHeadersResponse())

    data = data.decode("utf8")
    data = eval(data)
    self.logging( "Log", "rest_update_device_param - Data: %s" % data)

    parameter = data.get("Param")
    nwkid = data.get("NWKID")
    ieee = data.get("IEEE")

    if nwkid is None and ieee is None:
        return _log_and_return_with_error(self, "rest_update_device_param - missing IEEE or NWKID", "unexpected parameter %s ", _response, )

    if ieee:
        nwkid = self.IEEE2NWK.get( ieee )

    if parameter is None or nwkid is None:
        return _log_and_return_with_error(self, "rest_update_device_param - unexpected parameter: %s", data, "unexpected parameter %s ", _response, )
    if nwkid not in self.ListOfDevices:
        return _log_and_return_with_error(self, "rest_update_device_param - Unknown device %s ", nwkid, "unknown device %s ", _response, )
    old_parameter = self.ListOfDevices[ nwkid ].get("Param")
    _response["Data"] = {"NwkId %s set Param from: %s to %s" % (nwkid, old_parameter, parameter)}

    self.ListOfDevices[ nwkid ]["Param"] = parameter

    sanity_check_of_param(self, nwkid)

    return _response


def _log_and_return_with_error(self, arg0, arg1, arg2, _response):
    self.logging("Error", arg0 % arg1)
    _response["Data"] = {arg2 % arg1}
    return _response
