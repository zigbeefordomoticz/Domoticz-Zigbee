#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
Class WebGui

Description: Check if zigate.html, zigate folder and files exist, and update them if need

"""

import Domoticz
import z_database
import os


def CheckForUpdate( self ) :
    if self.DomoticzVersion >= '4.10267':
        DomoticzWWWFolder = self.StartupFolder + "www/templates"
    else :
        DomoticzWWWFolder = self.homedirectory + "../../www/templates"
    if not os.path.exists(DomoticzWWWFolder + "/zigate") :
        # define the access rights
        access_rights = 0o775
        os.mkdir(DomoticzWWWFolder + "/zigate", access_rights)
        os.mkdir(DomoticzWWWFolder + "/zigate/reports", access_rights)
    Domoticz.Log("web source dir : " + self.homedirectory + "www/zigate/")
    listOfFiles = os.listdir( self.homedirectory + "www/zigate/")
    for l in listOfFiles:
        fileOld=DomoticzWWWFolder + "/zigate/" + l
        Domoticz.Log("Old file : " + fileOld)
        fileNew=self.homedirectory + "/www/zigate/" + l
        Domoticz.Log("New file : " + fileNew)
        if os.path.isfile( fileOld ):
            if CheckVersion( fileNew ) >> CheckVersion( fileOld ) :
                z_database._copyfile( fileNew, fileOld)
                Domoticz.Log("New file " + l + " is copied")
        else :
            z_database._copyfile( fileNew, fileOld)
            Domoticz.Log("New file " + l + " is created")
    fileOld=DomoticzWWWFolder + "/zigate.html"
    fileNew=self.homedirectory + "www/zigate/zigate.html"
    if os.path.isfile( fileOld ):
        if CheckVersion( fileNew ) >> CheckVersion( fileOld ) :
            z_database._copyfile( fileNew, fileOld)
            Domoticz.Log("New file zigate.html is copied")
    else :
        z_database._copyfile( fileNew, fileOld)
        Domoticz.Log("New file zigate.html is created")
    Domoticz.Status("Check for Web update finished!")


def CheckVersion( file ) :
    version=""
    with open( file ) as f:
        first_line = f.readline()
        Domoticz.Log("firstline : " + str(first_line))
    version = first_line[first_line.find(":"),first_line.find(";")]
    Domoticz.Log(file + " version is : " + str(version))
    return int(version)

