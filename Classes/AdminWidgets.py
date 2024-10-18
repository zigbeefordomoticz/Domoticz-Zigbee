#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Class: AdminWidget.py

    Description: Manage the Admistration Widget available on Domoticz

"""

from Modules.domoticzAbstractLayer import (
    FreeUnit, domo_create_api, domo_read_nValue_sValue, domo_update_api,
    domoticz_error_api, find_first_unit_widget_from_deviceID)

DEVICEID_ADMIN_WIDGET = "Zigate-01-"
DEVICEID_STATUS_WIDGET = "Zigate-02-"
DEVICEID_TXT_WIDGET = "Zigate-03-"
DEVICEID_ADMIN_WIDGET_TXT = "Zigate Administration"
DEVICEID_STATUS_WIDGET_TXT = "Zigate Status"
DEVICEID_TXT_WIDGET_TXT = "Zigate Notifications"


def _get_switch_selector_options(self, ):
    if self.pluginconf.pluginConf["eraseZigatePDM"]:
        return {
            "LevelActions": "|||||||",
            "LevelNames": "Off|Purge Reports|Soft Reset|One Time Enrollment|Perm. Enrollment|Interf Scan|LQI Report|Erase PDM",
            "LevelOffHidden": "true",
            "SelectorStyle": "0",
        }
        
    return {
            "LevelActions": "|||||||",
            "LevelNames": "Off|Purge Reports|Soft Reset|One Time Enrolmennt|Perm. Enrollment|Interf Scan|LQI Report",
            "LevelOffHidden": "true",
            "SelectorStyle": "0",
        }

class AdminWidgets:
    def __init__(self, log, PluginConf, pluginParameters, ListOfDomoticzWidget, Devices, ListOfDevices, HardwareID, IEEE2NWK):

        self.pluginconf = PluginConf
        self.pluginParameters = pluginParameters
        self.ListOfDomoticzWidget = ListOfDomoticzWidget
        self.Devices = Devices  # Point to the List of Domoticz Devices
        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.HardwareID = HardwareID
        self.IEEE2NWK = IEEE2NWK
        self.log = log 
        self.createStatusWidget(Devices)
        self.createNotificationWidget(Devices)
        # createAdminWidget( self, Devices )

    def createAdminWidget(self, Devices):

        deviceid_admin_widget = DEVICEID_ADMIN_WIDGET + "%02s" % self.HardwareID

        if find_first_unit_widget_from_deviceID(self, Devices, deviceid_admin_widget ):
            return

        widget_name = DEVICEID_ADMIN_WIDGET_TXT + " %02s" % self.HardwareID
        unit = FreeUnit(self, Devices, deviceid_admin_widget, nbunit_=1)
        ID = domo_create_api(self, Devices, deviceid_admin_widget, unit, widget_name, Type_=244, Subtype_=62, Switchtype_=18, widgetOptions=_get_switch_selector_options(self))
        if ID == -1:
            domoticz_error_api("createAdminWidget - Fail to create %s." % (widget_name))
        return

    def createStatusWidget(self, Devices):

        deviceid_status_widget = DEVICEID_STATUS_WIDGET + "%02s" % self.HardwareID

        if find_first_unit_widget_from_deviceID(self, Devices, deviceid_status_widget):
            return

        unit = FreeUnit(self, Devices, deviceid_status_widget, nbunit_=1)
        widget_name = DEVICEID_STATUS_WIDGET_TXT + " %02s" % self.HardwareID
        ID = domo_create_api(self, Devices, deviceid_status_widget, unit, widget_name, Type_=243, Subtype_=22, Switchtype_=0,)
        
        if ID == -1:
            domoticz_error_api("createAdminWidget - Fail to create %s." % (widget_name))
            return

        self.updateStatusWidget(Devices, "Off")
        return

    def createNotificationWidget(self, Devices):

        deviceid_txt_widget = DEVICEID_TXT_WIDGET + "%02s" % self.HardwareID
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid_txt_widget ):
            return

        unit = FreeUnit(self, Devices, deviceid_txt_widget, nbunit_=1)
        widget_name = DEVICEID_TXT_WIDGET_TXT + " %02s" % self.HardwareID
        ID = domo_create_api(self, Devices, deviceid_txt_widget, unit, widget_name, Type_=243, Subtype_=19, Switchtype_=0,)
        if ID == -1:
            domoticz_error_api("createNotificationWidget - Fail to create %s." % (widget_name))
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

        unit = find_first_unit_widget_from_deviceID(self, Devices, deviceid_status_widget )
        if not unit:
            return

        nValue = STATUS_WIDGET[statusType]
        sValue = str(statusType)
        
        _, cur_svalue = domo_read_nValue_sValue(self, Devices, deviceid_status_widget, unit)
        
        if sValue != cur_svalue:
            domo_update_api(self, Devices, deviceid_status_widget, unit, nValue, sValue)

        return

    def updateNotificationWidget(self, Devices, notification):
        deviceid_txt_widget = DEVICEID_TXT_WIDGET + "%02s" % self.HardwareID
        unit = find_first_unit_widget_from_deviceID(self, Devices, deviceid_txt_widget )
        if not unit:
            return

        _, cur_svalue = domo_read_nValue_sValue(self, Devices, deviceid_txt_widget, unit)

        sValue = str(notification)
        if sValue != cur_svalue:
            domo_update_api(self, Devices, deviceid_txt_widget, unit, 0, sValue)

    def handleCommand(self, Command):
        return


