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

"""
    Module: domoAbstractLayer.py
    Description: Set of functions which abstract Domoticz Legacy and Extended framework API
"""


import ast
import base64
import contextlib
import copy
import json
import time
import zlib

import DomoticzEx as Domoticz

DIMMABLE_WIDGETS = {
    (7, 1, 241): { "Widget": "Dimmable_Light", "Name": "RGBW", "partially_opened_nValue": 15},
    (7, 2, 241): { "Widget": "Dimmable_Light", "Name": "RGB", "partially_opened_nValue": 15},
    (7, 4, 241): { "Widget": "Dimmable_Light", "Name": "RGBWW", "partially_opened_nValue": 15},
    (7, 7, 241): { "Widget": "Dimmable_Light", "Name": "RGBWWZ", "partially_opened_nValue": 15},
    (7, 8, 241): { "Widget": "Dimmable_Light", "Name": "WW Switch", "partially_opened_nValue": 15},
    (7, 73, 244): { "Widget": "Dimmable_Switch", "Name": "Dimmer", "partially_opened_nValue": 2},
    (14, 73, 244): { "Widget": "Blind", "Name": "Venetian Blinds US", "partially_opened_nValue": 17},
    (13, 73, 244): { "Widget": "Blind", "Name": "Blind Percentage", "partially_opened_nValue": 2},
    (15, 73, 244): { "Widget": "Blind", "Name": "Venetian Blinds EU", "partially_opened_nValue": 17},
    (21, 73, 244): { "Widget": "Blind", "Name": "Blinds + Stop", "partially_opened_nValue": 2},
    (3, 73, 244): { "Widget": "Blind", "Name": "BSO-Volet", "partially_opened_nValue": 17},
}


DELAY_BETWEEN_TOUCH = 120


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _device_unit_exists(Devices, DeviceID, Unit):
    """Return True only when both the device and the unit are present."""
    return (
        Devices is not None
        and DeviceID in Devices
        and Unit in Devices[DeviceID].Units
    )


def _device_exists(Devices, DeviceID):
    """Return True only when the device is present."""
    return Devices is not None and DeviceID in Devices


# ---------------------------------------------------------------------------
# Communication Helpers
# ---------------------------------------------------------------------------

def domoticz_connection(name, transport, protocol, address=None, port=None, baud=None):
    if address and baud:
        return Domoticz.Connection(Name=name, Transport=transport, Protocol=protocol,
                                   Address=address, Port=port, Baud=baud)
    if address:
        return Domoticz.Connection(Name=name, Transport=transport, Protocol=protocol,
                                   Address=address, Port=port)
    return Domoticz.Connection(Name=name, Transport=transport, Protocol=protocol, Port=port)


# ---------------------------------------------------------------------------
# Configuration Helpers
# ---------------------------------------------------------------------------

def setConfigItem(Key=None, Attribute="", Value=None):
    """
    Persist a value in the Domoticz configuration store.

    Returns the updated Config dict, or None on failure.
    """
    Config = {}
    if not isinstance(Value, (str, int, float, bool, bytes, bytearray, list, dict)):
        domoticz_error_api(
            "setConfigItem - A value is specified of a not allowed type: '"
            + str(type(Value)) + "'"
        )
        return None  # Consistent: always None on any error path

    if isinstance(Value, dict):
        Value = prepare_dict_for_storage(Value, Attribute)
        if Value is None:
            domoticz_error_api("setConfigItem - prepare_dict_for_storage/deepcopy failed after 3 attempts, skipping write")
            return None

    try:
        Config = Domoticz.Configuration()
        if Key is None:
            Config = Value
        else:
            Config[Key] = Value
        Config = Domoticz.Configuration(Config)
    except Exception as inst:
        domoticz_error_api(
            "setConfigItem - Domoticz.Configuration operation failed: '" + str(inst) + "'"
        )
        return None
    return Config


def getConfigItem(Key=None, Attribute="", Default=None):
    
    #domoticz_log_api("Loading %s - %s from Domoticz sqlite Db" %( Key, Attribute))
    
    if Default is None:
        Default = {}
    Value = Default
    try:
        Config = Domoticz.Configuration()
        Value = Config if Key is None else Config[Key]
    except KeyError:
        Value = Default
    except Exception as inst:
        domoticz_error_api(
            "getConfigItem - Domoticz.Configuration read failed: '" + str(inst) + "'"
        )

    return repair_dict_after_load(Value, Attribute)


def prepare_dict_for_storage(dict_items, Attribute):
    for _ in range(3):
        with contextlib.suppress(RuntimeError, ValueError, TypeError):
            dict_items = copy.deepcopy(dict_items)
            break
    else:
        return None

    if Attribute in dict_items:
        payload = json.dumps(dict_items[Attribute], ensure_ascii=False).encode("utf-8")
        dict_items[Attribute] = base64.b64encode(zlib.compress(payload)).decode("ascii")
    dict_items["Version"] = 2
    return dict_items


def repair_dict_after_load(b64_dict, Attribute):
    if not b64_dict or b64_dict == "":
        return {}

    if not isinstance(b64_dict, dict) or "Version" not in b64_dict:
        domoticz_log_api("repair_dict_after_load - Not supported storage")
        return {}

    if Attribute not in b64_dict:
        return b64_dict

    value = b64_dict[Attribute]

    if isinstance(value, dict):
        return b64_dict

    if not isinstance(value, (str, bytes, bytearray)):
        domoticz_log_api(
            f"repair_dict_after_load - Unexpected type for {Attribute}: {type(value)}"
        )
        return b64_dict

    # Try decode safely
    version = b64_dict.get("Version", 1)
    try:
        b64_dict[Attribute] = decode_b64_payload(value, attribute_name=Attribute, version=version)

    except Exception as e:
        domoticz_log_api(f"repair_dict_after_load - Failed to decode {Attribute}: {value} - {e}")
        return {}

    return b64_dict


def decode_b64_payload(value, attribute_name="", version=1):
    try:
        raw = base64.b64decode(value)
    except Exception as e:
        raise ValueError(f"{attribute_name}: base64 decode failed: {e}") from e

    if version == 2:
        try:
            raw = zlib.decompress(raw)
        except zlib.error as e:
            raise ValueError(f"{attribute_name}: zlib decompress failed: {e}") from e
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"{attribute_name}: JSON decode failed: {e}") from e

    # Version 1: uncompressed, stored as Python repr (str() output)
    try:
        decoded = raw.decode("utf-8")
    except Exception as e:
        raise ValueError(f"{attribute_name}: UTF-8 decode failed: {e}") from e

    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(decoded)

    try:
        return ast.literal_eval(decoded)
    except Exception as e:
        raise ValueError(
            f"{attribute_name}: neither JSON nor Python literal: {e}\n"
            f"Decoded content was:\n{decoded}"
        ) from e


# ---------------------------------------------------------------------------
# Devices helpers
# ---------------------------------------------------------------------------

def load_list_of_domoticz_widget(self, Devices):
    """
    Build (or rebuild) the in-memory index of Domoticz Widgets.

    Called at plugin start, after widget removal, and after new device pairing.
    """
    self.ListOfDomoticzWidget.clear()

    if Devices is None:
        domoticz_error_api("load_list_of_domoticz_widget - Devices is None")
        return

    for device_ieee in Devices:
        try:
            for unit_key, unit_data in Devices[device_ieee].Units.items():
                widget_info = {
                    "Name": unit_data.Name,
                    "Unit": unit_key,
                    "DeviceID": device_ieee,
                    "Switchtype": unit_data.SwitchType,
                    "Subtype": unit_data.SubType,
                }
                self.ListOfDomoticzWidget[unit_data.ID] = widget_info
        except Exception as e:
            domoticz_error_api(
                f"load_list_of_domoticz_widget - Failed to index device {device_ieee}: {e}"
            )


def find_widget_unit_from_WidgetID(self, Widget_Idx):
    """
    Return the Unit for a given Widget IDX, or None if not found.

    Widget_Idx is expected to be an int or a string that converts cleanly to int.
    """
    self.log.logging("AbstractDz", "Debug",
                     f"find_widget_unit_from_WidgetID - Widget_Idx: {Widget_Idx} ({type(Widget_Idx)})")

    # Defensive: Widget_Idx must be castable to int
    try:
        Widget_Idx = int(Widget_Idx)
    except (TypeError, ValueError):
        self.log.logging("AbstractDz", "Error",
                         f"find_widget_unit_from_WidgetID - invalid Widget_Idx: {Widget_Idx!r}")
        return None

    if Widget_Idx in self.ListOfDomoticzWidget:
        return self.ListOfDomoticzWidget[Widget_Idx]["Unit"]

    self.log.logging("AbstractDz", "Log",
                     f"Plugin looks for Domoticz Widget Id {Widget_Idx} which does not exist!")

    return None


def retrieve_widgetid_from_deviceId_unit(self, Devices, DeviceId, Unit):
    self.log.logging("AbstractDz", "Debug",
                     f"retrieve_widgetid_from_deviceId_unit: DeviceId: {DeviceId} Unit: {Unit}")
    return next(
        (
            x for x in self.ListOfDomoticzWidget
            if (
                self.ListOfDomoticzWidget[x]["DeviceID"] == DeviceId
                and self.ListOfDomoticzWidget[x]["Unit"] == Unit
            )
        ),
        None,
    )


def find_first_unit_widget_from_deviceID(self, Devices, DeviceID):
    """Return the first unit index for a specific DeviceID, or None if not found."""
    self.log.logging("AbstractDz", "Debug",
                     f"find_first_unit_widget_from_deviceID: {DeviceID}")
    if not _device_exists(Devices, DeviceID):
        return None
    units = Devices[DeviceID].Units
    return next(iter(units), None)



def retreive_free_unit_for_widget(self, Devices, DeviceId, nbunit_=1):
    """
    Look for a free Unit number. If nbunit_ > 1, look for nbunit_ consecutive slots.

    Returns an int unit number, or None if none is available.
    """
    if not isinstance(nbunit_, int) or nbunit_ < 1 or nbunit_ > 254:
        self.log.logging("AbstractDz", "Error",
                         f"retreive_free_unit_for_widget - invalid nbunit_: {nbunit_!r}")
        return None

    def _log_message(count):
        messages = {
            5: "It seems that you can create only 5 Domoticz widgets more !!!",
            15: "It seems that you can create only 15 Domoticz widgets more !!",
            30: "It seems that you can create only 30 Domoticz widgets more !",
        }
        message = messages.get(255 - count)
        if message:
            self.log.logging("AbstractDz", "Status", message)

    def _free_unit_in_device(available_units, nbunit_):
        for x in range(1, 255):
            if x not in available_units:
                if nbunit_ == 1:
                    self.log.logging("AbstractDz", "Debug",
                                     "_free_unit_in_device - found unit %s" % str(x))
                    return x
                nb = 1
                for y in range(x + 1, 255):
                    if y not in available_units:
                        nb += 1
                    else:
                        break
                    if nb == nbunit_:
                        self.log.logging("AbstractDz", "Debug",
                                         "_free_unit_in_device - found unit %s" % str(x))
                        return x
        return None

    self.log.logging("AbstractDz", "Debug",
                     f"retreive_free_unit_for_widget - looking for a free unit in {DeviceId}")
    available_units = set()
    if _device_exists(Devices, DeviceId):
        available_units = set(Devices[DeviceId].Units.keys())

    result = _free_unit_in_device(available_units, nbunit_)
    if result is not None:
        _log_message(result)
    return result


def is_device_ieee_in_domoticz_db(self, Devices, DeviceID_):
    """Return True only when the device exists and has at least one unit."""
    found = _device_exists(Devices, DeviceID_) and len(Devices[DeviceID_].Units) > 0
    self.log.logging("AbstractDz", "Debug",
                     f"is_device_ieee_in_domoticz_db: DeviceID={DeviceID_}, "
                     f"found={found}, total_devices={len(Devices) if Devices else 0}")
    return found


def domo_create_api(self, Devices, DeviceID_, Unit_, Name_,
                    widgetType=None, Type_=None, Subtype_=None, Switchtype_=None,
                    widgetOptions=None, Image=None):
    """
    Create a Domoticz Widget (Extended framework).

    Returns the widget IDX on success, or -1 on failure.
    """
    # --- Input validation ---------------------------------------------------
    if not DeviceID_:
        self.log.logging("AbstractDz", "Error",
                         "domo_create_api - DeviceID_ is empty or None")
        return -1

    if Unit_ is None:
        self.log.logging("AbstractDz", "Error",
                         f"domo_create_api - Unit_ is None for DeviceID={DeviceID_}")
        return -1

    if not Name_:
        self.log.logging("AbstractDz", "Error",
                         f"domo_create_api - Name_ is empty for DeviceID={DeviceID_} Unit={Unit_}")
        return -1
    # ------------------------------------------------------------------------

    self.log.logging(
        "AbstractDz", "Debug",
        "domo_create_api DeviceID: %s, Name: %s, Unit: %s, TypeName: %s, "
        "Type: %s, Subtype: %s, Switchtype: %s, widgetOptions: %s, Image: %s" % (
            DeviceID_, Name_, Unit_, widgetType, Type_, Subtype_,
            Switchtype_, widgetOptions, Image,
        ),
    )

    full_name = f"{self.pluginParameters['Name']} - {Name_}"

    if widgetOptions is None:
        widgetOptions = {}

    try:
        if widgetType:
            self.log.logging("AbstractDz", "Debug",
                             "- based on widgetType %s" % widgetType)
            Domoticz.Unit(
                DeviceID=DeviceID_, Name=full_name, Unit=Unit_, TypeName=widgetType,
            ).Create()

        elif widgetOptions:
            self.log.logging("AbstractDz", "Debug",
                             "- based on widgetOptions %s" % widgetOptions)
            _type = Type_ if Type_ is not None else 244
            _sub = Subtype_ if Subtype_ is not None else 62
            _sw = Switchtype_ if Switchtype_ is not None else 18
            Domoticz.Unit(
                DeviceID=DeviceID_, Name=full_name, Unit=Unit_,
                Type=_type, Subtype=_sub, Switchtype=_sw, Options=widgetOptions,
            ).Create()

        elif Image:
            self.log.logging("AbstractDz", "Debug", "- based on Image %s" % Image)
            Domoticz.Unit(
                DeviceID=DeviceID_, Name=full_name, Unit=Unit_,
                Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_, Image=Image,
            ).Create()

        elif Switchtype_:
            self.log.logging("AbstractDz", "Debug",
                             "- based on Switchtype_ %s" % Switchtype_)
            Domoticz.Unit(
                DeviceID=DeviceID_, Name=full_name, Unit=Unit_,
                Type=Type_, Subtype=Subtype_, Switchtype=Switchtype_,
            ).Create()

        else:
            self.log.logging("AbstractDz", "Debug", "- default")
            Domoticz.Unit(
                DeviceID=DeviceID_, Name=full_name, Unit=Unit_,
                Type=Type_, Subtype=Subtype_,
            ).Create()

    except Exception as e:
        self.log.logging("AbstractDz", "Error",
                         f"domo_create_api - Domoticz.Unit.Create() raised: {e}")
        return -1

    # Refresh index regardless
    load_list_of_domoticz_widget(self, Devices)

    # Verify creation (AND, not OR)
    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        self.log.logging("AbstractDz", "Error",
                         f"domo_create_api Created device: {DeviceID_} {Unit_} {full_name} failed !!!")
        return -1

    units_summary = {k: v.ID for k, v in Devices[DeviceID_].Units.items()}
    self.log.logging("AbstractDz", "Debug",
                     f"domo_create_api Created device: {DeviceID_} {Unit_} {full_name}")
    self.log.logging("AbstractDz", "Debug", f"        Units:   {units_summary}")
    self.log.logging("AbstractDz", "Debug",
                     f"        ID:      {Devices[DeviceID_].Units[Unit_].ID}")
    return Devices[DeviceID_].Units[Unit_].ID


def domo_delete_widget(self, Devices, DeviceID_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_delete_widget: DeviceID_: {DeviceID_} Unit_: {Unit_}")

    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        self.log.logging("AbstractDz", "Error",
                         f"domo_delete_widget - {DeviceID_}/{Unit_} not found, skipping")
        return

    try:
        Devices[DeviceID_].Units[Unit_].Delete()
    except Exception as e:
        self.log.logging("AbstractDz", "Error",
                         f"domo_delete_widget - Delete() raised: {e}")
        return

    if _device_exists(Devices, DeviceID_) and len(Devices[DeviceID_].Units) == 0:
        try:
            Devices[DeviceID_].Delete()
        except Exception as e:
            self.log.logging("AbstractDz", "Error",
                             f"domo_delete_widget - Device.Delete() raised: {e}")

    load_list_of_domoticz_widget(self, Devices)


def domo_update_api(self, Devices, DeviceID_, Unit_, nValue, sValue,
                    SignalLevel=None, BatteryLevel=None, TimedOut=None,
                    Color="", Options=None, SuppressTriggers=False):
    """
    Update a widget's nValue / sValue and optional attributes.

    Silently returns (with an error log) when the device/unit does not exist
    or when nValue is None, rather than raising a KeyError.
    """
    nwkid = self.IEEE2NWK.get(DeviceID_)

    self.log.logging(
        "AbstractDz", "Debug",
        "domo_update_api: DeviceID_: %s Unit_: %s nValue: %s sValue: %s "
        "SignalLevel: %s BatteryLevel: %s TimedOut: %s Color: %s Options: %s" % (
            DeviceID_, Unit_, nValue, sValue,
            SignalLevel, BatteryLevel, TimedOut, Color, Options,
        ),
        nwkid,
    )

    if nValue is None:
        self.log.logging(
            "AbstractDz", "Error",
            "domo_update_api - nValue is None for DeviceID_: %s Unit_: %s" % (DeviceID_, Unit_),
            nwkid,
        )
        return

    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        self.log.logging(
            "AbstractDz", "Error",
            f"domo_update_api - {DeviceID_}/{Unit_} does not exist, skipping update",
            nwkid,
        )
        return

    unit_obj = Devices[DeviceID_].Units[Unit_]
    unit_obj.nValue = nValue
    unit_obj.sValue = sValue

    # TimedOut lives on the Device, not the Unit
    if TimedOut is not None:
        Devices[DeviceID_].TimedOut = TimedOut

    if Color != "":
        unit_obj.Color = Color

    if BatteryLevel is not None:
        unit_obj.BatteryLevel = BatteryLevel

    if SignalLevel is not None:
        unit_obj.SignalLevel = SignalLevel

    if Options is not None:
        try:
            unit_obj.Options = Options
        except Exception as e:
            self.log.logging("AbstractDz", "Debug",
                             f"domo_update_api: Cannot write Options {Options}: {e}", nwkid)

    try:
        unit_obj.Update(Log=(not SuppressTriggers))
    except Exception as e:
        self.log.logging("AbstractDz", "Error",
                         f"domo_update_api - Unit.Update() raised: {e}", nwkid)


def domo_update_name(self, Devices, DeviceID_, Unit_, new_name):
    self.log.logging("AbstractDz", "Debug", f"domo_update_name: DeviceID_: {DeviceID_} Unit_: {Unit_} Name: {new_name}")

    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        self.log.logging("AbstractDz", "Error", f"domo_update_name - {DeviceID_}/{Unit_} does not exist")
        return

    if Devices[DeviceID_].Units[Unit_].Name != new_name:
        self.log.logging("AbstractDz", "Debug", f"domo_update_name: Updating from {Devices[DeviceID_].Units[Unit_].Name} to {new_name}")

        try:
            Devices[DeviceID_].Units[Unit_].Name = new_name
            Devices[DeviceID_].Units[Unit_].nValue = 0   # nValue must be changed to trigger the update of the name in Domoticz UI
            Devices[DeviceID_].Units[Unit_].sValue = ""  # sValue must be changed to trigger the update of the name in Domoticz UI

            Devices[DeviceID_].Units[Unit_].Update(UpdateProperties=True,SuppressTriggers=True)

        except Exception as e:
            self.log.logging("AbstractDz", "Error", f"domo_update_name - Update() raised: {e}")


def domo_update_SwitchType_SubType_Type(self, Devices, DeviceID_, Unit_,
                                        Type_=0, Subtype_=0, Switchtype_=0, Typename_=None):
    self.log.logging(
        "AbstractDz", "Debug",
        "domo_update_SwitchType_SubType_Type DeviceID: %s, Unit: %s, "
        "Type: %s, Subtype: %s, Switchtype: %s" % (DeviceID_, Unit_, Type_, Subtype_, Switchtype_),
    )

    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        self.log.logging("AbstractDz", "Error",
                         f"domo_update_SwitchType_SubType_Type - {DeviceID_}/{Unit_} does not exist")
        return

    if Typename_:
        try:
            Devices[DeviceID_].Units[Unit_].Update(TypeName=Typename_)
        except Exception as e:
            self.log.logging("AbstractDz", "Error",
                             f"domo_update_SwitchType_SubType_Type - Update() raised: {e}")


def domo_browse_widgets(self, Devices):
    """Return list of (DeviceId, unit) tuples."""
    self.log.logging("AbstractDz", "Debug", "domo_browse_widgets")
    if Devices is None:
        return []
    list_domoticz_widgets = []
    for deviceId in Devices:
        list_domoticz_widgets.extend((deviceId, unit) for unit in Devices[deviceId].Units)
    return list_domoticz_widgets


def domo_read_nValue_sValue(self, Devices, DeviceID, Unit):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_nValue_sValue: DeviceID: {DeviceID} Unit: {Unit}")
    if _device_unit_exists(Devices, DeviceID, Unit):
        _unit = Devices[DeviceID].Units[Unit]
        return _unit.nValue, _unit.sValue
    return None, None


def domo_read_TimedOut(self, Devices, DeviceId_):
    """Return the TimedOut flag for a device, or None if the device does not exist."""
    self.log.logging("AbstractDz", "Debug", f"domo_read_TimedOut: DeviceID: {DeviceId_}")
    if _device_exists(Devices, DeviceId_):
        return Devices[DeviceId_].TimedOut
    return None


def domo_read_LastUpdate(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_LastUpdate: DeviceID: {DeviceId_} Unit {Unit_}")
    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return None
    return Devices[DeviceId_].Units[Unit_].LastUpdate


def domo_read_BatteryLevel(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_BatteryLevel: DeviceID: {DeviceId_} Unit {Unit_}")
    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return None
    return Devices[DeviceId_].Units[Unit_].BatteryLevel


def domo_read_SignalLevel(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_SignalLevel: DeviceID: {DeviceId_} Unit {Unit_}")
    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return None
    return Devices[DeviceId_].Units[Unit_].SignalLevel


def domo_read_Color(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_Color: DeviceID: {DeviceId_} Unit {Unit_}")
    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return None
    return Devices[DeviceId_].Units[Unit_].Color


def domo_read_Name(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_Name: DeviceID: {DeviceId_} Unit {Unit_}")
    if _device_unit_exists(Devices, DeviceId_, Unit_):
        return Devices[DeviceId_].Units[Unit_].Name
    return ""


def domo_read_Options(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_Options: DeviceID: {DeviceId_} Unit {Unit_}")
    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return None
    return Devices[DeviceId_].Units[Unit_].Options


def domo_read_Device_Idx(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_Device_Idx: DeviceID: {DeviceId_} Unit {Unit_}")
    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return None
    return Devices[DeviceId_].Units[Unit_].ID


def domo_check_unit(self, Devices, DeviceId_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_check_unit: DeviceID: {DeviceId_} Unit {Unit_}")
    return _device_unit_exists(Devices, DeviceId_, Unit_)


def domo_read_SwitchType_SubType_Type(self, Devices, DeviceID, Unit):
    self.log.logging("AbstractDz", "Debug",
                     f"domo_read_SwitchType_SubType_Type: DeviceID: {DeviceID} Unit {Unit}")
    if not _device_unit_exists(Devices, DeviceID, Unit):
        return None, None, None
    _unit = Devices[DeviceID].Units[Unit]
    return _unit.SwitchType, _unit.SubType, _unit.Type


def _is_meter_widget(self, Devices, DeviceID_, Unit_):
    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        return False
    unit = Devices[DeviceID_].Units[Unit_]
    return unit.SwitchType == 0 and unit.SubType == 29 and unit.Type == 243


def _is_device_tobe_switched_off(self, Devices, DeviceID_, Unit_):
    self.log.logging("AbstractDz", "Debug",
                     f"_is_device_tobe_switched_off: {DeviceID_} {Unit_}")
    if not _device_unit_exists(Devices, DeviceID_, Unit_):
        return False
    unit = Devices[DeviceID_].Units[Unit_]
    return (
        (unit.Type == 244 and unit.SubType == 73 and unit.SwitchType == 7)
        or (unit.Type == 241 and unit.SwitchType == 7)
    )


def device_touch_api(self, Devices, DeviceId_):
    """Touch all widgets for a device (skipping meter widgets)."""
    self.log.logging("AbstractDz", "Debug", f"device_touch_api: {DeviceId_}")

    if not _device_exists(Devices, DeviceId_):
        return

    now = time.time()
    for unit in list(Devices[DeviceId_].Units):
        _device_touch_unit_api(self, Devices, DeviceId_, unit, now)


def _device_touch_unit_api(self, Devices, DeviceId_, Unit_, now):
    """Touch one widget for a device."""
    self.log.logging("AbstractDz", "Debug",
                     f"_device_touch_unit_api: {DeviceId_} {Unit_}")

    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return

    if _is_meter_widget(self, Devices, DeviceId_, Unit_):
        return

    last_time = Devices[DeviceId_].Units[Unit_].LastUpdate
    if not last_time:
        return

    try:
        last_update_time_seconds = time.mktime(
            time.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        )
    except (ValueError, OverflowError) as e:
        self.log.logging("AbstractDz", "Error",
                         f"_device_touch_unit_api - Cannot parse LastUpdate '{last_time}': {e}")
        return

    if now > (last_update_time_seconds + DELAY_BETWEEN_TOUCH):
        try:
            Devices[DeviceId_].Units[Unit_].Touch()
        except Exception as e:
            self.log.logging("AbstractDz", "Error",
                             f"_device_touch_unit_api - Touch() raised: {e}")


def timeout_widget_api(self, Devices, DeviceId_, timeout_value):
    """ TimedOut all Device Widgets """
    self.log.logging("AbstractDz", "Debug", f"timeout_widget_api: {DeviceId_}")
    
    if not _device_exists(Devices, DeviceId_):
        return

    Devices[DeviceId_].TimedOut = timeout_value
    if timeout_value == 1 and self.pluginconf.pluginConf.get("deviceOffWhenTimeOut"):
        for unit in list(Devices[DeviceId_].Units):
            _nValue, _sValue = domo_read_nValue_sValue(self, Devices, DeviceId_, unit)
            _switch_off_widget_due_to_timedout(self, Devices, DeviceId_, unit, _nValue, _sValue)


def update_battery_api(self, Devices, DeviceId, battery_level):
    self.log.logging(["AbstractDz", "BatteryManagement"], "Debug",
                     f"update_battery_api: {DeviceId} to {battery_level}")

    if not _device_exists(Devices, DeviceId):
        return

    for unit in list(Devices[DeviceId].Units):
        update_battery_device_unit_api(self, Devices, DeviceId, unit, battery_level)


def update_battery_device_unit_api(self, Devices, DeviceId_, Unit_, battery_level):
    self.log.logging("AbstractDz", "Debug",
                     f"update_battery_device_unit_api: {DeviceId_} / {Unit_} to {battery_level}")

    if not _device_unit_exists(Devices, DeviceId_, Unit_):
        return

    if domo_read_BatteryLevel(self, Devices, DeviceId_, Unit_) == battery_level:
        return

    nValue, sValue = domo_read_nValue_sValue(self, Devices, DeviceId_, Unit_)
    domo_update_api(self, Devices, DeviceId_, Unit_, nValue, sValue,
                    BatteryLevel=battery_level, SuppressTriggers=True)


def _switch_off_widget_due_to_timedout(self, Devices, DevicesId, Unit, _nValue, _sValue):
    self.log.logging("Widget", "Debug",
                     f"_switch_off_widget_due_to_timedout DeviceId {DevicesId} unit {Unit}")

    if (_nValue == 1 and _sValue == "On") or _is_device_tobe_switched_off(self, Devices, DevicesId, Unit):
        domo_update_api(self, Devices, DevicesId, Unit, 0, "Off", TimedOut=1)
    else:
        domo_update_api(self, Devices, DevicesId, Unit, _nValue, _sValue, TimedOut=1)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def domoticz_log_api(message):
    Domoticz.Log(message)


def domoticz_debug_api(message):
    Domoticz.Debug(message)


def domoticz_error_api(message):
    Domoticz.Error(message)


def domoticz_status_api(message):
    Domoticz.Status(message)


# ---------------------------------------------------------------------------
# Widget-type helpers
# ---------------------------------------------------------------------------

def is_dimmable_switch(self, Devices, DeviceId, Unit):
    _switchType, _subType, _type = domo_read_SwitchType_SubType_Type(
        self, Devices, DeviceId, Unit
    )
    if None in (_switchType, _subType, _type):
        return None
    if check_widget(_switchType, _subType, _type) == "Dimmable_Switch":
        return find_partially_opened_nValue(_switchType, _subType, _type)
    return None


def is_dimmable_light(self, Devices, DeviceId, Unit):
    _switchType, _subType, _type = domo_read_SwitchType_SubType_Type(
        self, Devices, DeviceId, Unit
    )
    if None in (_switchType, _subType, _type):
        return None
    if check_widget(_switchType, _subType, _type) == "Dimmable_Light":
        return find_partially_opened_nValue(_switchType, _subType, _type)
    return None


def is_dimmable_blind(self, Devices, DeviceId, Unit):
    _switchType, _subType, _type = domo_read_SwitchType_SubType_Type(
        self, Devices, DeviceId, Unit
    )
    if None in (_switchType, _subType, _type):
        return None
    if check_widget(_switchType, _subType, _type) == "Blind":
        return find_partially_opened_nValue(_switchType, _subType, _type)
    return None


def find_partially_opened_nValue(switch_type, sub_type, widget_type):
    key = (switch_type, sub_type, widget_type)
    return DIMMABLE_WIDGETS.get(key, {}).get("partially_opened_nValue")


def check_widget(switch_type, sub_type, widget_type):
    key = (switch_type, sub_type, widget_type)
    return DIMMABLE_WIDGETS.get(key, {}).get("Widget")
