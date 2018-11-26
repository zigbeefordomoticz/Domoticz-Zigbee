"""
Class PluginConf

Description: Import the PluginConf.txt file and initialized each of the available parameters in this file
Parameters not define in the PluginConf.txt file will be set to their default value.

"""

import Domoticz

PLUGINCONF_FILENAME = "PluginConf.txt"

class PluginConf:

    def __init__(self, homedir):
        self.homedirectory = homedir
        self.CrcCheck = 1
        self.sendDelay = 0
        self.logFORMAT = 0
        self.logLQI = 0
        self.allowRemoveZigateDevice = 0
        self.allowStoreDiscoveryFrames = 0
        self.forceCreationDomoDevice = 0
        self.networkScan = 0
        self.channel = 11

        # Import PluginConf.txt
        tmpPluginConf=""
        with open(self.homedirectory + PLUGINCONF_FILENAME, 'r') as myPluginConfFile:
            tmpPluginConf += myPluginConfFile.read().replace('\n', '')

        Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))

        self.PluginConf=eval(tmpPluginConf)

        if  self.PluginConf.get('sendDelay') and \
                self.PluginConf.get('sendDelay').isdigit():
            self.sendDelay = int(self.PluginConf['sendDelay'],10)

        if  self.PluginConf.get('allowStoreDiscoveryFrames') and \
                self.PluginConf.get('allowStoreDiscoveryFrames').isdigit():
            self.allowStoreDiscoveryFrames = int(self.PluginConf['allowStoreDiscoveryFrames'],10)

        if  self.PluginConf.get('logFORMAT') and \
                self.PluginConf.get('logFORMAT').isdigit():
            self.logFORMAT = int(self.PluginConf['logFORMAT'],10)

        if  self.PluginConf.get('logLQI') and self.PluginConf.get('logLQI').isdigit():
            self.logLQI = int(self.PluginConf['logLQI'],10)

        if  self.PluginConf.get('allowRemoveZigateDevice') and \
                self.PluginConf.get('allowRemoveZigateDevice').isdigit():
            self.allowRemoveZigateDevice = int(self.PluginConf['allowRemoveZigateDevice'],10)

        if  self.PluginConf.get('forceCreationDomoDevice') and \
                self.PluginConf.get('forceCreationDomoDevice').isdigit():
            self.forceCreationDomoDevice = int(self.PluginConf['forceCreationDomoDevice'],10)

        if  self.PluginConf.get('networkScan') and \
                self.PluginConf.get('networkScan').isdigit():
            self.networkScan = int(self.PluginConf['networkScan'],10)


        if self.PluginConf.get('channel') and \
                self.PluginConf.get('channel').isdigit():
            self.channel = self.PluginConf('channel')
            self.channel = [ c.strip() for c in self.channel.split(',') ]


