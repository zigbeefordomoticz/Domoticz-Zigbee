#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import mimetypes
import os
import os.path
from datetime import datetime
from time import gmtime, strftime
from urllib.parse import urlparse

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Classes.WebServer.tools import MAX_KB_TO_SEND, DumpHTTPResponseToLog


def onMessage(self, Connection, Data):

    self.logging("Debug", "WebServer onMessage : %s" % Data)
    # DumpHTTPResponseToLog(Data)

    headerCode = "200 OK"
    if "Verb" not in Data:
        Domoticz.Error("Invalid web request received, no Verb present")
        headerCode = "400 Bad Request"

    elif Data["Verb"] not in ("GET", "PUT", "POST", "DELETE"):
        Domoticz.Error("Invalid web request received, only GET requests allowed (" + Data["Verb"] + ")")
        headerCode = "405 Method Not Allowed"

    elif "URL" not in Data:
        Domoticz.Error("Invalid web request received, no URL present")
        headerCode = "400 Bad Request"

    parsed_url = urlparse(Data["URL"])
    self.logging("Debug", "URL: %s , Path: %s" % (Data["URL"], parsed_url.path))
    if Data["URL"][0] == "/":
        parsed_query = Data["URL"][1:].split("/")

    else:
        parsed_query = Data["URL"].split("/")

    self.logging("Debug", "parsed_query: %s" % (str(parsed_query)))

    # Any Cookie ?
    cookie = None
    if "Cookie" in Data["Headers"]:
        cookie = Data["Headers"]["Cookie"]

    if "Data" not in Data:
        Data["Data"] = None

    if headerCode != "200 OK":
        self.sendResponse(Connection, {"Status": headerCode})
        return
    
    url = Data["URL"]
    if len(parsed_query) >= 3 and parsed_query[0] == "rest-z4d" or parsed_query[0] == "rest-zigate":
        self.logging(
            "Debug",
            "Receiving a REST API - Version: %s, Verb: %s, Command: %s, Param: %s"
            % (parsed_query[1], Data["Verb"], parsed_query[2], parsed_query[3:]),
        )
        if parsed_query[0] == "rest-z4d" or parsed_query[0] == "rest-zigate" and parsed_query[1] == "1":
            # API Version 1
            self.do_rest(Connection, Data["Verb"], Data["Data"], parsed_query[1], parsed_query[2], parsed_query[3:])
        else:
            Domoticz.Error("Unknown API  %s" % parsed_query)
            headerCode = "400 Bad Request"
            self.sendResponse(Connection, {"Status": headerCode})
        return

    # Finaly we simply has to serve a File.
    webFilename = self.homedirectory + "www" + url
    self.logging("Debug", "webFilename: %s" % webFilename)
    if not os.path.isfile(webFilename):
        webFilename = self.homedirectory + "www" + "/z4d/index.html"
        self.logging("Debug", "Redirecting to /z4d/index.html")

    # We are ready to send the response
    _response = setupHeadersResponse(cookie)
    if self.pluginconf.pluginConf["enableKeepalive"]:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    if not self.pluginconf.pluginConf["enableCache"]:
        _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
        _response["Headers"]["Pragma"] = "no-cache"
        _response["Headers"]["Expires"] = "0"
        _response["Headers"]["Accept"] = "*/*"
    else:
        _response["Headers"]["Cache-Control"] = "private"

    self.logging("Debug", "Opening: %s" % webFilename)

    currentVersionOnServer = os.path.getmtime(webFilename)
    _lastmodified = strftime("%a, %d %m %y %H:%M:%S GMT", gmtime(currentVersionOnServer))

    # Check Referrrer
    if "Referer" in Data["Headers"]:
        self.logging("Debug", "Set Referer: %s" % Data["Headers"]["Referer"])
        _response["Headers"]["Referer"] = Data["Headers"]["Referer"]

    # Can we use Cache if exists
    if get_from_cache_if_available( self, Connection, webFilename, Data, _lastmodified, _response):
        return
    
    if "Ranges" in Data["Headers"]:
        get__range_and_send(self,Connection, webFilename, Data, _response )
    else:
        send_file( self, Connection, webFilename, Data, _lastmodified, _response)

def send_file(self, Connection, webFilename, Data, _lastmodified, _response):
    self.logging( "Debug", "send_file %s %s" %(webFilename, _response))

    _response["Headers"]["Last-Modified"] = _lastmodified
    with open(webFilename, mode="rb") as webFile:
        _response["Data"] = webFile.read()

    _contentType, _contentEncoding = mimetypes.guess_type(Data["URL"])
    self.logging( "Debug", "--- _contentType %s" %_contentType)
    self.logging( "Debug", "--- _contentEncoding %s" %_contentEncoding)
    
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

    self.logging( "Debug", "--- _contentType %s" %_contentType)
    self.logging( "Debug", "--- _contentEncoding %s" %_contentEncoding)

    if _contentType:
        _response["Headers"]["Content-Type"] = _contentType + "; charset=utf-8"
    if _contentEncoding:
        _response["Headers"]["Content-Encoding"] = _contentEncoding

    _response["Status"] = "200 OK"

    if "Accept-Encoding" in Data["Headers"]:
        self.logging( "Debug", "send_file  sendResponse %s %s" %(webFilename, _response))
        self.sendResponse(Connection, _response, AcceptEncoding=Data["Headers"]["Accept-Encoding"])
    else:
        self.logging( "Debug", "send_file  sendResponse %s %s" %(webFilename, _response))
        self.sendResponse(Connection, _response)
    
def get__range_and_send(self,Connection, webFilename, Data, _response ):
    self.logging("Debug", "Ranges processing")
    RangeProcess = Data["Headers"]["Range"]
    fileStartPosition = int(RangeProcess[RangeProcess.find("=") + 1 : RangeProcess.find("-")])
    messageFileSize = os.path.getsize(webFilename)
    messageFile = open(webFilename, mode="rb")
    messageFile.seek(fileStartPosition)
    fileContent = messageFile.read(MAX_KB_TO_SEND)
    self.logging(
        "Debug",
        Connection.Address
        + ":"
        + Connection.Port
        + " Sent 'GET' request file '"
        + Data["URL"]
        + "' from position "
        + str(fileStartPosition)
        + ", "
        + str(len(fileContent))
        + " bytes will be returned",
    )
    _response["Status"] = "200 OK"
    if len(fileContent) == MAX_KB_TO_SEND:
        _response["Status"] = "206 Partial Content"
        _response["Headers"]["Content-Range"] = (
            "bytes " + str(fileStartPosition) + "-" + str(messageFile.tell()) + "/" + str(messageFileSize)
        )
    DumpHTTPResponseToLog(_response)
    Connection.Send(_response)
    if not self.pluginconf.pluginConf["enableKeepalive"]:
        Connection.Disconnect()

def get_from_cache_if_available( self, Connection, webFilename, Data, _lastmodified, _response):
    if not self.pluginconf.pluginConf["enableCache"]:
        return False
    
    if "If-Modified-Since" not in Data["Headers"]:
        return False
    
    lastVersionInCache = Data["Headers"]["If-Modified-Since"]
    self.logging("Debug", "InCache: %s versus Current: %s" % (lastVersionInCache, _lastmodified))
    if lastVersionInCache != _lastmodified:
        return False
    
    # No need to send it back
    self.logging(
        "Debug",
        "User Caching - file: %s InCache: %s versus Current: %s"
        % (webFilename, lastVersionInCache, _lastmodified),
    )
    _response["Status"] = "304 Not Modified"
    self.sendResponse(Connection, _response)
    return True
