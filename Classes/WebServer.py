
import Domoticz
import json
import os.path

import mimetypes
from urllib.parse import urlparse, urlsplit, urldefrag

from time import time

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
        

    def  startWebServer( self ):

        self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port='9440')
        self.httpsServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTPS", Port='9443')
        self.httpServerConn.Listen()
        self.httpsServerConn.Listen()
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

            if  Data['URL'][0] == '/':
                parsed_query = Data['URL'][1:].split('/')
            else:
                parsed_query = Data['URL'].split('/')

            if 'Data' not in Data:
                Data['Data'] = None
            if ( parsed_query[0] == 'rest-zigate'):
                # REST API
                Domoticz.Log("Receiving a REST API - Version: %s, Verb: %s, Command: %s, Param: %s" \
                        %( parsed_query[1], Data['Verb'],  parsed_query[2], parsed_query[3:] ))
                self.do_rest( Connection, Data['Verb'], Data['Data'], parsed_query[1], parsed_query[2], parsed_query[3:])
                return
                
            elif (  parsed_query[0].find('json.htm') != -1 ):
                # JSON API
                self.jsonDispatch( Connection, Data )
                return

            elif not os.path.exists( self.homedirectory +'www'+ Data['URL']):
                Domoticz.Error("Invalid web request received, file '"+ self.homedirectory + 'www' +Data['URL'] + "' does not exist")
                headerCode = "404 File Not Found"

            if (headerCode != "200 OK"):
                DumpHTTPResponseToLog(Data)
                Connection.Send({"Status": headerCode})
                return

            # We are ready to send the response
            _response = setupHeadersResponse()

            #webFilename = self.homedirectory +'www'+Data['URL'] 
            webFilename = self.homedirectory +'www'+ Data['URL']
            with open(webFilename , mode ='rb') as webFile:
                _response["Data"] = webFile.read()

                Domoticz.Log("Reading file: %.40s len: %s" %(_response["Data"], len(_response["Data"])))

                _contentType, _contentEncoding = mimetypes.guess_type( Data['URL'] )
                Domoticz.Log("MimeType: %s, Content-Encoding: %s " %(_contentType, _contentEncoding))
    
                if _contentType:
                    _response["Headers"]["Content-Type"] = _contentType +"; charset=utf-8"
                if _contentEncoding:
                    _response["Headers"]["Content-Encoding"] = _contentEncoding 
    
                _response["Status"] = "200 OK"
    
                Connection.Send( _response )
    
                Domoticz.Log("Response sent")
                Domoticz.Log("--->Status: %s" %(_response["Status"]))
                Domoticz.Log("--->Headers")
                for item in _response["Headers"]:
                    Domoticz.Log("------>%s: %s" %(item, _response["Headers"][item]))
                if 'Data' in _response:
                    Domoticz.Log("--->Data: '%.40s'" %str(_response["Data"]))

    def keepConnectionAlive( self ):

        if (self.httpClientConn == None or self.httpClientConn.Connected() != True):
            self.httpClientConn = Domoticz.Connection(Name="Client Connection", Transport="TCP/IP", Protocol="HTTP", Address="127.0.0.1", Port=Parameters["Port"])
            self.httpClientConn.Connect()
            self.heartbeats = 0
        else:
            if (self.heartbeats == 1):
                self.httpClientConn.Send({"Verb":"GET", "URL":"/page.html", "Headers": {"Connection": "keep-alive", "Accept": "Content-Type: text/html; charset=UTF-8"}})
            elif (self.heartbeats == 2):
                postData = "param1=value&param2=other+value"
                self.httpClientConn.Send({'Verb':'POST', 'URL':'/MediaRenderer/AVTransport/Control', 'Data': postData})
            elif (self.heartbeats == 3) and (Parameters["Mode6"] != "File"):
                self.httpClientConn.Disconnect()
        self.heartbeats += 1

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

        if HTTPresponse != {}:
            HTTPresponse["Status"] = "200 OK"
            HTTPresponse["Headers"]["Connection"] = "Keealive"
            HTTPresponse["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        else:
            # We reach here due to failure !
            HTTPresponse["Status"] = "400 BAD REQUEST"
            HTTPresponse["Data"] = 'Unknown REST command'
            HTTPresponse["Headers"]["Connection"] = "Keealive"
            HTTPresponse["Headers"]["Content-Type"] = "text/plain; charset=utf-8"

        Domoticz.Log("Response sent")
        Domoticz.Log("--->Status: %s" %(HTTPresponse["Status"]))
        Domoticz.Log("--->Headers")
        for item in HTTPresponse["Headers"]:
            Domoticz.Log("------>%s: %s" %(item, HTTPresponse["Headers"][item]))
        if 'Data' in HTTPresponse:
            Domoticz.Log("--->Data: %s" %HTTPresponse["Data"])

        Connection.Send( HTTPresponse )


    def rest_Settings( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keealive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == 'GET':

            if len(parameters) == 0:
                settings = {}
                settings["Ping"] = {}
                settings["Ping"]["default"] = "1"
                settings["Ping"]["current"] = ""
                settings["enableWebServer"] = {}
                settings["enableWebServer"]["default"] = "0"
                settings["enableWebServer"]["current"] = ""
                _response["Data"] = json.dumps( settings,indent=4, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            Domoticz.Log("Data: %s" %data)
            data = data.decode('utf8')
            Domoticz.Log("Data: %s" %data)
            data = json.loads(data)

            if len(parameters) == 1:
                Domoticz.Log("parameters: %s value = %s" %(parameters[0], str(data)))
            else:
                Domoticz.Error("Unexpected number of Parameter")
                _response["Data"] = { 'unexpected number of parameters' }
                _response["Status"] = "400 SYNTAX ERROR"

        return _response

    def rest_PermitToJoin( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keealive"
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
        _response["Headers"]["Connection"] = "Keealive"
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
        _response["Headers"]["Connection"] = "Keealive"
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
        _response["Headers"]["Connection"] = "Keealive"
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

    def jsonListOfDevices( self, Connection, IEEE=None, Nwkid=None):

        return

    def jsonDispatch( self, Connection, Data ):
        """
        GET
            /json.htm?type=devices                          Provide the list ond the details of Domoticz Widget for this Zigate
            /json.htm?type=devicesbyIEEE&<IEEE address>     Provide the list and the details of Domoticz Widget matching this IEEE
            /json.htm?type=zdevices                         Provide the list and details of Zigate devices (managed by the Plugin)
            /json.htm?type=zdevicesbyIEEE&<IEEE address>    Provide the details of the Zigate paired device matching the IEEE
            /json.htm?type=zdevicesbySaddr&<Short address>  Provide the details of the Zigate paired device matching the Short Address
            /json.htm?type=zgroups                          Provide the list and details of Groups 
        """

        _response = setupHeadersResponse()

        _analyse = Data['URL'].split('?')
        if len(_analyse) != 2:
            _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
            _response["Status"] = "400 BAD REQUEST"
        elif _analyse[0] != '/json.htm':
            _response["Status"] = "400 BAD REQUEST"
            _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
        else:
            _api = _analyse[1].split('=')
            if (len(_api) != 2):
                _response["Status"] = "400 BAD REQUEST"
                _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
            elif _api[0] != 'type':
                _response["Status"] = "400 BAD REQUEST"
                _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
            else: 
                _command = _api[1].split('&')
                if _command[0] not in ('devicebyname', 'devicebyIEEE', 'devices', 'zdevices', 'zdevicesbyIEEE', 'zdevicesbySaddr', 'zgroups' ):
                    _response["Status"] = "400 BAD REQUEST"
                    _response["Data"] = "Authorized  Verbs are: devicebyname', 'devicebyIEEE', 'devices', 'zdevices', 'zdevicesbyIEEE', 'zdevicesbySaddr', 'zgroups '"
                else: 
                    if len(_command) > 2:
                        _response["Status"] = "400 BAD REQUEST"
                        _response["Data"] = "Syntax error, expecting: /json.htm?type=devicebyIEEE&00158d00028f8e74 in order get the Domoticz Widget info for Device 00158d00028f8e74"
                    else:
                        # Finally syntax, verbs are ok.
                        if _command[0] == 'devices':
                            if self.jsonListWidgets( Connection ):
                                return
                            _response["Status"] = "404 Not Found"
                            _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
                        elif _command[0] == 'zdevices':
                            if self.jsonListOfDevices( Connection ):
                                return
                            _response["Status"] = "404 Not Found"
                            _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
                        elif _command[0] == 'zgroups':
                            if self.jsonListOfGroups( Connection ):
                                return
                            _response["Status"] = "404 Not Found"
                            _response["Data"] = "Syntax error, expecting: /json.htm?type=devices  in order to get the full list of Domoticz Widgets"
                        elif _command[0] in ( 'devicebyname', 'devicebyIEEE' ) and len(_command) == 2:
                            if _command[0] == 'devicebyIEEE':
                                if self.jsonListWidgets( Connection, WidgetID=_command[1]):
                                    return
                                _response["Data"] = "Widget ID (IEEE): %s not found" %_command[1]
                                _response["Status"] = "404 Not Found"
                            else:
                                if self.jsonListWidgets( Connection,WidgetName=_command[1]):
                                    return
                                _response["Data"] = "Widget Name: %s not found" %_command[1]
                                _response["Status"] = "404 Not Found"
                        elif _command[0] in ( 'zdevicesbyIEEE', 'zdevicesbySaddr' ) and len(_command) == 2:
                            if _command[0] == 'zdevicesbyIEEE':
                                if self.jsonListOfDevices( Connection, IEEE=_command[1]):
                                    return
                                _response["Status"] = "404 Not Found"
                                _response["Data"] = "IEEE: %s not found" %_command[1]
                            else:
                                if self.jsonListOfDevices( Connection, Nwkid=_command[1]):
                                    return
                                _response["Status"] = "404 Not Found"
                                _response["Data"] = "Short Address: %s not found" %_command[1]


        # We reach here due to failure !
        if 'Status' not in _response:
                _response["Status"] = "400 BAD REQUEST"
                _response["Data"] = 'Syntax error'
    
        _response["Headers"]["Connection"] = "Keealive"
        _response["Headers"]["Content-Type"] = "text/plain; charset=utf-8"
        Connection.Send( _response )
        Domoticz.Log('"Status": %s, "Headers": %s' %(_response["Status"],_response["Headers"]))


    def jsonListWidgets( self, Connection, WidgetName=None, WidgetID = None):

        if self.Devices is None or len(self.Devices) == 0:
            return
        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keealive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if WidgetName and WidgetID:
            Domoticz.Error("jsonListWidgets - not expected")
            return False

        if WidgetName:
            # Return the list of Widgets for this particular IEEE
            for x in self.Devices:
                if self.Devices[x].Name == WidgetName:
                    break
            else:
                return False
            _dictDevices = {}
            _dictDevices['Name'] = self.Devices[x].Name
            _dictDevices['DeviceID'] = self.Devices[x].DeviceID
            _dictDevices['sValue'] = self.Devices[x].sValue
            _dictDevices['nValue'] = self.Devices[x].nValue
            _dictDevices['SignaleLevel'] = self.Devices[x].SignalLevel
            _dictDevices['BatteryLevel'] = self.Devices[x].BatteryLevel
            _dictDevices['TimedOut'] = self.Devices[x].TimedOut
            _dictDevices['Type'] = self.Devices[x].Type
            _dictDevices['SwitchType'] = self.Devices[x].SwitchType

            _response["Data"] = json.dumps( _dictDevices,indent=4, sort_keys=True )

        elif WidgetID:
            # Return the Widget Device information
            for x in self.Devices:
                if self.Devices[x].DeviceID == WidgetID:
                    break
            else:
                return False
            _dictDevices = {}
            _dictDevices['Name'] = self.Devices[x].Name
            _dictDevices['DeviceID'] = self.Devices[x].DeviceID
            _dictDevices['sValue'] = self.Devices[x].sValue
            _dictDevices['nValue'] = self.Devices[x].nValue
            _dictDevices['SignaleLevel'] = self.Devices[x].SignalLevel
            _dictDevices['BatteryLevel'] = self.Devices[x].BatteryLevel
            _dictDevices['TimedOut'] = self.Devices[x].TimedOut
            _dictDevices['Type'] = self.Devices[x].Type
            _dictDevices['SwitchType'] = self.Devices[x].SwitchType

            _response["Data"] = json.dumps( _dictDevices,indent=4, sort_keys=True )
        else:
            # Return the Full List of ZIgate Domoticz Widget
            _dictDevices = {}

            for x in self.Devices:
                _dictDevices[self.Devices[x].Name] = {}
                _dictDevices[self.Devices[x].Name]['Name'] = self.Devices[x].Name
                _dictDevices[self.Devices[x].Name]['DeviceID'] = self.Devices[x].DeviceID
                _dictDevices[self.Devices[x].Name]['sValue'] = self.Devices[x].sValue
                _dictDevices[self.Devices[x].Name]['nValue'] = self.Devices[x].nValue
                _dictDevices[self.Devices[x].Name]['SignaleLevel'] = self.Devices[x].SignalLevel
                _dictDevices[self.Devices[x].Name]['BatteryLevel'] = self.Devices[x].BatteryLevel
                _dictDevices[self.Devices[x].Name]['TimedOut'] = self.Devices[x].TimedOut
                _dictDevices[self.Devices[x].Name]['Type'] = self.Devices[x].Type
                _dictDevices[self.Devices[x].Name]['SwitchType'] = self.Devices[x].SwitchType

            _response["Data"] = json.dumps( _dictDevices,indent=4, sort_keys=True )

        Domoticz.Log('"Status": %s, "Headers": %s' %(_response["Status"],_response["Headers"]))
        Connection.Send( _response )
        return True

    def jsonListOfGroups( self, Connection):


        if self.groupmgt is None:
            return

        ListOfGroups = self.groupmgt.ListOfGroups
        if ListOfGroups is None or len(ListOfGroups) == 0:
            return
        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keealive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        _response["Data"] = json.dumps( ListOfGroups,indent=4, sort_keys=True )
        Domoticz.Log('"Status": %s, "Headers": %s' %(_response["Status"],_response["Headers"]))
        Connection.Send( _response )
        return True



    def jsonListOfDevices( self, Connection, IEEE=None, Nwkid=None):

        if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
            return
        _response = setupHeadersResponse()
        _response["Status"] = "200 OK"
        _response["Headers"]["Connection"] = "Keealive"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if IEEE and Nwkid:
            Domoticz.Error("jsonListOfDevices - not expected")
            return False
        if Nwkid:
            # Return the Device infos based on Nwkid
            if Nwkid not in self.ListOfDevices:
                return False
            _response["Data"] =  json.dumps( self.ListOfDevices[Nwkid],indent=4, sort_keys=True ) 
        elif IEEE:
            # Return the Deviceinfos after getting the Nwkid
            if IEEE not in self.IEEE2NWK:
                return False
            if self.IEEE2NWK[IEEE] not in self.ListOfDevices:
                return False
            _response["Data"] = json.dumps( self.ListOfDevices[self.IEEE2NWK[IEEE]],indent=4, sort_keys=True ) 
        else:
            # Return a sorted list of devices and filter 0000
            _response["Data"] = json.dumps( self.ListOfDevices,indent=4, sort_keys=True )

        Domoticz.Log('"Status": %s, "Headers": %s' %(_response["Status"],_response["Headers"]))
        Connection.Send( _response )
        return True


def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Log("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Log("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Log("--->'" + x + "':'" + str(httpDict[x]) + "'")



def setupHeadersResponse():

    _response = {}
    _response["Headers"] = {}
    _response["Headers"]["Connection"] = "Keealive"
    _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    _response["Headers"]["Pragma"] = "no-cache"
    _response["Headers"]["Expires"] = "0"
    _response["Headers"]["User-Agent"] = "Plugin-Zigate"

    return _response
