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

        self.dbCursor.execute("SELECT nValue FROM Preferences WHERE Key = 'AcceptNewHardware'" )
        value = self.dbCursor.fetchone()
        return value[0]


    def unsetAcceptNewHardware( self):

        self.dbCursor.execute("UPDATE Preferences Set nValue = '0' Where Key = 'AcceptNewHardware' " )
        self.dbConn.commit()

    def setAcceptNewHardware( self):

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

        self.dbCursor.execute("SELECT AddjValue2 FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
        value = self.dbCursor.fetchone()
        return value[0]

    def retreiveTimeOut_Motion( self, ID):
        """
        Retreive the TmeeOut Motion value of Device.ID
        """

        self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
        value = self.dbCursor.fetchone()
        return value[0]

    def retreiveAddjValue_temp( self, ID):
        """
        Retreive the AddjValue of Device.ID
        """

        self.dbCursor.execute("SELECT AddjValue FROM DeviceStatus WHERE ID = '%s' and HardwareID = '%s'" %(ID, self.HardwareID))
        value = self.dbCursor.fetchone()
        return value[0]


if __name__ == '__main__':


    tstdevice = DomoticzDB_DeviceStatus("/var/lib/domoticz/domoticz.db", "35")
    print(tstdevice.retreiveAddjValue_temp("35"))


    hardwaretable = DomoticzDB_Hardware("/var/lib/domoticz/domoticz.db", "35")
    hardwaretable.disablePermitToJoin()
