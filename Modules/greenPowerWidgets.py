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
Domoticz widgets of Green Power devices (GPD).

A GPD gets the same widgets as a Zigbee device: declared in certified JSON
(`Ep` / `Type`), created with the existing widget definitions, updated by the
existing per-widget-type code (Modules/domoMaj.py maj_domo_widgets()). What is
Green Power specific is only:

- matching a GPD to its configuration. A GPD has no Basic cluster and no Model
  string; certified JSON identifies it with a top-level key
      "GreenPower": {"DeviceID": "02", "ManufacturerID": "xxxx", "ModelID": "xxxx"}
  (lowercase hex). Most specific match first: DeviceID + ManufacturerID +
  ModelID, then DeviceID + ManufacturerID, then DeviceID alone (generic config
  per GP device type). Last resort, built into the plugin: widgets derived from
  the commands the GPD declared at commissioning. The plugin ships before the
  certified GP configs, so a GPD must get widgets without them;
- translating a GPD command into the ZCL cluster / value the widget code
  understands (GP_COMMAND_TO_ZCL);
- where the device lives: the Green Power device store (Modules/greenPowerStore.py),
  keyed by synthetic IEEE, never ListOfDevices. The store record holds
  "Model" and "Ep": {ep: {"ClusterType": {widget idx: widget type}}}, the
  same shape as a ListOfDevices record.

First version: On/Off (GPD commands Off / On / Toggle → cluster 0006 →
Switch). Scenes, buttons, move/step, sensors: later.
"""

from Modules.domoCreate import SIMPLE_WIDGET, set_default_value
from Modules.domoMaj import maj_domo_widgets
from Modules.domoticzAbstractLayer import (domo_create_api,
                                           domo_read_nValue_sValue,
                                           find_widget_unit_from_WidgetID,
                                           retreive_free_unit_for_widget)
from Modules.greenPowerFeed import gp_feed, gp_src_id
from Modules.greenPowerStore import (GP_WIDGET_CREATION_REQUESTS, gp_store,
                                     request_gp_store_flush)

GP_CONFIG_KEY = "GreenPower"

# GPD command id → (cluster, value). TOGGLE is resolved per widget from its current state.
TOGGLE = "toggle"
GP_COMMAND_TO_ZCL = {
    0x20: ("0006", "00"),    # Off
    0x21: ("0006", "01"),    # On
    0x22: ("0006", TOGGLE),  # Toggle
}

# Built-in fallback: GPD commands → widget type
GP_ONOFF_COMMANDS = {0x20, 0x21, 0x22}

# Commands a GPD of a given GP Device ID supports when it declared none (GP spec, Device ID table)
GP_DEVICE_ID_DEFAULT_COMMANDS = {
    0x02: sorted(GP_ONOFF_COMMANDS),  # On/Off switch
}

BUILTIN_MODEL_PREFIX = "GreenPower-"
DEFAULT_WIDGET_EP = "01"


# ─── Configuration ──────────────────────────────────────────────────────────

def _hex(value, digits):
    return None if value is None else "%0*x" % (digits, int(value))


def find_gp_device_config(self, record):
    """
    (model name, configuration) for a GPD store record, from certified JSON
    (self.DeviceConf) or, as last resort, built from its declared commands.
    (None, None) when nothing applies.
    """
    device_id = _hex(record.get("device_id"), 2)
    manufacturer_id = _hex(record.get("manufacturer_id"), 4)
    model_id = _hex(record.get("model_id"), 4)

    candidates = {}
    for model_name, conf in getattr(self, "DeviceConf", {}).items():
        gp = conf.get(GP_CONFIG_KEY) if isinstance(conf, dict) else None
        if not isinstance(gp, dict) or str(gp.get("DeviceID", "")).lower() != device_id:
            continue
        conf_manuf = str(gp["ManufacturerID"]).lower() if "ManufacturerID" in gp else None
        conf_model = str(gp["ModelID"]).lower() if "ModelID" in gp else None
        if conf_manuf is None and conf_model is None:
            candidates.setdefault(1, (model_name, conf))
        elif conf_manuf == manufacturer_id and conf_model is None:
            candidates.setdefault(2, (model_name, conf))
        elif conf_manuf == manufacturer_id and conf_model == model_id:
            candidates.setdefault(3, (model_name, conf))

    if candidates:
        return candidates[max(candidates)]

    return builtin_gp_device_config(record)


def builtin_gp_device_config(record):
    """Last resort: widgets from the commands the GPD declared (or the standard set of its Device ID)."""
    device_id = record.get("device_id")
    commands = set(record.get("commands") or GP_DEVICE_ID_DEFAULT_COMMANDS.get(device_id, []))

    if commands & GP_ONOFF_COMMANDS:
        return BUILTIN_MODEL_PREFIX + "OnOff", {"Ep": {DEFAULT_WIDGET_EP: {"0006": "", "Type": "Switch"}}}

    return None, None


def _widget_types(ep_conf):
    widget_type = ep_conf.get("Type", "") if isinstance(ep_conf, dict) else ""
    return [t for t in str(widget_type).split("/") if t]


# ─── Creation (heartbeat only) ──────────────────────────────────────────────

def process_gp_widget_creation_requests(self, Devices):
    """Carry out the creations queued by greenPowerStore.request_gp_widget_creation(). Heartbeat only."""
    queued = getattr(self, GP_WIDGET_CREATION_REQUESTS, None)
    while queued:
        create_gp_widgets(self, Devices, queued.pop())


def create_gp_widgets(self, Devices, ieee):
    """Create the widgets of a GPD that has none yet. A GPD commissioned again keeps its widgets."""
    store = gp_store(self)
    record = store.get(ieee) if store is not None else None
    if record is None:
        return

    nwk = record.get("nwk")
    if any(ep.get("ClusterType") for ep in (record.get("Ep") or {}).values()):
        self.log.logging("GreenPower", "Debug", "Green Power device %s already has its widgets" % ieee, nwk)
        return

    model_name, conf = find_gp_device_config(self, record)
    if conf is None:
        self.log.logging("GreenPower", "Status", "Green Power device %s: unknown model, no widget (device_id %s, manufacturer_id %s, model_id %s, commands %s)" % (
            ieee, record.get("device_id"), record.get("manufacturer_id"), record.get("model_id"), record.get("commands")), nwk)
        gp_feed(self).add("no-widget", IEEE=ieee, SrcId=gp_src_id(ieee), NwkId=nwk, DeviceId=record.get("device_id"))
        return

    nick_name = conf.get("NickName") or model_name
    ep_records = {}
    for ep, ep_conf in (conf.get("Ep") or {}).items():
        cluster_type = {}
        for widget_type in _widget_types(ep_conf):
            widget_idx = _create_gp_widget(self, Devices, ieee, nwk, ep, widget_type, nick_name)
            if widget_idx is not None:
                cluster_type[str(widget_idx)] = SIMPLE_WIDGET[widget_type].get("ForceClusterType") or widget_type
        if cluster_type:
            ep_records[ep] = {"ClusterType": cluster_type}

    store.update(ieee, {"Model": model_name, "Ep": ep_records})
    request_gp_store_flush(self)
    created = sum(len(e["ClusterType"]) for e in ep_records.values())
    self.log.logging("GreenPower", "Status", "Green Power device %s: %s widget(s) created as %s" % (ieee, created, model_name), nwk)
    gp_feed(self).add("widgets", IEEE=ieee, SrcId=gp_src_id(ieee), NwkId=nwk, Model=model_name, Widgets=created)


def _create_gp_widget(self, Devices, ieee, nwk, ep, widget_type, nick_name):
    """Create one widget with the definition the Zigbee path uses for the same type (SIMPLE_WIDGET)."""
    widget_record = SIMPLE_WIDGET.get(widget_type)
    if widget_record is None:
        self.log.logging("GreenPower", "Error", "Green Power device %s: widget type %s not supported for Green Power yet" % (ieee, widget_type),
                         nwk, {"Error code": "GPWIDGET-TYPE-01", "WidgetType": widget_type})
        return None

    unit = retreive_free_unit_for_widget(self, Devices, ieee)
    if unit is None:
        self.log.logging("GreenPower", "Error", "Green Power device %s: no free Domoticz unit for %s" % (ieee, widget_type),
                         nwk, {"Error code": "GPWIDGET-UNIT-01", "WidgetType": widget_type})
        return None

    widget_idx = domo_create_api(
        self, Devices, ieee, unit, "%s_%s-%s-%s" % (nick_name, widget_type, ieee, ep),
        widgetType=widget_record.get("widgetType"),
        Type_=widget_record.get("Type"),
        Subtype_=widget_record.get("Subtype"),
        Switchtype_=widget_record.get("Switchtype"),
        Image=widget_record.get("Image"),
    )
    if widget_idx is None or widget_idx == -1:
        self.log.logging("GreenPower", "Error", "Green Power device %s: Domoticz refused widget %s" % (ieee, widget_type),
                         nwk, {"Error code": "GPWIDGET-CREATE-01", "WidgetType": widget_type})
        return None

    set_default_value(self, Devices, ieee, unit, widget_record)
    return widget_idx


# ─── Update ─────────────────────────────────────────────────────────────────

def update_gp_widgets(self, Devices, ieee, command_id):
    """Update the widgets of a GPD with a command it sent (9e01)."""
    translation = GP_COMMAND_TO_ZCL.get(command_id)
    if translation is None:
        return

    store = gp_store(self)
    record = store.get(ieee) if store is not None else None
    if record is None:
        return

    cluster, value = translation
    model_name = record.get("Model", "")
    for ep, ep_record in (record.get("Ep") or {}).items():
        for widget_idx, widget_type in (ep_record.get("ClusterType") or {}).items():
            widget_value = _toggled_value(self, Devices, ieee, widget_idx) if value == TOGGLE else value
            if widget_value is None:
                continue
            maj_domo_widgets(self, Devices, None, ieee, model_name, [(ep, widget_idx, widget_type)], ep, cluster, widget_value)


def _toggled_value(self, Devices, ieee, widget_idx):
    """On/Off value opposite to the widget's current state; None when the widget is gone."""
    unit = find_widget_unit_from_WidgetID(self, widget_idx)
    if unit is None:
        return None
    nValue, _ = domo_read_nValue_sValue(self, Devices, ieee, unit)
    return "00" if nValue else "01"
