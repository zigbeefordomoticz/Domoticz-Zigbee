#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import os
import subprocess  # nosec

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

    url = url_base_api
    url += "/json.htm?type=command&param=updatehardware&htype=94"
    url += "&idx=%s" % self.pluginParameters["HardwareID"]
    url += "&name=%s" % self.pluginParameters["Name"].replace(" ", "%20")
    url += "&address=%s" % self.pluginParameters["Address"]
    url += "&port=%s" % self.pluginParameters["Port"]
    url += "&serialport=%s" % self.pluginParameters["SerialPort"]
    url += "&Mode1=%s" % self.pluginParameters["Mode1"]
    url += "&Mode2=%s" % self.pluginParameters["Mode2"]
    url += "&Mode3=%s" % erasePDM
    url += "&Mode4=%s" % self.pluginParameters["Mode4"]
    url += "&Mode5=%s" % self.pluginParameters["Mode5"]
    url += "&Mode6=%s" % self.pluginParameters["Mode6"]
    url += "&extra=%s" % self.pluginParameters["Key"]
    url += "&enabled=%s" % enabled
    url += "&datatimeout=0"
    if "LogLevel" in self.pluginParameters:
        url += "&loglevel=%s" % self.pluginParameters["LogLevel"]

    Domoticz.Status("Plugin Restart command : %s" % url)

    _cmd = CURL_COMMAND + " '%s' &" % url
    os.system(_cmd)  # nosec
   
    #process = subprocess.run( _cmd ,
    #                        cwd= self.pluginParameters["HomeFolder"],
    #                        universal_newlines=True,
    #                        text=True,
    #                        capture_output=False,
    #                        shell=True)
