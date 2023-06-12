#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
from time import time

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.domoCreate import (CreateDomoDevice,
                                over_write_type_from_deviceconf)
from Modules.domoTools import remove_all_widgets, update_model_name


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
    data = eval(data)
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
    _response["Data"] = {"NwkId %s set Model from: %s to %s" % (nwkid, old_model, new_model)}

    update_model_name( self, nwkid, new_model )
    remove_all_widgets( self, self.Devices, nwkid)
    over_write_type_from_deviceconf( self, self.Devices, nwkid)
    self.ListOfDevices[nwkid]["Status"] = "CreateDB"
    CreateDomoDevice(self, self.Devices, nwkid)

    return _response