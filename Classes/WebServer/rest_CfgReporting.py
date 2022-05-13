#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import json

import Domoticz
from Classes.WebServer.headerResponse import prepResponseMessage, setupHeadersResponse
from Modules.zigateConsts import ZCL_CLUSTERS_ACT


def rest_cfgrpt_ondemand(self, verb, data, parameters):
    # Trigger a Cfg Reporting on a specific Device

    _response = prepResponseMessage(self, setupHeadersResponse())
    if self.configureReporting is None or verb != "GET" or len(parameters) != 1:
        self.logging("Debug", f"rest_cfgrpt_ondemand incorrect request {verb} {data} {parameters}")
        return _response

    if parameters[0] not in self.ListOfDevices:
        self.logging("Debug", "rest_cfgrpt_ondemand requested on %s doesn't exist" % parameters[0])
        return _response

    self.configureReporting.cfg_reporting_on_demand( parameters[0] )
    self.logging("Debug", f"rest_cfgrpt_ondemand requested on {parameters[0]}")

    _response["Data"] = json.dumps({"status": "Configure Reporting requested"}, )
    return _response