#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_adminWidget.py

    Description: Manage the Admistration Widget available on Domoticz

"""

import Domoticz

DEVICEID_ADMIN_WIDGET = 'Zigate-01-'
DEVICEID_STATUS_WIDGET = 'Zigate-02-'
DEVICEID_TEXT_WIDGET = 'Zigate-03-'
DEVICEID_ADMIN_WIDGET_TXT = 'Zigate Administration'
DEVICEID_STATUS_WIDGET_TXT = 'Zigate Status'
DEVICEID_TEXT_WIDGET_TXT = 'Zigate Notifications'

def FreeUnit(self, Devices):
    '''
    FreeUnit
    Look for a Free Unit number.
    '''
    FreeUnit = ""
    for x in range(1, 255):
        if x not in Devices:
            Domoticz.Debug("FreeUnit - device " + str(x) + " available")
            return x
    else:
        Domoticz.Debug("FreeUnit - device " + str(len(Devices) + 1))
        return len(Devices) + 1

def createAdminWidget( self, Devices ):

    deviceid_admin_widget = DEVICEID_ADMIN_WIDGET + "%02s" %self.HardwareID
    unit = 0
    for x in Devices:
        if Devices[x].DeviceID == deviceid_admin_widget:
            unit = x
            break
    if unit != 0:
        return

    Options = {"LevelActions": "||||||",
               "LevelNames": "Off|Reset|Erase PDM|Pairing Object|Join for Ever|Interf Scan|LQI Report",
               "LevelOffHidden": "true", "SelectorStyle": "0"}
    unit = FreeUnit(self, Devices)
    widget_name = DEVICEID_ADMIN_WIDGET_TXT_01 + " %02s" %self.HardwareID
    myDev = Domoticz.Device(DeviceID=deviceid_admin_widget, Name=widget_name,
                    Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1 :
        Domoticz.Error("createAdminWidget - Fail to create %s. %s" %(widget_name, str(myDev)))
    return

def createStatusWidget( self, Devices ):

    deviceid_status_widget = DEVICEID_STATUS_WIDGET + "%02s" %self.HardwareID
    unit = 0
    for x in Devices:
        if Devices[x].DeviceID == deviceid_status_widget:
            unit = x
            break
    if unit != 0:
        return
        #Devices[unit].Delete()

    #Options = {"LevelActions": "||",
    #           "LevelNames": "Off|Startup|Ready|Enrolment|Busy",
    #           "LevelOffHidden": "true", "SelectorStyle": "1"}
    unit = FreeUnit(self, Devices)
    widget_name = DEVICEID_STATUS_WIDGET_TXT + " %02s" %self.HardwareID
    myDev = Domoticz.Device(DeviceID=deviceid_status_widget, Name=widget_name,
                    Unit=unit, Type=243, Subtype=22, Switchtype=0)
    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1 :
        Domoticz.Error("createAdminWidget - Fail to create %s. %s" %(widget_name, str(myDev)))
        return

    updateStatusWidget( self, Devices,  'Off' )
    return

def handleAdminWidget( self, Devices, Unit, Command , Color ):


    # 10 - Zigate soft Reset

    # 20 - Erase PDM

    # 30 - Pairing a new Object ( We will open the pairing for 5'

    # 40 - Paring for ever

    # 50 - NetworkScan

    # 60 - LQI Report

    return


def updateStatusWidget( self, Devices,  statusType ):


    STATUS_WIDGET = { 'Off':4, 
            'Startup':0, 
            'Ready':1, 
            'Enrolment':3, 
            'Busy':3 }

    deviceid_status_widget = DEVICEID_STATUS_WIDGET + "%02s" %self.HardwareID
    if statusType not in STATUS_WIDGET:
        return

    unit = 0
    for x in Devices:
        if Devices[x].DeviceID == deviceid_status_widget:
            unit = x
            break
    if unit == 0: 
        Domoticz.Log("updateStatusWidget - didn't find the Widget: %s" %deviceid_status_widget)
        return

    nValue = STATUS_WIDGET[statusType]
    sValue = str(statusType)
    if sValue != Devices[unit].sValue:
        Domoticz.Debug("updateStatusWidget - %s nValue: %s, sValue: %s/%s" 
                %(Devices[unit].DeviceID, nValue, sValue, Devices[unit].sValue))
        Devices[unit].Update( nValue =nValue , sValue=sValue)

    return
