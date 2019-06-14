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


SETTINGS = { 
            'DomoticzEnvironment': {
                'proto': { 'type':'str', 'default':'http', 'current':None, 'restart':False, 'hidden':False},
                'host': { 'type':'str', 'default':'127.0.0.1', 'current':None, 'restart':False, 'hidden':False},
                'port': { 'type':'str', 'default':'8080', 'current':None, 'restart':False, 'hidden':False}},

            'WebInterface': { 
                'enableWebServer': { 'type':'bool', 'default':0, 'current': None , 'restart':True , 'hidden':False},
                'enableGzip':      { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True},
                'enableDeflate':   { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True},
                'enableChunk':     { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True},
                'enableKeepalive': { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True},
                'enableCache':     { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True}},

            # Device Management
            'DeviceManagement': 
                {
                'allowStoreDiscoveryFrames': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
                'allowForceCreationDomoDevice':  { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':False},
                'allowReBindingClusters':  { 'type':'bool', 'default':1 , 'current': None , 'restart':False , 'hidden':False},
                'enableReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
                'resetConfigureReporting': { 'type':'bool', 'default':0 , 'current': None , 'restart':True , 'hidden':False},
                'resetMotiondelay': { 'type':'int', 'default':30 , 'current': None, 'restart':False , 'hidden':False},
                'resetReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':True  , 'hidden':False},
                'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None, 'restart':False , 'hidden':False},
                'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None, 'restart':False , 'hidden':False}
                },

            # Zigate Configuration
            'ZigateConfiguration':
                {
                'allowRemoveZigateDevice':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
                'blueLedOff':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
                'Certification':  { 'type':'str', 'default':'CE' , 'current': None, 'restart':True , 'hidden':False},
                'CertificationCode':  { 'type':'int', 'default':1 , 'current': None, 'restart':True , 'hidden':True},
                'channel':  { 'type':'str', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
                'extendedPANID': { 'type':'hex', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
                'enableAPSFailureLoging':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
                'enableAPSFailureReporting':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False},
                'eraseZigatePDM':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
                'Ping':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False},
                'TXpower_set':  { 'type':'int', 'default':0 , 'current': None, 'restart':True , 'hidden':False}
                },

                #Over The Air Upgrade
            'OverTheAirUpgrade':
                {
                'allowOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
                'batteryOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
                'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False}
                },

            # Plugin Transport
            'PluginTransport':
                {
                'CrcCheck':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True},
                'reTransmit':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True},
                'sendDelay':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':True},
                'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'restart':True , 'hidden':True},
                'zTimeOut':  { 'type':'int', 'default':2 , 'current': None, 'restart':True , 'hidden':True}
                },

            # Plugin Directories
            'PluginConfiguration':
                {
                'filename':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True},
                'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None, 'restart':False , 'hidden':False},
                'pluginHome':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True},
                'homedirectory':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True},
                'pluginData':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
                'pluginZData': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
                'pluginConfig': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
                'pluginOTAFirmware': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
                'pluginReports':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False},
                'pluginWWW':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False}
                },

            # Groups Management
            'GroupManagement':
                {
                'enablegroupmanagement':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False},
                },
    
            # Debugging
            'Debuging': 
                {
                'logFORMAT':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False},
                'debugReadCluster':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True}
                },
            #Others
            'Others':
                {
                    'logLQI':  { 'type':'int', 'default':3600 , 'current': None, 'restart':False , 'hidden':False},
                    'networkScan': { 'type':'int', 'default':3600 , 'current': None, 'restart':False , 'hidden':False}
                }
            }

class PluginConf:

    def __init__(self, homedir, hardwareid):

        self.pluginConf = {}
        self.homedir = homedir
        self.hardwareid = hardwareid
        self.pluginConf["pluginHome"] = homedir

        for theme in SETTINGS:
            for param in SETTINGS[theme]:
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
                    self.pluginConf[param] = SETTINGS[theme][param]['default']
                Domoticz.Log("pluginConf[%s] initialized to: %s" %(param, self.pluginConf[param]))

        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %hardwareid
        if not os.path.isfile(self.pluginConf['filename']):
            self._load_oldfashon( homedir, hardwareid)
        else:
            self._load_Settings()

        # Reset eraseZigatePDM to default
        self.pluginConf['eraseZigatePDM'] = 0

        # Sanity Checks
        if self.pluginConf['TradfriKelvinStep'] < 0 or  self.pluginConf['TradfriKelvinStep'] > 255:
            self.pluginConf['TradfriKelvinStep'] = 75
            Domoticz.Status(" -TradfriKelvinStep corrected: %s" %self.pluginConf['TradfriKelvinStep'])

        if self.pluginConf['Certification'] == 'CE':
            self.pluginConf['CertificationCode'] = 0x01

        elif self.pluginConf['Certification'] == 'FCC':
            self.pluginConf['CertificationCode'] = 0x02
        else:
            self.pluginConf['CertificationCode'] = 0x01

        if self.pluginConf['zmode'] == 'Agressive':
            self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command
            Domoticz.Status(" -zmod corrected: %s" %self.pluginConf['zmod'])

        # Check Path
        for theme in SETTINGS:
            for param in SETTINGS[theme]:
                if SETTINGS[theme][param]['type'] == 'path':
                    if not os.path.exists( self.pluginConf[ param] ):
                        Domoticz.Error( "Cannot access path: %s" % self.pluginConf[ param] )

        for theme in SETTINGS:
            for param in SETTINGS[theme]:
                Domoticz.Log(" -%s: %s" %(param, self.pluginConf[param]))


    def _load_oldfashon( self, homedir, hardwareid):

        # Import PluginConf.txt
        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.txt" %hardwareid
        if not os.path.isfile(self.pluginConf['filename']) :
            self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%d.txt" %hardwareid
            if not os.path.isfile(self.pluginConf['filename']) :
                self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf.txt"
                if not os.path.isfile(self.pluginConf['filename']) :
                    Domoticz.Log("No PluginConf.txt , using default values")
                    self.write_Settings( )
                    return

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
            for theme in SETTINGS:
                for param in SETTINGS[theme]:
                    Domoticz.Debug("Processing: %s" %param)
                    if PluginConf.get( param ):
                        if SETTINGS[theme][param]['type'] == 'hex':
                            if is_hex( PluginConf.get( param ) ):
                                self.pluginConf[param] = int(PluginConf[ param ], 16)
                                Domoticz.Status(" -%s: %s" %(param, self.pluginConf[param]))
                            else:
                                Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                        %( param, self.pluginConf[param]['default']))
                                self.pluginConf[param] = self.pluginConf[param]['default']
    
                        elif SETTINGS[theme][param]['type'] in ( 'bool', 'int'):
                            if PluginConf.get( param).isdigit():
                                self.pluginConf[param] = int(PluginConf[ param ])
                                Domoticz.Status(" -%s: %s" %(param, self.pluginConf[param]))
                            else:
                                Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                    %( param, self.pluginConf[param]['default']))
                                self.pluginConf[param] = self.pluginConf[param]['default']
                        elif SETTINGS[theme][param]['type'] == ( 'path', 'str'):
                            self.pluginConf[param] = PluginConf[ param ]

        self.write_Settings( )


    def write_Settings(self):
        ' serialize json format the pluginConf '
        ' Only the arameters which are different than default '

        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %self.hardwareid
        pluginConfFile = self.pluginConf['filename']
        Domoticz.Debug("Write %s" %pluginConfFile)
        write_pluginConf = {}
        for theme in SETTINGS:
            for param in SETTINGS[theme]:
                if self.pluginConf[param] != SETTINGS[theme][param]['default']:
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

