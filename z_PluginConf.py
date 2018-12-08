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
        self.homedirectory = homedir
        self.CrcCheck = 1
        self.sendDelay = 0
        self.logFORMAT = 0
        self.logLQI = 0
        self.logRepo = homedir
        self.allowRemoveZigateDevice = 0
        self.allowStoreDiscoveryFrames = 0
        self.allowForceCreationDomoDevice = 0
        self.networkScan = 0
        self.channel = 0
        self.zmode = 'ZigBee'  # Default mode. Cmd -> Ack -> Data
        self.reTransmit = 1  # Default mode, we do one retransmit if Data not reach at TO
        self.zTimeOut = 2  # 2'' Tiemout to get Ack and Data
        self.forceConfigureReporting = 0 # Allow to reset the Configure Reporting record
        self.forceReadAttributes = 0 # Allow to reset the ReadAttribute
        self.debugReadCluster = 0
        self.resetMotiondelay = 30
        self.enablegroupmanagement = 0
        self.filename = None

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

        if self.PluginConf.get('logRepo'):
            self.logRepo = self.PluginConf['logRepo']

        if self.PluginConf.get('enablegroupmanagement') and \
                self.PluginConf.get('enablegroupmanagement').isdigit():
            self.enablegroupmanagement = int(self.PluginConf['enablegroupmanagement'], 10)

        if self.PluginConf.get('debugReadCluster') and \
                self.PluginConf.get('debugReadCluster').isdigit():
            self.sendDelay = int(self.PluginConf['debugReadCluster'], 10)

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
