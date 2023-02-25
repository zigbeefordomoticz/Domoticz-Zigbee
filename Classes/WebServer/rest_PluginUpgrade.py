

import json
import os  # nosec
import subprocess  # nosec

import z4d_certified_devices

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.database import import_local_device_conf

PLUGIN_UPGRADE_SCRIPT = "Tools/plugin-auto-upgrade.sh"

def rest_plugin_upgrade(self, verb, data, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    if verb != "GET" or len(parameters) != 0:
        return _response
    
    pluginFolder = self.pluginParameters["HomeFolder"]
    upgrade_script = pluginFolder + PLUGIN_UPGRADE_SCRIPT

    self.logging("Log", "Plugin Upgrade starting: %s" %(upgrade_script))
    
    process = subprocess.run( 
        upgrade_script ,
        cwd=self.pluginParameters["HomeFolder"],
        universal_newlines=True,
        text=True,
        capture_output=True,
        shell=True
    )
    result = {"result": str(process.stdout), "ReturnCode": process.returncode }
    
    self.logging("Debug", "Result: %s" %str(result))
    
    lines = {}
    lines = result["result"].split("\n")
    Logging_mode = "Log" if result["ReturnCode"] == 0 else "Error"
    for line in lines:
        self.logging( Logging_mode, "%s" %(line))

    _response["Data"] = json.dumps(result)
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
    
    import_local_device_conf(self)
    z4d_certified_devices_pathname = os.path.dirname( z4d_certified_devices.__file__ ) + "/"
    z4d_certified_devices.z4d_import_device_configuration(self, z4d_certified_devices_pathname )

def certified_devices_update(self):
    self.logging("Status", "Plugin looks to upgrade the Certified Device package")
    
    stream = os.popen( 'python3 -m pip install z4d-certified-devices --upgrade')
    output = stream.readlines()
    
    _reload_device_conf(self)

    for line in output:    
        self.logging( "Log", "%s" %(line))
        
    return output
  
   
def rest_certified_devices_update(self, verb, data, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    if verb != "GET" or len(parameters) != 0:
        return _response
    
    result = {"result": str(certified_devices_update(self))}
    _response["Data"] = json.dumps(result)
    return _response
