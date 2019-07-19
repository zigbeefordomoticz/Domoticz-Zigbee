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

class DomoticzDB_Preferences:

    def __init__(self, database):
        self.dbConn = None
        self.dbCursor = None
        
        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return 
        self._openDB( database )


    def _openDB( self, database):

        Domoticz.Debug("Opening %s" %database)
        self.dbConn = sqlite3.connect(database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        self.dbConn.close()


    def retreiveAcceptNewHardware( self):

        if  self.dbCursor is None:
            return 0
        try:
            self.dbCursor.execute("SELECT nValue FROM Preferences WHERE Key = 'AcceptNewHardware'" )
            value = self.dbCursor.fetchone()
            if value == None:
                return 0
            else:
                return value[0]
        except sqlite3.Error as e:
            Domoticz.Error("retreiveAcceptNewHardware - Database error: %s" %e)
            return 0

        except Exception as e:
            Domoticz.Error("retreiveAcceptNewHardware - Exception: %s" %e)
            return 0

    def retreiveWebUserNamePassword( self ):

        if  self.dbCursor is None:
            return ( None, None)
        try:
            self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebUserName' ")
            WebUserName = self.dbCursor.fetchone()
            WebUserName = WebUserName[0]
            Domoticz.Debug("retreiveWebUserNamePassword - WebUserName: %s" %WebUserName)

        except sqlite3.Error as e:
            Domoticz.Error("retreiveWebUserNamePassword - Database error: %s" %e)
            WebUserName = None

        except Exception as e:
            Domoticz.Error("retreiveWebUserNamePassword - Exception: %s" %e)
            WebUserName = None


        try:
            self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebPassword' ")
            WebPassword = self.dbCursor.fetchone()
            WebPassword = WebPassword[0] 
            Domoticz.Debug("retreiveWebUserNamePassword - WebPassword: %s" %WebPassword)
            return (WebUserName, WebPassword)

        except sqlite3.Error as e:
            Domoticz.Error("retreiveWebUserNamePassword - Database error: %s" %e)
            WebPassword = None
            return (WebUserName, WebPassword)

        except Exception as e:
            Domoticz.Error("retreiveWebUserNamePassword - Exception: %s" %e)
            WebPassword = None
            return (WebUserName, WebPassword)

    def unsetAcceptNewHardware( self):

        if  self.dbCursor is None:
            return
        self.dbCursor.execute("UPDATE Preferences Set nValue = '0' Where Key = 'AcceptNewHardware' " )
        self.dbConn.commit()

    def setAcceptNewHardware( self):

        if  self.dbCursor is None:
            return
        self.dbCursor.execute("UPDATE Preferences Set nValue = '1' Where Key = 'AcceptNewHardware' " )
        self.dbConn.commit()


class DomoticzDB_Hardware:

    def __init__(self, database, hardwareID ):
        self.Devices = {}
        self.dbConn = None
        self.dbCursor = None
        self.HardwareID = hardwareID

        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return
        self._openDB( database )

    def _openDB( self, database):

        Domoticz.Debug("Opening %s" %database)
        self.dbConn = sqlite3.connect(database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        self.dbConn.close()

    def disableErasePDM( self):

        if  self.dbCursor is None:
            return
        # Permit to Join is stored in Mode3
        self.dbCursor.execute("UPDATE Hardware Set Mode3 = 'False' Where ID = '%s' " %self.HardwareID)
        self.dbConn.commit()

class DomoticzDB_DeviceStatus:

    def __init__(self, database, hardwareID ):
        Domoticz.Debug("DomoticzDB_DeviceStatus - Init")
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
        self._openDB( database )

    def _openDB( self, database):

        Domoticz.Debug("Opening %s" %database)
        self.dbConn = sqlite3.connect(database)
        self.dbCursor = self.dbConn.cursor()

    def closeDB( self ):

        self.dbConn.close()


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
        if self.AdjValue['Baro'][ID]['Value'] is not None and (int(time()) < self.AdjValue['Baro'][ID]['Stamp'] + 903):
            Domoticz.Debug("Return from Baro cache")
            return self.AdjValue['Baro'][ID]['Value']

        # We need to look to DB
        if  self.dbCursor is None:
            self.AdjValue['Baro'][ID]['Value'] = 0
            self.AdjValue['Baro'][ID]['Stamp'] = int(time())
            return 0
        try:
            Domoticz.Debug("DB AddjValue2 access for %s" %ID)
            self.dbCursor.execute("SELECT AddjValue2 FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
            value = self.dbCursor.fetchone()
            if value == None:
                self.AdjValue['Baro'][ID]['Value'] = 0
                self.AdjValue['Baro'][ID]['Stamp'] = int(time())
                return 0
            else:
                self.AdjValue['Baro'][ID]['Value'] = value[0]
                self.AdjValue['Baro'][ID]['Stamp'] = int(time())
                return value[0]
        except sqlite3.Error as e:
            Domoticz.Error("retreiveAddjValue_baro - Database error: %s" %e)
            return 0

        except Exception as e:
            Domoticz.Error("retreiveAddjValue_baro - Exception: %s" %e)
            return 0

    def retreiveTimeOut_Motion( self, ID):
        """
        Retreive the TmeeOut Motion value of Device.ID
        """

        if ID not in self.AdjValue['TimeOutMotion']:
            Domoticz.Debug("Init Timeoud cache")
            self.AdjValue['TimeOutMotion'][ID] = {}
            self.AdjValue['TimeOutMotion'][ID]['Value'] = None
            self.AdjValue['TimeOutMotion'][ID]['Stamp'] = 0

        Domoticz.Debug("TimeOut - Value: %s, Stamp: %s, Today: %s" %(self.AdjValue['TimeOutMotion'][ID]['Value'], self.AdjValue['TimeOutMotion'][ID]['Stamp'], int(time() )))
        if self.AdjValue['TimeOutMotion'][ID]['Value'] is not None  and ( int(time()) < self.AdjValue['TimeOutMotion'][ID]['Stamp'] + 905):
            Domoticz.Debug("Return from Timeout cache")
            return self.AdjValue['TimeOutMotion'][ID]['Value']

        if  self.dbCursor is None:
            return 0
        try:
            Domoticz.Debug("DB access AddjValue for %s" %ID)
            self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
            value = self.dbCursor.fetchone()
            if value == None:
                return 0
            else:
                self.AdjValue['TimeOutMotion'][ID]['Value'] = value[0]
                self.AdjValue['TimeOutMotion'][ID]['Stamp'] = int(time())
                return value[0]

        except sqlite3.Error as e:
            Domoticz.Error("retreiveTimeOut_Motion - Database error: %s" %e)
            Domoticz.Debug("retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
            return 0

        except Exception as e:
            Domoticz.Error("retreiveTimeOut_Motion - Exception: %s" %e)
            Domoticz.Debug("retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
            return 0


    def retreiveAddjValue_temp( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if ID not in self.AdjValue['Temp']:
            self.AdjValue['Temp'][ID] = {}
            self.AdjValue['Temp'][ID]['Value'] = None
            self.AdjValue['Temp'][ID]['Stamp'] = 0

        if self.AdjValue['Temp'][ID]['Value'] is not None and ( int(time()) < self.AdjValue['Temp'][ID]['Stamp'] + 909):
            Domoticz.Debug("Return from Temp cache")
            return self.AdjValue['Temp'][ID]['Value']

        if  self.dbCursor is None:
            return 0
        try:
            Domoticz.Debug("DB access AddjValue for %s" %ID)
            self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
            value = self.dbCursor.fetchone()
            if value == None:
                return 0
            else:
                self.AdjValue['Temp'][ID]['Value'] = value[0]
                self.AdjValue['Temp'][ID]['Stamp'] = int(time())
                return value[0]

        except sqlite3.Error as e:
            Domoticz.Error("retreiveAddjValue_temp - Database error: %s" %e)
            return 0

        except Exception as e:
            Domoticz.Error("retreiveAddjValue_temp - Exception: %s" %e)
            return 0
