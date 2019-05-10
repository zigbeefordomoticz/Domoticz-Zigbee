
import Domoticz
import json
import pickle
import os.path

from time import time

from Modules.consts import ADDRESS_MODE, MAX_LOAD_ZIGATE

class WebServer(object):
    hearbeats = 0 

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):

        self.httpServerConn = None
        self.httpsServerConn = None
        self.httpServerConns = {}
        self.httpClientConn = None

        self.pluginconf = PluginConf
        self.adminWidget = adminWidgets
        self.ZigateComm = ZigateComm

        self.ListOfDevices = ListOfDevices
        self.IEEE2NWK = IEEE2NWK
        self.Devices = Devices

        self.homedirectory = HomeDirectory
        self.hardwareID = hardwareID
        self.startWebServer()
        

    def  startWebServer( self ):

        self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port='9440')
        self.httpsServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTPS", Port='9443')
        self.httpServerConn.Listen()
        self.httpsServerConn.Listen()
        Domoticz.Log("Leaving on start")


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
            elif (Data['Verb'] != 'GET'):
                Domoticz.Error("Invalid web request received, only GET requests allowed ("+Data['Verb']+")")
                headerCode = "405 Method Not Allowed"
            elif (not 'URL' in Data):
                Domoticz.Error("Invalid web request received, no URL present")
                headerCode = "400 Bad Request"
            elif (not os.path.exists( self.homedirectory +'www'+Data['URL'])):
                Domoticz.Error("Invalid web request received, file '"+ self.homedirectory +'www'+Data['URL']+"' does not exist")
                headerCode = "404 File Not Found"

            if (headerCode != "200 OK"):
                DumpHTTPResponseToLog(Data)
                Connection.Send({"Status": headerCode})
                return

            # We are ready to send the response
            webFilename = self.homedirectory +'www'+Data['URL'] 
            webFile = open(  webFilename , mode ='rb')
            webPage = webFile.read()
            webFile.close()

            _contentType = 'application/octet-stream'
            if Data['URL'].find('.html') != -1: _contentType = 'text/html'
            elif Data['URL'].find('.css') != -1: _contentType = 'text/css'
            elif Data['URL'].find('.ico') != -1: _contentType = 'image/x-icon'
            elif Data['URL'].find('.js') != -1: _contentType = 'text/javascript'
            elif Data['URL'].find('.json') != -1: _contentType = 'application/json'
            elif Data['URL'].find('.png') != -1: _contentType = 'image/png'
            elif Data['URL'].find('.jpg') != -1: _contentType = 'image/jpg'

            _headers = {"Connection": "keep-alive", "Accept": "Content-Type:"+ _contentType +"; charset=utf-8-8"}
            Domoticz.Log("Send response : Headers: %s" %_headers)
            Connection.Send({"Status":"200 OK", "Headers": _headers, "Data": webPage})


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


