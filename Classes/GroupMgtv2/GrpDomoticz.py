#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import json

from Classes.GroupMgtv2.GrpCommands import (set_hue_saturation,
                                            set_kelvin_color, set_rgb_color)
from Classes.GroupMgtv2.GrpDatabase import update_due_to_nwk_id_change
from Modules.domoticzAbstractLayer import (
    domo_create_api, domo_delete_widget, domo_read_Name,
    domo_read_nValue_sValue, domo_read_SwitchType_SubType_Type,
    domo_update_api, domo_update_name, domo_update_SwitchType_SubType_Type,
    find_first_unit_widget_from_deviceID)
from Modules.tools import (Hex_Format, get_deviceconf_parameter_value,
                           is_domoticz_latest_typename, is_hex)
from Modules.zigateConsts import ADDRESS_MODE, LEGRAND_REMOTES, ZIGATE_EP
from Zigbee.zclCommands import (zcl_group_level_move_to_level,
                                zcl_group_move_to_level_stop,
                                zcl_group_move_to_level_with_onoff,
                                zcl_group_onoff_off_noeffect,
                                zcl_group_onoff_off_witheffect,
                                zcl_group_onoff_on,
                                zcl_group_window_covering_level,
                                zcl_group_window_covering_off,
                                zcl_group_window_covering_on,
                                zcl_group_window_covering_stop)

WIDGET_STYLE = {
    "Plug": (244, 73, 0),
    "Switch": (244, 73, 0),
    "LvlControl": (244, 73, 7),
    "BlindPercentInverted": (244, 73, 13),
    "BlindPercent": (244, 73, 13),
    "WindowCovering": (244, 73, 13),
    "Venetian": (244, 73, 15),
    "VenetianInverted": (244, 73, 15),
    "ColorControlWW": (241, 8, 7),
    "ColorControlRGB": (241, 2, 7),
    "ColorControlRGBWW": (241, 4, 7),
    "ColorControlFull": (241, 7, 7),
}

WIDGET_STYLE_TO_DOMOTICZ_TYPEMAP = {
    "Plug": "On/Off",
    "Switch": "On/Off",
    "LvlControl": "Dimmer",
    "BlindPercentInverted": "BlindsPercentage",
    "WindowCovering": "VenetianBlindsEU",
    "Venetian": "VenetianBlindsEU",
    "VenetianInverted": "VenetianBlindsEU",
    "ColorControlWW": "CW_WW",
    "ColorControlRGB": "RGB",
    "ColorControlRGBWW": "RGB_CW_WW",
    "ColorControlFull": "RGB_CW_WW_Z",

}

CLUSTER_MAPPING = {
    "Switch": "0006",
    "Plug": "0006",
    "LvlControl": "0008",
    "ColorControlWW": "0300",
    "ColorControlRGB": "0300",
    "ColorControlRGBWW": "0300",
    "ColorControl": "0300",
    "ColorControlFull": "0300",
    "Venetian": "0102",
    "WindowCovering": "0102",
    "VenetianInverted": "0102",
}

from dataclasses import dataclass


@dataclass
class GroupAccumulator:
    """Aggregates per-device state while iterating over the devices of a group."""

    # On/Off counters
    count_on: int = 0
    count_off: int = 0
    count_stop: int = 0

    # Level (dimmers) — running sum + count, raw Zigbee 0–255
    level_sum: int = 0
    level_count: int = 0

    # Covering (shutters/blinds) — running sum + count, normalized 0–100
    covering_sum: int = 0
    covering_count: int = 0

    def add_on_off(self, on_off):
        if on_off == 17:
            self.count_stop += 1
        elif on_off is not None and on_off != 0:
            self.count_on += 1
        elif on_off == 0:
            self.count_off += 1

    def add_level(self, raw_level):
        self.level_sum += raw_level
        self.level_count += 1

    def add_covering(self, pct):
        self.covering_sum += pct
        self.covering_count += 1

    @property
    def has_covering(self):
        return self.covering_count > 0

    @property
    def level(self):
        """Average level (0–255) or None if no dimmer contributed."""
        return round(self.level_sum / self.level_count) if self.level_count else None

    @property
    def covering(self):
        """Average covering position (0–100) or None if no cover contributed."""
        return round(self.covering_sum / self.covering_count) if self.covering_count else None
    @property
    def is_empty(self):
        """True if no device contributed any usable state."""
        return (
            self.count_on == 0
            and self.count_off == 0
            and self.count_stop == 0
            and self.level_count == 0
            and self.covering_count == 0
        )

DEFAULT_GROUP_UNIT = 1  # As of 8.1.003, DomoticzEx, all groups will be using Unit 1 at creation (only legacy will rely on Unit)

def create_domoticz_group_device(self, GroupName, GroupId):
    """ Create Device for just created group in Domoticz. """
    
    self.logging("Debug", f"createDomoticzGroupDevice - {GroupName}, {GroupId}")

    if GroupName == "" or GroupId == "":
        self.logging( "Error", "createDomoticzGroupDevice - Invalid Group Name: %s or GroupdID: %s" % (GroupName, GroupId) )
        return

    if find_first_unit_widget_from_deviceID(self, self.Devices, GroupId):
        self.logging( "Log", f"createDomoticzGroupDevice - {GroupId} exists alreday in Domoticz"  )
        return

    Type_, Subtype_, SwitchType_ = best_group_widget(self, GroupId)
    self.ListOfGroups[GroupId]['TypeName'] = get_typename(self, Type_, Subtype_, SwitchType_)

    idx = domo_create_api(self, self.Devices, GroupId, DEFAULT_GROUP_UNIT, GroupName, Type_=Type_, Subtype_=Subtype_, Switchtype_=SwitchType_, widgetOptions=None, Image=None)
    self.logging("Debug", "createDomoticzGroupDevice - Unit: %s" % DEFAULT_GROUP_UNIT)
    if idx == -1:
        self.logging("Error", f"createDomoticzGroupDevice - failed to create Group device. {GroupName} with unit {DEFAULT_GROUP_UNIT}")
        return

    self.ListOfGroups[GroupId]["WidgetType"] = idx


def LookForGroupAndCreateIfNeeded(self, GroupId):
    self.logging( "Debug", f"LookForGroupAndCreateIfNeeded - '{GroupId}'")
    if GroupId not in self.ListOfGroups:
        return

    if find_first_unit_widget_from_deviceID(self, self.Devices, GroupId):
        # Group Exist and has a valid unit
        update_domoticz_group_device_widget(self, GroupId)
        return

    if "GroupName" not in self.ListOfGroups[GroupId]:
        self.ListOfGroups[GroupId]["GroupName"] = "Zigate Group %s" % GroupId

    GroupName = self.ListOfGroups[GroupId]["GroupName"]
    create_domoticz_group_device(self, GroupName, GroupId)
    update_domoticz_group_device_widget(self, GroupId)


def update_domoticz_group_device_widget_name(self, GroupName, GroupId):

    self.logging( "Debug", f"update_domoticz_group_device_widget_name - '{GroupName}' '{GroupId}'")

    if GroupName == "" or GroupId == "":
        self.logging( "Error", "update_domoticz_group_device_widget_name - Invalid Group Name: %s or GroupdID: %s" % (GroupName, GroupId), )
        return

    unit = find_first_unit_widget_from_deviceID(self, self.Devices, GroupId)
    if unit is None:
        self.logging( "Debug", f"update_domoticz_group_device_widget_name - no unit found for GroupId {GroupId} - {self.ListOfGroups[GroupId]}" )
        LookForGroupAndCreateIfNeeded(self, GroupId)
        return

    domo_update_name(self, self.Devices, GroupId, unit, GroupName)
    # Update Group Structure
    self.ListOfGroups[GroupId]["Name"] = GroupName


def update_domoticz_group_device_widget(self, GroupId):

    self.logging("Debug", "update_domoticz_group_device_widget GroupId: %s" % GroupId)
    if GroupId == "":
        self.logging("Error", "update_domoticz_group_device_widget - Invalid GroupdID: %s" % (GroupId))

    unit = find_first_unit_widget_from_deviceID(self, self.Devices, GroupId)
    if unit is None:
        self.logging( "Debug", f"update_domoticz_group_device_widget - no unit found for GroupId {GroupId} - {self.ListOfGroups[GroupId]}" )
        LookForGroupAndCreateIfNeeded(self, GroupId)
        return

    Type_, Subtype_, SwitchType_ = best_group_widget(self, GroupId)

    if is_domoticz_latest_typename(self):
        current_typename = get_group_latest_typename(self, GroupId)
        if current_typename is None:
            current_switchType, current_Subtype, current_Type = domo_read_SwitchType_SubType_Type(self, self.Devices, GroupId, unit)
            current_typename = get_typename(self, current_switchType, current_Subtype, current_Type)

        new_typename = get_typename(self, Type_, Subtype_, SwitchType_)

        self.logging("Debug", f"      Looking to update Unit: {unit} from {current_typename} to {new_typename}")
        if current_typename != new_typename:
            self.ListOfGroups[GroupId]['TypeName'] = new_typename
            domo_update_SwitchType_SubType_Type(self, self.Devices, GroupId, unit, Type_, Subtype_, SwitchType_, Typename_=new_typename)

        return

    # Old fashion we rely only on Type_, Subtype_, SwitchType_
    current_switchType, current_Subtype, current_Type = domo_read_SwitchType_SubType_Type(self, self.Devices, GroupId, unit)
    self.logging("Debug", f"      Looking to update Unit: {unit} from {current_Type} {current_Subtype} {current_switchType} to {Type_} {Subtype_} {SwitchType_}")

    domo_update_SwitchType_SubType_Type(self, self.Devices, GroupId, unit, Type_, Subtype_, SwitchType_)


def get_typename(self, Type_, Subtype_, SwitchType_):
    for widget, style in WIDGET_STYLE.items():
        if style == (Type_, Subtype_, SwitchType_):
            widget_stype = widget
            return WIDGET_STYLE_TO_DOMOTICZ_TYPEMAP.get(widget_stype)
    return None


def best_group_widget(self, GroupId):

    group_widget_type_candidate = None
    GroupWidgetStyle = None

    self.logging("Debug", "best_group_widget Device - %s" % str(self.ListOfGroups[GroupId]["Devices"]))
    for NwkId, devEp, iterIEEE in self.ListOfGroups[GroupId]["Devices"]:
        # We will scan each Device in the Group and try to indentify which Widget is associated to it
        # Based on the list of Widget will try to identified the Most Features
        self.logging("Debug", "best_group_widget Device - %s  %s  %s" % (NwkId, devEp, iterIEEE))
        if NwkId == "0000":
            continue

        self.logging("Debug", "bestGroupWidget - Group: %s processing %s" % (GroupId, NwkId))
        if NwkId not in self.ListOfDevices:
            # We have some inconsistency !
            continue

        device_info = self.ListOfDevices.get(NwkId)
        device_ep_info = self.ListOfDevices.get(NwkId, {}).get("Ep", {}).get(devEp, {})
        if "ClusterType" not in device_ep_info:
            continue

        GroupWidgetStyle, group_widget_type_candidate = screen_device_list(self, NwkId, device_info, device_ep_info, GroupWidgetStyle, group_widget_type_candidate)
        self.logging( "Debug", f"best_group_widget {NwkId} {devEp} {iterIEEE} --> {GroupWidgetStyle} {group_widget_type_candidate}")

        # If GroupWidgetStyle is set then we stop here
        if GroupWidgetStyle in ( "BlindPercentInverted", "BlindPercent", "VenetianInverted"):
            break
    
    if group_widget_type_candidate is None:
        group_widget_type_candidate = "ColorControlFull"
        
    self.ListOfGroups[GroupId]["GroupWidgetType"] = group_widget_type_candidate

    # Update Tradfri Remote color mode
    self.ListOfGroups[GroupId].get("Tradfri Remote", {}).setdefault("Color Mode", group_widget_type_candidate)

    # Update Cluster based on WidgetStyle
    self.ListOfGroups[GroupId]["Cluster"] = CLUSTER_MAPPING.get(group_widget_type_candidate, "")

    self.logging( "Debug", "best_group_widget for GroupId: %s Found WidgetType: %s Widget: %s" % (
        GroupId, group_widget_type_candidate, WIDGET_STYLE.get(group_widget_type_candidate, WIDGET_STYLE["ColorControlFull"])), )

    if GroupWidgetStyle is None:
        GroupWidgetStyle = group_widget_type_candidate
        
    self.ListOfGroups[GroupId]["GroupWidgetStyle"] = GroupWidgetStyle
        
    return WIDGET_STYLE.get(GroupWidgetStyle, WIDGET_STYLE["ColorControlFull"])


def screen_device_list(self, NwkId, device_info, device_ep_info, GroupWidgetStyle, group_widget_type_candidate):
    
    for DomoDeviceUnit, device_widget_type in device_ep_info["ClusterType"].items():
        self.logging("Debug", f"------------screen_device_list {NwkId} DomoDeviceUnit: {DomoDeviceUnit} device_widget_type: {device_widget_type}" )
        if (device_widget_type is None):
            continue

        self.logging("Debug", f"------------screen_device_list {NwkId} group_widget_type_candidate: {group_widget_type_candidate} device_widget_type: {device_widget_type}" )

        if device_widget_type == "LvlControl":
            device_type = device_ep_info.get("Type") or device_info.get("Type")
            if device_type is not None:
                device_type = device_type.split('/')
            self.logging("Debug", f"------------screen_device_list {NwkId} device_ep_type: {device_type}" )

            if "BlindInverted" in device_type:
                # Blinds control via cluster 0x0008
                self.logging("Debug", "------------screen_device_list - Found BlindInverted!!")
                return "BlindPercentInverted", "LvlControl"

            elif "Blind" in device_type:
                # Blinds control via cluster 0x0008
                self.logging("Debug", "------------screen_device_list - Found Blind!!")
                return "BlindPercent", "LvlControl"

        if device_widget_type in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
            # Those widgets are commanded via cluster Level Control
            return "VenetianInverted", "LvlControl"

        if (device_widget_type == group_widget_type_candidate):
            continue

        group_widget_type_candidate = my_best_widget_offer(self, device_widget_type, group_widget_type_candidate)
        self.logging("Debug", f"------------screen_device_list - Found from my_best_widget_offer {group_widget_type_candidate}")
        
    return GroupWidgetStyle, group_widget_type_candidate

  
WIDGET_STYLE_RULES = {
    "Switch": {"Plug", "LvlControl", "ColorControlWW", "ColorControlRGB", "ColorControlRGBWW", "ColorControl", "ColorControlFull"},
    "Plug": {"Plug", "LvlControl", "ColorControlWW", "ColorControlRGB", "ColorControlRGBWW", "ColorControl", "ColorControlFull"},
    "LvlControl": {"ColorControlWW", "ColorControlRGB", "ColorControlRGBWW", "ColorControl", "ColorControlFull"},
    "ColorControlWW": {"ColorControlRGBWW"},
    "ColorControlRGB": {"ColorControlRGBWW"},
    "ColorControlRGBWW": set(),
    "ColorControl": set(),
    "ColorControlFull": set()  
}

def my_best_widget_offer(self, current_widget, current_group_widget):
    """ Find the best suitable widget. looks at the overlap features. If you have a Switch and ColorRGB, you can only do switch actions"""
    if current_group_widget in (None, current_widget):
        return current_widget
    
    if current_widget not in WIDGET_STYLE_RULES:
        return current_group_widget

    if current_group_widget in WIDGET_STYLE_RULES and current_widget in WIDGET_STYLE_RULES[current_group_widget]:
        return current_group_widget

    return current_widget

EXCLUDED_MODELS = {"TRADFRI remote control", "Remote Control N2"} | set(LEGRAND_REMOTES)

def update_domoticz_group_device(self, GroupId):
    """
    Recompute and push the On/Off + level state of a Zigbee group to Domoticz.

    Iterates over all devices in the group, collects their individual states,
    derives a combined nValue/sValue, and calls domo_update_api only when the
    state has actually changed.
    """
    
    if int(GroupId,16) == self.pluginconf.pluginConf["pingViaGroup"]:
        self.logging("Debug", "update_domoticz_group_device - Skip PingViaGroup: %s" % GroupId)
        return

    if GroupId not in self.ListOfGroups:
        self.logging("Error", "update_domoticz_group_device - unknown group: %s" % GroupId)
        return

    group_devices = self.ListOfGroups[GroupId].get("Devices")
    if group_devices is None or len(group_devices) == 0:
        self.logging( "Debug", "update_domoticz_group_device - no Devices for that group: %s" % self.ListOfGroups[GroupId])
        return

    unit = find_first_unit_widget_from_deviceID(self, self.Devices, GroupId)
    if unit is None:
        self.logging( "Debug", f"update_domoticz_group_device - no unit found for GroupId {GroupId} - {self.ListOfGroups[GroupId]}" )
        LookForGroupAndCreateIfNeeded(self, GroupId)
        return

    group_cluster = self.ListOfGroups[GroupId].get("Cluster")

    acc = GroupAccumulator()
    switchType, Subtype, _ = domo_read_SwitchType_SubType_Type(self, self.Devices, GroupId, unit)

    for NwkId, Ep, IEEE in group_devices:
        # Check each device in the group and count On/Off/Stop and average level for dimmers and covering
        if NwkId not in self.ListOfDevices:
            self.logging( "Debug", "update_domoticz_group_device - Nwkid: %s/%s not found for GroupId: %s" %(
                NwkId, IEEE, GroupId))
            if check_and_fix_missing_device(self, GroupId, NwkId, IEEE) is None:
                self.logging( "Error", "update_domoticz_group_device - Nwkid: %s/%s not found for GroupId: %s" %(
                    NwkId, IEEE, GroupId))
            # If we have updated the NwkId, then let's skip this and count on the next cycle to have the Group correctly updated.
            continue

        if Ep not in self.ListOfDevices[NwkId]["Ep"]:
            self.logging( "Debug", "update_domoticz_group_device - Nwkid: %s Ep: %s not found for GroupId: %s" %(
                NwkId, Ep, GroupId))
            continue

        model = self.ListOfDevices[NwkId].get("Model")
        if model in EXCLUDED_MODELS:
            continue

        _collect_device_state(self, NwkId, Ep, group_cluster, acc, switchType, GroupId)

        self.logging("Debug", "update_domoticz_group_device - Processing: Group: %s with device: %s/%s On: %s, Off: %s Stop: %s, level: %s" % (
            GroupId, NwkId, Ep, acc.count_on, acc.count_off, acc.count_stop, acc.level))

    current_nValue, current_sValue = domo_read_nValue_sValue(self, self.Devices, GroupId, unit)

    if acc.is_empty:   # count_on+off+stop == 0 and level_count == 0 and covering_count == 0
        self.logging("Debug", f"update_domoticz_group_device - no usable device state for {GroupId}, skipping")
        return

    elif acc.has_covering:
        # It is assumed that we cannot have a group with a mix of covering and non covering devices, 
        # For covering we directly use the covering value to compute nValue and sValue, as it is the most relevant
        # information for that type of device and should be the only one in the group
        nValue, sValue = ValuesForVenetian(acc.covering)

    else:
        nValue, sValue = _compute_nvalue_svalue(
            self, acc.level, switchType,
            acc.count_on, acc.count_off, acc.count_stop,
            GroupId, current_sValue
        )
            
    group_name = domo_read_Name( self, self.Devices, GroupId, unit )
    self.logging( "Debug", "update_domoticz_group_device - Processing: Group: %s ==  > from %s:%s to %s:%s" % (
        GroupId, current_nValue, current_sValue, nValue, sValue), )

    if nValue != current_nValue or sValue != current_sValue:
        self.ListOfGroups[GroupId]["nValue"] = nValue
        self.ListOfGroups[GroupId]["sValue"] = sValue
        self.ListOfGroups[GroupId]["prev_nValue"] = current_nValue
        self.ListOfGroups[GroupId]["prev_sValue"] = current_sValue
        self.ListOfGroups[GroupId]["Switchtype"] = switchType
        self.ListOfGroups[GroupId]["Subtype"] = Subtype
        self.logging("Log", f"UpdateGroup  - ({group_name:>15}) {nValue}:{sValue}")
        domo_update_api(self, self.Devices, GroupId, unit, nValue, sValue)


def _collect_device_state(self, nwkid, ep, group_cluster, acc, switchType, group_id=None):
    """
    Read one device endpoint's Zigbee state and fold it into the group accumulator.

    Mutates `acc` in place. Covering devices (cluster 0102, or 0008 on a covering
    widget) short-circuit and only update covering; otherwise on_off and level are
    folded in.
    """
    ep_data = self.ListOfDevices[nwkid]["Ep"][ep]

    if group_cluster == "0102":
        raw = ep_data.get("0102", {}).get("0008")
        if raw not in (None, "", {}):
            pct = int(raw) if isinstance(raw, int) else int(str(raw), 16)
            acc.add_covering(pct)   # 0102 attr 0008 is already 0–100
            return

    if group_cluster == "0008" and _is_covering_switchType(switchType):
        raw = ep_data.get("0008", {}).get("0000")
        if raw not in (None, "", {}):
            val = int(raw) if isinstance(raw, int) else int(str(raw), 16)
            acc.add_covering(round((val * 100) / 255))   # 0–255 → 0–100
            return

    if group_cluster in ("0006", "0008", "0300"):
        raw = ep_data.get("0006", {}).get("0000")
        if raw is not None and is_hex(str(raw)):
            if str(raw) == "f0":
                acc.add_on_off(17)
            elif int(raw) != 0:
                acc.add_on_off(1)
            else:
                acc.add_on_off(0)

    if group_cluster in ("0008", "0300"):
        raw = ep_data.get("0008", {}).get("0000")
        if raw not in (None, "", {}) and is_hex(str(raw)):
            val = int(raw) if isinstance(raw, int) else int(str(raw), 16)
            acc.add_level(val)


def _compute_nvalue_svalue(self, level, switchType, count_on, count_off, count_stop, group_id, current_sValue=None):
    """
    Derive the Domoticz (nValue, sValue) pair for the group from aggregated counters.

    nValue priority: Stop (17) > On/Off logic > Off (0).
    sValue is computed from level (dimmers), covering position (shutters),
    or falls back to "On"/"Off"/"Open"/"Close" for plain switches.
    current_sValue is used only in Stop mode to preserve the last known position.
    """
    nValue = 0 if self.pluginconf.pluginConf["OnIfOneOn"] else 1
    sValue = None

    if count_stop > 0:
        nValue = 17

    elif self.pluginconf.pluginConf["OnIfOneOn"]:
        if count_on > 0:
            nValue = 1

    elif count_off > 0:
        nValue = 0

    self.logging( "Debug", "update_domoticz_group_device - Processing: Group: %s ==  > nValue: %s, level: %s" % (
        group_id, nValue, level), )

    # At that stage
    # nValue == 0 if Off
    # nValue == 1 if Open/On
    # nValue == 17 if Stop
    # level is None, so we use nValue/sValue
    # level is not None; so we have a LvlControl

    if nValue == 17:
        # Covering is on Stop Mode, we keep the last sValue as it is the only way to keep the current position of the covering
        sValue = current_sValue if current_sValue is not None else "0"

    elif sValue is None and level is not None:
        if nValue == 0:
            # Device Off, we set sValue to 0 for covering and Off for others
            sValue = "Close" if _is_covering_switchType(switchType) else "Off"
    
        if not _is_covering_switchType(switchType):
            sValue = _compute_nvalue_svalue_for_level_control(level)

    elif sValue is None:
        if nValue == 0:
            sValue = "Close" if _is_covering_switchType(switchType) else "Off"
        else:
            sValue = "Open" if _is_covering_switchType(switchType) else "On"

    return nValue, sValue


def _compute_nvalue_svalue_for_level_control(level):
    """
    Convert a raw Zigbee level (0–255) to a Domoticz sValue percentage string.

    Returns "1" as a minimum when the device reports non-zero but rounds to 0.
    """
    analogValue = level
    if analogValue >= 255:
        sValue = 100
    else:
        sValue = round((level * 100) / 255)
        sValue = min(sValue, 100)
        if sValue == 0 and analogValue > 0:
            sValue = 1
    return str(sValue)

    
def _is_covering_switchType(switchType):
    """Return True if switchType corresponds to a shutter or blind (13–16)."""
    return switchType in (13, 14, 15, 16)


def ValuesForVenetian(level):
    """
    Convert a 0–100 percentage position to a Domoticz (nValue, sValue) for blinds/covers.

    nValue: 0 = closed, 1 = fully open, 2 = intermediate.
    Expects an already-normalized 0–100 value (see _collect_device_state).
    """

    if level == 0:
        return 0, "0"

    elif level >= 100:
        return 1, "100"

    else:
        return 2, str(level)
   
def update_domoticz_group_name(self, GrpId, NewGrpName):
    update_domoticz_group_device_widget_name(self, NewGrpName, GrpId)




def remove_domoticz_group_device(self, GroupId):
    " User has removed the Domoticz Device corresponding to this group"

    unit = find_first_unit_widget_from_deviceID(self, self.Devices, GroupId)
    if unit is None and GroupId in self.ListOfGroups:
        self.logging( "Debug", f"remove_domoticz_group_device - no unit found for GroupId {GroupId} - {self.ListOfGroups[GroupId]}" )
        return
    domo_delete_widget( self, self.Devices, GroupId, unit)


def update_device_list_attribute(self, GroupId, cluster, value):

    if GroupId not in self.ListOfGroups:
        return

    # search for all Devices in the group
    for iterItem in self.ListOfGroups[GroupId]["Devices"]:
        if len(iterItem) == 3:
            iterDev, iterEp, iterIEEE = iterItem

        elif len(iterItem) == 2:
            iterDev, iterEp = iterItem
            if iterDev in self.ListOfDevices:
                iterIEEE = self.ListOfDevices[iterDev]["IEEE"]

            else:
                self.logging("Error", "Unknown device %s, it is recommended to do a full rescan of Groups" % iterDev)
                continue
        else:
            continue

        if iterDev == "0000":
            continue

        if iterDev not in self.ListOfDevices:
            iterDev = check_and_fix_missing_device(self, GroupId, iterDev, iterIEEE)
            if iterDev is None:
                self.logging(
                    "Error",
                    "update_device_list_attribute - Device: %s of Group: %s not in the list anymore"
                    % (iterDev, GroupId),
                )
                continue

        if iterEp not in self.ListOfDevices[iterDev]["Ep"]:
            self.logging(
                "Error",
                "update_device_list_attribute - Not existing Ep: %s for Device: %s in Group: %s"
                % (iterEp, iterDev, GroupId),
            )
            continue

        if (
            "ClusterType" not in self.ListOfDevices[iterDev]["Ep"][iterEp]
            and "ClusterType" not in self.ListOfDevices[iterDev]
        ):
            self.logging(
                "Error",
                "update_device_list_attribute - No Widget attached to Device: %s/%s in Group: %s"
                % (iterDev, iterEp, GroupId),
            )
            continue

        if cluster not in self.ListOfDevices[iterDev]["Ep"][iterEp]:
            self.logging(
                "Debug",
                "update_device_list_attribute - Cluster: %s doesn't exist for Device: %s/%s in Group: %s"
                % (cluster, iterDev, iterEp, GroupId),
            )
            continue

        if cluster not in self.ListOfDevices[iterDev]["Ep"][iterEp]:
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster] = {}
        if not isinstance(self.ListOfDevices[iterDev]["Ep"][iterEp][cluster], dict):
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster] = {}

        if cluster == "0102":
            if "0008" not in self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]:
                self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0008"] = {}
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0008"] = value
        else:
            if "0000" not in self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]:
                self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0000"] = {}
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0000"] = value

        self.logging(
            "Debug",
            "update_device_list_attribute - Updating Device: %s/%s of Group: %s Cluster: %s to value: %s"
            % (iterDev, iterEp, GroupId, cluster, value),
        )

    return


def check_and_fix_missing_device(self, GroupId, NwkId, ieee):

    if ieee in self.IEEE2NWK:
        # Need to update the NwkId
        update_due_to_nwk_id_change(self, NwkId, self.IEEE2NWK[ieee])
        if self.IEEE2NWK[ieee] in self.ListOfDevices:
            return self.IEEE2NWK[ieee]
    return None


def processCommand(self, unit, GrpId, Command, Level, Color_):

    # Begin
    self.logging(
        "Debug",
        "processGroupCommand - unit: %s, NwkId: %s, cmd: %s, level: %s, color: %s"
        % (unit, GrpId, Command, Level, Color_),
    )

    if GrpId not in self.ListOfGroups:
        return

    # Not sure that Groups are always on EP 01 !!!!!
    EPout = "01"

    if self.ListOfGroups.get(GrpId, {}).get("Cluster") == "0102":
        if Command in ( "Off", "Close", ):
            nValue = 0
            sValue = "0"
            update_device_list_attribute(self, GrpId, "0102", 0)
            zcl_group_window_covering_on(self, GrpId, ZIGATE_EP, EPout)
            domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

        if Command in ( "On", "Open",):
            nValue = 1
            sValue = "100"
            zcl_group_window_covering_off(self, GrpId, ZIGATE_EP, EPout)
            update_device_list_attribute(self, GrpId, "0102", 100)
            domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

        if Command == "Stop":
            nValue = 17
            sValue = "0"
            zcl_group_window_covering_stop(self, GrpId, ZIGATE_EP, EPout)
            update_device_list_attribute(self, GrpId, "0102", 50)
            domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

        if Command == "Set Level":
            nValue = 2
            sValue = str(Level)
            if is_device_inverted(self, GrpId):
                Level = 0 if Level > 100 else 100 - Level
            Level = min(max(Level, 1), 99)
            update_device_list_attribute(self, GrpId, "0102", Level)
            self.logging( "Debug", "processGroupCommand - requesting level: %s for Group: %s" % (Level, GrpId), )
            zcl_group_window_covering_level(self, GrpId, ZIGATE_EP, EPout, level="%02x" %Level)
            domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

        resetDevicesHearttBeat(self, GrpId)
        return

    # Old Fashon
    if Command in ( "Off", "Close", ):
        if self.pluginconf.pluginConf["GrpfadingOff"]:
            if self.pluginconf.pluginConf["GrpfadingOff"] == 1:
                effect = "0002"  # 50% dim down in 0.8 seconds then fade to off in 12 seconds
            elif self.pluginconf.pluginConf["GrpfadingOff"] == 2:
                effect = "0100"  # 20% dim up in 0.5s then fade to off in 1 second
            elif self.pluginconf.pluginConf["GrpfadingOff"] == 255:
                effect = "0001"  # No fade

            zcl_group_onoff_off_witheffect(self, GrpId, ZIGATE_EP, EPout, effect)
        else:
            zcl_group_onoff_off_noeffect(self, GrpId, ZIGATE_EP, EPout)

        # Update Device
        nValue = 0
        sValue = "Off"
        domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

        update_device_list_attribute(self, GrpId, "0006", "00")
        update_domoticz_group_device(self, GrpId)

    elif Command in ( "On", "Open", ):
        nValue = 1
        sValue = "On"
        domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

        update_device_list_attribute(self, GrpId, "0006", "01")
        update_domoticz_group_device(self, GrpId)
        zcl_group_onoff_on(self, GrpId, ZIGATE_EP, EPout)

    elif Command in ( "Stop",) and self.ListOfGroups.get(GrpId, {}).get("Cluster") == "0102":
        # Windowscovering Stop
        zcl_group_window_covering_stop(self, GrpId, "01", EPout)

    elif Command in ( "Stop",) and self.ListOfGroups.get(GrpId, {}).get("Cluster") == "0008":
        # SetLevel Off
        zcl_group_move_to_level_stop(self, GrpId, EPout)

    elif Command == "Set Level":
        Level = max(0, min(Level, 100))
        OnOff = "01"

        value = "%02X" % int(Level * 255 // 100)
        update_device_list_attribute(self, GrpId, "0008", value)

        transitionMoveLevel = "%04x" % self.pluginconf.pluginConf["GrpmoveToLevel"]
        GroupLevelWithOnOff = bool(
            (
                "GroupLevelWithOnOff" in self.pluginconf.pluginConf
                and self.pluginconf.pluginConf["GroupLevelWithOnOff"]
            )
        )
        if GroupLevelWithOnOff:
            zcl_group_move_to_level_with_onoff(self, GrpId, EPout, OnOff, value, transition=transitionMoveLevel, ackIsDisabled=True)
        else:
            zcl_group_level_move_to_level( self, GrpId, ZIGATE_EP, EPout, "01", value, transition=transitionMoveLevel)

        if self.ListOfGroups[GrpId].get("WidgetStyle") in {"Switch", "Plug", "LvlControl", "ColorControlWW", "ColorControlRGB", "ColorControlRGBWW", "ColorControl", "ColorControlFull"} and Level == 100:
            zcl_group_onoff_on(self, GrpId, ZIGATE_EP, EPout)
            
        update_domoticz_group_device(self, GrpId)
        # Update Device
        nValue = 2
        sValue = str(Level)
        domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue)

    elif Command == "Set Color":
        Hue_List = json.loads(Color_)
        transitionRGB = "%04x" % self.pluginconf.pluginConf["GrpmoveToColourRGB"]
        transitionMoveLevel = "%04x" % self.pluginconf.pluginConf["GrpmoveToLevel"]
        transitionHue = "%04x" % self.pluginconf.pluginConf["GrpmoveToHueSatu"]
        transitionTemp = "%04x" % self.pluginconf.pluginConf["GrpmoveToColourTemp"]

        # First manage level
        if Hue_List["m"] != 9998:
            # In case of m ==3, we will do the Setlevel
            OnOff = "01"  # 00 = off, 01 = on
            value = Hex_Format(2, round(1 + Level * 254 / 100))  # To prevent off state
            update_device_list_attribute(self, GrpId, "0008", value)

            zcl_group_move_to_level_with_onoff(self, GrpId, EPout, OnOff, value, transition="0000")

        if Hue_List["m"] == 1:
            ww = int(Hue_List["ww"])  # Can be used as level for monochrome white
            self.logging("Debug", "Not implemented device color 1")

        # ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List["m"] == 2:
            set_kelvin_color( self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(Hue_List["t"]), transit=transitionTemp )

        elif Hue_List["m"] == 3:
            set_rgb_color( self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(Hue_List["r"]), int(Hue_List["g"]), int(Hue_List["b"]), transit=transitionRGB, )

        elif Hue_List["m"] == 4:
            # Gledopto GL_008
            # Color: {"b":43,"cw":27,"g":255,"m":4,"r":44,"t":227,"ww":215}
            self.logging("Log", "Not fully implemented device color 4")

            # Process White color
            cw = int(Hue_List["cw"])  # 0 < cw < 255 Cold White
            ww = int(Hue_List["ww"])  # 0 < ww < 255 Warm White
            if cw != 0 and ww != 0:
                set_kelvin_color(self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(ww), transit=transitionTemp)
            # Process Colour
            set_hue_saturation( self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(Hue_List["r"]), int(Hue_List["g"]), int(Hue_List["b"]), transit=transitionHue, )

        elif Hue_List["m"] == 9998:
            level = set_hue_saturation( self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(Hue_List["r"]), int(Hue_List["g"]), int(Hue_List["b"]), transit=transitionHue, )

            value = int(level * 254 // 100)
            OnOff = "01"
            self.logging("Debug", "---------- Set Level: %s instead of Level: %s" % (value, Level))
            zcl_group_move_to_level_with_onoff(self, GrpId, EPout, OnOff, Hex_Format(2, value), transition=transitionMoveLevel)

        # Update Device
        nValue = 1
        sValue = str(Level)
        domo_update_api(self, self.Devices, GrpId, unit, nValue, sValue, Color=Color_)

    # Request to force ReadAttribute to each devices part of that group
    resetDevicesHearttBeat(self, GrpId)


def resetDevicesHearttBeat(self, GrpId):

    if not self.pluginconf.pluginConf["forceGroupDeviceRefresh"]:
        return

    for NwkId, Ep, Ieee in self.ListOfGroups[GrpId]["Devices"]:
        self.logging("Debug", "processGroupCommand - reset heartbeat for device : %s" % NwkId)
        if NwkId not in self.ListOfDevices:
            if Ieee in self.IEEE2NWK:
                NwkId = self.IEEE2NWK[Ieee]
            else:
                self.logging(
                    "Error", "resetDevicesHearttBeat - Hum Hum something wrong NwkId: %s Ieee %s" % (NwkId, Ieee)
                )

        if NwkId in self.ListOfDevices:
            # Force Read Attribute consideration in the next hearbeat
            if "Heartbeat" in self.ListOfDevices[NwkId]:
                self.ListOfDevices[NwkId]["Heartbeat"] = "0"

            # Reset Health status of corresponding device if any in Not Reachable
            if "Health" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Health"] == "Not Reachable":
                self.ListOfDevices[NwkId]["Health"] = ""


def is_device_inverted(self, GroupId):
    """
    Check if at least one device in the group has the parameter WindowsCoverringLevelInverted
    set to True
    """
    if GroupId not in self.ListOfGroups:
        return False
    
    for NwkId, _, Ieee in self.ListOfGroups[GroupId]["Devices"]:
        model_name = self.ListOfDevices.get(NwkId, {}).get("Model")
        if model_name is None:
            continue
        self.logging( "Debug", "is_device_inverted - Looking for WindowsCoverringLevelInverted in  NwkId: %s Ieee %s Model: %s" % (NwkId, Ieee, model_name) )
        
        if get_deviceconf_parameter_value(self, model_name, "WindowsCoverringLevelInverted"):
            self.logging( "Debug", "is_device_inverted - Found WindowsCoverringLevelInverted for NwkId: %s Ieee %s" % (NwkId, Ieee) )
            return True

    return False


def get_group_latest_typename(self, GroupId):
    
    return self.ListOfGroups[GroupId].get("TypeName")