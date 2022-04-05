#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import os

import Domoticz

CURL_COMMAND = "/usr/bin/curl"


def restartPluginViaDomoticzJsonApi(self, stop=False):

    if not os.path.isfile(CURL_COMMAND):
        Domoticz.Log("Unable to restart the plugin, %s not available" % CURL_COMMAND)
        return

    
    if stop:
        enabled="false"
    else:
        enabled="true"
    
    if self.WebUsername and self.WebPassword:
        url = "http://%s:%s@127.0.0.1:%s" % (self.WebUsername, self.WebPassword, self.pluginconf.pluginConf["port"])
    else:
        url = "http://127.0.0.1:%s" % self.pluginconf.pluginConf["port"]

    url += "/json.htm?type=command&param=updatehardware&htype=94"
    url += "&idx=%s" % self.pluginParameters["HardwareID"]
    url += "&name=%s" % self.pluginParameters["Name"].replace(" ", "%20")
    url += "&address=%s" % self.pluginParameters["Address"]
    url += "&port=%s" % self.pluginParameters["Port"]
    url += "&serialport=%s" % self.pluginParameters["SerialPort"]
    url += "&Mode1=%s" % self.pluginParameters["Mode1"]
    url += "&Mode2=%s" % self.pluginParameters["Mode2"]
    url += "&Mode3=%s" % self.pluginParameters["Mode3"]
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
