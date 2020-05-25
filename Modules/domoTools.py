#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoTools.py
    Description: Tools to manage Domoticz widget inetractions
"""

import json
import time

import Domoticz

from Modules.logging import loggingWidget
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL
from Modules.widgets import SWITCH_LVL_MATRIX

def RetreiveWidgetTypeList( self, Devices, NwkId, DeviceUnit = None):
    """
    Return a list of tuple ( EndPoint, WidgetType, DeviceId)
    If DeviceUnit provides we have to return the WidgetType matching this Device Unit.

    """

    # Let's retreive All Widgets entries for the entire entry.
    ClusterTypeList = []
    if DeviceUnit:
        WidgetId = str(Devices[ DeviceUnit].ID)
        loggingWidget( self, 'Debug', "------> Looking for %s" %WidgetId, NwkId)

    if ( 'ClusterType' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['ClusterType'] != '' and self.ListOfDevices[NwkId]['ClusterType'] != {} ):
        # we are on the old fashion with Type at the global level like for the ( Xiaomi lumi.remote.n286acn01 )
        # In that case we don't need a match with the incoming Ep as the correct one is the Widget EndPoint
        loggingWidget( self, 'Debug', "------> OldFashion 'ClusterType': %s" %self.ListOfDevices[NwkId]['ClusterType'], NwkId)
        if DeviceUnit:
            if WidgetId in self.ListOfDevices[NwkId]['ClusterType']:
                WidgetType = self.ListOfDevices[NwkId]['ClusterType'][WidgetId]
                ClusterTypeList.append(  ( '00', WidgetId, WidgetType )  )
                return ClusterTypeList
        else:
            for WidgetId  in self.ListOfDevices[NwkId]['ClusterType']:
                WidgetType = self.ListOfDevices[NwkId]['ClusterType'][WidgetId]
                ClusterTypeList.append(  ( '00', WidgetId, WidgetType )  )

    for iterEp in self.ListOfDevices[NwkId]['Ep']:  
        if 'ClusterType' in self.ListOfDevices[NwkId]['Ep'][iterEp]:
            loggingWidget( self, 'Debug', "------> 'ClusterType': %s" %self.ListOfDevices[NwkId]['Ep'][iterEp]['ClusterType'], NwkId)
            if DeviceUnit:
                if WidgetId in self.ListOfDevices[NwkId]['Ep'][iterEp]['ClusterType']:
                    WidgetType = self.ListOfDevices[NwkId]['Ep'][iterEp]['ClusterType'][WidgetId] 
                    ClusterTypeList.append(  ( iterEp, WidgetId, WidgetType )  )
                    return ClusterTypeList
            else:
                for WidgetId  in self.ListOfDevices[NwkId]['Ep'][iterEp]['ClusterType']:
                    WidgetType = self.ListOfDevices[NwkId]['Ep'][iterEp]['ClusterType'][WidgetId]
                    ClusterTypeList.append(  ( iterEp, WidgetId, WidgetType )  )

    return ClusterTypeList

def RetreiveSignalLvlBattery( self, NwkID):
    
    
    # Takes the opportunity to update RSSI and Battery
    SignalLevel = '' 
    if 'RSSI' in self.ListOfDevices[NwkID]:
        SignalLevel = self.ListOfDevices[NwkID]['RSSI']

    # SignalLvl max is 12
    rssi = 12
    if isinstance(SignalLevel, int):
        rssi = round((SignalLevel * 12) / 255)
    
    BatteryLevel = ''
    if 'Battery' in self.ListOfDevices[NwkID] and self.ListOfDevices[NwkID]['Battery'] != {}:
        BatteryLevel = int(round((self.ListOfDevices[NwkID]['Battery'])))

    # Battery Level 255 means Main Powered device
    #if isinstance(BatteryLevel, float):
        # Looks like sometime we got a float instead of int.
        # in that case convert to int
    #    BatteryLvl = round( BatteryLevel)
    
    if BatteryLevel == '' or (not isinstance(BatteryLevel, int)):
        BatteryLevel = 255

    return (SignalLevel, BatteryLevel )

def WidgetForDeviceId( self, NwkId, DeviceId):
    
    WidgetType = ''
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if ( 'ClusterType' in self.ListOfDevices[NwkId]['Ep'][tmpEp] and str(DeviceId) in self.ListOfDevices[NwkId]['Ep'][tmpEp]['ClusterType'] ):
            WidgetType = self.ListOfDevices[NwkId]['Ep'][tmpEp]['ClusterType'][str(DeviceId)]

    if ( WidgetType == '' and 'ClusterType' in self.ListOfDevices[NwkId] and str(DeviceId) in self.ListOfDevices[NwkId]['ClusterType'] ):
        WidgetType = self.ListOfDevices[NwkId]['ClusterType'][str(DeviceId)]

    return WidgetType

def ResetDevice(self, Devices, ClusterType, HbCount):
    '''
        Reset all Devices from the ClusterType Motion after 30s
    '''

    for unit in Devices:
        if Devices[unit].nValue == 0 and Devices[unit].sValue == "Off":
            # Nothing to Reset
            continue

        LUpdate = Devices[unit].LastUpdate
        _tmpDeviceID_IEEE = Devices[unit].DeviceID
        if _tmpDeviceID_IEEE not in self.IEEE2NWK:
            # Unknown !
            continue

        try:
            LUpdate = time.mktime(time.strptime(LUpdate, "%Y-%m-%d %H:%M:%S"))
        except:
            Domoticz.Error("Something wrong to decode Domoticz LastUpdate %s" %LUpdate)
            break

        current = time.time()

        # Look for the corresponding Widget
        NWKID = self.IEEE2NWK[_tmpDeviceID_IEEE]

        if NWKID not in self.ListOfDevices:
            Domoticz.Error("ResetDevice " + str(NWKID) + " not found in " + str(self.ListOfDevices))
            continue

        ID = Devices[unit].ID
        WidgetType = ''        
        WidgetType = WidgetForDeviceId( self, NWKID, ID)

        if WidgetType not in ('Motion', 'Vibration'):
            continue

        if self.domoticzdb_DeviceStatus:
            from Classes.DomoticzDB import DomoticzDB_DeviceStatus

            # Let's check if we have a Device TimeOut specified by end user
            if self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion( Devices[unit].ID) > 0:
                continue

        SignalLevel, BatteryLvl = RetreiveSignalLvlBattery( self, NWKID)

        _timeout = self.pluginconf.pluginConf['resetMotiondelay']
        #resetMotionDelay = 0
        #if self.domoticzdb_DeviceStatus:
        #    from Classes.DomoticzDB import DomoticzDB_DeviceStatus
        #    resetMotionDelay = round(self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion( Devices[unit].ID),1)
        #if resetMotionDelay > 0:
        #    _timeout = resetMotionDelay

        if (current - LUpdate) >= _timeout: 
            loggingWidget( self, "Debug", "Last update of the devices " + str(unit) + " was : " + str(LUpdate) + " current is : " + str(
                current) + " this was : " + str(current - LUpdate) + " secondes ago", NWKID)
            UpdateDevice_v2(self, Devices, unit, 0, "Off", BatteryLvl, SignalLevel)

def UpdateDevice_v2(self, Devices, Unit, nValue, sValue, BatteryLvl, SignalLvl, Color_='', ForceUpdate_=False):

    loggingWidget( self, "Debug", "UpdateDevice_v2 %s:%s:%s   %3s:%3s:%5s (%15s)" %( nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID])

    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit not in Devices:
        return

    if (Devices[Unit].nValue != int(nValue)) or (Devices[Unit].sValue != sValue) or \
        ( Color_ !='' and Devices[Unit].Color != Color_) or \
        ForceUpdate_ or \
        Devices[Unit].BatteryLevel != int(BatteryLvl) or \
        Devices[Unit].TimedOut:

        if self.pluginconf.pluginConf['logDeviceUpdate']:
            Domoticz.Log("UpdateDevice - (%15s) %s:%s" %( Devices[Unit].Name, nValue, sValue ))
        loggingWidget( self, "Debug", "--->  [Unit: %s] %s:%s:%s %s:%s %s (%15s)" %( Unit, nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID])
        if Color_:
            Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_, SignalLevel=int(SignalLvl), BatteryLevel=int(BatteryLvl), TimedOut=0)
        else:
            Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue),               SignalLevel=int(SignalLvl), BatteryLevel=int(BatteryLvl), TimedOut=0)

def timedOutDevice( self, Devices, Unit=None, NwkId=None, MarkTimedOut=True):
 
    _Unit = _nValue = _sValue = None
    
    if Unit:
        _nValue = Devices[Unit].nValue
        _sValue = Devices[Unit].sValue
        _Unit = Unit
        if MarkTimedOut and not Devices[_Unit].TimedOut:
            Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=1)
        elif not MarkTimedOut and Devices[_Unit].TimedOut:
            Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=0)

    elif NwkId:
        if NwkId not in self.ListOfDevices:
            return
        if 'IEEE' not in self.ListOfDevices[NwkId]:
            return
        _IEEE = self.ListOfDevices[NwkId]['IEEE']
        self.ListOfDevices[NwkId]['Health'] = 'TimedOut' if MarkTimedOut else 'Live'
        for x in Devices:
            if Devices[x].DeviceID == _IEEE:
                _nValue = Devices[x].nValue
                _sValue = Devices[x].sValue
                _Unit = x
                if Devices[_Unit].TimedOut:
                    if MarkTimedOut:
                        continue
                    loggingWidget( self, 'Debug', 'reset timedOutDevice unit %s nwkid: %s ' % (Devices[_Unit].Name, NwkId), NwkId, )
                    Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=0)
                else:
                    if MarkTimedOut:
                        loggingWidget( self, 'Debug', 'timedOutDevice unit %s nwkid: %s ' % (Devices[_Unit].Name, NwkId), NwkId, )
                        Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=1)

def lastSeenUpdate( self, Devices, Unit=None, NwkId=None):

    # Purpose is here just to touch the device and update the Last Seen
    # It might required to call Touch everytime we receive a message from the device and not only when update is requested.

    if Unit:
        loggingWidget( self, "Debug", "Touch unit %s" %( Devices[Unit].Name ))
        if (not self.VersionNewFashion and (self.DomoticzMajor < 4 or ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10547))):
            loggingWidget( self, "Debug", "Not the good Domoticz level for lastSeenUpdate %s %s %s" 
                %(self.VersionNewFashion, self.DomoticzMajor, self.DomoticzMinor ), NwkId)
            return
        # Extract NwkId from Device Unit
        IEEE = Devices[Unit].DeviceID
        if Devices[Unit].TimedOut:
            timedOutDevice( self, Devices, Unit=Unit, MarkTimedOut=0)
        else:
            Devices[Unit].Touch()
        if NwkId is None and 'IEEE' in self.IEEE2NWK:
            NwkId = self.IEEE2NWK[ IEEE ]

    if NwkId:
        if NwkId not in self.ListOfDevices:
            return

        if 'IEEE' not in self.ListOfDevices[NwkId]:
            return

        if 'Stamp' not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['Stamp'] = {}
            self.ListOfDevices[NwkId]['Stamp']['Time'] = {}
            self.ListOfDevices[NwkId]['Stamp']['MsgType'] = {}
            self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = 0

        if 'LastSeen' not in self.ListOfDevices[NwkId]['Stamp']:
            self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = 0

        if 'ErrorManagement' in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['ErrorManagement'] = 0

        self.ListOfDevices[NwkId]['Health'] = 'Live'

        #if time.time() < self.ListOfDevices[NwkId]['Stamp']['LastSeen'] + 5*60:
        #    #loggingWidget( self, "Debug", "Too early for a new update of lastSeenUpdate %s" %NwkId, NwkId)
        #    return
        #loggingWidget( self, "Debug", "Update LastSeen for device %s" %NwkId, NwkId)

        self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = int(time.time())

        _IEEE = self.ListOfDevices[NwkId]['IEEE']
        if (not self.VersionNewFashion and (self.DomoticzMajor < 4 or ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10547))):
            loggingWidget( self, "Debug", "Not the good Domoticz level for Touch %s %s %s" %(self.VersionNewFashion, self.DomoticzMajor, self.DomoticzMinor ), NwkId)
            return
        for x in Devices:
            if Devices[x].DeviceID == _IEEE:
                loggingWidget( self, "Debug",  "Touch unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                if Devices[x].TimedOut:
                    timedOutDevice( self, Devices, Unit=x, MarkTimedOut=0)
                else:
                    Devices[x].Touch()

def GetType(self, Addr, Ep):
    Type = ""
    loggingWidget( self, "Debug", "GetType - Model " + str(self.ListOfDevices[Addr]['Model']) + " Profile ID : " + str(
        self.ListOfDevices[Addr]['ProfileID']) + " ZDeviceID : " + str(self.ListOfDevices[Addr]['ZDeviceID']), Addr)

    _Model = self.ListOfDevices[Addr]['Model']
    if _Model != {} and _Model in list(self.DeviceConf.keys()):
        # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
        if Ep in self.DeviceConf[ _Model ]['Ep']:
            Domoticz.Log( "Ep: %s found in DeviceConf" %Ep)
            if 'Type' in self.DeviceConf[ _Model ]['Ep'][Ep]:
                Domoticz.Log(" 'Type' entry found inf DeviceConf")
                if self.DeviceConf[ _Model ]['Ep'][Ep]['Type'] != "":
                    loggingWidget( self, "Debug", "GetType - Found Type in DeviceConf : %s" %self.DeviceConf[ _Model ]['Ep'][Ep]['Type'], Addr)
                    Type = self.DeviceConf[ _Model ]['Ep'][Ep]['Type']
                    Type = str(Type)
                else:
                    loggingWidget( self, 'Debug'"GetType - Found EpEmpty Type in DeviceConf for %s/%s" %(Addr, Ep), Addr)
            else:
                loggingWidget( self, 'Debug'"GetType - EpType not found in DeviceConf for %s/%s" %(Addr, Ep), Addr)   
        else:
            Type = self.DeviceConf[ _Model ]['Type']
            loggingWidget( self, "Debug", "GetType - Found Type in DeviceConf for %s/%s: %s " %(Addr, Ep, Type), Addr)            
    else:
        loggingWidget( self, "Debug", "GetType - Model:  >%s< not found with Ep: %s in DeviceConf. Continue with ClusterSearch" %( self.ListOfDevices[Addr]['Model'], Ep), Addr)
        loggingWidget( self, "Debug", "        - List of Entries: %s" %str(self.DeviceConf.keys() ), Addr)
        Type = ""

        # Check ProfileID/ZDeviceD
        if 'Manufacturer' in self.ListOfDevices[Addr]:
            if self.ListOfDevices[Addr]['Manufacturer'] == '117c': # Ikea
                if ( self.ListOfDevices[Addr]['ProfileID'] == 'c05e' and self.ListOfDevices[Addr]['ZDeviceID'] == '0830') :
                    return "Ikea_Round_5b"

                if self.ListOfDevices[Addr]['ProfileID'] == 'c05e' and self.ListOfDevices[Addr]['ZDeviceID'] == '0820':
                    return "Ikea_Round_OnOff"
                    
            elif self.ListOfDevices[Addr]['Manufacturer'] == '100b': # Philipps Hue
                pass
            elif str(self.ListOfDevices[Addr]['Manufacturer']).find('LIVOLO') != -1:
                loggingWidget( self, "Debug", "GetType - Found Livolo based on Manufacturer", Addr)
                return 'LivoloSWL/LivoloSWR'

        # Finaly Chec on Cluster
        for cluster in self.ListOfDevices[Addr]['Ep'][Ep]:
            if cluster in ('Type', 'ClusterType', 'ColorMode'): 
                continue

            loggingWidget( self, "Debug", "GetType - check Type for Cluster : " + str(cluster))

            if Type != "" and Type[:1] != "/":
                Type += "/"

            Type += TypeFromCluster(self, cluster, create_=True)
            loggingWidget( self, "Debug", "GetType - Type will be set to : " + str(Type))

        # Type+=Type
        # Ne serait-il pas plus simple de faire un .split( '/' ), puis un join ('/')
        # car j'ai un peu de problème sur cette serie de replace. 
        # ensuite j'ai vu également des Type avec un / à la fin !!!!!
        # Par exemple :  'Type': 'Switch/LvlControl/',
        Type = Type.replace("/////", "/")
        Type = Type.replace("////", "/")
        Type = Type.replace("///", "/")
        Type = Type.replace("//", "/")
        if Type[:-1] == "/":
            Type = Type[:-1]
        if Type[0:] == "/":
            Type = Type[1:]

        loggingWidget( self, "Debug", "GetType - ClusterSearch return : %s" %Type, Addr)

    loggingWidget(self, 'Debug', "GetType returning: %s" %Type, Addr)

    return Type

def TypeFromCluster( self, cluster, create_=False, ProfileID_='', ZDeviceID_=''):

    loggingWidget( self, "Debug", "---> ClusterSearch - Cluster: %s, ProfileID: %s, ZDeviceID: %s, create: %s" %(cluster, ProfileID_, ZDeviceID_, create_))

    TypeFromCluster = ''
    if ProfileID_ == 'c05e' and ZDeviceID_ == '0830':
        TypeFromCluster = 'Ikea_Round_5b'

    elif ProfileID_ == 'c05e' and ZDeviceID_ == '0820':
        TypeFromCluster = 'Ikea_Round_OnOff'

    elif cluster == "0001": 
        TypeFromCluster = "Voltage"

    elif cluster == "0006": 
        TypeFromCluster = "Switch"

    elif cluster == "0008": 
        TypeFromCluster = "LvlControl"

    elif cluster == "0009": 
        TypeFromCluster = "Alarm"

    elif cluster == "000c" and not create_: 
        TypeFromCluster = "XCube"

    elif cluster == "0012" and not create_: 
        TypeFromCluster = "XCube"

    elif cluster == "0101": 
        TypeFromCluster = "Vibration"

    elif cluster == "0102": 
        TypeFromCluster = "WindowCovering"

    elif cluster == "0201": 
        TypeFromCluster = "Temp/ThermoSetpoint/ThermoMode"

    elif cluster == "0300": 
        TypeFromCluster = "ColorControl"

    elif cluster == "0400": 
        TypeFromCluster = "Lux"

    elif cluster == "0402": 
        TypeFromCluster = "Temp"

    elif cluster == "0403": 
        TypeFromCluster = "Baro"

    elif cluster == "0405": 
        TypeFromCluster = "Humi"

    elif cluster == "0406": 
        TypeFromCluster = "Motion"

    elif cluster == "0702": 
        TypeFromCluster = "Power/Meter"

    elif cluster == "0500": 
        TypeFromCluster = "Door"

    elif cluster == "0502": 
        TypeFromCluster = "AlarmWD"

    elif cluster == "0b04": 
        TypeFromCluster = "Power/Meter"

    elif cluster == "fc00" : 
        TypeFromCluster = 'LvlControl'   # RWL01 - Hue remote

    # Propriatory cluster 0xfc21 Profalux PFX
    elif cluster == "fc21" : 
        TypeFromCluster = 'BSO-Orientation'

    # Propriatory Cluster. Plugin Cluster
    elif cluster == "rmt1": 
        TypeFromCluster = "Ikea_Round_5b"

    # Xiaomi Strenght for Vibration
    elif cluster == "Strenght": 
        TypeFromCluster = "Strenght"
    # Xiaomi Orientation for Vibration
    elif cluster == "Orientation": 
        TypeFromCluster = "Orientation"

    return TypeFromCluster

def subtypeRGB_FromProfile_Device_IDs( EndPoints, Model, ProfileID, ZDeviceID, ColorInfos=None):

    # Type 0xF1    pTypeColorSwitch
    # Switchtype 7 STYPE_Dimmer
    # SubType sTypeColor_RGB_W                0x01 // RGB + white, either RGB or white can be lit
    # SubType sTypeColor_White                0x03 // Monochrome white
    # SubType sTypeColor_RGB_CW_WW            0x04 // RGB + cold white + warm white, either RGB or white can be lit
    # SubType sTypeColor_LivCol               0x05
    # SubType sTypeColor_RGB_W_Z              0x06 // Like RGBW, but allows combining RGB and white
    # The test should be done in an other way ( ProfileID for instance )
    # default: SubType sTypeColor_RGB_CW_WW_Z 0x07 // Like RGBWW, # but allows combining RGB and white

    ColorControlRGB   = 0x02 # RGB color palette / Dimable
    ColorControlRGBWW = 0x04  # RGB + WW
    ColorControlFull  = 0x07  # 3 Color palettes widget
    ColorControlWW    = 0x08  # WW

    Subtype = None
    ZLL_Commissioning = False

    ColorMode = 0
    if ColorInfos:
        if 'ColorMode' in ColorInfos:
            ColorMode = ColorInfos['ColorMode']

    for iterEp in EndPoints:
        if '1000' in  iterEp:
            ZLL_Commissioning = True
            break

    # Device specifics section
    if Model:
        if Model == 'lumi.light.aqcn02':    # Aqara Bulb White Dim
            Subtype = ColorControlWW

    # Philipps Hue
    if Subtype is None and ProfileID == "a1e0": 
        if ZDeviceID == "0061":
            Subtype = ColorControlRGBWW

    # ZLL LightLink
    if Subtype is None and  ProfileID == 'c05e': 
        # We should Check that ZLL Commissioning is also there. Cluster 0x1000
        if ZDeviceID == '0100': # LED1622G12.Tradfri ou phillips hue white
            pass

        elif ZDeviceID == '0200': # ampoule Tradfri LED1624G9
            Subtype = ColorControlFull

        elif ZDeviceID == '0210': # 
            Subtype = ColorControlRGBWW

        elif ZDeviceID == '0220': # ampoule Tradfi LED1545G12.Tradfri
            Subtype = ColorControlWW

    # Home Automation / ZHA
    if Subtype is None and ProfileID == '0104': # Home Automation
        if ZLL_Commissioning and ZDeviceID == '0100': # Most likely IKEA Tradfri bulb LED1622G12
            Subtype = ColorControlWW

        elif ZDeviceID == '0101': # Dimable light
            pass

        elif ZDeviceID == '0102': # Color dimable light
            Subtype = ColorControlFull

        elif ZDeviceID == '010c': # White color temperature light
            Subtype = ColorControlWW

        elif ZDeviceID == '010d': # Extended color light
            # ZBT-ExtendedColor /  Müller-Licht 44062 "tint white + color" (LED E27 9,5W 806lm 1.800-6.500K RGB)
            Subtype = ColorControlRGBWW

    if Subtype is None and ColorInfos:
        if ColorMode == 2:
            Subtype = ColorControlWW

        elif ColorMode == 1:
            Subtype = ColorControlRGB

        else:
            Subtype = ColorControlFull

    if Subtype is None:
        Subtype = ColorControlFull

    return Subtype
