#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoCreat.py
    Description: Creation of Domoticz Widgets
"""


import Domoticz

from Modules.domoTools import (GetType, subtypeRGB_FromProfile_Device_IDs,
                               subtypeRGB_FromProfile_Device_IDs_onEp2)
from Modules.widgets import SWITCH_LVL_MATRIX
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL


def cleanup_widget_Type(widget_type_list):

    if ("ColorControlFull" in widget_type_list) and ("ColorControl" in widget_type_list):
        widget_type_list.remove("ColorControlFull")
    if ("ColorControlRGB" in widget_type_list) and ("ColorControlRGBWW" in widget_type_list):
        widget_type_list.remove("ColorControlRGB")
    if ("ColorControlWW" in widget_type_list) and ("ColorControlRGBWW" in widget_type_list):
        widget_type_list.remove("ColorControlWW")
    if ("ColorControlRGBWW" in widget_type_list) and ("ColorControl" in widget_type_list):
        widget_type_list.remove("ColorControlRGBWW")

    if ("Switch" in widget_type_list) and ("LvlControl" in widget_type_list):
        widget_type_list.remove("Switch")
    if ("LvlControl" in widget_type_list) and ("ColorControl" in widget_type_list):
        widget_type_list.remove("LvlControl")

    if "" in widget_type_list:
        widget_type_list.remove("")

    return widget_type_list


def deviceName(self, NWKID, DeviceType, IEEE_, EP_):
    """
    Return the Name of device to be created
    """

    _Model = _NickName = None
    devName = ""
    self.log.logging("Widget", "Debug", "deviceName - %s/%s - %s %s" % (NWKID, EP_, IEEE_, DeviceType), NWKID)
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] != {}:
        _Model = self.ListOfDevices[NWKID]["Model"]
        self.log.logging("Widget", "Debug", "deviceName - Model found: %s" % _Model, NWKID)
        if _Model in self.DeviceConf and "NickName" in self.DeviceConf[_Model]:
            _NickName = self.DeviceConf[_Model]["NickName"]
            self.log.logging("Widget", "Debug", "deviceName - NickName found %s" % _NickName, NWKID)

    if _NickName is None and _Model is None:
        _Model = ""
    elif _NickName:
        devName = _NickName + "_"
    elif _Model:
        devName = _Model + "_"

    devName += DeviceType + "-" + IEEE_ + "-" + EP_
    self.log.logging("Widget", "Debug", "deviceName - Dev Name: %s" % devName, NWKID)

    return devName


def how_many_slot_available( Devices ):
    return sum(x not in Devices for x in range( 1, 255 ))


def FreeUnit(self, Devices, nbunit_=1):
    """
    FreeUnit
    Look for a Free Unit number. If nbunit > 1 then we look for nbunit consecutive slots
    """
    if how_many_slot_available( Devices ) <= 5:
        self.log.logging("Widget", "Status", "It seems that you can create only 5 Domoticz widgets more !!!")
    elif how_many_slot_available( Devices ) <= 15:
        self.log.logging("Widget", "Status", "It seems that you can create only 15 Domoticz widgets more !!")
    elif how_many_slot_available( Devices ) <= 30:
        self.log.logging("Widget", "Status", "It seems that you can create only 30 Domoticz widgets more !")
        
    for x in range(1, 255):
        if x not in Devices:
            if nbunit_ == 1:
                return x
            nb = 1
            for y in range(x + 1, 255):
                if y not in Devices:
                    nb += 1
                else:
                    break
                if nb == nbunit_:  # We have found nbunit consecutive slots
                    self.log.logging("Widget", "Debug", "FreeUnit - device " + str(x) + " available")
                    return x

    self.log.logging("Widget", "Debug", "FreeUnit - device " + str(len(Devices) + 1))
    return len(Devices) + 1


def createSwitchSelector(self, nbSelector, DeviceType=None, OffHidden=False, SelectorStyle=0):
    """
    Generate an Options attribute to handle the number of required button, if Off is hidden or notand SelectorStype

    Options = {"LevelActions": "|||",
                "LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks",
                "LevelOffHidden": "false", "SelectorStyle": "1"}
    """

    Options = {}
    # Domoticz.Log( "createSwitchSelector -  nbSelector: %s DeviceType: %s OffHidden: %s SelectorStyle %s " %(nbSelector,DeviceType,OffHidden,SelectorStyle))
    if nbSelector <= 1:
        return Options

    Options["LevelNames"] = ""
    Options["LevelActions"] = ""
    Options["LevelOffHidden"] = "false"
    Options["SelectorStyle"] = "0"

    if DeviceType:
        if DeviceType in SWITCH_LVL_MATRIX:
            # In all cases let's populate with the Standard LevelNames
            if "LevelNames" in SWITCH_LVL_MATRIX[DeviceType]:
                Options["LevelNames"] = SWITCH_LVL_MATRIX[DeviceType]["LevelNames"]

            # In case we have a localized version, we will overwrite the standard vesion
            if self.pluginconf.pluginConf["Lang"] != "en-US" and "Language" in SWITCH_LVL_MATRIX[DeviceType]:
                lang = self.pluginconf.pluginConf["Lang"]
                if (
                    lang in SWITCH_LVL_MATRIX[DeviceType]["Language"]
                    and "LevelNames" in SWITCH_LVL_MATRIX[DeviceType]["Language"][lang]
                ):
                    Options["LevelNames"] = SWITCH_LVL_MATRIX[DeviceType]["Language"][lang]["LevelNames"]

            if Options["LevelNames"] != "":
                count = sum(map(lambda x: 1 if "|" in x else 0, Options["LevelNames"]))
                # Domoticz.Log("----> How many Levels: %s" %count)
                for _ in range(count):
                    Options["LevelActions"] += "|"
    else:
        for bt in range(nbSelector):
            Options["LevelNames"] += "BT %03s | " % bt
            Options["LevelActions"] += "|"

        Options["LevelNames"] = Options["LevelNames"][:-2]  # Remove the last '| '
        Options["LevelActions"] = Options["LevelActions"][:-1]  # Remove the last '|'

    if SelectorStyle:
        Options["SelectorStyle"] = "%s" % SelectorStyle

    if OffHidden:
        Options["LevelOffHidden"] = "true"

    # Domoticz.Log(" --> Options: %s" %str(Options))
    return Options


def createDomoticzWidget( self, Devices, nwkid, ieee, ep, cType, widgetType=None, Type_=None, Subtype_=None, Switchtype_=None, widgetOptions=None, Image=None, ForceClusterType=None, ):
    """
    widgetType are pre-defined widget Type
    Type_, Subtype_ and Switchtype_ allow to create a widget ( Switchtype_ is optional )
    Image is an optional parameter
    forceClusterType if you want to overwrite the ClusterType usally based with cType
    """

    unit = FreeUnit(self, Devices)
    self.log.logging("Widget", "Debug", "CreateDomoDevice - unit: %s" % unit, nwkid)

    self.log.logging(
        "Widget",
        "Debug",
        "--- cType: %s widgetType: %s Type: %s Subtype: %s SwitchType: %s widgetOption: %s Image: %s ForceCluster: %s"
        % (cType, widgetType, Type_, Subtype_, Switchtype_, widgetOptions, Image, ForceClusterType),
        nwkid,
    )

    widgetName = deviceName(self, nwkid, cType, ieee, ep)
    # oldFashionWidgetName = cType + "-" + ieee + "-" + ep

    if widgetType:
        # We only base the creation on widgetType
        myDev = Domoticz.Device(DeviceID=ieee, Name=widgetName, Unit=unit, TypeName=widgetType)

    elif widgetOptions:
        # In case of widgetOptions, we have a Selector widget
        if Type_ is None and Subtype_ is None and Switchtype_ is None:
            Type_ = 244
            Subtype_ = 62
            Switchtype_ = 18
        myDev = Domoticz.Device(
            DeviceID=ieee,
            Name=widgetName,
            Unit=unit,
            Type=Type_,
            Subtype=Subtype_,
            Switchtype=Switchtype_,
            Options=widgetOptions,
        )
    elif Image:
        myDev = Domoticz.Device( DeviceID=ieee, Name=widgetName, Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_, Image=Image )
    elif Switchtype_:
        myDev = Domoticz.Device( DeviceID=ieee, Name=widgetName, Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_ )
    else:
        myDev = Domoticz.Device(DeviceID=ieee, Name=widgetName, Unit=unit, Type=Type_, Subtype=Subtype_)

    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1:
        self.ListOfDevices[nwkid]["Status"] = "failDB"
        Domoticz.Error("Domoticz widget creation failed. Check that Domoticz can Accept New Hardware [%s]" % myDev)
    else:
        self.ListOfDevices[nwkid]["Status"] = "inDB"
        self.ListOfDevices[nwkid]["Ep"][ep]["ClusterType"][str(ID)] = ( ForceClusterType or cType )


def over_write_type_from_deviceconf( self, Devices, NwkId):

    self.log.logging( "Widget", "Debug", "over_write_type_from_deviceconf - NwkId to be processed : %s " % NwkId, NwkId )
    if NwkId not in self.ListOfDevices:
        self.log.logging( "Widget", "Log", "over_write_type_from_deviceconf - NwkId : %s not found " % NwkId, NwkId )
        return
    if 'Ep' not in self.ListOfDevices[ NwkId ]:
        self.log.logging( "Widget", "Log", "over_write_type_from_deviceconf - NwkId : %s 'Ep' not found" % NwkId, NwkId )
        return

    if "Model" not in self.ListOfDevices[ NwkId ]:
        self.log.logging( "Widget", "Log", "over_write_type_from_deviceconf - NwkId : %s 'Model' not found" % NwkId, NwkId )
        return
    _model = self.ListOfDevices[ NwkId ]["Model"]
    if _model not in self.DeviceConf:
        self.log.logging( "Widget", "Log", "over_write_type_from_deviceconf - NwkId : %s Model: %s not found in DeviceConf" % (NwkId, _model), NwkId )
        return
    _deviceConf = self.DeviceConf[ _model ]

    for _ep in self.ListOfDevices[ NwkId ]['Ep']:
        if _ep not in _deviceConf['Ep']:
            self.log.logging( "Widget", "Log", "over_write_type_from_deviceconf - NwkId : %s 'ep: %s' not found in DeviceConf" % (NwkId, _ep), NwkId )
            continue
        if "Type" not in _deviceConf['Ep'][ _ep ]:
            self.log.logging( "Widget", "Log", "over_write_type_from_deviceconf - NwkId : %s 'Type' not found in DevieConf" % (NwkId,), NwkId )
            continue
        if "Type" in self.ListOfDevices[ NwkId ]['Ep'][ _ep ] and self.ListOfDevices[ NwkId ]['Ep'][ _ep ]["Type"] == _deviceConf['Ep'][ _ep ]["Type"]:
            self.log.logging( "Widget", "Debug", "over_write_type_from_deviceconf - NwkId : %s Device Type: %s == Device Conf Type: %s" % (
                NwkId,self.ListOfDevices[ NwkId ]['Ep'][ _ep ]["Type"] , _deviceConf['Ep'][ _ep ]["Type"]), NwkId )
            continue

        self.log.logging(
            "Widget", "Debug", "over_write_type_from_deviceconf - Ep Overwrite Type with a new one %s on ep: %s" % (
                _deviceConf['Ep'][ _ep ]["Type"], _ep), NwkId )

        self.ListOfDevices[ NwkId ]['Ep'][ _ep ]["Type"] = _deviceConf['Ep'][ _ep ]["Type"]


def extract_key_infos( self, NWKID, Ep, GlobalEP, GlobalType):
    # First time, or we dont't GlobalType
    if "Type" in self.ListOfDevices[NWKID]["Ep"][Ep]:
        if self.ListOfDevices[NWKID]["Ep"][Ep]["Type"] == "":
            Type = GetType(self, NWKID, Ep).split("/")
            self.log.logging( "Widget", "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID )

        else:
            dType = self.ListOfDevices[NWKID]["Ep"][Ep]["Type"]
            aType = str(dType)
            Type = aType.split("/")
            self.log.logging( "Widget", "Debug", "CreateDomoDevice - Type via ListOfDevice: " + str(Type) + " Ep : " + str(Ep), NWKID, )
    elif self.ListOfDevices[NWKID]["Type"] in [{}, ""]:
        Type = GetType(self, NWKID, Ep).split("/")
        self.log.logging( "Widget", "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID )
    else:
        GlobalEP = True
        if "Type" in self.ListOfDevices[NWKID]:
            Type = self.ListOfDevices[NWKID]["Type"].split("/")
            self.log.logging("Widget", "Debug", "CreateDomoDevice - Type : '" + str(Type) + "'", NWKID)

    # Check if Type is known
    if len(Type) == 1 and Type[0] == "":
        return None, GlobalEP, GlobalType

    for iterType in Type:
        if iterType not in GlobalType and iterType != "":
            self.log.logging( "Widget", "Debug", "adding Type : %s to Global Type: %s" % (iterType, str(GlobalType)), NWKID )
            GlobalType.append(iterType)
            
    return Type, GlobalEP, GlobalType


def update_device_type( self, NWKID, GlobalType ):
    self.log.logging("Widget", "Debug", "GlobalType: %s" % (str(GlobalType)), NWKID)
    if len(GlobalType) != 0:
        self.ListOfDevices[NWKID]["Type"] = ""
        for iterType in GlobalType:
            if self.ListOfDevices[NWKID]["Type"] == "":
                self.ListOfDevices[NWKID]["Type"] = iterType
            else:
                self.ListOfDevices[NWKID]["Type"] = self.ListOfDevices[NWKID]["Type"] + "/" + iterType
        self.log.logging( "Widget", "Debug", "CreatDomoDevice - Set Type to : %s" % self.ListOfDevices[NWKID]["Type"], NWKID )


def CreateDomoDevice(self, Devices, NWKID):
    """
    CreateDomoDevice

    Create Domoticz Widget accordingly to the Type.

    """

    # Sanity check before starting the processing
    if NWKID == "" or NWKID not in self.ListOfDevices:
        Domoticz.Error("CreateDomoDevice - Cannot create a Device without an IEEE or not in ListOfDevice .")
        return

    DeviceID_IEEE = self.ListOfDevices[NWKID]["IEEE"]

    # When Type is at Global level, then we create all Type against the 1st EP
    # If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
    GlobalEP = False
    GlobalType = []

    self.log.logging( "Widget", "Debug", "CreatDomoDevice - Ep to be processed : %s " % self.ListOfDevices[NWKID]["Ep"].keys(), NWKID )
    for Ep in self.ListOfDevices[NWKID]["Ep"]:
        dType = aType = Type = ""
        # Use 'type' at level EndPoint if existe
        self.log.logging("Widget", "Debug", "CreatDomoDevice - Process EP : " + str(Ep), NWKID)
        if GlobalEP:
            # We have created already the Devices (as GlobalEP is set)
            break

        Type, GlobalEP, GlobalType = extract_key_infos( self, NWKID, Ep, GlobalType)
        if Type is None:
            continue

        # In case Type is issued from GetType functions, this is based on Clusters,
        # In such case and the device is a Bulb or a Dimmer Switch we will get a combinaison of Switch/LvlControl and ColorControlxxx
        # We want to avoid creating of 3 widgets while 1 is enought.
        # if self.ListOfDevices[NWKID][ 'Model'] not in self.DeviceConf:
        self.log.logging("Widget", "Debug", "---> Check if we need to reduce Type: %s" % Type)
        Type = cleanup_widget_Type(Type)

        self.log.logging("Widget", "Debug", "CreateDomoDevice - Creating devices based on Type: %s" % Type, NWKID)

        if "ClusterType" not in self.ListOfDevices[NWKID]["Ep"][Ep]:
            self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"] = {}

        if "Humi" in Type and "Temp" in Type and "Baro" in Type:
            # Detecteur temp + Hum + Baro
            create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum+Baro")

        if "Humi" in Type and "Temp" in Type:
            # Temp + Hum
            create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Humo")

        for t in Type:
            self.log.logging( "Widget", "Debug", "CreateDomoDevice - DevId: %s DevEp: %s Type: %s" % (DeviceID_IEEE, Ep, t), NWKID )

            t = update_widget_type_if_possible( self, NWKID, t)

            if create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue

            if create_switch_selector_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue

            if t in ("Aqara", "XCube") and create_xcube_widgets(self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue

    # for Ep
    update_device_type( self, NWKID, GlobalType )


def update_widget_type_if_possible( self, Nwkid, widget_type):
    if ( widget_type == "WindowCovering" and self.ListOfDevices[Nwkid]["ProfileID"] == "0104" ):
        if self.ListOfDevices[Nwkid]["ZDeviceID"] == "0202": 
            # Blind Percentage Inverted
            return "BlindInverted"
            
        elif self.ListOfDevices[Nwkid]["ZDeviceID"] == "0200":
            return "VenetianInverted"

    if ( widget_type == "LvlControl" and self.ListOfDevices[Nwkid]["Model"] in ('', {}) and self.ListOfDevices[Nwkid]["ProfileID"] == "0104" ):
        if self.ListOfDevices[Nwkid]["ZDeviceID"] == "0202":
            # Windows Covering / Profalux -> Inverted
            return "BlindInverted"

        elif self.ListOfDevices[Nwkid]["ZDeviceID"] == "0200":
            # Shade
            return "Venetian"

    if widget_type in ( "ColorControl", ):
        return colorcontrol_if_undefinded( self, Nwkid )
        
    return widget_type    
    

def create_xcube_widgets(self, Devices, NWKID, DeviceID_IEEE, Ep, t):

    # Do not use the generic createDomoticzWidget , because this one required 2 continuous widget.
    # usage later on is based on that assumption
    #
    # Xiaomi Magic Cube
    self.ListOfDevices[NWKID]["Status"] = "inDB"
    # Create the XCube Widget
    Options = createSwitchSelector(self, 10, DeviceType=t, OffHidden=True, SelectorStyle=1)
    unit = FreeUnit(self, Devices, nbunit_=2)  # Look for 2 consecutive slots
    myDev = Domoticz.Device(
        DeviceID=str(DeviceID_IEEE),
        Name=deviceName(self, NWKID, t, DeviceID_IEEE, Ep),
        Unit=unit,
        Type=244,
        Subtype=62,
        Switchtype=18,
        Options=Options,
    )
    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1:
        self.ListOfDevices[NWKID]["Status"] = "failDB"
        Domoticz.Error("Domoticz widget creation failed. %s" % (str(myDev)))
    else:
        self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"][str(ID)] = t

    # Create the Status (Text) Widget to report Rotation angle
    unit += 1
    myDev = Domoticz.Device(
        DeviceID=str(DeviceID_IEEE),
        Name=deviceName(self, NWKID, t, DeviceID_IEEE, Ep),
        Unit=unit,
        Type=243,
        Subtype=19,
        Switchtype=0,
    )
    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1:
        Domoticz.Error("Domoticz widget creation failed. %s" % (str(myDev)))
    else:
        self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"][str(ID)] = "Text"


def number_switch_selectors( widget_type ):
    if widget_type not in SWITCH_LVL_MATRIX:
        return 0
    if "LevelNames" not in SWITCH_LVL_MATRIX[ widget_type ]:
        return 0
    levels = SWITCH_LVL_MATRIX[ widget_type ]["LevelNames"]
    return len( levels.split('|') )

def off_hidden( widget_type ):
    if widget_type not in SWITCH_LVL_MATRIX:
        return False
    if "OffHidden" not in SWITCH_LVL_MATRIX[ widget_type ]:
        return False
    return SWITCH_LVL_MATRIX[ widget_type ]["OffHidden"]

def selector_style( widget_type ):
    if widget_type not in SWITCH_LVL_MATRIX:
        return 0
    if "SelectorStyle" not in SWITCH_LVL_MATRIX[ widget_type ]:
        return 0
    return SWITCH_LVL_MATRIX[ widget_type ]["SelectorStyle"]
    

def create_switch_selector_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):

    # 5 Selectors, Style 1, OffHidden
    if t in ("IAS_ACE", "HeimanSceneSwitch", "SwitchAQ2WithOff",):
        Options = createSwitchSelector(self, 5, DeviceType=t, OffHidden=True, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Generic_5" % (t), NWKID)

    # 6 Selectors, Style 1
    if t in ("AlarmWD", ):
        Options = createSwitchSelector(self, 6, DeviceType=t, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in AlarmWD" % (t), NWKID)

    # 6 Buttons, Style 1, OffHidden
    if t in ( "GenericLvlControl", "AqaraOppleMiddle", "SwitchAQ3WithOff",):
        Options = createSwitchSelector(self, 6, DeviceType=t, OffHidden=True, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in GenericLvlControl" % (t), NWKID)

    # 7 Selectors, Style 1
    if t in ("ThermoModeEHZBRTS", "INNR_RC110_LIGHT"):
        Options = createSwitchSelector(self, 7, DeviceType=t, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ThermoModeEHZBRTS" % (t), NWKID)

    # 7 Selectors, Style 0, OffHidden
    if t in ("LegrandFilPilote",):
        Options = createSwitchSelector(self, 7, DeviceType=t, OffHidden=True, SelectorStyle=0)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in LegrandFilPilote" % (t), NWKID)

    # 7 Selectors, Style 0, OffHidden, SelectorStyle 1
    if t in ("FIP",):
        Options = createSwitchSelector(self, 7, DeviceType=t, OffHidden=True, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in FIP" % (t), NWKID)

    # 8 Selectors, Style 0, OffShowen, SelectorStyle 1
    if t in ("Motionac01",):
        Options = createSwitchSelector(self, 9, DeviceType=t, OffHidden=False, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Motionac01" % (t), NWKID)

    # 10 Selectors, Style 1, OffHidden
    if t in ("DButton_3",):
        Options = createSwitchSelector(self, 10, DeviceType=t, OffHidden=True, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in DButton3" % (t), NWKID)

    # 12 Selectors
    if t in ("OrviboRemoteSquare"):
        Options = createSwitchSelector(self, 13, DeviceType=t, OffHidden=True, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)

    # 13 Selectors, Style 1
    if t in ("INNR_RC110_SCENE",):
        Options = createSwitchSelector(self, 13, DeviceType=t, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in INNR SCENE" % (t), NWKID)

    # 14 Selectors, Style 1
    if t in ("Ikea_Round_5b",):
        Options = createSwitchSelector(self, 14, DeviceType=t, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Ikea Round" % (t), NWKID)

    if t in ("TINT_REMOTE_WHITE",):
        Options = createSwitchSelector(self, 19, DeviceType=t, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Tint-Remote-White" % (t), NWKID)

    if t in ("LumiLock"):
        Options = createSwitchSelector(self, 16, DeviceType=t, SelectorStyle=1)
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Lumi Lock" % (t), NWKID)
            
    if t in SWITCH_LVL_MATRIX:
        Options = createSwitchSelector(self, 11, DeviceType=t, OffHidden=off_hidden( t ), SelectorStyle=selector_style( t ))
        createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
        self.log.logging("Widget", "Debug", "create_switch_selector_widget - t: %s" % (t), NWKID)
        return



def colorcontrol_if_undefinded( self, Nwkid ):
    self.log.logging("Widget", "Debug", "colorcontrol_if_undefinded %s" % (Nwkid), Nwkid)
    # variateur de couleur/luminosite/on-off
    # Generic ColorControl, let's try to find a better one.
    if "Epv2" in self.ListOfDevices[Nwkid]:
        Subtype_ = subtypeRGB_FromProfile_Device_IDs_onEp2(self.ListOfDevices[Nwkid]["Epv2"])

    if Subtype_ is None:
        if "ColorInfos" in self.ListOfDevices[Nwkid]:
            Subtype_ = subtypeRGB_FromProfile_Device_IDs(
                self.ListOfDevices[Nwkid]["Ep"],
                self.ListOfDevices[Nwkid]["Model"],
                self.ListOfDevices[Nwkid]["ProfileID"],
                self.ListOfDevices[Nwkid]["ZDeviceID"],
                self.ListOfDevices[Nwkid]["ColorInfos"],
            )
        else:
            Subtype_ = subtypeRGB_FromProfile_Device_IDs(
                self.ListOfDevices[Nwkid]["Ep"],
                self.ListOfDevices[Nwkid]["Model"],
                self.ListOfDevices[Nwkid]["ProfileID"],
                self.ListOfDevices[Nwkid]["ZDeviceID"],
                None,
            )

    if Subtype_ == 0x02:
        return "ColorControlRGB"
    if Subtype_ == 0x04:
        return "ColorControlRGBWW"
    if Subtype_ == 0x08:
        return "ColorControlWW"
    
    return "ColorControlFull"


def create_native_widget( self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name):
    
    if widget_name not in SIMPLE_WIDGET:
        return False
    
    widget_record = SIMPLE_WIDGET[ widget_name ]
    if "widgetType" in widget_record:
        self.log.logging( "Widget", "Debug", "CreateDomoDevice - Type: %s Widget %s for %s" %(
            widget_name, widget_record[ "widgetType" ], NwkId), NwkId)
        createDomoticzWidget(self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name, widget_record[ "widgetType" ])
        return True
    
    Type = widget_record[ "Type" ] if "Type" in widget_record else None
    Subtype = widget_record[ "Subtype" ] if "Subtype" in widget_record else None
    Switchtype = widget_record[ "Switchtype" ] if "Switchtype" in widget_record else None
    Image = widget_record[ "Image" ] if "Image" in widget_record else None
    ForceClusterType = widget_record[ "ForceClusterType" ] if "Image" in widget_record else None

    createDomoticzWidget( 
        self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name, 
        Type_=Type, 
        Subtype_=Subtype, 
        Switchtype_=Switchtype, 
        widgetOptions=None, 
        Image=Image, 
        ForceClusterType=ForceClusterType
    )
    
    return True


SIMPLE_WIDGET = {
    "Temp+Hum+Baro": { "widgetType": "Temp+Hum+Baro", },
    "Temp+Hum": { "widgetType": "Temp+Hum", },
    "Temp": { "widgetType": "Temperature", },
    "Humi": { "widgetType": "Humidity", },
    "Baro": { "widgetType": "Barometer", },
    "AirQuality": { "widgetType": "Air Quality", },
    "Power": { "widgetType": "Usage", },
    "Meter": { "widgetType": "kWh", },
    "Voltage": { "widgetType": "Voltage", },
    "Voc": { "widgetType": "Custom", "Options": "1;ppm" },
    "PM25": { "widgetType": "Custom", "Options": "1;ppm" },
    "CH2O": { "widgetType": "Custom", "Options": "1;ppm" },
    "CarbonDioxyde": { "Type": 0xF3, "Subtype": 31, "Switchtype": 0, "Options": "1;ppm", },
    "CarbonMonoxyde": { "Type": 0xF3, "Subtype": 31, "Switchtype": 0, "Options": "1;ppm", },
    "Analog": { "Type": 0xF3, "Subtype": 31, "Switchtype": 0, "Options": "1;tbd", },
    "Alarm": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Tamper": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Alarm_ZL": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Alarm_ZL2": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Alarm_ZL3": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "AirPurifierAlarm": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Valve": { "Type": 243, "Subtype": 6, "Switchtype": 0, },
    "FanSpeed": { "Type": 243, "Subtype": 6, "Switchtype": 0, },
    "ThermoSetpoint": { "Type": 242, "Subtype": 1, },
    "TempSetCurrent": { "Type": 242, "Subtype": 1, },
    "Ampere": { "Type": 243, "Subtype": 23, },
    "Ampere3": { "Type": 89, "Subtype": 1, },
    "Door": { "Type": 244, "Subtype": 73, "Switchtype": 11, },
    "DoorSensor": { "Type": 244, "Subtype": 73, "Switchtype": 11, },
    "DoorLock": { "Type": 244, "Subtype": 73, "Switchtype": 19, },
    "TuyaDoorLock": { "Type": 244, "Subtype": 73, "Switchtype": 19, },
    "Motion": { "Type": 244, "Subtype": 73, "Switchtype": 8, },
    "LivoloSWL": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "LivoloSWR": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "Smoke": { "Type": 244, "Subtype": 73, "Switchtype": 5, },
    "Lux": { "Type": 246, "Subtype": 1, "Switchtype": 0, },
    "Switch": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "Plug": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 1, },
    "SwitchButton": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "PAC-SWITCH": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "ShutterCalibration": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "HeatingStatus": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 15, },
    "ThermoOnOff": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 15, },
    "HeatingSwitch": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 15, },
    "Button": { "Type": 244, "Subtype": 73, "Switchtype": 9, },
    "Strength": { "Type": 243, "Subtype": 31, },
    "Orientation": { "Type": 243, "Subtype": 19, },
    "Water": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 11, },
    "P1Meter": { "Type": 250, "Subtype": 1, "Switchtype": 1, },
    "P1Meter_ZL": { "Type": 250, "Subtype": 1, "Switchtype": 1, },
    "ColorControlRGBWW": { "Type": 241, "Subtype": 0x04, "Switchtype": 7, },
    "ColorControlFull": { "Type": 241, "Subtype": 0x07, "Switchtype": 7, },
    "ColorControlWW": { "Type": 241, "Subtype": 0x08, "Switchtype": 7, },
    "ColorControlRGBW": { "Type": 241, "Subtype": 0x01, "Switchtype": 7, },
    "ColorControlRGBWZ": { "Type": 241, "Subtype": 0x02, "Switchtype": 7, },
    "ColorControlRGB": { "Type": 241, "Subtype": 1, "Switchtype": 7, },
    "LvlControl": { "Type": 244, "Subtype": 73, "Switchtype": 7 },
    "VenetianInverted": { "Type": 244, "Subtype": 73, "Switchtype": 15 },
    "Venetian": { "Type": 244, "Subtype": 73, "Switchtype": 15 },
    "BSO-Volet": { "Type": 244, "Subtype": 73, "Switchtype": 16 },
    "BSO-Orientation": { "Type": 244, "Subtype": 73, "Switchtype": 16 },
    "VanneInverted": { "Type": 244, "Subtype": 73, "Switchtype": 21 },
    "CurtainInverted": { "Type": 244, "Subtype": 73, "Switchtype": 21 },
    "Vanne": { "Type": 244, "Subtype": 73, "Switchtype": 22 },
    "Curtain": { "Type": 244, "Subtype": 73, "Switchtype": 22 },
    "BlindInverted": { "Type": 244, "Subtype": 73, "Switchtype": 16, "ForceClusterType": "LvlControl", },
    "Blind": { "Type": 244, "Subtype": 73, "Switchtype": 13, "ForceClusterType": "LvlControl", },
    "SwitchAlarm": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 13 },
}