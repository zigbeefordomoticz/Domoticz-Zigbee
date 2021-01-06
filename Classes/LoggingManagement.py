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
import threading
import time

class LoggingManagement:

    def __init__(self, pluginconf, PluginHealth, HardwareID, ListOfDevices, permitTojoin):
        self._newError = False
        self.LogErrorHistory = {}
        self.pluginconf = pluginconf
        self.loggingFileHandle = None
        self.PluginHealth =  PluginHealth
        self.HardwareID = HardwareID
        self.ListOfDevices = ListOfDevices
        self.permitTojoin = permitTojoin
        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None
        self._startTime = int(time.time())
          

    def reset_new_error( self ):
        self._newError  = False

    def is_new_error( self ):
        return bool(self._newError and bool(self.LogErrorHistory))

    def loggingUpdateFirmware(self, FirmwareVersion, FirmwareMajorVersion):
        if self.FirmwareVersion and self.FirmwareMajorVersion:
            return
        self.FirmwareVersion = FirmwareVersion
        self.FirmwareMajorVersion = FirmwareMajorVersion
        if ( self.LogErrorHistory and self.LogErrorHistory['LastLog'] and\
             'StartTime' in self.LogErrorHistory[str(self.LogErrorHistory['LastLog'])] and\
                self.LogErrorHistory[str(self.LogErrorHistory['LastLog'])][ 'StartTime' ] == self._startTime ):
            self.LogErrorHistory[str(self.LogErrorHistory['LastLog'])]['FirmwareVersion'] = FirmwareVersion
            self.LogErrorHistory[str(self.LogErrorHistory['LastLog'])]['FirmwareMajorVersion'] = FirmwareMajorVersion

        
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
            # By default we will leave No Error even if there are from the past
            #if bool(self.LogErrorHistory):
            #    self._newError  = True

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

            
            if self.pluginconf.pluginConf['logThreadName']:
                Domoticz.Log( " [%15s] " %threading.current_thread().name + message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) +  " [%15s] " %threading.current_thread().name + message + '\n'
            else:
                Domoticz.Log( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) +  message + '\n'
            self.loggingFileHandle.write( message )
            self.loggingFileHandle.flush()

    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            if self.pluginconf.pluginConf['logThreadName']:
                Domoticz.Status(  " [%15s] " %threading.current_thread().name + message)
            else:
                Domoticz.Status( message )
        else:
            if self.loggingFileHandle is None:
                self.openLogFile()
            self.logToFile(message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            if self.pluginconf.pluginConf['logThreadName']:
                Domoticz.Log(  " [%15s] " %threading.current_thread().name + message )
            else:
               Domoticz.Log( message ) 
        else: 
            if self.loggingFileHandle is None:
                self.openLogFile()
            self.logToFile( message )

    def _loggingDebug(self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            if self.pluginconf.pluginConf['logThreadName']:
                Domoticz.Log(  " [%15s] " %threading.current_thread().name + message )
            else:
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
        
        #Log to file
        if not self.pluginconf.pluginConf['useDomoticzLog']:
            if self.loggingFileHandle is None:
                self.openLogFile()
            self.logToFile( message )

        #Log empty
        if not self.LogErrorHistory or 'LastLog' not in self.LogErrorHistory:
            self.LogErrorHistory['LastLog'] = 0
            self.LogErrorHistory['0'] = {
                'LastLog': 0,
                'StartTime': self._startTime,
                'FirmwareVersion': self.FirmwareVersion,
                'FirmwareMajorVersion': self.FirmwareMajorVersion,
            }

            self.LogErrorHistory['0']['0'] = self.loggingBuildContext(module, message, nwkid, context)
            self.loggingWriteErrorHistory()
            return # log created, leaving

        #check if existing log contains plugin launch time
        if 'StartTime' in self.LogErrorHistory[str(self.LogErrorHistory['LastLog'])]:
            index = self.LogErrorHistory['LastLog']
            #check if launch time if the same, otherwise, create a new entry
            if self.LogErrorHistory[str(index)]['StartTime'] != self._startTime:
                index += 1
        else: #compatibility with older version
            index = self.LogErrorHistory['LastLog'] + 1

        #check if it's a new entry
        if str(index) not in self.LogErrorHistory:
            self.LogErrorHistory['LastLog'] += 1
            self.LogErrorHistory[str(index)] = {'LastLog': 0}
            self.LogErrorHistory[str(index)]['StartTime'] = self._startTime
            self.LogErrorHistory[str(index)]['FirmwareVersion'] = self.FirmwareVersion
            self.LogErrorHistory[str(index)]['FirmwareMajorVersion'] = self.FirmwareMajorVersion
            self.LogErrorHistory[str(index)]['0'] = self.loggingBuildContext(module, message, nwkid, context)
        else:
            self.LogErrorHistory[str(index)]['LastLog'] += 1
            self.LogErrorHistory[str(index)][str(self.LogErrorHistory[str(index)]['LastLog'])] = self.loggingBuildContext(module, message, nwkid, context)

            if len(self.LogErrorHistory[str(index)]) > 20+4: #log full for this launch time, remove oldest
                idx = list(self.LogErrorHistory[str(index)].keys())[4]
                self.LogErrorHistory[str(index)].pop(idx)

        if len(self.LogErrorHistory) > 5+1: #log full, remove oldest
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
                    'Time': int(time.time()),
                    'Module': module,
                    'nwkid': nwkid,
                    'PluginHealth': _txt,
                    'message': message,
                    'PermitToJoin': self.permitTojoin,
                    'Thread': threading.current_thread().name
                }
        if nwkid and nwkid in self.ListOfDevices:
            _context[ 'DeviceInfos'] = dict(self.ListOfDevices[ nwkid ])
        if context is not None:
            if isinstance(context, dict):
                _context['context'] = context.copy()
            elif isinstance(context, (str, int)):
                _context['context'] = str(context)
        return _context

    def loggingWriteErrorHistory( self ):
        jsonLogHistory =  self.pluginconf.pluginConf['pluginLogs'] + "/" + "Zigate_log_error_history.json"
        with open( jsonLogHistory, "w", encoding='utf-8') as json_file:
            try:
                json.dump( dict(self.LogErrorHistory), json_file)
                json_file.write('\n')
            except Exception as e:
                Domoticz.Error("Hops ! Unable to write LogErrorHistory error: %s log: %s" %(e,self.LogErrorHistory ))
                
    def loggingCleaningErrorHistory( self ):
        if len(self.LogErrorHistory) > 1:
            idx = list(self.LogErrorHistory.keys())[1]
            if 'Time' in self.LogErrorHistory[str(idx)]:
                if time.time() - self.LogErrorHistory[str(idx)]['Time'] > 1360800: #7 days for old structure
                    self.LogErrorHistory.pop(idx)
            elif len(self.LogErrorHistory[str(idx)]) > 4:
                idx2 = list(self.LogErrorHistory[str(idx)].keys())[4]
                if 'Time' in self.LogErrorHistory[str(idx)][str(idx2)] and (time.time() - self.LogErrorHistory[str(idx)][str(idx2)]['Time'] > 1360800): #7 days
                    self.LogErrorHistory[idx].pop(idx2)
            else:
                self.LogErrorHistory.pop(idx)
        if len(self.LogErrorHistory) == 1:
            self.LogErrorHistory.clear()

            
    def loggingClearErrorHistory( self ):
        self.LogErrorHistory.clear()
        self._newError = False
