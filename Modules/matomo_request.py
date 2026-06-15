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

"""Matomo analytics integration for the Zigbee for Domoticz plugin.

This module sends anonymous usage telemetry to the project's Matomo instance
(``https://z4d.pipiche.net/matomo.php``) so that maintainers can understand
how the plugin is used in the wild.  All tracking is opt-in and can be
disabled by the user at any time via the plugin settings.

Privacy
-------
The coordinator IEEE address is the only device-specific identifier used.
It is **always SHA-256 hashed** before transmission so that no raw MAC address
leaves the host — except on RoneLabs-branded hardware where the raw MAC is
deliberately included in ``dimension12`` for hardware-specific diagnostics.

Tracked events
--------------
- **Plugin lifecycle** — started, shutdown, restart, self-update outcome.
- **Coordinator** — new network formation.
- **Privacy** — user opt-in / opt-out actions.
- **Periodic analytics snapshot** (``Z4DPluginInfos``) — collects custom
  dimensions such as Domoticz version, coordinator model and firmware,
  plugin version, network size, OS distribution, CPU architecture, uptime
  category, and optional hardware-specific fields.

Custom dimensions (Matomo site ID 9)
-------------------------------------
==  ===========================  ====================================
#   Name                         Source
==  ===========================  ====================================
1   Domoticz version             ``pluginParameters["DomoticzVersion"]``
2   Coordinator model            ``pluginParameters["CoordinatorModel"]``
3   Plugin version               ``pluginParameters["PluginVersion"]``
4   Coordinator firmware         ``pluginParameters["DisplayFirmwareVersion"]``
5   Network size                 Router + end-device count (bucketed)
6   Certified DB version         ``pluginParameters["CertifiedDbVersion"]``
7   OS distribution              ``distro.name() + distro.version()``
8   Python / CPU architecture    ``platform`` module
9   Uptime category              Seconds since plugin start (bucketed)
10  RoneLabs model               ``/etc/modelinfo`` (RoneLabs only)
11  Raspberry Pi model           ``/proc/device-tree/model``
12  Raw coordinator MAC          Formatted IEEE string (RoneLabs only)
==  ===========================  ====================================

Dependencies
------------
- ``distro`` (third-party) — OS distribution detection.
- ``Modules.tools.how_many_devices`` — router / end-device count.
"""

import hashlib
import json
import os
import platform
import re
import time
import urllib.parse
import urllib.request

import distro

from Modules.tools import how_many_devices

# Matomo endpoint details
MATOMO_URL = "https://z4d.pipiche.net/matomo.php"
APIV = 1  # API Version
SITE_ID = 9
ACTION_NAME = "PluginInstanceInfos"

RONELABS_MODEL_INFO = "/etc/modelinfo"
DEVICE_TREE_CONFIGURATION = "/proc/device-tree/model"

_UPTIME_THRESHOLDS = [
    (1 * 86400, "1 day"),
    (2 * 86400, "2 days"),
    (3 * 86400, "3 days"),
    (4 * 86400, "4 days"),
    (5 * 86400, "5 days"),
    (7 * 86400, "1 week"),
    (14 * 86400, "2 weeks"),
    (21 * 86400, "3 weeks"),
    (28 * 86400, "4 weeks"),
    (30 * 86400, "1 month"),
    (60 * 86400, "2 months"),
    (90 * 86400, "3 months"),
    (120 * 86400, "4 months"),
    (150 * 86400, "5 months"),
    (180 * 86400, "6 months"),
]

_DIMENSION_CLEAN_RE = re.compile(r'[^a-zA-Z0-9 _.-]')
_MULTI_SPACE_RE = re.compile(r'\s{2,}')


def get_clientid(self, mode='hashed'):
    """Return the coordinator IEEE address in the requested format.

    Reads the coordinator IEEE address from device ``'0000'`` and returns it
    in one of three forms controlled by *mode*.

    Args:
        mode (str): Output format — one of:
            * ``'hashed'``  — SHA-256 hex digest (privacy-safe, for Matomo ``uid``).
            * ``'formated'`` — Colon-separated hex string (e.g. ``"aa:bb:cc:dd:ee:ff:00:11"``).

    Returns:
        str | None: Formatted address, or None if the IEEE address is unavailable.

    """
    mac_address = self.ListOfDevices.get('0000', {}).get('IEEE', None)
    if not mac_address:
        return None
    if mode == 'hashed':
        return hashlib.sha256(mac_address.encode()).hexdigest()
    elif mode =='formated':
        return ":".join(mac_address[i:i + 2] for i in range(0, len(mac_address), 2))
    return mac_address
    

def populate_custom_dimensions(self):
    """Build the Matomo custom-dimension payload for the current plugin instance.

    Dimension mapping:
        1  – Domoticz version
        2  – Coordinator model
        3  – Plugin version
        4  – Coordinator firmware version
        5  – Network size category
        6  – Certified device-DB version
        7  – OS distribution
        8  – Python / CPU architecture
        9  – Plugin uptime category
        10 – RoneLabs appliance model (only on RoneLabs hardware)
        11 – Raspberry Pi model string
        12 – Raw coordinator MAC address (only on RoneLabs hardware, intentional)

    Returns:
        dict: Mapping of ``"dimensionN"`` keys to sanitised string values.
              Keys for unavailable data are omitted.
    """
    _custom_dimensions = { }

    # Domoticz version
    _domo = self.pluginParameters.get("DomoticzVersion")
    if _domo:
        _custom_dimensions[ "dimension1"] = clean_custom_dimension_value( _domo)

    # Coordinator Model
    _coordinator_model = self.pluginParameters.get("CoordinatorModel")
    if _coordinator_model:
        _custom_dimensions[ "dimension2"] = clean_custom_dimension_value( _coordinator_model)

    # Plugin Version
    _plugin_version = self.pluginParameters.get("PluginVersion")
    if _plugin_version:
        _custom_dimensions[ "dimension3"] = clean_custom_dimension_value( _plugin_version)

    # Coordinator Firmware Version
    _coordinator_version = self.pluginParameters.get("DisplayFirmwareVersion")
    if _coordinator_version:
        _custom_dimensions[ "dimension4"] = clean_custom_dimension_value( _coordinator_version)

    # Network Size
    _custom_dimensions[ "dimension5"] = clean_custom_dimension_value(get_network_size_items(self))

    # Certified Db Version
    certified_db_version = self.pluginParameters.get("CertifiedDbVersion")
    if certified_db_version:
        _custom_dimensions[ "dimension6"] = clean_custom_dimension_value( certified_db_version)

    # OS Distribution
    _distribution = get_distribution(self)
    if _distribution:
        _custom_dimensions[ "dimension7"] = clean_custom_dimension_value( _distribution)

    # Platform Architecture
    _archi = get_architecture_model(self)
    if _archi:
        _custom_dimensions[ "dimension8"] = clean_custom_dimension_value( _archi)

    # Uptime
    if self.statistics:
        _uptime = get_uptime_category(self.statistics._start)
        if _uptime:
            _custom_dimensions[ "dimension9"] = clean_custom_dimension_value( _uptime)

    # Ronelab model
    ronelab_model = get_ronelabs_model_custom_definition()
    if ronelab_model:
        _custom_dimensions[ "dimension10"] = clean_custom_dimension_value(ronelab_model)
        formatted_mac = get_clientid(self,mode='formated')
        _custom_dimensions[ "dimension12"] = formatted_mac

    # Platform Id ( Pi Model )
    pi_model = get_raspberry_pi_model()
    if pi_model:
        _custom_dimensions[ "dimension11"] = clean_custom_dimension_value(pi_model)

    return _custom_dimensions


def matomo_plugin_analytics_infos(self):
    """Send a full plugin-instance analytics snapshot to Matomo.

    Collects all custom dimensions (versions, hardware, network size, uptime)
    and fires a single page-view request tagged as ``Z4DPluginInfos``.
    """
    send_matomo_request(self, "Z4DPluginInfos", None, populate_custom_dimensions(self))


def matomo_opt_out_action(self):
    """ Tracks a user's opt-out action in Matomo. """
    send_matomo_request( self, action_name="Opt-Out Action", event_category="Privacy", event_action="Opt-Out", event_name="User Opted Out" )


def matomo_opt_in_action(self):
    """ Tracks a user's opt-in action in Matomo. """
    send_matomo_request( self, action_name="Opt-In Action", event_category="Privacy", event_action="Opt-In", event_name="User Opted In" )


def matomo_coordinator_initialisation(self):
    """Track a coordinator network-formation event in Matomo."""
    send_matomo_request( self, action_name="Coordinator Action", event_category="Coordinator", event_action="NewNetwork", event_name="Coordinator Formed new network" )


def matomo_plugin_shutdown(self):
    """Track a plugin shutdown event in Matomo."""
    send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="Shutdown", event_name="Plugin Shutdown" )


def matomo_plugin_restart(self):
    """Track a plugin restart event in Matomo."""
    send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="Restart", event_name="Plugin Restart" )


def matomo_plugin_started(self):
    """Track a plugin start event in Matomo."""
    send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="Started", event_name="Plugin Started" )


def matomo_plugin_update(self, status):
    """Track a plugin self-update outcome in Matomo.

    Args:
        status (bool): True if the update completed successfully, False on error.
    """
    if status:
        send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="SuccessfullUpdate", event_name="Plugin Update Successfully" )
    else:
        send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="ErrorUpdate", event_name="Plugin Update with error" )


def send_matomo_request(self, action_name, custom_variable=None, custom_dimension=None, event_category=None, event_action=None, event_name=None):
    """
    Sends a tracking request to Matomo with optional custom variables, dimensions, and events.

    Args:
        action_name (str): Name of the action being tracked.
        custom_variable (dict, optional): Custom variables to include.
        custom_dimension (dict, optional): Custom dimensions to include.
        event_category (str, optional): Category for the event (e.g., "Privacy").
        event_action (str, optional): Action for the event (e.g., "Opt-Out").
        event_name (str, optional): Name of the event (e.g., "User Opted Out").
    """
    
    client_id = get_clientid(self,mode='hashed')
    if self.log:
        self.log.logging( "Matomo", "Debug", f"send_matomo_request - Client_id {client_id}")
    if client_id is None:
        if self.log:
            self.log.logging( "Matomo", "Error", "Nothing reported as MacAddress is None!")
        return

    # Construct the payload
    payload = {
        "idsite": SITE_ID,
        "rec": 1,
        "apiv": APIV,
        "action_name": action_name,
        "uid": client_id,
    }

    # Add custom variables if provided
    if custom_variable:
        try:
            payload["cvar"] = json.dumps(custom_variable)
        except TypeError as e:
            if self.log:
                self.log.logging("Matomo", "Error", f"Failed to serialize custom_variable: {e}")
            return

    # Add custom dimensions if provided
    if custom_dimension:
        payload.update(custom_dimension)

    # Add event-specific parameters if provided
    if event_category and event_action:
        payload["e_c"] = event_category  # Event category
        payload["e_a"] = event_action  # Event action
        if event_name:
            payload["e_n"] = event_name  # Event name (optional)

    if self.log:
        self.log.logging( "Matomo", "Debug", f"send_matomo_request - payload {payload}")
    # Send the request
    fetch_data_with_timeout(self, MATOMO_URL, payload)

def fetch_data_with_timeout(self, url, params, timeout=5):
    """Send a GET request to *url* with *params* URL-encoded, silently on failure.

    Args:
        url (str): Target URL.
        params (dict): Query parameters to encode and append.
        timeout (int): Socket timeout in seconds (default 5).
    """
    try:
        query = urllib.parse.urlencode(params or {})
        full_url = f"{url}?{query}" if query else url

        urllib.request.urlopen(full_url, timeout=timeout).close()

    except Exception as e:
        if self.log:
            self.log.logging("Matomo", "Debug", f"Matomo request failed: {e}")


def get_architecture_model(self):
    """
    Retrieve the architecture model of the current Python runtime and system.

    Returns:
        str: A string containing architecture information.
    """
    try:
        return f"python: {platform.python_version()} arch: {platform.architecture()[0]} machine: {platform.machine()} processor:{platform.processor()}"
    except Exception as e:
        if self.log:
            self.log.logging("Matomo", "Error", f"get_architecture_model error {e}")
    return None


def get_ronelabs_model_custom_definition():
    """Return the RoneLabs appliance model string, or None on non-RoneLabs hardware.

    Reads the first line of ``/etc/modelinfo``, which is only present on
    RoneLabs-branded devices.

    Returns:
        str | None: Model identifier string, or None if the file is absent.
    """
    if os.path.exists( RONELABS_MODEL_INFO ):
        with open(RONELABS_MODEL_INFO) as f:
            return f.readline().strip()
    return None


def classify_uptime(uptime_seconds):
    """Map an uptime duration in seconds to a human-readable category.

    Uses ``_UPTIME_THRESHOLDS`` (module-level constant) to find the first
    threshold that the value does not exceed.

    Args:
        uptime_seconds (float): Elapsed seconds since the plugin started.

    Returns:
        str: Category label such as ``"1 day"``, ``"2 weeks"``, or ``"Beyond 6 months"``.
    """
    return next(
        (label for threshold, label in _UPTIME_THRESHOLDS if uptime_seconds <= threshold),
        "Beyond 6 months",
    )


def get_uptime_category(start_time):
    """Return the uptime category for a plugin that started at *start_time*.

    Args:
        start_time (float): Unix timestamp when the plugin started.

    Returns:
        str: Human-readable uptime category (see :func:`classify_uptime`).
    """
    uptime_seconds = time.time() - start_time
    return classify_uptime(uptime_seconds)


def get_network_size_items(self):
    """Return the network-size category label for the current Zigbee network.

    Counts routers and end-devices then delegates to :func:`classify_nwk_size`.

    Returns:
        str: Size category such as ``"Small"``, ``"Large"``, or ``"unknown"``.
    """
    routers, end_devices = how_many_devices(self)
    networkTotalsize = routers + end_devices
    
    return classify_nwk_size(networkTotalsize)


def classify_nwk_size(value):
    """Classify a total device count into a named network-size bucket.

    Buckets: unknown (0), Micro (<5), Small (<10), Medium (<25),
    Large (<50), Very Large (<75), Xtra Large (≥75).

    Args:
        value (int): Total number of devices in the network.

    Returns:
        str: Size label.
    """
    if value == 0:
        return "unknown"
    if value < 5:
        return "Micro"
    elif value < 10:
        return "Small"
    elif value < 25:
        return "Medium"
    elif value < 50:
        return "Large"
    elif value < 75:
        return "Very Large"
    return "Xtra Large"


def get_distribution(self):
    """Return the OS distribution name and version as a single string.

    Returns:
        str | None: e.g. ``"Raspberry Pi OS 11"``, or None on failure.
    """
    try:
        return f"{distro.name()} {distro.version()}"
    except Exception as e:
        if self.log:
            self.log.logging("Matomo", "Error", f"get_distribution error {e}")
    return None


def clean_custom_dimension_value(value: str) -> str:
    """Sanitise a string for use as a Matomo custom-dimension value.

    Replaces any character outside ``[a-zA-Z0-9 _.-]`` with a space,
    collapses consecutive spaces, and strips leading/trailing whitespace.

    Args:
        value (str): Raw dimension value.

    Returns:
        str: Sanitised value safe for inclusion in a Matomo tracking URL.
    """
    return _MULTI_SPACE_RE.sub(' ', _DIMENSION_CLEAN_RE.sub(' ', value)).strip()


def get_raspberry_pi_model():
    """Return the Raspberry Pi model string from the device tree, or None.

    Reads ``/proc/device-tree/model``, which is present on Raspberry Pi
    hardware and contains a human-readable model name (e.g.
    ``"Raspberry Pi 4 Model B Rev 1.4"``).

    Returns:
        str | None: Model string, or None if the file is absent.
    """
    if os.path.exists( DEVICE_TREE_CONFIGURATION ):
        with open( DEVICE_TREE_CONFIGURATION , 'r') as f:
            return f.read().strip()
    return None
