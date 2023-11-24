#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: domoAbstractLayer.py
    Description: Set of functions which abstract Domoticz Legacy and Extended framework API
"""

import time

import Domoticz

DOMOTICZ_EXTENDED_API = False

DELAY_BETWEEN_TOUCH = 30

def load_list_of_domoticz_widget(self, Devices):
    """Use at plugin start to creat an index of Domoticz Widget. It is also called after a Widget removal and when a new device has been paired.

    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework
    """

    for x in list(Devices):
        if DOMOTICZ_EXTENDED_API:
            for y in list(Devices[x].Units):
                self.log.logging( "AbstractDz", "Debug", "Loading Devices[%s].Units[%s]: %s" % (
                    x, y, Devices[x].Units[y].Name) )
                self.ListOfDomoticzWidget[ x ] = {
                    "Name": Devices[x].Units[y].Name,
                    "Unit": y,
                    "DeviceID": Devices[x].Units[y].DeviceID,
                    "Switchtype": Devices[x].Units[y].SwitchType,
                    "Subtype": Devices[x].Units[y].SubType,
                }
        else:
            # Legacy
            self.ListOfDomoticzWidget[ Devices[x].ID ] = {
                "Name": Devices[x].Name,
                "Unit": x,
                "DeviceID": Devices[x].DeviceID,
                "Switchtype": Devices[x].SwitchType,
                "Subtype": Devices[x].SubType,
            }

        self.log.logging( "AbstractDz", "Debug", "Loading Devices[%s]: %s" % (
            Devices[x].ID,str(self.ListOfDomoticzWidget[ Devices[x].ID] )) )


def find_widget_unit_from_WidgetID(self, Devices, WidgetID ):
    """Find the Widget Unit with Legay framework, the tuple ( DeviceID, Unit ) with the Extended Framework

    Args:
        Devices (dict): Devices dictionary provided by the Domoticz framework
        WidgetID (str): Domoticz Widget Idx, usally store in the "ClusterType" attribute associated to each Ep
        Should be used in domoMaj, when looking for the 'DeviceUnit'

    Returns:
        _type_: Widget Unit with Legay framework, the tuple ( DeviceID, Unit ) with the Extended Framework
        In legacy 'DeviceUnit' will be a Number, while in Extended, it will be a Tupple of DeviceID and Unit
        
    """
    
    #self.log.logging( "AbstractDz", "Debug", "find_widget_unit - WidgetId: %s (%s)" % (WidgetID, type(WidgetID)))
    WidgetID = int(WidgetID)
    if WidgetID in self.ListOfDomoticzWidget:
        self.log.logging( "AbstractDz", "Debug", "- Found in ListOfDomoticzWidget" )
        if DOMOTICZ_EXTENDED_API:
            # TO-DO
            self.log.logging( "AbstractDz", "Error", "find_widget_unit() Extended Framework Not IMPLEMENTED")
            return None
        
        else:
            #Legacy
            self.log.logging( "AbstractDz", "Debug", "- returning %s (%s)" %(
                self.ListOfDomoticzWidget[WidgetID]['Unit'], type(self.ListOfDomoticzWidget[WidgetID]['Unit'])))
            return self.ListOfDomoticzWidget[WidgetID]['Unit'] 

    self.log.logging( "AbstractDz", "Log", "- Not Found in ListOfDomoticzWidget, looking the old way" )
    # In case it is not found with the new way, let's keep the old way 
    # TO-DO: Remove
    
    for x in list(Devices):
        if DOMOTICZ_EXTENDED_API:
            for y in list(Devices[x].Units):
                if Devices[x].Units[y].ID == WidgetID:
                    return ( x, y )
                
        elif Devices[x].ID == WidgetID:
            return x
    return None


def how_many_slot_available( Devices, DeviceId=None):
    """Return the number of unit slot available

    Args:
        Devices (dictionary): Devices dictionary provided by the Domoticz framework
        DeviceId (str, optional): DeviceID (ieee). Defaults to None (means Legacy framework)

    Returns:
        int: number of available unit slot
    """
    # If DeviceId is None, then we are in Legacy mode
    if DeviceId is None:
        return sum(x not in Devices for x in range( 1, 255 ))
    
    if DeviceId in Devices:
        # Look for how many entries left for this specific DeviceID ( IEEE )
        return sum( y not in Devices[ DeviceId ].Units[ y ] for y in range(1, 255) )
    
    return None


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
        available_units = set(Devices[DeviceId].Units.keys())
        return _free_unit_in_device( available_units, nbunit_ )
    
    # Legacy framework
    available_units = set(Devices.keys())
    _log_message(len(available_units) + 1)
    return _free_unit_in_device( available_units, nbunit_ )


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
        myDev = domoticz_device_api_class( 
            DeviceID=DeviceID_, 
            Name=Name_, 
            Unit=Unit_, 
            Type=Type_, 
            Subtype=Subtype_, 
            Switchtype=Switchtype_,
            Options=widgetOptions,)
               
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
    return myDev.ID


def domo_update_api(self, Devices, DeviceID_, Unit_, nValue, sValue, SignalLevel=None, BatteryLevel=None, TimedOut=None, Color="",):
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
    self.log.logging("AbstractDz", "Debug", "domo_update_api: %s %s %s %s %s %s %s %s" %(
        DeviceID_, Unit_, nValue, sValue, SignalLevel, BatteryLevel, TimedOut, Color))

    if DOMOTICZ_EXTENDED_API:
        Devices[DeviceID_].Units[Unit_].nValue = nValue
        Devices[DeviceID_].Units[Unit_].sValue = sValue

        if Color != "":
            Devices[DeviceID_].Units[Unit_].Color = Color
            Devices[DeviceID_].Units[Unit_].TimedOut = 0
        if BatteryLevel is not None:
            Devices[DeviceID_].Units[Unit_].BatteryLevel = BatteryLevel
            Devices[DeviceID_].Units[Unit_].TimedOut = 0
        if SignalLevel is not None:
            Devices[DeviceID_].Units[Unit_].SignalLevel = SignalLevel
            Devices[DeviceID_].Units[Unit_].TimedOut = 0
        if TimedOut is not None:
            Devices[DeviceID_].Units[Unit_].TimedOut = TimedOut
                 
        Devices[DeviceID_].Units[Unit_].Update(Log=True)
        return

    # Legacy
    if TimedOut:
        Devices[Unit_].Update(nValue=nValue, sValue=sValue, TimedOut=TimedOut,)

    elif SignalLevel is None and BatteryLevel is None:
        Devices[Unit_].Update(nValue=nValue, sValue=sValue, TimedOut=0,)
        
    elif Color != "":
        Devices[Unit_].Update( nValue=int(nValue), sValue=str(sValue), Color=Color, SignalLevel=int(SignalLevel), BatteryLevel=int(BatteryLevel), TimedOut=0, )

    else:
        Devices[Unit_].Update( nValue=int(nValue), sValue=str(sValue), SignalLevel=int(SignalLevel), BatteryLevel=int(BatteryLevel), TimedOut=0, )


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

    if DOMOTICZ_EXTENDED_API:
        _unit = Devices[DeviceID].Units[Unit]
    else:
        _unit = Devices[Unit]

    return _unit.nValue, _unit.sValue


def domo_read_SwitchType_SubType_Type(self, Devices, DeviceID, Unit):
    if DOMOTICZ_EXTENDED_API:
        _unit = Devices[DeviceID].Units[Unit]
    else:
        _unit = Devices[Unit]

    return _unit.SwitchType, _unit.SubType, _unit.Type


def _is_meter_widget( self, Devices,DeviceID_, Unit_):
    # self.log.logging("AbstractDz", "Debug", "_is_meter_widget: %s %s" %(DeviceID_, Unit_))
    if DOMOTICZ_EXTENDED_API:
        return (
            Devices[DeviceID_].Units[Unit_].SwitchType == 0
            and Devices[DeviceID_].Units[Unit_].SubType == 29
            and Devices[DeviceID_].Units[Unit_].Type == 243
        )
    return (
        Devices[Unit_].SwitchType == 0
        and Devices[Unit_].SubType == 29
        and Devices[Unit_].Type == 243
    )


def _is_device_tobe_switched_off(self, Devices,DeviceID_, Unit_):
    self.log.logging("AbstractDz", "Debug", "is_device_tobe_switched_off: %s %s" %(DeviceID_, Unit_))
    if DOMOTICZ_EXTENDED_API:
        return (
            (Devices[DeviceID_].Units[Unit_].Type == 244 and Devices[DeviceID_].Units[Unit_].SubType == 73 and Devices[DeviceID_].Units[Unit_].SwitchType == 7) 
            or (Devices[DeviceID_].Units[Unit_].Type == 241 and Devices[DeviceID_].Units[Unit_].SwitchType == 7)
        )
    return (
        (Devices[Unit_].Type == 244 and Devices[Unit_].SubType == 73 and Devices[Unit_].SwitchType == 7)
        or (Devices[Unit_].Type == 241 and Devices[Unit_].SwitchType == 7)
    )


def device_touch_api(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug", f"device_touch: {DeviceId_} {Unit_}")

    # In case of Meter Device (kWh), we must not touch it, otherwise it will destroy the metering
    # Type, Subtype, SwitchType 
    # 243|29|0

    if _is_meter_widget(self, Devices, DeviceId_, Unit_):
        return

    last_time = (
        Devices[DeviceId_].Units[Unit_].LastUpdate
        if DOMOTICZ_EXTENDED_API
        else Devices[Unit_].LastUpdate
    )

    last_update_time_seconds = time.mktime(time.strptime(last_time, "%Y-%m-%d %H:%M:%S"))

    if time.time() > last_update_time_seconds + DELAY_BETWEEN_TOUCH:
        # Last Touch was done more than 30 seconds ago.
        Devices[DeviceId_].Units[Unit_].Touch() if DOMOTICZ_EXTENDED_API else Devices[Unit_].Touch()
        return
    self.log.logging("AbstractDz", "Debug", f"device_touch too early: {DeviceId_} {Unit_}")
    

def timeout_widget_api(self, Devices, DeviceId_, Unit_, timeout_value):
    if _is_meter_widget( self, Devices, DeviceId_, Unit_):
        return
    
    if DOMOTICZ_EXTENDED_API:
        _nValue = Devices[DeviceId_].Units[Unit_].nValue
        _sValue = Devices[DeviceId_].Units[Unit_].sValue
        _TimedOut = Devices[DeviceId_].Units[Unit_].TimedOut
    else:
        _nValue = Devices[Unit_].nValue
        _sValue = Devices[Unit_].sValue
        _TimedOut = Devices[Unit_].TimedOut
    
    self.log.logging("Widget", "Debug", "timeout_widget unit %s -> %s from %s:%s %s" % (
        Devices[Unit_].Name, bool(timeout_value), _nValue, _sValue, Devices[Unit_].TimedOut))
    
    if _TimedOut != timeout_value:
        # Update is required
        if (
            timeout_value == 1
            and self.pluginconf.pluginConf["deviceOffWhenTimeOut"]
            and ( (_nValue == 1 and _sValue == "On") or _is_device_tobe_switched_off(self, Devices,DeviceId_, Unit_) )
        ):
            # Then we will switch off as per User setting
            domo_update_api(self, Devices, DeviceId_, Unit_, 0, "Off", TimedOut=timeout_value)
        else:
            domo_update_api(self, Devices, DeviceId_, Unit_, _nValue, _sValue, TimedOut=timeout_value)
    self.log.logging("Widget", "Debug", "timeout_widget DeviceId %s unit %s -> %s completed" % (DeviceId_, Unit_, bool(timeout_value)))
