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
import Domoticz

try:
    import dns.resolver
except:
    Domoticz.Error("Missing serial or dns modules. https://github.com/zigbeefordomoticz/wiki/blob/zigpy/en-eng/missing-modules.md#make-sure-that-you-have-correctly-installed-the-plugin")

PLUGIN_TXT_RECORD = "zigate_plugin.pipiche.net"
ZIGATEV1_FIRMWARE_TXT_RECORD = "zigatev1.pipiche.net"
ZIGATEV1OPTIPDM_TXT_RECORD = "zigatev1optipdm.pipiche.net"
ZIGATEV2_FIRMWARE_TXT_RECORD = "zigatev2.pipiche.net"

ZIGATE_DNS_RECORDS = {
    "03": ZIGATEV1_FIRMWARE_TXT_RECORD,
    "04": ZIGATEV1OPTIPDM_TXT_RECORD,
    "05": ZIGATEV2_FIRMWARE_TXT_RECORD,
}


def checkPluginVersion(zigbee_communitation, branch, zigate_model):

    TXT_RECORD = None
    if zigbee_communitation == "native":
        TXT_RECORD = ZIGATE_DNS_RECORDS.get(zigate_model)

    #Domoticz.Log("checkPluginVersion - Start request version for branche %s model: %s" %( branch, zigate_model))

    zigate_plugin = zigateVersions = None
    try:
        zigate_plugin = dns.resolver.resolve(PLUGIN_TXT_RECORD, "TXT", tcp=True, lifetime=1).response.answer[0]
        zigate_plugin = str( zigate_plugin[0] ).strip('"')
        if TXT_RECORD:
            zigateVersions = dns.resolver.resolve(TXT_RECORD, "TXT", tcp=True, lifetime=1).response.answer[0]
            zigateVersions = str(zigateVersions[0]).strip('"')
    except Exception as e:
        #Domoticz.Log("DNS error while checking Plugin and Firmware version: %s" %e)
        return (0, 0, 0)

    #Domoticz.Log("checkPluginVersion - Plugin Version record: %s Type: %s" %(str(zigate_plugin), type(zigate_plugin)))
    #Domoticz.Log("checkPluginVersion - Firmware Version record: %s Type: %s" %(str(zigateVersions), type(zigateVersions)))
    pluginVersion = {}
    if zigate_plugin and zigate_plugin != "":
        for branch_version in zigate_plugin.split(";"):
            pluginVersion[branch_version.split("=")[0]] = branch_version.split("=")[1].strip('"')
            #Domoticz.Log("checkPluginVersion - Available Plugin Versions are, %s , %s" %(branch_version.split("=")[0], pluginVersion[ branch_version.split("=")[0] ]))

    firmwareVersion = {}
    if zigateVersions and zigateVersions != "":
        for major_minor in zigateVersions.split(";"):
            firmwareVersion[major_minor.split("=")[0]] = major_minor.split("=")[1].strip('"')
            #Domoticz.Log("checkPluginVersion - Available Firmware Version is, %s , %s" %(major_minor.split("=")[0], firmwareVersion[ major_minor.split("=")[0] ]))

    if zigbee_communitation == "native" and  branch in pluginVersion and "firmMajor" in firmwareVersion and "firmMinor" in firmwareVersion:
        return (pluginVersion[branch], firmwareVersion["firmMajor"], firmwareVersion["firmMinor"])
    if zigbee_communitation == "zigpy" and branch in pluginVersion:
        return (pluginVersion[branch], 0, 0)

    Domoticz.Error("checkPluginVersion - Unknown branch: >%s< %s %s %s" % (branch,zigate_model, pluginVersion, firmwareVersion ))
    return (0, 0, 0)


def checkPluginUpdate(currentVersion, availVersion):
    if availVersion == 0:
        return False

    #Domoticz.Log("checkPluginUpdate - %s %s" %(currentVersion, availVersion))
    currentMaj, currentMin, currentUpd = currentVersion.split(".")
    availMaj, availMin, availUpd = availVersion.split(".")

    if availMaj > currentMaj:
        Domoticz.Log("checkPluginVersion - Upgrade available: %s" %availVersion)
        return True
    if availMaj == currentMaj and (
        availMin == currentMin
        and availUpd > currentUpd
        or availMin > currentMin
    ):
        Domoticz.Log("checkPluginVersion - Upgrade available: %s" %availVersion)
        return True
    return False


def checkFirmwareUpdate(currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if int(availfirmMinor, 16) > int(currentFirmwareVersion, 16):
        Domoticz.Log("checkFirmwareUpdate - Firmware update available")
        return True
    return False
