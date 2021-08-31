#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Class: AdminWidget.py

    Description: Manage the Admistration Widget available on Domoticz

"""

import Domoticz
from datetime import datetime

DEVICEID_ADMIN_WIDGET = "Zigate-01-"
DEVICEID_STATUS_WIDGET = "Zigate-02-"
DEVICEID_TXT_WIDGET = "Zigate-03-"
DEVICEID_ADMIN_WIDGET_TXT = "Zigate Administration"
DEVICEID_STATUS_WIDGET_TXT = "Zigate Status"
DEVICEID_TXT_WIDGET_TXT = "Zigate Notifications"


class AdminWidgets:
    def __init__(self, PluginConf, Devices, ListOfDevices, HardwareID):

        self.pluginconf = PluginConf
        self.Devices = Devices  # Point to the List of Domoticz Devices
        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.HardwareID = HardwareID
        self.createStatusWidget(Devices)
        self.createNotificationWidget(Devices)
        # createAdminWidget( self, Devices )

    def FreeUnit(self, Devices):
        """
        FreeUnit
        Look for a Free Unit number.
        """
        for x in range(1, 255):
            if x not in Devices:
                return x
        else:
            return len(Devices) + 1

    def createAdminWidget(self, Devices):

        deviceid_admin_widget = DEVICEID_ADMIN_WIDGET + "%02s" % self.HardwareID
        unit = 0
        for x in Devices:
            if Devices[x].DeviceID == deviceid_admin_widget:
                unit = x
                break
        if unit != 0:
            return

        if self.pluginconf.pluginConf["eraseZigatePDM"]:
            Options = {
                "LevelActions": "|||||||",
                "LevelNames": "Off|Purge Reports|Soft Reset|One Time Enrollment|Perm. Enrollment|Interf Scan|LQI Report|Erase PDM",
                "LevelOffHidden": "true",
                "SelectorStyle": "0",
            }
        else:
            Options = {
                "LevelActions": "|||||||",
                "LevelNames": "Off|Purge Reports|Soft Reset|One Time Enrolmennt|Perm. Enrollment|Interf Scan|LQI Report",
                "LevelOffHidden": "true",
                "SelectorStyle": "0",
            }

        unit = self.FreeUnit(Devices)
        widget_name = DEVICEID_ADMIN_WIDGET_TXT + " %02s" % self.HardwareID
        myDev = Domoticz.Device(
            DeviceID=deviceid_admin_widget,
            Name=widget_name,
            Unit=unit,
            Type=244,
            Subtype=62,
            Switchtype=18,
            Options=Options,
        )
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1:
            Domoticz.Error("createAdminWidget - Fail to create %s. %s" % (widget_name, str(myDev)))
        return

    def createStatusWidget(self, Devices):

        deviceid_status_widget = DEVICEID_STATUS_WIDGET + "%02s" % self.HardwareID
        unit = 0
        for x in Devices:
            if Devices[x].DeviceID == deviceid_status_widget:
                unit = x
                break
        if unit != 0:
            return

        unit = self.FreeUnit(Devices)
        widget_name = DEVICEID_STATUS_WIDGET_TXT + " %02s" % self.HardwareID
        myDev = Domoticz.Device(
            DeviceID=deviceid_status_widget, Name=widget_name, Unit=unit, Type=243, Subtype=22, Switchtype=0
        )
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1:
            Domoticz.Error("createAdminWidget - Fail to create %s. %s" % (widget_name, str(myDev)))
            return

        self.updateStatusWidget(Devices, "Off")
        return

    def createNotificationWidget(self, Devices):

        deviceid_txt_widget = DEVICEID_TXT_WIDGET + "%02s" % self.HardwareID
        unit = 0
        for x in Devices:
            if Devices[x].DeviceID == deviceid_txt_widget:
                unit = x
                break
        if unit != 0:
            return

        unit = self.FreeUnit(Devices)
        widget_name = DEVICEID_TXT_WIDGET_TXT + " %02s" % self.HardwareID
        myDev = Domoticz.Device(
            DeviceID=deviceid_txt_widget, Name=widget_name, Unit=unit, Type=243, Subtype=19, Switchtype=0
        )
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1:
            Domoticz.Error("createNotificationWidget - Fail to create %s. %s" % (widget_name, str(myDev)))
            return

        return

    def handleAdminWidget(self, Devices, Unit, Command, Color):

        # 10 - Zigate soft Reset
        # 20 - Erase PDM
        # 30 - Pairing a new Object ( We will open the pairing for 5'
        # 40 - Paring for ever
        # 50 - NetworkScan
        # 60 - LQI Report

        return

    def updateStatusWidget(self, Devices, statusType):

        STATUS_WIDGET = {"No Communication": 4, "Startup": 0, "Ready": 1, "Enrollment": 3, "Busy": 3}

        deviceid_status_widget = DEVICEID_STATUS_WIDGET + "%02s" % self.HardwareID
        if statusType not in STATUS_WIDGET:
            return

        unit = 0
        for x in Devices:
            if Devices[x].DeviceID == deviceid_status_widget:
                unit = x
                break
        if unit == 0:
            return

        nValue = STATUS_WIDGET[statusType]
        sValue = str(statusType)
        if sValue != Devices[unit].sValue:
            Devices[unit].Update(nValue=nValue, sValue=sValue)

        return

    def updateNotificationWidget(self, Devices, notification):

        deviceid_txt_widget = DEVICEID_TXT_WIDGET + "%02s" % self.HardwareID
        unit = 0
        for x in Devices:
            if Devices[x].DeviceID == deviceid_txt_widget:
                unit = x
                break
        if unit == 0:
            return

        nValue = 0
        sValue = str(notification)
        if sValue != Devices[unit].sValue:
            Devices[unit].Update(nValue=nValue, sValue=sValue)

    def handleCommand(self, Command):

        return
