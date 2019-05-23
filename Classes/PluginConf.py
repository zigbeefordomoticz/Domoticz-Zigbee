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

#from Modules.tools import is_hex


SETTINGS = { 'enableWebServer': { 'type':'int', 'default':0 , 'current': None },

            # Device Management
            'allowStoreDiscoveryFrames': { 'type':'int', 'default':0 , 'current': None },
            'allowForceCreationDomoDevice':  { 'type':'int', 'default':0 , 'current': None },
            'allowReBindingClusters':  { 'type':'int', 'default':1 , 'current': None },
            'resetConfigureReporting': { 'type':'int', 'default':0 , 'current': None },
            'resetReadAttributes': { 'type':'int', 'default':0 , 'current': None },
            'enableReadAttributes': { 'type':'int', 'default':0 , 'current': None },
            'resetMotiondelay': { 'type':'int', 'default':30 , 'current': None },
            'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None },
            'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None },
            'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None },

            # Zigate Configuration
            'channel':  { 'type':'int', 'default':0 , 'current': None },
            'allowRemoveZigateDevice':  { 'type':'int', 'default':0 , 'current': None },
            'eraseZigatePDM':  { 'type':'int', 'default':0 , 'current': None },
            'blueLedOff':  { 'type':'int', 'default':0 , 'current': None },
            'TXpower_set':  { 'type':'int', 'default':0 , 'current': None },
            'Certification':  { 'type':'str', 'default':0 , 'current': None },
            'enableAPSFailureLoging':  { 'type':'int', 'default':0 , 'current': None },
            'enableAPSFailureReporting':  { 'type':'int', 'default':1 , 'current': None },
            'allowOTA':  { 'type':'int', 'default':0 , 'current': None },
            'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None },
            'batteryOTA':  { 'type':'int', 'default':0 , 'current': None },
            'extendedPANID': { 'type':'hex', 'default':None , 'current': None },

            # Plugin Transport
            'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None },
            'reTransmit':  { 'type':'int', 'default':1 , 'current': None },
            'zTimeOut':  { 'type':'int', 'default':2 , 'current': None },
            'CrcCheck':  { 'type':'int', 'default':1 , 'current': None },
            'sendDelay':  { 'type':'int', 'default':0 , 'current': None },

            # Plugin Directories
            'pluginHome':  { 'type':'path', 'default':None , 'current': None },
            'homedirectory':  { 'type':'path', 'default':None , 'current': None },
            'pluginData':  { 'type':'path', 'default':None , 'current': None },
            'pluginZData': { 'type':'path', 'default':None , 'current': None },
            'pluginConfig': { 'type':'path', 'default':None , 'current': None },
            'pluginWWW':  { 'type':'path', 'default':None , 'current': None },
            'pluginReports':  { 'type':'path', 'default':None , 'current': None },
            'pluginOTAFirmware': { 'type':'path', 'default':None , 'current': None },
            'filename':  { 'type':'path', 'default':None , 'current': None },

            # Groups Management
            'enablegroupmanagement':  { 'type':'int', 'default':0 , 'current': None },
            'discoverZigateGroups':  { 'type':'int', 'default':1 , 'current': None },
            'enableConfigGroups':  { 'type':'int', 'default':1 , 'current': None },
    
            # Network Topoology
            'logLQI':  { 'type':'int', 'default':1 , 'current': None },
            'networkScan': { 'type':'int', 'default':0 , 'current': None },

            # Debugging
            'debugReadCluster':  { 'type':'int', 'default':0 , 'current': None }
            }

class PluginConf:

    def __init__(self, homedir, hardwareid):

        self.pluginConfig = {}
        for param in SETTINGS:
            self.pluginConfig[param] = SETTINGS[param]['default']
            if param == 'pluginHome':
                self.pluginConfig[param] = homedir
            elif param == 'homedirectory':
                self.pluginConfig[param] = homedir
            elif param == 'pluginData':
                self.pluginConfig[param] = self.pluginConfig['pluginHome'] + 'Data/'
            elif param == 'pluginZData':
                self.pluginConfig[param] = self.pluginConfig['pluginHome'] + 'Zdatas/'
            elif param == 'pluginConfig':
                self.pluginConfig[param] = self.pluginConfig['pluginHome'] + 'Conf/'
            elif param == 'pluginWWW':
                self.pluginConfig[param] = self.pluginConfig['pluginHome'] + 'www/'
            elif param == 'pluginReports':
                self.pluginConfig[param] = self.pluginConfig['pluginHome'] + 'www/zigate/reports/'
            elif param == 'pluginOTAFirmware':
                self.pluginConfig[param] = self.pluginConfig['pluginHome'] + 'OTAFirmware/'


        # Import PluginConf.txt
        self.pluginConfig['filename'] = self.pluginConfig['pluginConfig'] + "PluginConf-%02d.txt" %hardwareid
        if not os.path.isfile(self.pluginConfig['filename']) :
            self.pluginConfig['filename'] = self.pluginConfig['pluginConfig'] + "PluginConf-%d.txt" %hardwareid
            if not os.path.isfile(self.pluginConfig['filename']) :
                self.pluginConfig['filename'] = self.pluginConfig['pluginConfig'] + "PluginConf.txt"

        Domoticz.Status("PluginConf: %s" %self.pluginConfig['filename'])
        tmpPluginConf = ""
        if not os.path.isfile( self.pluginConfig['filename'] ) :
            return

        with open( self.pluginConfig['filename'], 'r') as myPluginConfFile:
            tmpPluginConf += myPluginConfFile.read().replace('\n', '')

        Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))

        PluginConf = {}

        try:
            PluginConf = eval(tmpPluginConf)

        except SyntaxError:
            Domoticz.Error("Syntax Error in %s, all plugin parameters set to default" %self.filename)
        except (NameError, TypeError, ZeroDivisionError):
            Domoticz.Error("Error while importing %s, all plugin parameters set to default" %self.filename)
            
        else:
            for param in SETTINGS:
                if PluginConf.get( param ):
                    if SETTINGS[param]['Type'] == 'hex':
                        if is_hex( PluginConf.get( param ) ):
                            self.pluginConfig[param] = int(PluginConf[ param ], 16)
                            Domoticz.Status(" -%s: %s" %(param, self.pluginConfig[param]))
                        else:
                            Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                    %( param, self.pluginConfig[param]['default']))
                            self.pluginConfig[param] = self.pluginConfig[param]['default']

                    elif SETTINGS[param]['Type'] == int:
                        if PluginConf.get('enableWebServer').isdigit():
                            self.pluginConfig[param] = int(PluginConf[ param ])
                            Domoticz.Status(" -%s: %s" %(param, self.pluginConfig[param]))
                        else:
                            Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                    %( param, self.pluginConfig[param]['default']))
                            self.pluginConfig[param] = self.pluginConfig[param]['default']
                    elif SETTINGS[param]['Type'] == 'str':
                        self.pluginConfig[param] = PluginConf[ param ]

            # Sanity Checks
            if self.pluginConfig['TradfriKelvinStep'] < 0 or  self.pluginConfig['TradfriKelvinStep'] > 255:
                self.pluginConfig['TradfriKelvinStep'] = 75
                Domoticz.Status(" -TradfriKelvinStep corrected: %s" %self.pluginConfig['TradfriKelvinStep'])

            if self.pluginConfig['Certification'] == 'CE':
                self.pluginConfig['Certification'] = 0x01
                Domoticz.Status(" -Certification corrected: %s" %self.pluginConfig['Certification'])

            elif self.pluginConfig['Certification'] == 'FCC':
                self.pluginConfig['Certification'] = 0x02
                Domoticz.Status(" -Certification corrected: %s" %self.pluginConfig['Certification'])
            else:
                self.pluginConfig['Certification'] = 0x00
                Domoticz.Status(" -Certification corrected: %s" %self.pluginConfig['Certification'])

            if self.pluginConfig['zmode'] == 'Agressive':
                self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command
                Domoticz.Status(" -zmod corrected: %s" %self.pluginConfig['zmod'])


        # Check Path
        for param in SETTINGS:
            if SETTINGS[param]['type'] == 'path':
                if not os.path.exists( self.pluginConfig[ param] ):
                    Domoticz.Error( "Cannot access path: %s" % self.pluginConfig[ param] )

        for param in SETTINGS:
            Domoticz.Log(" -%s: %s" %(param, self.pluginConfig[param]))



if __name__ == '__main__':

    pluginconf = PluginConf( '/tmp/', 3 )


