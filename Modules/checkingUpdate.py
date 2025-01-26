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
    Checks the plugin version against DNS TXT records and fetches firmware details if applicable.

    Args:
        zigbee_communication (str): Communication type ('native' or 'zigpy').
        branch (str): Current plugin branch (e.g., 'master', 'beta').
        zigate_model (str): Zigate model identifier.

    Returns:
        tuple: Plugin version, firmware major version, firmware minor version.
    """
    self.log.logging("CheckUpdate", "Debug", f"check_plugin_version_against_dns {zigbee_communication} {branch} {zigate_model}")

    # Fetch and parse plugin version DNS record
    plugin_version = _fetch_and_parse_dns_record(self, PLUGIN_TXT_RECORD, "Plugin")
    if plugin_version is None:
        self.log.logging("CheckUpdate", "Error", "Unable to access plugin version. Is Internet access available?")
        return (0, 0, 0)

    self.log.logging("CheckUpdate", "Debug", f"     plugin version: >{plugin_version}")

    firmware_version_dict = {}
    if zigbee_communication == "native":
        firmware_version = _fetch_and_parse_dns_record(self, ZIGATE_DNS_RECORDS.get(zigate_model), "Firmware")
        if firmware_version:
            firmware_version_dict = firmware_version

    self.log.logging("CheckUpdate", "Debug", f"     firmware version: >{firmware_version_dict}")
    
    # Determine the response based on communication type and branch support
    if zigbee_communication == "native" and branch in plugin_version and "firmMajor" in firmware_version_dict and "firmMinor" in firmware_version_dict:
        return (plugin_version[branch], firmware_version_dict["firmMajor"], firmware_version_dict["firmMinor"])

    if zigbee_communication == "zigpy" and branch in plugin_version:
        return (plugin_version[branch], 0, 0)

    self.log.logging("CheckUpdate", "Error", f"You are running on branch: {branch}, which is NOT SUPPORTED.")
    return (0, 0, 0)


def _fetch_and_parse_dns_record(self, record_name, record_type):
    """
    Fetches and parses a DNS TXT record.

    Args:
        record_name (str): The name of the DNS TXT record.
        record_type (str): Type of record (e.g., 'Plugin', 'Firmware') for logging.

    Returns:
        dict or None: Parsed DNS record as a dictionary, or None if unavailable.
    """
    if not record_name:
        self.log.logging("CheckUpdate", "Error", f"{record_type} DNS record not found.")
        return None

    self.log.logging("CheckUpdate", "Debug", f"Fetching {record_type} DNS record: {record_name}")
    record = _get_dns_txt_record(self, record_name)
    if record is None:
        self.log.logging("CheckUpdate", "Error", f"Failed to fetch {record_type} DNS record: {record_name}")
        return None

    self.log.logging("CheckUpdate", "Debug", f"Fetching {record_type} DNS record: {record_name} = {record}")

    parsed_record = _parse_dns_txt_record(record)
    self.log.logging("CheckUpdate", "Debug", f"Fetched and parsed {record_type} DNS record: {parsed_record}")
    return parsed_record


def _get_dns_txt_record(self, record, timeout=DNS_REQ_TIMEOUT):
    """
    Fetch a DNS TXT record.

    Args:
        record (str): The DNS record to fetch.
        timeout (int): Timeout for the DNS query in seconds.

    Returns:
        str or None: The DNS TXT record as a string, or None if unavailable.
    """
    if not self.internet_available:
        self.log.logging("CheckUpdate", "Error", f"Internet unavailable, skipping DNS resolution for {record}")
        return None

    try:
        # Attempt to resolve the DNS TXT record
        result = dns.resolver.resolve(record, "TXT", tcp=True, lifetime=timeout).response.answer[0]
        return str(result[0]).strip('"')

    except dns.resolver.Timeout:
        _handle_dns_error(self, f"DNS resolution timed out for {record} after {timeout} second(s)", fatal=True)

    except dns.resolver.NoAnswer:
        _handle_dns_error(self, f"DNS TXT record not found for {record}")

    except dns.resolver.NoNameservers:
        _handle_dns_error(self, f"No nameservers found for {record}", fatal=True)

    except Exception as e:
        _handle_dns_error(self, f"Unexpected error while resolving DNS TXT record for {record}: {e}")

    return None


def _handle_dns_error(self, message, fatal=False):
    """
    Handle DNS errors with consistent logging.

    Args:
        message (str): The error message to log.
        fatal (bool): If True, set internet_available to False.
    """
    self.log.logging("CheckUpdate", "Error", message)
    if fatal:
        self.internet_available = False


def _parse_dns_txt_record(txt_record):
    version_dict = {}
    if txt_record and txt_record != "":
        for branch_version in txt_record.split(";"):
            version_dict.update({k.strip(): v.strip('"') for k, v in (item.split("=") for item in branch_version.split(";"))})
    return version_dict


def is_plugin_update_available(self, currentVersion, availVersion):
    """
    Check if a plugin update is available.

    Args:
        currentVersion (str): Current plugin version (e.g., "1.0.0").
        availVersion (str): Available plugin version (e.g., "1.1.0").

    Returns:
        bool: True if an update is available, False otherwise.
    """
    if availVersion == "0":
        return False

    if _is_newer_version(self, currentVersion, availVersion):
        self.log.logging("CheckUpdate", "Status", f"Zigbee4Domoticz plugin: upgrade available: {availVersion}")
        return True
    
    return False


def _is_newer_version(self, currentVersion, availVersion):
    """
    Compare two version strings to determine if the second is newer.

    Args:
        currentVersion (str): Current version string (e.g., "1.0.0").
        availVersion (str): Available version string (e.g., "1.1.0").

    Returns:
        bool: True if availVersion is newer than currentVersion, False otherwise.
    """
    current = tuple(map(int, currentVersion.split(".")))
    available = tuple(map(int, availVersion.split(".")))
    return available > current


def is_zigate_firmware_available(self, currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if int(availfirmMinor, 16) > int(currentFirmwareVersion, 16):
        self.log.logging("CheckUpdate", "Status", "Zigate Firmware update available")
        return True
    return False


def is_internet_available(self):
    """
    Check if the internet is available by sending a GET request to a reliable website.

    Returns:
        bool: True if the internet is available, False otherwise.
    """
    url = "https://www.google.com"
    timeout = 3

    try:
        response = requests.get(url, timeout=timeout)
        # Return True if the status code indicates success (2xx)
        return 200 <= response.status_code < 300
    except requests.ConnectionError:
        # Handle cases where the connection fails
        return False
    except requests.Timeout:
        # Handle timeout errors
        return False
    except requests.RequestException as e:
        # Handle other request exceptions
        self.log.logging( "Plugin", "Status",f"Unexpected error while checking internet availability: {e}")
        return False
