#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier: GPL-3.0

"""
AdminWidget.py — Handles the creation and update of the Domoticz administration,
status, and notification widgets used by the Zigbee for Domoticz plugin.
"""

from typing import Any, Dict, Optional

from Modules.domoticzAbstractLayer import (
    FreeUnit,
    domo_create_api,
    domo_read_nValue_sValue,
    domo_update_api,
    domoticz_error_api,
    find_first_unit_widget_from_deviceID,
)

# Domoticz Widget identifiers for legacy Zigate* and new Z4D* conventions
DEVICEID_ADMIN_WIDGET = "Zigate-01-"
DEVICEID_STATUS_WIDGET = "Zigate-02-"
DEVICEID_TXT_WIDGET = "Zigate-03-"
DEVICEID_ADMIN_WIDGET_TXT = "Zigate Administration"
DEVICEID_STATUS_WIDGET_TXT = "Zigate Status"
DEVICEID_TXT_WIDGET_TXT = "Zigate Notifications"

Z4D_DEVICEID_ADMIN_WIDGET = "Z4D-01-"
Z4D_DEVICEID_STATUS_WIDGET = "Z4D-02-"
Z4D_DEVICEID_TXT_WIDGET = "Z4D-03-"
Z4D_DEVICEID_ADMIN_WIDGET_TXT = "Z4D Administration"
Z4D_DEVICEID_STATUS_WIDGET_TXT = "Z4D Status"
Z4D_DEVICEID_TXT_WIDGET_TXT = "Z4D Notifications"


def _get_switch_selector_options(self) -> Dict[str, str]:
    """
    Build the selector switch options for the Administration widget.

    Returns:
        dict: Configuration dictionary for Domoticz selector switch.
    """
    base: Dict[str, str] = {
        "LevelActions": "|||||||",
        "LevelNames": (
            "Off|Purge Reports|Soft Reset|One Time Enrollment|"
            "Perm. Enrollment|Interf Scan|LQI Report"
        ),
        "LevelOffHidden": "true",
        "SelectorStyle": "0",
    }

    if self.pluginconf.pluginConf.get("eraseZigatePDM"):
        base["LevelNames"] += "|Erase PDM"

    return base


class AdminWidgets:
    """
    Manage Domoticz Zigbee administrative widgets.

    This class creates and updates:
      - The Administration Selector Widget (reset, pairing, scans)
      - The Status Widget (Ready, Busy, Enrollment, etc.)
      - The Notification Widget (text messages)

    Args:
        log: Logger instance.
        PluginConf: Plugin configuration object.
        pluginParameters: General plugin parameters.
        ListOfDomoticzWidget: Domoticz widget registry.
        Devices: Domoticz devices table.
        ListOfDevices: Global Zigbee device table.
        HardwareID: Internal Zigbee hardware identifier.
        IEEE2NWK: Mapping of IEEE → NWK addresses.
    """

    def __init__(
        self,
        log: Any,
        PluginConf: Any,
        pluginParameters: Dict[str, Any],
        ListOfDomoticzWidget: Any,
        Devices: Dict[int, Any],
        ListOfDevices: Dict[str, Any],
        HardwareID: int,
        IEEE2NWK: Dict[str, str],
    ) -> None:

        self.pluginconf = PluginConf
        self.pluginParameters = pluginParameters
        self.ListOfDomoticzWidget = ListOfDomoticzWidget
        self.Devices = Devices
        self.ListOfDevices = ListOfDevices
        self.HardwareID = HardwareID
        self.IEEE2NWK = IEEE2NWK
        self.log = log

        self.createStatusWidget(Devices)
        self.createNotificationWidget(Devices)

    # ----------------------------------------------------------------------
    # Widget Creation
    # ----------------------------------------------------------------------

    def createAdminWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Administration selector widget if missing.
        """
        deviceid = DEVICEID_ADMIN_WIDGET + f"{self.HardwareID:02d}"
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid):
            return

        deviceid = Z4D_DEVICEID_ADMIN_WIDGET + f"{self.HardwareID:02d}"
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid):
            return

        widget_name = Z4D_DEVICEID_ADMIN_WIDGET_TXT + f" {self.HardwareID:02d}"
        unit = FreeUnit(self, Devices, deviceid, nbunit_=1)

        ID: int = domo_create_api(
            self,
            Devices,
            deviceid,
            unit,
            widget_name,
            Type_=244,
            Subtype_=62,
            Switchtype_=18,
            widgetOptions=_get_switch_selector_options(self),
        )

        if ID == -1:
            domoticz_error_api(f"createAdminWidget - Failed to create {widget_name}.")

    def createStatusWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Status widget (243.22).
        """
        deviceid = DEVICEID_STATUS_WIDGET + f"{self.HardwareID:02d}"
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid):
            return

        deviceid = Z4D_DEVICEID_STATUS_WIDGET + f"{self.HardwareID:02d}"
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid):
            return

        unit = FreeUnit(self, Devices, deviceid, nbunit_=1)
        widget_name = Z4D_DEVICEID_STATUS_WIDGET_TXT + f" {self.HardwareID:02d}"

        ID: int = domo_create_api(
            self, Devices, deviceid, unit, widget_name, Type_=243, Subtype_=22, Switchtype_=0
        )

        if ID == -1:
            domoticz_error_api(f"createStatusWidget - Failed to create {widget_name}.")
            return

        self.updateStatusWidget(Devices, "Off")

    def createNotificationWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Notification text widget (243.19).
        """
        deviceid = DEVICEID_TXT_WIDGET + f"{self.HardwareID:02d}"
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid):
            return

        deviceid = Z4D_DEVICEID_TXT_WIDGET + f"{self.HardwareID:02d}"
        if find_first_unit_widget_from_deviceID(self, Devices, deviceid):
            return

        unit = FreeUnit(self, Devices, deviceid, nbunit_=1)
        widget_name = Z4D_DEVICEID_TXT_WIDGET_TXT + f" {self.HardwareID:02d}"

        ID: int = domo_create_api(
            self, Devices, deviceid, unit, widget_name, Type_=243, Subtype_=19, Switchtype_=0
        )

        if ID == -1:
            domoticz_error_api(f"createNotificationWidget - Failed to create {widget_name}.")

    # ----------------------------------------------------------------------
    # Widget Updates
    # ----------------------------------------------------------------------

    def updateStatusWidget(self, Devices: Dict[int, Any], statusType: str) -> None:
        """
        Update the Status widget.

        Args:
            statusType: One of:
                "No Communication", "Startup", "Ready", "Enrollment", "Busy"
        """
        STATUS_MAP: Dict[str, int] = {
            "No Communication": 4,
            "Startup": 0,
            "Ready": 1,
            "Enrollment": 3,
            "Busy": 3,
        }

        if statusType not in STATUS_MAP:
            return

        deviceid = DEVICEID_STATUS_WIDGET + f"{self.HardwareID:02d}"
        unit: Optional[int] = find_first_unit_widget_from_deviceID(self, Devices, deviceid)

        if not unit:
            deviceid = Z4D_DEVICEID_STATUS_WIDGET + f"{self.HardwareID:02d}"
            unit = find_first_unit_widget_from_deviceID(self, Devices, deviceid)

        if not unit:
            return

        # Read current value
        _, current = domo_read_nValue_sValue(self, Devices, deviceid, unit)

        new_sValue = statusType
        new_nValue = STATUS_MAP[statusType]

        if new_sValue != current:
            domo_update_api(self, Devices, deviceid, unit, new_nValue, new_sValue)

    def updateNotificationWidget(self, Devices: Dict[int, Any], notification: str) -> None:
        """
        Update the Notification widget text.
        """
        deviceid = DEVICEID_TXT_WIDGET + f"{self.HardwareID:02d}"
        unit: Optional[int] = find_first_unit_widget_from_deviceID(self, Devices, deviceid)

        if not unit:
            deviceid = Z4D_DEVICEID_TXT_WIDGET + f"{self.HardwareID:02d}"
            unit = find_first_unit_widget_from_deviceID(self, Devices, deviceid)

        if not unit:
            return

        _, current = domo_read_nValue_sValue(self, Devices, deviceid, unit)
        new_sValue = notification

        if new_sValue != current:
            domo_update_api(self, Devices, deviceid, unit, 0, new_sValue)

    # ----------------------------------------------------------------------
    # Command Handling
    # ----------------------------------------------------------------------

    def handleAdminWidget(
        self,
        Devices: Dict[int, Any],
        Unit: int,
        Command: str,
        Color: Any,
    ) -> None:
        """
        Handle selector switch commands for the Administration widget.
        Currently a placeholder.

        Args:
            Devices: Domoticz devices.
            Unit: Unit number of the widget.
            Command: Selector value or string command.
            Color: Unused parameter (kept for API consistency).
        """
        return

    def handleCommand(self, Command: str) -> None:
        """
        Placeholder for generic incoming command handling.
        """
        return
