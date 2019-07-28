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
        'Services': { 'Order': 1, 'param': {
                    'enablegroupmanagement':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'enableReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'enableWebServer': { 'type':'bool', 'default':1, 'current':None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'internetAccess': { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'allowOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False}
                    }},

        'DomoticzEnvironment': { 'Order': 2, 'param':{
                    'proto': { 'type':'str', 'default':'http', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    'host': { 'type':'str', 'default':'127.0.0.1', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    'port': { 'type':'str', 'default':'8080', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False}
                    }},

        'WebInterface': { 'Order': 3, 'param': {
                    'enableGzip':      { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableDeflate':   { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableChunk':     { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableKeepalive': { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableCache':     { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':False}
                    }},

            # Polling
            'DevicePolling': { 'Order': 4, 'param': {
                    'polling0000':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0001':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'pollingONOFF':         { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'pollingLvlControl':    { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'polling000C':          { 'type':'int', 'default':3600 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0102':          { 'type':'int', 'default':300 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0201':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0204':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0300':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0400':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0402':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0403':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0405':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0406':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0500':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0502':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                    'polling0702':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True}
                }},
            # Device Management
            'DeviceManagement': { 'Order': 5, 'param': {
                    'allowForceCreationDomoDevice':  { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':False, 'Advanced':True},
                    'resetPluginDS': { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':True, 'Advanced':True},
                    'resetConfigureReporting': { 'type':'bool', 'default':0 , 'current': None , 'restart':True , 'hidden':False, 'Advanced':False},
                    'resetReadAttributes': { 'type':'bool', 'default':0 , 'current': None, 'restart':True  , 'hidden':False, 'Advanced':False},
                    'resetMotiondelay': { 'type':'int', 'default':30 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'doUnbindBind':  { 'type':'bool', 'default':0 , 'current': None , 'restart':False , 'hidden':False, 'Advanced':True},
                    'allowReBindingClusters':  { 'type':'bool', 'default':1 , 'current': None , 'restart':False , 'hidden':False, 'Advanced':True}
                    }},

            # Zigate Configuration
            'ZigateConfiguration': { 'Order': 6, 'param': {
                    'allowRemoveZigateDevice':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                    'blueLedOff':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'enableAPSFailureLoging':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                    'enableAPSFailureReporting':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'Ping':  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'eraseZigatePDM':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'allowAutoPairing': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'Certification':  { 'type':'str', 'default':'CE' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'CertificationCode':  { 'type':'int', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                    'channel':  { 'type':'str', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'TXpower_set':  { 'type':'int', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                    'extendedPANID': { 'type':'hex', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True}
                }},

                #Over The Air Upgrade
            'OverTheAirUpgrade': { 'Order': 7, 'param': {
                    'batteryOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                    'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False}
                }},

            # Plugin Transport
            'PluginTransport': { 'Order': 8, 'param': {
                    'CrcCheck':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                    'reTransmit':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                    'sendDelay':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                    'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                    'zTimeOut':  { 'type':'int', 'default':2 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False}
                }},

            # Plugin Directories
            'PluginConfiguration': { 'Order': 9, 'param': {
                    'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'filename':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                    'pluginHome':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                    'homedirectory':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                    'pluginData':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                    'pluginConfig': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                    'pluginOTAFirmware': { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                    'pluginReports':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                    'pluginWWW':  { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True}
                }},

            # Verbose
            'VerboseLogging': { 'Order': 9, 'param': {
                    'debugMatchId':  { 'type':'str', 'default':'ffff' , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'logFORMAT':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'capturePairingInfos': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'debugInput':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugOutput':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugCluster':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugHeartbeat':{ 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugWidget':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugPlugin':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugDatabase':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugCommand':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugPairing':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugNetworkMap':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugNetworkEnergy':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugGroups':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugIAS':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugAPS':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                    'debugWebServer':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True}
                    }},
            #Others
            'Others': { 'Order': 10, 'param': {
                    'alarmDuration': {'type':'int', 'default':1, 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'numTopologyReports': { 'type':'int', 'default':4 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                    'numEnergyReports': { 'type':'int', 'default':4 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False}
                    }}
            }

class PluginConf:

    def __init__(self, homedir, hardwareid):

        self.pluginConf = {}
        self.homedir = homedir
        self.hardwareid = hardwareid
        self.pluginConf["pluginHome"] = homedir

        for theme in SETTINGS:
            for param in SETTINGS[theme]['param']:
                if param == 'pluginHome':
                    pass
                elif param == 'homedirectory':
                    self.pluginConf[param] = homedir
                elif param == 'pluginData':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Data/'
                elif param == 'pluginConfig':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Conf/'
                elif param == 'pluginWWW':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'www/'
                elif param == 'pluginReports':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Reports/'
                elif param == 'pluginOTAFirmware':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'OTAFirmware/'
                else:
                    self.pluginConf[param] = SETTINGS[theme]['param'][param]['default']

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

        if self.pluginConf['Certification'] == 'CE':
            self.pluginConf['CertificationCode'] = 0x01

        elif self.pluginConf['Certification'] == 'FCC':
            self.pluginConf['CertificationCode'] = 0x02
        else:
            self.pluginConf['CertificationCode'] = 0x01

        if self.pluginConf['zmode'] == 'Agressive':
            self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command

        # Check Path
        for theme in SETTINGS:
            for param in SETTINGS[theme]['param']:
                if SETTINGS[theme]['param'][param]['type'] == 'path':
                    if not os.path.exists( self.pluginConf[ param] ):
                        Domoticz.Error( "Cannot access path: %s" % self.pluginConf[ param] )

        for theme in SETTINGS:
            for param in SETTINGS[theme]['param']:
                if self.pluginConf[param] != SETTINGS[theme]['param'][param]['default']:
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
                    self.write_Settings( )
                    return

        tmpPluginConf = ""
        if not os.path.isfile( self.pluginConf['filename'] ) :
            return
        with open( self.pluginConf['filename'], 'r') as myPluginConfFile:
            tmpPluginConf += myPluginConfFile.read().replace('\n', '')

        PluginConf = {}

        try:
            PluginConf = eval(tmpPluginConf)
        except SyntaxError:
            Domoticz.Error("Syntax Error in %s, all plugin parameters set to default" %self.filename)
        except (NameError, TypeError, ZeroDivisionError):
            Domoticz.Error("Error while importing %s, all plugin parameters set to default" %self.filename)
        else:
            for theme in SETTINGS:
                for param in SETTINGS[theme]['param']:
                    if PluginConf.get( param ):
                        if SETTINGS[theme]['param'][param]['type'] == 'hex':
                            if is_hex( PluginConf.get( param ) ):
                                self.pluginConf[param] = int(PluginConf[ param ], 16)
                            else:
                                Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                        %( param, self.pluginConf[param]['default']))
                                self.pluginConf[param] = self.pluginConf[param]['default']
    
                        elif SETTINGS[theme]['param'][param]['type'] in ( 'bool', 'int'):
                            if PluginConf.get( param).isdigit():
                                self.pluginConf[param] = int(PluginConf[ param ])
                            else:
                                Domoticz.Error("Wrong parameter type for %s, keeping default %s" \
                                    %( param, self.pluginConf[param]['default']))
                                self.pluginConf[param] = self.pluginConf[param]['default']
                        elif SETTINGS[theme]['param'][param]['type'] == ( 'path', 'str'):
                            self.pluginConf[param] = PluginConf[ param ]

        self.write_Settings( )


    def write_Settings(self):
        ' serialize json format the pluginConf '
        ' Only the arameters which are different than default '

        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %self.hardwareid
        pluginConfFile = self.pluginConf['filename']
        write_pluginConf = {}
        for theme in SETTINGS:
            for param in SETTINGS[theme]['param']:
                if self.pluginConf[param] != SETTINGS[theme]['param'][param]['default']:
                    write_pluginConf[param] = self.pluginConf[param]

        with open( pluginConfFile , 'wt') as handle:
            json.dump( write_pluginConf, handle, sort_keys=True, indent=2)


    def _load_Settings(self):

        ' deserialize json format of pluginConf'
        ' load parameters '

        with open( self.pluginConf['filename'] , 'rt') as handle:
            _pluginConf = {}
            try:
                _pluginConf = json.load( handle, encoding=dict)

            except json.decoder.JSONDecodeError as e:
                Domoticz.Error("poorly-formed %s, not JSON: %s" %(self.pluginConf['filename'],e))
                return

            for param in _pluginConf:
                self.pluginConf[param] = _pluginConf[param]

