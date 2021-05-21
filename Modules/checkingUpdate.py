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
import dns.resolver


PLUGIN_TXT_RECORD = "zigate_plugin.pipiche.net"
ZIGATEV1_FIRMWARE_TXT_RECORD = "zigatev1.pipiche.net"
ZIGATEV1OPTIPDM_TXT_RECORD = "zigatev1optipdm.pipiche.net"
ZIGATEV2_FIRMWARE_TXT_RECORD = "zigatev2.pipiche.net"




def checkPluginVersion( branch , zigate_model):
    

    Domoticz.Log("ZiGate Model: %s" %zigate_model)
    if zigate_model == '03':
        TXT_RECORD = ZIGATEV1_FIRMWARE_TXT_RECORD
    elif zigate_model == '04':
        TXT_RECORD = ZIGATEV1OPTIPDM_TXT_RECORD
    elif zigate_model == '05':
        TXT_RECORD = ZIGATEV2_FIRMWARE_TXT_RECORD

    Domoticz.Log("checkPluginVersion - Start request version")
    stableVersion = betaVersion = firmwareMajorVersion = firmwareMinorVersion = 0 
    try:
        zigate_plugin = (dns.resolver.query( PLUGIN_TXT_RECORD,"TXT", tcp=True, lifetime=1).response.answer[0][-1].strings[0]).decode('utf8')
        zigateVersions = (dns.resolver.query( TXT_RECORD, "TXT", tcp=True, lifetime=1).response.answer[0][-1].strings[0]).decode('utf8')
    except Exception as e:
        Domoticz.Log("DNS error while checking Plugin and Firmware version: %s" %e)
        return ( 0, 0, 0)

    Domoticz.Log("checkPluginVersion - Plugin Version record: %s Type: %s" %(str(zigate_plugin), type(zigate_plugin)))
    Domoticz.Log("checkPluginVersion - Firmware Version record: %s Type: %s" %(str(zigateVersions), type(zigateVersions)))
    if zigate_plugin and str(zigate_plugin) != '':
        for branch_version in zigate_plugin.split(';'):
            if branch_version.split("=")[0] == 'stable':
                stableVersion = branch_version.split("=")[1]
            elif branch_version.split("=")[0] == 'beta':
                betaVersion = branch_version.split("=")[1]
    
    if zigateVersions and str(zigateVersions) != '':
        for major_minor in zigateVersions.split(';'):
            if major_minor.split("=")[0] == 'firmMajor':
                firmwareMajorVersion = major_minor.split("=")[1]
            elif major_minor.split("=")[0] == 'firmMinor':
                firmwareMinorVersion = major_minor.split("=")[1]

    Domoticz.Log("checkPluginVersion - Available Plugin Versions are, stable: %s , beta: %s" %(stableVersion, betaVersion))
    Domoticz.Log("checkPluginVersion - Available Firmware Version is, Major: %s , Minor: %s" %(firmwareMajorVersion, firmwareMinorVersion))

    if branch == 'stable':
        return ( stableVersion, firmwareMajorVersion, firmwareMinorVersion )
    elif branch == 'beta':
        return ( betaVersion, firmwareMajorVersion, firmwareMinorVersion )
    else:
        Domoticz.Error("checkPluginVersion - Unknown branch: %s" %branch)

def checkPluginUpdate( currentVersion, availVersion):
    if availVersion == 0:
        return False

    #Domoticz.Debug("checkPluginUpdate - %s %s" %(currentVersion, availVersion))
    currentMaj, currentMin, currentUpd = currentVersion.split('.')
    availMaj, availMin, availUpd = availVersion.split('.')

    if availMaj > currentMaj:
        #Domoticz.Debug("checkPluginVersion - Upgrade available: %s" %availVersion)
        return True
    elif availMaj == currentMaj:
        if ( availMin == currentMin and availUpd > currentUpd or availMin > currentMin ):
            #Domoticz.Debug("checkPluginVersion - Upgrade available: %s" %availVersion)
            return True
    return False


def checkFirmwareUpdate( currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if int(availfirmMinor,16) > int(currentFirmwareVersion,16):
        #Domoticz.Debug("checkFirmwareUpdate - Firmware update available")
        return True
    return False
