#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

MAX_KB_TO_SEND = 8 * 1024   # Chunk size
DEBUG_HTTP = False


def keepConnectionAlive( self ):

    self.heartbeats += 1


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
