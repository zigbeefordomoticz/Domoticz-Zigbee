#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module : logging.py


    Description: Plugin logging routines

"""

import Domoticz
from datetime import datetime

def openLogFile( self ):

    if not self.pluginconf.pluginConf['useDomoticzLog']:
        #logfilename =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate" + '_' + '%02d' %self.HardwareID + "_" + str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + ".log"
        logfilename =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate" + '_' + '%02d' %self.HardwareID + "_" + str(datetime.now().strftime('%Y-%m-%d')) + ".log"
        self.loggingFileHandle = open( logfilename, "a+", encoding='utf-8')

def closeLogFile( self ):

    if self.loggingFileHandle:
        self.loggingFileHandle.close()
        self.loggingFileHandle = None

def loggingPairing( self, logType, message):

    if self.pluginconf.pluginConf['debugPairing'] and logType == 'Debug':
        _loggingLog( self, message )
    elif  logType == 'Log':
        _loggingLog( self, message )
    elif logType == 'Status':
        _loggingStatus( self, message )

    return

def _loggingStatus( self, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        Domoticz.Status( message )
    else:
        if self.loggingFileHandle is None:
            openLogFile( self )
        Domoticz.Status( message )
        message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
        self.loggingFileHandle.write( message )
        self.loggingFileHandle.flush()

def _loggingLog( self, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        Domoticz.Log( message )
    else: 
        if self.loggingFileHandle is None:
            openLogFile( self )
        Domoticz.Log( message )
        message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
        self.loggingFileHandle.write( message )
        self.loggingFileHandle.flush()

def _loggingDebug(self, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        Domoticz.Log( message )
    else: 
        if self.loggingFileHandle is None:
            openLogFile( self )
        message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
        self.loggingFileHandle.write( message )
        self.loggingFileHandle.flush()

def _logginfilter( self, message, nwkid):

    if nwkid is None:
        _loggingDebug( self, message )
    elif nwkid:
        nwkid = nwkid.lower()
        _debugMatchId =  self.pluginconf.pluginConf['debugMatchId'].lower().split(',')
        if ('ffff' in _debugMatchId) or (nwkid in _debugMatchId) or (nwkid == 'ffff'):
            _loggingDebug( self, message )


def loggingCommand( self, logType, message, nwkid=None):
    if self.pluginconf.pluginConf['debugCommand'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingDatabase( self, logType, message, nwkid=None):
    if self.pluginconf.pluginConf['debugDatabase'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingPlugin( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugPlugin'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingCluster( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugCluster'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingOutput( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugOutput'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingInput( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugInput'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingWidget( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugWidget'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return


def loggingHeartbeat( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugHeartbeat'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingLegrand( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugLegrand'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingLumi( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugLumi'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingProfalux( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugProfalux'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingSchneider( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugSchneider'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingPhilips( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugPhilips'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return

def loggingPDM( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugPDM'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    elif  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
    return
