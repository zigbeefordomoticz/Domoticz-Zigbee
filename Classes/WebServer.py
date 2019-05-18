
import Domoticz
import json
import os.path

import mimetypes
from urllib.parse import urlparse, urlsplit, urldefrag, parse_qs

from time import time, ctime, strftime, gmtime
from gzip import compress
from Modules.consts import ADDRESS_MODE, MAX_LOAD_ZIGATE


ALLOW_GZIP = 1
ALLOW_CHUNK = 1
MAX_KB_TO_SEND = 2 * 1024
KEEP_ALIVE = True
DEBUG_HTTP = True

class WebServer(object):
    hearbeats = 0 

    def __init__( self, PluginParameters, PluginConf, Statistics, adminWidgets, ZigateComm, HomeDirectory, hardwareID, groupManagement, Devices, ListOfDevices, IEEE2NWK ):

        self.httpServerConn = None
        self.httpsServerConn = None
        self.httpServerConns = {}
        self.httpClientConn = None

        self.pluginconf = PluginConf
        self.adminWidget = adminWidgets
        self.ZigateComm = ZigateComm
        self.statistics = Statistics
        self.pluginparameters = PluginParameters

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
        self.httpServerConn.Listen()
        Domoticz.Log("Web backend started")

    def onDisconnect ( self, Connection ):

        for x in self.httpServerConns:
            Domoticz.Log("--> "+str(x)+"'.")
        if Connection.Name in self.httpServerConns:
            del self.httpServerConns[Connection.Name]

    def onConnect(self, Connection, Status, Description):

        if (Status == 0):
            Domoticz.Debug("Connected successfully to: "+Connection.Address+":"+Connection.Port)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)

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

            if 'Data' not in Data: Data['Data'] = None

            if (headerCode != "200 OK"):
                self.sendResponse( Connection, {"Status": headerCode}, False  )
                return
            elif ( parsed_query[0] == 'rest-zigate'):
                Domoticz.Log("Receiving a REST API - Version: %s, Verb: %s, Command: %s, Param: %s" \
                        %( parsed_query[1], Data['Verb'],  parsed_query[2], parsed_query[3:] ))
                if parsed_query[1] == '1':
                    # API Version 1
                    self.do_rest( Connection, Data['Verb'], Data['Data'], parsed_query[1], parsed_query[2], parsed_query[3:])
                else:
                    Domoticz.Error("Unknown API version %s" %parsed_query[1])
                    headerCode = "400 Bad Request"
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
            _lastmodified = strftime("%a, %d %m %y %H:%M:%S GMT", gmtime(os.path.getmtime(webFilename)))

            #_response["Headers"]["Last-Modified"] = ctime(os.path.getmtime(webFilename))
            _response["Headers"]["Last-Modified"] = _lastmodified
            with open(webFilename , mode ='rb') as webFile:
                _response["Data"] = webFile.read()

            _contentType, _contentEncoding = mimetypes.guess_type( Data['URL'] )
            Domoticz.Debug("MimeType: %s, Content-Encoding: %s " %(_contentType, _contentEncoding))
   
            if _contentType:
                _response["Headers"]["Content-Type"] = _contentType +"; charset=utf-8"
            if _contentEncoding:
                _response["Headers"]["Content-Encoding"] = _contentEncoding 
  
            _response["Status"] = "200 OK"
            if 'Cookie' in Data['Headers']: 
                _response['Headers']['Cookie'] = Data['Headers']['Cookie']

            compress=False
            if Data['Headers']['Accept-Encoding'].find('gzip') != -1:
                compress=True
            self.sendResponse( Connection, _response, compress  )

    def sendResponse( self, Connection, Response, Compress ):

        if 'Data' not in Response or Response['Data'] == None:
            DumpHTTPResponseToLog( Response )
            if KEEP_ALIVE:
                Response['Connection'] = 'Keep-alive'
                Connection.Send( Response )
            else:
                Response['Connection'] = 'Close'
                Connection.Send( Response )
                Connection.Disconnect( )
            return

        Domoticz.Debug("sendResponse - Compress: %s, Chunk: %s" %(Compress, ALLOW_CHUNK))
        if ALLOW_GZIP and Compress and 'Data' in Response:
            if len(Response["Data"]) > MAX_KB_TO_SEND:
                Response["Data"] = compress( Response["Data"] )
                Response["Headers"]['Content-Encoding'] = 'gzip'

        if ALLOW_CHUNK  and len(Response['Data']) > MAX_KB_TO_SEND:
            idx = 0
            HTTPchunk = {}
            HTTPchunk['Status'] = Response['Status']
            HTTPchunk['Headers'] = {}
            HTTPchunk['Headers'] = dict(Response['Headers'])
            HTTPchunk['Chunk'] = True
            HTTPchunk['Data'] = Response['Data'][0:MAX_KB_TO_SEND]
            Domoticz.Debug("Sending: %s out of %s" %(idx, len((Response['Data']))))
            DumpHTTPResponseToLog( Response )
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
                    # we have to send MAX_KB_TO_SEND or less and then exit
                    tosend['Data'] = Response['Data'][idx:]        
                    idx = -1

                Connection.Send( tosend )
                Domoticz.Debug("Sending: %s out of %s" %(idx, len((Response['Data']))))
            tosend={}
            tosend['Connection'] = 'Close'
            tosend['Chunk'] = True
            DumpHTTPResponseToLog( Response )
            Connection.Send( tosend )
            Connection.Disconnect( )
        else:
            DumpHTTPResponseToLog( Response )
            if KEEP_ALIVE:
                Response['Connection'] = 'Keep-alive'
                Connection.Send( Response )
            else:
                Response['Connection'] = 'Close'
                Connection.Send( Response )
                Connection.Disconnect( )

    def keepConnectionAlive( self ):

        self.heartbeats += 1
        return

    def do_rest( self, Connection, verb, data, version, command, parameters):

        REST_COMMANDS = { 
                'setting':       {'Name':'setting',       'Verbs':{'GET','PUT'}, 'function':self.rest_Settings},
                'permit-to-join':{'Name':'permit-to-join','Verbs':{'GET','PUT'}, 'function':self.rest_PermitToJoin},
                'device':        {'Name':'device',        'Verbs':{'GET'}, 'function':self.rest_Device},
                'zdevice':       {'Name':'zdevice',       'Verbs':{'GET'}, 'function':self.rest_zDevice},
                'zdevice-name':  {'Name':'zdevice-name',  'Verbs':{'GET','PUT'}, 'function':self.rest_zDevice_name},
                'zgroup':        {'Name':'device',        'Verbs':{'GET'}, 'function':self.rest_zGroup},
                'zgroup-list-available-device':        {'Name':'zgroup-list-available-devic',        'Verbs':{'GET'}, 'function':self.rest_zGroup_lst_avlble_dev},
                'plugin':        {'Name':'plugin',        'Verbs':{'GET'}, 'function':self.rest_PluginEnv},
                'topologie':     {'Name':'topologie',     'Verbs':{'GET','DELETE'}, 'function':self.rest_netTopologie},
                'nwk-stat':      {'Name':'nwk_stat',      'Verbs':{'GET','DELETE'}, 'function':self.rest_nwk_stat},
                'plugin-stat':   {'Name':'plugin-stat',   'Verbs':{'GET'}, 'function':self.rest_plugin_stat}
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

        self.sendResponse( Connection, HTTPresponse, False  )


    def rest_PluginEnv( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                _response["Data"] = json.dumps( self.pluginparameters, sort_keys=True )
        return _response

    def rest_netTopologie( self, verb, data, parameters):

        _filename = self.pluginconf.pluginReports + 'LQI_reports-' + '%02d' %self.hardwareID + '.json'
        Domoticz.Log("Filename: %s" %_filename)

        _lqi = {}
        _key = {}

        with open( _filename , 'rt') as handle:
            for line in handle:
                Domoticz.Log("Line: %.40s" %line)
                if line[0] != '{': continue
                entry = json.loads( line, encoding=dict )
                for x in entry:
                    Domoticz.Log("--> %s" %x)
                    if x in entry:
                        _key[x] = '1'
                        if x in entry:
                            _lqi[x] = dict(entry[x])

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if len(parameters) == 0:
                # Send list of Time Stamps
                _response['Data'] = json.dumps( _key, sort_keys=True)

            elif len(parameters) == 1:
                _response['Data'] = json.dumps( _lqi[parameters[0]] , sort_keys=True ) 
        return _response

    def rest_nwk_stat( self, verb, data, parameters):

        return

    def rest_plugin_stat( self, verb, data, parameters):

        Statistics = {}
        Statistics['CRC'] =self.statistics._crcErrors
        Statistics['FrameErrors'] =self.statistics._frameErrors
        Statistics['Sent'] =self.statistics._sent
        Statistics['Received'] =self.statistics._received
        Statistics['Cluster'] =self.statistics._clusterOK
        Statistics['ReTx'] =self.statistics._reTx
        Statistics['MaxLoad'] =self.statistics._MaxLoad
        Statistics['StartTime'] =self.statistics._start

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                _response["Data"] = json.dumps( Statistics, sort_keys=True )
        return _response

    def rest_Settings( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if len(parameters) == 0:
                _response["Data"] = json.dumps( self.Settings, sort_keys=True )

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
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            _response["Data"] = '{"PermitToJoin":"254"}'

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

            _response["Data"] = json.dumps( _dictDevices, sort_keys=True )
        return _response

    def rest_zGroup_lst_avlble_dev( self, verb, data, parameters):

        """
        Provide a list of IEEE/EP/ZDeviceName/WidgetName with
            Main Powered
            Cluster 0x0004
            ClusterType
        """

        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            devName = {}
            for x in self.ListOfDevices:
                if x == '0000': continue
                if 'MacCapa' not in self.ListOfDevices[x]:
                    continue
                if self.ListOfDevices[x]['MacCapa'] != '8e':
                    continue
                if 'Ep' in self.ListOfDevices[x]:
                    if 'ZDeviceName' in self.ListOfDevices[x] and \
                          'IEEE' in self.ListOfDevices[x]:
                        devName[x] = {}
                        devName[x]['Ep'] = {}
                        devName[x]['ZDeviceName'] = self.ListOfDevices[x]['ZDeviceName']
                        devName[x]['IEEE'] = self.ListOfDevices[x]['IEEE']
                        for ep in self.ListOfDevices[x]['Ep']:
                            devName[x]['Ep'][ep] = {}
                            if '0004' not in self.ListOfDevices[x]['Ep'][ep] and \
                                'ClusterType' not in self.ListOfDevices[x]['Ep'][ep] and \
                                '0006' not in self.ListOfDevices[x]['Ep'][ep] and \
                                '0008' not in  self.ListOfDevices[x]['Ep'][ep]:
                                continue
                            if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]:
                                for widgetID in self.ListOfDevices[x]['Ep'][ep]['ClusterType']:
                                    if self.ListOfDevices[x]['Ep'][ep]['ClusterType'][widgetID] not in ( 'LvlControl', 'Switch', 'Plug', 
                                        "SwitchAQ2", "DSwitch", "Button", "DButton", 'LivoloSWL', 'LivoloSWR',
                                        'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl',
                                        'WindowCovering'):
                                        continue
                                    for widget in self.Devices:
                                        if self.Devices[widget].ID == int(widgetID):
                                            devName[x]['Ep'][ep]['WidgetName'] = self.Devices[widget].Name
                                            break
                            if ep in devName[x]['Ep'] and 'WidgetName' not in devName[x]['Ep'][ep]:
                                del devName[x]['Ep'][ep]
                        if devName[x]['Ep'] == {}:
                            del devName[x]['Ep']
                    if 'Ep' not in devName[x]:
                        del devName[x]

            _response["Data"] = json.dumps( devName, sort_keys=True )
            return _response

    def rest_zDevice_name( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"

        if verb == 'GET':
            _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
            devName = {}
            for x in self.ListOfDevices:
                if x == '0000': continue
                devName[x] = {}
                for item in ( 'ZDeviceName', 'IEEE', 'Model', 'PowerSource', 'MacCapa', 'Status', 'Logical Type' ):
                    if item in self.ListOfDevices[x]:
                        devName[x][item.strip()] = self.ListOfDevices[x][item]
                    else:
                        Domoticz.Log("rest_zDevice_name - warning device %s item: %s not reported to UI" %(x,item))

                devName[x]['WidgetNames'] = "[ "
                for ep in self.ListOfDevices[x]['Ep']:
                    if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]:
                        for widgetID in self.ListOfDevices[x]['Ep'][ep]['ClusterType']:
                            for widget in self.Devices:
                                if self.Devices[widget].ID == int(widgetID):
                                    Domoticz.Log("Widget Name: %s %s" %(widgetID, self.Devices[widget].Name))
                                    devName[x]['WidgetNames'] += self.Devices[widget].Name
                                    devName[x]['WidgetNames'] += " ,"
                if devName[x]['WidgetNames'][-1] == ',':
                    devName[x]['WidgetNames'] = devName[x]['WidgetNames'][:-1] + "]"
                else:
                    devName[x]['WidgetNames'] += " ]"

            _response["Data"] = json.dumps( devName, sort_keys=True )

        elif verb == 'PUT':

            _response["Data"] = None
            data = data.decode('utf8')
            Domoticz.Log("Data: %s" %data)
            data = eval(data)

            for x in data:
                if 'ZDeviceName' in data[x] and 'IEEE' in data[x]:
                    for dev in self.ListOfDevices:
                        if self.ListOfDevices[dev]['IEEE'] == data[x]['IEEE'] and \
                                self.ListOfDevices[dev]['ZDeviceName'] != data[x]['ZDeviceName']:
                            self.ListOfDevices[dev]['ZDeviceName'] = data[x]['ZDeviceName']
                            Domoticz.Log("Updating ZDeviceName to %s for IEEE: %s NWKID: %s" \
                                    %(self.ListOfDevices[dev]['ZDeviceName'], self.ListOfDevices[dev]['IEEE'], dev))
                else:
                    Domoticz.Error("wrong data received: %s" %data)

        return _response

    def rest_zDevice( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                _response["Data"] = json.dumps( self.ListOfDevices, sort_keys=True )
            elif len(parameters) == 1:
                if parameters[0] in self.ListOfDevices:
                    _response["Data"] =  json.dumps( self.ListOfDevices[parameters[0]], sort_keys=True ) 
                elif parameters[0] in self.IEEE2NWK:
                    _response["Data"] =  json.dumps( self.ListOfDevices[self.IEEE2NWK[parameters[0]]], sort_keys=True ) 
        return _response

    def rest_zGroup( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Data"] = {}
        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        Domoticz.Log("rest_zGroup - ListOfGroups = %s" %str(self.groupmgt))
        if verb == 'GET':
            if self.groupmgt is None:
                return _response
            ListOfGroups = self.groupmgt.ListOfGroups
            if ListOfGroups is None or len(ListOfGroups) == 0:
                return _response
            if len(parameters) == 0:
                _response["Data"] = json.dumps( ListOfGroups, sort_keys=True )
            if len(parameters) == 1:
                if parameters[0] in ListOfGroups:
                    _response["Data"] = json.dumps( ListOfGroups[parameters[0]], sort_keys=True )
        return _response


def DumpHTTPResponseToLog(httpDict):

    if not DEBUG_HTTP:
        return
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
    _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    _response["Headers"]["Pragma"] = "no-cache"
    _response["Headers"]["User-Agent"] = "Plugin-Zigate"
    _response["Headers"]["Server"] = "Domoticz"
    #_response["Headers"]["Accept-Range"] = "none"

    return _response


