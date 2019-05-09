
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

        self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port='9988')
        self.httpServerConn.Listen()
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
            else:
                # 'Range':'bytes=0-'
                for x in Data:
                    Domoticz.Log("%s: %s" %(x,Data[x]))

                webFile = open(  self.homedirectory +'www'+Data['URL'] , mode ='rt')
                webPage = webFile.read()
                webFile.close()

                Domoticz.Log("Connection: %s" %Connection)
                Domoticz.Log("self.httpClientConn: %s" %self.httpClientConn)
                Domoticz.Log("self.httpServerConns: %s" %self.httpServerConns)

                Connection.Send({"Status":"200 OK", "Headers": {"Connection": "keep-alive", "Accept": "Content-Type: text/html; charset=UTF-8"}, "Data": webPage})


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


