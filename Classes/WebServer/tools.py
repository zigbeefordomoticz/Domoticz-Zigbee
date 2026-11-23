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
import re

from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)

MAX_BLOCK_SIZE = 8 * 1024  # Chunk size
DEBUG_HTTP = False

# Request headers carrying credentials, e.g. the Domoticz session cookie (DMZSID)
# that the browser also sends to the WebUI port. Never written to the plugin log.
SENSITIVE_HEADERS = {"cookie", "authorization", "proxy-authorization"}
SENSITIVE_HEADER_LINE = re.compile(r"^(Cookie|Authorization|Proxy-Authorization)([ \t]*:)[^\r\n]*", re.IGNORECASE | re.MULTILINE)


def keepConnectionAlive(self):
    self.heartbeats += 1


def DumpHTTPResponseToLog(httpDict):

    if not DEBUG_HTTP:
        return
    if isinstance(httpDict, dict):
        domoticz_log_api("HTTP Details (" + str(len(httpDict)) + "):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                domoticz_log_api("--->'" + x + " (" + str(len(httpDict[x])) + "):")
                for y in httpDict[x]:
                    domoticz_log_api("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                if x == "Data":
                    domoticz_log_api("--->'%s':'%.40s'" % (x, str(httpDict[x])))
                else:
                    domoticz_log_api("--->'" + x + "':'" + str(httpDict[x]) + "'")


def redact_headers(headers):
    """Return a copy of the request headers that is safe to log."""
    return {name: "<redacted>" if name.lower() in SENSITIVE_HEADERS else value for name, value in headers.items()}


def redact_raw_request(raw_request):
    """Return the raw request text with the credential headers redacted, safe to log."""
    return SENSITIVE_HEADER_LINE.sub(r"\1\2 <redacted>", raw_request)


def parse_json_object(body):
    """Decode a REST request body that must be a JSON object.

    Return the dict, or None when the body is not UTF-8 JSON or is not an object.
    The body is only ever parsed as data, never evaluated.
    """
    if isinstance(body, (bytes, bytearray)):
        try:
            body = body.decode("utf8")
        except UnicodeDecodeError:
            return None
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def request_json_object(self, body, route):
    """parse_json_object() for a route handler: log an Error REST0001 when the body is refused."""
    value = parse_json_object(body)
    if value is None and self.log:
        context = {"Error code": "REST0001", "Route": route}
        self.log.logging("WebServer", "Error", "%s - request body is not a JSON object, request refused" % route, None, context)
    return value
