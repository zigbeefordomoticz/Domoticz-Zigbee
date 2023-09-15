#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

# Enable Version Check ( will required Internet connectivity )

# Use DNS TXT to check latest version  available on gitHub
# - stable
# - beta

# Provide response to REST API request
import time

import dns.resolver

import Domoticz

PLUGIN_TXT_RECORD = "zigate_plugin.pipiche.net"
ZIGATEV1_FIRMWARE_TXT_RECORD = "zigatev1.pipiche.net"
ZIGATEV1OPTIPDM_TXT_RECORD = "zigatev1optipdm.pipiche.net"
ZIGATEV2_FIRMWARE_TXT_RECORD = "zigatev2.pipiche.net"

ZIGATE_DNS_RECORDS = {
    "03": ZIGATEV1_FIRMWARE_TXT_RECORD,
    "04": ZIGATEV1OPTIPDM_TXT_RECORD,
    "05": ZIGATEV2_FIRMWARE_TXT_RECORD,
}


def checkPluginVersion(self, zigbee_communitation, branch, zigate_model):

    TXT_RECORD = None
    if zigbee_communitation == "native":
        TXT_RECORD = ZIGATE_DNS_RECORDS.get(zigate_model)

    zigate_plugin = zigateVersions = None
    try:
        zigate_plugin = dns.resolver.resolve(PLUGIN_TXT_RECORD, "TXT", tcp=True, lifetime=1).response.answer[0]
        zigate_plugin = str( zigate_plugin[0] ).strip('"')
        if TXT_RECORD:
            zigateVersions = dns.resolver.resolve(TXT_RECORD, "TXT", tcp=True, lifetime=1).response.answer[0]
            zigateVersions = str(zigateVersions[0]).strip('"')
    except Exception as e:
        return (0, 0, 0)

    pluginVersion = {}
    if zigate_plugin and zigate_plugin != "":
        for branch_version in zigate_plugin.split(";"):
            pluginVersion[branch_version.split("=")[0]] = branch_version.split("=")[1].strip('"')

    firmwareVersion = {}
    if zigateVersions and zigateVersions != "":
        for major_minor in zigateVersions.split(";"):
            firmwareVersion[major_minor.split("=")[0]] = major_minor.split("=")[1].strip('"')

    if zigbee_communitation == "native" and branch in pluginVersion and "firmMajor" in firmwareVersion and "firmMinor" in firmwareVersion:
        return (pluginVersion[branch], firmwareVersion["firmMajor"], firmwareVersion["firmMinor"])
    if zigbee_communitation == "zigpy" and branch in pluginVersion:
        return (pluginVersion[branch], 0, 0)

    self.log.logging("Plugin", "Error", "You are running %s-%s , a NOT SUPPORTED version. Please refer to https://github.com/zigbeefordomoticz/Domoticz-Zigbee to get the latest informations" % (branch, pluginVersion ))
    return (0, 0, 0)


def checkPluginUpdate(self, currentVersion, availVersion):
    if availVersion == 0:
        return False

    currentMaj, currentMin, currentUpd = currentVersion.split(".")
    availMaj, availMin, availUpd = availVersion.split(".")

    if availMaj > currentMaj:
        self.log.logging("Plugin", "Status", "checkPluginVersion - Upgrade available: %s" %availVersion)
        return True
    if availMaj == currentMaj and (
        availMin == currentMin
        and availUpd > currentUpd
        or availMin > currentMin
    ):
        self.log.logging("Plugin", "Status", "checkPluginVersion - Upgrade available: %s" %availVersion)
        return True
    return False


def checkFirmwareUpdate(self, currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if int(availfirmMinor, 16) > int(currentFirmwareVersion, 16):
        self.log.logging("Plugin", "Status", "checkFirmwareUpdate - Firmware update available")
        return True
    return False
