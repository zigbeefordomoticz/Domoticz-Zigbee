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
import time

class LoggingManagement:

    def __init__(self, pluginconf, PluginHealth, HardwareID):
        self.LogErrorHistory = {}
        self.pluginconf = pluginconf
        self.loggingFileHandle = None
        self.PluginHealth =  PluginHealth
        self.HardwareID = HardwareID
        
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
        self.loggingWriteErrorHistory()

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
                self.openLogFile()
            self.logToFile(message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else: 
            if self.loggingFileHandle is None:
                self.openLogFile()
            self.logToFile( message )

    def _loggingDebug(self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else: 
            if self.loggingFileHandle is None:
                self.openLogFile()
            self.logToFile( message )

    def _logginfilter( self, message, nwkid):

        if nwkid is None:
            self._loggingDebug( message )
        elif nwkid:
            nwkid = nwkid.lower()
            _debugMatchId =  self.pluginconf.pluginConf['debugMatchId'].lower().split(',')
            if ('ffff' in _debugMatchId) or (nwkid in _debugMatchId) or (nwkid == 'ffff'):
                self._loggingDebug(  message )

    def loggingDirector( self, logType, message):
        if  logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message )
            
    def logging( self, module, logType, message, nwkid=None, context=None):
        if logType == 'Error':
            self.loggingError(module, message, nwkid, context)
        elif logType == 'Debug':
            pluginConfModule = "debug"+str(module)
            if pluginConfModule in self.pluginconf.pluginConf:
                if self.pluginconf.pluginConf[pluginConfModule]:
                    self._logginfilter(message, nwkid)
            else:
                self._loggingDebug(message)
        else:
            self.loggingDirector(logType, message )

    def loggingError(self, module, message, nwkid, context):
        Domoticz.Error(message)

        if not self.LogErrorHistory or 'LastLog' not in self.LogErrorHistory:
            self.LogErrorHistory['LastLog'] = 0
            self.LogErrorHistory['0'] = self.loggingBuildContext(module, message, nwkid, context)
        else:
            self.LogErrorHistory['LastLog'] = int(self.LogErrorHistory['LastLog']) + 1
            self.LogErrorHistory[str(self.LogErrorHistory['LastLog'])] = self.loggingBuildContext( module, message, nwkid, context)
            if len(self.LogErrorHistory) > 20: #log full for this module, remove older
                idx = list(self.LogErrorHistory.keys())[1]
                self.LogErrorHistory.pop(idx)

        self.loggingWriteErrorHistory()

    def loggingBuildContext(self, module, message, nwkid, context):
        if not self.PluginHealth:
            _txt = 'Not Started'
        if 'Txt' not in self.PluginHealth:
            _txt = 'Not Started'
        else:
            _txt = self.PluginHealth['Txt']
        _context = {
                    'Time' : int(time.time()),
                    'nwkid' : nwkid,
                    'PluginHealth' : _txt,
                    'message' : message
                }
        if context is not None:
            _context['context'] = context.copy()
            
        return _context

    def loggingWriteErrorHistory( self ):
        jsonLogHistory =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate_log_error_history.json"
        with open( jsonLogHistory, "w", encoding='utf-8') as json_file:
            json.dump( self.LogErrorHistory, json_file)
            json_file.write('\n')

    def loggingCleaningErrorHistory( self ):
        if len(self.LogErrorHistory) > 1:
            idx = list(self.LogErrorHistory.keys())[1]
            if time.time() - self.LogErrorHistory[idx]['Time'] > 1360800: #7 days
                self.LogErrorHistory.pop(idx)
        elif len(self.LogErrorHistory) == 1:
            self.LogErrorHistory.clear()

            
    def loggingClearErrorHistory( self ):
        self.LogErrorHistory.clear()
