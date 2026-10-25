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

def prepResponseMessage(self, _response):
    plugin_conf = self.pluginconf.pluginConf  # Cache the config reference

    # Default headers
    _response["Headers"].update({
        "Connection": "Keep-alive" if plugin_conf.get("enableKeepalive", False) else "Close",
        "Content-Type": "application/json; charset=utf-8"
    })

    _response["Data"] = {}
    _response["Status"] = "200 OK"

    # REST answers reflect live state: never cached, whatever enableCache says (it is for the WebUI files)
    _response["Headers"].update({
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    })

    return _response


def setupHeadersResponse():
    _response = {
        "Headers": {
            # No Access-Control-Allow-*: the WebUI calls the REST API from its own origin, and no other
            # web page should be able to read the answers (device list, settings, paths)
            "Server": "Domoticz",
            "Referrer-Policy": "no-referrer"
        }
    }

    return _response
