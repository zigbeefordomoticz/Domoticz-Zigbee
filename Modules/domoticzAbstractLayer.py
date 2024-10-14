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

"""
    Module: domoAbstractLayer.py
    Description: Set of functions which abstract Domoticz Legacy and Extended framework API
"""

import time
#import DomoticzEx as Domoticz
#DOMOTICZ_EXTENDED_API = True#
import Domoticz as Domoticz

DIMMABLE_WIDGETS = {
    (7, 1, 241): { "Widget": "Dimmable_Light", "Name": "RGBW", "partially_opened_nValue": 15},
    (7, 2, 241): { "Widget": "Dimmable_Light", "Name": "RGB", "partially_opened_nValue": 15},
    (7, 4, 241): { "Widget": "Dimmable_Light", "Name": "RGBWW", "partially_opened_nValue": 15},
    (7, 7, 241): { "Widget": "Dimmable_Light", "Name": "RGBWWZ", "partially_opened_nValue": 15},
    (7, 8, 241): { "Widget": "Dimmable_Light", "Name": "WW Switch", "partially_opened_nValue": 15},
    (7, 73, 244): { "Widget": "Dimmable_Switch", "Name": "Dimmer", "partially_opened_nValue": 2},
    (14, 73, 244): { "Widget": "Blind", "Name": "Venetian Blinds US", "partially_opened_nValue": 17},
    (13, 73, 244): { "Widget": "Blind", "Name": "Blind Percentage", "partially_opened_nValue": 2},
    (15, 73, 244): { "Widget": "Blind", "Name": "Venetian Blinds EU", "partially_opened_nValue": 17},
    (21, 73, 244): { "Widget": "Blind", "Name": "Blinds + Stop", "partially_opened_nValue": 2},
    (3, 73, 244): { "Widget": "Blind", "Name": "BSO-Volet", "partially_opened_nValue": 17},

}

DOMOTICZ_EXTENDED_API = False

DELAY_BETWEEN_TOUCH = 120

def is_domoticz_extended():
    return DOMOTICZ_EXTENDED_API

# Communication Helpers
def domoticz_connection( name, transport, protocol, address=None, port=None, baud=None):
    if address and baud:
        return Domoticz.Connection( Name=name, Transport=transport, Protocol=protocol, Address=address, Port=port, Baud=baud)
    
    if address:
        return Domoticz.Connection( Name=name, Transport=transport, Protocol=protocol, Address=address, Port=port)

    return Domoticz.Connection( Name=name, Transport=transport, Protocol=protocol, Port=port )


# Configuration Helpers
def setConfigItem(Key=None, Attribute="", Value=None):

    Config = {}
    if not isinstance(Value, (str, int, float, bool, bytes, bytearray, list, dict)):
        domoticz_error_api("setConfigItem - A value is specified of a not allowed type: '" + str(type(Value)) + "'")
        return Config

    if isinstance(Value, dict):
        # There is an issue that Configuration doesn't allow None value in dictionary !
        # Replace none value to 'null'
        Value = prepare_dict_for_storage(Value, Attribute)

    try:
        Config = Domoticz.Configuration()
        if Key is None:
            Config = Value  # set whole configuration if no key specified
        else:
            Config[Key] = Value

        Config = Domoticz.Configuration(Config)
    except Exception as inst:
        domoticz_error_api("setConfigItem - Domoticz.Configuration operation failed: '" + str(inst) + "'")
        return None
    return Config


def getConfigItem(Key=None, Attribute="", Default=None):
    
    domoticz_log_api("Loading %s - %s from Domoticz sqlite Db" %( Key, Attribute))
    
    if Default is None:
        Default = {}
    Value = Default
    try:
        Config = Domoticz.Configuration()
        Value = Config if Key is None else Config[Key]
    except KeyError:
        Value = Default
    except Exception as inst:
        domoticz_error_api(
            "getConfigItem - Domoticz.Configuration read failed: '"
            + str(inst)
            + "'"
        )

    return repair_dict_after_load(Value, Attribute)


def prepare_dict_for_storage(dict_items, Attribute):

    from base64 import b64encode

    if Attribute in dict_items:
        dict_items[Attribute] = b64encode(str(dict_items[Attribute]).encode("utf-8"))
    dict_items["Version"] = 1
    return dict_items


def repair_dict_after_load(b64_dict, Attribute):
    if b64_dict in ("", {}):
        return {}
    if "Version" not in b64_dict:
        domoticz_log_api("repair_dict_after_load - Not supported storage")
        return {}
    if Attribute in b64_dict:
        from base64 import b64decode

        b64_dict[Attribute] = eval(b64decode(b64_dict[Attribute]))
    return b64_dict


# Devices helpers

def load_list_of_domoticz_widget(self, Devices):
    """
    Use at plugin start to create an index of Domoticz Widgets.
    It is also called after a Widget removal and when a new device has been paired.

    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework
    """

    # clean 
    self.ListOfDomoticzWidget.clear()

    if DOMOTICZ_EXTENDED_API:
        for device_ieee in Devices:
            for unit_key in Devices[ device_ieee ].Units:
                unit_data = Devices[ device_ieee ].Units[ unit_key ]
                widget_info = {
                    "Name": unit_data.Name,
                    "Unit": unit_key,
                    "DeviceID": device_ieee,
                    "Switchtype": unit_data.SwitchType,
                    "Subtype": unit_data.SubType,
                }
                self.ListOfDomoticzWidget[unit_data.ID] = widget_info

    else:
        for unit_key, device in Devices.items():
            widget_info = {
                "Name": device.Name,
                "Unit": unit_key,
                "DeviceID": device.DeviceID,
                "Switchtype": device.SwitchType,
                "Subtype": device.SubType,
            }
            self.log.logging("AbstractDz", "Debug", f"Loading {unit_key}")
            unit_id = device.ID
            self.ListOfDomoticzWidget[unit_id] = widget_info

    for x in self.ListOfDomoticzWidget:
        self.log.logging( "AbstractDz", "Debug", f"Loading Devices[{x}]: {self.ListOfDomoticzWidget[ x ]}")


def find_widget_unit_from_WidgetID(self, Devices, Widget_Idx ):
    """Find the Widget Unit with Legay framework, the tuple ( DeviceID, Unit ) with the Extended Framework

    Args:
        Devices (dict): Devices dictionary provided by the Domoticz framework
        Widget_Idx (str): Domoticz Widget Idx, usally store in the "ClusterType" attribute associated to each Ep
        Should be used in domoMaj, when looking for the 'DeviceUnit'

    Returns:
        _type_: Widget Unit with Legay framework, the tuple ( DeviceID, Unit ) with the Extended Framework
        In legacy 'DeviceUnit' will be a Number, while in Extended, it will be a Tupple of DeviceID and Unit
        
    """
    
    self.log.logging( "AbstractDz", "Debug", f"find_widget_unit_from_WidgetID - Widget_Idx: {Widget_Idx} ({type(Widget_Idx)})")
    
    Widget_Idx = int(Widget_Idx)
    if Widget_Idx in self.ListOfDomoticzWidget:
        return self.ListOfDomoticzWidget[Widget_Idx]['Unit']

    self.log.logging( "AbstractDz", "Log", f"Plugin looks for Domoticz Widget Id {Widget_Idx} which do not exist !!" )
    # In case it is not found with the new way, let's keep the old way 
    # TO-DO: Remove
    
    for x in list(Devices):
        if DOMOTICZ_EXTENDED_API:
            for y in list(Devices[x].Units):
                if Devices[x].Units[y].ID == Widget_Idx:
                    return y
                
        elif Devices[x].ID == Widget_Idx:
            return x
    return None


def retreive_widgetid_from_deviceId_unit(self, Devices, DeviceId, Unit):
    self.log.logging("AbstractDz", "Debug", f"retreive_widgetid_from_deviceId_unit: DeviceId: {DeviceId} Unit: {Unit}")
    return next( ( x for x in self.ListOfDomoticzWidget if self.ListOfDomoticzWidget[x]["DeviceID"] == DeviceId and self.ListOfDomoticzWidget[x]["Unit"] == Unit ), None, )
    
    
def find_first_unit_widget_from_deviceID(self, Devices, DeviceID):
    """ return the first unit for a specific DeviceID else return None"""
    self.log.logging("AbstractDz", "Debug", f"find_first_unit_widget_from_deviceID: {DeviceID}")
    if DOMOTICZ_EXTENDED_API:
        if DeviceID in Devices:
            for unit in Devices[DeviceID].Units:
                return unit
        return None
    
    return next((x for x in Devices if Devices[x].DeviceID == DeviceID), None)


def find_legacy_DeviceID_from_unit(self, Devices, Unit):
    self.log.logging("AbstractDz", "Debug", f"find_legacy_DeviceID_from_unit: Unit: {Unit}")
    
    return Devices[ Unit ].DeviceID if Unit in Devices else None    

    
def how_many_legacy_slot_available( Devices):
    """Return the number of unit slot available

    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework

    Returns:
        int: number of available unit slot
    """
    return sum(x not in Devices for x in range( 1, 255 ))
    

def FreeUnit(self, Devices, DeviceId, nbunit_=1):
    """Look for a Free Unit number. If nbunit > 1 then we look for nbunit consecutive slots

    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework
        DeviceId (str): DeviceID (ieee). Defaults to None (means Legacy framework)
        nbunit_ (int, optional): Number of consecutive unit required. Defaults to 1.

    Returns:
        int: unit number
    """
    
    
    def _log_message(count):
        messages = {
            5: "It seems that you can create only 5 Domoticz widgets more !!!",
            15: "It seems that you can create only 15 Domoticz widgets more !!",
            30: "It seems that you can create only 30 Domoticz widgets more !",
        }
        message = messages.get(255 - count)
        if message:
            self.log.logging("AbstractDz", "Status", message)
            
    def _free_unit_in_device( list_of_units, nbunit_):
        for x in range(1, 255):
            if x not in available_units:
                if nbunit_ == 1:
                    self.log.logging("AbstractDz", "Debug", "_free_unit_in_device - device %s unit" %str(x))
                    return x
                nb = 1
                for y in range(x + 1, 255):
                    if y not in available_units:
                        nb += 1
                    else:
                        break
                    if nb == nbunit_:  # We have found nbunit consecutive slots
                        self.log.logging("AbstractDz", "Debug", "_free_unit_in_device - device %s unit" %str(x))
                        return x
        return None

    if DOMOTICZ_EXTENDED_API:
        self.log.logging("AbstractDz", "Debug", f"FreeUnit - looking for a free unit in {DeviceId}")
        available_units = set(Devices[DeviceId].Units.keys()) if DeviceId in Devices else []
        return _free_unit_in_device( available_units, nbunit_ )
            
    
    # Legacy framework
    available_units = set(Devices.keys())
    _log_message(len(available_units) + 1)
    return _free_unit_in_device( available_units, nbunit_ )


def is_device_ieee_in_domoticz_db(self, Devices, DeviceID_):
    self.log.logging("AbstractDz", "Debug", f"is_device_ieee_in_domoticz_db: DeviceID: {DeviceID_}")
    
    return DOMOTICZ_EXTENDED_API and DeviceID_ in Devices or any(DeviceID_ == device.DeviceID for device in Devices.values())


def domo_create_api(self, Devices, DeviceID_, Unit_, Name_, widgetType=None, Type_=None, Subtype_=None, Switchtype_=None, widgetOptions=None, Image=None):
    """abstract layer to be used for Legacy or Extended framework in order to create a Domoticz Widget

    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework
        DeviceID_ (str): DeviceID (ieee). Defaults to None (means Legacy framework)
        Unit_ (_type_): Unit number found with FreeUnit()
        Name_ (str): Widget name
        widgetType (str, optional): _description_. Defaults to None.
        Type_ (int, optional): Device Type. Defaults to None.
        Subtype_ (int, optional): device subtype . Defaults to None.
        Switchtype_ (int, optional): device switchtype . Defaults to None.
        widgetOptions (dict, optional): Device options. Defaults to None.
        Image (int, optional): image number. Defaults to None.

    Returns:
        _type_: return the Domoticz Widget IDX
    """
    
    # Create the device
    self.log.logging("AbstractDz", "Debug", "domo_create_api DeviceID: %s,Name: %s,Unit: %s,TypeName: %s,Type: %s,Subtype: %s,Switchtype: %s, widgetOptions= %s, Image: %s" %(
        DeviceID_, Name_, Unit_, widgetType, Type_, Subtype_, Switchtype_, widgetOptions, Image,))

    Name_ = f"{self.pluginParameters['Name']} - {Name_}" if DOMOTICZ_EXTENDED_API else Name_

    # Determine the correct class to use based on the API type
    domoticz_device_api_class = Domoticz.Unit if DOMOTICZ_EXTENDED_API else Domoticz.Device

    # Define default values if necessary
    if widgetOptions is None:
        widgetOptions = {}
        
    if widgetType:
        self.log.logging("AbstractDz", "Debug", "- based on widgetType %s" %widgetType)
        myDev = domoticz_device_api_class( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, TypeName=widgetType, )

    elif widgetOptions:
        # In case of widgetOptions, we have a Selector widget
        self.log.logging("AbstractDz", "Debug", "- based on widgetOptions %s" %widgetOptions)
        if Type_ is None and Subtype_ is None and Switchtype_ is None:
            Type_ = 244
            Subtype_ = 62
            Switchtype_ = 18
        myDev = domoticz_device_api_class( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_,Options=widgetOptions,)
               
    elif Image:     
        self.log.logging("AbstractDz", "Debug", "- based on Image %s" %Image)     
        myDev = domoticz_device_api_class( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_, Image=Image, )

    elif Switchtype_:
        self.log.logging("AbstractDz", "Debug", "- based on Switchtype_ %s" %Switchtype_)     
        myDev = domoticz_device_api_class( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_)
        
    else:
        self.log.logging("AbstractDz", "Debug", "- default")   
        myDev = domoticz_device_api_class( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, )

    myDev.Create()

    if DOMOTICZ_EXTENDED_API:
        self.log.logging("AbstractDz", "Debug", "domo_create_api status %s" %Devices[DeviceID_].Units[Unit_].ID)
        return Devices[DeviceID_].Units[Unit_].ID

    self.log.logging("AbstractDz", "Debug", "domo_create_api status %s" %myDev.ID)

    # Update the ListOfWidgets index
    load_list_of_domoticz_widget(self, Devices)
    return myDev.ID


def domo_delete_widget( self, Devices, DeviceID_, Unit_):
    self.log.logging("AbstractDz", "Debug", "domo_delete_widget: DeviceID_ : %s Unit_: %s " %( DeviceID_, Unit_))

    if DOMOTICZ_EXTENDED_API:
        Devices[DeviceID_].Units[Unit_].Delete()
        # Update the ListOfWidgets index
        load_list_of_domoticz_widget(self, Devices)

    elif Unit_ in self.Devices:
        self.Devices[Unit_].Delete()
        # Update the ListOfWidgets index
        load_list_of_domoticz_widget(self, Devices)


def domo_update_api(self, Devices, DeviceID_, Unit_, nValue, sValue, SignalLevel=None, BatteryLevel=None, TimedOut=None, Color="", Options=None, SuppressTriggers=False):
    """
    Does a widget (domoticz device) value update ( nValue,sValue, Color, Battery and Signal Level)
    Calls from UpdateDevice_v2  
    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework
        DeviceID_ (str): DeviceID (ieee). Defaults to None (means Legacy framework)
        Unit_ (int): Unit number found with FreeUnit()
        nValue (int): numeric Value
        sValue (str): String Value
        SignalLevel (int, optional): Signal Level. Defaults to None.
        BatteryLevel (int, optional): Battery Level 255 for main powered devices . Defaults to None.
        TimedOut (int, optional): Timeoud flag 0 to unset the Timeout. Defaults to None.
        Color (str, optional): Color . Defaults to "".
    """
    nwkid = None
    try:
        nwkid = self.IEEE2NWK[DeviceID_]
    except KeyError :
        pass

    self.log.logging("AbstractDz", "Debug", "domo_update_api: DeviceID_ : %s Unit_: %s nValue: %s sValue: %s SignalLevel: %s BatteryLevel: %s TimedOut: %s Color: %s : %s" %(
        DeviceID_, Unit_, nValue, sValue, SignalLevel, BatteryLevel, TimedOut, Color, Options), nwkid)

    if nValue is None:
        self.log.logging("AbstractDz", "Error", "domo_update_api: DeviceID_ : %s Unit_: %s nValue: %s sValue: %s SignalLevel: %s BatteryLevel: %s TimedOut: %s Color: %s : %s" %(
            DeviceID_, Unit_, nValue, sValue, SignalLevel, BatteryLevel, TimedOut, Color, Options), nwkid)
        return

    if DOMOTICZ_EXTENDED_API:
        Devices[DeviceID_].Units[Unit_].nValue = nValue
        Devices[DeviceID_].Units[Unit_].sValue = sValue

        if Color != "":
            Devices[DeviceID_].Units[Unit_].Color = Color
            Devices[DeviceID_].TimedOut = 0
            
        if BatteryLevel is not None:
            Devices[DeviceID_].Units[Unit_].BatteryLevel = BatteryLevel
            Devices[DeviceID_].TimedOut = 0
            
        if SignalLevel is not None:
            Devices[DeviceID_].Units[Unit_].SignalLevel = SignalLevel
            Devices[DeviceID_].TimedOut = 0
            
        if TimedOut is not None:
            Devices[DeviceID_].TimedOut = TimedOut
            
        try:
            if Options is not None:
                Devices[DeviceID_].Units[Unit_].Options = Options
                
        except Exception as e:
            self.log.logging("AbstractDz", "Debug", f"domo_update_api: Cannot Write Attribute Option with {Options}", nwkid)

        Devices[DeviceID_].Units[Unit_].Update(Log=(not SuppressTriggers) )
        return

    # Legacy
    # Define common update parameters
    update_params = {
        'nValue': int(nValue),
        'sValue': str(sValue),
    }
    if SignalLevel is not None:
        update_params['SignalLevel'] = int(SignalLevel)

    if BatteryLevel is not None:
        update_params['BatteryLevel'] = int(BatteryLevel)

    if TimedOut is not None:
        update_params['TimedOut'] = TimedOut

    if Options is not None:
        update_params['Options'] = Options

    if Color != "":
        update_params['Color'] = Color
        
    if SuppressTriggers:
        update_params['SuppressTriggers'] = True

    # Perform the update with the defined parameters
    self.log.logging("AbstractDz", "Debug", "domo_update_api: update_params %s" %(update_params))

    Devices[Unit_].Update(**update_params)


def domo_update_name(self, Devices, DeviceID_, Unit_, Name_):
    self.log.logging("AbstractDz", "Log", "domo_update_name: DeviceID_ : %s Unit_: %s Name: %s" %(DeviceID_, Unit_, Name_))

    if DOMOTICZ_EXTENDED_API and Devices[DeviceID_].Units[Unit_].Name != Name_:
            Devices[DeviceID_].Units[Unit_].Name = Name_
            Devices[DeviceID_].Units[Unit_].Update(Log=True)
            return

    update_params = {
        'nValue': Devices[Unit_].nValue,
        'sValue': Devices[Unit_].sValue,
        'Name': Name_,
    }
    Devices[Unit_].Update(**update_params)


def domo_update_SwitchType_SubType_Type(self, Devices, DeviceID_, Unit_, Type_=0, Subtype_=0, Switchtype_=0, Typename_=None):
 
    self.log.logging("AbstractDz", "Debug", "domo_update_SwitchType_SubType_Type DeviceID: %s,Unit: %s,Type: %s,Subtype: %s,Switchtype: %s" %(
        DeviceID_, Unit_, Type_, Subtype_, Switchtype_))

    if DOMOTICZ_EXTENDED_API:
        # With Domoticz Extended the change of Widget type, can be done only via Typename
        if Typename_:
            Devices[DeviceID_].Units[Unit_].Update(TypeName=Typename_)
        return
    
    update_params = {
        'nValue': Devices[Unit_].nValue,
        'sValue': Devices[Unit_].sValue,
        'Type': Type_,
        'Subtype': Subtype_,
        'Switchtype': Switchtype_
    }
    Devices[Unit_].Update(**update_params)


def domo_browse_widgets(self, Devices):
    """ return list of DeviceId, Unit """
    self.log.logging("AbstractDz", "Debug", "domo_browse_widgets")

    list_domoticz_widgets = []
    if DOMOTICZ_EXTENDED_API:
        for deviceId in Devices:
            list_domoticz_widgets.extend((deviceId, unit) for unit in Devices[deviceId].Units)
        return list_domoticz_widgets
    
    list_domoticz_widgets.extend( (Devices[unit].DeviceID, unit) for unit in Devices )
    return list_domoticz_widgets
            
    
def domo_read_nValue_sValue(self, Devices, DeviceID, Unit):
    """
    Read the nValue and sValue of a device unit.

    Args:
        Devices: The dictionary of devices.
        DeviceID: The ID of the device.
        Unit: The unit number of the device.

    Returns:
        Tuple: A tuple containing the nValue and sValue of the device unit.
    """
    self.log.logging("AbstractDz", "Debug", "domo_read_nValue_sValue: DeviceID: %s Unit: %s" %(DeviceID, Unit))

    if DOMOTICZ_EXTENDED_API:
        _unit = Devices[DeviceID].Units[Unit]
    else:
        _unit = Devices[Unit]

    return _unit.nValue, _unit.sValue


def domo_read_TimedOut( self, Devices, DeviceId_ ):
    """ Retreive TimedOut flag, stop as soon as 1 TimedOut widget detected """
    self.log.logging("AbstractDz", "Debug", f"domo_read_TimedOut: DeviceID: {DeviceId_}")
    if DOMOTICZ_EXTENDED_API and DeviceId_ in Devices:
        return Devices[ DeviceId_].TimedOut
    
    # Legacy, return the TimedOut flag of 1st unit
    return next( ( 1 for x in Devices if Devices[x].DeviceID == DeviceId_ and Devices[x].TimedOut ), 0, )
        
def domo_read_legacy_TimedOut( self, Devices, DeviceId_, UnitId_ ):
    return Devices[ UnitId_ ].TimedOut
    
def domo_read_LastUpdate(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug", f"domo_read_LastUpdate: DeviceID: {DeviceId_} Unit {Unit_}")

    if DOMOTICZ_EXTENDED_API:
        device = Devices.get(DeviceId_)
        if device:
            return device.Units.get(Unit_).LastUpdate if device.Units else None
    else:
        device = Devices.get(Unit_)
        if device:
            return device.LastUpdate

    return None


def domo_read_BatteryLevel( self, Devices, DeviceId_, Unit_, ):
    self.log.logging("AbstractDz", "Debug", f"domo_read_BatteryLevel: DeviceID: {DeviceId_} Unit {Unit_}")
    return Devices[DeviceId_].Units[Unit_].BatteryLevel if DOMOTICZ_EXTENDED_API else Devices[Unit_].BatteryLevel


def domo_read_SignalLevel( self, Devices, DeviceId_, Unit_, ):
    self.log.logging("AbstractDz", "Debug", f"domo_read_BatteryLevel: DeviceID: {DeviceId_} Unit {Unit_}")
    return Devices[DeviceId_].Units[Unit_].SignalLevel if DOMOTICZ_EXTENDED_API else Devices[Unit_].SignalLevel


def domo_read_Color( self, Devices, DeviceId_, Unit_, ):
    self.log.logging("AbstractDz", "Debug", f"domo_read_Color: DeviceID: {DeviceId_} Unit {Unit_}")
    return Devices[DeviceId_].Units[Unit_].Color if DOMOTICZ_EXTENDED_API else Devices[Unit_].Color


def domo_read_Name( self, Devices, DeviceId_, Unit_, ):
    self.log.logging("AbstractDz", "Debug", f"domo_read_Name: DeviceID: {DeviceId_} Unit {Unit_}")
    return Devices[DeviceId_].Units[Unit_].Name if DOMOTICZ_EXTENDED_API else Devices[Unit_].Name


def domo_read_Options( self, Devices, DeviceId_, Unit_,):
    self.log.logging("AbstractDz", "Debug", f"domo_read_Options: DeviceID: {DeviceId_} Unit {Unit_}")
    return Devices[DeviceId_].Units[Unit_].Options if DOMOTICZ_EXTENDED_API else Devices[Unit_].Options


def domo_read_Device_Idx(self, Devices, DeviceId_, Unit_,):
    self.log.logging("AbstractDz", "Debug", f"domo_read_Device_Idx: DeviceID: {DeviceId_} Unit {Unit_}")
    return Devices[DeviceId_].Units[Unit_].ID if DOMOTICZ_EXTENDED_API else Devices[Unit_].ID


def domo_check_unit(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug", f"domo_check_unit: DeviceID: {DeviceId_} Unit {Unit_}")
    if DOMOTICZ_EXTENDED_API:
        return Unit_ in Devices[DeviceId_].Units
    else:
        return Unit_ in Devices

    
def domo_read_SwitchType_SubType_Type(self, Devices, DeviceID, Unit):
    self.log.logging("AbstractDz", "Debug", f"domo_read_SwitchType_SubType_Type: DeviceID: {DeviceID} Unit {Unit}")
    if DOMOTICZ_EXTENDED_API:
        _unit = Devices[DeviceID].Units[Unit]
    else:
        _unit = Devices[Unit]

    return _unit.SwitchType, _unit.SubType, _unit.Type


def _is_meter_widget(self, Devices, DeviceID_, Unit_):
    if DOMOTICZ_EXTENDED_API:
        device = Devices.get(DeviceID_)
        unit = device.Units[Unit_] if device and Unit_ in device.Units else None
    else:
        unit = Devices.get(Unit_)

    if unit:
        return (
            unit.SwitchType == 0
            and unit.SubType == 29
            and unit.Type == 243
        )
    return False


def _is_device_tobe_switched_off(self, Devices, DeviceID_, Unit_):
    self.log.logging("AbstractDz", "Debug", f"is_device_tobe_switched_off: {DeviceID_} {Unit_}")
    
    if DOMOTICZ_EXTENDED_API:
        unit = Devices.get(DeviceID_).Units.get(Unit_) if Devices.get(DeviceID_) else None
    else:
        unit = Devices.get(Unit_)

    if unit:
        return (
            (unit.Type == 244 and unit.SubType == 73 and unit.SwitchType == 7) 
            or (unit.Type == 241 and unit.SwitchType == 7)
        )
    return False


def device_touch_api(self, Devices, DeviceId_):
    """Touch all Devices Widgets"""
    self.log.logging("AbstractDz", "Debug", f"device_touch_api: {DeviceId_}")

    now = time.time()
    if DOMOTICZ_EXTENDED_API:
        if DeviceId_ in Devices:
            units = Devices[DeviceId_].Units
            for unit in list(units):
                _device_touch_unit_api(self, Devices, DeviceId_, unit, now)

    else:
        for unit in list(Devices):
            if Devices[ unit ].DeviceID == DeviceId_:
                _device_touch_unit_api(self, Devices, DeviceId_, unit, now)


def _device_touch_unit_api(self, Devices, DeviceId_, Unit_, now):
    """ Touch one widget for a particular Device """
    self.log.logging("AbstractDz", "Debug", f"device_touch_unit_api: {DeviceId_} {Unit_}")

    # In case of Meter Device (kWh), we must not touch it, otherwise it will destroy the metering
    # Type, Subtype, SwitchType 
    # 243|29|0
    if _sanity_check_device_unit(self, Devices, DeviceId_, Unit_):
        return
    
    if _is_meter_widget(self, Devices, DeviceId_, Unit_):
        return

    last_time = (
        Devices[DeviceId_].Units[Unit_].LastUpdate
        if DOMOTICZ_EXTENDED_API
        else Devices[Unit_].LastUpdate
    )

    last_update_time_seconds = time.mktime(time.strptime(last_time, "%Y-%m-%d %H:%M:%S"))

    if now > ( last_update_time_seconds + DELAY_BETWEEN_TOUCH):
        # Last Touch was done more than 30 seconds ago.
        Devices[DeviceId_].Units[Unit_].Touch() if DOMOTICZ_EXTENDED_API else Devices[Unit_].Touch()
        return
    

def timeout_widget_api(self, Devices, DeviceId_, timeout_value):
    """ TimedOut all Device Widgets """
    self.log.logging("AbstractDz", "Debug", f"timeout_widget_api: {DeviceId_}")
    
    if DOMOTICZ_EXTENDED_API:
        Devices[ DeviceId_].TimedOut = timeout_value
        if timeout_value == 1 and self.pluginconf.pluginConf["deviceOffWhenTimeOut"]:
            # Then we will switch off as per User setting
            for unit in Devices[ DeviceId_].Units:
                _switch_off_widget_due_to_timedout(self, Devices, DeviceId_, unit)
    else:
        for unit in list(Devices):
            if Devices[ unit ].DeviceID == DeviceId_:
                timeout_legacy_device_unit_api(self, Devices, DeviceId_, unit, timeout_value)


def timeout_legacy_device_unit_api(self, Devices, DeviceId_, Unit_, timeout_value):
    """ TimedOut one Device widget """

    self.log.logging("AbstractDz", "Debug", f"timeout_legacy_device_unit_api: {DeviceId_} {Unit_} {timeout_value}")
    if _is_meter_widget( self, Devices, DeviceId_, Unit_):
        return

    _nValue, _sValue = domo_read_nValue_sValue(self, Devices, DeviceId_, Unit_)
    _TimedOut = domo_read_legacy_TimedOut( self, Devices, DeviceId_, Unit_ )
    _Name = domo_read_Name( self, Devices, DeviceId_, Unit_, )

    self.log.logging("Widget", "Debug", "timeout_legacy_device_unit_api unit %s -> %s from %s:%s %s" % (
        _Name, bool(timeout_value), _nValue, _sValue, bool(_TimedOut)))

    if _TimedOut == timeout_value:
        return

    # Update is required
    if timeout_value == 1 and self.pluginconf.pluginConf["deviceOffWhenTimeOut"]:
        _switch_off_widget_due_to_timedout(self, Devices, DeviceId_, Unit_, _nValue, _sValue,)
    else:
        domo_update_api(self, Devices, DeviceId_, Unit_, _nValue, _sValue, TimedOut=timeout_value)


def update_battery_api(self, Devices, DeviceId, battery_level):
    self.log.logging( ["AbstractDz", "BatteryManagement"], "Debug", f"update_battery_api: {DeviceId} to {battery_level}")
          
    if DOMOTICZ_EXTENDED_API:
        if DeviceId in Devices:
            units = Devices[DeviceId].Units
            for unit in units:
                update_battery_device_unit_api(self, Devices, DeviceId, unit,battery_level)
    else:
        for unit in list(Devices):
            if Devices[ unit ].DeviceID == DeviceId:
                update_battery_device_unit_api(self, Devices, DeviceId, unit,battery_level)
  
        
def update_battery_device_unit_api(self, Devices, DeviceId_, Unit_, battery_level):
    self.log.logging("AbstractDz", "Debug", f"update_battery_device_unit_api: {DeviceId_} / {Unit_} to {battery_level}")
    if domo_read_BatteryLevel( self, Devices, DeviceId_, Unit_, ) == battery_level:
        return

    nValue, sValue = domo_read_nValue_sValue(self, Devices, DeviceId_, Unit_)
    
    domo_update_api(self, Devices, DeviceId_, Unit_, nValue, sValue, BatteryLevel=battery_level,SuppressTriggers=True)        


def _switch_off_widget_due_to_timedout(self, Devices, DevicesId, Unit, _nValue, _sValue,):
    self.log.logging("Widget", "Debug", f"_switch_off_widget_due_to_timedout DeviceId {DevicesId} unit {Unit}")
    
    if (_nValue == 1 and _sValue == "On") or _is_device_tobe_switched_off(self, Devices, DevicesId, Unit):
        domo_update_api(self, Devices, DevicesId, Unit, 0, "Off", TimedOut=1)
    else:
        domo_update_api(self, Devices, DevicesId, Unit, _nValue, _sValue, TimedOut=1)
        
    
def domoticz_log_api( message):
    Domoticz.Log( message )


def domoticz_error_api( message):
    Domoticz.Error( message )


def domoticz_status_api( message):
    Domoticz.Status( message )


def is_dimmable_switch(self, Devices, DeviceId, Unit):
    _switchType, _subType, _type = domo_read_SwitchType_SubType_Type(self, Devices, DeviceId, Unit)
    if check_widget(_switchType, _subType, _type) == "Dimmable_Switch":
        return find_partially_opened_nValue(_switchType, _subType, _type)
    return None
    
    
def is_dimmable_light(self, Devices, DeviceId, Unit):
    _switchType, _subType, _type = domo_read_SwitchType_SubType_Type(self, Devices, DeviceId, Unit)
    if check_widget(_switchType, _subType, _type) == "Dimmable_Light":
        return find_partially_opened_nValue(_switchType, _subType, _type)
    return None
        
    
def is_dimmable_blind(self, Devices, DeviceId, Unit):
    _switchType, _subType, _type = domo_read_SwitchType_SubType_Type(self, Devices, DeviceId, Unit)
    if check_widget(_switchType, _subType, _type) == "Blind":
        return find_partially_opened_nValue(_switchType, _subType, _type)
    return None


def find_partially_opened_nValue(switch_type, sub_type, widget_type):
    key = (switch_type, sub_type, widget_type)
    return DIMMABLE_WIDGETS.get(key,{}).get("partially_opened_nValue")


def check_widget(switch_type, sub_type, widget_type):
    key = (switch_type, sub_type, widget_type)
    return DIMMABLE_WIDGETS.get(key,{}).get("Widget")


def _sanity_check_device_unit(self, Devices, device_ieee, unit):
    """ check that device_ieee, unit exist in Domoticz Db"""
    return (
        (DOMOTICZ_EXTENDED_API and (device_ieee not in Devices or unit not in Devices[device_ieee].Units))
        or (not DOMOTICZ_EXTENDED_API and unit not in Devices)
    )
