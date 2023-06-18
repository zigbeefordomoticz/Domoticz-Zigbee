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
import ssl
import Domoticz

from Modules.restartPlugin import restartPluginViaDomoticzJsonApi
from Classes.LoggingManagement import LoggingManagement
from Modules.tools import is_domoticz_new_API

CACHE_TIMEOUT = (15 * 60) + 15  # num seconds

def init_domoticz_api(self):
    
    if is_domoticz_new_API(self):
        self.logging("Debug", 'Init domoticz api based on new api')
        init_domoticz_api_settings(
            self,
            "type=command&param=getsettings",
            "type=command&param=gethardware",
            "type=command&param=getdevices&rid=",
        )
    else:
        self.logging("Debug", 'Init domoticz api based on old api')
        init_domoticz_api_settings(
            self, "type=settings", "type=hardware", "type=devices&rid="
        )
        
def init_domoticz_api_settings(self, settings_api, hardware_api, devices_api):
    self.DOMOTICZ_SETTINGS_API = settings_api
    self.DOMOTICZ_HARDWARE_API = hardware_api
    self.DOMOTICZ_DEVICEST_API = devices_api


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
        return None, None, None, None
    
    self.logging("Debug", f'Extract username/password {url_base_api} ==> {items} ')
    host_port = items[1]
    proto = None
    if items[0].find("https") == 0:
        proto = 'https'
        items[0] = items[0][:5].lower() + items[0][5:]
        item1 = items[0].replace('https://','')
        usernamepassword = item1.split(':')
        if len(usernamepassword) == 2:
            username, password = usernamepassword
            return username, password, host_port, proto
        self.logging("Error", f'We are expecting a username and password but do not find it in {url_base_api} ==> {items} ==> {item1} ==> {usernamepassword}')
            
    elif items[0].find("http") == 0:
        proto = 'http'
        items[0] = items[0][:4].lower() + items[0][4:]
        item1 = items[0].replace('http://','')
        usernamepassword = item1.split(':')
        if len(usernamepassword) == 2:
            username, password = usernamepassword
            return username, password, host_port, proto
        self.logging("Error", f'We are expecting a username and password but do not find it in {url_base_api} ==> {items} ==> {item1} ==> {usernamepassword}')

    self.logging("Error", f'We are expecting a username and password but do not find it in {url_base_api} ==> {items} ')
    return None, None, None, None
        

def open_and_read( self, url ):
    self.logging("Log", f'opening url {url}')
    
    myssl_context = None
    if "https" in url.lower() and not self.pluginconf.pluginConf["CheckSSLCertificateValidity"]:
        myssl_context = ssl.create_default_context()
        myssl_context.check_hostname=False
        myssl_context.verify_mode=ssl.CERT_NONE
    
    retry = 3
    while retry:
        try:
            self.logging("Debug", f'opening url {url} with context {myssl_context}')
            with urllib.request.urlopen(url, context=myssl_context) as response:
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
    except urllib.error.URLError as e:
        self.logging("Error", "Request to %s rejected. Error: %s" %(url, e))
        return None
    
    self.logging("Debug",'domoticz request result: %s' %request)
    if self.authentication_str:
        self.logging("Debug",'domoticz request Authorization: %s' %request)
        request.add_header("Authorization", "Basic %s" % self.authentication_str)
    self.logging("Debug",'domoticz request open url')
    
    myssl_context = None
    if "https" in url.lower() and not self.pluginconf.pluginConf["CheckSSLCertificateValidity"]:
        myssl_context = ssl.create_default_context()
        myssl_context.check_hostname=False
        myssl_context.verify_mode=ssl.CERT_NONE

    try:
        self.logging("Debug", f'opening url {request} with context {myssl_context}')
        response = urllib.request.urlopen(request, context=myssl_context)
    except urllib.error.URLError as e:
        self.logging("Error", "Urlopen to %s rejected. Error: %s" %(url, e))
        return None
    
    return response.read()
  
def domoticz_base_url(self):
    
    if self.url_ready:
        self.logging( "Debug", "domoticz_base_url - API URL ready %s Basic Authentication: %s" %(self.url_ready, self.authentication_str))
        return self.url_ready
    
    username, password, host_port, proto = extract_username_password( self, self.api_base_url )
    
    self.logging("Debug",'Username: %s' %username)
    self.logging("Debug",'Password: %s' %password)
    self.logging("Debug",'Host+port: %s' %host_port)

    if len(self.api_base_url) == 0:
        # Seems that the field is empty
        self.logging( "Error", "You need to setup the URL Base to access the Domoticz JSON/API")
        return None
        
    # Check that last char is not a / , if the case then remove it 
    # https://www.domoticz.com/wiki/Security / https://username:password@IP:PORT/json.htm 
    if self.api_base_url[-1] == '/':
        self.api_base_url = self.api_base_url[:-1]
    if username and password and host_port:
        self.authentication_str = base64.encodebytes(('%s:%s' %(username, password)).encode()).decode().replace('\n','')
        url = f"{proto}://{host_port}/json.htm?"
    else:
        url = self.api_base_url + '/json.htm?'
    self.logging("Debug", "url: %s" %url)
    self.url_ready = url
    return url      

class DomoticzDB_Preferences:
    # sourcery skip: replace-interpolation-with-fstring
    
    def __init__(self, api_base_url, pluginconf, log, DomoticzBuild, DomoticzMajor, DomoticzMinor):
        self.api_base_url = api_base_url
        self.preferences = {}
        self.pluginconf = pluginconf
        self.log = log
        self.authentication_str = None
        self.url_ready = None
        self.DomoticzBuild = DomoticzBuild
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor
        init_domoticz_api(self)
        self.load_preferences()


    def load_preferences(self):
        # sourcery skip: replace-interpolation-with-fstring
        url = domoticz_base_url(self)
        if url is None:
            return
        url += self.DOMOTICZ_HARDWARE_API

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
    def __init__(self, api_base_url, pluginconf, hardwareID, log, pluginParameters, DomoticzBuild, DomoticzMajor, DomoticzMinor):
        self.api_base_url = api_base_url
        self.authentication_str = None
        self.url_ready = None
        self.hardware = {}
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log
        self.pluginParameters = pluginParameters
        self.DomoticzBuild = DomoticzBuild
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor

        init_domoticz_api(self)
        self.load_hardware()

    def load_hardware(self):  
        # sourcery skip: replace-interpolation-with-fstring
        url = domoticz_base_url(self)
        if url is None:
            return
        url += self.DOMOTICZ_HARDWARE_API

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
        if (
            self.hardware 
            and ("%s" %self.HardwareID) in self.hardware
            and 'LogLevel' in self.hardware[ '%s' %self.HardwareID ]
        ): 
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
    def __init__(self, api_base_url, pluginconf, hardwareID, log, DomoticzBuild, DomoticzMajor, DomoticzMinor):
        self.api_base_url = api_base_url
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log
        self.authentication_str = None
        self.url_ready = None
        self.DomoticzBuild = DomoticzBuild
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor

        init_domoticz_api(self)

    def logging(self, logType, message):
        # sourcery skip: replace-interpolation-with-fstring
        self.log.logging("DZDB", logType, message)

    def get_device_status(self, ID):
        # "http://%s:%s@127.0.0.1:%s" 
        # sourcery skip: replace-interpolation-with-fstring
        url = domoticz_base_url(self)
        if url is None:
            return
        url += self.DOMOTICZ_DEVICEST_API + "%s" %ID

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
