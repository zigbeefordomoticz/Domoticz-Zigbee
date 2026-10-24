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

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)


# Violations of the WebUI Content-Security-Policy, POSTed by the browser to the report-uri of WEBUI_CSP.
# Each distinct violation is logged once per plugin run, and only the first MAX_CSP_REPORTS of them: a screen
# in a loop, or a web page posting junk to this URL, cannot flood the plugin log.
CSP_REPORT_FIELDS = ("document-uri", "violated-directive", "effective-directive", "blocked-uri",
                     "source-file", "line-number", "script-sample")
MAX_CSP_REPORTS = 50
MAX_CSP_FIELD = 200


def rest_csp_report(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Status"] = "204 No Content"
    _response["Data"] = None

    seen = getattr(self, "csp_reports_seen", None)
    if seen is None:
        seen = self.csp_reports_seen = set()
    if verb != "POST" or len(seen) >= MAX_CSP_REPORTS:
        return _response

    try:
        report = json.loads(data)["csp-report"]
        fields = {key: str(report.get(key, ""))[:MAX_CSP_FIELD] for key in CSP_REPORT_FIELDS}
    except (ValueError, TypeError, KeyError, AttributeError):
        return _response

    directive = fields["effective-directive"] or fields["violated-directive"]
    violation = (directive, fields["blocked-uri"], fields["source-file"], fields["line-number"])
    if violation in seen:
        return _response
    seen.add(violation)

    message = f"WebUI Content-Security-Policy would block '{fields['blocked-uri']}' ({directive}) on {fields['document-uri']}"
    if fields["source-file"]:
        message += f" from {fields['source-file']}:{fields['line-number']}"
    if fields["script-sample"]:
        message += f" sample: {fields['script-sample']}"
    self.logging("Log", message)
    return _response


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
