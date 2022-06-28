#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_DomoticzDico.py

    Description: Retreive & Build Domoticz Dictionary

"""


import base64
import binascii
import json
import socket
import time
import urllib

import Domoticz

from Modules.restartPlugin import restartPluginViaDomoticzJsonApi
from Classes.LoggingManagement import LoggingManagement

CACHE_TIMEOUT = (15 * 60) + 15  # num seconds

DOMOTICZ_SETTINGS_API = "type=settings"
DOMOTICZ_HARDWARE_API = "type=hardware"
DOMOTICZ_DEVICEST_API = "type=devices&rid="

def isBase64( sb ):    
    try:
        return base64.b64encode(base64.b64decode(sb)).decode() == sb
    except TypeError:
        return False
    except binascii.Error:
        return False
    
def extract_username_password( self, url_base_api ):
    
    items = url_base_api.split('@')
    if len(items) != 2:
        return None, None, None
    self.logging("Debug", f'Extract username/password {url_base_api} ==> {items} ')
    host_port = items[1]
    item1 = items[0].replace('http://','')
    usernamepassword = item1.split(':')
    if len(usernamepassword) != 2:
        self.logging("Error", f'We are expecting a username and password but do not find it in {url_base_api} ==> {items} ==> {item1} ==> {usernamepassword}')
        return None, None, None
        
    username, password = usernamepassword
    if isBase64( username ) and isBase64( password):
        return username, password, host_port
    return (base64.b64encode( username.encode('ascii'))).decode('utf-8'), (base64.b64encode( password.encode('ascii'))).decode('utf-8'), host_port

def open_and_read( self, url ):
    
    retry = 3
    while retry:
        try:
            with urllib.request.urlopen(url) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code in [429,504]:  # 429=too many requests, 504=gateway timeout
                reason = f'{e.code} {str(e.reason)}'
            elif isinstance(e.reason, socket.timeout):
                reason = f'HTTPError socket.timeout {e.reason} - {e}'
            else:
                raise
        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                reason = f'URLError socket.timeout {e.reason} - {e}'
            else:
                raise
        except socket.timeout as e:
            reason = f'socket.timeout {e}'
        netloc = urllib.parse.urlsplit(url).netloc  # e.g. nominatim.openstreetmap.org
        self.logging("Error", f'*** {netloc} {reason}; will retry')
        time.sleep(1)
        retry -= 1

class DomoticzDB_Preferences:
    # sourcery skip: replace-interpolation-with-fstring
    
    def __init__(self, api_base_url, pluginconf, log):
        self.api_base_url = api_base_url
        self.preferences = {}
        self.pluginconf = pluginconf
        self.log = log
        self.load_preferences()


    def load_preferences(self):
        # sourcery skip: replace-interpolation-with-fstring
        username, password, host_port = extract_username_password( self, self.api_base_url )
        if username and password and host_port:
            url = 'http://' + host_port + '/json.htm?' + 'username=%s&password=%s&' %(username, password)
        else:
            url = self.api_base_url + '/json.htm?'
        
        url += DOMOTICZ_HARDWARE_API
        
        self.logging("Debug", "url: %s" %url)
        self.logging("Debug",'Username: %s' %username)
        self.logging("Debug",'Password: %s' %password)
        self.logging("Debug",'Host+port: %s' %host_port)
        
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
        webUserName = webPassword = ''
        if 'WebPassword' in self.preferences:
            webPassword = self.preferences['WebPassword']
        if 'WebUserName' in self.preferences:
            webUserName = self.preferences['WebUserName']
        self.logging("Debug", "retreiveWebUserNamePassword %s %s" %(webUserName, webPassword))   
        return webUserName, webPassword



class DomoticzDB_Hardware:
    def __init__(self, api_base_url, pluginconf, hardwareID, log, pluginParameters):
        self.api_base_url = api_base_url

        self.hardware = {}
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log
        self.pluginParameters = pluginParameters
        self.load_hardware()

    def load_hardware(self):  
        # sourcery skip: replace-interpolation-with-fstring
        username, password, host_port = extract_username_password( self, self.api_base_url )
        if username and password and host_port:
            url = 'http://' + host_port + '/json.htm?' + 'username=%s&password=%s&' %(username, password)
        else:
            url = self.api_base_url + '/json.htm?'

        url += DOMOTICZ_HARDWARE_API

        self.logging("Debug", "url: %s" %url)
        self.logging("Debug",'Username: %s' %username)
        self.logging("Debug",'Password: %s' %password)
        self.logging("Debug",'Host+port: %s' %host_port)

        response = urllib.request.urlopen( url )
        result = json.loads( response.read() )
        for x in result['result']:
            idx = x[ "idx" ]
            self.hardware[ idx ] = x

    def logging(self, logType, message):
        self.log.logging("DZDB", logType, message)

    def disableErasePDM(self, webUserName, webPassword):
        # sourcery skip: replace-interpolation-with-fstring
        # To disable the ErasePDM, we have to restart the plugin
        # This is usally done after ErasePDM
        restartPluginViaDomoticzJsonApi(self, stop=True, url_base_api=self.api_base_url)

    def get_loglevel_value(self):
        # sourcery skip: replace-interpolation-with-fstring
        self.logging("Debug", "get_loglevel_value %s " %(self.hardware[ '%s' %self.HardwareID ]['LogLevel']))
        return self.hardware[ '%s' %self.HardwareID ]['LogLevel']

    def multiinstances_z4d_plugin_instance(self):
        # sourcery skip: replace-interpolation-with-fstring
        self.logging("Debug", "multiinstances_z4d_plugin_instance")
        if sum("Zigate" in self.hardware[ x ]["Extra"] for x in self.hardware) > 1:
            return True
        return False

class DomoticzDB_DeviceStatus:
    def __init__(self, api_base_url, pluginconf, hardwareID, log):
        self.api_base_url = api_base_url
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log

    def logging(self, logType, message):
        # sourcery skip: replace-interpolation-with-fstring
        self.log.logging("DZDB", logType, message)

    def get_device_status(self, ID):
        # "http://%s:%s@127.0.0.1:%s" 
        # sourcery skip: replace-interpolation-with-fstring
        username, password, host_port = extract_username_password( self, self.api_base_url )
        if username and password and host_port:
            url = 'http://' + host_port + '/json.htm?' + 'username=%s&password=%s&' %(username, password)
        else:
            url = self.api_base_url + '/json.htm?'

        url += DOMOTICZ_DEVICEST_API + "%s" %ID

        self.logging("Debug", "url: %s" %url)
        self.logging("Debug",'Username: %s' %username)
        self.logging("Debug",'Password: %s' %password)
        self.logging("Debug",'Host+port: %s' %host_port)

        response = urllib.request.urlopen( url )
        result = json.loads( response.read() )
        self.logging("Debug", "Result: %s" %result)
        return result
    
    def extract_AddValue(self, ID, attribute):
        # sourcery skip: replace-interpolation-with-fstring
        result = self.get_device_status( ID)
        AdjValue = 0
        for x in result['result']:
            AdjValue = x[attribute]    
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