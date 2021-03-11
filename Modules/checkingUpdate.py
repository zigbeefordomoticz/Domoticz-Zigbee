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

TXT_RECORD = "zigate.pipiche.net"

import time
import Domoticz

def checkPluginVersion( branch ):

    import dns.resolver

    Domoticz.Log("checkPluginVersion - Start request version")
    
    stableVersion = betaVersion = firmwareMajorVersion = firmwareMinorVersion = 0 
    try:
        zigateVersions = (dns.resolver.query( TXT_RECORD,"TXT", tcp=True, lifetime=1).response.answer[0][-1].strings[0]).decode('utf8')
    except Exception as e:
        Domoticz.Log("DNS error while checking Plugin and Firmware version: %s" %e)
        return ( 0, 0, 0)

    Domoticz.Log("checkPluginVersion - Version record: %s Type: %s" %(str(zigateVersions), type(zigateVersions)))
    if zigateVersions and str(zigateVersions) != '':

        stable, beta , firmwareMajor, firmwareMinor = zigateVersions.split(";")
        label, stableVersion = stable.split("=")
        label, betaVersion = beta.split("=")
        label, firmwareMajorVersion = firmwareMajor.split("=")
        label, firmwareMinorVersion = firmwareMinor.split("=")

    Domoticz.Debug("checkPluginVersion - Available Plugin Versions are, stable: %s , beta: %s" %(stableVersion, betaVersion))
    Domoticz.Debug("checkPluginVersion - Available Firmware Version is, Major: %s , Minor: %s" %(firmwareMajorVersion, firmwareMinorVersion))

    if branch == 'stable':
        return ( stableVersion, firmwareMajorVersion, firmwareMinorVersion )
    elif branch == 'beta':
        return ( betaVersion, firmwareMajorVersion, firmwareMinorVersion )
    else:
        Domoticz.Error("checkPluginVersion - Unknown branch: %s" %branch)

def checkPluginUpdate( currentVersion, availVersion):

    if availVersion == 0:
        return False

    Domoticz.Debug("checkPluginUpdate - %s %s" %(currentVersion, availVersion))
    currentMaj, currentMin, currentUpd = currentVersion.split('.')
    availMaj, availMin, availUpd = availVersion.split('.')

    if availMaj > currentMaj:
        Domoticz.Debug("checkPluginVersion - Upgrade available: %s" %availVersion)
        return True
    elif availMaj == currentMaj:
        if ( availMin == currentMin and availUpd > currentUpd or availMin > currentMin ):
            Domoticz.Debug("checkPluginVersion - Upgrade available: %s" %availVersion)
            return True
    return False


def checkFirmwareUpdate( currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):

    if not (availfirmMinor and currentFirmwareVersion):
        return False
    if int(availfirmMinor,16) > int(currentFirmwareVersion,16):
        Domoticz.Debug("checkFirmwareUpdate - Firmware update available")
        return True
    return False
