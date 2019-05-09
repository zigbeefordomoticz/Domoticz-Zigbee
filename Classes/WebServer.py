
import Domoticz
import json
import pickle
import os.path

from time import time

from Modules.consts import ADDRESS_MODE, MAX_LOAD_ZIGATE

class WebServer(object):
    hearbeats = 0 
    httpServerConn = None
    httpServerConns = {}
    httpClientConn = None

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):

        self.pluginconf = PluginConf
        self.adminWidget = adminWidgets
        self.ZigateComm = ZigateComm

        self.ListOfDevices = ListOfDevices
        self.IEEE2NWK = IEEE2NWK
        self.Devices = Devices

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


        if "Verb" in Data:
            strVerb = Data["Verb"]
            #strData = Data["Data"].decode("utf-8", "ignore")
            Domoticz.Log(strVerb+" request received.")
            data = "<!doctype html><html><head></head><body><h1>Successful GET!!!</h1><body></html>"

            if (Connection != self.httpClientConn):
               httpClientConn =  self.httpServerConns[Connection.Name]
            else:
                httpClientConn = self.httpClientConn

            if (strVerb == "GET"):
                httpClientConn.Send({"Status":"200 OK", "Headers": {"Connection": "keep-alive", "Accept": "Content-Type: text/html; charset=UTF-8"}, "Data": data})
            elif (strVerb == "POST"):
                httpClientConn.Send({"Status":"200 OK", "Headers": {"Connection": "keep-alive", "Accept": "Content-Type: text/html; charset=UTF-8"}, "Data": data})
            else:
                Domoticz.Error("Unknown verb in request: "+strVerb)


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

