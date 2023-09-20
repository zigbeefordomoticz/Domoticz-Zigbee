#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: domoAbstractLayer.py
    Description: Set of functions which abstract Domoticz Legacy and Extended framework API
"""

import Domoticz
DOMOTICZ_EXTENDED_API = False

def load_list_of_domoticz_widget(self, Devices):

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
    # Should be used in domoMaj, when looking for the 'DeviceUnit'
    # In legacy 'DeviceUnit' will be a Number, while in Extended, it will be a Tupple of DeviceID and Unit
    
    self.log.logging( "AbstractDz", "Debug", "find_widget_unit - WidgetId: %s (%s)" % (WidgetID, type(WidgetID)))
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
    # If DeviceId is None, then we are in Legacy mode
    if DeviceId is None:
        return sum(x not in Devices for x in range( 1, 255 ))
    
    if DeviceId in Devices:
        # Look for how many entries left for this specific DeviceID ( IEEE )
        return sum( y not in Devices[ DeviceId ].Units[ y ] for y in range(1, 255) )
    
    return None


def FreeUnit(self, Devices, DeviceId, nbunit_=1):
    """
    FreeUnit
    Look for a Free Unit number. If nbunit > 1 then we look for nbunit consecutive slots
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
    # Should be used in domoCreate
    # to substitute the Create() and Unit() calls
    
    # Create the device
    self.log.logging("AbstractDz", "Debug", "domo_create_api DeviceID: %s,Name: %s,Unit: %s,TypeName: %s,Type: %s,Subtype: %s,Switchtype: %s,Image: %s" %(
        DeviceID_, Name_, Unit_, widgetType, Type_, Subtype_, Switchtype_, Image,))

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
        myDev = domoticz_device_api_class( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_ )
               
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
