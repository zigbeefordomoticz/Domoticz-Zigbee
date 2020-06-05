#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_DomoticzDico.py

    Description: Retreive & Build Domoticz Dictionary

"""

import sqlite3
import Domoticz
import os.path
from base64 import b64decode
from time import time
from datetime import datetime

CACHE_TIMEOUT = ((15 * 60) + 15)   # num seconds

class DomoticzDB_Preferences:

    def __init__(self, database, pluginconf, loggingFileHandle):
        self.dbConn = None
        self.dbCursor = None
        self.preferences = None
        self.WebUserName = None
        self.WebPassword = None
        self.database = database
        self.debugDZDB = None
        self.pluginconf = pluginconf
        self.loggingFileHandle = loggingFileHandle

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            Domoticz.Error("DB_DeviceStatus - Not existing DB %s" %self.database)
            return 

    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Status( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Status( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Status( message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Log( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def _loggingDebug( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def logging( self, logType, message):

        self.debugDZDB = self.pluginconf.pluginConf['debugDZDB']

        if logType == 'Debug' and self.debugDZDB:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)



    def _openDB( self):

        self.logging( "Debug", "DB_Preferences - Opening %s" %self.database)
        try:
            self.dbConn = sqlite3.connect(self.database)
            self.dbCursor = self.dbConn.cursor()

        except sqlite3.Error as e:
            Domoticz.Error("retreiveAcceptNewHardware - Database error: %s" %e)
            self.closeDB()
            return 0

    def closeDB( self ):

        if self.dbConn is not None:
            self.logging( "Debug", "DB_Preferences - Closing %s" %self.database)
            self.dbConn.close()
        self.dbConn = None
        self.dbCursor = None


    def retreiveAcceptNewHardware( self):

        if self.preferences is not None:
            return self.preferences

        if  self.dbConn is None and self.dbCursor is None:
            self._openDB( )
            try:
                self.dbCursor.execute("SELECT nValue FROM Preferences WHERE Key = 'AcceptNewHardware'" )
                value = self.dbCursor.fetchone()
                if value is None:
                    self.closeDB()
                    return 0
                else:
                    self.preferences = value[0]
                    self.closeDB()
                    return value[0]
            except sqlite3.Error as e:
                Domoticz.Error("retreiveAcceptNewHardware - Database error: %s" %e)
                self.closeDB()
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveAcceptNewHardware - Exception: %s" %e)
                self.closeDB()
                return 0

            self.closeDB()
            return 0

    def retreiveWebUserNamePassword( self ):

        if self.WebUserName is not None and self.WebPassword is not None:
           return ( self.WebUserName, self.WebPassword)

        if  self.dbConn is None and self.dbCursor is None:
            self._openDB( )
            try:
                self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebUserName' ")
                self.WebUserName = self.dbCursor.fetchone()
                if self.WebUserName:
                    self.WebUserName = self.WebUserName[0]
                    self.WebUserName = b64decode(self.WebUserName).decode('UTF-8')
                else:
                    self.WebUserName = None

            except sqlite3.Error as e:
                Domoticz.Error("retreiveWebUserNamePassword - Database error: %s" %e)
                self.WebUserName = None
            except Exception as e:
                Domoticz.Error("retreiveWebUserNamePassword - Exception: %s" %e)
                self.WebUserName = None

            try:
                self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebPassword' ")
                self.WebPassword = self.dbCursor.fetchone()
                if self.WebPassword:
                    self.WebPassword = self.WebPassword[0]
                else:
                    self.WebPassword = None

                self.closeDB()
                return (self.WebUserName, self.WebPassword)
            except sqlite3.Error as e:
                Domoticz.Error("retreiveWebUserNamePassword - Database error: %s" %e)
                self.WebPassword = None
                self.closeDB()
                return (self.WebUserName, self.WebPassword)
            except Exception as e:
                Domoticz.Error("retreiveWebUserNamePassword - Exception: %s" %e)
                self.WebPassword = None
                self.closeDB()
                return (self.WebUserName, self.WebPassword)

            self.closeDB()
            self.WebUserName = None
            self.WebPassword = None
            return (None, None)

    def unsetAcceptNewHardware( self):

        if  self.dbCursor is None:
            self._openDB( )
            self.dbCursor.execute("UPDATE Preferences Set nValue = '0' Where Key = 'AcceptNewHardware' " )
            self.dbConn.commit()
            self.closeDB()

    def setAcceptNewHardware( self):

        if  self.dbCursor is None:
            self._openDB( )
            self.dbCursor.execute("UPDATE Preferences Set nValue = '1' Where Key = 'AcceptNewHardware' " )
            self.dbConn.commit()
            self.closeDB()


class DomoticzDB_Hardware:

    def __init__(self, database, pluginconf, hardwareID , loggingFileHandle):
        self.Devices = {}
        self.dbConn = None
        self.dbCursor = None
        self.HardwareID = hardwareID
        self.database = database
        self.debugDZDB = None
        self.pluginconf = pluginconf
        self.loggingFileHandle = loggingFileHandle

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            Domoticz.Error("DB_DeviceStatus - Not existing DB %s" %self.database)
            return

    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Status( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
                Domoticz.Status( message )
            else:
                Domoticz.Status( message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
                Domoticz.Log( message )
            else:
                Domoticz.Log( message )

    def _loggingDebug( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )


    def logging( self, logType, message):

        self.debugDZDB = self.pluginconf.pluginConf['debugDZDB']

        if logType == 'Debug' and self.debugDZDB:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)


    def _openDB( self ):

        self.logging( "Debug", "DB_Hardware - Opening %s" %self.database)
        self.dbConn = sqlite3.connect(self.database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        if self.dbConn is not None:
            self.logging( "Debug", "DB_Hardware Closing %s" %self.database)
            self.dbConn.close()
        self.dbConn = None
        self.dbCursor = None

    def disableErasePDM( self):

        if  self.dbCursor is None:
            self._openDB( )
            # Permit to Join is stored in Mode3
            self.dbCursor.execute("UPDATE Hardware Set Mode3 = 'False' Where ID = '%s' " %self.HardwareID)
            self.dbConn.commit()
            self.dbConn.close()

    def updateMode4( self, newValue):

        if  self.dbCursor is None:
            self._openDB( )

            self.dbCursor.execute("UPDATE Hardware Set Mode4 = %s Where ID = '%s' " %( newValue, self.HardwareID))
            self.dbConn.commit()
            self.dbConn.close()


class DomoticzDB_DeviceStatus:

    def __init__(self, database, pluginconf, hardwareID , loggingFileHandle):
        self.database = database
        self.Devices = {}
        self.dbConn = None
        self.dbCursor = None
        self.HardwareID = hardwareID
        self.debugDZDB = None
        self.pluginconf = pluginconf
        self.loggingFileHandle = loggingFileHandle

        self.AdjValue = {}
        self.AdjValue['Baro'] = {}
        self.AdjValue['TimeOutMotion'] = {}
        self.AdjValue['Temp'] = {}

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return

    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Status( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
                Domoticz.Status( message )
            else:
                Domoticz.Status( message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
                Domoticz.Log( message )
            else:
                Domoticz.Log( message )

    def _loggingDebug( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def logging( self, logType, message):

        self.debugDZDB = self.pluginconf.pluginConf['debugDZDB']

        if logType == 'Debug' and self.debugDZDB:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)


    def _openDB( self):

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( self.database ) :
            Domoticz.Error("DB_DeviceStatus - Not existing DB %s" %self.database)
            return

        self.logging( "Debug", "DB_DeviceStatus - Opening %s" %self.database)
        self.dbConn = sqlite3.connect(self.database)
        self.logging( "Debug", "-----> dbConn: %s" %str(self.dbConn))
        self.dbCursor = self.dbConn.cursor()
        self.logging( "Debug", "-----> dbCursor: %s" %str(self.dbCursor))

    def closeDB( self ):

        if self.dbConn is not None:
            self.logging( "Debug", "DB_DeviceStatus - Closing %s" %self.database)
            self.dbConn.close()
        self.dbConn = None
        self.dbCursor = None


    def retreiveAddjValue_baro( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if ID not in self.AdjValue['Baro']:
            self.logging( "Debug", "Init Baro cache")
            self.AdjValue['Baro'][ID] = {}
            self.AdjValue['Baro'][ID]['Value'] = None
            self.AdjValue['Baro'][ID]['Stamp'] = 0

        self.logging( "Debug", "Baro - Value: %s, Stamp: %s, Today: %s" %(self.AdjValue['Baro'][ID]['Value'], self.AdjValue['Baro'][ID]['Stamp'], int(time() )))
        #if self.AdjValue['Baro'][ID]['Value'] is not None and (int(time()) < self.AdjValue['Baro'][ID]['Stamp'] + CACHE_TIMEOUT):
        if self.AdjValue['Baro'][ID]['Value'] is not None:
            self.logging( "Debug", "Return from Baro cache %s" %self.AdjValue['Baro'][ID]['Value'])
            return self.AdjValue['Baro'][ID]['Value']

        # We need to look to DB
        if  self.dbCursor is None:
            self._openDB( )
            try:
                self.logging( "Debug", "DB AddjValue2 access for %s" %ID)
                self.dbCursor.execute("SELECT AddjValue2 FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
                value = self.dbCursor.fetchone()
                self.logging( "Debug", "--> Value: %s" %value)
                if value is None:
                    self.AdjValue['Baro'][ID]['Value'] = 0
                    self.AdjValue['Baro'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    return 0
                else:
                    self.AdjValue['Baro'][ID]['Value'] = value[0]
                    self.AdjValue['Baro'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    return value[0]
            except sqlite3.Error as e:
                Domoticz.Error("retreiveAddjValue_baro - Database error: %s" %e)
                self.closeDB()
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveAddjValue_baro - Exception: %s" %e)
                self.closeDB()
                return 0

            Domoticz.Error("retreiveAddjValue_baro - Unexpected exception for ID: %s HardwareID: Ms" %(ID, self.HardwareID))
            self.closeDB()
            return 0

    def retreiveTimeOut_Motion( self, ID):
        """
        Retreive the TmeeOut Motion value of Device.ID
        """

        if ID not in self.AdjValue['TimeOutMotion']:
            self.logging( "Debug", "Init Timeoud cache")
            self.AdjValue['TimeOutMotion'][ID] = {}
            self.AdjValue['TimeOutMotion'][ID]['Value'] = None
            self.AdjValue['TimeOutMotion'][ID]['Stamp'] = 0

        #if self.AdjValue['TimeOutMotion'][ID]['Value'] is not None  and ( int(time()) < self.AdjValue['TimeOutMotion'][ID]['Stamp'] + CACHE_TIMEOUT):
        if self.AdjValue['TimeOutMotion'][ID]['Value'] is not None:
            self.logging( "Debug", "Return from Timeout cache %s" %self.AdjValue['TimeOutMotion'][ID]['Value'])
            return self.AdjValue['TimeOutMotion'][ID]['Value']

        if  self.dbCursor is None:
            self._openDB( )
            try:
                self.logging( "Debug", "DB access AddjValue for %s" %ID)
                self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
                value = self.dbCursor.fetchone()
                self.logging( "Debug", "--> Value: %s" %value)
                if value is None:
                    self.closeDB()
                    return 0
                else:
                    self.AdjValue['TimeOutMotion'][ID]['Value'] = value[0]
                    self.AdjValue['TimeOutMotion'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    return value[0]
    
            except sqlite3.Error as e:
                Domoticz.Error("retreiveTimeOut_Motion - Database error: %s" %e)
                self.logging( "Debug", "retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
                self.closeDB()
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveTimeOut_Motion - Exception: %s" %e)
                self.logging( "Debug", "retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
                self.closeDB()
                return 0

            Domoticz.Error("retreiveTimeOut_Motion - Unexpected exception for ID: %s HardwareID: Ms" %(ID, self.HardwareID))
            self.closeDB()
            return 0

    def retreiveAddjValue_temp( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if ID not in self.AdjValue['Temp']:
            self.AdjValue['Temp'][ID] = {}
            self.AdjValue['Temp'][ID]['Value'] = None
            self.AdjValue['Temp'][ID]['Stamp'] = 0

        #if self.AdjValue['Temp'][ID]['Value'] is not None and ( int(time()) < self.AdjValue['Temp'][ID]['Stamp'] + CACHE_TIMEOUT):
        if self.AdjValue['Temp'][ID]['Value'] is not None:
            self.logging( "Debug", "Return from Temp cache %s" %self.AdjValue['Temp'][ID]['Value'])
            return self.AdjValue['Temp'][ID]['Value']

        if  self.dbCursor is None:
            self._openDB( )
            try:
                self.logging( "Debug", "DB access AddjValue for %s" %ID)
                self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
                value = self.dbCursor.fetchone()
                self.logging( "Debug", "--> Value: %s" %value)
                if value is None:
                    self.closeDB()
                    return 0

                self.AdjValue['Temp'][ID]['Value'] = value[0]
                self.AdjValue['Temp'][ID]['Stamp'] = int(time())
                self.closeDB()
                return value[0]
    
            except sqlite3.Error as e:
                Domoticz.Error("retreiveAddjValue_temp - Database error: %s" %e)
                self.closeDB()
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveAddjValue_temp - Exception: %s" %e)
                self.closeDB()
                return 0

            Domoticz.Error("retreiveAddjValue_temp - Unexpected exception for ID: %s HardwareID: Ms" %(ID, self.HardwareID))
            self.closeDB()
            return 0
