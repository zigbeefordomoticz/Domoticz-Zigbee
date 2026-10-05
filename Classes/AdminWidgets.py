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
    retreive_free_unit_for_widget, domo_create_api, domo_read_nValue_sValue, domo_update_api,
    domoticz_debug_api, domoticz_error_api, domoticz_log_api,
    find_first_unit_widget_from_deviceID, is_device_ieee_in_domoticz_db)

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

# Admin widgets the plugin creates for itself, and the method that (re)creates one.
ADMIN_WIDGET_STATUS = "Status"
ADMIN_WIDGET_NOTIFICATIONS = "Notifications"

ADMIN_WIDGET_CREATORS = {
    ADMIN_WIDGET_STATUS: "createStatusWidget",
    ADMIN_WIDGET_NOTIFICATIONS: "createNotificationWidget",
}

# How many times the heartbeat comes back to an admin widget Domoticz refused to
# create. Kept in step with Modules/domoCreate.py: WIDGET_CREATION_MAX_RETRIES - a
# refusal that two retries apart has not cleared is a Domoticz-side setting, and no
# number of further attempts will change it.
ADMIN_WIDGET_MAX_RETRIES = 2

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

        # Admin widgets Domoticz refused to create, {widget key: retries spent so far}.
        # A refusal is invisible to us - Domoticz.Unit().Create() neither raises nor
        # returns a reason, it only logs one on its own side - so the only evidence is
        # the unit being absent afterwards, and the only way back is to try again.
        self.failed_admin_widgets: Dict[str, int] = {}

        self.createStatusWidget(Devices)
        self.createNotificationWidget(Devices)


    def _resolve_deviceid(
        self,
        Devices: Dict[int, Any],
        legacy_prefix: str,
        z4d_prefix: str,
    ) -> Tuple[Optional[str], Optional[int]]:

        #domoticz_log_api("_resolve_deviceid called with legacy_prefix=%s, z4d_prefix=%s" % (legacy_prefix, z4d_prefix)) 
        suffix_padded = f"{self.HardwareID:02d}"
        suffix_raw = "%02s" %self.HardwareID

        legacy_ids = [
            legacy_prefix + suffix_padded,
            legacy_prefix + suffix_raw,
        ]

        # Search for legacy name at 1st
        for legacy_id in legacy_ids:
            #domoticz_log_api("_resolve_deviceid checking legacy_id: %s" % legacy_id)
            if is_device_ieee_in_domoticz_db(self, Devices, legacy_id):
                #domoticz_log_api("_resolve_deviceid found legacy_id: %s" % legacy_id)
                unit = find_first_unit_widget_from_deviceID(self, Devices, legacy_id)
                if unit is not None:
                    return legacy_id, unit

        # If not found let look for new 
        z4d_id = z4d_prefix + suffix_padded

        #domoticz_log_api("_resolve_deviceid checking z4d_id: %s" % z4d_id)
        if is_device_ieee_in_domoticz_db(self, Devices, z4d_id):
            #domoticz_log_api("_resolve_deviceid found z4d_id: %s" % z4d_id)
            unit = find_first_unit_widget_from_deviceID(self, Devices, z4d_id)

            if unit:
                return z4d_id, unit

        return None, None
   
    # ----------------------------------------------------------------------
    # Widget Creation
    # ----------------------------------------------------------------------
    def createAdminWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Administration selector widget if missing.
        """
        #domoticz_log_api("createAdminWidget.")
        
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_ADMIN_WIDGET,
            Z4D_DEVICEID_ADMIN_WIDGET,
        )
        #domoticz_log_api("createAdminWidget - _resolve_deviceid returned: deviceid=%s, unit=%s" % (deviceid, unit))
        
        if unit:
            return  # already exists under one of the two naming conventions
        
        new_deviceid = Z4D_DEVICEID_ADMIN_WIDGET + f"{self.HardwareID:02d}"
        widget_name = Z4D_DEVICEID_ADMIN_WIDGET_TXT + f" {self.HardwareID:02d}"
        free_unit = retreive_free_unit_for_widget(self, Devices, new_deviceid, nbunit_=1)
        
        #domoticz_log_api("createAdminWidget - Creating new widget: %s"% new_deviceid)

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
            return None, None

        return new_deviceid, free_unit


    def createStatusWidget(self, Devices: Dict[int, Any]) -> None:
        """
        Create the Status widget (243.22).
        """
        #domoticz_log_api("createStatusWidget.")
        
        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_STATUS_WIDGET,
            Z4D_DEVICEID_STATUS_WIDGET,
        )
        #domoticz_log_api("createStatusWidget - _resolve_deviceid returned: deviceid=%s, unit=%s" % (deviceid, unit))   
        if unit:
            self._admin_widget_created(ADMIN_WIDGET_STATUS)
            return

        new_deviceid = Z4D_DEVICEID_STATUS_WIDGET + f"{self.HardwareID:02d}"
        widget_name = Z4D_DEVICEID_STATUS_WIDGET_TXT + f" {self.HardwareID:02d}"
        free_unit = retreive_free_unit_for_widget(self, Devices, new_deviceid, nbunit_=1)

        #domoticz_log_api("createStatusWidget - Creating new widget: %s" % new_deviceid)

        ID: int = domo_create_api(
            self, Devices, new_deviceid, free_unit, widget_name,
            Type_=243, Subtype_=22, Switchtype_=0, log_refusal=False,
        )
        if ID == WIDGET_CREATION_FAILED:
            self._admin_widget_creation_failed(
                ADMIN_WIDGET_STATUS, widget_name, new_deviceid, free_unit, Devices)
            return None, None

        self._admin_widget_created(ADMIN_WIDGET_STATUS)
        self.updateStatusWidget(Devices, "Startup")
        return new_deviceid, free_unit


    def createNotificationWidget(self, Devices: Dict[int, Any]) -> None:
        """Create the Notification text widget (Type 243.19) if it does not already exist."""
        #domoticz_log_api("createNotificationWidget.")

        deviceid, unit = self._resolve_deviceid(
            Devices,
            DEVICEID_TXT_WIDGET,
            Z4D_DEVICEID_TXT_WIDGET,
        )
        #domoticz_log_api("createNotificationWidget - _resolve_deviceid returned: deviceid=%s, unit=%s" % (deviceid, unit)) 
        if unit:
            self._admin_widget_created(ADMIN_WIDGET_NOTIFICATIONS)
            return

        new_deviceid = Z4D_DEVICEID_TXT_WIDGET + f"{self.HardwareID:02d}"
        widget_name = Z4D_DEVICEID_TXT_WIDGET_TXT + f" {self.HardwareID:02d}"
        free_unit = retreive_free_unit_for_widget(self, Devices, new_deviceid, nbunit_=1)

        #domoticz_log_api("createNotificationWidget - Creating new widget: %s" % new_deviceid)
        ID: int = domo_create_api(
            self, Devices, new_deviceid, free_unit, widget_name,
            Type_=243, Subtype_=19, Switchtype_=0, log_refusal=False,
        )
        if ID == WIDGET_CREATION_FAILED:
            self._admin_widget_creation_failed(
                ADMIN_WIDGET_NOTIFICATIONS, widget_name, new_deviceid, free_unit, Devices)
            return None, None

        self._admin_widget_created(ADMIN_WIDGET_NOTIFICATIONS)
        return new_deviceid, free_unit


    # ----------------------------------------------------------------------
    # Recovery from a refused admin-widget creation
    # ----------------------------------------------------------------------
    def _admin_widget_creation_failed(
        self,
        widget_key: str,
        widget_name: str,
        deviceid: str,
        unit: Optional[int],
        Devices: Dict[int, Any],
    ) -> None:
        """Remember a refused admin widget, and report it once per plugin start.

        This is the only error logged for the refusal: domo_create_api() is called
        with log_refusal=False, because what it can say - that a unit is absent
        after a creation that did not raise - is of no use to the person reading
        the log, while which admin widget was lost and what to do about it is.
        Its Domoticz-side view is carried over into the context below.

        Logged only on the first failure: the retries would otherwise reprint the
        same error every 5 minutes.
        """
        already_known = widget_key in self.failed_admin_widgets
        self.failed_admin_widgets.setdefault(widget_key, 0)

        if already_known:
            return

        self.log.logging(
            "WidgetCreation", "Error",
            "Domoticz refused to create the Z4D %s admin widget (%s). The reason is in "
            "the Domoticz log and not here; the usual one is that Domoticz is not "
            "allowed to accept new devices - see Setup, Settings, System, 'Accept new "
            "Hardware Devices'. The plugin will try again %s times, every 5 minutes."
            % (widget_key, widget_name, ADMIN_WIDGET_MAX_RETRIES),
            None,
            {
                "Reason": "Domoticz refused the admin widget creation",
                "AdminWidget": widget_key,
                "Request": {"DeviceID": deviceid, "Unit": unit, "Name": widget_name},
                "Domoticz": {
                    "device_known": deviceid in Devices if Devices is not None else None,
                    "total_devices": len(Devices) if Devices is not None else None,
                },
                "HardwareID": self.HardwareID,
                "MaxRetries": ADMIN_WIDGET_MAX_RETRIES,
            },
        )


    def _admin_widget_created(self, widget_key: str) -> None:
        """Clear a widget from the retry list, and say so if it had been failing."""
        if self.failed_admin_widgets.pop(widget_key, None) is None:
            return

        self.log.logging(
            "WidgetCreation", "Status",
            "The Z4D %s admin widget has been created - Domoticz is accepting new "
            "devices again." % widget_key)


    def retry_failed_admin_widget_creation(self, Devices: Dict[int, Any]) -> None:
        """Try again on the admin widgets Domoticz refused to create.

        Called from the heartbeat (Modules/heartbeat.py: processListOfDevices), which
        is the thread Domoticz calls the plugin on - the only thread the Domoticz
        plugin API may be used from. Without this, the Status and Notifications
        widgets stay missing for the whole session even once Domoticz is willing
        again, because they are only ever created from AdminWidgets.__init__, itself
        called once from onStart.

        Only the budget is decided here; the cadence is the caller's.
        """
        for widget_key in list(self.failed_admin_widgets):
            retries = self.failed_admin_widgets[widget_key]
            if retries >= ADMIN_WIDGET_MAX_RETRIES:
                continue

            self.failed_admin_widgets[widget_key] = retries + 1
            self.log.logging(
                "WidgetCreation", "Debug",
                "retry_failed_admin_widget_creation - %s, attempt %s of %s" % (
                    widget_key, retries + 1, ADMIN_WIDGET_MAX_RETRIES))

            getattr(self, ADMIN_WIDGET_CREATORS[widget_key])(Devices)

            if self.failed_admin_widgets.get(widget_key, 0) < ADMIN_WIDGET_MAX_RETRIES:
                # Either created - the creator dropped it from the list - or there is
                # still a retry left in the budget.
                continue

            self.log.logging(
                "WidgetCreation", "Error",
                "Giving up on the Z4D %s admin widget after %s attempts; the plugin "
                "will not try again this session. Fix the cause reported in the "
                "Domoticz log - most often Setup, Settings, System, 'Accept new "
                "Hardware Devices' - then restart the plugin."
                % (widget_key, ADMIN_WIDGET_MAX_RETRIES),
                None,
                {
                    "Reason": "admin widget retry budget exhausted",
                    "AdminWidget": widget_key,
                    "HardwareID": self.HardwareID,
                    "Attempts": ADMIN_WIDGET_MAX_RETRIES,
                },
            )


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
        if not unit and not deviceid:
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
