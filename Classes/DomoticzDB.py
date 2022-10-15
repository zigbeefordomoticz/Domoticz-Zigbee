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
import urllib.request

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
    items[0] = items[0][:4].lower() + items[0][4:]
    item1 = items[0].replace('http://','')
    usernamepassword = item1.split(':')
    if len(usernamepassword) != 2:
        self.logging("Error", f'We are expecting a username and password but do not find it in {url_base_api} ==> {items} ==> {item1} ==> {usernamepassword}')
        return None, None, None
        
    username, password = usernamepassword
    return username, password, host_port

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

def domoticz_request( self, url):
    self.logging("Debug",'domoticz request url: %s' %url)
    try:
        request = urllib.request.Request(url)
    except urllib.error.URLError:
        self.logging("Error", "domoticz_request - wrong URL to get access to Domoticz JSON/API: %s" %url)
        return None
    
    self.logging("Debug",'domoticz request result: %s' %request)
    if self.authentication_str:
        self.logging("Debug",'domoticz request Authorization: %s' %request)
        request.add_header("Authorization", "Basic %s" % self.authentication_str)
    self.logging("Debug",'domoticz request open url')
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.URLError:
        self.logging("Error", "domoticz_request - wrong URL toget access to Domoticz JSON/API: %s" %url)
        return None
    
    return response.read()
  
def domoticz_base_url(self):
    
    if self.url_ready:
        self.logging( "Debug", "domoticz_base_url - API URL ready %s Basic Authentication: %s" %(self.url_ready, self.authentication_str))
        return self.url_ready
    
    username, password, host_port = extract_username_password( self, self.api_base_url )
    self.logging("Debug",'Username: %s' %username)
    self.logging("Debug",'Password: %s' %password)
    self.logging("Debug",'Host+port: %s' %host_port)

    if len(self.api_base_url) == 0:
        # Seems that the field is empty
        self.logging( "Error", "You need to setup the URL Base to access the Domoticz JSON/API")
        return None
        
    # Check that last char is not a / , if the case then remove it 
    if self.api_base_url[-1] == '/':
        self.api_base_url = self.api_base_url[:-1]
    if username and password and host_port:
        self.authentication_str = base64.encodebytes(('%s:%s' %(username, password)).encode()).decode().replace('\n','')
        url = 'http://' + host_port + '/json.htm?' + 'username=%s&password=%s&' %(username, password)
    else:
        url = self.api_base_url + '/json.htm?'
    self.logging("Debug", "url: %s" %url)
    self.url_ready = url
    return url      

class DomoticzDB_Preferences:
    # sourcery skip: replace-interpolation-with-fstring
    
    def __init__(self, api_base_url, pluginconf, log):
        self.api_base_url = api_base_url
        self.preferences = {}
        self.pluginconf = pluginconf
        self.log = log
        self.authentication_str = None
        self.url_ready = None
        self.load_preferences()


    def load_preferences(self):
        # sourcery skip: replace-interpolation-with-fstring
        url = domoticz_base_url(self)
        if url is None:
            return
        url += DOMOTICZ_HARDWARE_API

        dz_response = domoticz_request( self, url)
        if dz_response is None:
            return

        self.preferences = json.loads( dz_response )
        
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
        self.authentication_str = None
        self.url_ready = None
        self.hardware = {}
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log
        self.pluginParameters = pluginParameters
        self.load_hardware()

    def load_hardware(self):  
        # sourcery skip: replace-interpolation-with-fstring
        url = domoticz_base_url(self)
        if url is None:
            return
        url += DOMOTICZ_HARDWARE_API

        dz_result = domoticz_request( self, url)
        if dz_result is None:
            return
        result = json.loads( dz_result )
        
        for x in result['result']:
            idx = x[ "idx" ]
            self.hardware[ idx ] = x

    def logging(self, logType, message):
        self.log.logging("DZDB", logType, message)

    def disableErasePDM(self, webUserName, webPassword):
        # sourcery skip: replace-interpolation-with-fstring
        # To disable the ErasePDM, we have to restart the plugin
        # This is usally done after ErasePDM
        restartPluginViaDomoticzJsonApi(self, stop=False, url_base_api=self.api_base_url)

    def get_loglevel_value(self):
        # sourcery skip: replace-interpolation-with-fstring
        if self.hardware and ("%s" %self.HardwareID) in self.hardware: 
            self.logging("Debug", "get_loglevel_value %s " %(self.hardware[ '%s' %self.HardwareID ]['LogLevel']))
            return self.hardware[ '%s' %self.HardwareID ]['LogLevel']
        return 7

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
        self.authentication_str = None
        self.url_ready = None

    def logging(self, logType, message):
        # sourcery skip: replace-interpolation-with-fstring
        self.log.logging("DZDB", logType, message)

    def get_device_status(self, ID):
        # "http://%s:%s@127.0.0.1:%s" 
        # sourcery skip: replace-interpolation-with-fstring
        url = domoticz_base_url(self)
        if url is None:
            return
        url += DOMOTICZ_DEVICEST_API + "%s" %ID

        dz_result = domoticz_request( self, url)
        if dz_result is None:
            return None
        result = json.loads( dz_result )
        self.logging("Debug", "Result: %s" %result)
        return result
    
    def extract_AddValue(self, ID, attribute):
        # sourcery skip: replace-interpolation-with-fstring
        result = self.get_device_status( ID)
        if result is None:
            return 0
        
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
