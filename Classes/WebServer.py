#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
import os
import os.path
import mimetypes
from datetime import datetime

try:
    import zlib
except Exception as Err:
    Domoticz.Error("zlib import error: '"+str(Err)+"'")
try:
    import gzip
except Exception as Err:
    Domoticz.Error("gzip import error: '"+str(Err)+"'")

from urllib.parse import urlparse, urlsplit, urldefrag, parse_qs
from time import time, ctime, strftime, gmtime, mktime, strptime

from Modules.zigateConsts import ADDRESS_MODE, MAX_LOAD_ZIGATE, ZCL_CLUSTERS_LIST , CERTIFICATION_CODE, PROFILE_ID, ZHA_DEVICES, ZLL_DEVICES, ZIGATE_COMMANDS, ZCL_CLUSTERS_ACT
from Modules.bindings import webBind, webUnBind
from Modules.output import ZigatePermitToJoin, sendZigateCmd, start_Zigate, setExtendedPANID, zigateBlueLed
from Modules.legrand_netatmo import legrand_ledInDark, legrand_ledIfOnOnOff, legrand_dimOnOff, legrand_ledShutter
from Modules.actuators import actuators
from Modules.tools import is_hex
from Classes.PluginConf import PluginConf,SETTINGS
from Classes.GroupMgt import GroupsManagement
from Classes.DomoticzDB import DomoticzDB_Preferences

MAX_KB_TO_SEND = 8 * 1024   # Chunk size
DEBUG_HTTP = False

MIMETYPES = { 
        "gif": "image/gif" ,
        "htm": "text/html" ,
        "html": "text/html" ,
        "jpg": "image/jpeg" ,
        "png": "image/png" ,
        "css": "text/css" ,
        "xml": "application/xml" ,
        "js": "application/javascript" ,
        "json": "application/json" ,
        "swf": "application/x-shockwave-flash" ,
        "manifest": "text/cache-manifest" ,
        "appcache": "text/cache-manifest" ,
        "xls": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ,
        "m3u": "audio/mpegurl" ,
        "mp3": "audio/mpeg" ,
        "ogg": "audio/ogg" ,
        "php": "text/html" ,
        "wav": "audio/x-wav" ,
        "svg": "image/svg+xml" ,
        "db": "application/octet-stream" ,
        "otf": "application/x-font-otf" ,
        "ttf": "application/x-font-ttf" ,
        "woff": "application/x-font-woff" 
   }



class WebServer(object):
    hearbeats = 0 

    def __init__( self, networkenergy, networkmap, ZigateData, PluginParameters, PluginConf, Statistics, adminWidgets, ZigateComm, HomeDirectory, hardwareID, DevicesInPairingMode, groupManagement, Devices, ListOfDevices, IEEE2NWK , permitTojoin, WebUserName, WebPassword, PluginHealth, httpPort, loggingFileHandle):

        self.httpServerConn = None
        self.httpClientConn = None
        self.httpServerConns = {}
        self.httpPort = httpPort
        self.loggingFileHandle = loggingFileHandle

        self.httpsServerConn = None
        self.httpsClientConn = None
        self.httpsServerConns = {}
        self.httpsPort = None

        self.PluginHealth = PluginHealth
        self.WebUsername = WebUserName
        self.WebPassword = WebPassword
        self.pluginconf = PluginConf
        self.zigatedata = ZigateData
        self.adminWidget = adminWidgets
        self.ZigateComm = ZigateComm
        self.statistics = Statistics
        self.pluginparameters = PluginParameters
        self.networkmap = networkmap
        self.networkenergy = networkenergy

        self.permitTojoin = permitTojoin

        if groupManagement:
            self.groupmgt = groupManagement
        else:
            self.groupmgt = None
        self.ListOfDevices = ListOfDevices
        self.DevicesInPairingMode = DevicesInPairingMode
        self.fakeDevicesInPairingMode = 0
        self.IEEE2NWK = IEEE2NWK
        self.Devices = Devices

        self.restart_needed = {}
        self.restart_needed['RestartNeeded'] = False

        self.homedirectory = HomeDirectory
        self.hardwareID = hardwareID
        mimetypes.init()
        # Start the WebServer
        self.startWebServer()
        
    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Status( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Status( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Status( message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Log( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def _loggingDebug( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def logging( self, logType, message):

        self.debugWebServer = self.pluginconf.pluginConf['debugWebServer']
        if self.debugWebServer and logType == 'Debug':
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)
        return


    def  startWebServer( self ):

        #self.httpPort = '9440'
        self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port=self.httpPort)
        self.httpServerConn.Listen()
        self.logging( 'Status', "Web backend for Web User Interface started on port: %s" %self.httpPort)

        #self.httpsPort = '9443'
        #self.httpsServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTPS", Port=self.httpsPort)
        #self.httpsServerConn.Listen()
        #self.logging( 'Status', "Web backend for Web User Interface started on port: %s" %self.httpsPort)


    def onConnect(self, Connection, Status, Description):

        self.logging( 'Debug', "Connection: %s, description: %s" %(Connection, Description))
        if Status != 0:
            Domoticz.Error("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
            return

        # Search for Protocol
        for item in str(Connection).split(','):
            if item.find('Protocol') != -1:
                label, protocol = item.split(':')
                protocol = protocol.strip().strip("'")
                self.logging( 'Debug', '%s:>%s' %(label, protocol))

        if protocol == 'HTTP':
            # http connection
            if Connection.Name not in self.httpServerConns:
                self.logging( 'Debug', "New Connection: %s" %(Connection.Name))
                self.httpServerConns[Connection.Name] = Connection
        elif protocol == 'HTTPS':
            # https connection
            if Connection.Name not in self.httpsServerConns:
                self.logging( 'Debug', "New Connection: %s" %(Connection.Name))
                self.httpServerConns[Connection.Name] = Connection
        else:
            Domoticz.Error("onConnect - unexpected protocol for connection: %s" %(Connection))

        self.logging( 'Debug', "Number of http  Connections : %s" %len(self.httpServerConns))
        self.logging( 'Debug', "Number of https Connections : %s" %len(self.httpsServerConns))

    def onDisconnect ( self, Connection ):

        self.logging( 'Debug', "onDisconnect %s" %(Connection))

        if Connection.Name in self.httpServerConns:
            self.logging( 'Debug', "onDisconnect - removing from list : %s" %Connection.Name)
            del self.httpServerConns[Connection.Name]
        elif Connection.Name in self.httpsServerConns:
            self.logging( 'Debug', "onDisconnect - removing from list : %s" %Connection.Name)
            del self.httpsServerConns[Connection.Name]
        else:
            # Most likely it is about closing the Server
            self.logging( "Log", "onDisconnect - Closing %s" %Connection)

    def onStop( self ):

        # Make sure that all remaining open connections are closed
        self.logging( 'Debug', "onStop()")

        # Search for Protocol
        for connection in self.httpServerConns:
            self.logging( 'Log', "Closing %s" %connection)
            self.httpServerConns[Connection.Name].close()
        for connection in self.httpsServerConns:
            self.logging( 'Log', "Closing %s" %connection)
            self.httpServerConns[Connection.Name].close()


    def onMessage( self, Connection, Data ):

            self.logging( 'Debug', "WebServer onMessage : %s" %Data)
            #DumpHTTPResponseToLog(Data)


            headerCode = "200 OK"
            if (not 'Verb' in Data):
                Domoticz.Error("Invalid web request received, no Verb present")
                headerCode = "400 Bad Request"
            elif (Data['Verb'] not in ( 'GET', 'PUT', 'POST', 'DELETE')):
                Domoticz.Error("Invalid web request received, only GET requests allowed ("+Data['Verb']+")")
                headerCode = "405 Method Not Allowed"
            elif (not 'URL' in Data):
                Domoticz.Error("Invalid web request received, no URL present")
                headerCode = "400 Bad Request"

            parsed_url = urlparse(  Data['URL'] )
            self.logging( 'Debug', "URL: %s , Path: %s" %( Data['URL'], parsed_url.path))
            if  Data['URL'][0] == '/': parsed_query = Data['URL'][1:].split('/')
            else: parsed_query = Data['URL'].split('/')

            # Any Cookie ?
            cookie = None
            if 'Cookie' in Data['Headers']:
                cookie = Data['Headers']['Cookie']

            if 'Data' not in Data: Data['Data'] = None

            if (headerCode != "200 OK"):
                self.sendResponse( Connection, {"Status": headerCode} )
                return
            else:
                if len(parsed_query) >= 3:
                    self.logging( 'Debug', "Receiving a REST API - Version: %s, Verb: %s, Command: %s, Param: %s" \
                        %( parsed_query[1], Data['Verb'],  parsed_query[2], parsed_query[3:] ))
                    if parsed_query[0] == 'rest-zigate' and parsed_query[1] == '1':
                        # API Version 1
                        self.do_rest( Connection, Data['Verb'], Data['Data'], parsed_query[1], parsed_query[2], parsed_query[3:])
                    else:
                        Domoticz.Error("Unknown API  %s" %parsed_query)
                        headerCode = "400 Bad Request"
                        self.sendResponse( Connection, {"Status": headerCode} )
                    return

            # Finaly we simply has to serve a File.
            webFilename = self.homedirectory +'www'+ Data['URL']
            self.logging( 'Debug', "webFilename: %s" %webFilename)
            if not os.path.isfile( webFilename ):
                webFilename =  self.homedirectory + 'www' + "/index.html"
                self.logging( 'Debug', "Redirecting to /index.html")

            # We are ready to send the response
            _response = setupHeadersResponse( cookie )
            if self.pluginconf.pluginConf['enableKeepalive']:
                _response["Headers"]["Connection"] = "Keep-alive"
            else:
                _response["Headers"]["Connection"] = "Close"
            if not self.pluginconf.pluginConf['enableCache']:
                _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
                _response["Headers"]["Pragma"] = "no-cache"
                _response["Headers"]["Expires"] = "0"
                _response["Headers"]["Accept"] = "*/*"
            else:
                _response["Headers"]["Cache-Control"] = "private"

            self.logging( 'Debug', "Opening: %s" %webFilename)
            currentVersionOnServer = os.path.getmtime(webFilename)
            _lastmodified = strftime("%a, %d %m %y %H:%M:%S GMT", gmtime(currentVersionOnServer))

            # Check Referrrer
            if 'Referer' in Data['Headers']:
                self.logging( 'Debug', "Set Referer: %s" %Data["Headers"]["Referer"])
                _response["Headers"]["Referer"] = Data['Headers']['Referer']

            # Can we use Cache if exists
            if self.pluginconf.pluginConf['enableCache']:
                if 'If-Modified-Since' in Data['Headers']:
                    lastVersionInCache = Data['Headers']['If-Modified-Since']
                    self.logging( 'Debug', "InCache: %s versus Current: %s" %(lastVersionInCache, _lastmodified))
                    if lastVersionInCache == _lastmodified:
                        # No need to send it back
                        self.logging( 'Debug', "User Caching - file: %s InCache: %s versus Current: %s" %(webFilename, lastVersionInCache, _lastmodified))
                        _response['Status'] = "304 Not Modified"
                        self.sendResponse( Connection, _response )
                        return _response

            if 'Ranges' in Data['Headers']:
                self.logging( 'Debug', "Ranges processing")
                range = Data['Headers']['Range']
                fileStartPosition = int(range[range.find('=')+1:range.find('-')])
                messageFileSize = os.path.getsize(webFilename)
                messageFile = open(webFilename, mode='rb')
                messageFile.seek(fileStartPosition)
                fileContent = messageFile.read(MAX_KB_TO_SEND)
                self.logging( 'Debug', Connection.Address+":"+Connection.Port+" Sent 'GET' request file '"+Data['URL']+"' from position "+str(fileStartPosition)+", "+str(len(fileContent))+" bytes will be returned")
                _response["Status"] = "200 OK"
                if (len(fileContent) == MAX_KB_TO_SEND):
                    _response["Status"] = "206 Partial Content"
                    _response["Headers"]["Content-Range"] = "bytes "+str(fileStartPosition)+"-"+str(messageFile.tell())+"/"+str(messageFileSize)
                DumpHTTPResponseToLog( _response )
                Connection.Send( _response)
                if not self.pluginconf.pluginConf['enableKeepalive']:
                    Connection.Disconnect()
            else:
                _response["Headers"]["Last-Modified"] = _lastmodified
                with open(webFilename , mode ='rb') as webFile:
                    _response["Data"] = webFile.read()
    
                _contentType, _contentEncoding = mimetypes.guess_type( Data['URL'] )
     
                if _contentType:
                    _response["Headers"]["Content-Type"] = _contentType +"; charset=utf-8"
                if _contentEncoding:
                    _response["Headers"]["Content-Encoding"] = _contentEncoding 
     
                _response["Status"] = "200 OK"

                if 'Accept-Encoding' in Data['Headers']:
                    self.sendResponse( Connection, _response, AcceptEncoding = Data['Headers']['Accept-Encoding']  )
                else:
                    self.sendResponse( Connection, _response )


    def sendResponse( self, Connection, Response, AcceptEncoding=None ):

        if 'Data' not in Response:
            DumpHTTPResponseToLog( Response )
            Connection.Send( Response )
            if not self.pluginconf.pluginConf['enableKeepalive']:
                Connection.Disconnect()
            return

        if Response['Data'] is None:
            DumpHTTPResponseToLog( Response )
            Connection.Send( Response )
            if not self.pluginconf.pluginConf['enableKeepalive']:
                Connection.Disconnect()
            return

        self.logging( 'Debug', "Sending Response to : %s" %(Connection.Name))

        # Compression
        allowgzip = self.pluginconf.pluginConf['enableGzip']
        allowdeflate = self.pluginconf.pluginConf['enableDeflate']

        if (allowgzip or allowdeflate ) and 'Data' in Response and AcceptEncoding:
            self.logging( 'Debug', "sendResponse - Accept-Encoding: %s, Chunk: %s, Deflate: %s , Gzip: %s" %(AcceptEncoding, self.pluginconf.pluginConf['enableChunk'], allowdeflate, allowgzip))
            if len(Response["Data"]) > MAX_KB_TO_SEND:
                orig_size = len(Response["Data"])
                if allowdeflate and AcceptEncoding.find('deflate') != -1:
                    self.logging( 'Debug', "Compressing - deflate")
                    zlib_compress = zlib.compressobj( 9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 2)
                    deflated = zlib_compress.compress(Response["Data"])
                    deflated += zlib_compress.flush()
                    Response["Headers"]['Content-Encoding'] = 'deflate'
                    Response["Data"] = deflated

                elif allowgzip and AcceptEncoding.find('gzip') != -1:
                    self.logging( 'Debug', "Compressing - gzip")
                    Response["Data"] = gzip.compress( Response["Data"] )
                    Response["Headers"]['Content-Encoding'] = 'gzip'

                self.logging( 'Debug', "Compression from %s to %s (%s %%)" %( orig_size, len(Response["Data"]), int(100-(len(Response["Data"])/orig_size)*100)))

        # Chunking, Follow the Domoticz Python Plugin Framework

        if self.pluginconf.pluginConf['enableChunk'] and len(Response['Data']) > MAX_KB_TO_SEND:
            idx = 0
            HTTPchunk = {}
            HTTPchunk['Status'] = Response['Status']
            HTTPchunk['Chunk'] = True
            HTTPchunk['Headers'] = {}
            HTTPchunk['Headers'] = dict(Response['Headers'])
            HTTPchunk['Data'] = Response['Data'][0:MAX_KB_TO_SEND]
            self.logging( 'Debug', "Sending: %s out of %s" %(idx, len((Response['Data']))))

            # Firs Chunk
            DumpHTTPResponseToLog( HTTPchunk )
            Connection.Send( HTTPchunk )

            idx = MAX_KB_TO_SEND
            while idx != -1:
                tosend={}
                tosend['Chunk'] = True
                if idx + MAX_KB_TO_SEND < len(Response['Data']):
                    # we have to send one chunk and then continue
                    tosend['Data'] = Response['Data'][idx:idx+MAX_KB_TO_SEND]        
                    idx += MAX_KB_TO_SEND
                else:
                    # Last Chunk with Data
                    tosend['Data'] = Response['Data'][idx:]        
                    idx = -1

                self.logging( 'Debug', "Sending Chunk: %s out of %s" %(idx, len((Response['Data']))))
                Connection.Send( tosend )

            # Closing Chunk
            tosend={}
            tosend['Chunk'] = True
            Connection.Send( tosend )
            if not self.pluginconf.pluginConf['enableKeepalive']:
                Connection.Disconnect()
        else:
            #Response['Headers']['Content-Length'] = len( Response['Data'] )
            DumpHTTPResponseToLog( Response )
            Connection.Send( Response )
            if not self.pluginconf.pluginConf['enableKeepalive']:
                Connection.Disconnect()

    def keepConnectionAlive( self ):

        self.heartbeats += 1
        return

    def do_rest( self, Connection, verb, data, version, command, parameters):

        REST_COMMANDS = { 
                'unbinding':     {'Name':'unbinding',     'Verbs':{'PUT'}, 'function':self.rest_unbinding},
                'binding':       {'Name':'binding',       'Verbs':{'PUT'}, 'function':self.rest_binding},
                'bindLSTcluster':{'Name':'bindLSTcluster','Verbs':{'GET'}, 'function':self.rest_bindLSTcluster},
                'bindLSTdevice': {'Name':'bindLSTdevice', 'Verbs':{'GET'}, 'function':self.rest_bindLSTdevice},
                'new-hrdwr':     {'Name':'new-hrdwr',     'Verbs':{'GET'}, 'function':self.rest_new_hrdwr},
                'rcv-nw-hrdwr':  {'Name':'rcv-nw-hrdwr',  'Verbs':{'GET'}, 'function':self.rest_rcv_nw_hrdwr},
                'device':        {'Name':'device',        'Verbs':{'GET'}, 'function':self.rest_Device},
                'dev-cap':       {'Name':'dev-cap',       'Verbs':{'GET'}, 'function':self.rest_dev_capabilities},
                'dev-command':   {'Name':'dev-command',       'Verbs':{'PUT'}, 'function':self.rest_dev_command},
                'raw-command':   {'Name':'raw-command',       'Verbs':{'PUT'}, 'function':self.rest_raw_command},
                'domoticz-env':  {'Name':'domoticz-env',  'Verbs':{'GET'}, 'function':self.rest_domoticz_env},
                'plugin-health': {'Name':'plugin-health', 'Verbs':{'GET'}, 'function':self.rest_plugin_health},
                'nwk-stat':      {'Name':'nwk_stat',      'Verbs':{'GET','DELETE'}, 'function':self.rest_nwk_stat},
                'permit-to-join':{'Name':'permit-to-join','Verbs':{'GET','PUT'}, 'function':self.rest_PermitToJoin},
                'plugin':        {'Name':'plugin',        'Verbs':{'GET'}, 'function':self.rest_PluginEnv},
                'plugin-stat':   {'Name':'plugin-stat',   'Verbs':{'GET'}, 'function':self.rest_plugin_stat},
                'plugin-restart':   {'Name':'plugin-restart',   'Verbs':{'GET'}, 'function':self.rest_plugin_restart},
                'rescan-groups': {'Name':'rescan-groups', 'Verbs':{'GET'}, 'function':self.rest_rescan_group},
                'restart-needed':{'Name':'restart-needed','Verbs':{'GET'}, 'function':self.rest_restart_needed},
                'req-nwk-inter': {'Name':'req-nwk-inter', 'Verbs':{'GET'}, 'function':self.rest_req_nwk_inter},
                'req-nwk-full':  {'Name':'req-nwk-full',  'Verbs':{'GET'}, 'function':self.rest_req_nwk_full},
                'req-topologie': {'Name':'req-topologie', 'Verbs':{'GET'}, 'function':self.rest_req_topologie},
                'sw-reset-zigate':  {'Name':'sw-reset-zigate',  'Verbs':{'GET'}, 'function':self.rest_reset_zigate},
                'setting':       {'Name':'setting',       'Verbs':{'GET','PUT'}, 'function':self.rest_Settings},
                'topologie':     {'Name':'topologie',     'Verbs':{'GET','DELETE'}, 'function':self.rest_netTopologie},
                'zdevice':       {'Name':'zdevice',       'Verbs':{'GET','DELETE'}, 'function':self.rest_zDevice},
                'zdevice-name':  {'Name':'zdevice-name',  'Verbs':{'GET','PUT','DELETE'}, 'function':self.rest_zDevice_name},
                'zdevice-raw':   {'Name':'zdevice-raw',  'Verbs':{'GET','PUT'}, 'function':self.rest_zDevice_raw},
                'zgroup':        {'Name':'device',        'Verbs':{'GET','PUT'}, 'function':self.rest_zGroup},
                'zgroup-list-available-device':   
                                 {'Name':'zgroup-list-available-devic',        'Verbs':{'GET'}, 'function':self.rest_zGroup_lst_avlble_dev},
                'zigate':        {'Name':'zigate',        'Verbs':{'GET'}, 'function':self.rest_zigate},
                'zigate-erase-PDM':{'Name':'zigate-erase-PDM', 'Verbs':{'GET'}, 'function':self.rest_zigate_erase_PDM}
                }

        self.logging( 'Debug', "do_rest - Verb: %s, Command: %s, Param: %s" %(verb, command, parameters))

        HTTPresponse = {}

        if command in REST_COMMANDS:
            if verb in REST_COMMANDS[command]['Verbs']:
                HTTPresponse = setupHeadersResponse()
                if self.pluginconf.pluginConf['enableKeepalive']:
                    HTTPresponse["Headers"]["Connection"] = "Keep-alive"
                else:
                    HTTPresponse["Headers"]["Connection"] = "Close"
                HTTPresponse["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
                HTTPresponse["Headers"]["Pragma"] = "no-cache"
                HTTPresponse["Headers"]["Expires"] = "0"
                HTTPresponse["Headers"]["Accept"] = "*/*"
                if version == '1':
                    HTTPresponse = REST_COMMANDS[command]['function']( verb, data, parameters)
                elif version == '2':
                    HTTPresponse = REST_COMMANDS[command]['functionv2']( verb, data, parameters)

        self.logging( 'Debug', "==> return HTTPresponse: %s" %(HTTPresponse))
        if HTTPresponse == {} or HTTPresponse is None:
            # We reach here due to failure !
            HTTPresponse = setupHeadersResponse()
            if self.pluginconf.pluginConf['enableKeepalive']:
                HTTPresponse["Headers"]["Connection"] = "Keep-alive"
            else:
                HTTPresponse["Headers"]["Connection"] = "Close"
            if not self.pluginconf.pluginConf['enableCache']:
                HTTPresponse["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
                HTTPresponse["Headers"]["Pragma"] = "no-cache"
                HTTPresponse["Headers"]["Expires"] = "0"
                HTTPresponse["Headers"]["Accept"] = "*/*"
            HTTPresponse["Status"] = "400 BAD REQUEST"
            HTTPresponse["Data"] = 'Unknown REST command: %s' %command
            HTTPresponse["Headers"]["Content-Type"] = "text/plain; charset=utf-8"

        self.logging( 'Debug', "==> sending HTTPresponse: %s to %s" %(HTTPresponse, Connection))
        self.sendResponse( Connection, HTTPresponse )

    def rest_plugin_health( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        if not self.pluginconf.pluginConf['enableCache']:
            _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
            _response["Headers"]["Pragma"] = "no-cache"
            _response["Headers"]["Expires"] = "0"
            _response["Headers"]["Accept"] = "*/*"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            health = {}
            health['HealthFlag'] = self.PluginHealth['Flag']
            health['HealthTxt'] = self.PluginHealth['Txt']
            if 'Firmware Update' in self.PluginHealth:
                health['OTAupdateProgress'] = self.PluginHealth['Firmware Update']['Progress']
                health['OTAupdateDevice'] = self.PluginHealth['Firmware Update']['Device']

            if self.groupmgt:
                health['GroupStatus'] = self.groupmgt.StartupPhase

            _response["Data"] = json.dumps( health, sort_keys=True )

        return _response

    def rest_req_nwk_inter( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        if not self.pluginconf.pluginConf['enableCache']:
            _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
            _response["Headers"]["Pragma"] = "no-cache"
            _response["Headers"]["Expires"] = "0"
            _response["Headers"]["Accept"] = "*/*"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            action = {}
            action['Name'] = "Nwk-Interferences"
            action['TimeStamp'] = int(time())
            _response["Data"] = json.dumps( action, sort_keys=True )

            if self.pluginparameters['Mode1'] != 'None':
                if self.networkenergy:
                    self.networkenergy.start_scan()

        return _response

    def rest_req_nwk_full( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        if not self.pluginconf.pluginConf['enableCache']:
            _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
            _response["Headers"]["Pragma"] = "no-cache"
            _response["Headers"]["Expires"] = "0"
            _response["Headers"]["Accept"] = "*/*"

        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            action = {}
            action['Name'] = "Nwk-Energy-Full"
            action['TimeStamp'] = int(time())
            _response["Data"] = json.dumps( action, sort_keys=True )

            if self.pluginparameters['Mode1'] != 'None':
                if self.networkenergy:
                    self.networkenergy.start_scan( root='0000', target='0000')

        return _response

    def rest_req_topologie( self, verb, data, parameters):
        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            action = {}
            action['Name'] = 'Req-Topology'
            action['TimeStamp'] = int(time())
            _response["Data"] = json.dumps( action, sort_keys=True )

            self.logging( 'Log', "Request a Start of Network Topology scan")
            if self.networkmap:
                if not self.networkmap.NetworkMapPhase():
                    self.networkmap.start_scan()
                else:
                    self.logging( 'Log', "Cannot start Network Topology as one is in progress...")
        return _response

    def rest_zigate_erase_PDM( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            self.logging( 'Status', "Erase Zigate PDM")
            Domoticz.Error("Erase Zigate PDM non implémenté pour l'instant")
            if self.pluginconf.pluginConf['eraseZigatePDM']:
                if self.pluginparameters['Mode1'] != 'None':
                    sendZigateCmd(self, "0012", "")
                self.pluginconf.pluginConf['eraseZigatePDM'] = 0

            if self.pluginconf.pluginConf['extendedPANID'] is not None:
                self.logging( 'Status', "ZigateConf - Setting extPANID : 0x%016x" %( self.pluginconf.pluginConf['extendedPANID'] ))
                if self.pluginparameters['Mode1'] != 'None':
                    setExtendedPANID(self, self.pluginconf.pluginConf['extendedPANID'])
            action = {}
            action['Description'] = 'Erase Zigate PDM - Non Implemente'
            #if self.pluginparameters['Mode1'] != 'None':
            #    start_Zigate( self )
        return _response

    def rest_rescan_group( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        action = {}
        if verb == 'GET':
            self.groupListFileName = self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %self.hardwareID
            JsonGroupConfigFileName = self.pluginconf.pluginConf['pluginData'] + "/ZigateGroupsConfig-%02d.json" %self.hardwareID
            TxtGroupConfigFileName = self.pluginconf.pluginConf['pluginConfig'] + "/ZigateGroupsConfig-%02d.txt" %self.hardwareID
            for filename in ( TxtGroupConfigFileName, JsonGroupConfigFileName, self.groupListFileName ):
                if os.path.isfile( filename ):
                    self.logging( 'Debug', "rest_rescan_group - Removing file: %s" %filename )
                    os.remove( filename )
                    self.restart_needed['RestartNeeded'] = True
            action['Name'] = 'Groups file removed.'
            action['TimeStamp'] = int(time())

        _response["Data"] = json.dumps( action , sort_keys=True )

        return _response


    def rest_reset_zigate( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        action = {}
        if verb == 'GET':
            if self.pluginparameters['Mode1'] != 'None':
                self.zigatedata['startZigateNeeded'] = True
                #start_Zigate( self )
                sendZigateCmd(self, "0011", "" ) # Software Reset

            action['Name'] = 'Software reboot of Zigate'
            action['TimeStamp'] = int(time())
        _response["Data"] = json.dumps( action , sort_keys=True )
        return _response

    def rest_zigate( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            if self.zigatedata:
                _response["Data"] = json.dumps( self.zigatedata, sort_keys=True )
            else:
                fake_zigate = {}
                fake_zigate['Firmware Version'] = "fake - 0310"
                fake_zigate['IEEE'] = "00158d0001ededde"
                fake_zigate['Short Address'] = "0000"
                fake_zigate['Channel'] = "0b"
                fake_zigate['PANID'] = "51cf"
                fake_zigate['Extended PANID'] = "bd1247ec9d358634"

                _response["Data"] = json.dumps( fake_zigate , sort_keys=True )
        return _response


    def rest_domoticz_env( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                
                dzenv = {}
                #dzenv['proto'] = self.pluginconf.pluginConf['proto']
                #dzenv['host'] = self.pluginconf.pluginConf['host']
                dzenv['port'] = self.pluginconf.pluginConf['port']

                dzenv['WebUserName'] = self.WebUsername
                dzenv['WebPassword'] = self.WebPassword

                _response["Data"] = json.dumps( dzenv, sort_keys=True )
        return _response

    def rest_PluginEnv( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                _response["Data"] = json.dumps( self.pluginparameters, sort_keys=True )
        return _response

    def rest_netTopologie( self, verb, data, parameters):

        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkTopology-v3-' + '%02d' %self.hardwareID + '.json'
        self.logging( 'Debug', "Filename: %s" %_filename)

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = "{}"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if not os.path.isfile( _filename ) :
            _response['Data'] = json.dumps( {} , sort_keys=True ) 
            return _response

        # Read the file, as we have anyway to do it
        _topo = {}           # All Topo reports
        _timestamps_lst = [] # Just the list of Timestamps
        with open( _filename , 'rt') as handle:
            for line in handle:
                if line[0] != '{' and line[-1] != '}': continue
                entry = json.loads( line, encoding=dict )
                for _ts in entry:
                    _timestamps_lst.append( int(_ts) )
                    _topo[_ts] = [] # List of Father -> Child relation for one TimeStamp
                    _check_duplicate = []
                    _nwkid_list = []
                    reportLQI = entry[_ts]

                    for item in reportLQI:
                        self.logging( 'Debug', "Node: %s" %item)
                        if item != '0000' and item not in self.ListOfDevices:
                            continue
                        if item not in _nwkid_list:
                            _nwkid_list.append( item )
                        for x in  reportLQI[item]['Neighbours']:
                            self.logging( 'Debug', "---> %s" %x)
                            # Report only Child relationship
                            if x != '0000' and x not in self.ListOfDevices: continue
                            if item == x: continue
                            if 'Neighbours' not in reportLQI[item]:
                                Domoticz.Error("Missing attribute :%s for (%s,%s)" %('Neighbours', item, x))
                                continue

                            for attribute in ( '_relationshp', '_lnkqty', '_devicetype', '_depth' ):
                                if attribute not in reportLQI[item]['Neighbours'][x]:
                                    Domoticz.Error("Missing attribute :%s for (%s,%s)" %(attribute, item, x))
                                    continue
                            if x not in _nwkid_list:
                                _nwkid_list.append( x )
                            
                            # We need to reorganise in Father/Child relationship.
                            if reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Parent':
                                _father = item
                                _child  = x
                            elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Child':
                                _father = x
                                _child = item
                            elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Sibling':
                                _father = item
                                _child  = x
                            elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Former Child':
                                # Not a Parent, not a Child, not a Sibbling
                                #_father = item
                                #_child  = x
                                continue
                            elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'None':
                                # Not a Parent, not a Child, not a Sibbling
                                #_father = item
                                #_child  = x
                                continue
                        
                            _relation = {}
                            _relation['Father'] = _father
                            _relation['Child'] = _child
                            _relation["_lnkqty"] = int(reportLQI[item]['Neighbours'][x]['_lnkqty'], 16)
                            _relation["DeviceType"] = reportLQI[item]['Neighbours'][x]['_devicetype']

                            if _father != "0000":
                                if 'ZDeviceName' in self.ListOfDevices[_father]:
                                    if self.ListOfDevices[_father]['ZDeviceName'] != "" and self.ListOfDevices[_father]['ZDeviceName'] != {}:
                                        #_relation[master] = self.ListOfDevices[_father]['ZDeviceName']
                                        _relation['Father'] = self.ListOfDevices[_father]['ZDeviceName']
                            else:
                                _relation['Father'] = "Zigate"

                            if _child != "0000":
                                if 'ZDeviceName' in self.ListOfDevices[_child]:
                                    if self.ListOfDevices[_child]['ZDeviceName'] != "" and self.ListOfDevices[_child]['ZDeviceName'] != {}:
                                        #_relation[slave] = self.ListOfDevices[_child]['ZDeviceName']
                                        _relation['Child'] = self.ListOfDevices[_child]['ZDeviceName']
                            else:
                                _relation['Child'] = "Zigate"

                            # Sanity check, remove the direct loop
                            if ( _relation['Child'], _relation['Father'] ) in _check_duplicate:
                                self.logging( 'Debug', "Skip (%s,%s) as there is already ( %s, %s)" %(_relation['Father'], _relation['Child'], _relation['Child'], _relation['Father']))
                                continue
                            _check_duplicate.append( ( _relation['Father'], _relation['Child']))
                            self.logging( 'Debug', "%10s Relationship - %15.15s - %15.15s %3s %2s" \
                                %( _ts, _relation['Father'], _relation['Child'], _relation["_lnkqty"],
                                        reportLQI[item]['Neighbours'][x]['_depth']))
                            _topo[_ts].append( _relation )
                        #end for x
                    #end for item

                    # Sanity check, to see if all devices are part of the report.
                    # for iterDev in self.ListOfDevices:
                    #     if iterDev in _nwkid_list: continue
                    #     if 'Status' not in self.ListOfDevices[iterDev]: continue
                    #     if self.ListOfDevices[iterDev]['Status'] != 'inDB': continue
                    #    self.logging( 'Debug', "Nwkid %s has not been reported by this scan" %iterDev)
                    #    _relation = {}
                    #    _relation['Father'] = _relation['Child'] = iterDev
                    #    _relation['_lnkqty'] = 0
                    #    _relation['DeviceType'] = ''
                    #    if 'ZDeviceName' in self.ListOfDevices[iterDev]:
                    #        if self.ListOfDevices[iterDev]['ZDeviceName'] != "" and self.ListOfDevices[iterDev]['ZDeviceName'] != {}:
                    #            _relation['Father'] = _relation['Child'] = self.ListOfDevices[iterDev]['ZDeviceName']
                    #    _topo[_ts].append( _relation )

                #end for _st

        if verb == 'DELETE':
            if len(parameters) == 0:
                os.remove( _filename )
                action = {}
                action['Name'] = 'File-Removed'
                action['FileName'] = _filename
                _response['Data'] = json.dumps( action , sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _topo:
                    self.logging( 'Debug', "Removing Report: %s from %s records" %(timestamp, len(_topo)))
                    with open( _filename, 'r+') as handle:
                        d = handle.readlines()
                        handle.seek(0)
                        for line in d:
                            if line[0] != '{' and line[-1] != '}':
                                handle.write( line )
                                continue
                            entry = json.loads( line, encoding=dict )
                            entry_ts = entry.keys()
                            if len( entry_ts ) == 1:
                                if timestamp in entry_ts:
                                    self.logging( 'Debug', "--------> Skiping %s" %timestamp)
                                    continue
                            else:
                                continue
                            handle.write( line )
                        handle.truncate()

                    action = {}
                    action['Name'] = 'Report %s removed' %timestamp
                    _response['Data'] = json.dumps( action , sort_keys=True)
                else:
                    Domoticz.Error("Removing Topo Report %s not found" %timestamp )
                    _response['Data'] = json.dumps( [] , sort_keys=True)
            return _response

        elif verb == 'GET':
            if len(parameters) == 0:
                # Send list of Time Stamps
                _response['Data'] = json.dumps( _timestamps_lst , sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _topo:
                    self.logging( 'Debug', "Topologie sent: %s" %_topo[timestamp])
                    _response['Data'] = json.dumps( _topo[timestamp] , sort_keys=True)
                else:
                    _response['Data'] = json.dumps( [] , sort_keys=True)

        return _response

    def rest_nwk_stat( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkEnergy-v3-' + '%02d' %self.hardwareID + '.json'

        _timestamps_lst = [] # Just the list of Timestamps
        _scan = {}
        if os.path.isfile( _filename ) :
            self.logging( 'Debug', "Opening file: %s" %_filename)
            with open( _filename , 'rt') as handle:
                for line in handle:
                    if line[0] != '{' and line[-1] != '}': continue
                    entry = json.loads( line, encoding=dict )
                    for _ts in entry:
                        _timestamps_lst.append( _ts )
                        _scan[_ts] = entry[ _ts ]

        if verb == 'DELETE':
            if len(parameters) == 0:
                #os.remove( _filename )
                action = {}
                action['Name'] = 'File-Removed'
                action['FileName'] = _filename
                _response['Data'] = json.dumps( action , sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _timestamps_lst:
                    self.logging( 'Debug', "Removing Report: %s from %s records" %(timestamp, len(_timestamps_lst)))
                    with open( _filename, 'r+') as handle:
                        d = handle.readlines()
                        handle.seek(0)
                        for line in d:
                            if line[0] != '{' and line[-1] != '}':
                                handle.write( line )
                                continue
                            entry = json.loads( line, encoding=dict )
                            entry_ts = entry.keys()
                            if len( entry_ts ) == 1:
                                if timestamp in entry_ts:
                                    self.logging( 'Debug', "--------> Skiping %s" %timestamp)
                                    continue
                            else:
                                continue
                            handle.write( line )
                        handle.truncate()

                    action = {}
                    action['Name'] = 'Report %s removed' %timestamp
                    _response['Data'] = json.dumps( action , sort_keys=True)
                else:
                    Domoticz.Error("Removing Nwk-Energy %s not found" %timestamp )
                    _response['Data'] = json.dumps( [] , sort_keys=True)
            return _response
        elif verb == 'GET':
            if len(parameters) == 0:
                _response['Data'] = json.dumps( _timestamps_lst , sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _scan:
                    for r in _scan[timestamp]:
                        self.logging( "Debug", "report: %s" %r)
                        if r['_NwkId'] == '0000':
                            _response['Data'] = json.dumps( r['MeshRouters'], sort_keys=True )
                else:
                    _response['Data'] = json.dumps( [] , sort_keys=True)
        return _response

    def rest_plugin_restart( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            if self.WebUsername and self.WebPassword:
                url = 'http://%s:%s@127.0.0.1:%s' %(self.WebUsername, self.WebPassword, self.pluginconf.pluginConf['port'])
            else:
                url = 'http://127.0.0.1:%s' %self.pluginconf.pluginConf['port']
            url += '/json.htm?type=command&param=updatehardware&htype=94'
            url += '&idx=%s' %self.pluginparameters['HardwareID']

            url += '&name=%s' %self.pluginparameters['Name']
            url += '&address=%s' %self.pluginparameters['Address']
            url += '&port=%s' %self.pluginparameters['Port']
            url += '&serialport=%s' %self.pluginparameters['SerialPort']
            url += '&Mode1=%s' %self.pluginparameters['Mode1']
            url += '&Mode2=%s' %self.pluginparameters['Mode2']
            url += '&Mode3=%s' %self.pluginparameters['Mode3']
            url += '&Mode4=%s' %self.pluginparameters['Mode4']
            url += '&Mode5=%s' %self.pluginparameters['Mode5']
            url += '&Mode6=%s' %self.pluginparameters['Mode6']
            url += '&extra=%s' %self.pluginparameters['Key']
            url += '&enabled=true'
            url += '&datatimeout=0'

            info = {}
            info['Text'] = 'Plugin restarted'
            info['TimeStamp'] = int(time())
            _response["Data"] = json.dumps( info, sort_keys=True )

            Domoticz.Log("Plugin Restart command : %s" %url)
            _cmd = "/usr/bin/curl '%s' &" %url
            try:
                os.system( _cmd )
            except:
                Domoticz.Error("Error while trying to restart plugin %s" %_cmd)

        return _response
        
    def rest_restart_needed( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            _response["Data"] = json.dumps( self.restart_needed, sort_keys=True )
        return _response



    def rest_plugin_stat( self, verb, data, parameters):

        Statistics = {}
        self.logging( 'Debug', "self.statistics: %s" %self.statistics)
        self.logging( 'Debug', " --> Type: %s" %type(self.statistics))

        if self.pluginparameters['Mode1'] == 'None':
            Statistics['CRC'] = 1
            Statistics['FrameErrors'] = 1
            Statistics['Sent'] = 5
            Statistics['Received'] = 10
            Statistics['Cluster'] = 268
            Statistics['ReTx'] = 3
            Statistics['CurrentLoad'] = 1
            Statistics['MaxLoad'] = 7
            Statistics['APSAck'] = 100
            Statistics['APSNck'] =  0
            Statistics['StartTime'] = int(time()) - 120
            Statistics['Trend'] = [ ]
        else:
            Statistics['CRC'] =self.statistics._crcErrors
            Statistics['FrameErrors'] =self.statistics._frameErrors
            Statistics['Sent'] =self.statistics._sent
            Statistics['Received'] =self.statistics._received
            Statistics['Cluster'] =self.statistics._clusterOK
            Statistics['ReTx'] =self.statistics._reTx
            Statistics['APSFailure'] =self.statistics._APSFailure
            Statistics['APSAck'] =self.statistics._APSAck
            Statistics['APSNck'] =self.statistics._APSNck
            Statistics['CurrentLoad'] = len(self.ZigateComm.zigateSendingFIFO)
            Statistics['MaxLoad'] = self.statistics._MaxLoad
            Statistics['StartTime'] =self.statistics._start

            Statistics['Trend'] = []
            _nbitems = len(self.statistics.TrendStats)
            
            minTS = 0
            if  len(self.statistics.TrendStats) == 120:
                # Identify the smallest TS (we cannot assumed the list is sorted)
                minTS = 120
                for item in self.statistics.TrendStats:
                    if item['_TS'] < minTS:
                        minTS = item['_TS']
                minTS -= 1 # To correct as the dataset start at 1 (and not 0)

            # Renum
            for item in self.statistics.TrendStats:
                _TS = item['_TS'] 
                if _nbitems >= 120:
                    # Rolling window in progress
                    _TS -= minTS

                Statistics['Trend'].append( {"_TS":_TS, "Rxps": item['Rxps'],"Txps": item['Txps'], "Load": item['Load']} )

        Statistics['Uptime'] = int(time() - Statistics['StartTime'])
        Statistics['Txps'] = round(Statistics['Sent'] / Statistics['Uptime'], 2)
        Statistics['Txpm'] = round(Statistics['Sent'] / Statistics['Uptime'] * 60, 2)
        Statistics['Txph'] = round(Statistics['Sent'] / Statistics['Uptime'] * 3600, 2)
        Statistics['Rxps'] = round(Statistics['Received'] / Statistics['Uptime'], 2)
        Statistics['Rxpm'] = round(Statistics['Received'] / Statistics['Uptime'] * 60, 2)
        Statistics['Rxph'] = round(Statistics['Received'] / Statistics['Uptime'] * 3600, 2)

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                _response["Data"] = json.dumps( Statistics, sort_keys=True )
        return _response

    def rest_Settings( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if len(parameters) == 0:
                setting_lst = []
                for _theme in SETTINGS:
                    if _theme in ( 'PluginTransport'): continue
                    theme = {}
                    theme['_Order'] = SETTINGS[_theme]['Order']
                    theme['_Theme'] = _theme
                    theme['ListOfSettings'] = []
                    for param in self.pluginconf.pluginConf:
                        if param not in SETTINGS[_theme]['param']: continue
                        if not SETTINGS[_theme]['param'][param]['hidden']:
                            setting = {}
                            setting['Name'] = param
                            setting['default_value'] = SETTINGS[_theme]['param'][param]['default']
                            setting['DataType'] = SETTINGS[_theme]['param'][param]['type']
                            setting['restart_need'] = SETTINGS[_theme]['param'][param]['restart']
                            setting['Advanced'] = SETTINGS[_theme]['param'][param]['Advanced']
                            if SETTINGS[_theme]['param'][param]['type'] == 'hex':
                                Domoticz.Debug("--> %s: %s - %s" %(param, self.pluginconf.pluginConf[param], type(self.pluginconf.pluginConf[param])))
                                if isinstance( self.pluginconf.pluginConf[param], int):
                                    setting['current_value'] = '%x' %self.pluginconf.pluginConf[param] 
                                else:
                                    setting['current_value'] = '%x' %int(self.pluginconf.pluginConf[param] ,16)
                            else:
                                setting['current_value'] = self.pluginconf.pluginConf[param] 
                            theme['ListOfSettings'].append ( setting )
                    setting_lst.append( theme )
                _response["Data"] = json.dumps( setting_lst, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            data = data.decode('utf8')
            self.logging( 'Debug', "Data: %s" %data)
            data = data.replace('true','1')     # UI is coming with true and not True
            data = data.replace('false','0')   # UI is coming with false and not False

            setting_lst = eval(data)
            upd = False
            for setting in setting_lst:
                found = False
                self.logging( 'Debug', "setting: %s = %s" %(setting, setting_lst[setting]['current']))

                # Do we have to update ?
                for _theme in SETTINGS:
                    for param in SETTINGS[_theme]['param']:
                        if param != setting: continue
                        found = True
                        upd = True
                        if str(setting_lst[setting]['current']) == str(self.pluginconf.pluginConf[param]):
                            #Nothing to do
                            continue
                        self.logging( 'Debug', "Updating %s from %s to %s" %( param, self.pluginconf.pluginConf[param], setting_lst[setting]['current']))
                        if SETTINGS[_theme]['param'][param]['restart']:
                            self.restart_needed['RestartNeeded'] = True

                        if param == 'Certification':
                            if setting_lst[setting]['current'] in CERTIFICATION_CODE:
                                self.pluginconf.pluginConf['Certification'] = setting_lst[setting]['current']
                                self.pluginconf.pluginConf['CertificationCode'] = CERTIFICATION_CODE[setting_lst[setting]['current']]
                            else:
                                Domoticz.Error("Unknown Certification code %s (allow are CE and FCC)" %(setting_lst[setting]['current']))
                                continue

                        elif param == 'blueLedOnOff':
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]['current']:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if self.pluginconf.pluginConf[param]:
                                    zigateBlueLed( self, True)
                                else:
                                    zigateBlueLed( self, False)

                        elif param == 'EnableLedShutter':
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]['current']:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_ledShutter( self, 'On')
                                else:
                                    legrand_ledShutter( self, 'Off')


                        elif param == 'EnableLedInDark':
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]['current']:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_ledInDark( self, 'On')
                                else:
                                    legrand_ledInDark( self, 'Off')

                        elif param == 'EnableDimmer':
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_dimOnOff( self, 'On')
                                else:
                                    legrand_dimOnOff( self, 'Off')

                        elif param == 'EnableLedIfOn':
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_ledIfOnOnOff( self, 'On')
                                else:
                                    legrand_ledIfOnOnOff( self, 'Off')

                        elif param == 'debugMatchId':
                            if setting_lst[setting]['current'] == 'ffff':
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                            else:
                                self.pluginconf.pluginConf['debugMatchId'] = ""
                                matchID = setting_lst[setting]['current'].lower().split(',')
                                for key in matchID:
                                    if len(key) == 4:
                                        if key not in self.ListOfDevices:
                                            continue
                                        self.pluginconf.pluginConf['debugMatchId'] += key + ","
                                    if len(key) == 16:
                                        # Expect an IEEE
                                        if key not in self.IEEE2NWK:
                                            continue
                                        self.pluginconf.pluginConf['debugMatchId'] += self.IEEE2NWK[key] + ","
                                self.pluginconf.pluginConf['debugMatchId'] = self.pluginconf.pluginConf['debugMatchId'][:-1] # Remove the last ,
                        else:
                            if SETTINGS[_theme]['param'][param]['type'] == 'hex':
                                #Domoticz.Log("--> %s: %s - %s" %(param, self.pluginconf.pluginConf[param], type(self.pluginconf.pluginConf[param])))
                                self.pluginconf.pluginConf[param] = int(setting_lst[setting]['current'],16)
                            else:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']


                if not found:
                    Domoticz.Error("Unexpected parameter: %s" %setting)
                    _response["Data"] = { 'unexpected parameters %s' %setting }

                if upd:
                    # We need to write done the new version of PluginConf
                    self.pluginconf.write_Settings()
                    pass

            
        return _response

    def rest_PermitToJoin( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            duration = self.permitTojoin['Duration']
            timestamp = self.permitTojoin['Starttime']
            info = {}
            if self.permitTojoin['Duration'] == 255:
                info['PermitToJoin'] = 255
            elif self.permitTojoin['Duration'] == 0:
                info['PermitToJoin'] = 0
            elif int(time()) >= ( self.permitTojoin['Starttime'] + self.permitTojoin['Duration']):
                info['PermitToJoin'] = 0
            else:
                rest =  ( self.permitTojoin['Starttime'] + self.permitTojoin['Duration'] ) - int(time())
                self.logging( 'Debug', "remain %s s" %rest)
                info['PermitToJoin'] = rest

            _response["Data"] = json.dumps( info, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)
                self.logging( 'Debug', "parameters: %s value = %s" %( 'PermitToJoin', data['PermitToJoin']))
                if self.pluginparameters['Mode1'] != 'None':
                    ZigatePermitToJoin(self, int( data['PermitToJoin']))

        return _response

    def rest_Device( self, verb, data, parameters):

        _dictDevices = {}
        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response

            if len(parameters) == 0:
                # Return the Full List of ZIgate Domoticz Widget
                device_lst = []
                for x in self.Devices:
                    if len(self.Devices[x].DeviceID)  != 16:
                        continue
                    device_info = {}
                    device_info['_DeviceID'] = self.Devices[x].DeviceID
                    device_info['Name'] = self.Devices[x].Name
                    device_info['ID'] = self.Devices[x].ID
                    device_info['sValue'] = self.Devices[x].sValue
                    device_info['nValue'] = self.Devices[x].nValue
                    device_info['SignaleLevel'] = self.Devices[x].SignalLevel
                    device_info['BatteryLevel'] = self.Devices[x].BatteryLevel
                    device_info['TimedOut'] = self.Devices[x].TimedOut
                    #device_info['Type'] = self.Devices[x].Type
                    #device_info['SwitchType'] = self.Devices[x].SwitchType
                    device_lst.append( device_info )
                _response["Data"] = json.dumps( device_lst, sort_keys=True )

            elif len(parameters) == 1:
                for x in self.Devices:
                    if len(self.Devices[x].DeviceID)  != 16:
                        continue
                    if parameters[0] == self.Devices[x].DeviceID:
                        _dictDevices = {}
                        _dictDevices['_DeviceID'] = self.Devices[x].DeviceID
                        _dictDevices['Name'] = self.Devices[x].Name
                        _dictDevices['ID'] = self.Devices[x].ID
                        _dictDevices['sValue'] = self.Devices[x].sValue
                        _dictDevices['nValue'] = self.Devices[x].nValue
                        _dictDevices['SignaleLevel'] = self.Devices[x].SignalLevel
                        _dictDevices['BatteryLevel'] = self.Devices[x].BatteryLevel
                        _dictDevices['TimedOut'] = self.Devices[x].TimedOut
                        #_dictDevices['Type'] = self.Devices[x].Type
                        #_dictDevices['SwitchType'] = self.Devices[x].SwitchType
                        _response["Data"] = json.dumps( _dictDevices, sort_keys=True )
                        break
            else:
                device_lst = []
                for parm in parameters:
                    device_info = {}
                    for x in self.Devices:
                        if len(self.Devices[x].DeviceID)  != 16:
                            continue
                        if parm == self.Devices[x].DeviceID:
                            device_info = {}
                            device_info['_DeviceID'] = self.Devices[x].DeviceID
                            device_info['Name'] = self.Devices[x].Name
                            device_info['ID'] = self.Devices[x].ID
                            device_info['sValue'] = self.Devices[x].sValue
                            device_info['nValue'] = self.Devices[x].nValue
                            device_info['SignaleLevel'] = self.Devices[x].SignalLevel
                            device_info['BatteryLevel'] = self.Devices[x].BatteryLevel
                            device_info['TimedOut'] = self.Devices[x].TimedOut
                            #device_info['Type'] = self.Devices[x].Type
                            #device_info['SwitchType'] = self.Devices[x].SwitchType
                            device_lst.append( device_info )
                _response["Data"] = json.dumps( device_lst, sort_keys=True )
        return _response

    def rest_zGroup_lst_avlble_dev( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            device_lst = []
            _device =  {}
            _widget = {}
            _device['_NwkId'] = '0000'
            _device['WidgetList'] = []

            _widget['_ID'] =  ''
            _widget['Name'] =  ''
            _widget['IEEE'] =  '0000000000000000'
            _widget['Ep'] =  '01' 
            _widget['ZDeviceName'] =  'Zigate (Coordinator)'
            if self.zigatedata:
                if 'IEEE' in self.zigatedata:
                    _widget['IEEE'] =  self.zigatedata['IEEE'] 
                    _device['_NwkId'] = self.zigatedata['Short Address']

            _device['WidgetList'].append( _widget )
            device_lst.append( _device )

            for x in self.ListOfDevices:
                if x == '0000':  continue
                if 'MacCapa' not in self.ListOfDevices[x]:
                    self.logging( 'Debug', "rest_zGroup_lst_avlble_dev - no 'MacCapa' info found for %s!!!!" %x)
                    continue
                
                IkeaRemote = False
                if 'Type' in self.ListOfDevices[x]:
                    if self.ListOfDevices[x]['Type'] == 'Ikea_Round_5b':
                        IkeaRemote = True
                if self.ListOfDevices[x]['MacCapa'] != '8e' and not IkeaRemote:
                    self.logging( 'Debug', "rest_zGroup_lst_avlble_dev - %s not a Main Powered device. " %x)
                    continue

                if 'Ep' in self.ListOfDevices[x]:
                    if 'ZDeviceName' in self.ListOfDevices[x] and \
                          'IEEE' in self.ListOfDevices[x]:
                        _device = {}
                        _device['_NwkId'] = x
                        _device['WidgetList'] = []
                        for ep in self.ListOfDevices[x]['Ep']:
                            if 'Type' in self.ListOfDevices[x]:
                                if self.ListOfDevices[x]['Type'] == 'Ikea_Round_5b':
                                    if ep == '01':
                                        if 'ClusterType' in self.ListOfDevices[x]['Ep']['01']:
                                            widgetID = ''
                                            for iterDev in self.ListOfDevices[x]['Ep']['01']['ClusterType']:
                                                if self.ListOfDevices[x]['Ep']['01']['ClusterType'][iterDev] == 'Ikea_Round_5b':
                                                    widgetID = iterDev
                                                    for widget in self.Devices:
                                                        if self.Devices[widget].ID == int(widgetID):
                                                            _widget = {}
                                                            _widget['_ID'] =  self.Devices[widget].ID 
                                                            _widget['Name'] =  self.Devices[widget].Name 
                                                            _widget['IEEE'] =  self.ListOfDevices[x]['IEEE'] 
                                                            _widget['Ep'] =  ep 
                                                            _widget['ZDeviceName'] =  self.ListOfDevices[x]['ZDeviceName'] 
                                                            if _widget not in _device['WidgetList']:
                                                                _device['WidgetList'].append( _widget )
                                                            break
                                                    if _device not in device_lst:
                                                        device_lst.append( _device )
                                            continue # Next Ep
                            if '0004' not in self.ListOfDevices[x]['Ep'][ep] and \
                                ( 'ClusterType' not in self.ListOfDevices[x]['Ep'][ep] or 'ClusterType' not in self.ListOfDevices[x]) and \
                                '0006' not in self.ListOfDevices[x]['Ep'][ep] and \
                                '0008' not in  self.ListOfDevices[x]['Ep'][ep] and \
                                '0102' not in  self.ListOfDevices[x]['Ep'][ep]:
                                continue
                            if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep] or 'ClusterType' in self.ListOfDevices[x]:
                                if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]:
                                    clusterType= self.ListOfDevices[x]['Ep'][ep]['ClusterType']
                                else:
                                    clusterType = self.ListOfDevices[x]['ClusterType']

                                for widgetID in clusterType:
                                    if clusterType[widgetID] not in ( 'LvlControl', 'Switch', 'Plug', 
                                        "SwitchAQ2", "DSwitch", "Button", "DButton", 'LivoloSWL', 'LivoloSWR',
                                        'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl',
                                        'VenetianInverted', 'Venetian', 'WindowCovering' ):
                                        continue
                                    for widget in self.Devices:
                                        if self.Devices[widget].ID == int(widgetID):
                                            _widget = {}
                                            _widget['_ID'] =  self.Devices[widget].ID 
                                            _widget['Name'] =  self.Devices[widget].Name 
                                            _widget['IEEE'] =  self.ListOfDevices[x]['IEEE'] 
                                            _widget['Ep'] =  ep 
                                            _widget['ZDeviceName'] =  self.ListOfDevices[x]['ZDeviceName'] 
                                            if _widget not in _device['WidgetList']:
                                                _device['WidgetList'].append( _widget )

                if _device not in device_lst:
                    device_lst.append( _device )
            self.logging( 'Debug', "Response: %s" %device_lst)
            _response["Data"] = json.dumps( device_lst, sort_keys=True )
            return _response

    def rest_zDevice_name( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"

        if verb == 'GET':
            _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
            device_lst = []
            for x in self.ListOfDevices:
                if x == '0000': continue
                device = {}
                device['_NwkId'] = x

                for item in ( 'ZDeviceName', 'IEEE', 'Model', 'MacCapa', 'Status', 'ConsistencyCheck', 'Health', 'RSSI', 'Battery'):
                    if item in self.ListOfDevices[x]:
                        if item == 'MacCapa':
                            device['MacCapa'] = []
                            mac_capability = int(self.ListOfDevices[x][item],16)
                            AltPAN      =   ( mac_capability & 0x00000001 )
                            DeviceType  =   ( mac_capability >> 1 ) & 1
                            PowerSource =   ( mac_capability >> 2 ) & 1
                            ReceiveonIdle = ( mac_capability >> 3 ) & 1
                            if DeviceType == 1 :
                                device['MacCapa'].append("FFD")
                            else :
                                device['MacCapa'].append("RFD")
                            if ReceiveonIdle == 1 :
                                device['MacCapa'].append("RxonIdle")
                            if PowerSource == 1 :
                                device['MacCapa'].append("MainPower")
                            else :
                                device['MacCapa'].append("Battery")
                            self.logging( 'Debug', "decoded MacCapa from: %s to %s" %(self.ListOfDevices[x][item], str(device['MacCapa'])))
                        else:
                            if self.ListOfDevices[x][item] != {}:
                                device[item] = self.ListOfDevices[x][item]
                            else:
                                device[item] = ''
                    else:
                        device[item] = ''

                device['WidgetList'] = []
                for ep in self.ListOfDevices[x]['Ep']:
                    if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep] or 'ClusterType' in self.ListOfDevices[x]:
                        if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]:
                            clusterType= self.ListOfDevices[x]['Ep'][ep]['ClusterType']
                        else:
                            clusterType = self.ListOfDevices[x]['ClusterType']
                        for widgetID in clusterType:
                            for widget in self.Devices:
                                if self.Devices[widget].ID == int(widgetID):
                                    self.logging( 'Debug', "Widget Name: %s %s" %(widgetID, self.Devices[widget].Name))
                                    if self.Devices[widget].Name not in device['WidgetList']:
                                        device['WidgetList'].append( self.Devices[widget].Name )

                if device not in device_lst:
                    device_lst.append( device )
            #_response["Data"] = json.dumps( device_lst, sort_keys=True )
            self.logging( 'Debug', "zDevice_name - sending %s" %device_lst)
            _response["Data"] = json.dumps( device_lst, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            data = data.decode('utf8')
            self.logging( 'Debug', "Data: %s" %data)
            data = eval(data)
            for x in data:
                if 'ZDeviceName' in x and 'IEEE' in x:
                    for dev in self.ListOfDevices:
                        if self.ListOfDevices[dev]['IEEE'] == x['IEEE'] and \
                                self.ListOfDevices[dev]['ZDeviceName'] != x['ZDeviceName']:
                            self.ListOfDevices[dev]['ZDeviceName'] = x['ZDeviceName']
                            self.logging( 'Debug', "Updating ZDeviceName to %s for IEEE: %s NWKID: %s" \
                                    %(self.ListOfDevices[dev]['ZDeviceName'], self.ListOfDevices[dev]['IEEE'], dev))
                else:
                    Domoticz.Error("wrong data received: %s" %data)

        elif verb == 'DELETE':
            if len(parameters) == 1:
                deviceId = parameters[0]
                if len( deviceId ) == 4: # Short Network Addr
                    if deviceId not in self.ListOfDevices:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown LOD" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    nwkid = deviceId
                    ieee = self.ListOfDevices[deviceId]['IEEE']
                else:
                    if deviceId not in self.IEEE2NWK:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown in IEEE22NWK" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    ieee = deviceId
                    nwkid = self.IEEE2NWK[ ieee ]
                
                del self.ListOfDevices[ nwkid ]
                del self.IEEE2NWK[ ieee ]
                # for a remove in case device didn't send the leave
                if 'IEEE' in self.zigatedata:
                    sendZigateCmd(self, "0026", self.zigatedata['IEEE'] + deviceId )

                action = {}
                action['Name'] = 'Device %s/%s removed' %(nwkid, ieee)
                _response['Data'] = json.dumps( action , sort_keys=True)

        return _response

    def rest_zDevice( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'DELETE':
            if len(parameters) == 1:
                deviceId = parameters[0]
                if len( deviceId ) == 4: # Short Network Addr
                    if deviceId not in self.ListOfDevices:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown LOD" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    nwkid = deviceId
                    ieee = self.ListOfDevice[deviceId]['IEEE']
                else:
                    if deviceId not in self.IEEE2NWK:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown in IEEE22NWK" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    ieee = deviceId
                    nwkid = self.IEEE2NWK[ ieee ]
                
                del self.ListOfDevice[ nwkid ]
                del self.IEEE2NWK[ ieee ]
                action = {}
                action['Name'] = 'Device %s/%s removed' %(nwkid, ieee)
                _response['Data'] = json.dumps( action , sort_keys=True)
            return _response

        elif verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                zdev_lst = []
                for item in self.ListOfDevices:
                    if item == '0000': continue
                    device = {}
                    device['_NwkId'] = item
                    # Main Attributes
                    for attribut in ( 'ZDeviceName', 'ConsistencyCheck', 'Stamp', 'Health', 'Status', 'Battery', 'RSSI', 'Model', 'IEEE', 'ProfileID', 'ZDeviceID', 'Manufacturer', 'DeviceType', 'LogicalType', 'PowerSource', 'ReceiveOnIdle', 'App Version', 'Stack Version', 'HW Version' ):

                        if attribut in self.ListOfDevices[item]:
                            if self.ListOfDevices[item][attribut] == {}:
                                device[attribut] = ''
                            elif self.ListOfDevices[item][attribut] == '' and self.ListOfDevices[item]['MacCapa'] == '8e':
                                if attribut == 'DeviceType':
                                    device[attribut] = 'FFD'
                                elif attribut == 'LogicalType':
                                    device[attribut] = 'Router'
                                elif attribut == 'PowerSource':
                                    device[attribut] = 'Main'
                            else:
                                device[attribut] = self.ListOfDevices[item][attribut]
                        else:
                            device[attribut] = ''

                    # Last Seen Information
                    device['LastSeen'] = ''
                    if 'Stamp' in self.ListOfDevices[item]:
                        if 'LastSeen' in self.ListOfDevices[item]['Stamp']:
                            device['LastSeen'] = self.ListOfDevices[item]['Stamp']['LastSeen']

                    # ClusterType
                    _widget_lst = []
                    if 'ClusterType' in self.ListOfDevices[item]:
                        for widgetId in self.ListOfDevices[item]['ClusterType']:
                            widget = {}
                            widget['_WidgetID'] = widgetId
                            widget['WidgetName'] = ''
                            for x in self.Devices:
                                if self.Devices[x].ID == int(widgetId):
                                    widget['WidgetName'] = self.Devices[x].Name
                                    break
                            widget['WidgetType'] = self.ListOfDevices[item]['ClusterType'][widgetId]
                            _widget_lst.append( widget )

                    # Ep informations
                    ep_lst = []
                    if 'Ep' in self.ListOfDevices[item]:
                        for epId in self.ListOfDevices[item]['Ep']:
                            _ep = {}
                            _ep['Ep'] = epId
                            _ep['ClusterList'] = []
                            for cluster in self.ListOfDevices[item]['Ep'][epId]:
                                if cluster == 'ColorMode': continue
                                if cluster == 'Type':
                                    device['Type'] = self.ListOfDevices[item]['Ep'][epId]['Type']
                                    continue
                                if cluster == 'ClusterType':
                                    for widgetId in self.ListOfDevices[item]['Ep'][epId]['ClusterType']:
                                        widget = {}
                                        widget['_WidgetID'] = widgetId
                                        widget['WidgetName'] = ''
                                        for x in self.Devices:
                                            if self.Devices[x].ID == int(widgetId):
                                                widget['WidgetName'] = self.Devices[x].Name
                                                break
                                        widget['WidgetType'] = self.ListOfDevices[item]['Ep'][epId]['ClusterType'][widgetId]
                                        _widget_lst.append( widget )
                                    continue
                                _cluster = {}
                                if cluster in ZCL_CLUSTERS_LIST:
                                    _cluster[cluster] = ZCL_CLUSTERS_LIST[cluster]
                                else:
                                    _cluster[cluster] = "Unknown"
                                _ep['ClusterList'].append( _cluster )

                            ep_lst.append ( _ep )
                    device['Ep'] = ep_lst
                    device['WidgetList'] = _widget_lst

                    # Last Commands
                    lastcmd_lst = []
                    if 'Last Cmds' in self.ListOfDevices[item]:
                        for lastCmd in self.ListOfDevices[item]['Last Cmds']:
                            timestamp = lastCmd[0]
                            cmd = lastCmd[1]
                            #payload = lastCmd[2]
                            _cmd = {}
                            _cmd['CmdCode'] = cmd
                            _cmd['TimeStamps'] =  timestamp
                            lastcmd_lst.append( _cmd )
                    device['LastCmds'] = lastcmd_lst
                    zdev_lst.append( device )

                _response["Data"] = json.dumps( zdev_lst, sort_keys=True )
        return _response


    def rest_zDevice_raw( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                zdev_lst = []
                for item in self.ListOfDevices:
                    entry = dict(self.ListOfDevices[item])
                    entry['NwkID'] = item
                    zdev_lst.append(entry)
                _response["Data"] = json.dumps( zdev_lst, sort_keys=False )
            elif len(parameters) == 1:
                if parameters[0] in self.ListOfDevices:
                    _response["Data"] =  json.dumps( self.ListOfDevices[parameters[0]], sort_keys=False ) 
                elif parameters[0] in self.IEEE2NWK:
                    _response["Data"] =  json.dumps( self.ListOfDevices[self.IEEE2NWK[parameters[0]]], sort_keys=False ) 

        return _response

    def rest_zGroup( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        self.logging( 'Debug', "rest_zGroup - ListOfGroups = %s" %str(self.groupmgt))

        if verb == 'GET':
            if self.groupmgt is None:
                return _response
            ListOfGroups = self.groupmgt.ListOfGroups
            if ListOfGroups is None or len(ListOfGroups) == 0:
                return _response

            if len(parameters) == 0:
                zgroup_lst = []
                for itergrp in ListOfGroups:
                    self.logging( 'Debug', "Process Group: %s" %itergrp)
                    zgroup = {}
                    zgroup['_GroupId'] = itergrp
                    zgroup['GroupName'] = ListOfGroups[itergrp]['Name']
                    zgroup['Devices'] = []
                    for itemDevice in ListOfGroups[itergrp]['Devices']:
                        if len(itemDevice) == 2:
                            dev, ep = itemDevice
                            ieee = self.ListOfDevices[dev]['IEEE']
                        elif len(itemDevice) == 3:
                            dev, ep, ieee = itemDevice
                        self.logging( 'Debug', "--> add %s %s %s" %(dev, ep, ieee))
                        _dev = {}
                        _dev['_NwkId'] = dev
                        _dev['Ep'] = ep
                        _dev['IEEE'] = ieee
                        zgroup['Devices'].append( _dev )

                    if 'WidgetStyle' in ListOfGroups[itergrp]:
                        zgroup['WidgetStyle'] = ListOfGroups[itergrp]['WidgetStyle']
                    if 'Cluster' in ListOfGroups[itergrp]:
                        zgroup['Cluster'] = ListOfGroups[itergrp]['Cluster']

                    # Let's check if we don't have an Ikea Remote in the group
                    if 'Tradfri Remote' in ListOfGroups[itergrp]:
                        self.logging( 'Debug', "--> add Ikea Tradfri Remote")
                        _dev = {}
                        _dev['_NwkId'] = ListOfGroups[itergrp]["Tradfri Remote"]["Device Addr"]
                        _dev['Ep'] = "01"
                        zgroup['Devices'].append( _dev )
                    zgroup_lst.append(zgroup)
                self.logging( 'Debug', "zGroup: %s" %zgroup_lst)
                _response["Data"] = json.dumps( zgroup_lst, sort_keys=True )

            elif len(parameters) == 1:
                if parameters[0] in ListOfGroups:
                    itemGroup =  parameters[0]
                    zgroup = {}
                    zgroup['_GroupId'] = itemGroup
                    zgroup['GroupName'] = ListOfGroups[itemGroup]['Name']
                    zgroup['Devices'] = {}
                    for itemDevice in ListOfGroups[itemGroup]['Devices']:
                        if len(itemDevice) == 2:
                            dev, ep = itemDevice
                            _ieee = self.ListOfDevices[dev]['IEEE']
                        elif len(itemDevice) == 3:
                            dev, ep, _ieee = itemDevice
                        self.logging( 'Debug', "--> add %s %s" %(dev, ep))
                        zgroup['Devices'][dev] = ep 
                    # Let's check if we don't have an Ikea Remote in the group
                    if 'Tradfri Remote' in ListOfGroups[itemGroup]:
                        self.logging( 'Log', "--> add Ikea Tradfri Remote")
                        _dev = {}
                        _dev['_NwkId'] = ListOfGroups[itemGroup]["Tradfri Remote"]["Device Addr"]
                        _dev['Ep'] = "01"
                        zgroup['Devices'].append( _dev )
                    _response["Data"] = json.dumps( zgroup, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            if  not self.groupmgt:
                Domoticz.Error("Looks like Group Management is not enabled")
                _response["Data"] = {}
                return _response

            ListOfGroups = self.groupmgt.ListOfGroups
            grp_lst = []
            if len(parameters) == 0:
                self.restart_needed['RestartNeeded'] = True
                data = data.decode('utf8')
                data = json.loads(data)
                self.logging( 'Debug', "data: %s" %data)
                for item in data:
                    self.logging( 'Debug', "item: %s" %item)
                    if '_GroupId' not in item:
                        self.logging( 'Debug', "--->Adding Group: ")
                        # Define a GroupId 
                        for x in range( 0x0001, 0x0999):
                            grpid = '%04d' %x
                            if grpid not in ListOfGroups:
                                break
                        else:
                            Domoticz.Error("Out of GroupId")
                            continue
                        ListOfGroups[grpid] = {}
                        ListOfGroups[grpid]['Name'] = item['GroupName']
                        ListOfGroups[grpid]['Devices'] = []
                    else:
                        if item['_GroupId'] not in ListOfGroups:
                            Domoticz.Error("zGroup REST API - unknown GroupId: %s" %grpid)
                            continue
                        grpid = item['_GroupId']

                    grp_lst.append( grpid ) # To memmorize the list of Group
                    #Update Group
                    self.logging( 'Debug', "--->Checking Group: %s" %grpid)
                    if item['GroupName'] != ListOfGroups[grpid]['Name']:
                        # Update the GroupName
                        self.logging( 'Debug', "------>Updating Group from :%s to : %s" %( ListOfGroups[grpid]['Name'], item['GroupName']))
                        self.groupmgt._updateDomoGroupDeviceWidgetName( item['GroupName'], grpid )

                    newdev = []
                    if 'devicesSelected' not in item:
                        continue
                    if 'GroupName' in item:
                        if item['GroupName'] == '':
                            continue
                    for devselected in item['devicesSelected']:
                        if 'IEEE' in devselected:
                            ieee = devselected['IEEE']
                        elif '_NwkId' in devselected:
                            nwkid = devselected['_NwkId']
                            if nwkid != '0000' and nwkid not in self.ListOfDevices:
                                Domoticz.Error("Not able to find nwkid: %s" %(nwkid))
                                continue
                            if 'IEEE' not in self.ListOfDevices[nwkid]:
                                Domoticz.Error("Not able to find IEEE for %s - no IEEE entry in %s" %(nwkid, self.ListOfDevices[nwkid]))
                                continue
                            ieee = self.ListOfDevices[nwkid]['IEEE']
                        else: 
                            Domoticz.Error("Not able to find IEEE for %s" %(_dev))
                            continue
                        self.logging( 'Debug', "------>Checking device : %s/%s" %(devselected['_NwkId'], devselected['Ep']))
                        # Check if this is not an Ikea Tradfri Remote
                        nwkid = devselected['_NwkId']
                        _tradfri_remote = False
                        if 'Ep' in self.ListOfDevices[nwkid]:
                            if '01' in self.ListOfDevices[nwkid]['Ep']:
                                if 'ClusterType' in self.ListOfDevices[nwkid]['Ep']['01']:
                                    for iterDev in self.ListOfDevices[nwkid]['Ep']['01']['ClusterType']:
                                        if self.ListOfDevices[nwkid]['Ep']['01']['ClusterType'][iterDev] == 'Ikea_Round_5b':
                                            # We should not process it through the group.
                                            self.logging( 'Debug', "------>Not processing Ikea Tradfri as part of Group. Will enable the Left/Right actions")
                                            ListOfGroups[grpid]['Tradfri Remote'] = {}
                                            ListOfGroups[grpid]['Tradfri Remote']['Device Addr'] = nwkid
                                            ListOfGroups[grpid]['Tradfri Remote']['Device Id'] = iterDev
                                            _tradfri_remote = True
                        if _tradfri_remote:
                            continue
                        # Process the rest
                        for itemDevice in ListOfGroups[grpid]['Devices']:
                            if len(itemDevice) == 2:
                                _dev, _ep = itemDevice
                                _ieee = self.ListOfDevices[dev]['IEEE']
                            elif len(itemDevice) == 3:
                                _dev, _ep, _ieee = itemDevice

                            if _dev == devselected['_NwkId'] and _ep == devselected['Ep']:
                                if (ieee, _ep) not in newdev:
                                    self.logging( 'Debug', "------>--> %s to be added to group %s" %( (ieee, _ep), grpid))
                                    newdev.append( (ieee, _ep) )
                                else:
                                    self.logging( 'Debug', "------>--> %s already in %s" %( (ieee, _ep), newdev))
                                break
                        else:
                            if (ieee, devselected['Ep']) not in newdev:
                                self.logging( 'Debug', "------>--> %s to be added to group %s" %( (ieee, devselected['Ep']), grpid))
                                newdev.append( (ieee, devselected['Ep']) )
                            else:
                                self.logging( 'Debug', "------>--> %s already in %s" %( (_dev, _ep), newdev))
                    # end for devselecte

                    if 'coordinatorInside' in item:
                        if item['coordinatorInside']:
                            if 'IEEE' in self.zigatedata:
                                ieee_zigate = self.zigatedata['IEEE']
                                if ( ieee_zigate, '01') not in newdev:
                                    self.logging( 'Debug', "------>--> %s to be added to group %s" %( (ieee_zigate, '01'), grpid))
                                    newdev.append( (ieee_zigate, _ep) )

                    self.logging( 'Debug', "--->Devices Added: %s" %newdev)
                    ListOfGroups[grpid]['Imported'] = list( newdev )
                    self.logging( 'Debug', "--->Grp: %s - tobe Imported: %s" %(grpid, ListOfGroups[grpid]['Imported']))

                # end for item / next group
                # Finaly , we need to check if AnyGroup have been removed !
                self.logging( 'Debug', "Group to be removed")
                Domoticz.Log("ListOfGroups: %s" %ListOfGroups)
                for grpid in ListOfGroups:
                    if grpid not in grp_lst:
                        self.logging( 'Debug', "--->Group %s has to be removed" %grpid)
                        if 'Imported' in ListOfGroups[grpid]:
                            del ListOfGroups[grpid]['Imported']
                        ListOfGroups[grpid]['Imported'] = []

                self.logging( 'Debug', "Group to be worked out")
                for grpid in ListOfGroups:
                    self.logging( 'Debug', "Group: %s" %grpid)
                    if 'Imported' in ListOfGroups[grpid]:
                        for dev in ListOfGroups[grpid]['Imported']:
                            self.logging( 'Debug', "---> %s to be imported" %str(dev))

                self.groupmgt.write_jsonZigateGroupConfig()
            # end if len()
        # end if Verb=

        return _response

    def rest_bindLSTcluster( self, verb, data, parameters):
        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        bindCluster = []
        for key in self.ListOfDevices:
            if key == '0000': continue
            for ep in self.ListOfDevices[key]['Ep']:
                for cluster in self.ListOfDevices[key]['Ep'][ep]:
                    if cluster in ZCL_CLUSTERS_ACT:
                        if cluster not in bindCluster:
                            bindCluster.append( cluster )
        _response["Data"] = json.dumps( bindCluster )
        return _response

    def rest_bindLSTdevice( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if len(parameters) == 1:
            listofdevices = []
            clustertobind = parameters[0]
            for key in self.ListOfDevices:
                if key == '0000': continue
                for ep in self.ListOfDevices[key]['Ep']:
                    if clustertobind in self.ListOfDevices[key]['Ep'][ep]:
                        dev={}
                        dev['IEEE'] = self.ListOfDevices[key]['IEEE']
                        dev['NwkId'] = key
                        dev['Ep'] = ep
                        dev['ZDeviceName'] = self.ListOfDevices[key]['ZDeviceName']
                        if dev not in listofdevices:
                            listofdevices.append( dev )
            _response["Data"] = json.dumps( listofdevices )
        else:
            Domoticz.Error("Must have 1 argument. %s" %parameters)
        return _response


    def rest_binding( self, verb, data, parameters):
        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)

                if 'sourceIeee' not in data and \
                        'sourceEp' not in data and \
                        'destIeee' not in data and \
                        'destEp' not in data and \
                        'cluster' not in data:
                    Domoticz.Log("-----> uncomplet json %s" %data)
                    _response["Data"] = json.dumps("uncomplet json %s" %data)
                    return _response

                self.logging( 'Log', "rest_binding - Source: %s/%s Dest: %s/%s Cluster: %s" %(data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster']))
                webBind( self, data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster'] )
                _response["Data"] = json.dumps( "Binding cluster %s between %s/%s and %s/%s" %(data['cluster'], data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp']))
                return _response

    def rest_unbinding( self, verb, data, parameters):
        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)

                if 'sourceIeee' not in data and \
                        'sourceEp' not in data and \
                        'destIeee' not in data and \
                        'destEp' not in data and \
                        'cluster' not in data:
                    Domoticz.Log("-----> uncomplet json %s" %data)
                    _response["Data"] = json.dumps("uncomplet json %s" %data)
                    return _response

                self.logging( 'Log', "rest_unbinding - Source: %s/%s Dest: %s/%s Cluster: %s" %(data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster']))
                webUnBind( self, data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster'] )
                _response["Data"] = json.dumps( "Binding cluster %s between %s/%s and %s/%s" %(data['cluster'], data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp']))
                return _response

    def rest_raw_command( self, verb, data, parameters):

        Domoticz.Log("raw_command - %s %s" %(verb, data))
        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)
                Domoticz.Log("---> Data: %s" %str(data))
                if 'Command' not in data and 'payload' not in data:
                    Domoticz.Error("Unexpected request: %s" %data)
                    _response["Data"] = json.dumps( "Executing %s on %s" %(data['Command'], data['payload']) )
                    return _response
                msgtype = int( data['Command'] , 16 )
                if msgtype not in ZIGATE_COMMANDS:
                    Domoticz.Error("raw_command - Unknown MessageType received %s" %msgtype)
                    _response["Data"] = json.dumps( "Unknown MessageType received %s" %msgtype)
                    return _response
                
                cmd = data['Command']
                payload = data['payload']
                if payload == None:
                    payload = ""
                sendZigateCmd( self, data['Command'], data['payload'])
                self.logging( 'Log', "rest_dev_command - Command: %s payload %s" %(data['Command'], data['payload']))
                _response["Data"] = json.dumps( "Executing %s on %s" %(data['Command'], data['payload']) ) 

        return _response

    def rest_dev_command( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)
                Domoticz.Log("---> Data: %s" %str(data))
                self.logging( 'Log', "rest_dev_command - Command: %s on object: %s with extra %s %s" %(data['Command'], data['NwkId'], data['Value'],  data['Color']))
                _response["Data"] = json.dumps( "Executing %s on %s" %(data['Command'], data['NwkId']) ) 
                if 'Command' not in data:
                    return _response
                if data['Command'] == '':
                    return _response
                if data['Value'] == '' or data['Value'] is None:
                    Level = 0
                else:
                    if is_hex(str(data['Value'])):
                        Level = int(str(data['Value']),16)
                    else:
                        Level = int(str(data['Value']))
                ColorMode = ColorValue = ''
                color = ''
                if data['Color'] == '' or data['Color'] is None:
                    Hue_List = {}
                    Color = json.dumps( Hue_List )
                else:
                    # Decoding RGB
                    # rgb(30,96,239)
                    ColorMode = data['Color'].split('(')[0]
                    ColorValue = data['Color'].split('(')[1].split(')')[0]
                    if ColorMode == 'rgb':
                        Hue_List = {}
                        Hue_List['m'] = 3
                        Hue_List['r'], Hue_List['g'], Hue_List['b'] = ColorValue.split(',') 
                    self.logging( 'Log', "rest_dev_command -        Color decoding m: %s r:%s g: %s b: %s"  %(Hue_List['m'], Hue_List['r'], Hue_List['g'], Hue_List['b']))
                    Color = json.dumps( Hue_List )



                epout = '01'
                if 'Type' not in data:
                    actuators( self,  data['Command'], data['NwkId'], epout , 'Switch')
                else:
                    SWITCH_2_CLUSTER = { 'Switch':'0006',
                        'LivoloSWL':'0006',
                        'LivoloSWR':'0006',
                        'LvlControl':'0008',
                        'WindowCovering':'0102',
                        'ThermoSetpoint':'0201',
                        'ColorControlRGBWW':'0300',
                        'ColorControlWW':'0300',
                        'ColorControlRGB':'0300'}

                    key = data['NwkId']
                    if data['Type'] is None:
                        clusterCode = '0003'
                    else:
                        clusterCode = SWITCH_2_CLUSTER[ data['Type'] ]

                    for tmpEp in self.ListOfDevices[data['NwkId']]['Ep']:
                        if clusterCode  in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                            epout=tmpEp
                    actuators( self,  data['Command'], key, epout , data['Type'], value=Level, color=Color)

        return _response

    def rest_dev_capabilities( self, verb, data, parameters):

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                Domoticz.Error("rest_dev_capabilities - expecting a device id! %s" %(parameters))
                return _response
            elif len(parameters) == 1:
                if parameters[0] not in self.ListOfDevices and parameters[0] not in self.IEEE2NWK:
                    Domoticz.Error("rest_dev_capabilities - Device %s doesn't exist" %(parameters[0]))
                    return _response
                # Check Capabilities
                CLUSTER_INFOS = {
                        '0003': [ 
                            { 'actuator': 'Identify', 'Value': '', 'Type': ( ) },
                            { 'actuator': 'IdentifyEffect', 'Value': 'hex', 'Type': ( ) },
                        ],
                        '0006': [
                            { 'actuator': 'On', 'Value':'', 'Type': ( 'Switch',) },
                            { 'actuator': 'Off', 'Value':'', 'Type': ( 'Switch', ) },
                            { 'actuator': 'Toggle', 'Value':'', 'Type': ( 'Switch', ) },
                        ],
                        '0008': [
                            { 'actuator': 'SetLevel', 'Value':'int', 'Type': ( 'LvlControl',) },
                        ],
                        '0102': [
                            { 'actuator': 'On', 'Value':'', 'Type': ( 'WindowCovering',) },
                            { 'actuator': 'Off', 'Value':'', 'Type': ( 'WindowCovering',) },
                            { 'actuator': 'Stop', 'Value':'', 'Type': ( 'WindowCovering',) },
                            { 'actuator': 'SetLevel', 'Value':'hex', 'Type': ( 'WindowCovering',) },
                        ],
                        '0201': [
                            { 'actuator': 'SetPoint', 'Value':'hex', 'Type': ( 'ThermoSetpoint',) },
                        ],
                        '0300': [
                            { 'actuator': 'SetColor', 'Value':'rgbww', 'Type': ( 'ColorControlRGBWW', 'ColorControlWW', 'ColorControlRGB') },
                        ]

                    }
                dev_capabilities = {}
                dev_capabilities['NwkId'] = {}
                dev_capabilities['Capabilities'] = []
                dev_capabilities['Types'] = []
                if  parameters[0] in self.ListOfDevices:
                    _nwkid = parameters[0]
                elif parameters[0] in self.IEEE2NWK:
                    _nwkid = self.IEEE2NWK[parameters[0]]
                dev_capabilities['NwkId'] = _nwkid

                for ep in self.ListOfDevices[ _nwkid ]['Ep']:
                    for cluster in self.ListOfDevices[ _nwkid ]['Ep'][ ep ]:
                        if cluster in CLUSTER_INFOS:
                            for action in CLUSTER_INFOS[cluster]:
                                _capabilitie = {}
                                _capabilitie['actuator'] = action['actuator']
                                if action['Value'] == '':
                                    _capabilitie['Value'] = False
                                else: 
                                    _capabilitie['Value'] = action['Value']
                                if len( action['Type']):
                                    _capabilitie['Type'] = True
                                else:
                                    _capabilitie['Type'] = False
                                dev_capabilities['Capabilities'].append( _capabilitie )

                                for cap in action['Type']:
                                    if cap not in dev_capabilities['Types']:
                                        dev_capabilities['Types'].append( cap )

                                # Adding non generic Capabilities
                                if 'Model' in self.ListOfDevices[ _nwkid ]:
                                    if self.ListOfDevices[ _nwkid ]['Model'] != {}:
                                        if self.ListOfDevices[ _nwkid ]['Model'] =='TI0001':
                                            if 'LivoloSWL' not in dev_capabilities['Types']:
                                                dev_capabilities['Types'].append( 'LivoloSWL' )
                                            if 'LivoloSWR' not in dev_capabilities['Types']:
                                                dev_capabilities['Types'].append( 'LivoloSWR' )

                _response["Data"] = json.dumps( dev_capabilities )
                return _response


    def rest_new_hrdwr( self, verb, data, parameters):

        """
        This is call to Enable/Disable a Provisioning process. As a toggle you will enable the provisioning or disable it
        it will return either Enable or Disable
        """

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            data = {}
            if len(parameters) != 1:
                Domoticz.Error("rest_new_hrdwr - unexpected parameter %s " %parameters)
                _response["Data"] = { "unexpected parameter %s " %parameters}
                return _response

            if parameters[0] not in ( 'enable', 'cancel', 'disable' ):
                Domoticz.Error("rest_new_hrdwr - unexpected parameter %s " %parameters[0])
                _response["Data"] = { "unexpected parameter %s " %parameters[0] }
                return _response
            if parameters[0] == 'enable':
                Domoticz.Log("Enable Assisted pairing")
                if len(self.DevicesInPairingMode):
                    del self.DevicesInPairingMode
                    self.DevicesInPairingMode = []
                if not self.zigatedata:
                    # Seems we are in None mode - Testing for ben
                    self.fakeDevicesInPairingMode = 0

                if self.permitTojoin['Duration'] != 255 and self.pluginparameters['Mode1'] != 'None':
                    ZigatePermitToJoin(self, ( 4 * 60 ))

                _response["Data"] = { "start pairing mode at %s " %int(time()) }
                return _response

            elif parameters[0] in ( 'cancel', 'disable'):
                Domoticz.Log("Disable Assisted pairing")
                if len(self.DevicesInPairingMode):
                    del self.DevicesInPairingMode
                    self.DevicesInPairingMode = []
                if not self.zigatedata:
                    # Seems we are in None mode - Testing for ben
                    self.fakeDevicesInPairingMode = 0
                if self.permitTojoin['Duration'] != 255 and self.pluginparameters['Mode1'] != 'None':
                    ZigatePermitToJoin(self, 0)

                _response["Data"] = { "stop pairing mode at %s " %int(time()) }
                return _response

    def rest_rcv_nw_hrdwr( self, verb, data, parameters):

        """
        Will return a status on the provisioning process. Either Enable or Disable and in case there is a new device provisionned
        during the period, it will return the information captured.
        """

        _response = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            data = {}
            data['NewDevices'] = []

            if not self.zigatedata:
                # Seems we are in None mode - Testing for ben
                if self.fakeDevicesInPairingMode in ( 0, 1):
                    # Do nothing just wait the next pool
                    self.fakeDevicesInPairingMode += 1
                    _response["Data"] = json.dumps( data )
                    return _response

                elif self.fakeDevicesInPairingMode in ( 2, 3 ):
                    self.fakeDevicesInPairingMode += 1
                    newdev = {}
                    newdev['NwkId'] = list(self.ListOfDevices.keys())[0]
                    data['NewDevices'].append( newdev )
                    _response["Data"] = json.dumps( data )
                    return _response

                elif self.fakeDevicesInPairingMode in ( 4, 5 ):
                    self.fakeDevicesInPairingMode += 1
                    newdev = {}
                    newdev['NwkId'] = list(self.ListOfDevices.keys())[0]
                    data['NewDevices'].append( newdev )
                    newdev = {}
                    newdev['NwkId'] = list(self.ListOfDevices.keys())[1]
                    data['NewDevices'].append( newdev )
                    _response["Data"] = json.dumps( data )
                    return _response

                elif self.fakeDevicesInPairingMode in ( 6, 7 ):
                    self.fakeDevicesInPairingMode += 1
                    self.DevicesInPairingMode.append( list(self.ListOfDevices.keys())[0] )
                    self.DevicesInPairingMode.append( list(self.ListOfDevices.keys())[1] )
                    self.DevicesInPairingMode.append( list(self.ListOfDevices.keys())[2] )

            Domoticz.Log("Assisted Pairing: Polling: %s" %str(self.DevicesInPairingMode))
            if len(self.DevicesInPairingMode) == 0:
                Domoticz.Log("--> Empty queue")
                _response["Data"] = json.dumps( data )
                return _response
            else:
                listOfPairedDevices = list(self.DevicesInPairingMode)
                _fake = 0
                for nwkid in listOfPairedDevices:
                    if not self.zigatedata:
                        _fake += 1
                    newdev = {}
                    newdev['NwkId'] = nwkid

                    Domoticz.Log("--> New device: %s" %nwkid)
                    if 'Status' not in self.ListOfDevices[ nwkid ]:
                        Domoticz.Error("Something went wrong as the device seems not be created")
                        data['NewDevices'].append( newdev )
                        continue

                    if self.ListOfDevices[ nwkid ]['Status'] in ( '004d', '0045', '0043', '8045', '8043') or ( _fake == 1):
                        # Pairing in progress, just return the Nwkid
                        data['NewDevices'].append( newdev )
                        continue

                    elif self.ListOfDevices[ nwkid ]['Status'] == 'UNKNOW' or ( _fake == 2):
                        Domoticz.Log("--> UNKNOW , removed %s from List" %nwkid)
                        self.DevicesInPairingMode.remove( nwkid )
                        newdev['ProvisionStatus'] = 'Failed'
                        newdev['ProvisionStatusDesc'] = 'Failed'

                    elif self.ListOfDevices[ nwkid ]['Status'] == 'inDB':
                        Domoticz.Log("--> inDB , removed %s from List" %nwkid)
                        self.DevicesInPairingMode.remove( nwkid )
                        newdev['ProvisionStatus'] = 'inDB'
                        newdev['ProvisionStatusDesc'] = 'inDB'
                    else:
                        Domoticz.Log("--> Unexpected , removed %s from List" %nwkid)
                        self.DevicesInPairingMode.remove( nwkid )
                        newdev['ProvisionStatus'] = 'Unexpected'
                        newdev['ProvisionStatusDesc'] = 'Unexpected'
                        Domoticz.Error('Unexpected')
                        continue

                    newdev['IEEE'] = 'Unknown'
                    if 'IEEE' in self.ListOfDevices[ nwkid ]:
                        newdev['IEEE'] = self.ListOfDevices[ nwkid ]['IEEE']
    
                    newdev['ProfileId'] = ''
                    newdev['ProfileIdDesc'] = 'Unknow'
                    if 'ProfileID' in self.ListOfDevices[ nwkid ]:
                        if self.ListOfDevices[ nwkid ]['ProfileID'] != {}:
                            newdev['ProfileId'] = self.ListOfDevices[ nwkid ]['ProfileID']
                            if int(newdev['ProfileId'],16) in PROFILE_ID:
                                newdev['ProfileIdDesc'] = PROFILE_ID[ int(newdev['ProfileId'],16) ]

                    newdev['ZDeviceID'] = ''
                    newdev['ZDeviceIDDesc'] = 'Unknow'
                    if 'ZDeviceID' in self.ListOfDevices[ nwkid ]:
                        if self.ListOfDevices[ nwkid ]['ZDeviceID'] != {}:
                            newdev['ZDeviceID'] = self.ListOfDevices[ nwkid ]['ZDeviceID']
                            if int(newdev['ProfileId'],16) == 0x0104: # ZHA
                                if int(newdev['ZDeviceID'],16) in ZHA_DEVICES:
                                    newdev['ZDeviceIDDesc'] = ZHA_DEVICES[ int(newdev['ZDeviceID'],16) ]
                                else:
                                    newdev['ZDeviceIDDesc'] = 'Unknow'
                            elif int(newdev['ProfileId'],16) == 0xc05e: # ZLL
                                if int(newdev['ZDeviceID'],16) in ZLL_DEVICES:
                                    newdev['ZDeviceIDDesc'] = ZLL_DEVICES[ int(newdev['ZDeviceID'],16) ]
         
                    if 'Model' in self.ListOfDevices[ nwkid ]:
                        newdev['Model'] = self.ListOfDevices[ nwkid ]['Model']
        
                    newdev['PluginCertified'] = 'Unknow'
                    if 'ConfigSource' in self.ListOfDevices[nwkid]:
                        if self.ListOfDevices[nwkid]['ConfigSource'] == 'DeviceConf':
                            newdev['PluginCertified'] = 'yes'
                        else:
                            newdev['PluginCertified'] = 'no'
       
                    newdev['Ep'] = []
                    if 'Ep' in self.ListOfDevices[ nwkid ]:
                        for iterEp in  self.ListOfDevices[ nwkid ][ 'Ep' ]:
                            ep = {}
                            ep['Ep'] = iterEp
                            ep['Clusters'] = []
                            for clusterId in self.ListOfDevices[ nwkid ][ 'Ep' ][ iterEp ]:
                                if clusterId in ( 'ClusterType', 'Type', 'ColorControl' ): continue
                                cluster = {}
                                cluster['ClusterId'] = clusterId
                                if clusterId in ZCL_CLUSTERS_LIST:
                                    cluster['ClusterDesc'] = ZCL_CLUSTERS_LIST[ clusterId ]
                                else:
                                    cluster['ClusterDesc'] = 'Unknown'
                                ep['Clusters'].append( cluster )
                                Domoticz.Log("------> New Cluster: %s" %str(cluster))
                            newdev['Ep'].append( ep )
                            Domoticz.Log("----> New Ep: %s" %str(ep))
                    data['NewDevices'].append( newdev )
                    Domoticz.Log(" --> New Device: %s" %str(newdev))
                # for nwkid in listOfPairedDevices:
                    
            _response["Data"] = json.dumps( data )
            return _response

def DumpHTTPResponseToLog(httpDict):

    if not DEBUG_HTTP:
        return
    if isinstance(httpDict, dict):
        self.logging( 'Log', "HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                self.logging( 'Log', "--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    self.logging( 'Log', "------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                if x == 'Data':
                    self.logging( 'Log', "--->'%s':'%.40s'" %(x, str(httpDict[x])))
                else:
                    self.logging( 'Log', "--->'" + x + "':'" + str(httpDict[x]) + "'")

def setupHeadersResponse( cookie = None ):

    _response = {}
    _response["Headers"] = {}
    _response["Headers"]["Server"] = "Domoticz"
    _response["Headers"]["User-Agent"] = "Plugin-Zigate/v1"

    _response["Headers"]['Access-Control-Allow-Headers'] = 'Cache-Control, Pragma, Origin, Authorization,   Content-Type, X-Requested-With'
    _response["Headers"]['Access-Control-Allow-Methods'] = 'GET, POST, DELETE'
    _response["Headers"]['Access-Control-Allow-Origin'] = '*'

    _response["Headers"]["Referrer-Policy"] = "no-referrer"

    if cookie:
        _response["Headers"]["Cookie"] = cookie

    #_response["Headers"]["Accept-Ranges"] = "bytes"
    # allow users of a web application to include images from any origin in their own conten
    # and all scripts only to a specific server that hosts trusted code.
    #_response["Headers"]["Content-Security-Policy"] = "default-src 'self'; img-src *"
    #_response["Headers"]["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval'"

    return _response


