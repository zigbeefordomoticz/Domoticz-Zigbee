#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_DomoticzDico.py

    Description: Retreive & Build Domoticz Dictionary

"""


import Domoticz

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
        self.logging("Debug", "retreiveAcceptNewHardware status %s" %self.preferences['AcceptNewHardware'])
        return self.preferences['AcceptNewHardware']

    def retreiveWebUserNamePassword(self):
        # sourcery skip: replace-interpolation-with-fstring
        self.logging("Debug", "retreiveWebUserNamePassword %s %s" %('', ''))
        return '', ''



class DomoticzDB_Hardware:
    def __init__(self, database, pluginconf, hardwareID, log):
        self.hardware = {}
        self.HardwareID = hardwareID
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
        # sourcery skip: replace-interpolation-with-fstring
        self.logging("Debug", "disableErasePDM %s " %("Not implemented Yet"))
        

    def get_loglevel_value(self):
        # sourcery skip: replace-interpolation-with-fstring
        self.logging("Debug", "get_loglevel_value %s " %(self.hardware[ '%s' %self.HardwareID ]['LogLevel']))
        return self.hardware[ '%s' %self.HardwareID ]['LogLevel']

    def multiinstances_z4d_plugin_instance(self):
        # sourcery skip: replace-interpolation-with-fstring
        self.logging("Debug", "multiinstances_z4d_plugin_instance")
        return sum("Zigate" in self.hardware[ x ]["Extra"] for x in self.hardware)



class DomoticzDB_DeviceStatus:
    def __init__(self, database, pluginconf, hardwareID, log):
        self.database = database
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log

    def logging(self, logType, message):
        # sourcery skip: replace-interpolation-with-fstring
        self.log.logging("DZDB", logType, message)

    def get_device_status(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        url = "http://127.0.0.1:%s/%s%s" %(self.pluginconf.pluginConf["port"], DOMOTICZ_DEVICEST_API, "%s" %ID)
        response = urllib.request.urlopen( url )
        result = json.loads( response.read() )
        self.logging("Debug", "Result: %s" %result)
        return result
    
    def extract_AddValue(self, ID, attribute):
        # sourcery skip: replace-interpolation-with-fstring
        result = self.get_device_status( ID)
        AdjValue = 0
        for x in result[ 'result' ]:
            AdjValue = x [ attribute ]    
        self.logging("Debug", "return extract_AddValue %s %s %s" % (ID, attribute, AdjValue)  )  
        return AdjValue
       
    def retreiveAddjValue_baro(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        return self.extract_AddValue( ID, 'AddjValue2')

    def retreiveTimeOut_Motion(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        """
        Retreive the TmeeOut Motion value of Device.ID
        """
        return self.extract_AddValue( ID, 'AddjValue')  


    def retreiveAddjValue_temp(self, ID):
        # sourcery skip: replace-interpolation-with-fstring
        """
        Retreive the AddjValue of Device.ID
        """
        return self.extract_AddValue( ID, 'AddjValue')      