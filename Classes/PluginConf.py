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

from Modules.tools import is_hex

class PluginConf:

    def __init__(self, homedir, hardwareid):

        self.logFORMAT = 0

        # Device Management
        self.allowStoreDiscoveryFrames = 0
        self.allowForceCreationDomoDevice = 0
        self.allowReBindingClusters = 1  # When receiving a Device Annouced, allow rebinding on clustered.
        self.resetConfigureReporting = 0 # Allow to reset the Configure Reporting record
        self.resetReadAttributes = 0 # Allow to reset the ReadAttribute
        self.enableReadAttributes = 0 # Enable the plugin to poll information from the devices.
        self.resetMotiondelay = 30
        self.vibrationAqarasensitivity = 'medium' # Possible values are 'high', 'medium', 'low'
        self.TradfriKelvinStep = 51

        # Zigate Configuration
        self.channel = 0
        self.allowRemoveZigateDevice = 0
        self.eraseZigatePDM = 0
        self.blueLedOff = 0
        self.TXpower_set = 0
        self.Certification = 0  # 1- CE; 2- FCC
        self.enableAPSFailureLoging = 0
        self.enableAPSFailureReporting = 1
        self.allowOTA = 0
        self.waitingOTA = 3600
        self.batteryOTA = 0
        self.extendedPANID = None

        # Plugin Transport
        self.zmode = 'ZigBee'  # Default mode. Cmd -> Ack -> Data
        self.reTransmit = 1  # Default mode, we do one retransmit if Data not reach at TO
        self.zTimeOut = 2  # 2'' Tiemout to get Ack and Data
        self.CrcCheck = 1
        self.sendDelay = 0
        self.Ping = 1

        # Plugin Directories
        self.pluginHome = homedir
        self.homedirectory = homedir
        self.pluginData = self.pluginHome + 'Data/'
        self.pluginZData = self.pluginHome + 'Zdatas/'
        self.pluginConfig = self.pluginHome + 'Conf/'
        self.pluginWWW = self.pluginHome + 'www/'
        #self.pluginReports = self.pluginWWW + 'zigate/reports/'
        self.pluginReports = self.pluginHome + 'www/zigate/reports/'
        self.pluginOTAFirmware = self.pluginHome + 'OTAFirmware/'

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

        # Zigate

        # Import PluginConf.txt
        self.filename = self.pluginConfig + "PluginConf-%02d.txt" %hardwareid
        if not os.path.isfile(self.filename) :
            self.filename = self.pluginConfig + "PluginConf-%d.txt" %hardwareid
            if not os.path.isfile(self.filename) :
                self.filename = self.pluginConfig + "PluginConf.txt"

        Domoticz.Status("PluginConf: %s" %self.filename)
        tmpPluginConf = ""
        self.PluginConf = {}
        if not os.path.isfile( self.filename ) :
            return

        with open( self.filename, 'r') as myPluginConfFile:
            tmpPluginConf += myPluginConfFile.read().replace('\n', '')

        Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))

        try:
            self.PluginConf = eval(tmpPluginConf)

        except SyntaxError:
            Domoticz.Error("Syntax Error in %s, all plugin parameters set to default" %self.filename)
        except (NameError, TypeError, ZeroDivisionError):
            Domoticz.Error("Error while importing %s, all plugin parameters set to default" %self.filename)
            
        else:
            if self.PluginConf.get('vibrationAqarasensitivity'):
                self.vibrationAqarasensitivity = self.PluginConf['vibrationAqarasensitivity']
                Domoticz.Status(" -vibrationAqarasensitivity: %s" %self.vibrationAqarasensitivity)

            if self.PluginConf.get('TradfriKelvinStep') and \
                    self.PluginConf.get('TradfriKelvinStep').isdigit():
                self.TradfriKelvinStep = int(self.PluginConf['TradfriKelvinStep'], 10)
                if self.TradfriKelvinStep < 0 or self.TradfriKelvinStep > 255:
                    self.TradfriKelvinStep = 75

            if self.PluginConf.get('pluginData'):
                self.pluginData = self.PluginConf['pluginData']

            if self.PluginConf.get('pluginZData'):
                self.pluginZData = self.PluginConf['pluginZData']
                Domoticz.Status(" -pluginData: %s" %self.pluginData)

            if self.PluginConf.get('pluginReports'):
                self.pluginReports = self.PluginConf['pluginReports']
                Domoticz.Status(" -pluginReports: %s" %self.pluginReports)

            if self.PluginConf.get('pluginOTAFirmware'):
                self.pluginOTAFirmware = self.PluginConf['pluginOTAFirmware']
                Domoticz.Status(" -pluginOTAFirmware: %s" %self.pluginOTAFirmware)

            if self.PluginConf.get('pluginConfig'):
                self.pluginConfig = self.PluginConf['pluginConfig']
                Domoticz.Status(" -pluginConfig: %s" %self.pluginConfig)

            if self.PluginConf.get('pluginWWW'):
                self.pluginWWW = self.PluginConf['pluginWWW']
                Domoticz.Status(" -pluginWWW: %s" %self.pluginWWW)

            if self.PluginConf.get('enablegroupmanagement') and \
                    self.PluginConf.get('enablegroupmanagement').isdigit():
                self.enablegroupmanagement = int(self.PluginConf['enablegroupmanagement'], 10)
                Domoticz.Status(" -enablegroupmanagement: %s" %self.enablegroupmanagement)

            if self.PluginConf.get('debugReadCluster') and \
                    self.PluginConf.get('debugReadCluster').isdigit():
                self.debugReadCluster = int(self.PluginConf['debugReadCluster'], 10)

            if self.PluginConf.get('resetMotiondelay') and \
                    self.PluginConf.get('resetMotiondelay').isdigit():
                self.resetMotiondelay = int(self.PluginConf['resetMotiondelay'], 10)
                Domoticz.Status(" -resetMotiondelay: %s" %self.resetMotiondelay)

            if self.PluginConf.get('sendDelay') and \
                    self.PluginConf.get('sendDelay').isdigit():
                self.sendDelay = int(self.PluginConf['sendDelay'], 10)
                Domoticz.Status(" -sendDelay: %s" %self.sendDelay)

            if self.PluginConf.get('Ping') and \
                    self.PluginConf.get('Ping').isdigit():
                self.Ping = int(self.PluginConf['Ping'], 10)
                Domoticz.Status(" -Ping: %s" %self.Ping)

            if self.PluginConf.get('allowStoreDiscoveryFrames') and \
                    self.PluginConf.get('allowStoreDiscoveryFrames').isdigit():
                self.allowStoreDiscoveryFrames = int(self.PluginConf['allowStoreDiscoveryFrames'], 10)
                Domoticz.Status(" -allowStoreDiscoveryFrames : %s" %self.allowStoreDiscoveryFrames)

            if self.PluginConf.get('allowReBindingClusters') and \
                    self.PluginConf.get('allowReBindingClusters').isdigit():
                self.allowReBindingClusters = int(self.PluginConf['allowReBindingClusters'], 10)
                Domoticz.Status(" -allowReBindingClusters: %s" %self.allowReBindingClusters)

            if self.PluginConf.get('resetConfigureReporting') and \
                    self.PluginConf.get('resetConfigureReporting').isdigit():
                self.resetConfigureReporting = int(self.PluginConf['resetConfigureReporting'], 10)
                Domoticz.Status(" -resetConfigureReporting: %s" %self.resetConfigureReporting)

            if self.PluginConf.get('resetReadAttributes') and \
                    self.PluginConf.get('resetReadAttributes').isdigit():
                self.resetReadAttributes = int(self.PluginConf['resetReadAttributes'], 10)
                Domoticz.Status(" -resetReadAttributes: %s" %self.resetReadAttributes)

            if self.PluginConf.get('enableReadAttributes') and \
                    self.PluginConf.get('enableReadAttributes').isdigit():
                self.enableReadAttributes = int(self.PluginConf['enableReadAttributes'], 10)
                Domoticz.Status(" -enableReadAttributes: %s" %self.enableReadAttributes)

            if self.PluginConf.get('logFORMAT') and \
                    self.PluginConf.get('logFORMAT').isdigit():
                self.logFORMAT = int(self.PluginConf['logFORMAT'], 10)
                Domoticz.Status(" -logFORMAT: %s" %self.logFORMAT)

            if self.PluginConf.get('logLQI') and self.PluginConf.get('logLQI').isdigit():
                self.logLQI = int(self.PluginConf['logLQI'], 10)
                Domoticz.Status(" -logLQI: %s"% self.logLQI)

            if self.PluginConf.get('allowRemoveZigateDevice') and \
                    self.PluginConf.get('allowRemoveZigateDevice').isdigit():
                self.allowRemoveZigateDevice = int(self.PluginConf['allowRemoveZigateDevice'], 10)
                Domoticz.Status(" -allowRemoveZigateDevice: %s" %self.allowRemoveZigateDevice)

            if self.PluginConf.get('allowForceCreationDomoDevice') and \
                    self.PluginConf.get('allowForceCreationDomoDevice').isdigit():
                self.allowForceCreationDomoDevice = int(self.PluginConf['allowForceCreationDomoDevice'], 10)
                Domoticz.Status(" -allowForceCreationDomoDevice: %s" %self.allowForceCreationDomoDevice)

            if self.PluginConf.get('networkScan') and \
                    self.PluginConf.get('networkScan').isdigit():
                self.networkScan = int(self.PluginConf['networkScan'], 10)
                Domoticz.Status(" -networkScan: %s" %self.networkScan)

            if self.PluginConf.get('channel'): 
                self.channel = self.PluginConf.get('channel')
                self.channel = [c.strip() for c in self.channel.split(',')]
                Domoticz.Status(" -channel: %s" %self.channel)

            if self.PluginConf.get('enableAPSFailureReporting') and \
                    self.PluginConf.get('enableAPSFailureReporting').isdigit():
                self.enableAPSFailureReporting = int(self.PluginConf.get('enableAPSFailureReporting'))
                Domoticz.Status(" -enableAPSFailureReporting: %s" %self.enableAPSFailureReporting)

            if self.PluginConf.get('enableAPSFailureLoging') and \
                    self.PluginConf.get('enableAPSFailureLoging').isdigit():
                self.enableAPSFailureLoging = int(self.PluginConf.get('enableAPSFailureLoging'))
                Domoticz.Status(" -enableAPSFailureLogin: %s" %self.enableAPSFailureLoging)

            if self.PluginConf.get('blueLedOff') and \
                    self.PluginConf.get('blueLedOff').isdigit():
                self.blueLedOff = int(self.PluginConf.get('blueLedOff'))
                Domoticz.Status(" -blueLedOff: %s" %self.blueLedOff)

            if self.PluginConf.get('TXpower') and \
                    self.PluginConf.get('TXpower').isdigit():
                self.TXpower_set = int(self.PluginConf.get('TXpower'))
                Domoticz.Status(" -TXpower: %s" %self.TXpower_set)

            if self.PluginConf.get('allowOTA') and \
                    self.PluginConf.get('allowOTA').isdigit():
                self.allowOTA = int(self.PluginConf.get('allowOTA'))
                Domoticz.Status(" -allowOTA: %s" %self.allowOTA)

            if self.PluginConf.get('waitingOTA') and \
                    self.PluginConf.get('waitingOTA').isdigit():
                self.waitingOTA = int(self.PluginConf.get('waitingOTA'))
                Domoticz.Status(" -waitingOTA: %s" %self.waitingOTA)

            if self.PluginConf.get('batteryOTA') and \
                    self.PluginConf.get('batteryOTA').isdigit():
                self.batteryOTA = int(self.PluginConf.get('batteryOTA'))
                Domoticz.Status(" -batteryOTA: %s" %self.batteryOTA)

            if self.PluginConf.get('Certification'):
                if self.PluginConf.get('Certification') == 'CE':
                    self.Certification = 0x01
                elif self.PluginConf.get('Certification') == 'FCC':
                    self.Certification = 0x02
                else:
                    self.Certification = 0
                Domoticz.Status(" -Certification: %s" %self.Certification)

            if self.PluginConf.get('zmode'):
                if self.PluginConf.get('zmode') == 'Agressive':
                    self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command
                Domoticz.Status(" -zmode: %s" %self.zmode)

            if self.PluginConf.get('reTransmit') and \
                    self.PluginConf.get('reTransmit').isdigit():
                self.reTransmit = int(self.PluginConf.get('reTransmit'))
                Domoticz.Status(" -reTransmit: %s" %self.reTransmit)

            if self.PluginConf.get('zTimeOut') and \
                    self.PluginConf.get('zTimeOut').isdigit():
                self.zTimeOut = int(self.PluginConf.get('zTimeOut'))
                Domoticz.Status(" -zTimeOut: %s" %self.zTimeOut)

            if self.PluginConf.get('extendedPANID'):
                if is_hex( self.PluginConf.get('extendedPANID') ):
                    self.extendedPANID = int(self.PluginConf.get('extendedPANID'), 16)
                    Domoticz.Status(" -extendedPANID: 0x%x" %self.extendedPANID)
                else:
                    Domoticz.Error("PluginConf - wrong parameter extendedPANID must be hex. %s" \
                            %self.PluginConf.get('extendedPANID'))

        Domoticz.Debug("Device Management:")
        Domoticz.Debug(" -allowStoreDiscoveryFrames : %s" %self.allowStoreDiscoveryFrames)
        Domoticz.Debug(" -allowForceCreationDomoDevice: %s" %self.allowForceCreationDomoDevice)
        Domoticz.Debug(" -allowReBindingClusters: %s" %self.allowReBindingClusters)
        Domoticz.Debug(" -resetConfigureReporting: %s" %self.resetConfigureReporting)
        Domoticz.Debug(" -resetReadAttributes: %s" %self.resetReadAttributes)
        Domoticz.Debug(" -enableReadAttributes: %s" %self.enableReadAttributes)
        Domoticz.Debug(" -resetMotiondelay: %s" %self.resetMotiondelay)
        Domoticz.Debug(" -vibrationAqarasensitivity: %s" %self.vibrationAqarasensitivity)

        Domoticz.Debug("Zigate Configuration")
        Domoticz.Debug(" -channel: %s" %self.channel)
        Domoticz.Debug(" -allowRemoveZigateDevice: %s" %self.allowRemoveZigateDevice)
        Domoticz.Debug(" -eraseZigatePDM: %s" %self.eraseZigatePDM)
        Domoticz.Debug(" -blueLedOff: %s" %self.blueLedOff)
        Domoticz.Debug(" -TXpower: %s" %self.TXpower_set)
        Domoticz.Debug(" -Certification: %s" %self.Certification)
        Domoticz.Debug(" -allowOTA: %s" %self.allowOTA)

        Domoticz.Debug("Plugin Transport")
        Domoticz.Debug(" -zmode: %s" %self.zmode)
        Domoticz.Debug(" -reTransmit: %s" %self.reTransmit)
        Domoticz.Debug(" -zTimeOut: %s" %self.zTimeOut)
        Domoticz.Debug(" -CrcCheck: %s" %self.CrcCheck)
        Domoticz.Debug(" -sendDelay: %s" %self.sendDelay)
        Domoticz.Debug(" -Ping: %s" %self.Ping)

        Domoticz.Debug("Plugin Directories")
        Domoticz.Debug(" -pluginHome: %s" %self.pluginHome)
        Domoticz.Debug(" -pluginData: %s" %self.pluginData)
        Domoticz.Debug(" -pluginZData: %s" %self.pluginZData)
        Domoticz.Debug(" -pluginReports: %s" %self.pluginReports)
        Domoticz.Debug(" -pluginConfig: %s" %self.pluginConfig)
        Domoticz.Debug(" -pluginWWW: %s" %self.pluginWWW)
        Domoticz.Debug(" -homedirectory: %s" %self.homedirectory)
        Domoticz.Debug(" -filename: %s" %self.filename)

        # Groups Management
        Domoticz.Debug("Groups Management")
        Domoticz.Debug(" -enablegroupmanagement: %s" %self.enablegroupmanagement)
        Domoticz.Debug(" -discoverZigateGroups: %s" %self.discoverZigateGroups)
        Domoticz.Debug(" -enableConfigGroups: %s" %self.enableConfigGroups)

        # Network Topoology
        Domoticz.Debug("Reportings and Statistics")
        Domoticz.Debug(" -logLQI: %s"% self.logLQI)
        Domoticz.Debug(" -networkScan: %s" %self.networkScan)

        if not os.path.exists( self.pluginData ):
            Domoticz.Error( "Cannot access pluginData: %s" %self.pluginData)
        if not os.path.exists( self.pluginZData ):
            Domoticz.Error( "Cannot access pluginZData: %s" %self.pluginZData)
        if not os.path.exists( self.pluginConfig ):
            Domoticz.Error( "Cannot access pluginConfig: %s" %self.pluginConfig)
        if not os.path.exists( self.pluginWWW ):
            Domoticz.Error( "Cannot access pluginWWW: %s" %self.pluginWWW)
        if not os.path.exists( self.pluginReports ):
            Domoticz.Error( "Cannot access pluginReports: %s" %self.pluginReports)
        if not os.path.exists( self.pluginOTAFirmware ):
            Domoticz.Error( "Cannot access pluginReports: %s" %self.pluginOTAFirmware)
