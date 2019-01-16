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
DEVICEID_TXT_WIDGET = 'Zigate-03-'
DEVICEID_ADMIN_WIDGET_TXT = 'Zigate Administration'
DEVICEID_STATUS_WIDGET_TXT = 'Zigate Status'
DEVICEID_TXT_WIDGET_TXT = 'Zigate Notifications'

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


def initializeZigateWidgets( self, Devices ):

    createStatusWidget( self, Devices)
    createNotificationWidget( self, Devices)
    # createAdminWidget( self, Devices )
    return

def createAdminWidget( self, Devices ):

    deviceid_admin_widget = DEVICEID_ADMIN_WIDGET + "%02s" %self.HardwareID
    unit = 0
    for x in Devices:
        if Devices[x].DeviceID == deviceid_admin_widget:
            unit = x
            break
    if unit != 0:
        return

    if self.pluginconf.eraseZigatePDM:
        Options = {"LevelActions": "|||||||",
               "LevelNames": "Off|Purge Reports|Soft Reset|One Time Enrollment|Perm. Enrollment|Interf Scan|LQI Report|Erase PDM",
               "LevelOffHidden": "true", "SelectorStyle": "0"}
    else:
        Options = {"LevelActions": "|||||||",
               "LevelNames": "Off|Purge Reports|Soft Reset|One Time Enrolmennt|Perm. Enrollment|Interf Scan|LQI Report",
               "LevelOffHidden": "true", "SelectorStyle": "0"}

    unit = FreeUnit(self, Devices)
    widget_name = DEVICEID_ADMIN_WIDGET_TXT+ " %02s" %self.HardwareID
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
            Domoticz.Log("createStatusWidget - existing %s -> %s" %(x, Devices[x].DeviceID))
            break
    if unit != 0:
        return
        #Devices[unit].Delete()

    #Options = {"LevelActions": "||",
    #           "LevelNames": "Off|Startup|Ready|Enrollment|Busy",
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

def createNotificationWidget( self, Devices ):

    deviceid_txt_widget = DEVICEID_TXT_WIDGET + "%02s" %self.HardwareID
    unit = 0
    for x in Devices:
        if Devices[x].DeviceID == deviceid_txt_widget:
            unit = x
            Domoticz.Log("createNotificationWidget - existing %s -> %s" %(x, Devices[x].DeviceID))
            break
    if unit != 0:
        return

    unit = FreeUnit(self, Devices)
    widget_name = DEVICEID_TXT_WIDGET_TXT + " %02s" %self.HardwareID
    myDev = Domoticz.Device(DeviceID=deviceid_txt_widget, Name=widget_name,
                    Unit=unit, Type=243, Subtype=19, Switchtype=0)
    myDev.Create()
    ID = myDev.ID
    if myDev.ID == -1 :
        Domoticz.Error("createNotificationWidget - Fail to create %s. %s" %(widget_name, str(myDev)))
        return

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

    STATUS_WIDGET = { 'No Communication':4, 
            'Startup':0, 
            'Ready':1, 
            'Enrollment':3, 
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
        Domoticz.Log("updateNotificationWidget - didn't find the Widget: %s" %deviceid_status_widget)
        return

    nValue = STATUS_WIDGET[statusType]
    sValue = str(statusType)
    if sValue != Devices[unit].sValue:
        Domoticz.Debug("updateNotificationWidget - %s nValue: %s, sValue: %s/%s" 
                %(Devices[unit].DeviceID, nValue, sValue, Devices[unit].sValue))
        Devices[unit].Update( nValue =nValue , sValue=sValue)

    return

def updateNotificationWidget( self, Devices, notification ):

    deviceid_txt_widget = DEVICEID_TXT_WIDGET + "%02s" %self.HardwareID
    unit = 0
    for x in Devices:
        if Devices[x].DeviceID == deviceid_txt_widget:
            unit = x
            break
    if unit == 0:
        Domoticz.Log("updateNotificationWidget - didn't find the Widget: %s" %deviceid_txt_widget)
        return

    nValue = 0
    sValue = str(notification)
    if sValue != Devices[unit].sValue:
        Domoticz.Debug("updateNotificationWidget - %s nValue: %s, sValue: %s/%s"
                %(Devices[unit].DeviceID, nValue, sValue, Devices[unit].sValue))
        Devices[unit].Update( nValue =nValue , sValue=sValue)


def handleCommand( self, Command):

    if Command == '00':
        pass

    elif Command == '10':
        Domoticz.Log("handleCommand - Purge reports")

    elif Command == '20':
        Domoticz.Log("handleCommand - Soft Reset")

    elif Command == '30':
        Domoticz.Log("handleCommand - One Time Enrolmennt")

    elif Command == '40':
        Domoticz.Log("handleCommand - Perm. Enrollment")

    elif Command == '50':
        Domoticz.Log("handleCommand - Interference Scan")

    elif Command == '60':
        Domoticz.Log("handleCommand - LQI Report")

    elif Command == '70':
        Domoticz.Log("handleCommand - Erase Permanent Memory")
        if self.pluginconf.eraseZigatePDM:
            pass

