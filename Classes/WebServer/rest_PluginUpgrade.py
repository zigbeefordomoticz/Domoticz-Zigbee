

import json
import subprocess  # nosec

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)

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
