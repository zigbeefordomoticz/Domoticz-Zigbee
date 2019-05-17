
import Domoticz
import json
import os.path

import mimetypes
from urllib.parse import urlparse, urlsplit, urldefrag, parse_qs

from time import time
import gzip
from Modules.consts import ADDRESS_MODE, MAX_LOAD_ZIGATE

class WebServer(object):
    hearbeats = 0 

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, groupManagement, Devices, ListOfDevices, IEEE2NWK ):

        self.httpServerConn = None
        self.httpsServerConn = None
        self.httpServerConns = {}
        self.httpClientConn = None

        self.pluginconf = PluginConf
        self.adminWidget = adminWidgets
        self.ZigateComm = ZigateComm

        if groupManagement:
            self.groupmgt = groupManagement
        else:
            self.groupmgt = None
        self.ListOfDevices = ListOfDevices
        self.IEEE2NWK = IEEE2NWK
        self.Devices = Devices

        self.homedirectory = HomeDirectory
        self.hardwareID = hardwareID
        mimetypes.init()
        self.startWebServer()
        
        self.Settings = {}
        self.Settings["Ping"] = {}
        self.Settings["Ping"]["default"] = "1"
        self.Settings["Ping"]["current"] = ""
        self.Settings["enableWebServer"] = {}
        self.Settings["enableWebServer"]["default"] = "0"
        self.Settings["enableWebServer"]["current"] = ""

    def  startWebServer( self ):

        self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port='9440')
        #self.httpsServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTPS", Port='9443')
        self.httpServerConn.Listen()
        #self.httpsServerConn.Listen()
        Domoticz.Log("Web backend started")

    def onDisconnect ( self, Connection ):

        for x in self.httpServerConns:
            Domoticz.Log("--> "+str(x)+"'.")
        if Connection.Name in self.httpServerConns:
            del self.httpServerConns[Connection.Name]

    def onConnect(self, Connection, Status, Description):

        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address+":"+Connection.Port)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
        Domoticz.Log(str(Connection))
        if (Connection != self.httpClientConn):
            self.httpServerConns[Connection.Name] = Connection

    def onMessage( self, Connection, Data ):

            Domoticz.Log("WebServer onMessage")
            DumpHTTPResponseToLog(Data)

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
            Domoticz.Log("URL: %s , Path: %s" %( Data['URL'], parsed_url.path))

            if  Data['URL'][0] == '/': parsed_query = Data['URL'][1:].split('/')
            else: parsed_query = Data['URL'].split('/')

            if 'Data' not in Data:
                Data['Data'] = None

            if (headerCode != "200 OK"):
                self.sendResponse( Connection, {"Status": headerCode}, False  )
                return
            elif ( parsed_query[0] == 'rest-zigate'):
                Domoticz.Log("Receiving a REST API - Version: %s, Verb: %s, Command: %s, Param: %s" \
                        %( parsed_query[1], Data['Verb'],  parsed_query[2], parsed_query[3:] ))
                self.do_rest( Connection, Data['Verb'], Data['Data'], parsed_query[1], parsed_query[2], parsed_query[3:])
                return

            webFilename = self.homedirectory +'www'+ Data['URL']
            Domoticz.Debug("webFilename: %s" %webFilename)
            if not os.path.isfile( webFilename ):
                webFilename =  self.homedirectory + 'www' + "/index.html"
                Domoticz.Debug("Redirecting to /index.html")

            # We are ready to send the response
            _response = setupHeadersResponse()

            #webFilename = self.homedirectory +'www'+Data['URL'] 
            Domoticz.Debug("Opening: %s" %webFilename)
            with open(webFilename , mode ='rb') as webFile:
                _response["Data"] = webFile.read()

            _contentType, _contentEncoding = mimetypes.guess_type( Data['URL'] )
            Domoticz.Debug("MimeType: %s, Content-Encoding: %s " %(_contentType, _contentEncoding))
   
            if _contentType:
                _response["Headers"]["Content-Type"] = _contentType +"; charset=utf-8"
            if _contentEncoding:
                _response["Headers"]["Content-Encoding"] = _contentEncoding 
  
            _response["Status"] = "200 OK"
            compress=False
            if Data['Headers']['Accept-Encoding'].find('gzip') != -1:
                compress=True
            self.sendResponse( Connection, _response, compress  )

    def sendResponse( self, Connection, Response, Compress ):

        ALLOW_CHUNK = 1
        MAX_KB_TO_SEND = 16 * 1024

        Domoticz.Log("sendResponse - Compress: %s, Chunk: %s" %(Compress, ALLOW_CHUNK))
        for item in Response["Headers"]:
            Domoticz.Log("------>%s: %s" %(item, Response["Headers"][item]))
        if 'Data' in Response:
            Domoticz.Log("--->Data: '%.40s'" %str(Response["Data"]))

        if Compress:
            Response["Data"] = gzip.compress( Response["Data"] )
            Response["Headers"]['Content-Encoding'] = 'gzip'

        if ALLOW_CHUNK and len(Response['Data']) > MAX_KB_TO_SEND:

            idx = 0
            HTTPchunk = {}
            HTTPchunk['Status'] = Response['Status']
            HTTPchunk['Headers'] = {}
            HTTPchunk['Headers'] = dict(Response['Headers'])
            HTTPchunk['Chunk'] = True
            HTTPchunk['Data'] = Response['Data'][0:MAX_KB_TO_SEND]

            Domoticz.Log("Sending: %s out of %s" %(idx, len((Response['Data']))))
            DumpHTTPResponseToLog( Response )
            Connection.Send( HTTPchunk )

            idx = MAX_KB_TO_SEND
            while idx != -1:
                tosend={}
                tosend['Chunk'] = True
                if idx + MAX_KB_TO_SEND <= len(Response['Data']):
                    tosend['Data'] = Response['Data'][idx:idx+MAX_KB_TO_SEND]        
                    idx += MAX_KB_TO_SEND
                else:
                    tosend['Data'] = Response['Data'][idx:]        
                    idx = -1

                Connection.Send( tosend )
                Domoticz.Log("Sending: %s out of %s" %(idx, len((Response['Data']))))
                DumpHTTPResponseToLog( Response )

            tosend={}
            tosend['Chunk'] = True
            DumpHTTPResponseToLog( Response )
            Connection.Send( tosend )

        else:
            Connection.Send( Response )


    def keepConnectionAlive( self ):

        self.heartbeats += 1
        return

    def do_rest( self, Connection, verb, data, version, command, parameters):

        REST_COMMANDS = { 
                'setting':       {'Name':'setting',       'Verbs':{'GET','PUT'}, 'function':self.rest_Settings},
                'permit-to-join':{'Name':'permit-to-join','Verbs':{'GET','PUT'}, 'function':self.rest_PermitToJoin},
                'device':        {'Name':'device',        'Verbs':{'GET'}, 'function':self.rest_Device},
                'zdevice':       {'Name':'zdevice',       'Verbs':{'GET'}, 'function':self.rest_zDevice},
                'zgroup':        {'Name':'device',        'Verbs':{'GET'}, 'function':self.rest_zGroup}
                }

        Domoticz.Log("do_rest - Verb: %s, Command: %s, Param: %s" %(verb, command, parameters))
        HTTPresponse = setupHeadersResponse()
        if command in REST_COMMANDS:
            if verb in REST_COMMANDS[command]['Verbs']:
                HTTPresponse = REST_COMMANDS[command]['function']( verb, data, parameters)

        if HTTPresponse == {}:
            # We reach here due to failure !
            HTTPresponse["Status"] = "400 BAD REQUEST"
            HTTPresponse["Data"] = 'Unknown REST command'
            HTTPresponse["Headers"]["Connection"] = "Close"
            HTTPresponse["Headers"]["Content-Type"] = "text/plain; charset=utf-8"

        Domoticz.Log("Response sent")
        Domoticz.Log("--->Status: %s" %(HTTPresponse["Status"]))
        Domoticz.Log("--->Headers")
        for item in HTTPresponse["Headers"]:
            Domoticz.Log("------>%s: %s" %(item, HTTPresponse["Headers"][item]))
        if 'Data' in HTTPresponse:
            Domoticz.Debug("--->Data: %s" %HTTPresponse["Data"])

        self.sendResponse( Connection, HTTPresponse, False  )


    def rest_Settings( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keep-alive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if len(parameters) == 0:
                _response["Data"] = json.dumps( self.Settings,indent=4, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            data = data.decode('utf8')
            Domoticz.Log("Data: %s" %data)
            data = eval(data)

            for item in data:
                Domoticz.Log("Data[%s] = %s" %(item, data[item]))
                if item not in self.Settings:
                    Domoticz.Error("Unexpectped parameter: %s" %item)
                    Domoticz.Error("Unexpected number of Parameter")
                    _response["Data"] = { 'unexpected parameters %s' %item }
                    _response["Status"] = "400 SYNTAX ERROR"
                    break
                else:
                    Domoticz.Log(" self.Settings[%s] = %s" %(item, self.Settings[item]))
                    if data[item]['current'] != self.Settings[item]['current']:
                        self.Settings[item]['current'] = data[item]['current']
        return _response

    def rest_PermitToJoin( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keep-alive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            _response["Data"] = { 'permit-to-join':254 }

        elif verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                Domoticz.Log("Data: %s" %data)
                data = data.decode('utf8')
                Domoticz.Log("Data: %s" %data)
                data = json.loads(data)
                Domoticz.Log("parameters: %s value = %s" %('permit-to-join', str(data)))

        return _response

    def rest_Device( self, verb, data, parameters):

        _dictDevices = {}
        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keep-alive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response

            if len(parameters) == 0:
                # Return the Full List of ZIgate Domoticz Widget
                for x in self.Devices:
                    _dictDevices[self.Devices[x].Name] = {}
                    _dictDevices[self.Devices[x].Name]['Name'] = self.Devices[x].Name
                    _dictDevices[self.Devices[x].Name]['ID'] = self.Devices[x].ID
                    _dictDevices[self.Devices[x].Name]['DeviceID'] = self.Devices[x].DeviceID
                    _dictDevices[self.Devices[x].Name]['sValue'] = self.Devices[x].sValue
                    _dictDevices[self.Devices[x].Name]['nValue'] = self.Devices[x].nValue
                    _dictDevices[self.Devices[x].Name]['SignaleLevel'] = self.Devices[x].SignalLevel
                    _dictDevices[self.Devices[x].Name]['BatteryLevel'] = self.Devices[x].BatteryLevel
                    _dictDevices[self.Devices[x].Name]['TimedOut'] = self.Devices[x].TimedOut
                    _dictDevices[self.Devices[x].Name]['Type'] = self.Devices[x].Type
                    _dictDevices[self.Devices[x].Name]['SwitchType'] = self.Devices[x].SwitchType

            elif len(parameters) == 1:
                for x in self.Devices:
                    if parameters[0] == self.Devices[x].DeviceID:
                        _dictDevices[x] = {}
                        _dictDevices[x]['Name'] = self.Devices[x].Name
                        _dictDevices[x]['ID'] = self.Devices[x].ID
                        _dictDevices[x]['DeviceID'] = self.Devices[x].DeviceID
                        _dictDevices[x]['sValue'] = self.Devices[x].sValue
                        _dictDevices[x]['nValue'] = self.Devices[x].nValue
                        _dictDevices[x]['SignaleLevel'] = self.Devices[x].SignalLevel
                        _dictDevices[x]['BatteryLevel'] = self.Devices[x].BatteryLevel
                        _dictDevices[x]['TimedOut'] = self.Devices[x].TimedOut
                        _dictDevices[x]['Type'] = self.Devices[x].Type
                        _dictDevices[x]['SwitchType'] = self.Devices[x].SwitchType
            else:
                for parm in parameters:
                    for x in self.Devices:
                        if parm == self.Devices[x].DeviceID:
                            _dictDevices[x] = {}
                            _dictDevices[x]['Name'] = self.Devices[x].Name
                            _dictDevices[x]['ID'] = self.Devices[x].ID
                            _dictDevices[x]['DeviceID'] = self.Devices[x].DeviceID
                            _dictDevices[x]['sValue'] = self.Devices[x].sValue
                            _dictDevices[x]['nValue'] = self.Devices[x].nValue
                            _dictDevices[x]['SignaleLevel'] = self.Devices[x].SignalLevel
                            _dictDevices[x]['BatteryLevel'] = self.Devices[x].BatteryLevel
                            _dictDevices[x]['TimedOut'] = self.Devices[x].TimedOut
                            _dictDevices[x]['Type'] = self.Devices[x].Type
                            _dictDevices[x]['SwitchType'] = self.Devices[x].SwitchType

            _response["Data"] = json.dumps( _dictDevices,indent=4, sort_keys=True )
        return _response

    def rest_zDevice( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keep-alive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                _response["Data"] = json.dumps( self.ListOfDevices,indent=4, sort_keys=True )
            elif len(parameters) == 1:
                if parameters[0] in self.ListOfDevices:
                    _response["Data"] =  json.dumps( self.ListOfDevices[parameters[0]],indent=4, sort_keys=True ) 
                elif parameters[0] in self.IEEE2NWK:
                    _response["Data"] =  json.dumps( self.ListOfDevices[self.IEEE2NWK[parameters[0]]],indent=4, sort_keys=True ) 
        return _response

    def rest_zGroup( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keep-alive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        Domoticz.Log("rest_zGroup - ListOfGroups = %s" %str(self.groupmgt))
        if verb == 'GET':
            if self.groupmgt is None:
                return _response
            ListOfGroups = self.groupmgt.ListOfGroups
            if ListOfGroups is None or len(ListOfGroups) == 0:
                return _response
            if len(parameters) == 0:
                _response["Data"] = json.dumps( ListOfGroups,indent=4, sort_keys=True )
            if len(parameters) == 1:
                if parameters[0] in ListOfGroups:
                    _response["Data"] = json.dumps( ListOfGroups[parameters[0]],indent=4, sort_keys=True )
        return _response


def DumpHTTPResponseToLog(httpDict):

    if isinstance(httpDict, dict):
        Domoticz.Log("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Log("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                if x == 'Data':
                    Domoticz.Log("--->'%s':'%.40s'" %(x, str(httpDict[x])))
                else:
                    Domoticz.Log("--->'" + x + "':'" + str(httpDict[x]) + "'")

def setupHeadersResponse():

    _response = {}
    _response["Headers"] = {}
    _response["Headers"]["Connection"] = "keep-alive"
    _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    _response["Headers"]["Pragma"] = "no-cache"
    _response["Headers"]["Expires"] = "0"
    _response["Headers"]["User-Agent"] = "Plugin-Zigate"
    _response["Headers"]["Server"] = "Domoticz"
    _response["Headers"]["Accept-Range"] = "none"

    return _response


