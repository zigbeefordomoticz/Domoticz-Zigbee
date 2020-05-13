#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz


def  startWebServer( self ):

    #self.httpPort = '9440'
    self.httpServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTP", Port=self.httpPort)
    self.httpServerConn.Listen()
    self.logging( 'Status', "Web backend for Web User Interface started on port: %s" %self.httpPort)

    #self.httpsPort = '9443'
    #self.httpsServerConn = Domoticz.Connection(Name="Zigate Server Connection", Transport="TCP/IP", Protocol="HTTPS", Port=self.httpsPort)
    #self.httpsServerConn.Listen()
    #self.logging( 'Status', "Web backend for Web User Interface started on port: %s" %self.httpsPort)len(fileContent))+" bytes will be returned")