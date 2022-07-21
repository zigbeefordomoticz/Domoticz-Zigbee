

import json
import subprocess  # nosec

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)

PLUGIN_UPGRADE_SCRIPT = "Tools/plugin-auto-upgrade.sh"

def rest_plugin_upgrade(self, verb, data, parameters):
    
    pluginFolder = self.pluginParameters["HomeFolder"]
    upgrade_script = pluginFolder + PLUGIN_UPGRADE_SCRIPT
    result = {}
    _response = prepResponseMessage(self, setupHeadersResponse())
    if verb == "GET" and len(parameters) == 0:
        self.logging("Log", "Plugin Upgrade starting: %s" %(upgrade_script))
        process = subprocess.run( upgrade_script ,
                                 cwd= self.pluginParameters["HomeFolder"],
                                universal_newlines=True,
                                text=True,
                                capture_output=True,
                                shell=True)
        result = {"result": str(process.stdout), "ReturnCode": process.returncode }
    _response["Data"] = json.dumps(result)
    lines = {}
    lines = result["result"].split("\n")
    for line in lines:
        self.logging("Log", "%s" %(line))
    self.logging("Log", "Plugin Upgrade return code: %s" %(result["ReturnCode"]))

    return _response
