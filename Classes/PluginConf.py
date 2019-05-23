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
import json

#from Modules.tools import is_hex


SETTINGS = { 'enableWebServer': { 'type':'int', 'default':0 , 'current': None , 'Restart':True },

            # Device Management
            'allowStoreDiscoveryFrames': { 'type':'int', 'default':0 , 'current': None, 'Restart':False },
            'allowForceCreationDomoDevice':  { 'type':'int', 'default':0 , 'current': None , 'Restart':False },
            'allowReBindingClusters':  { 'type':'int', 'default':1 , 'current': None , 'Restart':False },
            'resetConfigureReporting': { 'type':'int', 'default':0 , 'current': None , 'Restart':True },
            'resetReadAttributes': { 'type':'int', 'default':0 , 'current': None, 'Restart':True  },
            'enableReadAttributes': { 'type':'int', 'default':0 , 'current': None, 'Restart':False },
            'resetMotiondelay': { 'type':'int', 'default':30 , 'current': None, 'Restart':False },
            'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None, 'Restart':False },
            'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None, 'Restart':False },
            'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None, 'Restart':False },

            # Zigate Configuration
            'channel':  { 'type':'str', 'default':0 , 'current': None, 'Restart':True },
            'allowRemoveZigateDevice':  { 'type':'int', 'default':0 , 'current': None, 'Restart':False },
            'eraseZigatePDM':  { 'type':'int', 'default':0 , 'current': None, 'Restart':False },
            'blueLedOff':  { 'type':'int', 'default':0 , 'current': None, 'Restart':True },
            'TXpower_set':  { 'type':'int', 'default':0 , 'current': None, 'Restart':True },
            'Certification':  { 'type':'str', 'default':0 , 'current': None, 'restart':True },
            'enableAPSFailureLoging':  { 'type':'int', 'default':0 , 'current': None, 'Restart':False },
            'enableAPSFailureReporting':  { 'type':'int', 'default':1 , 'current': None, 'Restart':False },
            'allowOTA':  { 'type':'int', 'default':0 , 'current': None, 'Restart':True },
            'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None, 'Restart':True },
            'batteryOTA':  { 'type':'int', 'default':0 , 'current': None, 'Restart':True },
            'extendedPANID': { 'type':'hex', 'default':None , 'current': None, 'Restart':True },

            # Plugin Transport
            'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'Restart':True },
            'reTransmit':  { 'type':'int', 'default':1 , 'current': None, 'Restart':True },
            'zTimeOut':  { 'type':'int', 'default':2 , 'current': None, 'Restart':True },
            'CrcCheck':  { 'type':'int', 'default':1 , 'current': None, 'Restart':True },
            'sendDelay':  { 'type':'int', 'default':0 , 'current': None, 'Restart':True },

            # Plugin Directories
            'pluginHome':  { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'homedirectory':  { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'pluginData':  { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'pluginZData': { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'pluginConfig': { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'pluginWWW':  { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'pluginReports':  { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'pluginOTAFirmware': { 'type':'path', 'default':None , 'current': None, 'Restart':True },
            'filename':  { 'type':'path', 'default':None , 'current': None, 'Restart':True },

            # Groups Management
            'enablegroupmanagement':  { 'type':'int', 'default':0 , 'current': None, 'Restart':True },
            'discoverZigateGroups':  { 'type':'int', 'default':1 , 'current': None, 'Restart':True },
            'enableConfigGroups':  { 'type':'int', 'default':1 , 'current': None, 'Restart':True },
    
            # Network Topoology
            'logLQI':  { 'type':'int', 'default':1 , 'current': None, 'Restart':True },
            'networkScan': { 'type':'int', 'default':0 , 'current': None, 'Restart':True },

            # Debugging
            'debugReadCluster':  { 'type':'int', 'default':0 , 'current': None, 'Restart':False }
            }

class PluginConf:

    def __init__(self, homedir, hardwareid):

        self.pluginConf = {}
        for param in SETTINGS:
            self.pluginConf[param] = SETTINGS[param]['default']
            if param == 'pluginHome':
                self.pluginConf[param] = homedir
            elif param == 'homedirectory':
                self.pluginConf[param] = homedir
            elif param == 'pluginData':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Data/'
            elif param == 'pluginZData':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Zdatas/'
            elif param == 'pluginConfig':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Conf/'
            elif param == 'pluginWWW':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'www/'
            elif param == 'pluginReports':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'www/zigate/reports/'
            elif param == 'pluginOTAFirmware':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'OTAFirmware/'

        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %hardwareid
        if not os.path.isfile(self.pluginConf['filename']) :
            self._load_oldfashon( homedir, hardwareid)
        else:
            self._load_Settings()

        # Sanity Checks
        if self.pluginConf['TradfriKelvinStep'] < 0 or  self.pluginConf['TradfriKelvinStep'] > 255:
            self.pluginConf['TradfriKelvinStep'] = 75
            Domoticz.Status(" -TradfriKelvinStep corrected: %s" %self.pluginConf['TradfriKelvinStep'])

        if self.pluginConf['Certification'] == 'CE':
            self.pluginConf['Certification'] = 0x01
            Domoticz.Status(" -Certification corrected: %s" %self.pluginConf['Certification'])

        elif self.pluginConf['Certification'] == 'FCC':
            self.pluginConf['Certification'] = 0x02
            Domoticz.Status(" -Certification corrected: %s" %self.pluginConf['Certification'])
        else:
            self.pluginConf['Certification'] = 0x00
            Domoticz.Status(" -Certification corrected: %s" %self.pluginConf['Certification'])

        if self.pluginConf['zmode'] == 'Agressive':
            self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command
            Domoticz.Status(" -zmod corrected: %s" %self.pluginConf['zmod'])

        # Check Path
        for param in SETTINGS:
            if SETTINGS[param]['type'] == 'path':
                if not os.path.exists( self.pluginConf[ param] ):
                    Domoticz.Error( "Cannot access path: %s" % self.pluginConf[ param] )

        for param in SETTINGS:
            Domoticz.Log(" -%s: %s" %(param, self.pluginConf[param]))



    def _load_oldfashon( self, homedir, hardwareid):

        # Import PluginConf.txt
        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.txt" %hardwareid
        if not os.path.isfile(self.pluginConf['filename']) :
            self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%d.txt" %hardwareid
            if not os.path.isfile(self.pluginConf['filename']) :
                self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf.txt"

        Domoticz.Status("PluginConfig: %s" %self.pluginConf['filename'])
        tmpPluginConf = ""
        if not os.path.isfile( self.pluginConf['filename'] ) :
            return
        with open( self.pluginConf['filename'], 'r') as myPluginConfFile:
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
                Domoticz.Log("Processing: %s" %param)
                if PluginConf.get( param ):
                    Domoticz.Log("---> found in PluginConf.txt")
                    if SETTINGS[param]['type'] == 'hex':
                        if is_hex( PluginConf.get( param ) ):
                            self.pluginConf[param] = int(PluginConf[ param ], 16)
                            Domoticz.Status(" -%s: %s" %(param, self.pluginConf[param]))
                        else:
                            Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                    %( param, self.pluginConf[param]['default']))
                            self.pluginConf[param] = self.pluginConf[param]['default']

                    elif SETTINGS[param]['type'] == 'int':
                        if PluginConf.get('enableWebServer').isdigit():
                            self.pluginConf[param] = int(PluginConf[ param ])
                            Domoticz.Status(" -%s: %s" %(param, self.pluginConf[param]))
                        else:
                            Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                    %( param, self.pluginConf[param]['default']))
                            self.pluginConf[param] = self.pluginConf[param]['default']
                    elif SETTINGS[param]['type'] == 'str':
                        self.pluginConf[param] = PluginConf[ param ]


    def _write_Settings(self):
        ' serialize json format the pluginConf '
        ' Only the arameters which are different than default '

        Domoticz.Log("Write %s" %self.pluginConfFile)
        for param in SETTINGS:
            if self.pluginConf[param]['current'] != SETTINGS[param]['default']
                write_pluginConf[param] = self.pluginConf[param]['current']

        with open( self.groupListFileName , 'wb') as handle:
            json.dump( handle, write_pluginConf, sort=True, indent=2)


    def _load_Settings(self):
        ' deserialize json format of pluginConf'
        ' load parameters '

        Domoticz.Status("Opening %s" %self.pluginConf['filename'])
        load_pluginConf = {}
        with open( self.pluginConf['filename'] , 'rt') as handle:
            json.load( handle, load_pluginConf)
            for param in load_pluginConf:
                self.pluginConf[param]['current'] = load_pluginConf[param]
                Domoticz.Status(" PluginConf settings: %s updated to: %s" %(param, self.pluginConf[param]['current']))
