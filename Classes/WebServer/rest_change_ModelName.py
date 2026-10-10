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

from time import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.domoCreate import request_widget_creation
from Modules.domoTools import update_model_name


def rest_change_model_name(self, verb, data, parameters):

    # curl -X PUT -d '{
    #   "Model": "MWA1-TIC-historique-mono-base",
    #   "NWKID": "1234"
    # }' http://127.0.0.1:9441/rest-zigate/1/recreate-widgets

    _response = prepResponseMessage(self, setupHeadersResponse())
    self.logging("Log", "rest_change_model_name -->Verb: %s Data: %s Parameters: %s" % (verb, data, parameters))

    if verb != "PUT":
        return _response

    data = data.decode("utf8")
    data = eval(data)  # nosec B307
    self.logging( "Log", "rest_change_model_name - Data: %s" % data)

    if "Model" not in data and "NWKID" not in data:
        self.logging( "Error", "rest_change_model_name - unexpected parameter: %s" % data)
        _response["Data"] = {"unexpected parameter %s " % parameters}
        return _response

    nwkid = data["NWKID"]
    new_model = data["Model"]
    if nwkid not in self.ListOfDevices:
        self.logging( "Error", "rest_recreate_widgets - Unknown device %s " % nwkid)
        return _response
    old_model = self.ListOfDevices[ nwkid ]["Model"] if "Model" in self.ListOfDevices[ nwkid ] else ""
    _response["Data"] = {"NwkId %s set Model from: %s to %s, widgets will be re-created on the next heartbeat" % (nwkid, old_model, new_model)}

    update_model_name( self, nwkid, new_model )

    # Removing and re-creating the widgets are both Domoticz API calls, and this
    # runs in a WebServer client thread (Classes/WebServer/com.py: handle_client).
    # The Domoticz plugin API must only be used from the thread Domoticz calls the
    # plugin on, so the heartbeat does both (Modules/domoCreate.py).
    request_widget_creation(
        self, nwkid, "model changed from %s to %s from the WebUI" % (old_model, new_model),
        remove_existing_widgets=True)

    return _response