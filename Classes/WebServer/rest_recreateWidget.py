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


def rest_recreate_widgets(self, verb, data, parameters):

    # curl -X PUT -d '{"IEEE":"00158d0005bea6da"}' http://127.0.0.1:9441/rest-zigate/1/recreate-widgets

    _response = prepResponseMessage(self, setupHeadersResponse())

    Domoticz.Log("rest_recreate_widgets -->Verb: %s Data: %s Parameters: %s" % (verb, data, parameters))

    if verb != "PUT":
        return _response

    data = data.decode("utf8")
    data = eval(data)
    self.logging("Log", "rest_recreate_widgets - Data: %s" % data)

    if "IEEE" not in data and "NWKID" not in data:
        Domoticz.Error("rest_recreate_widgets - unexpected parameter %s " % parameters)
        _response["Data"] = {"unexpected parameter %s " % parameters}
        return _response

    if "IEEE" in data:
        key = data["IEEE"]
        if key not in self.IEEE2NWK:
            Domoticz.Error("rest_recreate_widgets - Unknown device %s " % key)
            return _response
        nwkid = self.IEEE2NWK[key]
        _response["Data"] = {"IEEE %s set to Provisioning Requested at %s" % (key, int(time()))}
    else:
        nwkid = data["NWKID"]
        if nwkid not in self.ListOfDevices:
            Domoticz.Error("rest_recreate_widgets - Unknown device %s " % nwkid)
            return _response
        _response["Data"] = {"NwkId %s set to Provisioning Requested at %s" % (nwkid, int(time()))}

    over_write_type_from_deviceconf( self, self.Devices, nwkid)
    self.ListOfDevices[nwkid]["Status"] = "CreateDB"
    CreateDomoDevice(self, self.Devices, nwkid)

    return _response