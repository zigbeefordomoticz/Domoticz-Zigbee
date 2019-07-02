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
                    'proto': { 'type':'str', 'default':'http', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    'host': { 'type':'str', 'default':'127.0.0.1', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    'port': { 'type':'str', 'default':'8080', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False}},

            'WebInterface': { 
                    'enableWebServer': { 'type':'bool', 'default':0, 'current': None , 'restart':True , 'hidden':False, 'Advanced':False},
                    'enableGzip':      { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True, 'Advanced':False},
                    'enableDeflate':   { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True, 'Advanced':False},
                    'enableChunk':     { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True, 'Advanced':False},
                    'enableKeepalive': { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True, 'Advanced':False},
                    'enableCache':     { 'type':'bool', 'default':0, 'current':None, 'restart':False, 'hidden':True, 'Advanced':False}},

            # Device Management
            'DeviceManagement': 
                {
                    'capturePairingInfos': { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'allowForceCreationDomoDevice':  { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':False, 'Advanced':True},
                    'doUnbindBind':  { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':False, 'Advanced':False},
                    'allowReBindingClusters':  { 'type':'bool', 'default':1 , 'current': None , 'restart':False , 'hidden':False, 'Advanced':False},
                    'enableReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'resetConfigureReporting': { 'type':'bool', 'default':0 , 'current': None , 'restart':True , 'hidden':False, 'Advanced':False},
                    'resetReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':True  , 'hidden':False, 'Advanced':False},
                    'resetMotiondelay': { 'type':'int', 'default':30 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False}
                    },

            # Zigate Configuration
            'ZigateConfiguration':
                {
                    'allowRemoveZigateDevice':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'blueLedOff':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'Certification':  { 'type':'str', 'default':'CE' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'CertificationCode':  { 'type':'int', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                    'channel':  { 'type':'str', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'extendedPANID': { 'type':'hex', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'enableAPSFailureLoging':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'enableAPSFailureReporting':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'eraseZigatePDM':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'Ping':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'TXpower_set':  { 'type':'int', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True}
                },

                #Over The Air Upgrade
            'OverTheAirUpgrade':
                {
                        'allowOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                        'batteryOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                        'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False}
                },

            # Plugin Transport
            'PluginTransport':
                {
                        'CrcCheck':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                        'reTransmit':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                        'sendDelay':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                        'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                        'zTimeOut':  { 'type':'int', 'default':2 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False}
                },

            # Plugin Directories
            'PluginConfiguration':
                {
                        'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                        'filename':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                        'pluginHome':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                        'homedirectory':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                        'pluginData':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                        'pluginZData': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                        'pluginConfig': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                        'pluginOTAFirmware': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                        'pluginReports':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                        'pluginWWW':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True}
                },

            # Groups Management
            'GroupManagement':
                {
                        'enablegroupmanagement':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False}
                },
    
            # Verbose
            'VerboseLogging': 
                {
                        'logFORMAT':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                        'debugNwkIDMatch':  { 'type':'str', 'default':'ffff' , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugInput':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugOutput':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugCluster':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugWidget':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugPairing':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugNetworkMap':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugNetworkEnergy':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugGroups':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                        'debugWebServer':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True}
                },
            #Others
            'Others':
                {
                        'alarmDuration': {'type':'int', 'default':1, 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                        'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                        'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False}
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
                Domoticz.Debug("pluginConf[%s] initialized to: %s" %(param, self.pluginConf[param]))

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
            Domoticz.Debug(" -TradfriKelvinStep corrected: %s" %self.pluginConf['TradfriKelvinStep'])

        if self.pluginConf['Certification'] == 'CE':
            self.pluginConf['CertificationCode'] = 0x01

        elif self.pluginConf['Certification'] == 'FCC':
            self.pluginConf['CertificationCode'] = 0x02
        else:
            self.pluginConf['CertificationCode'] = 0x01

        if self.pluginConf['zmode'] == 'Agressive':
            self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command
            Domoticz.Debug(" -zmod corrected: %s" %self.pluginConf['zmod'])

        # Check Path
        for theme in SETTINGS:
            for param in SETTINGS[theme]:
                if SETTINGS[theme][param]['type'] == 'path':
                    if not os.path.exists( self.pluginConf[ param] ):
                        Domoticz.Error( "Cannot access path: %s" % self.pluginConf[ param] )

        for theme in SETTINGS:
            for param in SETTINGS[theme]:
                if self.pluginConf[param] != SETTINGS[theme][param]['default']:
                    Domoticz.Status("%s set to %s" %(param, self.pluginConf[param]))


    def _load_oldfashon( self, homedir, hardwareid):

        # Import PluginConf.txt
        # Migration 
        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.txt" %hardwareid
        if not os.path.isfile(self.pluginConf['filename']) :
            self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%d.txt" %hardwareid
            if not os.path.isfile(self.pluginConf['filename']) :
                self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf.txt"
                if not os.path.isfile(self.pluginConf['filename']) :
                    Domoticz.Debug("No PluginConf.txt , using default values")
                    self.write_Settings( )
                    return

        Domoticz.Debug("PluginConfig: %s" %self.pluginConf['filename'])
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
                                Domoticz.Debug(" -%s: %s" %(param, self.pluginConf[param]))
                            else:
                                Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                        %( param, self.pluginConf[param]['default']))
                                self.pluginConf[param] = self.pluginConf[param]['default']
    
                        elif SETTINGS[theme][param]['type'] in ( 'bool', 'int'):
                            if PluginConf.get( param).isdigit():
                                self.pluginConf[param] = int(PluginConf[ param ])
                                Domoticz.Debug(" -%s: %s" %(param, self.pluginConf[param]))
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

