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

import mimetypes
import os
import os.path
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from time import gmtime, strftime
from urllib.parse import urlparse

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Classes.WebServer.tools import DumpHTTPResponseToLog, redact_headers
from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)

# The WebUI build names its bundles after their content: main.0eca488920832a0f.js (webpack),
# main-5NFAGTK3.js (esbuild). A new release brings new names, so these can be cached for good.
HASHED_FILENAME = re.compile(r"\.[0-9a-f]{16,}\.\w+$|-[0-9A-Z]{8}\.\w+$")
CACHE_IMMUTABLE = "public, max-age=31536000, immutable"
CACHE_REVALIDATE = "no-cache"
CACHE_NO_STORE = "no-cache, no-store, must-revalidate"

# Content-Security-Policy of the WebUI page, sent as Report-Only: the browser lists what it would block in its
# console and blocks nothing. Switch to Content-Security-Policy once every screen has run clean.
# - the hash is the inline onload="this.media='all'" Angular writes in index.html (critical CSS)
# - Angular component styles and the charts use inline styles
# - no frame-ancestors: the Domoticz custom menu frames the WebUI from the Domoticz host and port
WEBUI_CSP = "; ".join((
    "default-src 'self'",
    "script-src 'self' 'unsafe-hashes' 'sha256-MhtPZXr7+LpJUY5qtMutB+qWfQtMaPccfe7QXtCcEYc='",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
))


def measure_execution_time(func):
    def wrapper(self, Connection, Data):
        t_start = None
        if self.pluginconf.pluginConf.get("WebUIReactTime", False):
            t_start = int(1000 * time.time())

        try:
            func(self, Connection, Data)

        finally:
            if t_start:
                t_end = int(1000 * time.time())
                t_elapse = t_end - t_start
                self.statistics.add_rxTiming(t_elapse)  
                _verb = Data['Verb'] if 'Verb' in Data else None
                _url = Data['URL'] if 'URL' in Data else None
                self.logging( "Log", f"| (onMessage WebUI) | {t_elapse} | {_verb} | {_url}")
    return wrapper


@measure_execution_time
def onMessage(self, Connection, Data):
    self.logging("Debug", f"WebServer onMessage: {dict(Data, Headers=redact_headers(Data.get('Headers') or {}))}")

    headerCode = check_header(Data)
    self.logging("Debug", f"onMessage - headerCode: {headerCode}")

    if headerCode != "200 OK":
        self.sendResponse(Connection, {"Status": headerCode})
        return

    url, parsed_url, parsed_query = parse_and_decode_query(Data)
    Data.setdefault("Data", None)

    if handle_rest_api(self, Connection, Data, parsed_query):
        return

    download = is_download( parsed_query, parsed_url)
    self.logging("Debug", f"Download: {download}")
    if download:
        # Only the plugin log files can be downloaded (rest_logPlugin hands out /download/<pluginLogs>/<file>)
        webFilename = get_download_filename(self, parsed_url)
        if webFilename is None:
            # Refused, and answered as any wrong or missing file: with the WebUI index.html
            self.logging("Log", f"WebUI - refused {url}: not a plugin log file")
            webFilename = redirect_to_index_html(self)

    else:
        # Most likely a file from the wwww/ to be served
        webFilename = get_web_filename(self, parsed_url)
        if webFilename is None:
            # Refused, and answered as any wrong or missing file: with the WebUI index.html
            self.logging("Log", f"WebUI - refused {url}: outside of www/")
            webFilename = redirect_to_index_html(self)

    self.logging("Debug", f"Downloading: {webFilename}")

    if not os.path.isfile(webFilename):
        self.logging("Debug", "Redirect to index.html")
        webFilename = redirect_to_index_html(self)

    response_headers = prepare_response_headers(self, webFilename, download)
    _response = setupHeadersResponse()
    _response["Headers"].update(response_headers)

    self.logging("Debug", f"Opening: {webFilename}")

    _last_modified = get_last_modified(webFilename)

    if get_from_cache_or_send(self, Connection, webFilename, Data, _last_modified, _response):
        return

    send_file(self, Connection, webFilename, Data, _last_modified, _response)

def handle_rest_api(self, Connection, Data, parsed_query):
    if len(parsed_query) < 3 or parsed_query[0] not in ["rest-z4d","rest-zigate",]:
        return False
    api_version = parsed_query[1]
    verb = Data.get("Verb")
    command = parsed_query[2]
    params = parsed_query[3:]
    self.logging("Debug", f"Receiving a REST API - Version: {api_version}, Verb: {verb}, Command: {command}, Params: {params}")

    if parsed_query[0] in ["rest-z4d", "rest-zigate"] and api_version == "1":
        self.do_rest(Connection, verb, Data.get("Data"), api_version, command, params)
    else:
        domoticz_error_api(f"Unknown API {parsed_query}")
        self.sendResponse(Connection, {"Status": "400 Bad Request"})
    return True


def is_download( parsed_query, parsed_url):
    return parsed_query[0] == 'download'


def get_download_filename(self, parsed_url):
    """Map /download/<absolute path> onto a file under the plugin log directory, or None."""
    log_root = self.pluginconf.pluginConf.get("pluginLogs")
    if not log_root:
        return None
    log_root = os.path.normpath(os.path.abspath(log_root))
    downloadFilename = os.path.normpath(parsed_url.path[len('/download'):])
    if not os.path.isabs(downloadFilename):
        return None
    try:
        if os.path.commonpath([log_root, downloadFilename]) != log_root:
            return None
    except ValueError:
        # Not on the same drive (Windows)
        return None
    return downloadFilename


def get_web_filename(self, parsed_url):
    """Map the URL path onto a file under www/, or None when it would leave www/ (e.g. '/../')."""
    www_root = os.path.normpath(os.path.join(self.homedirectory, "www"))
    webFilename = os.path.normpath(os.path.join(www_root, parsed_url.path.lstrip("/")))
    self.logging("Debug", f"webFilename: {webFilename}")
    if os.path.commonpath([www_root, webFilename]) != www_root:
        return None
    return webFilename


def redirect_to_index_html(self):
    _homedir = Path(self.homedirectory)
    webFilename = _homedir / "www/z4d/index.html"
    self.logging("Debug", "Redirecting to /z4d/index.html")
    return webFilename


def cache_control_for(self, webFilename, download):
    if download or not self.pluginconf.pluginConf["enableCache"]:
        return CACHE_NO_STORE
    if HASHED_FILENAME.search(os.path.basename(webFilename)):
        return CACHE_IMMUTABLE
    # index.html and the unhashed assets: kept, but checked (If-Modified-Since -> 304) on every use,
    # so that a plugin upgrade is picked up on the next page load
    return CACHE_REVALIDATE


def prepare_response_headers(self, webFilename, download=False):
    cache_control = cache_control_for(self, webFilename, download)
    return {
        "Connection": (
            "Keep-alive"
            if self.pluginconf.pluginConf["enableKeepalive"]
            else "Close"
        ),
        "Cache-Control": cache_control,
        "Pragma": "no-cache" if cache_control == CACHE_NO_STORE else "",
        "Expires": "0" if cache_control == CACHE_NO_STORE else "",
        "Content-Security-Policy-Report-Only": WEBUI_CSP if str(webFilename).endswith(".html") else "",
    }


def get_last_modified(webFilename):
    current_version_on_server = os.path.getmtime(webFilename)
    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(current_version_on_server))


def get_from_cache_or_send(self, Connection, webFilename, Data, _last_modified, _response):
    return bool(
        get_from_cache_if_available(
            self, Connection, webFilename, Data, _last_modified, _response
        )
    )


def parse_and_decode_query( Data ):
    url = Data["URL"]
    parsed_url = urlparse(Data["URL"])
    if Data["URL"][0] == "/":
        parsed_query = Data["URL"][1:].split("/")
    else:
        parsed_query = Data["URL"].split("/")  
    return url, parsed_url, parsed_query


def check_header( Data):
    if "Verb" not in Data:
        domoticz_error_api("Invalid web request received, no Verb present")
        return "400 Bad Request"
    elif Data["Verb"] not in ("GET", "PUT", "POST", "DELETE"):
        domoticz_error_api("Invalid web request received, only GET requests allowed (" + Data["Verb"] + ")")
        return "405 Method Not Allowed"
    elif "URL" not in Data:
        domoticz_error_api("Invalid web request received, no URL present")
        return "400 Bad Request"
    return "200 OK"


def send_file(self, Connection, webFilename, Data, _lastmodified, _response):
    self.logging( "Debug", "send_file %s %s" %(webFilename, _response))

    _response["Headers"]["Last-Modified"] = _lastmodified
    with open(webFilename, mode="rb") as webFile:
        _response["Data"] = webFile.read()

    _contentType, _contentEncoding = mimetypes.guess_type(str(webFilename))

    if _contentType is None:
        filename, file_extension = os.path.splitext(webFilename)
        EXTENSION_MIME_TYPE = {
            '.js': 'text/jscript',
            '.html': 'text/html',
            '.txt': 'text',
            '.woff': 'font/woff',
            '.woff2': 'font/woff',
            '.json': 'application/json',
            '.ttf': 'font/ttf',
            '.svg': 'image/svg+xml',
            '.eot': 'font/woff',
            '.css': 'text/css'

        }
        if file_extension in EXTENSION_MIME_TYPE:
            _contentType = EXTENSION_MIME_TYPE[ file_extension ]

    if _contentType:
        _response["Headers"]["Content-Type"] = with_charset(_contentType)
    if _contentEncoding:
        _response["Headers"]["Content-Encoding"] = _contentEncoding

    _response["Status"] = "200 OK"

    if "Accept-Encoding" in Data["Headers"]:
        self.sendResponse(Connection, _response, AcceptEncoding=Data["Headers"]["Accept-Encoding"])
    else:
        self.sendResponse(Connection, _response)


def with_charset(content_type):
    """Text types are served as UTF-8; a charset on a binary type (image/png) is meaningless."""
    if content_type.startswith("text/") or content_type in ("application/json", "application/javascript", "image/svg+xml"):
        return content_type + "; charset=utf-8"
    return content_type


def get_from_cache_if_available(self, Connection, webFilename, Data, _lastmodified, _response):
    if not self.pluginconf.pluginConf["enableCache"]:
        return False

    if not is_not_modified_since(Data["Headers"].get("If-Modified-Since"), webFilename):
        return False

    # No need to send it back
    self.logging( "Debug", f"User Caching - file: {webFilename} InCache: {Data['Headers']['If-Modified-Since']} versus Current: {_lastmodified}" )
    _response["Status"] = "304 Not Modified"
    self.sendResponse(Connection, _response)
    return True

def is_not_modified_since(if_modified_since, webFilename):
    """True when webFilename has not changed since the If-Modified-Since date (compared as dates, not strings)."""
    if not if_modified_since:
        return False
    try:
        since = parsedate_to_datetime(if_modified_since)
    except (TypeError, ValueError):
        return False
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    # HTTP dates have a one-second resolution
    return int(os.path.getmtime(webFilename)) <= since.timestamp()
