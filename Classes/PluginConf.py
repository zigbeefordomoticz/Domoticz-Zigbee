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
                'allowOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                'pingDevices': { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                }},

        'DomoticzEnvironment': { 'Order': 2, 'param':{
                    #'proto': { 'type':'str', 'default':'http', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    #'host': { 'type':'str', 'default':'127.0.0.1', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    'port': { 'type':'str', 'default':'8080', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False}
                    }},

        'WebInterface': { 'Order': 3, 'param': {
                    'Lang':            { 'type':'str', 'default':'en-US', 'current':None, 'restart':False, 'hidden':False, 'Advanced':False},
                    'enableGzip':      { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableDeflate':   { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableChunk':     { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableKeepalive': { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True},
                    'enableCache':     { 'type':'bool', 'default':1, 'current':None, 'restart':False, 'hidden':False, 'Advanced':True}
                    }},

        # Polling
        'DevicePolling': { 'Order': 4, 'param': {
                'pingDevicesFeq':       { 'type':'int', 'default':3600 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'pollingPhilips':       { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'pollingGledopto':      { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'pollingSchneider':     { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'polling0000':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0001':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'pollingONOFF':         { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'pollingLvlControl':    { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'polling000C':          { 'type':'int', 'default':3600 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0100':          { 'type':'int', 'default':3600 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0102':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'polling0201':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'polling0204':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0300':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0400':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0402':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0403':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0405':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0406':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0500':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0502':          { 'type':'int', 'default':86400 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'polling0702':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'polling000f':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'pollingfc01':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'pollingfc21':          { 'type':'int', 'default':900 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True}
            }},
        # Device Management
        'DeviceManagement': { 'Order': 5, 'param': {
                'forcePollingAfterAction':       { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'forcePassiveWidget':            { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'allowForceCreationDomoDevice':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'resetPluginDS':                 { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'resetConfigureReporting':       { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'resetReadAttributes':           { 'type':'bool', 'default':0 , 'current': None, 'restart':True  , 'hidden':False, 'Advanced':True},
                'resetMotiondelay':              { 'type':'int', 'default':30 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'allowGroupMembership':          { 'type':'bool', 'default':1 , 'current': None, 'restart':True  , 'hidden':False, 'Advanced':True},
                'doUnbindBind':                  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'allowReBindingClusters':        { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True}
            }},

        # Zigate Configuration
        'ZigateConfiguration': { 'Order': 6, 'param': {
                'zigatePartOfGroup0000':         { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'allowRemoveZigateDevice':       { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'blueLedOnOff':                  { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'enableACKNACK':                 { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'resetPermit2Join':              { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'enableAPSFailureLoging':        { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                'enableAPSFailureReporting':     { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                'Ping':                          { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'eraseZigatePDM':                { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'breakConfigureReporting':       { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'Certification':                 { 'type':'str', 'default':'CE' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                'CertificationCode':             { 'type':'int', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                'channel':                       { 'type':'str', 'default':'0' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                'TXpower_set':                   { 'type':'int', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'extendedPANID':                 { 'type':'hex', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True}  
            }},

        # Command Transitionin tenth of seconds
        'CommandTransition': { 'Order': 7, 'param': {
                'moveToHueSatu':     { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'moveToColourTemp':  { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'moveToColourRGB':   { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'moveToLevel':       { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
            }},

            #Over The Air Upgrade
        'OverTheAirUpgrade': { 'Order': 7, 'param': {
                'forceOTAUpgrade': { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'forceOTAMask': { 'type':'hex', 'default':0x00050000 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'batteryOTA':  { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                'waitingOTA':  { 'type':'int', 'default':3600 , 'current': None, 'restart':True , 'hidden':False, 'Advanced':False},
                'OTAwait4nextImage': { 'type':'int', 'default':60 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True}
            }},

        # Plugin Transport
        'PluginTransport': { 'Order': 9, 'param': {
                #'APSrteError':  {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                #'APSreTx': {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                #'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                'CrcCheck':    { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                'reTransmit':  { 'type':'bool', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                'sendDelay':   { 'type':'bool', 'default':0 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                'zTimeOut':    { 'type':'int', 'default':1 , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
            }},

        # Plugin Directories
        'PluginConfiguration': { 'Order': 10, 'param': {
                'numDeviceListVersion': { 'type':'int', 'default':12 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'filename':             { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                'pluginHome':           { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                'homedirectory':        { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':True},
                'pluginData':           { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'pluginConfig':         { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'pluginOTAFirmware':    { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'pluginReports':        { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'pluginWWW':            { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True},
                'pluginLogs':           { 'type':'path', 'default':'' , 'current': None, 'restart':True , 'hidden':False, 'Advanced':True}
            }},

        # Verbose
        'VerboseLogging': { 'Order': 11, 'param': {
                'debugMatchId':         { 'type':'str', 'default':'ffff' , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'useDomoticzLog':       { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'logDeviceUpdate':      { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'logFORMAT':            { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'capturePairingInfos':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'debugRSSI':            { 'type':'int', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'debugInput':           { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugBasicOutput':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugBinding':         { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugConfigureReporting':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugWriteAttributes':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugReadAttributes':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugThermostats':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugTransportTx':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'debugTransportRx':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'debugCluster':         { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugHeartbeat':       { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugWidget':          { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugPlugin':          { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugDatabase':        { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugCommand':         { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugPairing':         { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugNetworkMap':      { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugNetworkEnergy':   { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugGroups':          { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugOTA':             { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugIAS':             { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugAPS':             { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugDZDB':            { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugWebServer':       { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugzigateCmd':       { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'debugLegrand':         { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugLumi':            { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugLivolo':          { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugProfalux':        { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugSchneider':       { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugPhilips':         { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'debugPDM':             { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True}
                }},

        # Legrand Specific
        'Legrand': { 'Order': 12, 'param': {
                'EnableLedIfOn':    {'type':'bool', 'default':1, 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'EnableLedInDark':  {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'EnableLedShutter': {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'EnableDimmer':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'EnableReleaseButton':     { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'LegrandFilPilote': { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                }},

        # Schneider Wiser configuration
        'Schneider Wiser':  { 'Order': 13, 'param': {
                'enableSchneiderWiser': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'reenforcementWiser': { 'type':'int', 'default':300 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                }},

        #Others
        'Others': { 'Order': 14, 'param': {
                'alarmDuration': {'type':'int', 'default':1, 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'numTopologyReports': { 'type':'int', 'default':4 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'numEnergyReports': { 'type':'int', 'default':4 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'PowerOn_OnOff': { 'type':'int', 'default':255 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'TradfriKelvinStep': { 'type':'int', 'default':51 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                'AqaraOppleBulbMode': {'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'vibrationAqarasensitivity': { 'type':'str', 'default':'medium' , 'current': None, 'restart':False , 'hidden':False, 'Advanced':False},
                }},

        'Patching': { 'Order': 15, 'param': {
            'Bug566': {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                }},

        # Experimental
        'Experimental': { 'Order': 16, 'param': {
                'expJsonDatabase': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'ExpDeviceAnnoucement1': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'ExpDeviceAnnoucement2': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'ExpDeviceAnnoucement3': { 'type':'bool', 'default':1 , 'current': None, 'restart':False , 'hidden':False, 'Advanced':True},
                'XiaomiLeave':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
                'rebindLivolo':  { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'zmode':  { 'type':'str', 'default':'ZigBee' , 'current': None, 'restart':True , 'hidden':True, 'Advanced':False},
                'APSrteError':  {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'APSreTx': {'type':'bool', 'default':0, 'current': None, 'restart':False , 'hidden':True, 'Advanced':False},
                'allowAutoPairing': { 'type':'bool', 'default':0 , 'current': None, 'restart':False , 'hidden':True, 'Advanced':True},
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
                    continue
                if param == 'homedirectory':
                    self.pluginConf[param] = homedir
                elif param == 'pluginConfig':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Conf/'
                elif param == 'pluginData':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Data/'
                elif param == 'pluginLogs':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Logs/'
                elif param == 'pluginOTAFirmware':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'OTAFirmware/'
                elif param == 'pluginReports':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'Reports/'
                elif param == 'pluginWWW':
                    self.pluginConf[param] = self.pluginConf['pluginHome'] + 'www/'
                else:
                    self.pluginConf[param] = SETTINGS[theme]['param'][param]['default']

        self.pluginConf['filename'] = self.pluginConf['pluginConfig'] + "PluginConf-%02d.json" %hardwareid
        if os.path.isfile(self.pluginConf['filename']):
            self._load_Settings()

        else:
            self._load_oldfashon( homedir, hardwareid)

        # Reset eraseZigatePDM to default
        self.pluginConf['eraseZigatePDM'] = 0

        # Sanity Checks
        if self.pluginConf['TradfriKelvinStep'] < 0 or  self.pluginConf['TradfriKelvinStep'] > 255:
            self.pluginConf['TradfriKelvinStep'] = 75

        if (
            self.pluginConf['Certification'] == 'CE'
            or self.pluginConf['Certification'] != 'FCC'
        ):
            self.pluginConf['CertificationCode'] = 0x01

        else:
            self.pluginConf['CertificationCode'] = 0x02

        if self.pluginConf['zmode'] == 'Agressive':
            self.zmode = 'Agressive'  # We are only waiting for Ack to send the next Command

        # Check Path
        for theme in SETTINGS:
            for param in SETTINGS[theme]['param']:
                if SETTINGS[theme]['param'][param]['type'] == 'path' and not os.path.exists(self.pluginConf[param]):
                    Domoticz.Error( "Cannot access path: %s" % self.pluginConf[ param] )

        # Let's check the Type
        for theme in SETTINGS:
            for param in SETTINGS[theme]['param']:
                if self.pluginConf[param] != SETTINGS[theme]['param'][param]['default']:
                    if SETTINGS[theme]['param'][param]['type'] == 'hex':
                        if isinstance(self.pluginConf[param], str):
                            self.pluginConf[param] = int(self.pluginConf[param],16)
                        Domoticz.Status("%s set to 0x%x" %(param, self.pluginConf[param]))
                    else:
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
                    if SETTINGS[theme]['param'][param]['type'] == 'hex':
                        write_pluginConf[param] = '%X' %self.pluginConf[param]
                    else:
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