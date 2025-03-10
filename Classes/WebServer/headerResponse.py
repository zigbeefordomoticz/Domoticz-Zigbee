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

    if not plugin_conf.get("enableCache", False):
        _response["Headers"].update({
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Accept": "*/*"
        })
    else:
        _response["Headers"]["Cache-Control"] = "private"

    return _response


def setupHeadersResponse(cookie=None):
    _response = {
        "Headers": {
            "Server": "Domoticz",
            "User-Agent": "Plugin-Zigbee4Domoticz/v1",
            "Access-Control-Allow-Headers": "Cache-Control, Pragma, Origin, Authorization, Content-Type, X-Requested-With",
            "Access-Control-Allow-Methods": "GET, POST, DELETE",
            "Access-Control-Allow-Origin": "*",
            "Referrer-Policy": "no-referrer"
        }
    }

    # Add cookie only if provided
    if cookie:
        _response["Headers"]["Cookie"] = cookie

    return _response
