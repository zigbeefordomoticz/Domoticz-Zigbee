#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Module to restart the Zigbee plugin in Domoticz using its JSON API.

This script is designed to interact with the Domoticz home automation system
via HTTP requests executed through the `curl` command-line tool. It automates
the process of restarting a specific plugin (Zigate), optionally erasing the
Persistent Data Memory (PDM), and toggling the plugin's enabled state.

It uses system-specific `curl` binaries depending on the OS (Windows or Linux),
and constructs appropriate Domoticz API URLs to update hardware parameters.

Functions:
    restartPluginViaDomoticzJsonApi(self, stop=False, erasePDM=False, url_base_api=DOMOTICZ_URL, auth=None):
        Restarts the Zigbee plugin in Domoticz with various configurable options.
"""

import json
import os
import subprocess  # nosec, B404
from urllib.parse import urlencode

from Modules.domoticzAbstractLayer import domoticz_error_api, domoticz_log_api

LINUX_CURL_COMMAND = "/usr/bin/curl"
WINDOWS_CURL_COMMAND = r"c:\Windows\System32\curl.exe"
DOMOTICZ_URL = "http://127.0.0.1:8080"
ZIGBEE_PLUGIN_KEY = "Zigate"


def restartPluginViaDomoticzJsonApi(self, stop=False, erasePDM=False, url_base_api=DOMOTICZ_URL, auth=None):
    """
    Restarts the Zigbee plugin in Domoticz by sending an `updatehardware` command through the JSON API.

    This function:
        - Detects the correct `curl` binary based on the OS.
        - Queries Domoticz for a list of hardware configurations.
        - Locates the Zigbee plugin based on the `Extra` key.
        - Constructs and executes a `curl` command to update hardware parameters.
        - Can stop the plugin or trigger an erase of the persistent data memory (PDM).

    Args:
        self: Reference to the plugin instance containing configuration in `self.pluginParameters`.
        stop (bool): If True, the plugin will be disabled (default: False).
        erasePDM (bool): If True, triggers an erase of the PDM during restart (default: False).
        url_base_api (str): Base URL for Domoticz API (default: "http://127.0.0.1:8080").
        auth (tuple or None): Optional basic auth credentials as (username, password).

    Returns:
        bool: True if the plugin restart command was successfully issued, False otherwise.
    """
    
    curl_command = WINDOWS_CURL_COMMAND if os.name == 'nt' else LINUX_CURL_COMMAND
    if not os.path.isfile(curl_command):
        domoticz_error_api(f"Unable to restart the plugin, {curl_command} not available.")
        return False

    auth_opts = ["-u", f"{auth[0]}:{auth[1]}"] if auth else []

    # Get hardware list
    get_url = f"{url_base_api}/json.htm?type=command&param=gethardware"

    # --- Call Domoticz -------------------------------------------------------
    try:
        result = subprocess.check_output( [curl_command, "-s"] + auth_opts + [get_url], stderr=subprocess.STDOUT, )  # nosec B603
    except subprocess.CalledProcessError as e:
        domoticz_error_api( f"Domoticz gethardware call failed (rc={e.returncode}): {e.output!r}" )
        return False

    if not result:
        domoticz_error_api("Domoticz returned an empty response to gethardware.")
        return False

    # --- Decode JSON ---------------------------------------------------------
    # hw_list = json.loads(result)
    try:
        hw_list = json.loads(result)
    except (json.JSONDecodeError, TypeError) as e:
        domoticz_error_api( f"Invalid JSON received from Domoticz gethardware: {e}, raw={result!r}" )
        return False

    if not isinstance(hw_list, dict):
        domoticz_error_api(f"Unexpected JSON structure: {hw_list!r}")
        return False

    if hw_list.get("status") != "OK":
        domoticz_error_api(f"Domoticz API returned error: {hw_list}")
        return False

    hardware = hw_list.get("result")
    if not isinstance(hardware, list):
        domoticz_error_api(f"Missing or invalid 'result' field: {hw_list}")
        return False

    # --- Locate plugin -------------------------------------------------------
    plugin = next( (h for h in hardware if h.get("Extra") == ZIGBEE_PLUGIN_KEY), None, )

    if not plugin:
        domoticz_error_api( f"Plugin '{ZIGBEE_PLUGIN_KEY}' not found in hardware list." )
        return False

    # --- Build update command -----------------------------------------------
    cmd = _build_update_cmd(self, curl_command, auth_opts, url_base_api,plugin, erasePDM, stop)

    domoticz_log_api( f"Restarting plugin '{ZIGBEE_PLUGIN_KEY}' (stop={stop}, erasePDM={erasePDM})" )
    domoticz_log_api( f"Domoticz update command: {cmd}")

    # --- Fire and forget -----------------------------------------------------
    try:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            shell=False,
            text=True,
        )  # nosec B603

    except OSError as e:
        domoticz_error_api(f"Failed to execute Domoticz update command: {e}")
        return False

    domoticz_log_api("Plugin restart command sent successfully.")
    return True


def _build_update_cmd(self, curl_command, auth_opts, url_base_api, plugin, erasePDM, stop):
    base_url = f"{url_base_api}/json.htm?type=command&param=updatehardware"

    params = {
        "idx": self.pluginParameters["HardwareID"],
        "htype": "94",
        "name": self.pluginParameters["Name"],
        "extra": self.pluginParameters["Key"],
        "loglevel": plugin.get("LogLevel", 0),
        "datatimeout": "0",
        "Mode1": self.pluginParameters["Mode1"],
        "Mode2": self.pluginParameters["Mode2"],
        "Mode3": "True" if erasePDM else "False",
        "Mode4": self.pluginParameters["Mode4"],
        "Mode5": self.pluginParameters["Mode5"],
        "Mode6": self.pluginParameters["Mode6"],
        "enabled": "false" if stop else "true"
    }

    optional_fields_map = {
        "Address": "address",
        "Port": "port",
        "SerialPort": "serialport",
        "Username": "username",  # nosec B105
        "Password": "password",  # nosec B105
    }

    for domoticz_key, api_key in optional_fields_map.items():
        params[api_key] = self.pluginParameters.get(domoticz_key, "")

    # Properly encode all query parameters
    full_url = base_url + "&" + urlencode(params)

    # domoticz_log_api(f"Constructed update URL: {full_url}")
    return [curl_command, ] + auth_opts + [full_url]
