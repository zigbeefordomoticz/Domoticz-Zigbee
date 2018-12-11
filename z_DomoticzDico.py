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
#import Domoticz
import os.path

DOMOTICZ_DB = "domoticz.db"


class DomoticzDictionnary:

    def __init__(self, startupfolder):
        self.preferences = {}
        dbConn = None
        database = startupfolder + DOMOTICZ_DB
        
        # Check if we have access to the database, if not Error and return
        if not os.path.isfile( database ) :
            return 
        dbConn = sqlite3.connect(database)
        for Key, nValue, sValue in dbConn.execute("SELECT Key, nValue, sValue FROM Preferences"):
            if not sValue:
                self.preferences[str(Key)] = str(nValue)
            else:
                self.preferences[str(Key)] = str(sValue)
        dbConn.close()




if __name__ == '__main__':

    domoDico = DomoticzDictionnary( "/var/lib/domoticz/")
    for key, value in  domoDico.preferences.items():
        print( "%s = %s" %(key,value))
