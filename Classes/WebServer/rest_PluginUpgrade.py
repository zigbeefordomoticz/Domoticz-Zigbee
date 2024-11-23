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
import os
import subprocess  # nosec
from pathlib import Path

import distro
import z4d_certified_devices

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.database import import_local_device_conf
from Modules.matomo_request import matomo_plugin_update


PLUGIN_UPGRADE_SCRIPT = "Tools/plugin-auto-upgrade.sh"

def rest_plugin_upgrade(self, verb, data, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    if verb != "GET" or len(parameters) != 0:
        return _response
    
    pluginFolder = Path(self.pluginParameters["HomeFolder"])
    upgrade_script = str( pluginFolder / PLUGIN_UPGRADE_SCRIPT)

    self.logging("Log", "Plugin Upgrade starting: %s" %(upgrade_script))
    
    process = subprocess.run( 
        upgrade_script ,
        cwd=self.pluginParameters["HomeFolder"],
        universal_newlines=True,
        text=True,
        capture_output=True,
        shell=True,
        errors='backslashreplace'
    )
    result = {"result": str(process.stdout), "ReturnCode": process.returncode }
    
    self.logging("Debug", "Result: %s" %str(result))
    
    lines = {}
    lines = result["result"].split("\n")
    Logging_mode = "Log" if result["ReturnCode"] == 0 else "Error"
    for line in lines:
        self.logging( Logging_mode, "%s" %(line))

    _response["Data"] = json.dumps(result)
    
    if self.pluginconf.pluginConf["MatomoOptIn"]:
        matomo_plugin_update(self, Logging_mode != "Error")
    
    return _response

def rest_reload_device_conf(self, verb, data, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if verb != "GET":
        return _response
    _reload_device_conf(self)
    _response["Data"] = {"Certified Configuration loaded"}
    return _response

def _reload_device_conf(self):
    
    self.DeviceConf = {}
    self.ModelManufMapping = {}
    import_local_device_conf(self)
    z4d_certified_devices_pathname = os.path.dirname( z4d_certified_devices.__file__ ) + "/"
    z4d_certified_devices.z4d_import_device_configuration(self, z4d_certified_devices_pathname )

def certified_devices_update(self):
    
    if not self.pluginconf.pluginConf["internetAccess"]:
        # No Internet, or Internet disabled
        self.logging( "Error", "Internet access is disable !!!")
        return { "result": "Internet access disabled !!!", "ReturnCode": -1}

    if distro.id() in ("debian", "raspbian") and distro.version() >= '12':
        CERTIFIED_DEVICES_UPGRADE_CMD = "python3 -m pip install z4d-certified-devices --upgrade --break-system-packages"
    else:
        CERTIFIED_DEVICES_UPGRADE_CMD = "python3 -m pip install z4d-certified-devices --upgrade"

    self.logging("Status", "Plugin looks to upgrade the Certified Device package")
    
    process = subprocess.run( 
        CERTIFIED_DEVICES_UPGRADE_CMD ,
        cwd=self.pluginParameters["HomeFolder"],
        universal_newlines=True,
        text=True,
        capture_output=True,
        shell=True,
        errors='backslashreplace'
    )
    result = {"result": str(process.stdout), "ReturnCode": process.returncode }
    Logging_mode = "Log" if result["ReturnCode"] == 0 else "Error"
    
    #_reload_device_conf(self)
    self.logging(Logging_mode, "Certified Device package upgrade results")
    for line in result["result"].split("\n"):    
        self.logging( Logging_mode, "%s" %(line))
        
    return result
  
   
def rest_certified_devices_update(self, verb, data, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    if verb != "GET" or len(parameters) != 0:
        return _response
    
    result = {"result": str(certified_devices_update(self))}
    _response["Data"] = json.dumps(result)
    return _response
