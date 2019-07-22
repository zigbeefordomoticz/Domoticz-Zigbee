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
from time import time

CACHE_TIMEOUD = ((15 * 60) + 15)   # num seconds

class DomoticzDB_Preferences:

    def __init__(self, database):
        self.dbConn = None
        self.dbCursor = None
        self.preferences = None
        self.WebUserName = None
        self.WebPassword = None
        self.database = database

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return 


    def _openDB( self):

        Domoticz.Debug("Opening %s" %self.database)
        self.dbConn = sqlite3.connect(self.database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        Domoticz.Debug("Closing %s" %self.database)
        if self.dbConn is not None:
            self.dbConn.close()


    def retreiveAcceptNewHardware( self):

        if self.preferences is not None:
            return self.preferences

        if  self.dbConn is None and self.dbCursor is None:
            self._openDB( )
            try:
                self.dbCursor.execute("SELECT nValue FROM Preferences WHERE Key = 'AcceptNewHardware'" )
                value = self.dbCursor.fetchone()
                if value == None:
                    self.closeDB()
                    self.dbCursor = None
                    return 0
                else:
                    self.preferences = value[0]
                    self.closeDB()
                    self.dbCursor = None
                    return value[0]
            except sqlite3.Error as e:
                Domoticz.Error("retreiveAcceptNewHardware - Database error: %s" %e)
                self.closeDB()
                self.dbCursor = None
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveAcceptNewHardware - Exception: %s" %e)
                self.closeDB()
                self.dbCursor = None
                return 0

            self.closeDB()
            self.dbCursor = None

    def retreiveWebUserNamePassword( self ):

        if self.WebUserName is not None and self.WebPassword is not None:
           return ( self.WebUserName, self.WebPassword)

        if  self.dbConn is None and self.dbCursor is None:
            self._openDB( )
            try:
                self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebUserName' ")
                self.WebUserName = self.dbCursor.fetchone()
                self.WebUserName = WebUserName[0]
                Domoticz.Debug("retreiveWebUserNamePassword - WebUserName: %s" %self.WebUserName)
            except sqlite3.Error as e:
                Domoticz.Error("retreiveWebUserNamePassword - Database error: %s" %e)
                self.WebUserName = None
            except Exception as e:
                Domoticz.Error("retreiveWebUserNamePassword - Exception: %s" %e)
                self.WebUserName = None
    
            try:
                self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebPassword' ")
                self.WebPassword = self.dbCursor.fetchone()
                self.WebPassword = WebPassword[0] 
                Domoticz.Debug("retreiveWebUserNamePassword - WebPassword: %s" %self.WebPassword)
                self.closeDB()
                self.dbCursor = None
                return (self.WebUserName, self.WebPassword)
            except sqlite3.Error as e:
                Domoticz.Error("retreiveWebUserNamePassword - Database error: %s" %e)
                self.WebPassword = None
                self.closeDB()
                self.dbCursor = None
                return (self.WebUserName, self.WebPassword)
            except Exception as e:
                Domoticz.Error("retreiveWebUserNamePassword - Exception: %s" %e)
                self.WebPassword = None
                self.closeDB()
                self.dbCursor = None
                return (self.WebUserName, self.WebPassword)

            self.closeDB()
            self.dbCursor = None

    def unsetAcceptNewHardware( self):

        if  self.dbCursor is None:
            self._openDB( )
            self.dbCursor.execute("UPDATE Preferences Set nValue = '0' Where Key = 'AcceptNewHardware' " )
            self.dbConn.commit()
            self.closeDB()
            self.dbCursor = None

    def setAcceptNewHardware( self):

        if  self.dbCursor is None:
            self._openDB( )
            self.dbCursor.execute("UPDATE Preferences Set nValue = '1' Where Key = 'AcceptNewHardware' " )
            self.dbConn.commit()
            self.closeDB()
            self.dbCursor = None


class DomoticzDB_Hardware:

    def __init__(self, database, hardwareID ):
        self.Devices = {}
        self.dbConn = None
        self.dbCursor = None
        self.HardwareID = hardwareID
        self.database = database

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return

    def _openDB( self, database):

        Domoticz.Debug("Opening %s" %database)
        self.dbConn = sqlite3.connect(database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        Domoticz.Debug("Closing %s" %self.database)
        if self.dbConn is not None:
            self.dbConn.close()

    def disableErasePDM( self):

        if  self.dbCursor is None:
            self._openDB( )
            # Permit to Join is stored in Mode3
            self.dbCursor.execute("UPDATE Hardware Set Mode3 = 'False' Where ID = '%s' " %self.HardwareID)
            self.dbConn.commit()
            self.dbConn.close()
            self.dbCursor = None

class DomoticzDB_DeviceStatus:

    def __init__(self, database, hardwareID ):
        Domoticz.Debug("DomoticzDB_DeviceStatus - Init")
        self.database = database
        self.Devices = {}
        self.dbConn = None
        self.dbCursor = None
        self.HardwareID = hardwareID

        self.AdjValue = {}
        self.AdjValue['Baro'] = {}
        self.AdjValue['TimeOutMotion'] = {}
        self.AdjValue['Temp'] = {}

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return

    def _openDB( self):

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( self.database ) :
            return
        Domoticz.Debug("Opening %s" %self.database)
        self.dbConn = sqlite3.connect(self.database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        if self.dbConn is not None:
            self.dbConn.close()
        Domoticz.Debug("Closing %s" %self.database)


    def retreiveAddjValue_baro( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if ID not in self.AdjValue['Baro']:
            Domoticz.Debug("Init Baro cache")
            self.AdjValue['Baro'][ID] = {}
            self.AdjValue['Baro'][ID]['Value'] = None
            self.AdjValue['Baro'][ID]['Stamp'] = 0

        Domoticz.Debug("Baro - Value: %s, Stamp: %s, Today: %s" %(self.AdjValue['Baro'][ID]['Value'], self.AdjValue['Baro'][ID]['Stamp'], int(time() )))
        if self.AdjValue['Baro'][ID]['Value'] is not None and (int(time()) < self.AdjValue['Baro'][ID]['Stamp'] + CACHE_TIMEOUD):
            Domoticz.Debug("Return from Baro cache")
            return self.AdjValue['Baro'][ID]['Value']

        # We need to look to DB
        if  self.dbCursor is None:
            self._openDB( )
            try:
                Domoticz.Debug("DB AddjValue2 access for %s" %ID)
                self.dbCursor.execute("SELECT AddjValue2 FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
                value = self.dbCursor.fetchone()
                if value == None:
                    self.AdjValue['Baro'][ID]['Value'] = 0
                    self.AdjValue['Baro'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    self.dbCursor = None
                    return 0
                else:
                    self.AdjValue['Baro'][ID]['Value'] = value[0]
                    self.AdjValue['Baro'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    self.dbCursor = None
                    return value[0]
            except sqlite3.Error as e:
                Domoticz.Error("retreiveAddjValue_baro - Database error: %s" %e)
                self.closeDB()
                self.dbCursor = None
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveAddjValue_baro - Exception: %s" %e)
                self.closeDB()
                self.dbCursor = None
                return 0

            self.closeDB()
            self.dbCursor = None

    def retreiveTimeOut_Motion( self, ID):
        """
        Retreive the TmeeOut Motion value of Device.ID
        """

        if ID not in self.AdjValue['TimeOutMotion']:
            Domoticz.Debug("Init Timeoud cache")
            self.AdjValue['TimeOutMotion'][ID] = {}
            self.AdjValue['TimeOutMotion'][ID]['Value'] = None
            self.AdjValue['TimeOutMotion'][ID]['Stamp'] = 0

        if self.AdjValue['TimeOutMotion'][ID]['Value'] is not None  and ( int(time()) < self.AdjValue['TimeOutMotion'][ID]['Stamp'] + CACHE_TIMEOUD):
            Domoticz.Debug("Return from Timeout cache")
            return self.AdjValue['TimeOutMotion'][ID]['Value']

        if  self.dbCursor is None:
            self._openDB( )
            try:
                Domoticz.Debug("DB access AddjValue for %s" %ID)
                self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
                value = self.dbCursor.fetchone()
                if value == None:
                    self.closeDB()
                    self.dbCursor = None
                    return 0
                else:
                    self.AdjValue['TimeOutMotion'][ID]['Value'] = value[0]
                    self.AdjValue['TimeOutMotion'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    self.dbCursor = None
                    return value[0]
    
            except sqlite3.Error as e:
                Domoticz.Error("retreiveTimeOut_Motion - Database error: %s" %e)
                Domoticz.Debug("retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
                self.closeDB()
                self.dbCursor = None
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveTimeOut_Motion - Exception: %s" %e)
                Domoticz.Debug("retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
                self.closeDB()
                self.dbCursor = None
                return 0

            self.closeDB()
            self.dbCursor = None

    def retreiveAddjValue_temp( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if ID not in self.AdjValue['Temp']:
            self.AdjValue['Temp'][ID] = {}
            self.AdjValue['Temp'][ID]['Value'] = None
            self.AdjValue['Temp'][ID]['Stamp'] = 0

        if self.AdjValue['Temp'][ID]['Value'] is not None and ( int(time()) < self.AdjValue['Temp'][ID]['Stamp'] + CACHE_TIMEOUD):
            Domoticz.Debug("Return from Temp cache")
            return self.AdjValue['Temp'][ID]['Value']

        if  self.dbCursor is None:
            self._openDB( )
            try:
                Domoticz.Debug("DB access AddjValue for %s" %ID)
                self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
                value = self.dbCursor.fetchone()
                if value == None:
                    self.closeDB()
                    self.dbCursor = None
                    return 0
                else:
                    self.AdjValue['Temp'][ID]['Value'] = value[0]
                    self.AdjValue['Temp'][ID]['Stamp'] = int(time())
                    self.closeDB()
                    self.dbCursor = None
                    return value[0]
    
            except sqlite3.Error as e:
                Domoticz.Error("retreiveAddjValue_temp - Database error: %s" %e)
                self.closeDB()
                return 0
    
            except Exception as e:
                Domoticz.Error("retreiveAddjValue_temp - Exception: %s" %e)
                self.closeDB()
                self.dbCursor = None
                return 0

            self.closeDB()
            self.dbCursor = None
