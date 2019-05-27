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

from Modules.tools import is_hex


SETTINGS = { 'enableWebServer': { 'type':'bool', 'default':0 , 'current': None , 'restart':True , 'hidden':False},

            # Device Management
            'allowStoreDiscoveryFrames': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
            'allowForceCreationDomoDevice':  { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':False},
            'allowReBindingClusters':  { 'type':'bool', 'default':1 , 'current': None , 'restart':False , 'hidden':False},
            'enableReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
            'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None, 'restart':False , 'hidden':False},
            'resetConfigureReporting': { 'type':'bool', 'default':0 , 'current': None , 'restart':True , 'hidden':False},
            'resetMotiondelay': { 'type':'int', 'default':30 , 'current': None, 'restart':False , 'hidden':False},
            'resetReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':True  , 'hidden':False},
            'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None, 'restart':False , 'hidden':False},
            'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None, 'restart':False , 'hidden':False},

            # Zigate Configuration
            'allowRemoveZigateDevice':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
            'allowOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
            'batteryOTA':  { 'type':'int', 'default':60 , 'current': None, 'restart':True , 'hidden':False},
            'blueLedOff':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
            'Certification':  { 'type':'str', 'default':'CE' , 'current': None, 'restart':True , 'hidden':False},
            'channel':  { 'type':'str', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
            'extendedPANID': { 'type':'hex', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'enableAPSFailureLoging':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
            'enableAPSFailureReporting':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False},
            'eraseZigatePDM':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
            'Ping':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False},
            'TXpower_set':  { 'type':'int', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
            'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False},

            # Plugin Transport
            'CrcCheck':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True},
            'reTransmit':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True},
            'sendDelay':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':True},
            'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'restart':True , 'hidden':True},
            'zTimeOut':  { 'type':'int', 'default':2 , 'current': None, 'restart':True , 'hidden':True},

            # Plugin Directories
            'pluginHome':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'homedirectory':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'pluginData':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'pluginZData': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'pluginConfig': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'filename':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'pluginOTAFirmware': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'pluginReports':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
            'pluginWWW':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},

            # Groups Management
            'enableConfigGroups':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':False},
            'enablegroupmanagement':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
            'discoverZigateGroups':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':False},
    
            # Network Topoology
            'logLQI':  { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False},
            'networkScan': { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False},

            # Debugging
            'logFORMAT':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
            'debugReadCluster':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True}
            }

class PluginConf:

    def __init__(self, homedir, hardwareid):

        self.pluginConf = {}
        self.pluginConf["pluginHome"] = homedir

        for param in SETTINGS:
            if param == 'pluginHome':
                pass
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
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Reports/'
            elif param == 'pluginOTAFirmware':
                self.pluginConf[param] = self.pluginConf['pluginHome'] + 'OTAFirmware/'
            else:
                self.pluginConf[param] = SETTINGS[param]['default']
            Domoticz.Log("pluginConf[%s] initialized to: %s" %(param, self.pluginConf[param]))

        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %hardwareid
        if not os.path.isfile(self.pluginConf['filename']):
            self._load_oldfashon( homedir, hardwareid)
        else:
            self._load_Settings()

        # Sanity Checks
        if self.pluginConf['TradfriKelvinStep'] < 0 or  self.pluginConf['TradfriKelvinStep'] > 255:
            self.pluginConf['TradfriKelvinStep'] = 75
            Domoticz.Status(" -TradfriKelvinStep corrected: %s" %self.pluginConf['TradfriKelvinStep'])

        if self.pluginConf['Certification'] == 'CE':
            self.pluginConf['Certification'] = 0x01

        elif self.pluginConf['Certification'] == 'FCC':
            self.pluginConf['Certification'] = 0x02
        else:
            self.pluginConf['Certification'] = 0x00

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
                Domoticz.Debug("Processing: %s" %param)
                if PluginConf.get( param ):
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

        self.write_Settings( homedir, hardwareid)


    def write_Settings(self, homedir, hardwareid):
        ' serialize json format the pluginConf '
        ' Only the arameters which are different than default '

        pluginConfFile = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %hardwareid
        Domoticz.Debug("Write %s" %pluginConfFile)
        write_pluginConf = {}
        for param in SETTINGS:
            if self.pluginConf[param] != SETTINGS[param]['default']:
                write_pluginConf[param] = self.pluginConf[param]
                Domoticz.Debug("archive %s" %param)

        Domoticz.Debug("Number elements to write: %s" %len(write_pluginConf))
        with open( pluginConfFile , 'wt') as handle:
            json.dump( write_pluginConf, handle, sort_keys=True, indent=2)


    def _load_Settings(self):
        ' deserialize json format of pluginConf'
        ' load parameters '

        with open( self.pluginConf['filename'] , 'rt') as handle:
            _pluginConf = {}
            _pluginConf = json.load( handle, encoding=dict)
            for param in _pluginConf:
                self.pluginConf[param] = _pluginConf[param]

