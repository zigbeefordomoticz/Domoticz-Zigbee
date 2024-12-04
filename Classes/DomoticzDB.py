#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

""" This Classe allow retreiving and settings information in Domoticz via the JSON API """

import base64
import binascii
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from Modules.restartPlugin import restartPluginViaDomoticzJsonApi
from Modules.tools import is_domoticz_new_API

REQ_TIMEOUT = .750  # 750 ms Timeout


def init_domoticz_api(self):
    """
    Initializes the Domoticz API by determining whether to use the new or old API format.
    """
    is_new_api = is_domoticz_new_API(self)
    self.logging(
        "Debug",
        f"Initializing Domoticz API using {'new' if is_new_api else 'old'} API format"
    )
    
    api_settings = {
        "new": (
            "type=command&param=getsettings",
            "type=command&param=gethardware",
            "type=command&param=getdevices&rid=",
        ),
        "old": (
            "type=settings",
            "type=hardware",
            "type=devices&rid=",
        ),
    }
    
    selected_settings = api_settings["new"] if is_new_api else api_settings["old"]
    init_domoticz_api_settings(self, *selected_settings)

        
def init_domoticz_api_settings(self, settings_api, hardware_api, devices_api):
    self.DOMOTICZ_SETTINGS_API = settings_api
    self.DOMOTICZ_HARDWARE_API = hardware_api
    self.DOMOTICZ_DEVICEST_API = devices_api


def isBase64(sb):
    """
    Checks if the given string is valid Base64.
    :param sb: The string to check.
    :return: True if the string is valid Base64, False otherwise.
    """
    try:
        return base64.b64encode(base64.b64decode(sb)).decode() == sb
    except (TypeError, binascii.Error):
        return False
   

def extract_username_password(self, url_base_api):
    """
    Extracts the username, password, host, and protocol from a URL.
    :param url_base_api: The URL containing credentials in the format <proto>://<username>:<password>@<host>
    :return: A tuple (username, password, host_port, proto) or (None, None, None, None) if invalid.
    """
    items = url_base_api.split('@')
    if len(items) != 2:
        self.logging("Debug", f"no credentials in the URL: {url_base_api}")
        return None, None, None, None
    
    self.logging("Debug", f"Extracting username/password from {url_base_api} ==> {items}")
    
    proto = None
    credentials, host_port = items
    if credentials.startswith("https://"):
        proto = "https"
        credentials = credentials[8:]  # Remove 'https://'
    elif credentials.startswith("http://"):
        proto = "http"
        credentials = credentials[7:]  # Remove 'http://'
    else:
        self.logging("Error", f"Unsupported protocol in URL: {url_base_api}")
        return None, None, None, None

    username_password = credentials.split(':', 1)
    if len(username_password) == 2:
        username, password = username_password
        return username, password, host_port, proto
    
    self.logging("Error", f"Missing username or password in {url_base_api} ==> {credentials} ==> {username_password}")
    return None, None, None, None
        

def open_and_read(self, url):
    """
    Opens a URL and reads the response with optional SSL context, retries, and a timeout.
    :param url: The URL to open.
    :return: Response content or None if the request fails.
    """
    self.logging("Log", f"Opening URL: {url}")

    # Set up SSL context if necessary
    ssl_context = None
    if "https" in url.lower() and not self.pluginconf.pluginConf["CheckSSLCertificateValidity"]:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    for retries in range(3, 0, -1):
        try:
            self.logging("Log", f"Opening URL: {url} with SSL context: {ssl_context} and REQ_TIMEOUT timeout")
            with urllib.request.urlopen(url, context=ssl_context, timeout=REQ_TIMEOUT) as response:
                return response.read()

        except urllib.error.HTTPError as e:
            if e.code in [429, 504]:
                reason = f"{e.code} {e.reason}"
            elif isinstance(e.reason, socket.timeout):
                reason = f"HTTPError socket.timeout {e.reason} - {e}"
            else:
                raise

        except (urllib.error.URLError, socket.timeout) as e:
            reason = f"{type(e).__name__} {e.reason}" if hasattr(e, 'reason') else str(e)

        # Log retry information
        netloc = urlsplit(url).netloc
        self.logging("Error", f"*** {netloc} {reason}; retrying ({retries - 1} attempts left)")
        time.sleep(1)
    

def domoticz_request(self, url):
    """
    Makes a request to the given Domoticz URL with optional SSL context, authentication, and a timeout.
    :param url: The target URL.
    :return: Response content or None if the request fails.
    """
    self.logging("Debug", f"Domoticz request URL: {url}")
    
    # Create the request object
    try:
        request = urllib.request.Request(url)
    except ValueError as e:
        self.logging("Error", f"Invalid URL: {url}. Error: {e}")
        return None
    
    # Add authorization header if available
    if self.authentication_str:
        request.add_header("Authorization", f"Basic {self.authentication_str}")
        self.logging("Debug", "Authorization header added to request.")
    
    # Set up SSL context if necessary
    ssl_context = None
    if url.lower().startswith("https") and not self.pluginconf.pluginConf["CheckSSLCertificateValidity"]:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    
    # Open the URL with a 750ms timeout
    try:
        self.logging("Status", f"Opening URL: {url} with SSL context: {ssl_context} and REQ_TIMEOUT timeout")
        with urllib.request.urlopen(request, context=ssl_context, timeout=REQ_TIMEOUT) as response:
            return response.read()
    except urllib.error.URLError as e:
        self.logging("Error", f"Request to {url} failed. Error: {e}")
    except socket.timeout:
        self.logging("Error", f"Request to {url} timed out after 750ms.")
    except Exception as e:
        self.logging("Error", f"Unexpected error occurred for URL {url}: {e}")
    
    return None


def domoticz_base_url(self):
    """
    Returns the base URL for the Domoticz API, either from the configuration (if we have processed it once)
    or by constructing it using credentials and host information.
    """
    
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
    """ interact in Read Only with the Domoticz Preferences Table (Domoticz Settings) """

    def __init__(self, api_base_url, pluginconf, log, DomoticzBuild, DomoticzMajor, DomoticzMinor):
        """
        Initializes the DomoticzDB_Preferences class with the necessary parameters
        and loads the preferences from the Domoticz API.
        """
        self.api_base_url = api_base_url
        self.url_ready = None
        self.preferences = {}
        self.pluginconf = pluginconf
        self.log = log
        self.authentication_str = None
        self.url_ready = None
        self.DomoticzBuild = DomoticzBuild
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor
        
        # Initialize API settings and load preferences
        init_domoticz_api(self)
        self.load_preferences()

    def load_preferences(self):
        """
        Loads preferences from the Domoticz API and stores them in the preferences attribute.
        """
        url = domoticz_base_url(self)
        if not url:
            return

        url += self.DOMOTICZ_HARDWARE_API
        dz_response = domoticz_request(self, url)
        if dz_response:
            self.preferences = json.loads(dz_response)

    def logging(self, logType, message):
        """
        Logs messages to the specified log with the given log type.
        """
        self.log.logging("DZDB", logType, message)

    def retrieve_accept_new_hardware(self):
        """
        Retrieves the 'AcceptNewHardware' status from the preferences.
        """
        accept_new_hardware = self.preferences.get('AcceptNewHardware', False)
        self.logging("Debug", f"retrieve_accept_new_hardware status {accept_new_hardware}")
        return accept_new_hardware

    def retrieve_web_user_name_password(self):
        """
        Retrieves the web username and password from the preferences.
        """
        web_user_name = self.preferences.get('WebUserName', '')
        web_password = self.preferences.get('WebPassword', '')
        self.logging("Debug", f"retrieve_web_user_name_password {web_user_name} {web_password}")
        return web_user_name, web_password


class DomoticzDB_Hardware:
    """ interact in Read Write with the Domoticz Hardware Table (Domoticz Plugins) """

    def __init__(self, api_base_url, pluginconf, hardwareID, log, pluginParameters, DomoticzBuild, DomoticzMajor, DomoticzMinor):
        """ Initializes the DomoticzDB_Hardware class with the necessary parameters and loads hardware information. """
        self.api_base_url = api_base_url
        self.url_ready = None
        self.authentication_str = None
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
        """ Loads hardware data from the Domoticz API and stores it in the hardware attribute. """
        url = domoticz_base_url(self)
        if not url:
            return

        url += self.DOMOTICZ_HARDWARE_API
        dz_result = domoticz_request(self, url)
        if dz_result:
            result = json.loads(dz_result)
            for x in result.get('result', []):
                self.hardware[x["idx"]] = x

    def logging(self, logType, message):
        """ Logs messages to the specified log with the given log type. """
        self.log.logging("DZDB", logType, message)

    def disable_erase_pdm(self, webUserName, webPassword):
        """ Disables the ErasePDM feature by restarting the plugin. """
        restartPluginViaDomoticzJsonApi(self, stop=False, url_base_api=self.api_base_url)

    def get_loglevel_value(self):
        """ Retrieves the log level for the hardware, defaults to 7 if not found. """
        hardware_info = self.hardware.get(str(self.HardwareID), {})
        log_level = hardware_info.get('LogLevel', 7)
        self.logging("Debug", f"get_loglevel_value {log_level}")
        return log_level

    def multiinstances_z4d_plugin_instance(self):
        """ Checks if there are multiple instances of the Z4D plugin running. """
        self.logging("Debug", "multiinstances_z4d_plugin_instance")
        return sum("Zigate" in x.get("Extra", "") for x in self.hardware.values()) > 1


class DomoticzDB_DeviceStatus:
    """
    Interact in Read Only with the Domoticz DeviceStatus Table (Domoticz Devices).
    This mainly is used to retrieve the Adjusted Value parameters for Temp/Baro and the Motion delay.
    """

    def __init__(self, api_base_url, pluginconf, hardwareID, log, DomoticzBuild, DomoticzMajor, DomoticzMinor):
        """
        Initializes the DomoticzDB_DeviceStatus class with the necessary parameters.
        """
        self.api_base_url = api_base_url
        self.url_ready = None
        self.HardwareID = hardwareID
        self.pluginconf = pluginconf
        self.log = log
        self.authentication_str = None
        self.DomoticzBuild = DomoticzBuild
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor
        self.cache = {}  # Caching device status data

        init_domoticz_api(self)

    def logging(self, logType, message):
        """Logs messages with the specified log type."""
        self.log.logging("DZDB", logType, message)

    def _get_cached_device_status(self, device_id):
        """Returns the cached device status if it's still valid."""
        cached_entry = self.cache.get(device_id)
        if cached_entry:
            timestamp, data = cached_entry
            self.logging("Debug", f"Using cached data for device ID {device_id}: {data}")
            return data
        return None

    def _cache_device_status(self, device_id, data):
        """Caches the device status with the current timestamp."""
        self.cache[device_id] = (time.time(), data)
        self.logging("Debug", f"Cached data for device ID {device_id}")

    def get_device_status(self, device_id):
        """
        Retrieves the device status for a given device ID, with caching.
        """
        # Check if data is already cached
        cached_data = self._get_cached_device_status(device_id)
        if cached_data is not None:
            return cached_data

        # If not cached, make a request
        url = domoticz_base_url(self)
        if not url:
            return None

        url += f"{self.DOMOTICZ_DEVICEST_API}{device_id}"
        dz_result = domoticz_request(self, url)
        if dz_result is None:
            return None

        result = json.loads(dz_result)
        self.logging("Debug", f"Result: {result}")

        # Cache the result before returning
        self._cache_device_status(device_id, result)
        return result

    def _extract_add_value(self, device_id, attribute):
        """Extracts the value of a specified attribute from the device status."""
        result = self.get_device_status(device_id)
        if result is None or 'result' not in result:
            return 0

        return next((device[attribute] for device in result['result'] if attribute in device), 0)

    def retrieve_addj_value_baro(self, device_id):
        """Retrieves the AddjValue2 attribute for the given device."""
        return self._extract_add_value(device_id, 'AddjValue2')

    def retrieve_timeout_motion(self, device_id):
        """Retrieves the AddjValue (motion timeout) for the given device."""
        return self._extract_add_value(device_id, 'AddjValue')

    def retrieve_addj_value_temp(self, device_id):
        """Retrieves the AddjValue (temperature) for the given device."""
        return self._extract_add_value(device_id, 'AddjValue')
