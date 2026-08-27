#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readZclClusters.py:process_cluster_attribute_response

Coverage:
  - TUYA_REMOTE-flagged devices (e.g. TS0041 and its siblings): a plain OnOff
    (cluster 0x0006 attribute 0x0000) Report Attributes frame must NOT reach
    action_majdomodevice()/MajDomoDevice(). This is the code path actually
    taken in production for this traffic: Conf/ZclDefinitions/0006.json
    declares attribute 0000 as a generic, always-enabled ZCL attribute with
    ActionList ["check_store_value", "upd_domo_device"], so ReadCluster()'s
    is_cluster_zcl_config_available() check routes every 0006/0000 message
    through this function - never through readClusters.py:Cluster0006(),
    regardless of device model.
  - Non-TUYA_REMOTE devices are unaffected: the OnOff attribute report still
    reaches action_majdomodevice() as before (regression guard).
  - check_store_value still runs for TUYA_REMOTE devices (bookkeeping kept).
"""

import sys
import types
import importlib
from unittest.mock import MagicMock

import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def rzc():
    """Import Modules.readZclClusters with all external deps stubbed out."""
    stubs = {
        "DevicesModules": _make_stub(
            "DevicesModules", FUNCTION_MODULE={}, FUNCTION_WITH_ACTIONS_MODULE={}
        ),
        "Modules.batterieManagement": _make_stub(
            "Modules.batterieManagement", UpdateBatteryAttribute=MagicMock(name="UpdateBatteryAttribute")
        ),
        "Modules.domoMaj": _make_stub(
            "Modules.domoMaj", MajDomoDevice=MagicMock(name="MajDomoDevice")
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
            get_device_config_param=MagicMock(name="get_device_config_param", return_value=False),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            getAttributeValue=MagicMock(name="getAttributeValue"),
            store_battery_percentage_time_stamp=MagicMock(name="store_battery_percentage_time_stamp"),
            store_battery_voltage_time_stamp=MagicMock(name="store_battery_voltage_time_stamp"),
        ),
        "Modules.zclClusterHelpers": _make_stub(
            "Modules.zclClusterHelpers",
            decoding_attribute_data=MagicMock(name="decoding_attribute_data", return_value="00"),
            handle_model_name=MagicMock(name="handle_model_name"),
        ),
    }

    tracked = list(stubs) + ["Modules.readZclClusters"]
    saved = {name: sys.modules.get(name) for name in tracked}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.readZclClusters", None)
    module = importlib.import_module("Modules.readZclClusters")

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


ONOFF_CLUSTER_DEF = {
    "Description": "On/Off",
    "Version": "1",
    "Attributes": {
        "0000": {
            "Enabled": True,
            "Name": "OnOff",
            "DataType": "10",
            "Mandatory": True,
            "ActionList": ["check_store_value", "upd_domo_device"],
        }
    },
}


def _plugin(model, tuya_remote):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {"TrackingEraticValue": False, "trackZclClustersIn": False}
    p.ListOfDevices = {NWKID: {"Model": model}}
    p.DeviceConf = {model: {"Ep": {EP: {"0006": ""}}}}
    if tuya_remote:
        p.DeviceConf[model]["TUYA_REMOTE"] = True
    p.readZclClusters = {"0006": ONOFF_CLUSTER_DEF}
    return p


NWKID = "c4b2"
EP = "01"
CLUSTER = "0006"
ATTR_ONOFF = "0000"


def test_tuya_remote_onoff_report_does_not_reach_majdomodevice(rzc, monkeypatch):
    """Regression: a TS0041-style plain OnOff heartbeat must not drive a Domoticz update."""
    maj_domo = MagicMock()
    check_store = MagicMock()
    get_devconf = MagicMock(side_effect=lambda self_, model, attr, return_default=None: True if attr == "TUYA_REMOTE" else return_default)
    monkeypatch.setattr(rzc, "MajDomoDevice", maj_domo)
    monkeypatch.setattr(rzc, "checkAndStoreAttributeValue", check_store)
    monkeypatch.setattr(rzc, "get_deviceconf_parameter_value", get_devconf)

    p = _plugin(model="TS0041", tuya_remote=True)
    rzc.process_cluster_attribute_response(p, {}, "01", NWKID, EP, CLUSTER, ATTR_ONOFF, "10", "0001", "00", Source="8102")

    maj_domo.assert_not_called()
    check_store.assert_called_once_with(p, NWKID, EP, CLUSTER, ATTR_ONOFF, "00")


def test_non_tuya_remote_onoff_report_reaches_majdomodevice(rzc, monkeypatch):
    """Regression guard: ordinary OnOff devices keep driving MajDomoDevice as before."""
    maj_domo = MagicMock()
    check_store = MagicMock()
    get_devconf = MagicMock(return_value=None)
    monkeypatch.setattr(rzc, "MajDomoDevice", maj_domo)
    monkeypatch.setattr(rzc, "checkAndStoreAttributeValue", check_store)
    monkeypatch.setattr(rzc, "get_deviceconf_parameter_value", get_devconf)

    p = _plugin(model="TS011F-plug", tuya_remote=False)
    rzc.process_cluster_attribute_response(p, {}, "01", NWKID, EP, CLUSTER, ATTR_ONOFF, "10", "0001", "00", Source="8102")

    maj_domo.assert_called_once()
    args = maj_domo.call_args.args
    assert args[1:5] == ({}, NWKID, EP, CLUSTER)
    check_store.assert_called_once_with(p, NWKID, EP, CLUSTER, ATTR_ONOFF, "00")
