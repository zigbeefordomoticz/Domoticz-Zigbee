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
import os


def _copyfileasB( source, dest ):
    copy_buffer =''
    with open(source, 'r+b') as src, open(dest, 'w+b') as dst:
        for line in src:
            dst.write(line)


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
        if len(l) >=3 :
            fileOld=DomoticzWWWFolder + "/zigate/" + l
            Domoticz.Log("Old file : " + fileOld)
            fileNew=self.homedirectory + "www/zigate/" + l
            Domoticz.Log("New file : " + fileNew)
            if not os.path.isdir(fileNew) :
                if os.path.isfile( fileOld ) :
                    if CheckVersion( fileNew ) >> CheckVersion( fileOld ) :
                        _copyfileasB( fileNew, fileOld)
                        Domoticz.Log("New file " + l + " is copied")
                else :
                    _copyfileasB( fileNew, fileOld)
                    Domoticz.Log("New file " + l + " is created")
    fileOld=DomoticzWWWFolder + "/zigate.html"
    fileNew=self.homedirectory + "www/zigate.html"
    if os.path.isfile( fileOld ):
        if CheckVersion( fileNew ) >> CheckVersion( fileOld ) :
            _copyfileasB( fileNew, fileOld)
            Domoticz.Log("New file zigate.html is copied")
    else :
        _copyfileasB( fileNew, fileOld)
        Domoticz.Log("New file zigate.html is created")
    Domoticz.Status("Check for Web update finished!")


def CheckVersion( file ) :
    Domoticz.Status("Reading " + file + "'s version")
    with open( file , 'rt', encoding='utf-8') as f :
        line = f.readline()
        Domoticz.Log("firstline : " + str(line))
    version = find_between(line, ":", ";")
    Domoticz.Log(file + " version is : " + str(version))
    return int(version)

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return "0"
