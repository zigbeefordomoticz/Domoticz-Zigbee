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

# Use DNS TXT to check latest version  available on gitHub
# - stable
# - beta

"""
Zigbee for Domoticz Plugin - Version Checking via DNS TXT Records
=================================================================

This module provides functionality to check and validate the versions of the Zigbee
for Domoticz plugin and Zigate firmware against the latest versions published via
DNS TXT records.

It supports multiple Zigate hardware models (V1, V1 OPTIPDM, V2) and can handle
both native and Zigpy-based Zigbee communication.

Key Features:
-------------
- Retrieve the expected plugin version for a given branch (stable, beta) via DNS TXT.
- Retrieve the expected firmware version for native Zigate devices via DNS TXT.
- Parse semicolon-separated key=value DNS TXT records into Python dictionaries.
- Compare current plugin or firmware versions against available versions.
- Detect whether a plugin or firmware update is available.
- Check Internet availability to ensure version checks can be performed.

Constants:
----------
PLUGIN_TXT_RECORD: str
    DNS TXT record for the Zigbee for Domoticz plugin version.
ZIGATEV1_FIRMWARE_TXT_RECORD: str
    DNS TXT record for Zigate V1 firmware.
ZIGATEV1OPTIPDM_TXT_RECORD: str
    DNS TXT record for Zigate V1 OPTIPDM firmware.
ZIGATEV2_FIRMWARE_TXT_RECORD: str
    DNS TXT record for Zigate V2 firmware.
DNS_REQ_TIMEOUT: int
    Default timeout in seconds for DNS TXT queries.
ZIGATE_DNS_RECORDS: dict
    Mapping of Zigate hardware model codes to their respective DNS TXT records.

Functions:
----------
check_plugin_version_against_dns(self, zigbee_communication, branch, zigate_model)
    Checks plugin and firmware versions against DNS TXT records and returns the latest versions.

_get_dns_txt_record(self, record, timeout=DNS_REQ_TIMEOUT)
    Retrieves the TXT record for a given DNS record, handling UDP/TCP fallback and errors.

_parse_dns_txt_record(txt_record: str) -> dict
    Parses a semicolon-separated key=value string from a DNS TXT record into a dictionary.

is_plugin_update_available(self, currentVersion, availVersion)
    Determines if a newer plugin version is available compared to the current version.

is_zigate_firmware_available(self, currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor)
    Determines if a newer firmware version is available for a Zigate device.

is_internet_available()
    Performs a basic check to verify whether Internet access is available.

Usage Example:
--------------
# Check plugin version for stable branch and native Zigate V2
plugin_version, firm_major, firm_minor = check_plugin_version_against_dns(self, "native", "stable", "05")
if is_plugin_update_available(self, current_version, plugin_version):
    print("Plugin update available:", plugin_version)
if is_zigate_firmware_available(self, current_major, current_firmware, firm_major, firm_minor):
    print("Zigate firmware update available:", f"{firm_major}.{firm_minor}")
"""

import dns.resolver
import requests

PLUGIN_TXT_RECORD = "zigate_plugin.pipiche.net"
ZIGATEV1_FIRMWARE_TXT_RECORD = "zigatev1.pipiche.net"
ZIGATEV1OPTIPDM_TXT_RECORD = "zigatev1optipdm.pipiche.net"
ZIGATEV2_FIRMWARE_TXT_RECORD = "zigatev2.pipiche.net"

DNS_REQ_TIMEOUT = 2

ZIGATE_DNS_RECORDS = {
    "03": ZIGATEV1_FIRMWARE_TXT_RECORD,
    "04": ZIGATEV1OPTIPDM_TXT_RECORD,
    "05": ZIGATEV2_FIRMWARE_TXT_RECORD,
}


def check_plugin_version_against_dns(self, zigbee_communication, branch, zigate_model):
    """
    Checks the plugin and (if native communication) firmware versions against expected versions
    retrieved via DNS TXT records.

    Args:
        zigbee_communication (str): 'native' or 'zigpy'
        branch (str): The plugin branch name (e.g., 'stable', 'beta')
        zigate_model (str): The Zigate hardware model (used when communication is 'native')

    Returns:
        tuple: (plugin_version, firmware_major, firmware_minor)
               If not available, returns (0, 0, 0)
    """
    self.log.logging("Plugin", "Debug", f"check_plugin_version_against_dns {zigbee_communication} {branch} {zigate_model}")

    plugin_version_txt = _get_dns_txt_record(self, PLUGIN_TXT_RECORD)
    if plugin_version_txt is None:
        self.log.logging("Plugin", "Error", "Unable to get access to plugin expected version. Is Internet access available?")
        return (0, 0, 0)

    plugin_version_dict = _parse_dns_txt_record(plugin_version_txt)
    self.log.logging("Plugin", "Debug", f"Plugin version DNS TXT: {plugin_version_dict}")

    firmware_version_dict = {}
    if zigbee_communication == "native":
        zigate_plugin_record = ZIGATE_DNS_RECORDS.get(zigate_model)
        firmware_version_txt = _get_dns_txt_record(self, zigate_plugin_record)
        firmware_version_dict = _parse_dns_txt_record(firmware_version_txt)
        self.log.logging("Plugin", "Debug", f"Firmware version DNS TXT: {firmware_version_dict}")

    if zigbee_communication == "native":
        if (
            branch in plugin_version_dict
            and "firmMajor" in firmware_version_dict
            and "firmMinor" in firmware_version_dict
        ):
            return (
                plugin_version_dict[branch],
                int(firmware_version_dict["firmMajor"],16),
                int(firmware_version_dict["firmMinor"],16)
            )
    elif zigbee_communication == "zigpy":
        if branch in plugin_version_dict:
            return (plugin_version_dict[branch], 0, 0)

    self.log.logging("Plugin", "Error", f"You are running {branch}-{plugin_version_txt}, a NOT SUPPORTED version.")
    return (0, 0, 0)


def _get_dns_txt_record(self, record, timeout=DNS_REQ_TIMEOUT):
    """
    Resolves a DNS TXT record and returns its content as a string.
    
    Tries UDP first, falls back to TCP on failure.
    Handles common DNS resolution errors and logs appropriately.
    
    Args:
        record (str): The DNS record name.
        timeout (int): Timeout in seconds for the DNS query.
    
    Returns:
        str or None: The concatenated TXT record contents, or None on failure.
    """
    if not self.internet_available:
        return None

    try:
        resolver = dns.resolver.Resolver()
        #resolver.lifetime = timeout  # Apply timeout globally to all attempts

        try:
            answers = resolver.resolve(record, "TXT", tcp=False)
            self.log.logging("Plugin", "Debug", f"_get_dns_txt_record: {record} via UDP: {answers}")
        except dns.exception.DNSException:
            answers = resolver.resolve(record, "TXT", tcp=True)
            self.log.logging("Plugin", "Debug", f"_get_dns_txt_record: {record} via TCP: {answers}")

        # Extract actual strings from TXT response
        txt_records = []
        txt_records.extend(rdata.to_text().strip('"') for rdata in answers)
        return ";".join(txt_records) if txt_records else None

    except dns.resolver.Timeout:
        error_message = f"DNS resolution timed out for {record} after {timeout} seconds"
        self.internet_available = False

    except dns.resolver.NoAnswer:
        error_message = f"No DNS TXT answer found for {record}"

    except dns.resolver.NoNameservers:
        error_message = f"No nameservers found while resolving {record}"
        self.internet_available = False

    except Exception as e:
        error_message = f"Unexpected error while resolving {record}: {e}"

    self.log.logging("Plugin", "Error", error_message)
    return None


def _parse_dns_txt_record(txt_record: str) -> dict:
    """
    Parse a DNS TXT record containing semicolon-separated key=value pairs.

    Args:
        txt_record (str): Raw TXT record string.

    Returns:
        dict: Parsed key-value pairs.
    """
    version_dict = {}

    if not txt_record:
        return version_dict

    for item in txt_record.split(";"):
        item = item.strip()
        if not item:
            continue

        if "=" not in item:
            # Skip invalid items or log a warning if needed
            continue

        key, value = item.split("=", 1)  # only split at the first =
        version_dict[key.strip()] = value.strip('"').strip()

    return version_dict


def is_plugin_update_available(self, currentVersion, availVersion):
    if availVersion == 0:
        return False

    currentMaj, currentMin, currentUpd = currentVersion.split(".")
    availMaj, availMin, availUpd = availVersion.split(".")

    if availMaj > currentMaj:
        self.log.logging("Plugin", "Status", "Zigbee4Domoticz plugin:  upgrade available: %s" %availVersion)
        return True

    if availMaj == currentMaj and (
        availMin == currentMin
        and availUpd > currentUpd
        or availMin > currentMin
    ):
        self.log.logging("Plugin", "Status", "Zigbee4Domoticz plugin:  upgrade available: %s" %availVersion)
        return True
    return False


def is_zigate_firmware_available(self, currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    self.log.logging("Plugin", "Debug", f"is_zigate_firmware_available {type(currentMajorVersion)}, {type(currentFirmwareVersion)}, {type(availfirmMajor)}, {type(availfirmMinor)}")
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if availfirmMinor > int(currentFirmwareVersion, 16):
        self.log.logging("Plugin", "Debug", "Zigate Firmware update available")
        return True
    return False


def is_internet_available():
    try:
        response = requests.get("https://www.google.com", timeout=3)
        # Check if the status code is a success code (2xx)
        return response.status_code == 200
    except requests.ConnectionError:
        return False
