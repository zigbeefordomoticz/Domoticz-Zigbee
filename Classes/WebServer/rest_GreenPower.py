#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Green Power devices (GPD) in the WebUI.

The GPDs live in the Green Power device store (Modules/greenPowerStore.py),
not in ListOfDevices, so the routes built on ListOfDevices never show them:

    /rcv-nw-hrdwr     Admin → Provisioning: rest_Provisioning appends the
                      entries built here for the GPDs commissioned since the
                      page opened pairing
    /zgp-device-raw   Tools → Data: the store content

The store record holds the GPD security key: it never leaves the plugin
(SECRET_FIELDS are dropped from every answer).
"""

import json
import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.greenPowerStore import gp_store

SECRET_FIELDS = ("security_key",)

# A GPD that has no widget this long after its commissioning gets none: its
# widgets are created at the next heartbeat, or never (unknown model)
GP_PROVISIONING_TIMEOUT = 60

GP_PROFILE_ID = "a1e0"
GP_PROFILE_DESC = "Green Power"

# GP Device IDs (Green Power specification, as zigpy.zgp.types.DeviceID)
GP_DEVICE_IDS = {
    0x00: "Simple Generic 1-state Switch",
    0x01: "Simple Generic 2-state Switch",
    0x02: "On/Off Switch",
    0x03: "Level Control Switch",
    0x04: "Simple Sensor",
    0x05: "Advanced Generic 1-state Switch",
    0x06: "Advanced Generic 2-state Switch",
    0x07: "Generic Switch",
    0x10: "Color Dimmer Switch",
    0x11: "Light Sensor",
    0x12: "Occupancy Sensor",
    0x20: "Door Lock Controller",
    0x30: "Temperature Sensor",
    0x31: "Pressure Sensor",
    0x32: "Flow Sensor",
    0x33: "Indoor Environment Sensor",
    0xFE: "Manufacturer specific",
}

# Model names of the built-in fallback (Modules/greenPowerWidgets.BUILTIN_MODEL_PREFIX)
BUILTIN_MODEL_PREFIX = "GreenPower-"


def public_gp_record(record):
    """A copy of a store record without its secrets."""
    return {key: value for key, value in record.items() if key not in SECRET_FIELDS}


def gp_widget_names(self, record):
    """Names of the Domoticz widgets of a GPD, from its ClusterType entries."""
    names = []
    widgets = getattr(self, "ListOfDomoticzWidget", None) or {}
    for ep_record in (record.get("Ep") or {}).values():
        for widget_idx in (ep_record.get("ClusterType") or {}):
            widget = widgets.get(int(widget_idx))
            if widget and widget.get("Name") and widget["Name"] not in names:
                names.append(widget["Name"])
    return names


def _has_widgets(record):
    return any(ep.get("ClusterType") for ep in (record.get("Ep") or {}).values())


def gp_new_hardware(self, ieee, record):
    """
    The /rcv-nw-hrdwr entry of a GPD, with the fields of a Zigbee device
    (NewHardware in the WebUI) plus GreenPower and WidgetList: a GPD is not in
    /zdevice-name, where the page finds the widgets of a Zigbee device.
    """
    device_id = record.get("device_id")
    model = record.get("Model") or ""
    return {
        "NwkId": record.get("nwk") or "",
        "GreenPower": True,
        "IEEE": ieee,
        "ProfileId": GP_PROFILE_ID,
        "ProfileIdDesc": GP_PROFILE_DESC,
        "ZDeviceID": "" if device_id is None else "%02x" % int(device_id),
        "ZDeviceIDDesc": GP_DEVICE_IDS.get(device_id, "Unknown") if device_id is not None else "Unknown",
        "Model": model,
        "PluginCertified": "no" if not model or model.startswith(BUILTIN_MODEL_PREFIX) else "yes",
        "Ep": [],
        "WidgetList": gp_widget_names(self, record),
    }


def gp_provisioning_entries(self, now=None):
    """
    /rcv-nw-hrdwr entries of the GPDs commissioned since pairing was opened
    from the page (self.GreenPowerInPairingMode: ieee → (commissioning time, nwk)).

    As for a Zigbee device: NwkId only while its widgets are not created yet,
    then once with ProvisionStatus, after which it leaves the queue.
    """
    now = time.time() if now is None else now
    pending = getattr(self, "GreenPowerInPairingMode", None)
    if not pending:
        return []

    store = gp_store(self)
    entries = []
    for ieee, (since, nwk) in list(pending.items()):
        record = store.get(ieee) if store is not None else None
        if record is None:
            # Removed meanwhile, or no store
            pending.pop(ieee, None)
            entries.append({"NwkId": nwk or "", "IEEE": ieee, "GreenPower": True, "ProvisionStatus": "Failed", "ProvisionStatusDesc": "Failed"})
            continue

        if _has_widgets(record):
            pending.pop(ieee, None)
            entry = gp_new_hardware(self, ieee, record)
            entry.update({"ProvisionStatus": "inDB", "ProvisionStatusDesc": "inDB"})
            entries.append(entry)
            continue

        if now - since > GP_PROVISIONING_TIMEOUT:
            # Commissioned, but no configuration gives it a widget
            pending.pop(ieee, None)
            entry = gp_new_hardware(self, ieee, record)
            entry.update({"ProvisionStatus": "Unexpected", "ProvisionStatusDesc": "No widget for this Green Power device"})
            entries.append(entry)
            continue

        entries.append({"NwkId": record.get("nwk") or "", "IEEE": ieee, "GreenPower": True})
    return entries


def rest_zgp_device_raw(self, verb, data, parameters):
    """
    GET /zgp-device-raw            the Green Power device store, one entry per GPD
    GET /zgp-device-raw/<ieee>     one GPD ({} when unknown)

    Each entry is the store record without its security key, plus IEEE and
    WidgetList.
    """
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if verb != "GET":
        return _response

    store = gp_store(self)
    records = store.snapshot() if store is not None else {}

    def entry(ieee, record):
        answer = public_gp_record(record)
        answer["IEEE"] = ieee
        answer["WidgetList"] = gp_widget_names(self, record)
        return answer

    if len(parameters) == 0:
        _response["Data"] = json.dumps([entry(ieee, record) for ieee, record in sorted(records.items())], sort_keys=False)
    elif len(parameters) == 1:
        ieee = parameters[0].lower()
        _response["Data"] = json.dumps(entry(ieee, records[ieee]) if ieee in records else {}, sort_keys=False)
    return _response
