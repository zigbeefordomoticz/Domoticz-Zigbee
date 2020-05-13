#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz


def startWebServer( self ):

    #self.httpPort = '9440'
    self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port=self.httpPort)
    self.httpServerConn.Listen()
    self.logging( 'Status', "Web backend for Web User Interface started on port: %s" %self.httpPort)

    #self.httpsPort = '9443'
    #self.httpsServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTPS", Port=self.httpsPort)
    #self.httpsServerConn.Listen()
    #self.logging( 'Status', "Web backend for Web User Interface started on port: %s" %self.httpsPort)len(fileContent))+" bytes will be returned")

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
