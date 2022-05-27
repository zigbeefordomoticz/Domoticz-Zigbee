#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_DomoticzDico.py

    Description: Retreive & Build Domoticz Dictionary

"""

import sqlite3
import Domoticz
import os.path
from base64 import b64decode
from time import time
from datetime import datetime
from Classes.LoggingManagement import LoggingManagement
import urllib
import json

CACHE_TIMEOUT = (15 * 60) + 15  # num seconds

DOMOTICZ_SETTINGS_API = "json.htm?type=settings"
DOMOTICZ_HARDWARE_API = "json.htm?type=hardware"
DOMOTICZ_DEVICEST_API = "json.htm?type=devices&rid="




class DomoticzDB_Preferences:
    # sourcery skip: replace-interpolation-with-fstring
    
    def __init__(self, database, pluginconf, log):
        self.dbConn = None
        self.dbCursor = None
        self.preferences = {}
        self.pluginconf = pluginconf
        self.log = log
        self.load_preferences()


    def load_preferences(self):
        # sourcery skip: replace-interpolation-with-fstring
        url = "http://127.0.0.1:%s/%s" %(self.pluginconf.pluginConf["port"], DOMOTICZ_SETTINGS_API)
        response = urllib.request.urlopen( url )
        self.preferences = json.loads( response.read() )
        
    def logging(self, logType, message):
        # sourcery skip: replace-interpolation-with-fstring
        self.log.logging("DZDB", logType, message)

    def retreiveAcceptNewHardware(self):
        # sourcery skip: replace-interpolation-with-fstring
        return self.preferences['AcceptNewHardware']

    def retreiveWebUserNamePassword(self):
        # sourcery skip: replace-interpolation-with-fstring
        return '', ''



class DomoticzDB_Hardware:
    def __init__(self, database, pluginconf, hardwareID, log):
        self.dbConn = None
        self.dbCursor = None
        self.hardware = {}
        self.HardwareID = hardwareID
        self.database = database
        self.pluginconf = pluginconf
        self.log = log
        self.load_hardware()

    def load_hardware(self):  
        # sourcery skip: replace-interpolation-with-fstring
        url = "http://127.0.0.1:%s/%s" %(self.pluginconf.pluginConf["port"], DOMOTICZ_HARDWARE_API)
        response = urllib.request.urlopen( url )
        result = json.loads( response.read() )
        for x in result['result']:
            idx = x[ "idx" ]
            self.hardware[ idx ] = x

    def logging(self, logType, message):
        self.log.logging("DZDB", logType, message)

    def disableErasePDM(self):
        pass

    def get_loglevel_value(self):
        # sourcery skip: replace-interpolation-with-fstring
        return self.hardware[ '%s' %self.HardwareID ]['LogLevel']

    def multiinstances_z4d_plugin_instance(self):
        return sum("Zigate" in self.hardware[ x ]["Extra"] for x in self.hardware)



class DomoticzDB_DeviceStatus:
    def __init__(self, database, pluginconf, hardwareID, log):
        self.database = database
        self.dbConn = None
        self.dbCursor = None
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log
        self.AdjValue = {"Baro": {}, "TimeOutMotion": {}, "Temp": {}}

    def logging(self, logType, message):
        # sourcery skip: replace-interpolation-with-fstring
        self.log.logging("DZDB", logType, message)


    def get_device_status(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        url = "http://127.0.0.1:%s/%s%s" %(self.pluginconf.pluginConf["port"], DOMOTICZ_DEVICEST_API, "%s" %ID)
        response = urllib.request.urlopen( url )
        result = json.loads( response.read() )
        Domoticz.Log("Result: %s" %result)
        return result
    
        
    def retreiveAddjValue_baro(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        """
        Retreive the AddjValue of Device.ID
        """
        result = self.get_device_status( ID)
        AdjValue = 0
        for x in result[ 'result' ]:
            AdjValue = x [ 'AddjValue2'] 
        Domoticz.Log( "retreiveAddjValue_baro %s" %  AdjValue)    
        return AdjValue

    def retreiveTimeOut_Motion(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        """
        Retreive the TmeeOut Motion value of Device.ID
        """
        result = self.get_device_status( ID)
        AdjValue = 0
        for x in result[ 'result' ]:
            AdjValue = x [ 'AddjValue']    
        Domoticz.Log( "retreiveTimeOut_Motion %s" %  AdjValue)      
        return AdjValue

    def retreiveAddjValue_temp(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        """
        Retreive the AddjValue of Device.ID
        """
        result = self.get_device_status( ID)
        AdjValue = 0
        for x in result[ 'result' ]:
            AdjValue = x [ 'AddjValue']
        Domoticz.Log( "retreiveAddjValue_temp %s" %  AdjValue)    
        return AdjValue