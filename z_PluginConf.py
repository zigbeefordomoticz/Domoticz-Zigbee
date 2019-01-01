#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
Class PluginConf

Description: Import the PluginConf.txt file and initialized each of the available parameters in this file
Parameters not define in the PluginConf.txt file will be set to their default value.

"""

import Domoticz
import os.path

PLUGINCONF_FILENAME = "PluginConf.txt"


class PluginConf:

    def __init__(self, homedir, hardwareid):
        self.logFORMAT = 0

        # Device Management
        self.allowStoreDiscoveryFrames = 0
        self.allowForceCreationDomoDevice = 0
        self.forceConfigureReporting = 0 # Allow to reset the Configure Reporting record
        self.forceReadAttributes = 0 # Allow to reset the ReadAttribute
        self.resetMotiondelay = 30
        self.vibrationAqarasensitivity = 'medium' # Possible values are 'high', 'medium', 'low'

        # Zigate Configuration
        self.channel = 0
        self.allowRemoveZigateDevice = 0
        self.eraseZigatePDM = 0

        # Plugin Transport
        self.zmode = 'ZigBee'  # Default mode. Cmd -> Ack -> Data
        self.reTransmit = 1  # Default mode, we do one retransmit if Data not reach at TO
        self.zTimeOut = 2  # 2'' Tiemout to get Ack and Data
        self.CrcCheck = 1
        self.sendDelay = 0

        # Plugin Directories
        self.pluginHome = homedir
        self.homedirectory = homedir
        self.pluginData = self.pluginHome + './'
        self.pluginZData = self.pluginHome + './Zdatas/'
        self.pluginConfig = self.pluginHome + './'
        self.pluginWWW = self.pluginHome + '../../www/templates/'
        self.pluginReports = self.pluginWWW + 'zigate/reports/'
        self.filename = None

        # Groups Management
        self.enablegroupmanagement = 0
        self.discoverZigateGroups = 1
        self.enableConfigGroups = 1

        # Network Topoology
        self.logLQI = 0
        self.networkScan = 0

        # Debugging
        self.debugReadCluster = 0

        # Import PluginConf.txt

        self.filename = self.homedirectory + "PluginConf-%02d.txt" %hardwareid
        if not os.path.isfile(self.filename) :
            self.filename = self.homedirectory + "PluginConf.txt"

        Domoticz.Status("PluginConf: %s" %self.filename)
        tmpPluginConf = ""
        with open( self.filename, 'r') as myPluginConfFile:
            tmpPluginConf += myPluginConfFile.read().replace('\n', '')

        Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))

        self.PluginConf = eval(tmpPluginConf)

        if self.PluginConf.get('vibrationAqarasensitivity'):
            self.vibrationAqarasensitivity = self.PluginConf['vibrationAqarasensitivity']

        if self.PluginConf.get('pluginData'):
            self.pluginData = self.PluginConf['pluginData']

        if self.PluginConf.get('pluginZData'):
            self.pluginZData = self.PluginConf['pluginZData']

        if self.PluginConf.get('pluginReports'):
            self.pluginReports = self.PluginConf['pluginReports']

        if self.PluginConf.get('pluginConfig'):
            self.pluginConfig = self.PluginConf['pluginConfig']

        if self.PluginConf.get('pluginWWW'):
            self.pluginWWW = self.PluginConf['pluginWWW']

        if self.PluginConf.get('enablegroupmanagement') and \
                self.PluginConf.get('enablegroupmanagement').isdigit():
            self.enablegroupmanagement = int(self.PluginConf['enablegroupmanagement'], 10)

        if self.PluginConf.get('debugReadCluster') and \
                self.PluginConf.get('debugReadCluster').isdigit():
            self.debugReadCluster = int(self.PluginConf['debugReadCluster'], 10)

        if self.PluginConf.get('resetMotiondelay') and \
                self.PluginConf.get('resetMotiondelay').isdigit():
            self.resetMotiondelay = int(self.PluginConf['resetMotiondelay'], 10)

        if self.PluginConf.get('sendDelay') and \
                self.PluginConf.get('sendDelay').isdigit():
            self.sendDelay = int(self.PluginConf['sendDelay'], 10)

        if self.PluginConf.get('allowStoreDiscoveryFrames') and \
                self.PluginConf.get('allowStoreDiscoveryFrames').isdigit():
            self.allowStoreDiscoveryFrames = int(self.PluginConf['allowStoreDiscoveryFrames'], 10)

        if self.PluginConf.get('forceConfigureReporting') and \
                self.PluginConf.get('forceConfigureReporting').isdigit():
            self.forceConfigureReporting = int(self.PluginConf['forceConfigureReporting'], 10)

        if self.PluginConf.get('forceReadAttributes') and \
                self.PluginConf.get('forceReadAttributes').isdigit():
            self.forceReadAttribute = int(self.PluginConf['forceReadAttributes'], 10)

        if self.PluginConf.get('logFORMAT') and \
                self.PluginConf.get('logFORMAT').isdigit():
            self.logFORMAT = int(self.PluginConf['logFORMAT'], 10)

        if self.PluginConf.get('logLQI') and self.PluginConf.get('logLQI').isdigit():
            self.logLQI = int(self.PluginConf['logLQI'], 10)

        if self.PluginConf.get('allowRemoveZigateDevice') and \
                self.PluginConf.get('allowRemoveZigateDevice').isdigit():
            self.allowRemoveZigateDevice = int(self.PluginConf['allowRemoveZigateDevice'], 10)

        if self.PluginConf.get('allowForceCreationDomoDevice') and \
                self.PluginConf.get('allowForceCreationDomoDevice').isdigit():
            self.allowForceCreationDomoDevice = int(self.PluginConf['allowForceCreationDomoDevice'], 10)

        if self.PluginConf.get('networkScan') and \
                self.PluginConf.get('networkScan').isdigit():
            self.networkScan = int(self.PluginConf['networkScan'], 10)

        if self.PluginConf.get('channel'): 
            self.channel = self.PluginConf.get('channel')
            self.channel = [c.strip() for c in self.channel.split(',')]

        if self.PluginConf.get('zmode'):
            if self.PluginConf.get('zmode') == 'Agressive':
                self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command

        if self.PluginConf.get('reTransmit') and \
                self.PluginConf.get('reTransmit').isdigit():
            self.reTransmit = int(self.PluginConf.get('reTransmit'))

        if self.PluginConf.get('zTimeOut') and \
                self.PluginConf.get('zTimeOut').isdigit():
            self.zTimeOut = int(self.PluginConf.get('zTimeOut'))


        Domoticz.Log("Device Management:")
        Domoticz.Log(" -allowStoreDiscoveryFrames : %s" %self.allowStoreDiscoveryFrames)
        Domoticz.Log(" -allowForceCreationDomoDevice: %s" %self.allowForceCreationDomoDevice)
        Domoticz.Log(" -forceConfigureReporting: %s" %self.forceConfigureReporting)
        Domoticz.Log(" -forceReadAttributes: %s" %self.forceReadAttributes)
        Domoticz.Log(" -resetMotiondelay: %s" %self.resetMotiondelay)
        Domoticz.Log(" -vibrationAqarasensitivity: %s" %self.vibrationAqarasensitivity)

        Domoticz.Log("Zigate Configuration")
        Domoticz.Log(" -channel: %s" %self.channel)
        Domoticz.Log(" -allowRemoveZigateDevice: %s" %self.allowRemoveZigateDevice)
        Domoticz.Log(" -eraseZigatePDM: %s" %self.eraseZigatePDM)

        Domoticz.Log("Plugin Transport")
        Domoticz.Log(" -zmode: %s" %self.zmode)
        Domoticz.Log(" -reTransmit: %s" %self.reTransmit)
        Domoticz.Log(" -zTimeOut: %s" %self.zTimeOut)
        Domoticz.Log(" -CrcCheck: %s" %self.CrcCheck)
        Domoticz.Log(" -sendDelay: %s" %self.sendDelay)

        Domoticz.Log("Plugin Directories")
        Domoticz.Log(" -pluginHome: %s" %self.pluginHome)
        Domoticz.Log(" -pluginData: %s" %self.pluginData)
        Domoticz.Log(" -pluginZData: %s" %self.pluginZData)
        Domoticz.Log(" -pluginReports: %s" %self.pluginReports)
        Domoticz.Log(" -pluginConfig: %s" %self.pluginConfig)
        Domoticz.Log(" -pluginWWW: %s" %self.pluginWWW)
        Domoticz.Log(" -homedirectory: %s" %self.homedirectory)
        Domoticz.Log(" -filename: %s" %self.filename)

        # Groups Management
        Domoticz.Log("Groups Management")
        Domoticz.Log(" -enablegroupmanagement: %s" %self.enablegroupmanagement)
        Domoticz.Log(" -discoverZigateGroups: %s" %self.discoverZigateGroups)
        Domoticz.Log(" -enableConfigGroups: %s" %self.enableConfigGroups)

        # Network Topoology
        Domoticz.Log("Reportings and Statistics")
        Domoticz.Log(" -logLQI: %s"% self.logLQI)
        Domoticz.Log(" -networkScan: %s" %self.networkScan)
