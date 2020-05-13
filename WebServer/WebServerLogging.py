import Domoticz
import datetime

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

def logging( self, logType, message):
    self.debugWebServer = self.pluginconf.pluginConf['debugWebServer']
    if self.debugWebServer and logType == 'Debug':
        self._loggingDebug( message)
    elif logType == 'Log':
        self._loggingLog( message )
    elif logType == 'Status':
        self._loggingStatus( message)
    return