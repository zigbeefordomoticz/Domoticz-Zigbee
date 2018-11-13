#!/usr/bin/env python3
# coding: utf-8 -*-
"""
    Module: z_database.py

    Description: Function to access Zigate Plugin Database & Dictionary

"""

import Domoticz
import z_var
import z_tools
import os.path
import shutil
import datetime



def LoadDeviceList( self ):
    # Load DeviceList.txt into ListOfDevices
    #
    Domoticz.Debug("LoadDeviceList - DeviceList filename : " +self.DeviceListName )

    # Check if the DeviceList file exist.
    if not os.path.isfile( self.DeviceListName ) :
        self.ListOfDevices = {}
        return True    

    _backup =  self.DeviceListName + "_" + str(datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S'))
    shutil.copyfile( str(self.DeviceListName) , str(_backup) )

    # Keep the Size of the DeviceList in order to check changes
    self.DeviceListSize = os.path.getsize( self.DeviceListName )

    # File exists, let's go one
    res = "Success"
    nb = 0
    with open( self.DeviceListName , 'r') as myfile2:
        Domoticz.Debug( "Open : " + self.DeviceListName )
        for line in myfile2:
            if not line.strip() :
                #Empty line
                continue
            (key, val) = line.split(":",1)
            key = key.replace(" ","")
            key = key.replace("'","")

            dlVal=eval(val)
            Domoticz.Debug("LoadDeviceList - " +str(key) + " => dlVal " +str(dlVal) )

            if not dlVal.get('Version') :
                Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
                res = "Failed"

            if dlVal['Version'] != '3' :
                Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
                res = "Failed"
            else:
                nb = nb +1
                z_tools.CheckDeviceList( self, key, val )

    Domoticz.Status("Entries loaded from " +str(self.DeviceListName) + " : " +str(nb) )

    myfile2.close()
    return res


def WriteDeviceList(self, Folder, count):
    if self.HBcount>=count :
        Domoticz.Debug("Write " + self.DeviceListName + " = " + str(self.ListOfDevices))
        with open( self.DeviceListName , 'wt') as file:
            for key in self.ListOfDevices :
                file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
        self.HBcount=0
        file.close()
    else :
        Domoticz.Debug("HB count = " + str(self.HBcount))
        self.HBcount=self.HBcount+1


def importDeviceConf( self ) :
    #Import DeviceConf.txt
    tmpread=""
    with open( self.homedirectory + "DeviceConf.txt", 'r') as myfile:
        tmpread+=myfile.read().replace('\n', '')
    self.DeviceConf=eval(tmpread)
    myfile.close()


def importPluginConf( self ) :
    # Import PluginConf.txt
    tmpPluginConf=""
    with open(self.homedirectory+"PluginConf.txt", 'r') as myPluginConfFile:
        tmpPluginConf+=myPluginConfFile.read().replace('\n', '')
    myPluginConfFile.close()
    Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))
    self.PluginConf=eval(tmpPluginConf)

def checkListOfDevice2Devices( self, Devices ) :

    # As of V3 we will be loading only the IEEE information as that is the only one existing in Domoticz area.
    # It is also expected that the ListOfDevices is already loaded.

    # At that stage the ListOfDevices has beene initialized.
    for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
        ID = Devices[x].DeviceID
        if str(ID) not in self.IEEE2NWK :
            if self.ForceCreationDevice == 1 :
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


