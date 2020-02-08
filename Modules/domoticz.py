#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_domoticz.py
    Description: All interactions with Domoticz database
"""

import Domoticz
import binascii
import time
import struct
import json

from Modules.tools import loggingWidget
from Modules.output import schneider_EHZBRTS_thermoMode
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL

def CreateDomoDevice(self, Devices, NWKID):
    """
    CreateDomoDevice

    Create Domoticz Device accordingly to the Type.

    """

    def deviceName( self, NWKID, type_, IEEE_, EP_ ):
        """
        Return the Name of device to be created
        """

        _Model = _NickName = None
        devName = ''
        loggingWidget( self, "Debug", "deviceName - %s/%s - %s %s" %(NWKID, EP_, IEEE_, type_), NWKID)
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] != {}:
                _Model = self.ListOfDevices[NWKID]['Model']
                loggingWidget( self, "Debug", "deviceName - Model found: %s" %_Model, NWKID)
                if _Model in self.DeviceConf:
                    if 'NickName' in self.DeviceConf[_Model]:
                        _NickName = self.DeviceConf[_Model]['NickName']
                        loggingWidget( self, "Debug", "deviceName - NickName found %s" %_NickName, NWKID)

        if _NickName is None and _Model is None:
            _Model = ''
        elif _NickName:
            devName = _NickName + '_'
        elif _Model:
            devName = _Model+ '_'

        devName +=  type_ + "-" + IEEE_ + "-" + EP_
        loggingWidget( self, "Debug", "deviceName - Dev Name: %s" %devName, NWKID)

        return devName

    def getCreatedID(self, Devices, DeviceID, Name):
        """
        getCreateID
        Return DeviceID of the recently created device based  on its creation name.
        """
        # for x in Devices :
        #    if Devices[x].DeviceID == DeviceID and Devices[x].Name.find(Name) >= 0 :
        #        return Devices[x].ID
        return (Devices[x].ID for x in Devices if (Devices[x].DeviceID == DeviceID and Devices[x].Name.find(Name) >= 0))

    def FreeUnit(self, Devices, nbunit_=1):
        '''
        FreeUnit
        Look for a Free Unit number. If nbunit > 1 then we look for nbunit consecutive slots
        '''
        FreeUnit = ""
        for x in range(1, 255):
            if x not in Devices:
                if nbunit_ == 1:
                    return x
                nb = 1
                for y in range(x+1, 255):
                    if y not in Devices:
                        nb += 1
                    else: 
                        break
                    if nb == nbunit_: # We have found nbunit consecutive slots
                        loggingWidget( self, "Debug", "FreeUnit - device " + str(x) + " available")
                        return x

        else:
            loggingWidget( self, "Debug", "FreeUnit - device " + str(len(Devices) + 1))
            return len(Devices) + 1

    # Sanity check before starting the processing 
    if NWKID == '' or NWKID not in self.ListOfDevices:
        Domoticz.Error("CreateDomoDevice - Cannot create a Device without an IEEE or not in ListOfDevice .")
        return

    DeviceID_IEEE = self.ListOfDevices[NWKID]['IEEE']

    # When Type is at Global level, then we create all Type against the 1st EP
    # If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
    GlobalEP = False
    GlobalType = []
    for Ep in self.ListOfDevices[NWKID]['Ep']:
        dType = aType = Type = ''
        # Use 'type' at level EndPoint if existe
        loggingWidget( self, "Debug", "CreatDomoDevice - Process EP : " + str(Ep), NWKID)
        if not GlobalEP:  # First time, or we dont't GlobalType
            if 'Type' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                if self.ListOfDevices[NWKID]['Ep'][Ep]['Type'] != '':
                    dType = self.ListOfDevices[NWKID]['Ep'][Ep]['Type']
                    aType = str(dType)
                    Type = aType.split("/")
                    loggingWidget( self, "Debug", "CreateDomoDevice - Type via ListOfDevice: " + str(Type) + " Ep : " + str(Ep), NWKID)
                else:
                    Type = GetType(self, NWKID, Ep).split("/")
                    loggingWidget( self, "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID)

            else:
                if self.ListOfDevices[NWKID]['Type'] == {} or self.ListOfDevices[NWKID]['Type'] == '':
                    Type = GetType(self, NWKID, Ep).split("/")
                    loggingWidget( self, "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID)
                else:
                    GlobalEP = True
                    if 'Type' in self.ListOfDevices[NWKID]:
                        if self.ListOfDevices[NWKID]['Type'] != '':
                            Type = self.ListOfDevices[NWKID]['Type'].split("/")
                            loggingWidget( self, "Debug", "CreateDomoDevice - Type : '" + str(Type) + "'", NWKID)
        else:
            break  # We have created already the Devices (as GlobalEP is set)

        # Check if Type is known
        if Type == '':
            continue

        for iterType in Type:
            if iterType not in GlobalType and iterType != '': 
                loggingWidget( self, "Debug", "adding Type : %s to Global Type: %s" %(iterType, str(GlobalType)), NWKID)
                GlobalType.append(iterType)

        loggingWidget( self, "Debug", "CreateDomoDevice - Creating devices based on Type: %s" % Type, NWKID)

        if 'ClusterType' not in self.ListOfDevices[NWKID]['Ep'][Ep]:
            self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'] = {}

        if "Humi" in Type and "Temp" in Type and "Baro" in Type:
            t = "Temp+Hum+Baro"  # Detecteur temp + Hum + Baro
            unit = FreeUnit(self, Devices)
            loggingWidget( self, "Debug", "CreateDomoDevice - unit: %s" %unit, NWKID)
            myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                            Unit=unit, TypeName=t)
            myDev.Create()
            ID = myDev.ID
            if myDev.ID == -1 :
                self.ListOfDevices[NWKID]['Status'] = "failDB"
                Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
            else:
                self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

        if "Humi" in Type and "Temp" in Type:
            t = "Temp+Hum"
            unit = FreeUnit(self, Devices)
            myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                    Unit=unit, TypeName=t)
            myDev.Create()
            ID = myDev.ID
            if myDev.ID == -1 :
                self.ListOfDevices[NWKID]['Status'] = "failDB"
                Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
            else:
                self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

        if self.ListOfDevices[NWKID]['Model'] == {} or \
                self.ListOfDevices[NWKID][ 'Model'] not in self.DeviceConf:    # If Model is known, then Type must be set correctly
            if ("Switch" in Type) and ("LvlControl" in Type):
                Type = ['LvlControl']
                if 'ColorControl' in Type or 'ColorControlRGB' in Type or 'ColorControlWW' in Type or 'ColorControlRGBWW' in Type or \
                        'ColorControlFull' in Type or  'ColorControl' in Type :
                    Type = ['ColorControl']

        for t in Type:
            loggingWidget( self, "Debug", "CreateDomoDevice - DevId: %s DevEp: %s Type: %s" %(DeviceID_IEEE, Ep, t), NWKID)

            if t == "ThermoModeEHZBRTS":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                Options = {"LevelActions": "||||||", "LevelNames": "Off| Manual| Schedule| Manual Energy Saver| Schedule Energy Saver| Holiday| Holiday Frost Protection",
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep),
                           Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "ThermoSetpoint":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=242, Subtype=1)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "ThermoMode":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                Options = {"LevelActions": "|||", "LevelNames": "Off|Auto|Cool|Heat|Force Heat",
                           "LevelOffHidden": "false", "SelectorStyle": "0"}
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep),
                           Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "HACTMODE":
                    self.ListOfDevices[NWKID]['Status'] = "inDB"
                    unit = FreeUnit(self, Devices)
                    Options = {"LevelActions": "||", "LevelNames": "Off|Conventional|Fil Pilote",
                            "LevelOffHidden": "true", "SelectorStyle": "0"}
                    myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep),
                            Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                    myDev.Create()
                    ID = myDev.ID
                    if myDev.ID == -1 :
                        self.ListOfDevices[NWKID]['Status'] = "failDB"
                        Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                    else:
                        self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "FIP":
                    loggingWidget( self, "Debug", "==> hactFIPMode enabled,create FIP widget", NWKID)
                    self.ListOfDevices[NWKID]['Status'] = "inDB"
                    unit = FreeUnit(self, Devices)
                    Options = {"LevelActions": "||||||", "LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off",
                            "LevelOffHidden": "true", "SelectorStyle": "0"}
                    myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep),
                            Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                    myDev.Create()
                    ID = myDev.ID
                    if myDev.ID == -1 :
                        self.ListOfDevices[NWKID]['Status'] = "failDB"
                        Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                    else:
                        self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "LegrandFilPilote":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                Options = {"LevelActions": "||||||", "LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Hors Gel|Off",
                           "LevelOffHidden": "true", "SelectorStyle": "0"}
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep),
                           Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t


            if t == "Temp":  # Detecteur temp
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, TypeName="Temperature")
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Humi":  # Detecteur hum
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, TypeName="Humidity")
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Baro":  # Detecteur Baro
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, TypeName="Barometer")
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "AlarmWD": # IAS object / matching 0x0502 Cluster / Alarm/Siren
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||||", "LevelNames": "Stop|Alarm|Siren|Strobe|Armed|Disarmed",
                           "LevelOffHidden": "false", "SelectorStyle": "0"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t
                
            if t == "Door":  # capteur ouverture/fermeture xiaomi
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=11)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Motion":  # detecteur de presence
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=8)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t in ( "LivoloSWL", "LivoloSWR" ):
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=0)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == 'Generic_5_buttons':
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||", "LevelNames": "button1|button2|button3|button4|button5",
                            "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == 'GenericLvlControl':
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||", "LevelNames": "Off|Off|On|Move Up|Move Down|Stop",
                            "LevelOffHidden": "true", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == 'LegrandSelector':
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||", "LevelNames": "Off|On|Move Up|Move Down|Stop",
                            "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "SwitchAQ2":  # interrupteur multi lvl lumi.sensor_switch.aq2
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                if self.ListOfDevices[NWKID]['Model'] == 'lumi.sensor_switch':
                    Options = {"LevelActions": "|||", "LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks",
                            "LevelOffHidden": "false", "SelectorStyle": "1"}
                else:
                    Options = {"LevelActions": "|||", "LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks",
                            "LevelOffHidden": "false", "SelectorStyle": "0"}

                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "SwitchAQ3":  # interrupteur multi lvl lumi.sensor_switch.aq2
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||", "LevelNames": "Click|Double Click|Long Click|Release Click|Shake",
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t



            if t == "DSwitch":  # interrupteur double sur EP different
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click",
                           "LevelOffHidden": "true", "SelectorStyle": "0"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "DButton":  # interrupteur double sur EP different lumi.sensor_86sw2
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||", "LevelNames": "Off|Switch 1|Switch 2|Both_Click",
                           "LevelOffHidden": "true", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "DButton_3":  # interrupteur double sur EP different lumi.sensor_86sw2
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||||||||", "LevelNames": "Off|Left Click|Left Double Clink|Left Long Click|Right Click|Right Double Click|Right Long Click|Both Click|Both Double Click|Both Long Click",
                           "LevelOffHidden": "true", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Smoke":  # detecteur de fumee
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=5)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Lux":  # Lux sensors
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=246, Subtype=1, Switchtype=0)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Toggle": # Switch selector provding On, Off and Toggle
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                Options = {"LevelActions": "||", "LevelNames": "Off|On|Toggle",
                           "LevelOffHidden": "false", "SelectorStyle": "0"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Switch":  # inter sans fils 1 touche 86sw1 xiaomi
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=0)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Button":  # inter sans fils 1 touche 86sw1 xiaomi
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=9)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Button_3":  # inter sans fils 1 touche 86sw1 xiaomi 3 States 
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||", "LevelNames": "Off|Click|Double Click|Long Click", \
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep),
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Aqara" or t == "XCube":  # Xiaomi Magic Cube
                self.ListOfDevices[NWKID]['Status'] = "inDB"

                # Create the XCube Widget
                Options = {"LevelActions": "||||||||||",
                           "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
                           "LevelOffHidden": "true", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices, nbunit_=2) # Look for 2 consecutive slots
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t
                
                # Create the Status (Text) Widget to report Rotation angle
                unit += 1
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=243, Subtype=19, Switchtype=0)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = 'Text'

            if t == "Vibration":  # Aqara Vibration Sensor v1
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||", "LevelNames": "Off|Tilt|Vibrate|Free Fall", \
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Strength":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=243, Subtype=31)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Orientation":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=243, Subtype=19)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t


            if t == "Water":  # detecteur d'eau
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=0, Image=11)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Plug":  # prise pilote
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=73, Switchtype=0, Image=1)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t in ( "VenetianInverted", "Venetian"):
                loggingWidget( self, "Debug", "Create Widget %s Blind EU" %t, NWKID)
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                    Unit=unit, Type=244, Subtype=73, Switchtype=15)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t


            if t == "WindowCovering":
                # Subtype = 
                # Blind / Window covering
                #   13 Blind percentage
                #   16 Blind Percentage Inverted
                # Shade
                #   14 Venetian Blinds US
                #   15 Venetian Blind EU
                loggingWidget( self, "Debug", "Create Widget WindowCovering" , NWKID)
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                if self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0202':
                    loggingWidget( self, "Debug", "---> Blind based on ZDeviceID" , NWKID)
                    # Window covering
                    myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                        Unit=unit, Type=244, Subtype=73, Switchtype=16)
                elif self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0200':
                    # Shade
                    loggingWidget( self, "Debug", "---> Shade based on ZDeviceID" , NWKID)
                    myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                        Unit=unit, Type=244, Subtype=73, Switchtype=15)
                else:
                    myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                        Unit=unit, Type=244, Subtype=73, Switchtype=7)

                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "LvlControl":
                loggingWidget( self, "Debug", "Create Widget LvlControl" , NWKID)
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)

                if self.ListOfDevices[NWKID]['Model'] != '' and self.ListOfDevices[NWKID]['Model'] != {} :  
                    loggingWidget( self, "Debug", "---> Shade based on ZDeviceID" , NWKID)
                    # Well Identified Model
                    # variateur de luminosite + On/off
                    myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                    Unit=unit, Type=244, Subtype=73, Switchtype=7)
                else:
                    if self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0202':
                        # Windows Covering / Profalux -> Inverted 
                        loggingWidget( self, "Debug", "---> Blind Inverted based on ZDeviceID" , NWKID)
                        myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                            Unit=unit, Type=244, Subtype=73, Switchtype=16)
                    elif self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0200':
                        # Shade
                        loggingWidget( self, "Debug", "---> Shade based on ZDeviceID" , NWKID)
                        myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                            Unit=unit, Type=244, Subtype=73, Switchtype=15)
                    else:
                        # variateur de luminosite + On/off
                        myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                            Unit=unit, Type=244, Subtype=73, Switchtype=7)

                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 
                      'ColorControlFull', 'ColorControl'):  # variateur de couleur/luminosite/on-off
                self.ListOfDevices[NWKID]['Status'] = "inDB"

                if t == 'ColorControlRGB': 
                    Subtype_ = 0x02 # RGB color palette / Dimable
                elif t == 'ColorControlRGBWW': 
                    Subtype_ = 0x04  # RGB + WW / Dimable
                elif t == 'ColorControlFull': 
                    Subtype_ = 0x07  # 3 Color palettes widget
                elif t == 'ColorControlWW': 
                    Subtype_ = 0x08  # White color palette / Dimable
                else:
                    # Generic ColorControl, let's try to find a better one.
                    if 'ColorInfos' in self.ListOfDevices[NWKID]:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs( self.ListOfDevices[NWKID]['Ep'], self.ListOfDevices[NWKID]['Model'],
                            self.ListOfDevices[NWKID]['ProfileID'], self.ListOfDevices[NWKID]['ZDeviceID'], self.ListOfDevices[NWKID]['ColorInfos'])
                    else:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs( self.ListOfDevices[NWKID]['Ep'], self.ListOfDevices[NWKID]['Model'],
                            self.ListOfDevices[NWKID]['ProfileID'], self.ListOfDevices[NWKID]['ZDeviceID'], None)

                    if Subtype_ == 0x02:
                        t = 'ColorControlRGB'
                    elif Subtype_ == 0x04:
                        t = 'ColorControlRGBWW'
                    elif Subtype_ == 0x07:
                        t = 'ColorControlFull'
                    elif Subtype_ == 0x08:
                        t = 'ColorControlWW'
                    else:
                        t = 'ColorControlFull'

                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=241, Subtype=Subtype_, Switchtype=7)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "P1Meter":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                # P1 Smart Meter Energy Type 250, Subtype = 250
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=250, Subtype=1, Switchtype=1)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            # Ajout meter
            if t == "Power":  # Will display Watt real time
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, TypeName="Usage")
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Meter":  # Will display kWh 
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, TypeName="kWh")
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Voltage":  
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, TypeName="Voltage")
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == 'INNR_RC110_SCENE': # INNR Remote Control
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||||||||||", "LevelNames": "Off|On|click_up|click_down|move_up|move_down|stop|scene1|scene2|scene3|scene4|scene5|scene6", \
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, 'SCENES', DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == 'INNR_RC110_LIGHT': # INNR Remote Control
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||||", "LevelNames": "Off|On|click_up|click_down|move_up|move_down|stop", \
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, 'LIGHTS', DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "SwitchIKEA":
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "||||", "LevelNames": "Off|On|Push Up|Push Down|Release", \
                           "LevelOffHidden": "false", "SelectorStyle": "1"}

                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t

            if t == "Ikea_Round_5b": # IKEA Remote 5 buttons round one.
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                Options = {"LevelActions": "|||||||||||||", "LevelNames": "Off|ToggleOnOff|Left_click|Right_click|Up_click|Up_push|Up_release|Down_click|Down_push|Down_release|Right_push|Right_release|Left_push|Left_release", \
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                unit = FreeUnit(self, Devices)
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t


    # for Ep
    loggingWidget( self, "Debug", "GlobalType: %s" %(str(GlobalType)), NWKID)
    if len(GlobalType) != 0:
        self.ListOfDevices[NWKID]['Type'] = ''
        for iterType in GlobalType:
            if self.ListOfDevices[NWKID]['Type'] == '':
                self.ListOfDevices[NWKID]['Type'] = iterType 
            else:
                self.ListOfDevices[NWKID]['Type'] = self.ListOfDevices[NWKID]['Type'] + '/' + iterType 
        loggingWidget( self, "Debug", "CreatDomoDevice - Set Type to : %s" %self.ListOfDevices[NWKID]['Type'], NWKID)

def MajDomoDevice(self, Devices, NWKID, Ep, clusterID, value, Attribute_='', Color_=''):
    '''
    MajDomoDevice
    Update domoticz device accordingly to Type found in EP and value/Color provided
    '''

    if NWKID not in self.ListOfDevices:
        Domoticz.Error("MajDomoDevice - %s not known" %NWKID)
        return
    if 'IEEE' not in self.ListOfDevices[NWKID]:
        Domoticz.Error("MajDomoDevice - no IEEE for %s" %NWKID)
        return

    DeviceID_IEEE = self.ListOfDevices[NWKID]['IEEE']
    loggingWidget( self, "Debug", 
        "MajDomoDevice - Device ID : " + str(DeviceID_IEEE) + " - Device EP : " + str(Ep) + " - Type : " + str(
            clusterID) + " - Value : " + str(value) + " - Hue : " + str(Color_) + "  - Attribute_ : " +str(Attribute_), NWKID)

    ClusterType = TypeFromCluster(self, clusterID)
    loggingWidget( self, "Debug", "MajDomoDevice - Type = " + str(ClusterType), NWKID)

    x = 0
    for x in Devices:
        if Devices[x].DeviceID == DeviceID_IEEE:
            loggingWidget( self, "Debug", "MajDomoDevice - NWKID = " + str(NWKID) + " IEEE = " + str(DeviceID_IEEE) + " Unit = " + str(Devices[x].ID), NWKID)

            ID = Devices[x].ID
            DeviceType = ""
            loggingWidget( self, "Debug", "MajDomoDevice - " + str(self.ListOfDevices[NWKID]['Ep'][Ep]), NWKID)


            newFashon = True
            if 'ClusterType' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['ClusterType'] != {}:
                    # We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
                    if str(ID) not in self.ListOfDevices[NWKID]['ClusterType']:
                        Domoticz.Error("MajDomoDevice - inconsistency on ClusterType. Id: %s not found in %s" \
                                %( str(ID), str(self.ListOfDevices[NWKID]['ClusterType'])))
                        return
                    loggingWidget( self, "Debug", "MajDomoDevice - search ClusterType in : " + str(
                        self.ListOfDevices[NWKID]['ClusterType']) + " for : " + str(ID), NWKID)
                    DeviceType = self.ListOfDevices[NWKID]['ClusterType'][str(ID)]
                    newFashon = False
            if newFashon:
                # Are we in a situation with one Devices whatever Eps are ?
                # To do that, check there is only 1 ClusterType even if several EPs
                nbClusterType = 0
                ptEP = Ep
                for tmpEp in self.ListOfDevices[NWKID]['Ep']:
                    if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                        nbClusterType = nbClusterType + 1
                        ptEP_single = tmpEp

                loggingWidget( self, "Debug", "MajDomoDevice - We have " + str(nbClusterType) + " EPs with ClusterType", NWKID)

                if nbClusterType == 1:  # All Updates are redirected to the same EP
                    # We must redirect all to the EP where there is a ClusterType
                    # ptEP_single is be the Only  EP where we have found ClusterType
                    for key in self.ListOfDevices[NWKID]['Ep'][ptEP_single]['ClusterType']:
                        if str(ID) == str(key):
                            DeviceType = str(self.ListOfDevices[NWKID]['Ep'][ptEP_single]['ClusterType'][key])

                else:
                    ptEp_multi = Ep
                    loggingWidget( self, "Debug", "MajDomoDevice - search ClusterType in : " + str(
                        self.ListOfDevices[NWKID]['Ep'][ptEp_multi]) + " for : " + str(ID), NWKID)
                    if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][ptEp_multi]:
                        loggingWidget( self, "Debug", "MajDomoDevice - search ClusterType in : " + str(
                            self.ListOfDevices[NWKID]['Ep'][ptEp_multi]['ClusterType']) + " for : " + str(ID), NWKID)
                        for key in self.ListOfDevices[NWKID]['Ep'][ptEp_multi]['ClusterType']:
                            if str(ID) == str(key):
                                DeviceType = str(self.ListOfDevices[NWKID]['Ep'][ptEp_multi]['ClusterType'][key])
                    else:
                        loggingWidget( self, "Debug", "MajDomoDevice - receive an update on an Ep which doesn't have any ClusterType !", NWKID)
                        loggingWidget( self, "Debug", "MajDomoDevice - Network Id : " + NWKID + " Ep : " + str(
                            ptEp_multi) + " Expected Cluster is " + str(clusterID), NWKID)
                        continue
            if DeviceType == "":  # No match with ClusterType
                continue

            loggingWidget( self, "Debug", "MajDomoDevice - NWKID: %s SwitchType: %s, DeviceType: %s, ClusterType: %s, old_nVal: %s , old_sVal: %s" \
                         % (NWKID, Devices[x].SwitchType, DeviceType, ClusterType, Devices[x].nValue, Devices[x].sValue), NWKID)

            if self.ListOfDevices[NWKID]['RSSI'] != 0:
                SignalLevel = self.ListOfDevices[NWKID]['RSSI']
            else:
                SignalLevel = 15
            if self.ListOfDevices[NWKID]['Battery'] != '':
                BatteryLevel = self.ListOfDevices[NWKID]['Battery']
            else:
                BatteryLevel = 255

            if ('Power' in ClusterType and DeviceType == 'P1Meter' and Attribute_ == '0000'):
                conso = 0
                if '0702' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                    if '0400' in self.ListOfDevices[NWKID]['Ep'][Ep]['0702']:
                        conso = round(float(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0400']),2)

                summation = round(float(value),2)
                sValue = "%s;%s;%s;%s;%s;%s" %(summation,0,0,0,conso,0)
                loggingWidget( self, "Debug", "MajDomoDevice P1Meter : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, x, 0, str(sValue), BatteryLevel, SignalLevel)

            # Instant Watts. 
            # PowerMeter is for Compatibility , as it was created as a PowerMeter device.
            # if ( DeviceType=="Power" or DeviceType=="PowerMeter") and clusterID == "000c":
            if ('Power' in ClusterType and DeviceType == "Power" and Attribute_== '') or \
                    (clusterID == "000c" and DeviceType == "Power"):  # kWh
                nValue = round(float(value),2)
                sValue = value
                loggingWidget( self, "Debug", "MajDomoDevice Power : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, x, nValue, str(sValue), BatteryLevel, SignalLevel)

            # Meter Usage. EnergyMode 0 from Device, 1 from Compute
            if 'Meter' in ClusterType and \
                    (DeviceType == "Meter" and Attribute_== '') or \
                    (clusterID == "000c" and DeviceType == "Power"):  # kWh

                summation = 0
                if '0702' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                    if '0000' in self.ListOfDevices[NWKID]['Ep'][Ep]['0702']:
                        if self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != {} and self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != '' and \
                                self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != '0':
                            summation = int(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'])

                Options = {}
                if 'EnergyMeterMode' in Devices[ x ].Options:
                    Options = Devices[ x ].Options
                else:
                    Options['EnergyMeterMode'] = '0' # By default from device

                if summation:
                    # Make sure we are set as from Device
                    if Options['EnergyMeterMode'] != '0':
                        oldnValue = Devices[ x ].nValue
                        oldsValue = Devices[ x ].sValue
                        Options = {}
                        Options['EnergyMeterMode']='0'
                        Devices[ x ].Update( oldnValue, oldsValue, Options=Options )
                else:
                    # Report summation as Conso
                    #summation = value

                    # Make sure we are set as Compute
                    if Options['EnergyMeterMode'] != '1':
                        oldnValue = Devices[ x ].nValue
                        oldsValue = Devices[ x ].sValue
                        Options = {}
                        Options['EnergyMeterMode']='1'
                        Devices[ x ].Update( oldnValue, oldsValue, Options=Options )

                nValue = round(float(value),2)
                summation = round(float(summation),2)
                sValue = "%s;%s" % (nValue, summation)
                loggingWidget( self, "Debug", "MajDomoDevice Meter : " + sValue)

                UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)

            if ClusterType == DeviceType == "Voltage":  # Volts
                nValue = round(float(value),2)
                sValue = "%s;%s" % (nValue, nValue)
                loggingWidget( self, "Debug", "MajDomoDevice Voltage : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)

            if 'ThermoSetpoint' in ClusterType and DeviceType == 'ThermoSetpoint' and Attribute_ in ( '4003', '0012'):

                nValue = round(float(value),2)
                sValue = "%s;%s" % (nValue, nValue)

                loggingWidget( self, "Debug", "MajDomoDevice Thermostat Setpoint: %s %s" %(nValue,sValue), NWKID)
                UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)

            if 'ThermoMode' in ClusterType and DeviceType == 'ThermoMode' and Attribute_ == '001c':
                loggingWidget( self, "Debug", "MajDomoDevice Thermostat Mode %s" %value, NWKID)
                if isinstance( value, str):
                    nValue = int(value,16)
                else:
                    nValue = value
                if nValue in THERMOSTAT_MODE_2_LEVEL:
                    sValue = THERMOSTAT_MODE_2_LEVEL[nValue]
                    UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)
                    loggingWidget( self, "Debug", "MajDomoDevice Thermostat Mode: %s %s" %(nValue,sValue), NWKID)

            if 'ThermoMode' in ClusterType and DeviceType == 'ThermoModeEHZBRTS' and Attribute_ == '001c':
                loggingWidget( self, "Debug", "MajDomoDevice EHZBRTS Schneider Thermostat Mode %s" %value, NWKID)
                # Decode value

                THERMOSTAT_MODE = {
                        0:0,
                        1:10,
                        2:20,
                        3:30,
                        4:40,
                        5:50,
                        6:60
                        }

                if value in THERMOSTAT_MODE:
                    value = THERMOSTAT_MODE[ value ]
                schneider_EHZBRTS_thermoMode( self, NWKID, value)

            if ClusterType == "Temp":  # temperature
                loggingWidget( self, "Debug", "MajDomoDevice Temp: %s, DeviceType: >%s<" %(value,DeviceType), NWKID)
                adjvalue = 0
                if self.domoticzdb_DeviceStatus:
                    from Classes.DomoticzDB import DomoticzDB_DeviceStatus
                    adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_temp( Devices[x].ID),1)
                loggingWidget( self, "Debug", "Adj Value : %s from: %s to %s " %(adjvalue, value, (value+adjvalue)), NWKID)
                CurrentnValue = Devices[x].nValue
                CurrentsValue = Devices[x].sValue
                if CurrentsValue == '':
                    # First time after device creation
                    CurrentsValue = "0;0;0;0;0"
                SplitData = CurrentsValue.split(";")
                NewNvalue = 0
                NewSvalue = ''
                if DeviceType == "Temp":
                    NewNvalue = round(value + adjvalue,1)
                    NewSvalue = str(round(value + adjvalue,1))
                    loggingWidget( self, "Debug", "MajDomoDevice Temp update: %s - %s" %(NewNvalue, NewSvalue))
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

                elif DeviceType == "Temp+Hum":
                    NewNvalue = 0
                    NewSvalue = '%s;%s;%s' %(round(value + adjvalue,1), SplitData[1], SplitData[2])
                    loggingWidget( self, "Debug", "MajDomoDevice Temp+Hum update: %s - %s" %(NewNvalue, NewSvalue))
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

                elif DeviceType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                    NewNvalue = 0
                    NewSvalue = '%s;%s;%s;%s;%s' %(round(value + adjvalue,1), SplitData[1], SplitData[2], SplitData[3], SplitData[4])
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

            if ClusterType == "Humi":  # humidite
                loggingWidget( self, "Debug", "MajDomoDevice Humi: %s, DeviceType: >%s<" %(value,DeviceType), NWKID)
                CurrentnValue = Devices[x].nValue
                CurrentsValue = Devices[x].sValue
                if CurrentsValue == '':
                    # First time after device creation
                    CurrentsValue = "0;0;0;0;0"
                SplitData = CurrentsValue.split(";")
                NewNvalue = 0
                NewSvalue = ''
                # Humidity Status
                if value < 40:
                    humiStatus = 2
                elif 40 <= value < 70:
                    humiStatus = 1
                else:
                    humiStatus = 3

                if DeviceType == "Humi":
                    NewNvalue = value
                    NewSvalue = "%s" %humiStatus
                    loggingWidget( self, "Debug", "MajDomoDevice Humi update: %s - %s" %(NewNvalue, NewSvalue))
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

                elif DeviceType == "Temp+Hum":  # temp+hum xiaomi
                    NewNvalue = 0
                    NewSvalue = '%s;%s;%s' % (SplitData[0], value, humiStatus)
                    loggingWidget( self, "Debug", "MajDomoDevice Temp+Hum update: %s - %s" %(NewNvalue, NewSvalue))
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

                elif DeviceType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                    NewNvalue = 0
                    NewSvalue = '%s;%s;%s;%s;%s' % (SplitData[0], value, humiStatus, SplitData[3], SplitData[4])
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

            if ClusterType == "Baro":  # barometre
                loggingWidget( self, "Debug", "MajDomoDevice Baro: %s, DeviceType: %s" %(value,DeviceType), NWKID)
                adjvalue = 0
                if self.domoticzdb_DeviceStatus:
                    from Classes.DomoticzDB import DomoticzDB_DeviceStatus
                    adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_baro( Devices[x].ID),1)
                baroValue = round( (value + adjvalue), 1)
                loggingWidget( self, "Debug", "Adj Value : %s from: %s to %s " %(adjvalue, value, baroValue), NWKID)

                CurrentnValue = Devices[x].nValue
                CurrentsValue = Devices[x].sValue
                if CurrentsValue == '':
                    # First time after device creation
                    CurrentsValue = "0;0;0;0;0"
                SplitData = CurrentsValue.split(";")
                NewNvalue = 0
                NewSvalue = ''

                if baroValue < 1000:
                    Bar_forecast = 4 # RAIN
                elif baroValue < 1020:
                    Bar_forecast = 3 # CLOUDY
                elif baroValue < 1030:
                    Bar_forecast = 2 # PARTLY CLOUDY
                else:
                    Bar_forecast = 1 # SUNNY

                if DeviceType == "Baro":
                    NewSvalue = '%s;%s' %(baroValue, Bar_forecast)
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

                elif DeviceType == "Temp+Hum+Baro":
                    NewSvalue = '%s;%s;%s;%s;%s' % (SplitData[0], SplitData[1], SplitData[2], baroValue, Bar_forecast)
                    UpdateDevice_v2(self, Devices, x, NewNvalue, str(NewSvalue), BatteryLevel, SignalLevel)

            if ClusterType == "Orientation" and DeviceType == "Orientation":
                UpdateDevice_v2(self, Devices, x, 0, str(value), BatteryLevel, SignalLevel)

            if ClusterType == "Strenght" and DeviceType == "Strength":
                UpdateDevice_v2(self, Devices, x, 0, str(value), BatteryLevel, SignalLevel)

            if ClusterType == "Door":
                if DeviceType == "Door":  # Door / Window
                    value = int(value)
                    if value == 1:
                        state = "Open"
                        UpdateDevice_v2(self, Devices, x, value, str(state), BatteryLevel, SignalLevel)
                    elif value == 0:
                        state = "Closed"
                        UpdateDevice_v2(self, Devices, x, value, str(state), BatteryLevel, SignalLevel)

                elif DeviceType == "Smoke":  # detecteur de fume
                    state = ''
                    if value == "01":
                        state = "On"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                    elif value == "00":
                        state = "Off"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)

                elif DeviceType == "Water":  # detecteur d eau
                    state = ''
                    if value == "01":
                        state = "On"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                    elif value == "00":
                        state = "Off"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)

            if ClusterType == "Switch":
                if DeviceType == "Plug":
                    if value == "01":
                        UpdateDevice_v2(self, Devices, x, 1, "On", BatteryLevel, SignalLevel)
                    elif value == "00":
                        UpdateDevice_v2(self, Devices, x, 0, "Off", BatteryLevel, SignalLevel)
                elif DeviceType == "Door":  # porte / fenetre
                    if value == "01":
                        state = "Open"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                    elif value == "00":
                        state = "Closed"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                elif DeviceType == "Switch":  # Switch
                    state = ''
                    if value == "01":
                        state = "On"
                    elif value == "00":
                        state = "Off"
                    UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                elif DeviceType == "Button":  # boutton simple
                    state = ''
                    if int(value) == 1:
                        state = "On"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel,
                                        ForceUpdate_=True)
                elif DeviceType == "Button_3":  # boutton simple 3 states
                    state = ''
                    if int(value) == 1:
                        state = '10'
                    elif int(value) == 2:
                        state = '20'
                    elif int(value) == 3:
                        state = '30'
                    else:
                        value = 0
                        state = '00'
                    UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel,
                                    ForceUpdate_=True)
                elif DeviceType == "Water":  # detecteur d eau
                    state = ''
                    if value == "01":
                        state = "On"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                    elif value == "00":
                        state = "Off"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)

                elif DeviceType == "Smoke":  # detecteur de fume
                    state = ''
                    if value == "01":
                        state = "On"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)
                    elif value == "00":
                        state = "Off"
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)

                elif DeviceType == "LivoloSWL":
                    value = int(value)
                    state = None
                    if value == 0: # Off Left/Single
                        state = 'Off'
                    elif value == 1: # On Left/Single
                        state = 'On'
                    if state is not None:
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)

                elif DeviceType == 'LivolSWR':
                    value = int(value)
                    state = None
                    if value == 2: # Off Right
                        state = 'Off'
                    elif value == 3: # On Right
                        state = 'On'
                    if state is not None:
                        UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel)

                elif DeviceType == "SwitchIKEA":  # On/Off switch
                    nvalue = int(value)
                    svalue = '%02s' %( nvalue * 10 )
                    UpdateDevice_v2(self, Devices, x, nvalue, svalue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == 'Generic_5_buttons':
                    loggingWidget( self, "Debug", "Generic 5 buttons : Value -> %s" %value, NWKID)
                    nvalue = 0
                    state = '00'
                    if value == '00': nvalue = 0; state = '00'
                    elif value == '01': nvalue = 1; state = '10'
                    elif value == '02': nvalue = 2; state = '20'
                    elif value == '03': nvalue = 3; state = '30'
                    elif value == '04': nvalue = 4; state = '40'
                    UpdateDevice_v2(self, Devices, x, nvalue, str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == 'LegrandSelector':
                    loggingWidget( self, "Debug", "LegrandSelector : Value -> %s" %value, NWKID)
                    if value == '00': nvalue = 0 ; state = '00' #Off
                    elif value == '01': nvalue = 1 ; state = "10" # On
                    elif value == 'moveup': nvalue = 2 ; state = "20" # Move Up
                    elif value == 'movedown': nvalue = 3 ; state = "30" # Move Down
                    elif value == 'stop': nvalue = 4 ; state = "40" # Stop
                    UpdateDevice_v2(self, Devices, x, nvalue, str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == 'GenericLvlControl':
                    # 1,10: Off
                    # 2,20: On
                    # 3,30: Move Up
                    # 4,40: Move Down
                    # 5,50: Stop
                    loggingWidget( self, "Debug", "GenericLvlControl : Value -> %s" %value, NWKID)
                    if value == '00': nvalue = 1 ; state = '10' #Off
                    elif value == '01': nvalue = 2 ; state = "20" # On
                    elif value == 'moveup': nvalue = 3 ; state = "30" # Move Up
                    elif value == 'movedown': nvalue = 3 ; state = "40" # Move Down
                    elif value == 'stop': nvalue = 5 ; state = "50" # Stop
                    UpdateDevice_v2(self, Devices, x, nvalue, str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == "SwitchAQ2":  # multi lvl switch
                    value = int(value)
                    loggingWidget( self, "Debug", "SwitchAQ2 : Value -> %s" %value, NWKID)
                    if value == 1: state = "00"
                    elif value == 2: state = "10"
                    elif value == 3: state = "20"
                    elif value == 4: state = "30"
                    elif value == 80: state = "30"
                    elif value == 255: state = "30"
                    else:
                        return  # Simply return and don't process any other values than the above
                    value = int(state)/10 
                    UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == "SwitchAQ3":  # Xiaomi Aqara Smart Wireless Switch Key Built In Gyro Multi-Functional 
                    value = int(value)
                    if value == 1: state = "00"
                    elif value == 2: state = "10"
                    elif value == 16: state = "20"
                    elif value == 17: state = "30"
                    elif value == 18: state = "40"
                    else:
                        return  # Simply return and don't process any other values than the above
                    value = int(state)/10 
                    UpdateDevice_v2(self, Devices, x, int(value), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == "DSwitch":
                    # double switch avec EP different 
                    value = int(value)
                    if Ep == "01":
                        if value == 1 or value == 0:
                            state = "10"
                            data = "01"
                            UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel)
                    elif Ep == "02":
                        if value == 1 or value == 0:
                            state = "20"
                            data = "02"
                            UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel)
                    elif Ep == "03":
                        if value == 1 or value == 0:
                            state = "30"
                            data = "03"
                            UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel)

                elif DeviceType == "DButton":
                    # double bouttons avec EP different lumi.sensor_86sw2 
                    value = int(value)
                    if Ep == "01":
                        if value == 1: state = "10"; data = "01"; UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)
                    elif Ep == "02":
                        if value == 1:
                            state = "20"; data = "02"; UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)
                    elif Ep == "03":
                        if value == 1:
                            state = "30"; data = "03"; UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == "DButton_3":
                    # double bouttons avec EP different lumi.sensor_86sw2 
                    value = int(value)
                    data = '00'
                    state = '00'
                    if Ep == "01":
                        if value == 1: state = "10"; data = "01"
                        elif value == 2: state = "20"; data = "02"
                        elif value == 3: state = "30"; data = "03"
                        UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel,
                                            ForceUpdate_=True)
                    elif Ep == "02":
                        if value == 1: state = "40"; data = "04"
                        elif value == 2: state = "50"; data = "05"
                        elif value == 3: state = "60"; data = "06"
                        UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel,
                                            ForceUpdate_=True)
                    elif Ep == "03":
                        if value == 1: state = "70"; data = "07"
                        elif value == 2: state = "80"; data = "08"
                        elif value == 3: state = "90"; data = "09"
                        UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel,
                                            ForceUpdate_=True)

                elif DeviceType == "LvlControl" or DeviceType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                    if Devices[x].SwitchType in (13,14,15,16):
                        if value == "00":
                            UpdateDevice_v2(self, Devices, x, 0, '0', BatteryLevel, SignalLevel)
                        else:
                            # We are in the case of a Shutter/Blind inverse. If we receieve a Read Attribute telling it is On, great
                            # We only update if the shutter was off before, otherwise we will keep its Level.
                            if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                                UpdateDevice_v2(self, Devices, x, 1, '100', BatteryLevel, SignalLevel)
                    else:
                        if value == "00":
                            UpdateDevice_v2(self, Devices, x, 0, 'Off', BatteryLevel, SignalLevel)
                        else:
                            if Devices[x].sValue == "Off":
                                # We do update only if this is a On/off
                                UpdateDevice_v2(self, Devices, x, 1, 'On', BatteryLevel, SignalLevel)

                elif DeviceType == "INNR_RC110_SCENE":
                    loggingWidget( self, "Debug", "MajDomoDevice - Updating INNR_RC110_SCENE (Switch) Value: %s" %value, NWKID)
                    if value == '01': nValue = 1 ; sValue= "10"
                    elif value == '00': nValue = 0; sValue = "00"
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

                elif DeviceType == 'INNR_RC110_LIGHT':
                    loggingWidget( self, "Debug", "MajDomoDevice - Updating INNR_RC110_LIGHT (Switch) Value: %s" %value, NWKID)
                    if value == '01': nValue = 1 ; sValue= "10"
                    elif value == '00': nValue = 0; sValue = "00"
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

            if ClusterType == 'WindowCovering':
                value = int(value,16)
                if DeviceType in ( 'VenetianInverted', 'Venetian', 'WindowCovering'):
                    loggingWidget( self, "Debug", "MajDomoDevice - %s/%s Updating %s Value: %s" %(NWKID, Ep, DeviceType,value), NWKID)
                    if DeviceType == "VenetianInverted":
                        value = 100 - value
                        loggingWidget( self, "Debug", "--------------- - Patching %s/%s Value: %s" %(NWKID, Ep,value), NWKID)

                    if value == 0: nValue = 0
                    elif value == 100: nValue = 1
                    else: nValue = 2
                    UpdateDevice_v2(self, Devices, x, nValue, str(value), BatteryLevel, SignalLevel)

            if ClusterType == "LvlControl":
                if DeviceType == "LvlControl":
                    # We need to handle the case, where we get an update from a Read Attribute or a Reporting message
                    # We might get a Level, but the device is still Off and we shouldn't make it On .
                    nValue = None

                    # Normalize sValue vs. analog value coomming from a ReadATtribute
                    analogValue = int(value, 16)

                    loggingWidget( self, "Debug", "--> LvlControl analogValue: -> %s" %analogValue, NWKID)
                    if analogValue >= 255:
                        sValue = 100
                    else:
                        sValue = round( ((int(value, 16) * 100) / 255))
                        if sValue > 100: 
                            sValue = 100
                        if sValue == 0 and analogValue > 0:
                            sValue = 1
                        # Looks like in the case of the Profalux shutter, we never get 0 or 100
                        if Devices[x].SwitchType in (13,14,15,16):
                            if sValue == 1 and analogValue == 1:
                                sValue = 0
                            if sValue == 99 and analogValue == 254:
                                sValue = 100

                    loggingWidget( self, "Debug", "----> LvlControl sValue: -> %s" %sValue, NWKID)

                    # In case we reach 0% or 100% we shouldn't switch Off or On, except in the case of Shutter/Blind
                    if sValue == 0:
                        nValue = 0
                        if Devices[x].SwitchType in (13,14,15,16):
                            loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(0,0, Devices[x].SwitchType), NWKID)
                            UpdateDevice_v2(self, Devices, x, 0, '0', BatteryLevel, SignalLevel)
                        else:
                            if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                                pass
                            else:
                                #UpdateDevice_v2(Devices, x, 0, 'Off', BatteryLevel, SignalLevel)
                                loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s" %(0,0), NWKID)
                                UpdateDevice_v2(self, Devices, x, 0, '0', BatteryLevel, SignalLevel)

                    elif sValue == 100:
                        nValue = 1
                        if Devices[x].SwitchType in (13,14,15,16):
                            loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(1,100, Devices[x].SwitchType), NWKID)
                            UpdateDevice_v2(self, Devices, x, 1, '100', BatteryLevel, SignalLevel)
                        else:
                            if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                                pass
                            else:
                                #UpdateDevice_v2(Devices, x, 1, 'On', BatteryLevel, SignalLevel)
                                loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s" %(1,100), NWKID)
                                UpdateDevice_v2(self, Devices, x, 1, '100', BatteryLevel, SignalLevel)
                    else: # sValue != 0 and sValue != 100
                        if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                            # Do nothing. We receive a ReadAttribute  giving the position of a Off device.
                            pass
                        elif Devices[x].SwitchType in (13,14,15,16):
                            nValue = 2
                            loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(nValue,sValue, Devices[x].SwitchType), NWKID)
                            UpdateDevice_v2(self, Devices, x, str(nValue), str(sValue), BatteryLevel, SignalLevel)
                        else:
                            nValue = 1
                            loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(nValue,sValue, Devices[x].SwitchType), NWKID)
                            UpdateDevice_v2(self, Devices, x, str(nValue), str(sValue), BatteryLevel, SignalLevel)

                elif DeviceType  in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                    if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                        pass
                    else:
                        nValue = 1
                        analogValue = int(value, 16)
                        if analogValue >= 255:
                            sValue = 100
                        else:
                            sValue = round(((int(value, 16) * 100) / 255))
                            if sValue > 100: sValue = 100
                            if sValue == 0 and analogValue > 0:
                                sValue = 1
                        UpdateDevice_v2(self, Devices, x, str(nValue), str(sValue), BatteryLevel, SignalLevel, Color_)

                elif DeviceType == 'LegrandSelector':
                    loggingWidget( self, "Debug", "LegrandSelector : Value -> %s" %value, NWKID)
                    if value == '00': nvalue = 0 ; state = '00' #Off
                    elif value == '01': nvalue = 1 ; state = "10" # On
                    elif value == 'moveup': nvalue = 2 ; state = "20" # Move Up
                    elif value == 'movedown': nvalue = 3 ; state = "30" # Move Down
                    elif value == 'stop': nvalue = 4 ; state = "40" # Stop
                    else:
                        Domoticz.Error("MajDomoDevice - %s LegrandSelector Unknown value %s" %(NWKID, value))
                        return
                    UpdateDevice_v2(self, Devices, x, nvalue, str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == 'Generic_5_buttons':
                    loggingWidget( self, "Debug", "Generic 5 buttons : Value -> %s" %value, NWKID)
                    nvalue = 0
                    state = '00'
                    if value == '00': nvalue = 0; state = '00'
                    elif value == '01': nvalue = 1; state = '10'
                    elif value == '02': nvalue = 2; state = '20'
                    elif value == '03': nvalue = 3; state = '30'
                    elif value == '04': nvalue = 4; state = '40'
                    UpdateDevice_v2(self, Devices, x, nvalue, str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif DeviceType == "INNR_RC110_SCENE":
                    loggingWidget( self, "Debug", "MajDomoDevice - Updating INNR_RC110_SCENE (LvlControl) Value: %s" %value, NWKID)
                    if value == "Off": nValue = 0
                    elif value == "On": nValue = 1
                    elif value == "clickup": nValue = 2
                    elif value == "clickdown": nValue = 3
                    elif value == "moveup": nValue = 4
                    elif value == "movedown": nValue = 5
                    elif value == "stop":   nValue = 6
                    elif value == "scene1": nValue = 7
                    elif value == "scene2": nValue = 8
                    elif value == "scene3": nValue = 9
                    elif value == "scene4": nValue = 10
                    elif value == "scene5": nValue = 11
                    elif value == "scene6": nValue = 12
                    sValue = "%s" %(10 * nValue)
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

                elif DeviceType == 'INNR_RC110_LIGHT':
                    loggingWidget( self, "Debug", "MajDomoDevice - Updating INNR_RC110_LIGHT (LvlControl) Value: %s" %value, NWKID)
                    if value == "00": nValue = 0
                    elif value == "01": nValue = 1
                    elif value == "clickup": nValue = 2
                    elif value == "clickdown": nValue = 3
                    elif value == "moveup": nValue = 4
                    elif value == "movedown": nValue = 5
                    elif value == "stop":   nValue = 6
                    sValue = "%s" %(10 * nValue)
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

            if ClusterType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl') and  \
                    ClusterType == DeviceType:
                nValue = 1

                analogValue = int(value, 16)
                if analogValue >= 255:
                    sValue = 100
                else:
                    sValue = round(((int(value, 16) * 100) / 255))
                    if sValue > 100: sValue = 100
                    if sValue == 0 and analogValue > 0:
                        sValue = 1

                UpdateDevice_v2(self, Devices, x, str(nValue), str(sValue), BatteryLevel, SignalLevel, Color_)

            if ClusterType == "XCube" and DeviceType == "Aqara" and Ep == "02":  # Magic Cube Acara
                loggingWidget( self, "Debug", "MajDomoDevice - XCube update device with data = " + str(value), NWKID)
                UpdateDevice_v2(self, Devices, x, int(value), str(value), BatteryLevel, SignalLevel, ForceUpdate_ = True)

            if ClusterType == "XCube" and DeviceType == "Aqara" and Ep == "03":  # Magic Cube Acara Rotation
                if Attribute_ == '0055': # Rotation Angle
                    # Update Text widget ( unit + 1 )
                    UpdateDevice_v2(self, Devices, x + 1, 0 , value, BatteryLevel, SignalLevel, ForceUpdate_ = True)

                else:
                    state = value
                    data = value
                    if value == "80":
                        data = 8
                    elif value == "90":
                        data = 9
                    loggingWidget( self, "Debug", "MajDomoDevice - XCube update device with data = %s , nValue: %s sValue: %s" %(value, data, state), NWKID)
                    UpdateDevice_v2(self, Devices, x, int(value), str(value), BatteryLevel, SignalLevel, ForceUpdate_ = True)

            if ClusterType == DeviceType == "XCube" and Ep == "02":  # cube xiaomi
                if value == "0000":  # shake
                    state = "10"
                    data = "01"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value in ( "0204", "0200", "0203", "0201", "0202", "0205" ):
                    state = "50"
                    data = "05"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value in ( "0103", "0100", "0104", "0101", "0102", "0105"): # Slide/M%ove
                    state = "20"
                    data = "02"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value == "0003":  # Free Fall
                    state = "70"
                    data = "07"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif "0004" <= value <= "0059":  # 90°
                    state = "30"
                    data = "03"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value >= "0060":  # 180°
                    state = "90"
                    data = "09"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

            if ClusterType == DeviceType == "Vibration":
                    if value =="00":
                        data = 0
                        state = "00"
                    elif value == "10":
                        data = 1
                        state = "10"
                    elif value == "20":
                        data = 2
                        state = "20"
                    elif value == "30":
                        data = 3
                        state = "30"
                    else:
                        data = 0
                        state = "00"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

            if ClusterType == DeviceType == "Lux":
                UpdateDevice_v2(self, Devices, x, int(value), str(value), BatteryLevel, SignalLevel)

            if ClusterType == DeviceType == "Motion":
                if value == '01':
                    UpdateDevice_v2(self, Devices, x, 1, str("On"), BatteryLevel, SignalLevel, ForceUpdate_=True)
                if value == '00':
                    UpdateDevice_v2(self, Devices, x, 0, str("Off"), BatteryLevel, SignalLevel)

            if ClusterType == DeviceType == "Ikea_Round_OnOff": # IKEA Remote On/Off
                nValue = 0
                sValue = 0
                if value == "00":
                    nValue = 0
                    sValue = 0
                elif value == "toggle": # Toggle
                    nValue = 1
                    sValue = '10'
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True )

            if ClusterType == DeviceType == "Ikea_Round_5b": # IKEA Remote 5 buttons round one.
                nValue = 0
                sValue = 0
                if value == "00":
                    nValue = 0
                    sValue = 0
                elif value == "toggle": # Toggle
                    nValue = 1
                    sValue = '10'
                elif value == "left_click": # Left Click
                    nValue = 2
                    sValue = '20'
                elif value == "right_click": # Right Click
                    nValue = 3
                    sValue = '30'
                elif value == "click_up": # Up Click
                    nValue = 4
                    sValue = '40'
                elif value == "hold_up": # Up Push
                    nValue = 5
                    sValue = '50'
                elif value == "release_up": # Up Release
                    nValue = 6
                    sValue = '60'
                elif value == "click_down": # Down Click
                    nValue = 7
                    sValue = '70'
                elif value == "hold_down": # Down Push
                    nValue = 8
                    sValue = '80'
                elif value == "release_down": # Down Release
                    nValue = 9
                    sValue = '90'
                elif value == "right_hold": # 
                    nValue = 10
                    sValue = '100'
                elif value == "release_down": # Down Release
                    nValue = 11
                    sValue = '110'
                elif value == "left_hold": # Down Release
                    nValue = 12
                    sValue = '120'
                elif value == "release_down": # Down Release
                    nValue = 13
                    sValue = '130'
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True )


def ResetDevice(self, Devices, ClusterType, HbCount):
    '''
        Reset all Devices from the ClusterType Motion after 30s
    '''

    x = 0
    for x in Devices:
        if Devices[x].nValue == 0 and Devices[x].sValue == "Off":
            # No need to spend time as it is already in the state we want, go to next device
            continue


        LUpdate = Devices[x].LastUpdate
        _tmpDeviceID_IEEE = Devices[x].DeviceID
        try:
            LUpdate = time.mktime(time.strptime(LUpdate, "%Y-%m-%d %H:%M:%S"))
        except:
            Domoticz.Error("Something wrong to decode Domoticz LastUpdate %s" %LUpdate)
            break

        current = time.time()

        # Look for the corresponding ClusterType
        if _tmpDeviceID_IEEE in self.IEEE2NWK:
            NWKID = self.IEEE2NWK[_tmpDeviceID_IEEE]

            if NWKID not in self.ListOfDevices:
                Domoticz.Error("ResetDevice " + str(NWKID) + " not found in " + str(self.ListOfDevices))
                continue

            ID = Devices[x].ID
            DeviceType = ''
            for tmpEp in self.ListOfDevices[NWKID]['Ep']:
                if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    if str(ID) in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']:
                        DeviceType = self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][str(ID)]
            if DeviceType == '':
                if 'ClusterType' in self.ListOfDevices[NWKID]:
                    if str(ID) in self.ListOfDevices[NWKID]['ClusterType']:
                        DeviceType = self.ListOfDevices[NWKID]['ClusterType'][str(ID)]
            
            if DeviceType not in ('Motion', 'Vibration'):
                continue

            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus

                # Let's check if we have a Device TimeOut specified by end user
                if self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion( Devices[x].ID) > 0:
                    continue

            # Takes the opportunity to update RSSI and Battery
            SignalLevel = ''
            BatteryLevel = ''
            if self.ListOfDevices[NWKID].get('RSSI'):
                SignalLevel = self.ListOfDevices[NWKID]['RSSI']
            if self.ListOfDevices[NWKID].get('Battery'):
                BatteryLevel = self.ListOfDevices[NWKID]['Battery']

            _timeout = self.pluginconf.pluginConf['resetMotiondelay']
            #resetMotionDelay = 0

            #if self.domoticzdb_DeviceStatus:
            #    from Classes.DomoticzDB import DomoticzDB_DeviceStatus
            #    resetMotionDelay = round(self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion( Devices[x].ID),1)

            #if resetMotionDelay > 0:
            #    _timeout = resetMotionDelay

            if (current - LUpdate) >= _timeout: 
                loggingWidget( self, "Debug", "Last update of the devices " + str(x) + " was : " + str(LUpdate) + " current is : " + str(
                    current) + " this was : " + str(current - LUpdate) + " secondes ago", NWKID)
                UpdateDevice_v2(self, Devices, x, 0, "Off", BatteryLevel, SignalLevel)
    return


def UpdateDevice_v2(self, Devices, Unit, nValue, sValue, BatteryLvl, SignalLvl, Color_='', ForceUpdate_=False):

    loggingWidget( self, "Debug", "UpdateDevice_v2 %s:%s:%s_%s:%s_%s (%15s)" %( nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID])

    rssi = 12
    if isinstance(SignalLvl, int):
        rssi = round((SignalLvl * 12) / 255)
        loggingWidget( self, "Debug", "UpdateDevice_v2 for : " + str(Devices[Unit].Name) + " RSSI = " + str(rssi), self.IEEE2NWK[Devices[Unit].DeviceID])

    if BatteryLvl == '' or (not isinstance(BatteryLvl, int)):
        BatteryLvl = 255
    else:
        loggingWidget( self, "Debug", "UpdateDevice_v2 for : " + str(Devices[Unit].Name) + " BatteryLevel = " + str(BatteryLvl), self.IEEE2NWK[Devices[Unit].DeviceID])

    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != int(nValue)) or (Devices[Unit].sValue != sValue) or \
            ( Color_ !='' and Devices[Unit].Color != Color_) or \
            ForceUpdate_ or \
            Devices[Unit].BatteryLevel != int(BatteryLvl) or \
            Devices[Unit].TimedOut:

            if self.pluginconf.pluginConf['logDeviceUpdate']:
                Domoticz.Log("UpdateDevice - (%15s) %s:%s" %( Devices[Unit].Name, nValue, sValue ))
            loggingWidget( self, "Debug", "Update Values %s:%s:%s %s:%s %s (%15s)" %( nValue, sValue, Color_, BatteryLvl, rssi, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID])
            if Color_:
                Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_, SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), TimedOut=0)
            else:
                Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue),               SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), TimedOut=0)
    return


def timedOutDevice( self, Devices, Unit=None, NwkId=None, TO=1):
 
    _Unit = _nValue = _sValue = None
    if Unit:
        _nValue = Devices[Unit].nValue
        _sValue = Devices[Unit].sValue
        _Unit = Unit
        if TO and not Devices[_Unit].TimedOut:
            Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=1)
        elif not TO and Devices[_Unit].TimedOut:
            Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=0)

    elif NwkId:
        if NwkId not in self.ListOfDevices:
            return
        if 'IEEE' not in self.ListOfDevices[NwkId]:
            return
        _IEEE = self.ListOfDevices[NwkId]['IEEE']
        if TO:
            self.ListOfDevices[NwkId]['Health'] = 'TimedOut'
        else:
            self.ListOfDevices[NwkId]['Health'] = 'Live'

        for x in Devices:
            if Devices[x].DeviceID == _IEEE:
                _nValue = Devices[x].nValue
                _sValue = Devices[x].sValue
                _Unit = x
                if Devices[_Unit].TimedOut:
                    if not TO:
                        loggingWidget( self, "Debug",  "reset timedOutDevice unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                        Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=0)
                else:
                    if TO:
                        loggingWidget( self, "Debug",  "timedOutDevice unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                        Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=1)


def lastSeenUpdate( self, Devices, Unit=None, NwkId=None):

    # Purpose is here just to touch the device and update the Last Seen
    # It might required to call Touch everytime we receive a message from the device and not only when update is requested.

    if Unit:
        loggingWidget( self, "Debug", "Touch unit %s" %( Devices[Unit].Name ))
        if self.DomoticzMajor <= 4 and ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10547):
            loggingWidget( self, "Debug", "Not the good Domoticz level for Touch")
            return
        # Extract NwkId from Device Unit
        IEEE = Devices[Unit].DeviceID
        if Devices[Unit].TimedOut:
            timedOutDevice( self, Devices, Unit=Unit, TO=0)
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

        if time.time() < self.ListOfDevices[NwkId]['Stamp']['LastSeen'] + 5*60:
            loggingWidget( self, "Debug", "Too early for a new update of LastSeen %s" %NwkId, NwkId)
            return

        self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = int(time.time())

        _IEEE = self.ListOfDevices[NwkId]['IEEE']
        if self.DomoticzMajor <= 4 and ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10547):
            loggingWidget( self, "Debug", "Not the good Domoticz level for Touch", NwkId)
            return
        for x in Devices:
            if Devices[x].DeviceID == _IEEE:
                loggingWidget( self, "Debug",  "Touch unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                if Devices[x].TimedOut:
                    timedOutDevice( self, Devices, Unit=x, TO=0)
                else:
                    Devices[x].Touch()

def GetType(self, Addr, Ep):
    Type = ""
    loggingWidget( self, "Debug", "GetType - Model " + str(self.ListOfDevices[Addr]['Model']) + " Profile ID : " + str(
        self.ListOfDevices[Addr]['ProfileID']) + " ZDeviceID : " + str(self.ListOfDevices[Addr]['ZDeviceID']), Addr)

    if self.ListOfDevices[Addr]['Model'] != {} and self.ListOfDevices[Addr][ 'Model'] in self.DeviceConf:
        # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
        if Ep in self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep']:
            if 'Type' in self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]:
                if self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type'] != "":
                    loggingWidget( self, "Debug", "GetType - Found Type in DeviceConf : " + str(
                        self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type']))
                    Type = self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type']
                    Type = str(Type)
        else:
            loggingWidget( self, "Debug", "GetType - Found Type in DeviceConf : " + str(
                self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Type']))
            Type = self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Type']
    else:
        loggingWidget( self, "Debug", "GetType - Model:  >%s< not found with Ep: %s in DeviceConf. Continue with ClusterSearch" %( self.ListOfDevices[Addr]['Model'], Ep), Addr)
        loggingWidget( self, "Debug", "        - List of Entries: %s" %str(self.DeviceConf.keys() ), Addr)
        Type = ""

        # Check ProfileID/ZDeviceD
        if 'Manufacturer' in self.ListOfDevices[Addr]:
            if self.ListOfDevices[Addr]['Manufacturer'] == '117c': # Ikea
                if ( self.ListOfDevices[Addr]['ProfileID'] == 'c05e' and self.ListOfDevices[Addr]['ZDeviceID'] == '0830') :
                    return "Ikea_Round_5b"
                elif self.ListOfDevices[Addr]['ProfileID'] == 'c05e' and self.ListOfDevices[Addr]['ZDeviceID'] == '0820':
                    return "Ikea_Round_OnOff"
            elif self.ListOfDevices[Addr]['Manufacturer'] == '100b': # Philipps Hue
                pass
            elif str(self.ListOfDevices[Addr]['Manufacturer']).find('LIVOLO') != -1:
                loggingWidget( self, "Debug", "GetType - Found Livolo based on Manufacturer", Addr)
                return 'LivoloSWL/LivoloSWR'

        # Finaly Chec on Cluster
        for cluster in self.ListOfDevices[Addr]['Ep'][Ep]:
            if cluster in ('Type', 'ClusterType', 'ColorMode'): continue
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
    return Type


def TypeFromCluster( self, cluster, create_=False, ProfileID_='', ZDeviceID_=''):

    loggingWidget( self, "Debug", "ClusterSearch - Cluster: %s, ProfileID: %s, ZDeviceID: %s, create: %s" %(cluster, ProfileID_, ZDeviceID_, create_))

    TypeFromCluster = ''
    if ProfileID_ == 'c05e' and ZDeviceID_ == '0830':
        TypeFromCluster = 'Ikea_Round_5b'
    elif ProfileID_ == 'c05e' and ZDeviceID_ == '0820':
        TypeFromCluster = 'Ikea_Round_OnOff'
    elif cluster == "0001": TypeFromCluster = "Voltage"
    elif cluster == "0006": TypeFromCluster = "Switch"
    elif cluster == "0008": TypeFromCluster = "LvlControl"
    elif cluster == "000c" and not create_: TypeFromCluster = "XCube"
    elif cluster == "0012" and not create_: TypeFromCluster = "XCube"
    elif cluster == "0101": TypeFromCluster = "Vibration"
    elif cluster == "0102": TypeFromCluster = "WindowCovering"
    elif cluster == "0201": TypeFromCluster = "Temp/ThermoSetpoint/ThermoMode"
    elif cluster == "0300": TypeFromCluster = "ColorControl"
    elif cluster == "0400": TypeFromCluster = "Lux"
    elif cluster == "0402": TypeFromCluster = "Temp"
    elif cluster == "0403": TypeFromCluster = "Baro"
    elif cluster == "0405": TypeFromCluster = "Humi"
    elif cluster == "0406": TypeFromCluster = "Motion"
    elif cluster == "0702": TypeFromCluster = "Power/Meter"
    elif cluster == "0500": TypeFromCluster = "Door"
    elif cluster == "0502": TypeFromCluster = "AlarmWD"
    elif cluster == "0b04": TypeFromCluster = "Power/Meter"

    elif cluster == "fc00" : TypeFromCluster = 'LvlControl'   # RWL01 - Hue remote

    # Propriatory Cluster. Plugin Cluster
    elif cluster == "rmt1": TypeFromCluster = "Ikea_Round_5b"

    # Xiaomi Strenght for Vibration
    elif cluster == "Strenght": TypeFromCluster = "Strenght"
    # Xiaomi Orientation for Vibration
    elif cluster == "Orientation": TypeFromCluster = "Orientation"

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


    loggingWidget( self, "Debug", "subtypeRGB_FromProfile_Device_IDs - Model: %s, ProfileID: %s, ZDeviceID: %s ColorInfos: %s" %(Model, ProfileID, ZDeviceID, ColorInfos))
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
            pass

    # Home Automation / ZHA
    if Subtype is None and ProfileID == '0104': # Home Automation
        if ZLL_Commissioning and ZDeviceID == '0100': # Most likely IKEA Tradfri bulb LED1622G12
            Subtype = ColorControlWW
            loggingWidget( self, "Debug", "subtypeRGB_FromProfile_Device_IDs - ProfileID: %s ZDeviceID: %s Subtype: %s" %(ProfileID, ZDeviceID, Subtype))
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
            loggingWidget( self, "Debug", "subtypeRGB_FromProfile_Device_IDs - ColorMode: %s Subtype: %s" %(ColorMode,Subtype))
        elif ColorMode == 1:
            Subtype = ColorControlRGB
            loggingWidget( self, "Debug", "subtypeRGB_FromProfile_Device_IDs - ColorMode: %s Subtype: %s" %(ColorMode,Subtype))
        else:
            Subtype = ColorControlFull

    if Subtype is None:
        Subtype = ColorControlFull

    loggingWidget( self, "Debug", "subtypeRGB_FromProfile_Device_IDs - ProfileID: %s ZDeviceID: %s Subtype: %s" %(ProfileID, ZDeviceID, Subtype))
    return Subtype
