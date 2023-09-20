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
    
    self.ListOfDomoticzWidget = {}
    for x in list(Devices):
        if DOMOTICZ_EXTENDED_API:
            for y in list(Devices[x].Units):
                self.log.logging( "AbstractDz", "Debug", "Loading Devices[%s].Units[%s]: %s" % (
                    x, y, Devices[x].Units[y].Name) )
        else:
            self.ListOfDomoticzWidget[ Devices[x].ID ] = {
                "Name": Devices[x].Name,
                "Unit": x,
                "DeviceID": Devices[x].DeviceID,
                "Switchtype": Devices[x].SwitchType,
                "Subtype": Devices[x].SubType,
            }
            self.log.logging( "AbstractDz", "Debug", "Loading Devices[%s]: %s" % (
                Devices[x].ID,str(self.ListOfDomoticzWidget[ Devices[x].ID] )) )



def find_widget_unit(self, Devices, WidgetID ):
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
                if Devices[x].Units[y].ID == int(WidgetID):
                    return ( x, y )
                
        elif Devices[x].ID == int(WidgetID):
            return x
    return None


def domo_create_api(self, Devices, DeviceID_, Unit_, Name_, widgetType=None, Type=None, Type_=None, Subtype_=None, Switchtype_=None, widgetOptions=None, Image=None, ForceClusterType=None):
    # Should be used in domoCreate
    # to substitute the Create() and Unit() calls
    
    self.log.logging( "AbstractDz", "Debug","domo_create_api(Name: %s, DeviceID: %s, Unit: %s, Type: %s, Subtype: %s, Switchtype: %s, Option: %s)" %(
        Name_, DeviceID_, Unit_, Type_, Subtype_, Switchtype_, widgetOptions ))
    
    if DOMOTICZ_EXTENDED_API:
        # Extended API
        # TO DO
        self.log.logging( "AbstractDz", "Error", "domo_create_api() Extended Framework Not IMPLEMENTED")
    else:
        # Legacy API
        if widgetType:
            # We only base the creation on widgetType
            myDev = Domoticz.Device(DeviceID=DeviceID_, Name=Name_, Unit=Unit_, TypeName=widgetType)

        elif widgetOptions:
            # In case of widgetOptions, we have a Selector widget
            if Type_ is None and Subtype_ is None and Switchtype_ is None:
                Type_ = 244
                Subtype_ = 62
                Switchtype_ = 18
            myDev = Domoticz.Device( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_, Options=widgetOptions, )
        elif Image:
            myDev = Domoticz.Device( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_, Image=Image )
        elif Switchtype_:
            myDev = Domoticz.Device( DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_ )
        else:
            myDev = Domoticz.Device(DeviceID=DeviceID_, Name=Name_, Unit=Unit_, Type=Type_, Subtype=Subtype_)

        myDev.Create()
        return myDev.ID