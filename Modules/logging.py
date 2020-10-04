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
import json
from datetime import datetime

def openLogFile( self ):

    if not self.pluginconf.pluginConf['useDomoticzLog']:
        #logfilename =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate" + '_' + '%02d' %self.HardwareID + "_" + str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + ".log"
        logfilename =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate" + '_' + '%02d' %self.HardwareID + "_" + str(datetime.now().strftime('%Y-%m-%d')) + ".log"
        self.loggingFileHandle = open( logfilename, "a+", encoding='utf-8')
    
    jsonLogHistory =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate_log_error_history.json"
    try:
        handle = open( jsonLogHistory, "r", encoding='utf-8')
    except Exception as e:
        Domoticz.Status("Log history not found, no error logged")
        #Domoticz.Error(repr(e))
        return
    try:
        self.LogErrorHistory = json.load( handle, encoding=dict)
    except json.decoder.JSONDecodeError as e:
        res = "Failed"
        Domoticz.Error("load Json LogErrorHistory poorly-formed %s, not JSON: %s" %(jsonLogHistory,e))
    handle.close()


def closeLogFile( self ):

    if self.loggingFileHandle:
        self.loggingFileHandle.close()
        self.loggingFileHandle = None
    loggingWriteErrorHistory(self)

def logToFile( self, message ):

        Domoticz.Status( message )
        message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
        self.loggingFileHandle.write( message )
        self.loggingFileHandle.flush()

def _loggingStatus( self, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        Domoticz.Status( message )
    else:
        if self.loggingFileHandle is None:
            openLogFile( self )
        logToFile( self, message )

def _loggingLog( self, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        Domoticz.Log( message )
    else: 
        if self.loggingFileHandle is None:
            openLogFile( self )
        logToFile( self, message )

def _loggingDebug(self, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        Domoticz.Log( message )
    else: 
        if self.loggingFileHandle is None:
            openLogFile( self )
        logToFile( self, message )

def _logginfilter( self, message, nwkid):

    if nwkid is None:
        _loggingDebug( self, message )
    elif nwkid:
        nwkid = nwkid.lower()
        _debugMatchId =  self.pluginconf.pluginConf['debugMatchId'].lower().split(',')
        if ('ffff' in _debugMatchId) or (nwkid in _debugMatchId) or (nwkid == 'ffff'):
            _loggingDebug( self, message )

def loggingDirector( self, logType, message):

    if  logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message )
        
def logging( self, module, logType, message, nwkid=None, context=None):
    if logType == 'Error':
        loggingError(self, module, message, nwkid, context)
    elif logType == 'Debug':
        pluginConfModule = "debug"+str(module)
        if pluginConfModule in self.pluginconf.pluginConf:
            if self.pluginconf.pluginConf[pluginConfModule]:
                _logginfilter( self, message, nwkid)
        else:
            _loggingDebug(self, message)
    else:
        loggingDirector(self, logType, message )

def loggingError(self, module, message, nwkid, context):
    Domoticz.Error(message)
    if module is None:
        return

    if module not in self.LogErrorHistory:
        self.LogErrorHistory[module] = {
            'LastLog' : 0,
            '0': loggingBuildContext(self, module, message, nwkid, context)
            }
    elif self.LogErrorHistory[module]['LastLog'] != 4:
        logIndex = self.LogErrorHistory[module]['LastLog'] + 1
        self.LogErrorHistory[module]['LastLog'] = logIndex
        self.LogErrorHistory[module][str(logIndex)] = loggingBuildContext(self, module, message, nwkid, context)
    else: #log full for this module, rotate
        self.LogErrorHistory[module]['0'] = self.LogErrorHistory[module]['1'].copy()
        self.LogErrorHistory[module]['1'] = self.LogErrorHistory[module]['2'].copy()
        self.LogErrorHistory[module]['2'] = self.LogErrorHistory[module]['3'].copy()
        self.LogErrorHistory[module]['3'] = self.LogErrorHistory[module]['4'].copy()
        self.LogErrorHistory[module]['4']: loggingBuildContext(self, module, message, nwkid, context)

    loggingWriteErrorHistory(self)

def loggingBuildContext(self, module, message, nwkid, context):
    _context = {
                'time' : str(datetime.now()),
                'nwkid' : nwkid,
                'PluginHealth' : self.PluginHealth['Txt'],
                'context' : context.copy()
            }
    return _context

def loggingWriteErrorHistory( self ):
    jsonLogHistory =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate_log_error_history.json"
    with open( jsonLogHistory, "w", encoding='utf-8') as json_file:
        json.dump( self.LogErrorHistory, json_file)
        json_file.write('\n')

def loggingCleaningErrorHistory( self ):
    _now = datetime.now()
    for module in self.LogErrorHistory:
        _delta = _now - datetime.fromisoformat(self.LogErrorHistory[module]['0']['time'])
        if _delta.days > 7:
            for i in range(0,self.LogErrorHistory[module]['LastLog']):
                self.LogErrorHistory[module][str(i)] = self.LogErrorHistory[module][str(i+1)].copy()
            self.LogErrorHistory[module].pop(str(self.LogErrorHistory[module]['LastLog']))
            if self.LogErrorHistory[module]['LastLog'] == 0:
                self.LogErrorHistory.pop(module)
            else:
                self.LogErrorHistory[module]['LastLog'] -= 1
        return #one by one is enouhgt to prevent too much time in the function


def loggingPairing( self, logType, message):
    
    if self.pluginconf.pluginConf['debugPairing'] and logType == 'Debug':
        _loggingLog( self, message )
    else:
        loggingDirector(self, logType, message )

def loggingCommand( self, logType, message, nwkid=None):
    if self.pluginconf.pluginConf['debugCommand'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingDatabase( self, logType, message, nwkid=None):
    if self.pluginconf.pluginConf['debugDatabase'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingPlugin( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugPlugin'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingCluster( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugCluster'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingBasicOutput( self, logType, message):

    if self.pluginconf.pluginConf['debugBasicOutput'] and logType == 'Debug':   
        _loggingLog( self,  message )       
    else:
        loggingDirector(self, logType, message )

def loggingReadAttributes( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugReadAttributes'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingBinding( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugBinding'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingConfigureReporting( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugConfigureReporting'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingWriteAttributes( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugWriteAttributes'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingThermostats( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugThermostats'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingInput( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugInput'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingWidget( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugWidget'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingHeartbeat( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugHeartbeat'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingLegrand( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugLegrand'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingLumi( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugLumi'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingProfalux( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugProfalux'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingSchneider( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugSchneider'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingPhilips( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugPhilips'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingLivolo( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugLivolo'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingTuya( self, logType, message, nwkid=None):
    
    if self.pluginconf.pluginConf['debugTuya'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def loggingPDM( self, logType, message, nwkid=None):

    if self.pluginconf.pluginConf['debugPDM'] and logType == 'Debug':
        _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )

def logginginRawAPS(self, logType, message, nwkid=None):
    if self.pluginconf.pluginConf['debuginRawAPS'] and logType == 'Debug':
            _logginfilter( self, message, nwkid)
    else:
        loggingDirector(self, logType, message )
