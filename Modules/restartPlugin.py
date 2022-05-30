#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import os
import urllib.parse 

import Domoticz

CURL_COMMAND = "/usr/bin/curl"


def restartPluginViaDomoticzJsonApi(self, stop=False, erasePDM=False, url_base_api="http://127.0.0.1:8080"):
    # sourcery skip: replace-interpolation-with-fstring

    if not os.path.isfile(CURL_COMMAND):
        Domoticz.Log("Unable to restart the plugin, %s not available" % CURL_COMMAND)
        return

    erasePDM = "True" if erasePDM else "False"
    enabled = "false" if stop else "true"

    #if webUserName and webPassword:
    #    url = "http://%s:%s@127.0.0.1:%s" % (self.WebUsername, self.WebPassword, self.pluginconf.pluginConf["port"])
    #else:
    #    url = "http://127.0.0.1:%s" % self.pluginconf.pluginConf["port"]

    url = url_base_api + "/json.htm?"
    
    url_infos = {
        "type": "command",
        "param": "updatehardware",
        "htype": "94", # Python Plugin Framework
        "idx": self.pluginParameters["HardwareID"],
        "name": self.pluginParameters["Name"],
        "address": self.pluginParameters["Address"],
        "port": self.pluginParameters["Port"],
        "serialport": self.pluginParameters["SerialPort"],
        "Mode1": self.pluginParameters["Mode1"],
        "Mode2": self.pluginParameters["Mode2"],
        "Mode3": erasePDM,
        "Mode4": self.pluginParameters["Mode4"],
        "Mode5": self.pluginParameters["Mode5"],
        "Mode6": self.pluginParameters["Mode6"],
        "extra": self.pluginParameters["Key"],
        "enabled": enabled,
        "datatimeout": "0",
    }

    if "LogLevel" in self.pluginParameters:
        url_infos["loglevel"] = self.pluginParameters["LogLevel"]

    Domoticz.Log("URL INFOS %s" %url_infos)
    url += urllib.parse.urlencode(url_infos, quote_via=urllib.parse.quote )
    
    Domoticz.Status("Plugin Restart command : %s" % url)

    _cmd = CURL_COMMAND + " '%s' &" % url
    os.system(_cmd)  # nosec