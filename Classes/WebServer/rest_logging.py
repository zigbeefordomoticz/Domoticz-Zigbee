


import json
import os

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)


def rest_logErrorHistory(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if verb == "GET" and self.log.LogErrorHistory:
            try:
                _response["Data"] = json.dumps(self.log.LogErrorHistory, sort_keys=False)
                self.log.reset_new_error()
            except Exception as e:
                domoticz_error_api("rest_logErrorHistory - Exception %s while saving: %s" % (e, str(self.log.LogErrorHistory)))
    return _response

def rest_logErrorHistoryClear(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if verb == "GET":
        self.logging("Status", "Erase Log History")
        self.log.loggingClearErrorHistory()
    return _response

def rest_logPlugin(self, verb, data, parameters):
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if not self.pluginconf.pluginConf["enablePluginLogging"]:
        # No log file
        self.logging("Log", "rest_logPlugin: Plugin Logging not enabled !!")
        return _response

    if verb != "GET":
        self.logging("Error", "rest_logPlugin: Expect a GET request !!")
        return _response
    
    LOG_FILE = "/PluginZigbee_"
    logfilename = LOG_FILE + "%02d" % self.hardwareID + ".log"
    full_logfilename = self.pluginconf.pluginConf["pluginLogs"] + logfilename
    
    _response["Data"] = json.dumps({ 
        'Filename': LOG_FILE + "%02d" % self.hardwareID + ".log",
        'Size': os.path.getsize( full_logfilename ) ,
        'URL': '/download' + full_logfilename
    })
    
    self.logging("Debug", "rest_logPlugin: %s" %(_response["Data"]))

    return _response
