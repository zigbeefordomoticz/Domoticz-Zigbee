#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import mimetypes
import os
import os.path
import time
from datetime import datetime
from pathlib import Path
from time import gmtime, strftime
from urllib.parse import urlparse

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Classes.WebServer.tools import MAX_BLOCK_SIZE, DumpHTTPResponseToLog
from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)

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
    self.logging("Debug", f"WebServer onMessage: {Data}")

    headerCode = check_header(Data)
    self.logging("Debug", f"onMessage - headerCode: {headerCode}")

    if headerCode != "200 OK":
        self.sendResponse(Connection, {"Status": headerCode})
        return

    url, parsed_url, parsed_query = parse_and_decode_query(Data)
    cookie = Data["Headers"].get("Cookie")
    Data.setdefault("Data", None)

    if handle_rest_api(self, Connection, Data, parsed_query):
        return

    self.logging("Debug", f"Download: {is_download( parsed_query, parsed_url)}")
    if is_download( parsed_query, parsed_url):
        # we have to serve a file for download purposes, let's remove '/download' to get the filename to access
        webFilename = parsed_url.path[len('/download'):]

    else:
        # Most likely a file from the wwww/ to be served
        webFilename = get_web_filename(self, url, parsed_query, parsed_url)

    self.logging("Debug", f"Downloading: {webFilename}")

    if not os.path.isfile(webFilename):
        self.logging("Debug", "Redirect to index.html")
        webFilename = redirect_to_index_html(self)

    response_headers = prepare_response_headers(self,cookie)
    _response = setupHeadersResponse(cookie)
    _response["Headers"].update(response_headers)

    self.logging("Debug", f"Opening: {webFilename}")

    _last_modified = get_last_modified(webFilename)
    set_referer_header(self, Data, _response)

    if get_from_cache_or_send(self, Connection, webFilename, Data, _last_modified, _response):
        return

    if "Ranges" in Data["Headers"]:
        get_range_and_send(self, Connection, webFilename, Data, _response)
    else:
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


def get_web_filename(self, url, parsed_query, parsed_url):
    if parsed_query[0] == 'download':
        webFilename = parsed_url.path[len('/download'):]
    else:
        _homedir = Path(self.homedirectory)
        webFilename = _homedir / ("www" + url)
        self.logging("Debug", f"webFilename: {webFilename}")
    return webFilename


def redirect_to_index_html(self):
    _homedir = Path(self.homedirectory)
    webFilename = _homedir / "www/z4d/index.html"
    self.logging("Debug", "Redirecting to /z4d/index.html")
    return webFilename


def prepare_response_headers(self, cookie):
    return {
        "Connection": (
            "Keep-alive"
            if self.pluginconf.pluginConf["enableKeepalive"]
            else "Close"
        ),
        "Cache-Control": (
            "private"
            if self.pluginconf.pluginConf["enableCache"]
            else "no-cache, no-store, must-revalidate"
        ),
        "Pragma": (
            "" if self.pluginconf.pluginConf["enableCache"] else "no-cache"
        ),
        "Expires": "" if self.pluginconf.pluginConf["enableCache"] else "0",
        "Accept": "" if self.pluginconf.pluginConf["enableCache"] else "*/*",
    }


def get_last_modified(webFilename):
    current_version_on_server = os.path.getmtime(webFilename)
    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(current_version_on_server))


def set_referer_header(self, Data, _response):
    if "Referer" in Data["Headers"]:
        _response["Headers"]["Referer"] = Data["Headers"]["Referer"]


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

    _contentType, _contentEncoding = mimetypes.guess_type(Data["URL"])

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
        _response["Headers"]["Content-Type"] = _contentType + "; charset=utf-8"
    if _contentEncoding:
        _response["Headers"]["Content-Encoding"] = _contentEncoding

    _response["Status"] = "200 OK"

    if "Accept-Encoding" in Data["Headers"]:
        self.sendResponse(Connection, _response, AcceptEncoding=Data["Headers"]["Accept-Encoding"])
    else:
        self.sendResponse(Connection, _response)


def get_range_and_send(self, Connection, webFilename, Data, _response):
    self.logging("Debug", "Ranges processing")

    RangeProcess = Data["Headers"]["Range"]
    fileStartPosition = int(RangeProcess[RangeProcess.find("=") + 1 : RangeProcess.find("-")])

    messageFileSize = os.path.getsize(webFilename)
    messageFile = open(webFilename, mode="rb")
    messageFile.seek(fileStartPosition)

    fileContent = messageFile.read(MAX_BLOCK_SIZE)

    self.logging(
        "Debug",
        f"{Connection.Address}:{Connection.Port} Sent 'GET' request file '{Data['URL']}' from position {fileStartPosition}, {len(fileContent)} bytes will be returned",
    )

    _response["Status"] = "200 OK"
    if len(fileContent) == MAX_BLOCK_SIZE:
        _response["Status"] = "206 Partial Content"
        _response["Headers"]["Content-Range"] = f"bytes {fileStartPosition}-{messageFile.tell()}/{messageFileSize}"

    Connection.Send(_response)

    if not self.pluginconf.pluginConf["enableKeepalive"]:
        Connection.Disconnect()


def get_from_cache_if_available(self, Connection, webFilename, Data, _lastmodified, _response):
    if not self.pluginconf.pluginConf["enableCache"]:
        return False

    if "If-Modified-Since" not in Data["Headers"]:
        return False

    if Data["Headers"]["If-Modified-Since"] != _lastmodified:
        return False

    # No need to send it back
    self.logging( "Debug", f"User Caching - file: {webFilename} InCache: {Data['Headers']['If-Modified-Since']} versus Current: {_lastmodified}" )
    _response["Status"] = "304 Not Modified"
    self.sendResponse(Connection, _response)
    return True