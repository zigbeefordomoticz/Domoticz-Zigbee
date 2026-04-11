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

This module provides functionality to check the latest versions of the Zigbee for Domoticz
plugin and the firmware of Zigate devices using DNS TXT records. It supports multiple
Zigate hardware models (V1, V1 OPTIPDM, V2) and both native and Zigpy-based Zigbee
communication.

Key Features:
-------------
- Retrieve expected plugin version for a given branch (stable, beta) via DNS TXT.
- Retrieve expected firmware version for native Zigate devices via DNS TXT.
- Parse semicolon-separated key=value DNS TXT records into Python dictionaries.
- Compare current plugin or firmware versions against available versions.
- Detect whether a plugin or firmware update is available.
- Verify Internet availability to ensure version checks can be performed.

Dependencies:
-------------
- dnspython3
- requests
"""

import dns.resolver
import urllib.request
import urllib.error
import socket
#import requests

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
    Check the plugin and firmware versions against expected versions retrieved via DNS TXT records.

    Args:
        self: Plugin instance with `log` and `internet_available`.
        zigbee_communication (str): Type of communication ('native' or 'zigpy').
        branch (str): Plugin branch ('stable', 'beta').
        zigate_model (str): Zigate hardware model (used for native communication).

    Returns:
        tuple: (plugin_version, firmware_major, firmware_minor)
               If not available or unsupported, returns (0, 0, 0)
    """
    self.log.logging("DNS", "Debug", f"check_plugin_version_against_dns {zigbee_communication} {branch} {zigate_model}")

    plugin_version_txt = _get_dns_txt_record(self, PLUGIN_TXT_RECORD)
    if plugin_version_txt is None:
        self.log.logging("DNS", "Error", "Unable to get access to plugin expected version. Is Internet access available?")
        return (0, 0, 0)

    plugin_version_dict = _parse_dns_txt_record(plugin_version_txt)
    self.log.logging("DNS", "Debug", f"Plugin version DNS TXT: {plugin_version_dict}")

    firmware_version_dict = {}
    if zigbee_communication == "native":
        zigate_plugin_record = ZIGATE_DNS_RECORDS.get(zigate_model)
        firmware_version_txt = _get_dns_txt_record(self, zigate_plugin_record)
        firmware_version_dict = _parse_dns_txt_record(firmware_version_txt)
        self.log.logging("DNS", "Debug", f"Firmware version DNS TXT: {firmware_version_dict}")

    if zigbee_communication == "native":
        if (
            branch in plugin_version_dict
            and "firmMajor" in firmware_version_dict
            and "firmMinor" in firmware_version_dict
        ):
            return (
                plugin_version_dict[branch],
                int(firmware_version_dict["firmMajor"], 16),
                int(firmware_version_dict["firmMinor"], 16)
            )
    elif zigbee_communication == "zigpy":
        if branch in plugin_version_dict:
            return (plugin_version_dict[branch], 0, 0)

    self.log.logging("DNS", "Error", f"You are running {branch}-{plugin_version_txt}, a NOT SUPPORTED version.")
    return (0, 0, 0)


def _get_dns_txt_record(self, record, timeout=DNS_REQ_TIMEOUT):
    """
    Retrieve the content of a DNS TXT record.

    This function detects the dnspython major version and dispatches
    the DNS query to the appropriate implementation.

    Args:
        record (str): Fully-qualified DNS TXT record to query.
        timeout (int): DNS query timeout in seconds.

    Returns:
        str or None: TXT record content or None on failure.
    """
    if not self.internet_available:
        return None

    try:
        import dns
        version = getattr(dns, "__version__", "1.0")
        major = int(version.split(".", 1)[0])
    except Exception:
        major = 1  # Safe default for very old environments

    self.log.logging( "DNS", "Debug", f"_get_dns_txt_record: dnspython major version {major}" )

    if major >= 2:
        return _get_dns_txt_record_v2(self, record, timeout)

    return _get_dns_txt_record_v1(self, record, timeout)


def _get_dns_txt_record_v1(self, record, timeout):
    """
    Retrieve a DNS TXT record using dnspython 1.x API (resolver.query).

    Args:
        record (str): DNS TXT record name.
        timeout (int): DNS timeout in seconds.

    Returns:
        str or None: TXT record content or None on failure.
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    try:
        try:
            answers = resolver.query(record, "TXT", tcp=False)
            self.log.logging("DNS", "Debug", f"{record} resolved via UDP (v1)")
        except dns.exception.DNSException:
            answers = resolver.query(record, "TXT", tcp=True)
            self.log.logging("DNS", "Debug", f"{record} resolved via TCP (v1)")

        txt_records = []
        for rdata in answers:
            # rdata.strings: list of byte chunks
            parts = [s.decode("utf-8", "ignore") for s in rdata.strings]
            txt_records.append("".join(parts))

        return ";".join(txt_records) if txt_records else None

    except dns.resolver.Timeout:
        self.internet_available = False
        self.log.logging( "DNS", "Error", f"DNS timeout while resolving {record} (v1)" )

    except Exception as e:
        self.log.logging( "DNS", "Error", f"Unexpected DNS error (v1) for {record}: {e}" )

    return None


def _get_dns_txt_record_v2(self, record, timeout):
    """
    Retrieve a DNS TXT record using dnspython 2.x API (resolver.resolve).

    Args:
        record (str): DNS TXT record name.
        timeout (int): DNS timeout in seconds.

    Returns:
        str or None: TXT record content or None on failure.
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    try:
        try:
            answers = resolver.resolve(record, "TXT", tcp=False)
            self.log.logging("DNS", "Debug", f"{record} resolved via UDP (v2)")

        except dns.exception.DNSException:
            answers = resolver.resolve(record, "TXT", tcp=True)
            self.log.logging("DNS", "Debug", f"{record} resolved via TCP (v2)")

        txt_records = []
        for rdata in answers:
            strings = getattr(rdata, "strings", None)
            if strings:
                parts = [s.decode("utf-8", "ignore") for s in strings]
                txt_records.append("".join(parts))
            else:
                txt_records.append(rdata.to_text().strip('"'))

        return ";".join(txt_records) if txt_records else None

    except dns.resolver.Timeout:
        self.internet_available = False
        self.log.logging( "DNS", "Error", f"DNS timeout while resolving {record} (v2)" )

    except Exception as e:
        self.log.logging( "DNS", "Error", f"Unexpected DNS error (v2) for {record}: {e}" )

    return None


def _parse_dns_txt_record(txt_record: str) -> dict:
    """
    Parse a DNS TXT record containing semicolon-separated key=value pairs.

    Args:
        txt_record (str): Raw TXT record string.

    Returns:
        dict: Dictionary of key-value pairs.
    """
    version_dict = {}
    if not txt_record:
        return version_dict

    for item in txt_record.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        version_dict[key.strip()] = value.strip('"').strip()

    return version_dict


def is_plugin_update_available(self, currentVersion, availVersion):
    """
    Determine if a plugin update is available.

    Args:
        self: Plugin instance with `log`.
        currentVersion (str): Current plugin version (format: "X.Y.Z").
        availVersion (str): Available plugin version from DNS TXT.

    Returns:
        bool: True if an update is available, False otherwise.
    """
    if availVersion == 0:
        return False

    currentMaj, currentMin, currentUpd = currentVersion.split(".")
    availMaj, availMin, availUpd = availVersion.split(".")

    if availMaj > currentMaj:
        self.log.logging("DNS", "Status", f"Zigbee4Domoticz plugin: upgrade available: {availVersion}")
        return True

    if availMaj == currentMaj and (
        (availMin == currentMin and availUpd > currentUpd) or availMin > currentMin
    ):
        self.log.logging("DNS", "Status", f"Zigbee4Domoticz plugin: upgrade available: {availVersion}")
        return True

    return False


def is_zigate_firmware_available(self, currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    """
    Determine if a Zigate firmware update is available.

    Args:
        self: Plugin instance with `log`.
        currentMajorVersion (int): Current major firmware version.
        currentFirmwareVersion (str): Current firmware version in hex string.
        availfirmMajor (int): Available major firmware version from DNS TXT.
        availfirmMinor (int): Available minor firmware version from DNS TXT.

    Returns:
        bool: True if a firmware update is available, False otherwise.
    """
    self.log.logging("DNS", "Debug", f"is_zigate_firmware_available {type(currentMajorVersion)}, {type(currentFirmwareVersion)}, {type(availfirmMajor)}, {type(availfirmMinor)}")
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if availfirmMinor > int(currentFirmwareVersion, 16):
        self.log.logging("DNS", "Debug", "Zigate Firmware update available")
        return True
    return False


#def is_internet_available():
#    """
#    Simple check to verify if Internet access is available.
#
#    Returns:
#        bool: True if Internet is reachable, False otherwise.
#    """
#    try:
#        response = requests.get("https://www.google.com", timeout=3)
#        return response.status_code == 200
#    except requests.ConnectionError:
#        return False



def is_internet_available():
    try:
        with urllib.request.urlopen(
            "https://www.google.com",
            timeout=3
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, socket.timeout):
        return False
