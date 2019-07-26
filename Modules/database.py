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

import Modules.tools

def _copyfile( source, dest ):
    copy_buffer =''
    with open(source, 'r') as src, open(dest, 'wt') as dst:
        for line in src:
            dst.write(line)

def _versionFile( source , nbversion ):

    if nbversion == 0:
        return
    elif nbversion == 1:
        _copyfile( source, source +  "-%02d" %1 )
    else:
        for version in range ( nbversion - 1 , 0, -1 ):
            _fileversion_n =  source + "-%02d" %version
            if not os.path.isfile( _fileversion_n ):
                continue
            else:
                _fileversion_n1 =  source + "-%02d" %(version + 1)
                _copyfile( _fileversion_n, _fileversion_n1 )

        _copyfile( source, source +  "-%02d" %1 )


def LoadDeviceList( self ):
    # Load DeviceList.txt into ListOfDevices
    #
    Modules.tools.loggingDatabase( self, 'Debug', "LoadDeviceList - DeviceList filename : " +self.DeviceListName )

    _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName
    # Check if the DeviceList file exist.
    if not os.path.isfile( _DeviceListFileName ) :
        self.ListOfDevices = {}
        return True    

    _versionFile( _DeviceListFileName , self.pluginconf.pluginConf['numDeviceListVersion'])

    # Keep the Size of the DeviceList in order to check changes
    self.DeviceListSize = os.path.getsize( _DeviceListFileName )

    # File exists, let's go one
    res = "Success"
    nb = 0
    with open( _DeviceListFileName , 'r') as myfile2:
        Modules.tools.loggingDatabase( self, 'Debug',  "Open : " + _DeviceListFileName )
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

            Modules.tools.loggingDatabase( self, 'Debug', "LoadDeviceList - " +str(key) + " => dlVal " +str(dlVal) , key)

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
        if self.pluginconf.pluginConf['resetReadAttributes']:
            Domoticz.Log("ReadAttributeReq - Reset ReadAttributes data %s" %addr)
            self.ListOfDevices[addr]['ReadAttributes'] = {}
            self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}
            for iterEp in self.ListOfDevices[addr]['Ep']:
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][iterEp] = {}
                self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'] = {}

        if self.pluginconf.pluginConf['resetConfigureReporting']:
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
        if self.pluginconf.pluginConf['pluginData'] is None or self.DeviceListName is None:
            Domoticz.Error("WriteDeviceList - self.pluginconf.pluginConf['pluginData']: %s , self.DeviceListName: %s" %(self.pluginconf.pluginConf['pluginData'], self.DeviceListName))
        _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName
        Modules.tools.loggingDatabase( self, 'Debug', "Write " + _DeviceListFileName + " = " + str(self.ListOfDevices))
        with open( _DeviceListFileName , 'wt') as file:
            for key in self.ListOfDevices :
                file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
        self.HBcount=0
        Modules.tools.loggingDatabase( self, 'Debug', "WriteDeviceList - flush Plugin db to %s" %_DeviceListFileName)
    else :
        self.HBcount=self.HBcount+1

def importDeviceConf( self ) :
    #Import DeviceConf.txt
    tmpread=""
    self.DeviceConf = {}
    with open( self.pluginconf.pluginConf['pluginConfig']  + "DeviceConf.txt", 'r') as myfile:
        tmpread+=myfile.read().replace('\n', '')
        try:
            self.DeviceConf=eval(tmpread)
        except (SyntaxError, NameError, TypeError, ZeroDivisionError):
            Domoticz.Error("Error while loading %s in line : %s" %(self.pluginconf.pluginConf['pluginConfig'], tmpread))
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
                if self.pluginconf.pluginConf['allowForceCreationDomoDevice'] == 1 :
                    Domoticz.Log("checkListOfDevice2Devices - " +str(Devices[x].Name) + " - " +str(ID) + " not found in Plugin Database" )
                    continue
                else:
                    Domoticz.Error("checkListOfDevice2Devices - " +str(Devices[x].Name) + " - " +str(ID) + " not found in Plugin Database" )
                    Modules.tools.loggingDatabase( self, 'Debug', "checkListOfDevice2Devices - " +str(ID) + " not found in " +str(self.IEEE2NWK) )
                    continue
    
            NWKID = self.IEEE2NWK[ID]
            if str(NWKID) in self.ListOfDevices :
                Modules.tools.loggingDatabase( self, 'Debug', "checkListOfDevice2Devices - we found a matching entry for ID " +str(x) + " as DeviceID = " +str(ID) +" NWK_ID = " + str(NWKID) , NWKID)
            else :
                Domoticz.Error("loadListOfDevices -  : " +Devices[x].Name +" with IEEE = " +str(ID) +" not found in Zigate plugin Database!" )

def saveZigateNetworkData( self, nkwdata ):

        json_filename = self.pluginconf.pluginConf['pluginData'] + "/Zigate.json" 
        Modules.tools.loggingDatabase( self, 'Debug', "Write " + json_filename + " = " + str(self.ListOfDevices))
        with open (json_filename, 'wt') as json_file:
            json.dump(nkwdata, json_file, indent=4, sort_keys=True)


def CheckDeviceList(self, key, val) :
    '''
        This function is call during DeviceList load
    '''

    Modules.tools.loggingDatabase( self, 'Debug', "CheckDeviceList - Address search : " + str(key), key)
    Modules.tools.loggingDatabase( self, 'Debug', "CheckDeviceList - with value : " + str(val), key)

    DeviceListVal=eval(val)
    # Do not load Devices in State == 'unknown' or 'left' 
    if 'Status' in DeviceListVal:
        if DeviceListVal['Status'] in ( 'UNKNOW', 'failDB', 'DUP' ):
            Domoticz.Status("Not Loading %s as Status: %s" %( key, DeviceListVal['Status']))
            return

    if Modules.tools.DeviceExist(self, key, DeviceListVal.get('IEEE','')) == False :
        Modules.tools.initDeviceInList(self, key)

        self.ListOfDevices[key]['RIA']="10"

        MANDATORY_ATTRIBUTES = ( 'App Version', 
                'Attributes List', 
                'Battery', 
                'Bind', 
                'ColorInfos', 
                'ClusterType', 
                'DeviceType', 
                'Ep', 
                'HW Version', 
                'Heartbeat', 
                'IAS',
                'Location', 
                'LogicalType', 
                'MacCapa', 
                'Manufacturer', 
                'Manufacturer Name', 
                'Model', 
                'NbEp',
                'PowerSource', 
                'ProfileID', 
                'ReceiveOnIdle', 
                'Stack Version', 
                'RIA', 
                'RSSI',
                'SQN', 
                'SWBUILD_1', 
                'SWBUILD_2', 
                'SWBUILD_3', 
                'Stack Version', 
                'Stamp', 
                'Status', 
                'Type',
                'Version', 
                'ZCL Version', 
                'ZDeviceID', 
                'ZDeviceName')

        BUILD_ATTRIBUTES = ('ConfigureReporting',
                'Last Cmds',
                'ReadAttributes', 
                'Stamp', 
                'Health')



        if not self.pluginconf.pluginConf['resetPluginDS']:
            Modules.tools.loggingDatabase( self, 'Debug', "CheckDeviceList - DeviceID (IEEE)  = %s Load Full Attributes" %DeviceListVal['IEEE'])
            IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES + BUILD_ATTRIBUTES))
        else:
            IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES))

        Modules.tools.loggingDatabase( self, 'Debug', "--> Attributes loaded: %s" %IMPORT_ATTRIBUTES)
        for attribute in IMPORT_ATTRIBUTES:
            if attribute in DeviceListVal:
                self.ListOfDevices[key][ attribute ] = DeviceListVal[ attribute]

        self.ListOfDevices[key]['Health'] = ''

        if 'IEEE' in DeviceListVal:
            self.ListOfDevices[key]['IEEE'] = DeviceListVal['IEEE']
            Modules.tools.loggingDatabase( self, 'Debug', "CheckDeviceList - DeviceID (IEEE)  = " + str(DeviceListVal['IEEE']) + " for NetworkID = " +str(key) , key)
            if  DeviceListVal['IEEE']:
                IEEE = DeviceListVal['IEEE']
                self.IEEE2NWK[IEEE] = key
            else :
                Modules.tools.loggingDatabase( self, 'Debug', "CheckDeviceList - IEEE = " + str(DeviceListVal['IEEE']) + " for NWKID = " +str(key) , key )

