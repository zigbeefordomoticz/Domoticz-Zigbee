#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_database.py

    Description: Function to access Zigate Plugin Database & Dictionary

"""

import Domoticz
import os.path
import datetime
import json

from Modules.tools import CheckDeviceList

def _copyfile( source, dest ):
    copy_buffer =''
    with open(source, 'r') as src, open(dest, 'wt') as dst:
        for line in src:
            dst.write(line)


def LoadDeviceList( self ):
    # Load DeviceList.txt into ListOfDevices
    #
    Domoticz.Debug("LoadDeviceList - DeviceList filename : " +self.DeviceListName )

    _DeviceListFileName = self.pluginconf.pluginData + self.DeviceListName
    # Check if the DeviceList file exist.
    if not os.path.isfile( _DeviceListFileName ) :
        self.ListOfDevices = {}
        return True    

    _backup = _DeviceListFileName + "_" + str(datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S'))
    _copyfile( str(_DeviceListFileName) , str(_backup) )

    # Keep the Size of the DeviceList in order to check changes
    self.DeviceListSize = os.path.getsize( _DeviceListFileName )

    # File exists, let's go one
    res = "Success"
    nb = 0
    with open( _DeviceListFileName , 'r') as myfile2:
        Domoticz.Debug( "Open : " + _DeviceListFileName )
        for line in myfile2:
            if not line.strip() :
                #Empty line
                continue
            (key, val) = line.split(":",1)
            key = key.replace(" ","")
            key = key.replace("'","")

            if key in  ( 'ffff', '0000'): continue

            try:
                dlVal=eval(val)
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                Domoticz.Error("LoadDeviceList failed on %s" %val)
                continue

            Domoticz.Debug("LoadDeviceList - " +str(key) + " => dlVal " +str(dlVal) )

            if not dlVal.get('Version') :
                Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
                res = "Failed"

            if dlVal['Version'] != '3' :
                Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
                res = "Failed"
            else:
                nb = nb +1
                CheckDeviceList( self, key, val )

    for addr in self.ListOfDevices:
        if self.pluginconf.resetReadAttributes:
            Domoticz.Log("ReadAttributeReq - Reset ReadAttributes data %s" %addr)
            self.ListOfDevices[addr]['ReadAttributes'] = {}
            self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}
            for iterEp in self.ListOfDevices[addr]['Ep']:
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][iterEp] = {}
                self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'] = {}

        if self.pluginconf.resetConfigureReporting:
            Domoticz.Log("Reset ConfigureReporting data %s" %addr)
            self.ListOfDevices[addr]['ConfigureReporting'] = {}
            self.ListOfDevices[addr]['ConfigureReporting']['Ep'] = {}
            for iterEp in self.ListOfDevices[addr]['Ep']:
                self.ListOfDevices[addr]['ConfigureReporting']['Ep'][iterEp] = {}
                self.ListOfDevices[addr]['ConfigureReporting']['TimeStamps'] = {}

    Domoticz.Status("Entries loaded from " +str(_DeviceListFileName) + " : " +str(nb) )

    return res


def WriteDeviceList(self, count):

    if self.HBcount >= count :
        _DeviceListFileName = self.pluginconf.pluginData + self.DeviceListName
        Domoticz.Debug("Write " + _DeviceListFileName + " = " + str(self.ListOfDevices))
        with open( _DeviceListFileName , 'wt') as file:
            for key in self.ListOfDevices :
                file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
        self.HBcount=0

        # To be written in the Reporting folder
        json_filename = self.pluginconf.pluginReports + self.DeviceListName.replace('.txt','.json') 
        Domoticz.Debug("Write " + json_filename + " = " + str(self.ListOfDevices))
        with open (json_filename, 'wt') as json_file:
            json.dump(self.ListOfDevices, json_file, indent=4, sort_keys=True)
    else :
        self.HBcount=self.HBcount+1

def importDeviceConf( self ) :
    #Import DeviceConf.txt
    tmpread=""
    self.DeviceConf = {}
    with open( self.pluginconf.pluginConfig  + "DeviceConf.txt", 'r') as myfile:
        tmpread+=myfile.read().replace('\n', '')
        try:
            self.DeviceConf=eval(tmpread)
        except (SyntaxError, NameError, TypeError, ZeroDivisionError):
            Domoticz.Error("Error while loading %s in line : %s" %(self.pluginconf.pluginConfig, tmpread))
            return

    # Remove comments
    for iterDevType in list(self.DeviceConf):
        if iterDevType == '':
            del self.DeviceConf[iterDevType]
            
    #for iterDevType in list(self.DeviceConf):
    #    Domoticz.Log("%s - %s" %(iterDevType, self.DeviceConf[iterDevType]))

    Domoticz.Status("DeviceConf loaded")

def checkListOfDevice2Devices( self, Devices ) :

    # As of V3 we will be loading only the IEEE information as that is the only one existing in Domoticz area.
    # It is also expected that the ListOfDevices is already loaded.

    # At that stage the ListOfDevices has beene initialized.
    for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
        ID = Devices[x].DeviceID
        if (len(str(ID)) == 4 ):
            # This is a Group Id (short address)
            continue
        elif ID.find('Zigate-01-') != -1 or \
                ID.find('Zigate-02-') != -1 or \
                ID.find('Zigate-03-') != -1:
            continue # This is a Widget ID
        else:
            # Let's check if this is End Node
            if str(ID) not in self.IEEE2NWK :
                if self.pluginconf.allowForceCreationDomoDevice == 1 :
                    Domoticz.Log("checkListOfDevice2Devices - " +str(Devices[x].Name) + " - " +str(ID) + " not found in Plugin Database" )
                    continue
                else:
                    Domoticz.Error("checkListOfDevice2Devices - " +str(Devices[x].Name) + " - " +str(ID) + " not found in Plugin Database" )
                    Domoticz.Debug("checkListOfDevice2Devices - " +str(ID) + " not found in " +str(self.IEEE2NWK) )
                    continue
    
            NWKID = self.IEEE2NWK[ID]
            if str(NWKID) in self.ListOfDevices :
                Domoticz.Debug("checkListOfDevice2Devices - we found a matching entry for ID " +str(x) + " as DeviceID = " +str(ID) +" NWK_ID = " + str(NWKID) )
            else :
                Domoticz.Error("loadListOfDevices -  : " +Devices[x].Name +" with IEEE = " +str(ID) +" not found in Zigate plugin Database!" )

def saveZigateNetworkData( self, nkwdata ):

        json_filename = self.pluginconf.pluginData + "/Zigate.json" 
        Domoticz.Debug("Write " + json_filename + " = " + str(self.ListOfDevices))
        with open (json_filename, 'wt') as json_file:
            json.dump(nkwdata, json_file, indent=4, sort_keys=True)
