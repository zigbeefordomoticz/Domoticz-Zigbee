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


def FreeUnit(self, Devices, nbunit_=1):
    """
    FreeUnit
    Look for a Free Unit number. If nbunit > 1 then we look for nbunit consecutive slots
    """
    FreeUnit = ""
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


def createDomoticzWidget(
    self,
    Devices,
    nwkid,
    ieee,
    ep,
    cType,
    widgetType=None,
    Type_=None,
    Subtype_=None,
    Switchtype_=None,
    widgetOptions=None,
    Image=None,
    ForceClusterType=None,
):
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
        myDev = Domoticz.Device(
            DeviceID=ieee, Name=widgetName, Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_, Image=Image
        )
    elif Switchtype_:
        myDev = Domoticz.Device(
            DeviceID=ieee, Name=widgetName, Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_
        )
    else:
        myDev = Domoticz.Device(DeviceID=ieee, Name=widgetName, Unit=unit, Type=Type_, Subtype=Subtype_)

    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1:
        self.ListOfDevices[nwkid]["Status"] = "failDB"
        Domoticz.Error("Domoticz widget creation failed. Check that Domoticz can Accept New Hardware [%s]" % myDev)
    else:
        self.ListOfDevices[nwkid]["Status"] = "inDB"
        if ForceClusterType:
            self.ListOfDevices[nwkid]["Ep"][ep]["ClusterType"][str(ID)] = ForceClusterType
        else:
            self.ListOfDevices[nwkid]["Ep"][ep]["ClusterType"][str(ID)] = cType

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



def CreateDomoDevice(self, Devices, NWKID):
    """
    CreateDomoDevice

    Create Domoticz Device accordingly to the Type.

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

    self.log.logging(
        "Widget", "Debug", "CreatDomoDevice - Ep to be processed : %s " % self.ListOfDevices[NWKID]["Ep"].keys(), NWKID
    )
    for Ep in self.ListOfDevices[NWKID]["Ep"]:
        dType = aType = Type = ""
        # Use 'type' at level EndPoint if existe
        self.log.logging("Widget", "Debug", "CreatDomoDevice - Process EP : " + str(Ep), NWKID)
        if GlobalEP:
            # We have created already the Devices (as GlobalEP is set)
            break

        # First time, or we dont't GlobalType
        if "Type" in self.ListOfDevices[NWKID]["Ep"][Ep]:
            if self.ListOfDevices[NWKID]["Ep"][Ep]["Type"] != "":
                dType = self.ListOfDevices[NWKID]["Ep"][Ep]["Type"]
                aType = str(dType)
                Type = aType.split("/")
                self.log.logging(
                    "Widget",
                    "Debug",
                    "CreateDomoDevice - Type via ListOfDevice: " + str(Type) + " Ep : " + str(Ep),
                    NWKID,
                )
            else:
                Type = GetType(self, NWKID, Ep).split("/")
                self.log.logging(
                    "Widget", "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID
                )

        else:
            if self.ListOfDevices[NWKID]["Type"] == {} or self.ListOfDevices[NWKID]["Type"] == "":
                Type = GetType(self, NWKID, Ep).split("/")
                self.log.logging(
                    "Widget", "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID
                )
            else:
                GlobalEP = True
                if "Type" in self.ListOfDevices[NWKID]:
                    Type = self.ListOfDevices[NWKID]["Type"].split("/")
                    self.log.logging("Widget", "Debug", "CreateDomoDevice - Type : '" + str(Type) + "'", NWKID)

        # Check if Type is known
        if len(Type) == 1 and Type[0] == "":
            continue

        for iterType in Type:
            if iterType not in GlobalType and iterType != "":
                self.log.logging(
                    "Widget", "Debug", "adding Type : %s to Global Type: %s" % (iterType, str(GlobalType)), NWKID
                )
                GlobalType.append(iterType)

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
            createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum+Baro", "Temp+Hum+Baro")
            self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Humi and Temp and Baro" % (Type), NWKID)

        if "Humi" in Type and "Temp" in Type:
            # Temp + Hum
            createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum", "Temp+Hum")
            self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Humi and Temp" % (Type), NWKID)

        for t in Type:
            self.log.logging(
                "Widget", "Debug", "CreateDomoDevice - DevId: %s DevEp: %s Type: %s" % (DeviceID_IEEE, Ep, t), NWKID
            )

            # === Selector Switches
            if t in ("ACMode_2",):  # 5
                Options = createSwitchSelector(self, 5, DeviceType=t, OffHidden=False, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options, Image=16)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ACMode_2" % (t), NWKID)

            if t in ("FanControl",):  # 6
                Options = createSwitchSelector(self, 6, DeviceType=t, OffHidden=False, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options, Image=7)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in FanControl" % (t), NWKID)

            if t in ("ACSwing", "TuyaSirenHumi", "TuyaSirenTemp"):  # 2
                Options = createSwitchSelector(self, 2, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ACSwing" % (t), NWKID)

            # 3 Selectors, Style 0
            if t in ("Toggle", "ThermoMode_2"):
                Options = createSwitchSelector(self, 3, DeviceType=t, SelectorStyle=0)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Toggle/ThermoMode_2" % (t), NWKID)

            # 3 Selector , OffHidden, Style 0 (command)
            if t in ("HACTMODE", "LegranCableMode", ):
                Options = createSwitchSelector(self, 3, DeviceType=t, OffHidden=True, SelectorStyle=0)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in HACTMODE..." % (t), NWKID)

            # 4 Selector , OffHidden, Style 0 (command)
            if t in ("DSwitch", "blindIKEA", "ThermoMode_5"):
                Options = createSwitchSelector(self, 4, DeviceType=t, OffHidden=True, SelectorStyle=0)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in DSwitch..." % (t), NWKID)

            # 5 Selector , OffHidden, Style 0 (command)
            if t in ("ContractPower", "KF204Switch"):
                Options = createSwitchSelector(self, 6, DeviceType=t, OffHidden=True, SelectorStyle=0)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ContractPower ..." % (t), NWKID)

            # 4 Selectors, OffHidden, Style 1
            if t in ("DButton", "ThermoMode_4",):
                Options = createSwitchSelector(self, 4, DeviceType=t, OffHidden=True, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in DButton" % (t), NWKID)

            if t in ("HueSmartButton",):
                Options = createSwitchSelector(self, 3, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in HueSmartButton" % (t), NWKID)

            # 4 Selectors, Style 1
            if t in (
                "Vibration",
                "Button_3",
                "SwitchAQ2",
            ):
                Options = createSwitchSelector(self, 4, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Vibration" % (t), NWKID)

            # 5 Selectors, Style 0 ( mode command)
            if t in ("ThermoMode", "ThermoMode_3"):
                Options = createSwitchSelector(self, 6, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ThermoMode" % (t), NWKID)

            if t in ("ACMode",):
                Options = createSwitchSelector(self, 5, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ACMode" % (t), NWKID)

            # 6 Selectors, Style 1
            if t in (
                "Generic_5_buttons",
                "LegrandSelector",
                "SwitchAQ3",
                "SwitchIKEA",
                "AqaraOppleMiddleBulb",
                "TuyaSiren",
            ):
                Options = createSwitchSelector(self, 6, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Generic_5" % (t), NWKID)

            # 5 Selectors, Style 1, OffHidden
            if t in ("IAS_ACE",):
                Options = createSwitchSelector(self, 5, DeviceType=t, OffHidden=True, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Generic_5" % (t), NWKID)

            # 6 Selectors, Style 1
            if t in ("AlarmWD",):
                Options = createSwitchSelector(self, 6, DeviceType=t, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in AlarmWD" % (t), NWKID)

            # 6 Buttons, Style 1, OffHidden
            if t in (
                "GenericLvlControl",
                "AqaraOppleMiddle",
            ):

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

            # ==== Classic Widget
            if t in ("AirQuality",):
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetType="Air Quality")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Air Quality" % (t), NWKID)

            if t in ("Voc",):
                Options = "1;ppm"
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetType="Custom")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in VOC" % (t), NWKID)

            if t in ("CH2O",):
                Options = "1;ppm"
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetType="Custom")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in VOC" % (t), NWKID)

            if t in ("CarbonDioxyde",):
                Options = "1;ppm"
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=0xF3,
                    Subtype_=31,
                    Switchtype_=0,
                    widgetOptions=Options,
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Carbon Dioxyde" % (t), NWKID)

            if t in ("CarbonMonoxyde",):
                Options = "1;ppm"
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=0xF3,
                    Subtype_=31,
                    Switchtype_=0,
                    widgetOptions=Options,
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Carbon Monoxyde" % (t), NWKID)

            if t in ("Analog",):
                Options = "1;tbd"
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=0xF3,
                    Subtype_=31,
                    Switchtype_=0,
                    widgetOptions=Options,
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Analog Device" % (t), NWKID)

            if t in ("Alarm", "Tamper", "Alarm_ZL", "Alarm_ZL2", "Alarm_ZL3"):
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=243, Subtype_=22, Switchtype_=0)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Alarm" % (t), NWKID)

            if t == "Valve":
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=243, Subtype_=6, Switchtype_=0)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Valve" % (t), NWKID)

            if t in ("ThermoSetpoint", "TempSetCurrent"):
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=242, Subtype_=1)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in ThermoSetPoint" % (t), NWKID)

            if t == "Temp":
                # Detecteur temp
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Temperature")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Temp" % (t), NWKID)

            if t == "Humi":
                # Detecteur hum
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Humidity")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Humidity" % (t), NWKID)

            if t == "Baro":
                # Detecteur Baro
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Barometer")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Barometer" % (t), NWKID)

            if t in ("Ampere",):
                # Will display Current real time
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=243, Subtype_=23)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Ampere" % (t), NWKID)

            if t in ("Ampere3",):
                # Widget Ampere for Tri-Phase installation
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=89, Subtype_=1)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Ampere Tri" % (t), NWKID)

            if t == "Power":
                # Will display Watt real time
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Usage")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Power" % (t), NWKID)

            if t == "Meter":
                # Will display kWh
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, "kWh")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Meter" % (t), NWKID)

            if t == "Voltage":
                # Voltage
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Voltage")
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Voltage" % (t), NWKID)

            if t in ("Door", "DoorSensor",):
                # capteur ouverture/fermeture xiaomi
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=11)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Door" % (t), NWKID)

            if t == "Motion":
                # detecteur de presence
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=8)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Motion" % (t), NWKID)

            if t in ("LivoloSWL", "LivoloSWR"):
                # Livolo Switch Left and Right
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=0)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Livolo" % (t), NWKID)

            if t == "Smoke":
                # detecteur de fumee
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=5)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Smoke" % (t), NWKID)

            if t == "Lux":
                # Lux sensors
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=246, Subtype_=1, Switchtype_=0)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Lux" % (t), NWKID)

            if t in (
                "Switch",
                "SwitchButton",
                "PAC-SWITCH",
                "ShutterCalibration",
            ):
                # inter sans fils 1 touche 86sw1 xiaomi
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=0)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Switch" % (t), NWKID)

            if t in ("HeatingStatus", "ThermoOnOff", "HeatingSwitch"):
                # inter sans fils 1 touche 86sw1 xiaomi
                createDomoticzWidget(
                    self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=0, Image=15
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Switch" % (t), NWKID)

            if t == "DoorLock":
                # Switchtype_ = 19 Doorlock
                # Switchtype_ = 20 DoorlockInvertded
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=19)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Button" % (t), NWKID)

            if t == "Button":
                # inter sans fils 1 touche 86sw1 xiaomi
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=9)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Button" % (t), NWKID)

            if t in ("Aqara", "XCube"):
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

            if t == "Strength":
                # Vibration strength
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=243, Subtype_=31)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Strenght" % (t), NWKID)

            if t in ("Orientation",):
                # Vibration Orientation (text)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=243, Subtype_=19)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Orientation" % (t), NWKID)

            if t == "Water":
                # detecteur d'eau
                createDomoticzWidget(
                    self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=0, Image=11
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Water" % (t), NWKID)

            if t == "Plug":
                # prise pilote
                createDomoticzWidget(
                    self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=0, Image=1
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Plug" % (t), NWKID)

            if t in ("P1Meter", "P1Meter_ZL"):
                # P1 Smart Meter Energy Type 250, Subtype = 250
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=250, Subtype_=1, Switchtype_=1)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in P1Meter" % (t), NWKID)

            # ====== Blind and Venetian
            # Subtype =
            # Blind / Window covering
            #   13 Blind percentage
            #   16 Blind Percentage Inverted
            # Shade
            #   14 Venetian Blinds US
            #   15 Venetian Blind EU
            if t in ("VenetianInverted", "Venetian"):
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=15)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in VenetianInverted" % (t), NWKID)

            if t == "BSO-Volet":
                # BSO for Profalux , created as a Blinded Inverted Percentage
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=16)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in BSO" % (t), NWKID)

            if t == "BSO-Orientation":
                # BSO Orientation for Profalux, Create a Switch selector instead of Slider
                # createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 13 )
                Options = createSwitchSelector(self, 11, DeviceType=t, OffHidden=True, SelectorStyle=1)
                createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in BSO-Orientation" % (t), NWKID)

            if t == "VanneInverted":
                # Blind Percentage Inverterd
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=244,
                    Subtype_=73,
                    Switchtype_=21,
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in BlindInverted" % (t), NWKID)
    
            if t == "BlindInverted":
                # Blind Percentage Inverterd
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=244,
                    Subtype_=73,
                    Switchtype_=16,
                    ForceClusterType="LvlControl",
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in BlindInverted" % (t), NWKID)

            if t == "Vanne":
                # Blind Percentage
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=244,
                    Subtype_=73,
                    Switchtype_=22,
                )
                
            if t == "Blind":
                # Blind Percentage
                createDomoticzWidget(
                    self,
                    Devices,
                    NWKID,
                    DeviceID_IEEE,
                    Ep,
                    t,
                    Type_=244,
                    Subtype_=73,
                    Switchtype_=13,
                    ForceClusterType="LvlControl",
                )
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Blind" % (t), NWKID)

            if t == "WindowCovering":
                # Blind Percentage Inverted
                # or Venetian Blind EU
                if (
                    self.ListOfDevices[NWKID]["ProfileID"] == "0104"
                    and self.ListOfDevices[NWKID]["ZDeviceID"] == "0202"
                ):
                    createDomoticzWidget(
                        self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=16
                    )
                elif (
                    self.ListOfDevices[NWKID]["ProfileID"] == "0104"
                    and self.ListOfDevices[NWKID]["ZDeviceID"] == "0200"
                ):
                    createDomoticzWidget(
                        self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=15
                    )

                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in WindowCovering" % (t), NWKID)

            # ======= Level Control / Dimmer
            if t == "LvlControl":
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in LvlControl" % (t), NWKID)
                if self.ListOfDevices[NWKID]["Model"] != "" and self.ListOfDevices[NWKID]["Model"] != {}:
                    self.log.logging("Widget", "Debug", "---> Shade based on ZDeviceID", NWKID)
                    # Well Identified Model
                    # variateur de luminosite + On/off
                    createDomoticzWidget(
                        self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=7
                    )

                else:
                    if (
                        self.ListOfDevices[NWKID]["ProfileID"] == "0104"
                        and self.ListOfDevices[NWKID]["ZDeviceID"] == "0202"
                    ):
                        # Windows Covering / Profalux -> Inverted
                        createDomoticzWidget(
                            self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=16
                        )

                    elif (
                        self.ListOfDevices[NWKID]["ProfileID"] == "0104"
                        and self.ListOfDevices[NWKID]["ZDeviceID"] == "0200"
                    ):
                        # Shade
                        self.log.logging("Widget", "Debug", "---> Shade based on ZDeviceID", NWKID)
                        createDomoticzWidget(
                            self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=15
                        )

                    else:
                        # variateur de luminosite + On/off
                        createDomoticzWidget(
                            self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=244, Subtype_=73, Switchtype_=7
                        )

            # ======= Color Control: RGB, WW, Z or combinaisons
            if t in (
                "ColorControlRGB",
                "ColorControlWW",
                "ColorControlRGBWW",
                "ColorControlFull",
                "ColorControl",
                "ColorControlRGBW",
                "ColorControlRGBWZ",
            ):
                self.log.logging("Widget", "Debug", "CreateDomoDevice - t: %s in Colorxxxx" % (t), NWKID)
                # variateur de couleur/luminosite/on-off

                if t == "ColorControlRGB":
                    Subtype_ = 0x02  # RGB color palette / Dimable
                elif t == "ColorControlRGBWW":
                    Subtype_ = 0x04  # RGB + WW / Dimable
                elif t == "ColorControlFull":
                    Subtype_ = 0x07  # 3 Color palettes widget
                elif t == "ColorControlWW":
                    Subtype_ = 0x08  # White color palette / Dimable
                elif t == "ColorControlRGBW":
                    Subtype_ = 0x01  # RGBW
                elif t == "ColorControlRGBWZ":
                    Subtype_ = 0x06
                else:
                    # Generic ColorControl, let's try to find a better one.
                    if "Epv2" in self.ListOfDevices[NWKID]:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs_onEp2(self.ListOfDevices[NWKID]["Epv2"])

                    if Subtype_ is None:
                        if "ColorInfos" in self.ListOfDevices[NWKID]:
                            Subtype_ = subtypeRGB_FromProfile_Device_IDs(
                                self.ListOfDevices[NWKID]["Ep"],
                                self.ListOfDevices[NWKID]["Model"],
                                self.ListOfDevices[NWKID]["ProfileID"],
                                self.ListOfDevices[NWKID]["ZDeviceID"],
                                self.ListOfDevices[NWKID]["ColorInfos"],
                            )
                        else:
                            Subtype_ = subtypeRGB_FromProfile_Device_IDs(
                                self.ListOfDevices[NWKID]["Ep"],
                                self.ListOfDevices[NWKID]["Model"],
                                self.ListOfDevices[NWKID]["ProfileID"],
                                self.ListOfDevices[NWKID]["ZDeviceID"],
                                None,
                            )

                    if Subtype_ == 0x02:
                        t = "ColorControlRGB"
                    elif Subtype_ == 0x04:
                        t = "ColorControlRGBWW"
                    elif Subtype_ == 0x07:
                        t = "ColorControlFull"
                    elif Subtype_ == 0x08:
                        t = "ColorControlWW"
                    else:
                        t = "ColorControlFull"
                createDomoticzWidget(
                    self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_=241, Subtype_=Subtype_, Switchtype_=7
                )

    # for Ep
    self.log.logging("Widget", "Debug", "GlobalType: %s" % (str(GlobalType)), NWKID)
    if len(GlobalType) != 0:
        self.ListOfDevices[NWKID]["Type"] = ""
        for iterType in GlobalType:
            if self.ListOfDevices[NWKID]["Type"] == "":
                self.ListOfDevices[NWKID]["Type"] = iterType
            else:
                self.ListOfDevices[NWKID]["Type"] = self.ListOfDevices[NWKID]["Type"] + "/" + iterType
        self.log.logging(
            "Widget", "Debug", "CreatDomoDevice - Set Type to : %s" % self.ListOfDevices[NWKID]["Type"], NWKID
        )
