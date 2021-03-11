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
from queue import Queue

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
        self.running = True
        self.logging_queue = None
        self.logging_thread = None
        self._startTime = int(time.time())
        start_logging_thread( self )
          
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
            self.LogErrorHistory = json.load( handle)
            # By default we will leave No Error even if there are from the past
            #if bool(self.LogErrorHistory):
            #    self._newError  = True

        except json.decoder.JSONDecodeError as e:
            self.loggingWriteErrorHistory() #flush the file to avoid the error next startup
            Domoticz.Error("load Json LogErrorHistory poorly-formed %s, not JSON: %s" %(jsonLogHistory,e))
        handle.close()

    def closeLogFile( self ):

        if self.logging_thread is None:
            return
            
        if self.loggingFileHandle:
            self.loggingFileHandle.close()
            self.loggingFileHandle = None

        loggingWriteErrorHistory(self)

        if self.logging_thread:
            self.running = False
            self.logging_queue.put( 'QUIT' )
            self.logging_thread.join()
            del self.logging_thread
            self.logging_thread = None
            del self.logging_queue
            self.logging_queue = None
            Domoticz.Log("Logging Thread shutdown")

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

    def logging( self, module, logType, message, nwkid=None, context=None):

        if self.logging_thread and self.logging_queue:
            logging_tupple = [ threading.current_thread().name, module, logType, message, nwkid, context ]
            self.logging_queue.put( logging_tupple )
        else:
            Domoticz.Log("%s" %message)



def logToFile( self, thread_name, message ):
    
        
        if self.pluginconf.pluginConf['logThreadName']:
            Domoticz.Log( " [%15s] " %tthread_name + message )
            message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) +  " [%15s] " %thread_name + message + '\n'
        else:
            Domoticz.Log( message )
            message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) +  message + '\n'
        self.loggingFileHandle.write( message )
        self.loggingFileHandle.flush()


def _loggingStatus( self, thread_name, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        if self.pluginconf.pluginConf['logThreadName']:
            Domoticz.Status(  " [%15s] " %thread_name + message)
        else:
            Domoticz.Status( message )
    else:
        if self.loggingFileHandle is None:
            self.openLogFile()
        logToFile(self, thread_name, message )

def _loggingLog( self, thread_name, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        if self.pluginconf.pluginConf['logThreadName']:
            Domoticz.Log(  " [%15s] " %thread_name + message )
        else:
            Domoticz.Log( message ) 
    else: 
        if self.loggingFileHandle is None:
            self.openLogFile()
        logToFile( self, thread_name, message )

def _loggingDebug(self, thread_name, message):

    if self.pluginconf.pluginConf['useDomoticzLog']:
        if self.pluginconf.pluginConf['logThreadName']:
            Domoticz.Log(  " [%15s] " %thread_name + message )
        else:
            Domoticz.Log( message )
    else: 
        if self.loggingFileHandle is None:
            self.openLogFile()
        logToFile( self, thread_name, message )

def _logginfilter( self, thread_name, message, nwkid):

    if nwkid is None:
        self._loggingDebug( thread_name, message )
    elif nwkid:
        nwkid = nwkid.lower()
        _debugMatchId =  self.pluginconf.pluginConf['debugMatchId'].lower().split(',')
        if ('ffff' in _debugMatchId) or (nwkid in _debugMatchId) or (nwkid == 'ffff'):
            _loggingDebug( self, thread_name, message )

def loggingDirector( self, thread_name, logType, message):
    if  logType == 'Log':
        _loggingLog( self, thread_name, message )
    elif logType == 'Status':
        _loggingStatus( self, thread_name, message )

def loggingError(self, thread_name, module, message, nwkid, context):
    Domoticz.Error(message)
    self._newError  = True
    
    #Log to file
    if not self.pluginconf.pluginConf['useDomoticzLog']:
        if self.loggingFileHandle is None:
            self.openLogFile()
        self.logToFile( thread_name, message )

    #Log empty
    if not self.LogErrorHistory or 'LastLog' not in self.LogErrorHistory:
        self.LogErrorHistory['LastLog'] = 0
        self.LogErrorHistory['0'] = {
            'LastLog': 0,
            'StartTime': self._startTime,
            'FirmwareVersion': self.FirmwareVersion,
            'FirmwareMajorVersion': self.FirmwareMajorVersion,
        }

        self.LogErrorHistory['0']['0'] = loggingBuildContext(self, thread_name, module, message, nwkid, context)
        loggingWriteErrorHistory( self )
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
        self.LogErrorHistory[str(index)]['0'] = loggingBuildContext(self, thread_name, module, message, nwkid, context)
    else:
        self.LogErrorHistory[str(index)]['LastLog'] += 1
        self.LogErrorHistory[str(index)][str(self.LogErrorHistory[str(index)]['LastLog'])] = loggingBuildContext(self, thread_name, module, message, nwkid, context)

        if len(self.LogErrorHistory[str(index)]) > 20+4: #log full for this launch time, remove oldest
            idx = list(self.LogErrorHistory[str(index)].keys())[4]
            self.LogErrorHistory[str(index)].pop(idx)

    if len(self.LogErrorHistory) > 5+1: #log full, remove oldest
            idx = list(self.LogErrorHistory.keys())[1]
            self.LogErrorHistory.pop(idx)

    loggingWriteErrorHistory( self )

def loggingBuildContext(self, thread_name, module, message, nwkid, context):
    
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
                'Thread': thread_name
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
                    

def start_logging_thread( self ):
    Domoticz.Log( "start_serstart_logging_threadial_reader_thread")
    if self.logging_thread is None:
        self.logging_queue = Queue()
        self.logging_thread = threading.Thread( name="ZiGateLogging_%s" %self.HardwareID,  target=logging_thread,  args=(self,))
        self.logging_thread.start()
        

def logging_thread( self ):
    
    Domoticz.Log( "logging_thread - listening")
    while self.running:
        # We loop until self.running is set to False, 
        # which indicate plugin shutdown   
        data = None

        logging_tupple = self.logging_queue.get()
        if logging_tupple == 'QUIT':
            break

        elif len(logging_tupple) == 6:

            thread_name, module, logType, message, nwkid, context = logging_tupple
            
            if logType == 'Error':
                loggingError( self, thread_name, module, message, nwkid, context)

            elif logType == 'Debug':
                pluginConfModule = "debug"+str(module)

                if pluginConfModule in self.pluginconf.pluginConf:
                    if self.pluginconf.pluginConf[pluginConfModule]:
                        _logginfilter(self, thread_name, message, nwkid)

                else:
                    Domoticz.Error("%s debug module unknown %s" %(pluginConfModule, module))
                    _loggingDebug(self, thread_name, message)
            else:
                loggingDirector(self, thread_name, logType, message )
                
    Domoticz.Log( "logging_thread - ended")
    