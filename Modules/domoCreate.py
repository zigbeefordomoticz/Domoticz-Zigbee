#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoCreat.py
    Description: Creation of Domoticz Widgets
"""


from Modules.domoticzAbstractLayer import (FreeUnit, domo_create_api)
from Modules.domoTools import (GetType, subtypeRGB_FromProfile_Device_IDs,
                               subtypeRGB_FromProfile_Device_IDs_onEp2,
                               update_domoticz_widget)
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.tools import is_domoticz_new_blind


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

        Options["LevelNames"] = Options["LevelNames"][:-2]  # Remove the last '| '
        Options["LevelActions"] = Options["LevelActions"][:-1]  # Remove the last '|'

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


def over_write_type_from_deviceconf( self, Devices, NwkId):

    self.log.logging( "WidgetCreation", "Debug", "over_write_type_from_deviceconf - NwkId to be processed : %s " % NwkId, NwkId )
    if NwkId not in self.ListOfDevices:
        self.log.logging( "WidgetCreation", "Log", "over_write_type_from_deviceconf - NwkId : %s not found " % NwkId, NwkId )
        return
    if 'Ep' not in self.ListOfDevices[ NwkId ]:
        self.log.logging( "WidgetCreation", "Log", "over_write_type_from_deviceconf - NwkId : %s 'Ep' not found" % NwkId, NwkId )
        return

    if "Model" not in self.ListOfDevices[ NwkId ]:
        self.log.logging( "WidgetCreation", "Log", "over_write_type_from_deviceconf - NwkId : %s 'Model' not found" % NwkId, NwkId )
        return
    _model = self.ListOfDevices[ NwkId ]["Model"]
    if _model not in self.DeviceConf:
        self.log.logging( "WidgetCreation", "Log", "over_write_type_from_deviceconf - NwkId : %s Model: %s not found in DeviceConf" % (NwkId, _model), NwkId )
        return
    _deviceConf = self.DeviceConf[ _model ]

    for _ep in self.ListOfDevices[ NwkId ]['Ep']:
        if _ep not in _deviceConf['Ep']:
            self.log.logging( "WidgetCreation", "Log", "over_write_type_from_deviceconf - NwkId : %s 'ep: %s' not found in DeviceConf" % (NwkId, _ep), NwkId )
            continue
        if "Type" not in _deviceConf['Ep'][ _ep ]:
            self.log.logging( "WidgetCreation", "Log", "over_write_type_from_deviceconf - NwkId : %s 'Type' not found in DeviceConf" % (NwkId,), NwkId )
            continue
        if "Type" in self.ListOfDevices[ NwkId ]['Ep'][ _ep ] and self.ListOfDevices[ NwkId ]['Ep'][ _ep ]["Type"] == _deviceConf['Ep'][ _ep ]["Type"]:
            self.log.logging( "WidgetCreation", "Debug", "over_write_type_from_deviceconf - NwkId : %s Device Type: %s == Device Conf Type: %s" % (
                NwkId,self.ListOfDevices[ NwkId ]['Ep'][ _ep ]["Type"] , _deviceConf['Ep'][ _ep ]["Type"]), NwkId )
            continue

        self.log.logging(
            "WidgetCreation", "Debug", "over_write_type_from_deviceconf - Ep Overwrite Type with a new one %s on ep: %s" % (
                _deviceConf['Ep'][ _ep ]["Type"], _ep), NwkId )

        self.ListOfDevices[ NwkId ]['Ep'][ _ep ]["Type"] = _deviceConf['Ep'][ _ep ]["Type"]


def extract_key_infos( self, NWKID, Ep, GlobalEP, GlobalType):
    self.log.logging( "WidgetCreation", "Debug", "extract_key_infos - entering %s %s %s" % ( Ep, GlobalEP, str(GlobalType)), NWKID )
    _dType = ""
    _aType = ""
    _Type = ""
    # First time, or we dont't GlobalType
    if "Type" in self.ListOfDevices[NWKID]["Ep"][Ep]:
        if self.ListOfDevices[NWKID]["Ep"][Ep]["Type"] == "":
            _Type = GetType(self, NWKID, Ep).split("/")
            self.log.logging( "WidgetCreation", "Debug", "extract_key_infos - Type via GetType: %s Ep: %s" %( 
                str(_Type) , str(Ep)), NWKID )
        else:
            _dType = self.ListOfDevices[NWKID]["Ep"][Ep]["Type"]
            _aType = str(_dType)
            _Type = _aType.split("/")
            self.log.logging( "WidgetCreation", "Debug", "extract_key_infos - Type via ListOfDevice: %s Ep: %s" %( 
                str(_Type), str(Ep)), NWKID, )
            
    elif self.ListOfDevices[NWKID]["Type"] in [{}, ""]:
        _Type = GetType(self, NWKID, Ep).split("/")
        self.log.logging( "WidgetCreation", "Debug", "extract_key_infos - Type via GetType: %s Ep: %s" %( 
            str(_Type), str(Ep)), NWKID )
        
    else:
        GlobalEP = True
        if "Type" in self.ListOfDevices[NWKID]:
            _Type = self.ListOfDevices[NWKID]["Type"].split("/")
            self.log.logging("WidgetCreation", "Debug", "extract_key_infos - Type : %s " %(str(_Type)), NWKID)

    # Check if Type is known
    if len(_Type) == 1 and _Type[0] == "":
        return None, GlobalEP, GlobalType

    for iterType in _Type:
        if iterType not in GlobalType and iterType != "":
            self.log.logging( "WidgetCreation", "Debug", "adding Type : %s to Global Type: %s" % (
                iterType, str(GlobalType)), NWKID )
            GlobalType.append(iterType)
            
    self.log.logging( "WidgetCreation", "Debug", "extract_key_infos - returning %s %s %s" % (
        _Type, GlobalEP, str(GlobalType)), NWKID )
            
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

    DeviceID_IEEE = self.ListOfDevices[NWKID]["IEEE"]

    # When Type is at Global level, then we create all Type against the 1st EP
    # If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
    GlobalEP = False
    GlobalType = []

    self.log.logging( "WidgetCreation", "Debug", "CreateDomoDevice - Ep to be processed : %s " % self.ListOfDevices[NWKID]["Ep"].keys(), NWKID )
    for Ep in self.ListOfDevices[NWKID]["Ep"]:

        # Use 'type' at level EndPoint if existe
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
        # if self.ListOfDevices[NWKID][ 'Model'] not in self.DeviceConf:
        self.log.logging("WidgetCreation", "Debug", "---> Check if we need to reduce Type: %s" % Type)
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

            if create_native_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue

            if create_switch_selector_widget( self, Devices, NWKID, DeviceID_IEEE, Ep, t):
                continue

            if t in ("Aqara", "XCube") and create_xcube_widgets(self, Devices, NWKID, DeviceID_IEEE, Ep, t):
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
    # Xiaomi Magic Cube, this one required 2 continuous widget.
    self.ListOfDevices[NWKID]["Status"] = "inDB"
    
    # Create the XCube Widget
    Options = createSwitchSelector(self, 10, DeviceType=t, OffHidden=True, SelectorStyle=1)
    unit = FreeUnit(self, Devices, DeviceID_IEEE, nbunit_=2)  # Look for 2 consecutive slots
    
    idx = domo_create_api(self, Devices, DeviceID_IEEE, unit, deviceName(self, NWKID, t, DeviceID_IEEE, Ep), Type_=244, Subtype_=62, Switchtype_=18, widgetOptions=Options)
    
    if idx == -1:
        self.ListOfDevices[NWKID]["Status"] = "failDB"
        self.log.logging("WidgetCreation", "Error", f"Domoticz widget creation failed. {DeviceID_IEEE} {Ep} {t} {unit}")
    else:
        self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"][str(idx)] = t

    # Create the Status (Text) Widget to report Rotation angle
    unit += 1
    idx = domo_create_api(self, Devices, DeviceID_IEEE, unit, deviceName(self, NWKID, t, DeviceID_IEEE, Ep), Type_=243, Subtype_=19, Switchtype_=0,)
    
    if idx == -1:
        self.log.logging("WidgetCreation", "Error", f"Domoticz widget creation failed. {DeviceID_IEEE} {Ep} {t} {unit}")
    else:
        self.ListOfDevices[NWKID]["Ep"][Ep]["ClusterType"][str(idx)] = "Text"


def number_switch_selectors( widget_type ):
    if widget_type not in SWITCH_SELECTORS:
        return 0
    if "LevelNames" not in SWITCH_SELECTORS[ widget_type ]:
        return 0
    levels = SWITCH_SELECTORS[ widget_type ]["LevelNames"]
    return len( levels.split('|') )


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
    self.log.logging( "WidgetCreation", "Debug", "create_native_widget - NwkId: %s Ieee: %s Widget %s  Dz2023.1: %s" %(
        NwkId, DeviceID_IEEE, widget_name, is_domoticz_new_blind(self)), NwkId)

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
    "Temp+Hum+Baro": { "widgetType": "Temp+Hum+Baro", },
    "Temp+Hum": { "widgetType": "Temp+Hum", },
    "Temp": { "widgetType": "Temperature", },
    "Humi": { "widgetType": "Humidity", },
    "Baro": { "widgetType": "Barometer", },
    "AirQuality": { "widgetType": "Air Quality", },
    "Power": { "widgetType": "Usage", },
    "Meter": { "widgetType": "kWh", },
    "ConsoMeter": { "Type": 113, "Subtype": 0, "Switchtype": 0, "sValue": "0", "nValue": 0},
    "ProdMeter": { "Type": 113, "Subtype": 0, "Switchtype": 4, "sValue": "0", "nValue": 0},
    "ProdPower": { "widgetType": "Usage", },
    "Voltage": { "widgetType": "Voltage", },
    "Voc": { "widgetType": "Custom", "Options": "1;ppm" },
    "PM25": { "widgetType": "Custom", "Options": "1;ppm" },
    "CH2O": { "widgetType": "Custom", "Options": "1;ppm" },
    "SmokePPM": { "widgetType": "Custom", "Options": "1;ppm" },
    "CarbonDioxyde": { "Type": 0xF3, "Subtype": 31, "Switchtype": 0, "Options": "1;ppm", },
    "CarbonMonoxyde": { "Type": 0xF3, "Subtype": 31, "Switchtype": 0, "Options": "1;ppm", },
    "Analog": { "Type": 0xF3, "Subtype": 31, "Switchtype": 0, "Options": "1;tbd", },
    "Alarm": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Tamper": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Alarm_ZL": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Alarm_ZL2": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "Alarm_ZL3": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "AirPurifierAlarm": { "Type": 243, "Subtype": 22, "Switchtype": 0, },
    "PowerFactor": { "Type": 243, "Subtype": 6, "Switchtype": 0, },
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
    "SwitchAlarm": { "Type": 244, "Subtype": 73, "Switchtype": 0, "Image": 13 },
    "TamperSwitch": { "Type": 244, "Subtype": 73, "Switchtype": 0, },
    "Distance": { "Type": 243, "Subtype": 27, "Switchtype": 0},
    "WaterCounter": { "Type": 243, "Subtype": 28, "Switchtype": 2, "Image": 22, "sValue": "0", "nValue": 0},
    "GazMeter": { "Type": 251, "Subtype": 2, "Switchtype": 0, "sValue": "0", "nValue": 0},
    "Counter": { "Type": 113, "Subtype": 0, "Switchtype": 0, "sValue": "0", "nValue": 0},
    "Notification": {"Type":243, "Subtype":19, "Switchtype":0,}
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
