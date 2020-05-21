#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
from datetime import datetime

def logging( self, logType, message):

    def _writeMessage( self, message):
        message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
        self.loggingFileHandle.write( message )
        self.loggingFileHandle.flush()

    def _loggingStatus( self, message):
        Domoticz.Status( message )
        if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
            _writeMessage( self, message)

    def _loggingLog( self, message):
        Domoticz.Log( message )
        if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
            _writeMessage( self, message)

    def _loggingDebug( self, message):
        if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
            _writeMessage( self, message)
        else:
            Domoticz.Log( message )


    self.debugWebServer = self.pluginconf.pluginConf['debugGroups']
    if self.debugWebServer and logType == 'Debug':
        _loggingDebug( self, message)
    elif logType == 'Log':
        _loggingLog( self,  message )
    elif logType == 'Status':
        _loggingStatus( self, message)