#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
AdminWidget.py — Handles the creation and update of the Domoticz administration,
status, and notification widgets used by the Zigbee for Domoticz plugin.
"""

from typing import Any, Dict, Optional, Tuple

from Modules.domoticzAbstractLayer import (
    FreeUnit, domo_create_api, domo_read_nValue_sValue, domo_update_api,
    domoticz_debug_api, domoticz_error_api, domoticz_log_api,
    find_first_unit_widget_from_deviceID)

# Widget device-ID prefixes — legacy Zigate* and new Z4D* conventions
DEVICEID_ADMIN_WIDGET = "Zigate-01-"
DEVICEID_STATUS_WIDGET = "Zigate-02-"
DEVICEID_TXT_WIDGET = "Zigate-03-"

Z4D_DEVICEID_ADMIN_WIDGET = "Z4D-01-"
Z4D_DEVICEID_STATUS_WIDGET = "Z4D-02-"
Z4D_DEVICEID_TXT_WIDGET = "Z4D-03-"

Z4D_DEVICEID_ADMIN_WIDGET_TXT = "Z4D Administration"
Z4D_DEVICEID_STATUS_WIDGET_TXT = "Z4D Status"
Z4D_DEVICEID_TXT_WIDGET_TXT = "Z4D Notifications"


ADMIN_WIDGET_PREFIXES = {
    DEVICEID_ADMIN_WIDGET,
    DEVICEID_STATUS_WIDGET,
    DEVICEID_TXT_WIDGET,
    Z4D_DEVICEID_ADMIN_WIDGET,
    Z4D_DEVICEID_STATUS_WIDGET,
    Z4D_DEVICEID_TXT_WIDGET,
}

# Status widget nValue mapping — defined once at module level
_STATUS_MAP: Dict[str, int] = {
    "No Communication": 4,
    "Startup": 0,
    "Ready": 1,
    "Enrollment": 3,
    "Busy": 3,
    "Off": 0
}

WIDGET_CREATION_FAILED = -1

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


    def _resolve_deviceid(
        self,
        Devices: Dict[int, Any],
        legacy_prefix: str,
        z4d_prefix: str,
    ) -> Tuple[Optional[str], Optional[int]]:


        suffix_padded = f"{self.HardwareID:02d}"
        suffix_raw = "%02s" %self.HardwareID

        legacy_ids = [
            legacy_prefix + suffix_padded,
            legacy_prefix + suffix_raw,
        ]

        # Search for legacy name at 1st
        for legacy_id in legacy_ids:
            domoticz_log_api(f"Trying legacy_id={legacy_id}")
            unit = find_first_unit_widget_from_deviceID(self, Devices, legacy_id)
            if unit is not None:
                domoticz_log_api(f"_resolve_deviceid: Result for legacy_id={legacy_id} -> unit={unit}")
                return legacy_id, unit

        # If not found let look for new 
        z4d_id = z4d_prefix + suffix_padded
        domoticz_log_api(f"_resolve_deviceid: Trying z4d_id={z4d_id}")

        unit = find_first_unit_widget_from_deviceID(self, Devices, z4d_id)
        domoticz_log_api(f"_resolve_deviceid: Result for z4d_id={z4d_id} -> unit={unit}")

        if unit:
            domoticz_log_api(f"_resolve_deviceid: FOUND via z4d_id={z4d_id}, unit={unit}")
            return z4d_id, unit

        domoticz_log_api(
            f"_resolve_deviceid: NOT FOUND (legacy_id={legacy_id}, z4d_id={z4d_id})"
        )

        return None, None
   
    # ----------------------------------------------------------------------
    # Widget Creation
    # ----------------------------------------------------------------------
    def createAdminWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Administration selector widget if missing.
        """
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_ADMIN_WIDGET,
            Z4D_DEVICEID_ADMIN_WIDGET,
        )
        if unit:
            return  # already exists under one of the two naming conventions
        
        new_deviceid = Z4D_DEVICEID_ADMIN_WIDGET + f"{self.HardwareID:02d}"
        widget_name = Z4D_DEVICEID_ADMIN_WIDGET_TXT + f" {self.HardwareID:02d}"
        free_unit = FreeUnit(self, Devices, new_deviceid, nbunit_=1)

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

        if ID == WIDGET_CREATION_FAILED:
            domoticz_error_api(f"createAdminWidget - Failed to create {widget_name}.")


    def createStatusWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Status widget (243.22).
        """
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_STATUS_WIDGET,
            Z4D_DEVICEID_STATUS_WIDGET,
        )
        if unit:
            return

        new_deviceid = Z4D_DEVICEID_STATUS_WIDGET + f"{self.HardwareID:02d}"
        widget_name = Z4D_DEVICEID_STATUS_WIDGET_TXT + f" {self.HardwareID:02d}"
        free_unit = FreeUnit(self, Devices, new_deviceid, nbunit_=1)

        ID: int = domo_create_api(
            self, Devices, new_deviceid, free_unit, widget_name,
            Type_=243, Subtype_=22, Switchtype_=0,
        )
        if ID == WIDGET_CREATION_FAILED:
            domoticz_error_api(f"createStatusWidget - Failed to create {widget_name}.")
            return

        self.updateStatusWidget(Devices, "Startup")


    def createNotificationWidget(self, Devices: Dict[int, Any]) -> None:
        """Create the Notification text widget (Type 243.19) if it does not already exist."""
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_TXT_WIDGET,
            Z4D_DEVICEID_TXT_WIDGET,
        )
        if unit:
            return

        new_deviceid = Z4D_DEVICEID_TXT_WIDGET + f"{self.HardwareID:02d}"
        widget_name = Z4D_DEVICEID_TXT_WIDGET_TXT + f" {self.HardwareID:02d}"
        free_unit = FreeUnit(self, Devices, new_deviceid, nbunit_=1)

        ID: int = domo_create_api(
            self, Devices, new_deviceid, free_unit, widget_name,
            Type_=243, Subtype_=19, Switchtype_=0,
        )
        if ID == WIDGET_CREATION_FAILED:
            domoticz_error_api(f"createNotificationWidget - Failed to create {widget_name}.")


    def updateStatusWidget(self, Devices: Dict[int, Any], statusType: str) -> None:
        """
        Update the Status widget.

        Args:
            statusType: One of:
                "No Communication", "Startup", "Ready", "Enrollment", "Busy"
        """

        if statusType not in _STATUS_MAP:
            return
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_STATUS_WIDGET,
            Z4D_DEVICEID_STATUS_WIDGET,
        )
        if not unit:
            return

        _, current = domo_read_nValue_sValue(self, Devices, deviceid, unit)

        if statusType != current:
            domo_update_api(self, Devices, deviceid, unit, _STATUS_MAP[statusType], statusType)


    def updateNotificationWidget(self, Devices: Dict[int, Any], notification: str) -> None:
        """
        Update the Notification widget text.
        """
        """Update the Notification widget text."""
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_TXT_WIDGET,
            Z4D_DEVICEID_TXT_WIDGET,
        )
        if not unit:
            return

        _, current = domo_read_nValue_sValue(self, Devices, deviceid, unit)

        if notification != current:
            domo_update_api(self, Devices, deviceid, unit, 0, notification)


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
        domoticz_debug_api( f"handleAdminWidget called: Command={Command}")
        return


    def handleCommand(self, Command: str) -> None:
        """
        Placeholder for generic incoming command handling.
        """
        domoticz_debug_api( f"handleCommand called: Command={Command}")
        return
