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


import dns.resolver
import requests

PLUGIN_TXT_RECORD = "zigate_plugin.pipiche.net"
ZIGATEV1_FIRMWARE_TXT_RECORD = "zigatev1.pipiche.net"
ZIGATEV1OPTIPDM_TXT_RECORD = "zigatev1optipdm.pipiche.net"
ZIGATEV2_FIRMWARE_TXT_RECORD = "zigatev2.pipiche.net"

ZIGATE_DNS_RECORDS = {
    "03": ZIGATEV1_FIRMWARE_TXT_RECORD,
    "04": ZIGATEV1OPTIPDM_TXT_RECORD,
    "05": ZIGATEV2_FIRMWARE_TXT_RECORD,
}


def check_plugin_version_against_dns(self, zigbee_communication, branch, zigate_model):
    self.log.logging("Plugin", "Debug", f"check_plugin_version_against_dns {zigbee_communication} {branch} {zigate_model}")

    plugin_version = None
    plugin_version = _get_dns_txt_record(self, PLUGIN_TXT_RECORD)
    self.log.logging("Plugin", "Debug", f"check_plugin_version_against_dns {plugin_version}")

    if plugin_version is None:
        # Something weird happened
        self.log.logging("Plugin", "Error", "Unable to get access to plugin expected version. Is Internet access available ?")
        return (0, 0, 0)

    plugin_version_dict = _parse_dns_txt_record( plugin_version)
    self.log.logging("Plugin", "Debug", f"check_plugin_version_against_dns {plugin_version} {plugin_version_dict}")

    # If native communication (zigate) let's find the zigate firmware
    firmware_version = None
    if zigbee_communication == "native":
        zigate_plugin_record = ZIGATE_DNS_RECORDS.get(zigate_model)
        firmware_version = _get_dns_txt_record(self, zigate_plugin_record)
        firmware_version_dict = _parse_dns_txt_record(firmware_version)
        self.log.logging("Plugin", "Debug", f"check_plugin_version_against_dns {firmware_version} {firmware_version_dict}")

    self.log.logging("Plugin", "Debug", f"check_plugin_version_against_dns {plugin_version} {plugin_version_dict}")

    if zigbee_communication == "native" and branch in plugin_version_dict and "firmMajor" in firmware_version_dict and "firmMinor" in firmware_version_dict:
        return (plugin_version_dict[branch], firmware_version_dict["firmMajor"], firmware_version_dict["firmMinor"])

    if zigbee_communication == "zigpy" and branch in plugin_version_dict:
        return (plugin_version_dict[branch], 0, 0)

    self.log.logging("Plugin", "Error", f"You are running {branch}-{plugin_version}, a NOT SUPPORTED version. ")
    return (0, 0, 0)


def _get_dns_txt_record(self, record, timeout=1):
    if not self.internet_available:
        return None

    try:
        result = dns.resolver.resolve(record, "TXT", tcp=True, lifetime=1).response.answer[0]
        return str(result[0]).strip('"')

    except dns.resolver.Timeout:
        error_message = f"DNS resolution timed out for {record} after {timeout} second"
        self.internet_available = False

    except dns.resolver.NoAnswer:
        error_message = f"DNS TXT record not found for {record}"

    except dns.resolver.NoNameservers:
        error_message = f"No nameservers found for {record}"
        self.internet_available = False

    except Exception as e:
        error_message = f"An unexpected error occurred while resolving DNS TXT record for {record}: {e}"

    self.log.logging("Plugin", "Error", error_message)
    return None


def _parse_dns_txt_record(txt_record):
    version_dict = {}
    if txt_record and txt_record != "":
        for branch_version in txt_record.split(";"):
            version_dict.update({k.strip(): v.strip('"') for k, v in (item.split("=") for item in branch_version.split(";"))})
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
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if int(availfirmMinor, 16) > int(currentFirmwareVersion, 16):
        self.log.logging("Plugin", "Status", "Zigate Firmware update available")
        return True
    return False


def is_internet_available():
    try:
        response = requests.get("http://www.google.com", timeout=3)
        # Check if the status code is a success code (2xx)
        return response.status_code == 200
    except requests.ConnectionError:
        return False
