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
            return
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
            return
        try:
            self.dbCursor.execute("SELECT sValue FROM Preferences WHERE Key = 'WebUserName' ")
            WebUserName = self.dbCursor.fetchone()
            WebUserName = WebUserName[0]
            Domoticz.Log("retreiveWebUserNamePassword - WebUserName: %s" %WebUserName)

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
            Domoticz.Log("retreiveWebUserNamePassword - WebPassword: %s" %WebPassword)
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


    def retreiveAddjValue_baro( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if  self.dbCursor is None:
            return
        try:
            self.dbCursor.execute("SELECT AddjValue2 FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
            value = self.dbCursor.fetchone()
            if value == None:
                return 0
            else:
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

        if  self.dbCursor is None:
            return
        try:
            self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
            value = self.dbCursor.fetchone()
            if value == None:
                return 0
            else:
                return value[0]

        except sqlite3.Error as e:
            Domoticz.Error("retreiveTimeOut_Motion - Database error: %s" %e)
            Domoticz.Log("retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
            return 0

        except Exception as e:
            Domoticz.Error("retreiveTimeOut_Motion - Exception: %s" %e)
            Domoticz.Log("retreiveTimeOut_Motion for ID: %s HardwareID: %s" %(ID, self.HardwareID))
            return 0


    def retreiveAddjValue_temp( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        if  self.dbCursor is None:
            return
        try:
            self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
            value = self.dbCursor.fetchone()
            if value == None:
                return 0
            else:
                return value[0]

        except sqlite3.Error as e:
            Domoticz.Error("retreiveAddjValue_temp - Database error: %s" %e)
            return 0

        except Exception as e:
            Domoticz.Error("retreiveAddjValue_temp - Exception: %s" %e)
            return 0


if __name__ == '__main__':


    tstdevice = DomoticzDB_DeviceStatus("/var/lib/domoticz/domoticz.db", "35")
    print(tstdevice.retreiveAddjValue_temp("35"))


    hardwaretable = DomoticzDB_Hardware("/var/lib/domoticz/domoticz.db", "35")
    hardwaretable.disablePermitToJoin()
