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
import pickle

import Modules.tools
from Modules.logging import loggingDatabase

def _copyfile( source, dest, move=True ):

    try:
        import shutil
        if move:
            shutil.move( source, dest)
        else:
            shutil.copy( source, dest)
    except:
        with open(source, 'r') as src, open(dest, 'wt') as dst:
            for line in src:
                dst.write(line)


def _versionFile( source , nbversion ):

    if nbversion == 0:
        return

    if nbversion == 1:
        _copyfile( source, source +  "-%02d" %1 )
    else:
        for version in range ( nbversion - 1 , 0, -1 ):
            _fileversion_n =  source + "-%02d" %version
            if not os.path.isfile( _fileversion_n ):
                continue
            else:
                _fileversion_n1 =  source + "-%02d" %(version + 1)
                _copyfile( _fileversion_n, _fileversion_n1 )

        # Last one
        _copyfile( source, source +  "-%02d" %1 , move=False)


def LoadDeviceList( self ):
    # Load DeviceList.txt into ListOfDevices
    #

        # File exists, let's go one
    def loadTxtDatabase( self , dbName ):

        res = "Success"
        nb = 0
        with open( dbName , 'r') as myfile2:
            loggingDatabase( self, 'Debug',  "Open : " + dbName )
            for line in myfile2:
                if not line.strip() :
                    #Empty line
                    continue
                (key, val) = line.split(":",1)
                key = key.replace(" ","")
                key = key.replace("'","")

                #if key in  ( 'ffff', '0000'): continue
                if key in  ( 'ffff'): continue

                try:
                    dlVal=eval(val)
                except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                    Domoticz.Error("LoadDeviceList failed on %s" %val)
                    continue

                loggingDatabase( self, 'Debug', "LoadDeviceList - " +str(key) + " => dlVal " +str(dlVal) , key)

                if not dlVal.get('Version') :
                    if key == '0000': # Bug fixed in later version
                        continue
                    Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
                    res = "Failed"
                    continue

                if dlVal['Version'] != '3' :
                    Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
                    res = "Failed"
                    continue
                else:
                    nb = nb +1
                    CheckDeviceList( self, key, val )

        return res

    def loadJsonDatabase( self , dbName ):
        
        res = "Success"

        with open( dbName , 'rt') as handle:
            _listOfDevices = {}
            try:
                _listOfDevices = json.load( handle, encoding=dict)
            except json.decoder.JSONDecodeError as e:
                res = "Failed"
                Domoticz.Error("loadJsonDatabase poorly-formed %s, not JSON: %s" %(self.pluginConf['filename'],e))
        
        for key in _listOfDevices:
            CheckDeviceList( self, key, str(_listOfDevices[key]))

        return res


    # Let's check if we have a .json version. If so, we will be using it, otherwise
    # we fall back to the old fashion .txt
    jsonFormatDB = True
    
    if self.pluginconf.pluginConf['expJsonDatabase']:
        if os.path.isfile( self.pluginconf.pluginConf['pluginData'] + self.DeviceListName[:-3] + 'json' ):
            # JSON Format
            _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName[:-3] + 'json'
            jsonFormatDB = True
            res = loadJsonDatabase( self , _DeviceListFileName)

        elif os.path.isfile( self.pluginconf.pluginConf['pluginData'] + self.DeviceListName ):
            _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName
            jsonFormatDB = False
            res = loadTxtDatabase( self , _DeviceListFileName)
        else:
            # Do not exist 
            self.ListOfDevices = {}
            return True 
    else:
        if os.path.isfile( self.pluginconf.pluginConf['pluginData'] + self.DeviceListName ):
            _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName
            jsonFormatDB = False
            res = loadTxtDatabase( self , _DeviceListFileName)
        else:
            # Do not exist 
            self.ListOfDevices = {}
            return True 
      

    loggingDatabase( self, 'Debug', "LoadDeviceList - DeviceList filename : " + _DeviceListFileName )

    _versionFile( _DeviceListFileName , self.pluginconf.pluginConf['numDeviceListVersion'])

    # Keep the Size of the DeviceList in order to check changes
    self.DeviceListSize = os.path.getsize( _DeviceListFileName )

    for addr in self.ListOfDevices:
        # Check if 566 fixs are needed
        if self.pluginconf.pluginConf['Bug566']:
            if 'Model' in self.ListOfDevices[addr]:
               if self.ListOfDevices[addr]['Model'] == 'TRADFRI control outlet':
                   fixing_Issue566( self, addr )

        if self.pluginconf.pluginConf['resetReadAttributes']:
            loggingDatabase( self, "Log", "ReadAttributeReq - Reset ReadAttributes data %s" %addr)
            self.ListOfDevices[addr]['ReadAttributes'] = {}
            self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}
            for iterEp in self.ListOfDevices[addr]['Ep']:
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][iterEp] = {}
                self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'] = {}

        if self.pluginconf.pluginConf['resetConfigureReporting']:
            loggingDatabase( self, "Log", "Reset ConfigureReporting data %s" %addr)
            self.ListOfDevices[addr]['ConfigureReporting'] = {}
            self.ListOfDevices[addr]['ConfigureReporting']['Ep'] = {}
            for iterEp in self.ListOfDevices[addr]['Ep']:
                self.ListOfDevices[addr]['ConfigureReporting']['Ep'][iterEp] = {}
                self.ListOfDevices[addr]['ConfigureReporting']['TimeStamps'] = {}

    loggingDatabase( self, "Status", "Entries loaded from " +str(_DeviceListFileName)  )

    return res


def WriteDeviceList(self, count):

    if self.HBcount >= count :

        if self.pluginconf.pluginConf['pluginData'] is None or self.DeviceListName is None:
            Domoticz.Error("WriteDeviceList - self.pluginconf.pluginConf['pluginData']: %s , self.DeviceListName: %s" \
                %(self.pluginconf.pluginConf['pluginData'], self.DeviceListName))

        # Write in classic format ( .txt )
        try:
            _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName
            loggingDatabase( self, 'Debug', "Write " + _DeviceListFileName + " = " + str(self.ListOfDevices))
            with open( _DeviceListFileName , 'wt') as file:
                for key in self.ListOfDevices :
                    try:
                        file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
                    except IOError:
                        Domoticz.Error("Error while writing to plugin Database %s" %_DeviceListFileName)
        except IOError:
            Domoticz.Error("Error while Opening plugin Database %s" %_DeviceListFileName)

        # If enabled, write in JSON
        if self.pluginconf.pluginConf['expJsonDatabase']:
            _DeviceListFileName = self.pluginconf.pluginConf['pluginData'] + self.DeviceListName[:-3] + 'json'
            loggingDatabase( self, 'Debug', "Write " + _DeviceListFileName + " = " + str(self.ListOfDevices))
            with open( _DeviceListFileName , 'wt') as file:
                json.dump( self.ListOfDevices, file, sort_keys=True, indent=2)

        self.HBcount=0
        loggingDatabase( self, 'Debug', "WriteDeviceList - flush Plugin db to %s" %_DeviceListFileName)
    else :
        self.HBcount=self.HBcount+1

def importDeviceConf( self ) :
    #Import DeviceConf.txt
    tmpread=""
    self.DeviceConf = {}

    if os.path.isfile( self.pluginconf.pluginConf['pluginConfig']  + "DeviceConf.txt" ):
        with open( self.pluginconf.pluginConf['pluginConfig']  + "DeviceConf.txt", 'r') as myfile:
            tmpread+=myfile.read().replace('\n', '')
            try:
                self.DeviceConf=eval(tmpread)
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                Domoticz.Error("Error while loading %s in line : %s" %(self.pluginconf.pluginConf['pluginConfig']+"DeviceConf.txt", tmpread))
                return

    # Remove comments
    for iterDevType in list(self.DeviceConf):
        if iterDevType == '':
            del self.DeviceConf[iterDevType]
            
    #for iterDevType in list(self.DeviceConf):
    #    Domoticz.Log("%s - %s" %(iterDevType, self.DeviceConf[iterDevType]))

    loggingDatabase( self, "Status", "DeviceConf loaded")


def importDeviceConfV2( self ):

    from os import listdir
    from os.path import isfile, isdir, join

    # Read DeviceConf for backward compatibility
    importDeviceConf( self )

    model_certified = self.pluginconf.pluginConf['pluginConfig'] + 'Certified'

    if os.path.isdir( model_certified ):
        model_brand_list = [ f for f in listdir(model_certified) if isdir(join(model_certified, f))]
    
        for brand in model_brand_list:
            if brand in ( 'README.md', '.PRECIOUS' ):
                continue
    
            model_directory = model_certified + '/' + brand 

            model_list = [ f for f in listdir(model_directory) if isfile(join(model_directory, f))]
         
            for model_device in model_list:
                if model_device in ( 'README.md', '.PRECIOUS' ):
                    continue
     
                filename = str(model_directory + '/' + model_device)
                with open( filename, 'rt') as handle:
                    try:
                        model_definition = json.load( handle )
                    except ValueError as e: 
                        Domoticz.Error("--> JSON ConfFile: %s load failed with error: %s" %(str(filename), str(e)))
                        continue
                    except Exception as e:
                        Domoticz.Error("--> JSON ConfFile: %s load general error: %s" %(str(filename), str(e)))
                        continue

                try:
                    device_model_name = model_device.rsplit('.',1)[0]
    
                    if device_model_name not in self.DeviceConf:
                        loggingDatabase( self, "Debug", "--> Config for %s/%s" %( str(brand), str(device_model_name)))
                        self.DeviceConf[ device_model_name ] = dict(model_definition)
                    else:
                        loggingDatabase( self, "Debug", "--> Config for %s/%s not loaded as already defined" %(str(brand), str(device_model_name)))
                except:
                    Domoticz.Error("--> Unexpected error when loading a configuration file")

    loggingDatabase( self, 'Status', "--> Config loaded: %s" %self.DeviceConf.keys())

def checkDevices2LOD( self, Devices):

    for nwkid in self.ListOfDevices:
        self.ListOfDevices[nwkid]['ConsistencyCheck'] = ''
        if self.ListOfDevices[nwkid]['Status'] == 'inDB':
            for dev in Devices:
                if Devices[dev].DeviceID == self.ListOfDevices[nwkid]['IEEE']:
                    self.ListOfDevices[nwkid]['ConsistencyCheck'] = 'ok'
                    break
            else:
                self.ListOfDevices[nwkid]['ConsistencyCheck'] = 'not in DZ'


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
                    loggingDatabase( self, "Log", "checkListOfDevice2Devices - " +str(Devices[x].Name) + " - " +str(ID) + " not found in Plugin Database" )
                    continue
                else:
                    Domoticz.Error("checkListOfDevice2Devices - " +str(Devices[x].Name) + " - " +str(ID) + " not found in Plugin Database" )
                    loggingDatabase( self, 'Debug', "checkListOfDevice2Devices - " +str(ID) + " not found in " +str(self.IEEE2NWK) )
                    continue
    
            NWKID = self.IEEE2NWK[ID]
            if str(NWKID) in self.ListOfDevices :
                loggingDatabase( self, 'Debug', "checkListOfDevice2Devices - we found a matching entry for ID " +str(x) + " as DeviceID = " +str(ID) +" NWK_ID = " + str(NWKID) , NWKID)
            else :
                Domoticz.Error("loadListOfDevices -  : " +Devices[x].Name +" with IEEE = " +str(ID) +" not found in Zigate plugin Database!" )

def saveZigateNetworkData( self, nkwdata ):

        json_filename = self.pluginconf.pluginConf['pluginData'] + "Zigate.json" 
        loggingDatabase( self, 'Debug', "Write " + json_filename + " = " + str(self.ListOfDevices))
        try:
            with open (json_filename, 'wt') as json_file:
                json.dump(nkwdata, json_file, indent=4, sort_keys=True)
        except IOError:
            Domoticz.Error("Error while writing Zigate Network Details%s" %json_filename)


def CheckDeviceList(self, key, val) :
    '''
        This function is call during DeviceList load
    '''

    loggingDatabase( self, 'Debug', "CheckDeviceList - Address search : " + str(key), key)
    loggingDatabase( self, 'Debug', "CheckDeviceList - with value : " + str(val), key)

    DeviceListVal=eval(val)
    # Do not load Devices in State == 'unknown' or 'left' 
    if 'Status' in DeviceListVal:
        if DeviceListVal['Status'] in ( 'UNKNOW', 'failDB', 'DUP' ):
            loggingDatabase( self, 'Status', "Not Loading %s as Status: %s" %( key, DeviceListVal['Status']))
            return

    if Modules.tools.DeviceExist(self, key, DeviceListVal.get('IEEE','')):
        return
        
    if key == '0000':
        self.ListOfDevices[ key ] = {}
        self.ListOfDevices[ key ]['Status'] = ''
    else:
        Modules.tools.initDeviceInList(self, key)

    self.ListOfDevices[key]['RIA']="10"

    # List of Attribnutes that will be Loaded from the deviceList-xx.txt database
    ZIGATE_ATTRIBUTES = {
            'Version',
            'ZDeviceName',
            'Ep',
            'IEEE',
            'LogicalType',
            'PowerSource',
            'Neighbours',
            }

    MANDATORY_ATTRIBUTES = ( 'App Version', 
            'Attributes List', 
            'Bind', 
            'WebBind',
            'Capability'
            'ColorInfos', 
            'ClusterType', 
            'ConfigSource',
            'DeviceType', 
            'Ep', 
            'Epv2'
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
            'OTA',
            'PowerSource', 
            'ProfileID', 
            'ReceiveOnIdle', 
            'Stack Version', 
            'RIA', 
            'SWBUILD_1', 
            'SWBUILD_2', 
            'SWBUILD_3', 
            'Stack Version', 
            'Status', 
            'Type',
            'Version', 
            'ZCL Version', 
            'ZDeviceID', 
            'ZDeviceName')

    # List of Attributes whcih are going to be loaded, ut in case of Reset (resetPluginDS) they will be re-initialized.
    BUILD_ATTRIBUTES = (
            'Battery', 
            'ConfigureReporting',
            'Last Cmds',
            'Neighbours',
            'ReadAttributes', 
            'RSSI',
            'SQN', 
            'Stamp', 
            'Health')

    MANUFACTURER_ATTRIBUTES = (
            'Legrand', 'Schneider', 'Lumi' )

    if self.pluginconf.pluginConf['resetPluginDS']:
        loggingDatabase( self, 'Status', "Reset Build Attributes for %s" %DeviceListVal['IEEE'])
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES))

    elif key == '0000':
        # Reduce the number of Attributes loaded for Zigate
        loggingDatabase( self, 'Debug', "CheckDeviceList - Zigate (IEEE)  = %s Load Zigate Attributes" %DeviceListVal['IEEE'])
        IMPORT_ATTRIBUTES = list(set(ZIGATE_ATTRIBUTES))
        loggingDatabase( self, 'Debug', "--> Attributes loaded: %s" %IMPORT_ATTRIBUTES)
    else:
        loggingDatabase( self, 'Debug', "CheckDeviceList - DeviceID (IEEE)  = %s Load Full Attributes" %DeviceListVal['IEEE'])
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES + BUILD_ATTRIBUTES + MANUFACTURER_ATTRIBUTES))

    loggingDatabase( self, 'Debug', "--> Attributes loaded: %s" %IMPORT_ATTRIBUTES)
    for attribute in IMPORT_ATTRIBUTES:
        if attribute not in DeviceListVal:
            continue

        self.ListOfDevices[key][ attribute ] = DeviceListVal[ attribute]
        # Patching unitialize Model to empty
        if attribute == 'Model' and self.ListOfDevices[key][ attribute ] == {}:
            self.ListOfDevices[key][ attribute ] = ''
        # If Model has a '/', just strip it as we strip it from now
        if attribute == 'Model':
            OldModel = self.ListOfDevices[key][ attribute ]
            self.ListOfDevices[key][ attribute ] = self.ListOfDevices[key][ attribute ].replace('/', '')
            if OldModel != self.ListOfDevices[key][ attribute ]:
                Domoticz.Status("Model adjustement during import from %s to %s"
                    %(OldModel,self.ListOfDevices[key][ attribute ] ))

    self.ListOfDevices[key]['Health'] = ''

    if 'IEEE' in DeviceListVal:
        self.ListOfDevices[key]['IEEE'] = DeviceListVal['IEEE']
        loggingDatabase( self, 'Debug', "CheckDeviceList - DeviceID (IEEE)  = " + str(DeviceListVal['IEEE']) + " for NetworkID = " +str(key) , key)
        if  DeviceListVal['IEEE']:
            IEEE = DeviceListVal['IEEE']
            self.IEEE2NWK[IEEE] = key
        else :
            loggingDatabase( self, 'Debug', "CheckDeviceList - IEEE = " + str(DeviceListVal['IEEE']) + " for NWKID = " +str(key) , key )


def fixing_Issue566( self, key ):

    if 'Model' not in self.ListOfDevices[key]:
        return False
    if self.ListOfDevices[key]['Model'] != 'TRADFRI control outlet':
        return False

    if 'Cluster Revision' in self.ListOfDevices[key]['Ep']:
        Domoticz.Log("++++Issue #566: Fixing Cluster Revision for NwkId: %s" %key)
        del self.ListOfDevices[key]['Ep']['Cluster Revision']
        res = True

    for ep in self.ListOfDevices[key]['Ep']:
        if 'Cluster Revision' in self.ListOfDevices[key]['Ep'][ep]:
            Domoticz.Log("++++Issue #566 Cluster Revision NwkId: %s Ep: %s" %(key, ep))
            del self.ListOfDevices[key]['Ep'][ep]['Cluster Revision']
            res = True

    if '02' in self.ListOfDevices[key]['Ep'] and '01' in self.ListOfDevices[key]['Ep']:
        if 'ClusterType' in self.ListOfDevices[key]['Ep']['02']:
            if len(self.ListOfDevices[key]['Ep']['02']['ClusterType']) != 0:
                if 'ClusterType' in self.ListOfDevices[key]['Ep']['01']:
                    if len(self.ListOfDevices[key]['Ep']['01']['ClusterType']) == 0:
                        Domoticz.Log("++++Issue #566 ClusterType mixing NwkId: %s Ep 01 and 02" %key)
                        self.ListOfDevices[key]['Ep']['01']['ClusterType'] = dict(self.ListOfDevices[key]['Ep']['02']['ClusterType'])
                        self.ListOfDevices[key]['Ep']['02']['ClusterType'] = {}
                        res = True
    return True