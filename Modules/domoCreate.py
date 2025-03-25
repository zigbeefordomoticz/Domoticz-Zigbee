#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license
#
"""
    Module: domoCreat.py
    Description: Creation of Domoticz Widgets
"""


from Modules.domoticzAbstractLayer import FreeUnit, domo_create_api
from Modules.domoTools import (GetType, subtypeRGB_FromProfile_Device_IDs,
                               subtypeRGB_FromProfile_Device_IDs_onEp2,
                               update_domoticz_widget)
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.tools import get_deviceconf_parameter_value, is_domoticz_new_blind


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
    if "{}" in widget_type_list:
        widget_type_list.remove("{}")

    return widget_type_list


def deviceName(self, NWKID, DeviceType, IEEE_, EP_):
    """
    Return the Name of device to be created
    """

    _Model = _NickName = None
    devName = ""
    self.log.logging("WidgetCreation", "Debug", "deviceName - %s/%s - %s %s" % (NWKID, EP_, IEEE_, DeviceType), NWKID)
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] != {}:
        _Model = self.ListOfDevices[NWKID]["Model"]
        self.log.logging("WidgetCreation", "Debug", "deviceName - Model found: %s" % _Model, NWKID)
        if _Model in self.DeviceConf and "NickName" in self.DeviceConf[_Model]:
            _NickName = self.DeviceConf[_Model]["NickName"]
            self.log.logging("WidgetCreation", "Debug", "deviceName - NickName found %s" % _NickName, NWKID)

    if _NickName is None and _Model is None:
        _Model = ""
    elif _NickName:
        devName = _NickName + "_"
    elif _Model:
        devName = _Model + "_"

    devName += DeviceType + "-" + IEEE_ + "-" + EP_
    self.log.logging("WidgetCreation", "Debug", "deviceName - Dev Name: %s" % devName, NWKID)

    return devName


def createSwitchSelector(self, nbSelector, DeviceType=None, OffHidden=False, SelectorStyle=0):
    """
    Generate an Options attribute to handle the number of required button, if Off is hidden or notand SelectorStype

    Options = {"LevelActions": "|||",
                "LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks",
                "LevelOffHidden": "false", "SelectorStyle": "1"}
    """

    Options = {}
    self.log.logging("WidgetCreation", "Debug", "createSwitchSelector -  nbSelector: %s DeviceType: %s OffHidden: %s SelectorStyle %s " %(
        nbSelector,DeviceType,OffHidden,SelectorStyle))
    if nbSelector <= 1:
        return Options

    Options["LevelNames"] = ""
    Options["LevelActions"] = ""
    Options["LevelOffHidden"] = "false"
    Options["SelectorStyle"] = "0"

    if DeviceType:
        if DeviceType in SWITCH_SELECTORS:
            # In all cases let's populate with the Standard LevelNames
            if "LevelNames" in SWITCH_SELECTORS[DeviceType]:
                Options["LevelNames"] = SWITCH_SELECTORS[DeviceType]["LevelNames"]

            # In case we have a localized version, we will overwrite the standard vesion
            if self.pluginconf.pluginConf["Lang"] != "en-US" and "Language" in SWITCH_SELECTORS[DeviceType]:
                lang = self.pluginconf.pluginConf["Lang"]
                if (
                    lang in SWITCH_SELECTORS[DeviceType]["Language"]
                    and "LevelNames" in SWITCH_SELECTORS[DeviceType]["Language"][lang]
                ):
                    Options["LevelNames"] = SWITCH_SELECTORS[DeviceType]["Language"][lang]["LevelNames"]

            if Options["LevelNames"] != "":
                count = sum(map(lambda x: 1 if "|" in x else 0, Options["LevelNames"]))
                self.log.logging("WidgetCreation", "Debug", "----> How many Levels: %s" %count)
                for _ in range(count):
                    Options["LevelActions"] += "|"
    else:
        for bt in range(nbSelector):
            Options["LevelNames"] += "BT %03s | " % bt
            Options["LevelActions"] += "|"

        Options["LevelNames"] = Options["LevelNames"][:-2]      # Remove the last "| "
        Options["LevelActions"] = Options["LevelActions"][:-1]  # Remove the last "|"

    if SelectorStyle:
        Options["SelectorStyle"] = "%s" % SelectorStyle

    if OffHidden:
        Options["LevelOffHidden"] = "true"

    self.log.logging("WidgetCreation", "Debug", " --> Options: %s" %str(Options))
    return Options


def createDomoticzWidget( self, Devices, nwkid, ieee, ep, cType, widgetType=None, Type_=None, Subtype_=None, Switchtype_=None, widgetOptions=None, Image=None, ForceClusterType=None, ):
    """
    widgetType are pre-defined widget Type
    Type_, Subtype_ and Switchtype_ allow to create a widget ( Switchtype_ is optional )
    Image is an optional parameter
    forceClusterType if you want to overwrite the ClusterType usally based with cType
    """

    unit = FreeUnit(self, Devices, ieee)
    self.log.logging("WidgetCreation", "Debug", "createDomoticzWidget - unit: %s" % unit, nwkid)

    self.log.logging( "WidgetCreation", "Debug", "--- cType: %s widgetType: %s Type: %s Subtype: %s SwitchType: %s widgetOption: %s Image: %s ForceCluster: %s" % (
        cType, widgetType, Type_, Subtype_, Switchtype_, widgetOptions, Image, ForceClusterType), nwkid, )

    widgetName = deviceName(self, nwkid, cType, ieee, ep)
    # oldFashionWidgetName = cType + "-" + ieee + "-" + ep

    myDev_ID = domo_create_api(self, Devices, ieee, unit, widgetName, widgetType=widgetType, Type_=Type_, Subtype_=Subtype_, Switchtype_=Switchtype_, widgetOptions=widgetOptions, Image=Image)
    
    if myDev_ID == -1:
        self.ListOfDevices[nwkid]["Status"] = "failDB"
        self.log.logging("WidgetCreation", "Error", "Domoticz widget creation failed. Check that Domoticz can Accept New Hardware [%s]" % myDev_ID)
        return None

    self.ListOfDevices[nwkid]["Status"] = "inDB"
    self.ListOfDevices[nwkid]["Ep"][ep]["ClusterType"][str(myDev_ID)] = ( ForceClusterType or cType )
    return unit


def over_write_type_from_deviceconf(self, Devices, NwkId):
    """
    Updates the 'Type' of endpoints (Ep) for a given device (NwkId) based on `DeviceConf`.

    This function:
    - Checks if the device exists in `ListOfDevices`.
    - Validates that the device has a model and endpoint data.
    - Updates the 'Type' field for each endpoint if it differs from the configuration.

    Args:
        Devices (dict): Device data (not directly used in this function).
        NwkId (str): The network identifier of the device.

    Returns:
        None
    """
    self.log.logging("WidgetCreation", "Debug", f"over_write_type_from_deviceconf - Processing NwkId: {NwkId}", NwkId)

    device_data = self.ListOfDevices.get(NwkId)
    if not device_data:
        self.log.logging("WidgetCreation", "Log", f"over_write_type_from_deviceconf - NwkId: {NwkId} not found", NwkId)
        return

    ep_data = device_data.get("Ep")
    if not ep_data:
        self.log.logging("WidgetCreation", "Log", f"over_write_type_from_deviceconf - NwkId: {NwkId} 'Ep' not found", NwkId)
        return

    model = device_data.get("Model")
    if not model:
        self.log.logging("WidgetCreation", "Log", f"over_write_type_from_deviceconf - NwkId: {NwkId} 'Model' not found", NwkId)
        return

    device_conf = self.DeviceConf.get(model)
    if not device_conf:
        self.log.logging("WidgetCreation", "Log", f"over_write_type_from_deviceconf - NwkId: {NwkId} Model: {model} not found in DeviceConf", NwkId)
        return

    for ep, ep_conf in ep_data.items():
        conf_ep = device_conf.get("Ep", {}).get(ep)
        if not conf_ep:
            self.log.logging("WidgetCreation", "Log", f"over_write_type_from_deviceconf - NwkId: {NwkId} Ep: {ep} not found in DeviceConf", NwkId)
            continue

        new_type = conf_ep.get("Type")
        if not new_type:
            self.log.logging("WidgetCreation", "Log", f"over_write_type_from_deviceconf - NwkId: {NwkId} Ep: {ep} 'Type' not found in DeviceConf", NwkId)
            continue

        current_type = ep_conf.get("Type", "")
        if current_type == new_type:
            self.log.logging("WidgetCreation", "Debug",
                             f"over_write_type_from_deviceconf - NwkId: {NwkId} Ep: {ep} Type unchanged: {current_type}", NwkId)
            continue

        self.log.logging("WidgetCreation", "Debug",
                         f"over_write_type_from_deviceconf - Updating Ep: {ep} with new Type: {new_type}", NwkId)

        ep_conf["Type"] = new_type



def extract_key_infos(self, NWKID, Ep, GlobalEP, GlobalType):
    """
    Extracts and returns the key device type information for a given network ID (NWKID) and endpoint (Ep).

    This function determines the device type by checking:
    1. The device's endpoint data in `ListOfDevices[NWKID]["Ep"][Ep]`.
    2. The global device type in `ListOfDevices[NWKID]`.
    3. If neither exists, it calls `GetType()` to determine the type.

    The extracted types are added to `GlobalType` if they are not already present.

    Args:
        NWKID (str): The network identifier of the device.
        Ep (str): The endpoint identifier.
        GlobalEP (bool): A flag indicating if a global endpoint type is being used.
        GlobalType (list): A list of known global types, which may be updated.

    Returns:
        tuple[list, bool, list]:
            - A list of extracted device types (`_Type`).
            - The updated `GlobalEP` flag.
            - The updated `GlobalType` list.
    """

    self.log.logging("WidgetCreation", "Debug",
                     f"extract_key_infos - entering {Ep} {GlobalEP} {GlobalType}", NWKID)

    _Type = []

    # Extract Type from ListOfDevices safely
    ep_data = self.ListOfDevices.get(NWKID, {}).get("Ep", {}).get(Ep, {})
    dev_type = ep_data.get("Type", "")

    if dev_type:
        _Type = dev_type.split("/")
        self.log.logging("WidgetCreation", "Debug",
                         f"extract_key_infos - Type via ListOfDevice: {_Type} Ep: {Ep}", NWKID)
    else:
        # Check global Type if endpoint Type is missing
        global_dev_type = self.ListOfDevices.get(NWKID, {}).get("Type", "")
        if global_dev_type in [{}, ""]:
            _Type = GetType(self, NWKID, Ep).split("/")
            self.log.logging("WidgetCreation", "Debug",
                             f"extract_key_infos - Type via GetType: {_Type} Ep: {Ep}", NWKID)
        else:
            GlobalEP = True
            _Type = global_dev_type.split("/")
            self.log.logging("WidgetCreation", "Debug",
                             f"extract_key_infos - Type from global device: {_Type}", NWKID)

    # Check if Type is known
    if not _Type or _Type == [""]:
        return None, GlobalEP, GlobalType

    # Add new types to GlobalType if not already present
    for iterType in _Type:
        if iterType and iterType != '{}' and iterType not in GlobalType:
            self.log.logging("WidgetCreation", "Debug",
                             f"adding Type: {iterType} to Global Type: {GlobalType}", NWKID)
            GlobalType.append(iterType)

    self.log.logging("WidgetCreation", "Debug",
                     f"extract_key_infos - returning {_Type} {GlobalEP} {GlobalType}", NWKID)

    return _Type, GlobalEP, GlobalType


def CreateDomoDevice(self, Devices, NWKID):
    """
    CreateDomoDevice

    Create Domoticz Widget accordingly to the Type.

    """

    # Sanity check before starting the processing
    if NWKID == "" or NWKID not in self.ListOfDevices:
        self.log.logging("WidgetCreation", "Error", "CreateDomoDevice - Cannot create a Device without an IEEE or not in ListOfDevice .")
        return

    DeviceID_IEEE = self.ListOfDevices[NWKID].get("IEEE", "")
    model_name = self.ListOfDevices[NWKID].get("Model", "")

    # When Type is at Global level, then we create all Type against the 1st EP
    # If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
    GlobalEP = False
    GlobalType = []

    self.log.logging( "WidgetCreation", "Debug", "CreateDomoDevice - Ep to be processed : %s " % self.ListOfDevices[NWKID]["Ep"].keys(), NWKID )
    for Ep in self.ListOfDevices[NWKID]["Ep"]:

        # Use "type" at level EndPoint if existe
        self.log.logging("WidgetCreation", "Debug", "CreateDomoDevice - Process EP : %s GlobalEP: %s GlobalType: %s" %( 
            Ep, GlobalEP, str(GlobalType)), NWKID)
   
        if GlobalEP:
            # We have created already the Devices (as GlobalEP is set)
            break
        
        Type, GlobalEP, GlobalType = extract_key_infos( self, NWKID, Ep, GlobalEP, GlobalType)
        self.log.logging("WidgetCreation", "Debug", "CreateDomoDevice - Type: >%s< GlobalEp: >%s< GlobalType: >%s<" %( 
            Type, GlobalEP, str(GlobalType)), NWKID)
        
        if Type is None or Type in ( "", {} ):
            continue

        # In case Type is issued from GetType functions, this is based on Clusters,
        # In such case and the device is a Bulb or a Dimmer Switch we will get a combinaison of Switch/LvlControl and ColorControlxxx
        # We want to avoid creating of 3 widgets while 1 is enought.
        # if self.ListOfDevices[NWKID][ "Model"] not in self.DeviceConf:
        allow_switch_lvlcontrol = get_deviceconf_parameter_value(self, model_name, "AllowSwitchLvlControl", return_default=False)
        self.log.logging("WidgetCreation", "Debug", "---> Check if we need to reduce Type: %s, AllowSwitchLvlControl: %s" % (Type, allow_switch_lvlcontrol), NWKID)

        if not allow_switch_lvlcontrol:
            Type = cleanup_widget_Type(Type)

        self.log.logging("WidgetCreation", "Debug", "CreateDomoDevice - Creating devices based on Type: %s" % Type, NWKID)

        if "ClusterType" not in self.ListOfDevices[NWKID]["Ep"][Ep]:
            self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"] = {}

        # Create Combo Temp+Hum and/or Temp+Hum+Baro
        if ( "Hum" in Type or "Humi" in Type) and "Temp" in Type and "Baro" in Type:
            # Detecteur temp + Hum + Baro
            create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum+Baro")

        if ( "Hum" in Type or "Humi" in Type) and "Temp" in Type:
            # Temp + Hum
            create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum")

        for t in Type:
            self.log.logging( "WidgetCreation", "Debug", "CreateDomoDevice - DevId: %s DevEp: %s Type: %s" % (DeviceID_IEEE, Ep, t), NWKID )

            t = update_widget_type_if_possible( self, NWKID, t)

            if t in ("Aqara", "XCube"):
                # We expect Only 1 Type, so after the creation of the 2 Widgets break
                create_xcube_widgets(self, Devices, NWKID, DeviceID_IEEE, Ep, t)
                break

            if create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue

            if create_switch_selector_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue


    # for Ep
    update_device_type( self, NWKID, GlobalType )


def update_device_type( self, NWKID, GlobalType ):
    self.log.logging("WidgetCreation", "Debug", "GlobalType: %s" % (str(GlobalType)), NWKID)
    if len(GlobalType) != 0:
        self.ListOfDevices[NWKID]["Type"] = ""
        for iterType in GlobalType:
            if self.ListOfDevices[NWKID]["Type"] == "":
                self.ListOfDevices[NWKID]["Type"] = iterType
            else:
                self.ListOfDevices[NWKID]["Type"] = self.ListOfDevices[NWKID]["Type"] + "/" + iterType
        self.log.logging( "WidgetCreation", "Debug", "CreatDomoDevice - Set Type to : %s" % self.ListOfDevices[NWKID]["Type"], NWKID )


def update_widget_type_if_possible( self, Nwkid, widget_type):
    if ( widget_type == "WindowCovering" and self.ListOfDevices[Nwkid]["ProfileID"] == "0104" ):
        if self.ListOfDevices[Nwkid]["ZDeviceID"] == "0202": 
            # Blind Percentage Inverted
            return "WindowCovering"
            
        elif self.ListOfDevices[Nwkid]["ZDeviceID"] == "0200":
            return "VenetianInverted"

    if ( widget_type == "LvlControl" and self.ListOfDevices[Nwkid]["Model"] in ("", {}) and self.ListOfDevices[Nwkid]["ProfileID"] == "0104" ):
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

    # Xiaomi Magic Cube, this one required 2 continuous widget.

    # Do not use the generic createDomoticzWidget , because this one required 2 continuous widget.
    # usage later on is based on that assumption
    #
    # Xiaomi Magic Cube
    self.log.logging( "WidgetCreation", "Debug", f"create_xcube_widgets - Xiaomi Magic Cube {NWKID} {DeviceID_IEEE} {Ep} {t}")
    
    self.ListOfDevices[NWKID]["Status"] = "inDB"

    # Create the XCube Widget
    Options = createSwitchSelector(self, 10, DeviceType=t, OffHidden=True, SelectorStyle=1)
    unit = FreeUnit(self, Devices, DeviceID_IEEE, nbunit_=2)  # Look for 2 consecutive slots
    
    idx = domo_create_api(self, Devices, DeviceID_IEEE, unit, deviceName(self, NWKID, t, DeviceID_IEEE, Ep), Type_=244, Subtype_=62, Switchtype_=18, widgetOptions=Options)
    
    if idx == -1:
        self.ListOfDevices[NWKID]["Status"] = "failDB"
        self.log.logging("WidgetCreation", "Error", f"Domoticz widget creation failed. {DeviceID_IEEE} {Ep} {t} {unit}")
    else:
        self.log.logging( "WidgetCreation", "Debug", f"create_xcube_widgets - widgetID {idx} for '{t}'")
        self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"][str(idx)] = t

    # Create the Status (Text) Widget to report Rotation angle
    unit += 1
    idx = domo_create_api(self, Devices, DeviceID_IEEE, unit, deviceName(self, NWKID, "Text", DeviceID_IEEE, Ep), Type_=243, Subtype_=19, Switchtype_=0,)
    
    if idx == -1:
        self.log.logging("WidgetCreation", "Error", f"Domoticz widget creation failed. {DeviceID_IEEE} {Ep} Text {unit}")
    else:
        self.log.logging( "WidgetCreation", "Debug", f"create_xcube_widgets - widgetID {idx} for 'Text'")
        self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"][str(idx)] = "Text"


def number_switch_selectors( widget_type ):
    if widget_type not in SWITCH_SELECTORS:
        return 0
    if "LevelNames" not in SWITCH_SELECTORS[ widget_type ]:
        return 0
    levels = SWITCH_SELECTORS[ widget_type ]["LevelNames"]
    return len( levels.split("|") )


def off_hidden( widget_type ):
    if widget_type not in SWITCH_SELECTORS:
        return False
    if "OffHidden" not in SWITCH_SELECTORS[ widget_type ]:
        return False
    return SWITCH_SELECTORS[ widget_type ]["OffHidden"]


def selector_style( widget_type ):
    if widget_type not in SWITCH_SELECTORS:
        return 0
    if "SelectorStyle" not in SWITCH_SELECTORS[ widget_type ]:
        return 0
    return SWITCH_SELECTORS[ widget_type ]["SelectorStyle"]
    

def create_switch_selector_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):

    if t not in SWITCH_SELECTORS:
        return False

    _OffHidden=off_hidden( t )
    _SelectorStyle=selector_style( t )
    _num_level = number_switch_selectors( t )
    Options = createSwitchSelector(self, _num_level, DeviceType=t, OffHidden=_OffHidden, SelectorStyle=_SelectorStyle)
    createDomoticzWidget(self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions=Options)
    
    self.log.logging("WidgetCreation", "Debug", "create_switch_selector_widget - t: %s Levels: %s Off: %s Style: %s " % (
        t, _num_level, _OffHidden, _SelectorStyle), NWKID)
    return True


def colorcontrol_if_undefinded( self, Nwkid ):
    self.log.logging("WidgetCreation", "Debug", "colorcontrol_if_undefinded %s" % (Nwkid), Nwkid)
    # variateur de couleur/luminosite/on-off
    # Generic ColorControl, let's try to find a better one.
    Subtype_ = None
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
    self.log.logging( "WidgetCreation", "Debug", "create_native_widget - %s NwkId: %s Ieee: %s Widget %s  Dz2023.1: %s" %(
        widget_name, NwkId, DeviceID_IEEE, widget_name, is_domoticz_new_blind(self)), NwkId)

    if widget_name in SIMPLE_WIDGET:
        widget_record = SIMPLE_WIDGET[ widget_name ]
        if "widgetType" in widget_record:
            self.log.logging( "WidgetCreation", "Debug", "create_native_widget - Type: %s Widget %s for %s" %(
                widget_name, widget_record[ "widgetType" ], NwkId), NwkId)
            unit = createDomoticzWidget(self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name, widget_record[ "widgetType" ])
            if unit:
                set_default_value( self, Devices, DeviceID_IEEE, unit, widget_record)

            return True

    elif is_domoticz_new_blind(self) and widget_name in BLIND_DOMOTICZ_2023:
        widget_record = BLIND_DOMOTICZ_2023[ widget_name ]
        if "widgetType" in widget_record:
            self.log.logging( "WidgetCreation", "Debug", "create_native_widget - BLIND_DOMOTICZ_2023 Type: %s Widget %s for %s" %(
                widget_name, widget_record[ "widgetType" ], NwkId), NwkId)
            unit = createDomoticzWidget(self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name, widget_record[ "widgetType" ])
            if unit:
                set_default_value( self, Devices,DeviceID_IEEE, unit, widget_record)

            return True
        
    elif widget_name in BLIND_DOMOTICZ_2022:
        widget_record = BLIND_DOMOTICZ_2022[ widget_name ]
        if "widgetType" in widget_record:
            self.log.logging( "WidgetCreation", "Debug", "create_native_widget - BLIND_DOMOTICZ_2022 Type: %s Widget %s for %s" %(
                widget_name, widget_record[ "widgetType" ], NwkId), NwkId)
            unit = createDomoticzWidget(self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name, widget_record[ "widgetType" ])
            if unit:
                set_default_value( self, Devices, DeviceID_IEEE, unit, widget_record)

            return True
 
    else:
        return False
    
    Type = widget_record[ "Type" ] if "Type" in widget_record else None
    Subtype = widget_record[ "Subtype" ] if "Subtype" in widget_record else None
    Switchtype = widget_record[ "Switchtype" ] if "Switchtype" in widget_record else None
    Image = widget_record[ "Image" ] if "Image" in widget_record else None
    ForceClusterType = widget_record[ "ForceClusterType" ] if "ForceClusterType" in widget_record else None

    unit = createDomoticzWidget( 
        self, Devices, NwkId, DeviceID_IEEE, Ep, widget_name, 
        Type_=Type, 
        Subtype_=Subtype, 
        Switchtype_=Switchtype, 
        widgetOptions=None, 
        Image=Image, 
        ForceClusterType=ForceClusterType
    )
    if unit:
        set_default_value( self, Devices, DeviceID_IEEE, unit, widget_record)
    return True


def set_default_value( self, Devices, device_id_ieee, device_unit, widget_record):
    # Check if we need to initialize the Widget immediatly
    if device_unit and "sValue" in widget_record and "nValue" in widget_record:
        sValue = widget_record["sValue"] 
        nValue = widget_record["nValue"] 
        update_domoticz_widget(self, Devices, device_id_ieee, device_unit, nValue, sValue, 0, 0, ForceUpdate_=True)

 
SIMPLE_WIDGET = {
    "AirPurifierAlarm": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    "AirQuality": {
        "widgetType": "Air Quality"
    },
    "Alarm": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    # Période tarifaire en cours
    "LinkyTarif": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    "Alarm_ZL": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    "Alarm_ZL2": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    "Alarm_ZL3": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    "Ampere": {
        "Type": 243,
        "Subtype": 23
    },
    "Ampere3": {
        "Type": 89,
        "Subtype": 1
    },
    "Analog": {
        "Type": 243,
        "Subtype": 31,
        "Switchtype": 0,
        "Options": "1;tbd"
    },
    "Baro": {
        "widgetType": "Barometer"
    },
    "Button": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 9
    },
    "CH2O": {
        "widgetType": "Custom",
        "Options": "1;ppm"
    },
    "CarbonDioxyde": {
        "Type": 243,
        "Subtype": 31,
        "Switchtype": 0,
        "Options": "1;ppm"
    },
    "CarbonMonoxyde": {
        "Type": 243,
        "Subtype": 31,
        "Switchtype": 0,
        "Options": "1;ppm"
    },
    "ColorControlFull": {
        "Type": 241,
        "Subtype": 7,
        "Switchtype": 7
    },
    "ColorControlRGB": {
        "Type": 241,
        "Subtype": 1,
        "Switchtype": 7
    },
    "ColorControlRGBW": {
        "Type": 241,
        "Subtype": 1,
        "Switchtype": 7
    },
    "ColorControlRGBWW": {
        "Type": 241,
        "Subtype": 4,
        "Switchtype": 7
    },
    "ColorControlRGBWZ": {
        "Type": 241,
        "Subtype": 2,
        "Switchtype": 7
    },
    "ColorControlWW": {
        "Type": 241,
        "Subtype": 8,
        "Switchtype": 7
    },
    "ConsoMeter": {
        "Type": 113,
        "Subtype": 0,
        "Switchtype": 0,
        "sValue": "0",
        "nValue": 0
    },
    "Counter": {
        "Type": 113,
        "Subtype": 0,
        "Switchtype": 0,
        "sValue": "0",
        "nValue": 0
    },
    "Distance": {
        "Type": 243,
        "Subtype": 27,
        "Switchtype": 0
    },
    "Door": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 11
    },
    "DoorLock": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 19
    },
    "DoorSensor": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 11
    },
    "FanSpeed": {
        "Type": 243,
        "Subtype": 6,
        "Switchtype": 0
    },
    "Flow": {
        "Type": 243,
        "Subtype": 30,
        "Switchtype": 0,
        "sValue": "0.0",
        "nValue": 0
    },
    "GazMeter": {
        "Type": 251,
        "Subtype": 2,
        "Switchtype": 0,
        "sValue": "0",
        "nValue": 0
    },
    "HeatingStatus": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0,
        "Image": 15
    },
    "HeatingSwitch": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0,
        "Image": 15
    },
    "Humi": {
        "widgetType": "Humidity"
    },
    "LivoloSWL": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "LivoloSWR": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "Lux": {
        "Type": 246,
        "Subtype": 1,
        "Switchtype": 0
    },
    "Lux20MinAverage": {
        "Type": 246,
        "Subtype": 1,
        "Switchtype": 0
    },
    "LvlControl": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 7
    },
    "Meter": {
        "widgetType": "kWh"
    },
    "Motion": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 8
    },
    "Notification": {
        "Type": 243,
        "Subtype": 19,
        "Switchtype": 0
    },
    "Orientation": {
        "Type": 243,
        "Subtype": 19
    },
    "BatteryPercentage": {
        "Type": 243,
        "Subtype": 6,
        "Switchtype": 0
    },
    "P1Meter": {
        "Type": 250,
        "Subtype": 1,
        "Switchtype": 1
    },
    "P1Meter_HPHC": { "Type": 250, "Subtype": 1, "Switchtype": 1 },
    "P1Meter_ZL": {
        "Type": 250,
        "Subtype": 1,
        "Switchtype": 1
    },
    "PAC-SWITCH": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "PM25": {
        "widgetType": "Custom",
        "Options": "1;ppm"
    },
    "Plug": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0,
        "Image": 1
    },
    "Power": {
        "widgetType": "Usage"
    },
    "PowerFactor": {
        "Type": 243,
        "Subtype": 6,
        "Switchtype": 0
    },
    "ProdMeter": {
        "Type": 113,
        "Subtype": 0,
        "Switchtype": 4,
        "sValue": "0",
        "nValue": 0
    },
    "ProdPower": {
        "widgetType": "Usage"
    },
    "SOS": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 9,
        "Image": 13
    },
    "ShutterCalibration": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "Smoke": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 5
    },
    "SmokePPM": {
        "widgetType": "Custom",
        "Options": "1;ppm"
    },
    
    "phMeter": { "widgetType": "Custom", "Options": "1;pH" },
    "ec": { "widgetType": "Custom", "Options": "1;µS/cm" },
    "orp": { "widgetType": "Custom", "Options": "1;mV" },
    "freeChlorine": { "widgetType": "Custom", "Options": "1;mg/L" },
    "salinity": { "widgetType": "Custom", "Options": "1;ppm" },
    "tds": { "widgetType": "Custom", "Options": "1;ppm" },

    "Strength": {
        "Type": 243,
        "Subtype": 31
    },
    "Switch": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "SwitchAlarm": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0,
        "Image": 13
    },
    "SwitchButton": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "SwitchCalibration": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "KeypadLockout": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "SwitchCleaning": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "Tamper": {
        "Type": 243,
        "Subtype": 22,
        "Switchtype": 0
    },
    "TamperSwitch": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0
    },
    "Temp": {
        "widgetType": "Temperature"
    },
    "Temp+Hum": {
        "widgetType": "Temp+Hum"
    },
    "Temp+Hum+Baro": {
        "widgetType": "Temp+Hum+Baro"
    },
    "TempSetCurrent": {
        "Type": 242,
        "Subtype": 1
    },
    "ThermoOnOff": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0,
        "Image": 15
    },
    "ThermoSetpoint": {
        "Type": 242,
        "Subtype": 1
    },
    "TuyaDoorLock": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 19
    },
    "Valve": {
        "Type": 243,
        "Subtype": 6,
        "Switchtype": 0
    },
    "Voc": {
        "widgetType": "Custom",
        "Options": "1;ppm"
    },
    "Voltage": {
        "widgetType": "Voltage"
    },
    "Water": {
        "Type": 244,
        "Subtype": 73,
        "Switchtype": 0,
        "Image": 11
    },
    "RainIntensity": { "widgetType": "Custom", "Options": "1;mV" },
    "WaterCounter": {
        "Type": 243,
        "Subtype": 28,
        "Switchtype": 2,
        "Image": 22,
        "sValue": "0",
        "nValue": 0
    }
}


BLIND_DOMOTICZ_2022 = {
    # Blind old version before Domoticz 2023.1
    "Blind": { "Type": 244, "Subtype": 73, "Switchtype": 13, "ForceClusterType": "LvlControl", },

    "VenetianInverted": { "Type": 244, "Subtype": 73, "Switchtype": 15 },
    "Venetian": { "Type": 244, "Subtype": 73, "Switchtype": 15 },

    "WindowCovering": { "Type": 244, "Subtype": 73, "Switchtype": 16 },

    "BlindInverted": { "Type": 244, "Subtype": 73, "Switchtype": 16, "ForceClusterType": "LvlControl", },
    "BSO-Volet": { "Type": 244, "Subtype": 73, "Switchtype": 16 },
    "BSO-Orientation": { "Type": 244, "Subtype": 73, "Switchtype": 16 },

    "VanneInverted": { "Type": 244, "Subtype": 73, "Switchtype": 21 },
    "CurtainInverted": { "Type": 244, "Subtype": 73, "Switchtype": 21 },

    "Vanne": { "Type": 244, "Subtype": 73, "Switchtype": 22 },
    "Curtain": { "Type": 244, "Subtype": 73, "Switchtype": 22 },
} 


BLIND_DOMOTICZ_2023 = {
    # Blinds new version after 2023.1
    #                      Type   Subtype  Switchtype  Options
    # Switch               244     73       0            ReversePosition: false ;ReverseState: false   
    # Blinds               244     73       3            ReversePosition: false ;ReverseState: false   
    # Blinds+Stop          244     73       21           ReversePosition: false ;ReverseState: false    
    # Blinds+Percent       244     73       73           ReversePosition: false ;ReverseState: false   
    # Blinds+Venetian EU   244     73       15           ReversePosition: false ;ReverseState: false   
    # Blinds+Venetian US   244     73       14           ReversePosition: false ;ReverseState: false   

    "Blind": { "Type": 244, "Subtype": 73, "Switchtype": 3, "Options": "ReversePosition: false ;ReverseState: false", "ForceClusterType": "LvlControl", },

    "WindowCovering": { "Type": 244, "Subtype": 73, "Switchtype": 3, "Options": "ReversePosition: true; ReverseState: true", },

    "BlindInverted": { "Type": 244, "Subtype": 73, "Switchtype": 3, "Options": "ReversePosition: true  ;ReverseState: true", "ForceClusterType": "LvlControl", },
    "BSO-Volet": { "Type": 244, "Subtype": 73, "Switchtype": 3, "Options": "ReversePosition: false ;ReverseState: false" },

    "Venetian": { "Type": 244, "Subtype": 73, "Switchtype": 15, "Options": "ReversePosition: false ;ReverseState: false" },
    "VenetianInverted": { "Type": 244, "Subtype": 73, "Switchtype": 15, "Options": "ReversePosition: true  ;ReverseState: true" },

    "BSO-Orientation": { "Type": 244, "Subtype": 73, "Switchtype": 15, "Options": "ReversePosition: false ;ReverseState: false" },

    "Blind+Stop": { "Type": 244, "Subtype": 73, "Switchtype": 21, "Options": "ReversePosition: false ;ReverseState: false" },
    "VanneInverted": { "Type": 244, "Subtype": 73, "Switchtype": 21, "Options": "ReversePosition: false ;ReverseState: false" },
    "CurtainInverted": { "Type": 244, "Subtype": 73, "Switchtype": 21, "Options": "ReversePosition: false ;ReverseState: false" },
    "Vanne": { "Type": 244, "Subtype": 73, "Switchtype": 21, "Options": "ReversePosition: true  ;ReverseState: true" },
    "Curtain": { "Type": 244, "Subtype": 73, "Switchtype": 21, "Options": "ReversePosition: true  ;ReverseState: true" },
}
