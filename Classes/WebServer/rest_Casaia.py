#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
import Domoticz
import json


from Modules.casaia import DEVICE_ID
from Classes.WebServer.headerResponse import setupHeadersResponse, prepResponseMessage
from time import time


def rest_casa_device_list(self, verb, data, parameters):  # Ok 10/11/2020

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    _response["Data"] = list_casaia_ac201(self)

    if verb == "GET" and len(parameters) == 0:
        if len(self.zigatedata) == 0:
            _response["Data"] = json.dumps(fake_list_casaia_ac201(), sort_keys=True)
            return _response

        _response["Data"] = json.dumps(list_casaia_ac201(self), sort_keys=True)

    return _response


def fake_list_casaia_ac201():
    Domoticz.Log("fake_list_casaia_ac201")

    return [
        {"NwkId": "aef3", "IEEE": "3c6a2cfffed012345", "Model": "AC201A", "Name": "Clim Bureau", "IRCode": "1234"},
        {"NwkId": "531a", "IEEE": "12345cfffed012345", "Model": "AC201A", "Name": "Clim Salon", "IRCode": "0000"},
        {"NwkId": "47ab", "IEEE": "3c6a2cfffbbb12345", "Model": "AC201A", "Name": "Clim Cave", "IRCode": "461"},
        {"NwkId": "2755", "IEEE": "3c6a2caaaed012345", "Model": "AC201A", "Name": "Clim Extérieur", "IRCode": "000"},
    ]


def rest_casa_device_ircode_update(self, verb, data, parameters):
    # wget --method=PUT --body-data='[
    # {
    # 	"NwkId": "0a90",
    # 	"IRCode": "1234",
    # },
    # {
    # ....
    # ]
    # ' http://127.0.0.1:9440/rest-zigate/1/ota-firmware-update

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    if verb != "PUT":
        # Only Put command with a Valid JSON is allow
        return _response

    if data is None:
        return _response

    if len(parameters) != 0:
        return _response

    # We receive a JSON with a list of NwkId to be scaned
    data = data.decode("utf8")

    self.logging("Debug", "rest_casa_device_ircode_update - Data received  %s " % (data))

    data = json.loads(data)
    self.logging("Debug", "rest_casa_device_ircode_update - List of Device IRCode  %s " % (data))

    status = 0
    for x in data:
        if "NwkId" not in x and "IRCode" not in x:
            status = 1
            continue

        if x["NwkId"] in self.ListOfDevices and "CASA.IA" in self.ListOfDevices[x["NwkId"]]:
            Domoticz.Log("Updating : %s with %s" % (x["NwkId"], x["IRCode"]))
            if self.ListOfDevices[x["NwkId"]] and "Model" in self.ListOfDevices[x["NwkId"]]:
                self.ListOfDevices[x["NwkId"]]["CASA.IA"][DEVICE_ID]["IRCode"] = x["IRCode"]

    action = {" Name": "IRCode update performed status: %s" % status, "TimeStamp": int(time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def list_casaia_ac201(self):
    # Return a list of ac201 devices

    self.log.logging("CasaIA", "Debug", "list_casaia_ac201")

    _casaiaDeviceList = []
    for x in self.ListOfDevices:
        if (
            "CASA.IA" in self.ListOfDevices[x]
            and "Model" in self.ListOfDevices[x]
            and self.ListOfDevices[x]["Model"] in ("AC201A", "AC211", "AC221")
        ):
            irCode = "0000"
            if "IRCode" in self.ListOfDevices[x]["CASA.IA"][DEVICE_ID]:
                irCode = self.ListOfDevices[x]["CASA.IA"][DEVICE_ID]["IRCode"]
            zName = ""
            if "ZDeviceName" in self.ListOfDevices[x]:
                zName = self.ListOfDevices[x]["ZDeviceName"]

            _device = {
                "NwkId": x,
                "IEEE": self.ListOfDevices[x]["IEEE"],
                "Model": self.ListOfDevices[x]["Model"],
                "Name": zName,
                "IRCode": irCode,
            }

            self.log.logging("CasaIA", "Debug", "list_casaia_ac201 adding %s" % x)
            _casaiaDeviceList.append(_device)
    return _casaiaDeviceList
