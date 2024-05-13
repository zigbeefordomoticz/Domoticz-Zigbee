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
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)


def rest_device_settings_help(self, verb, data, parameters):
    self.logging("Debug", "rest_device_settings_help")
    _response = prepResponseMessage(self, setupHeadersResponse())
    if verb == "GET":
        list_of_settings = []
        for setting, setting_info in self.device_settings.items():
            self.logging("Debug", "rest_device_settings_help %s %s" %(setting, str(setting_info)))
            if not callable(setting_info) and setting not in list_of_settings:
                self.logging("Debug", "rest_device_settings_help %s %s" %(setting, str(setting_info)))
                list_of_settings.append( ( setting, setting_info[ "description"]))
            else:
                list_of_settings.append( ( setting, ""))
            
        _response["Data"] = json.dumps(list_of_settings, sort_keys=True)

    return _response
