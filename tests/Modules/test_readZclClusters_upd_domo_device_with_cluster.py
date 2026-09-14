#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readZclClusters.py:action_majdomodevice

"UpdDomoDeviceWithCluster" routes an attribute to the widget of another cluster; it now
accepts several targets (a list, or "A/B") so one attribute can feed several widgets with
the same value - e.g. the Sonoff SWV-ZFE 0x501f status record, decoded into a dict, drives
both the TextStatus ("text") and the Flow ("flow_l_min") widgets.
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
        "DevicesModules": _make_stub("DevicesModules", FUNCTION_MODULE={}, FUNCTION_WITH_ACTIONS_MODULE={}),
        "Modules.batterieManagement": _make_stub("Modules.batterieManagement", UpdateBatteryAttribute=MagicMock()),
        "Modules.domoMaj": _make_stub("Modules.domoMaj", MajDomoDevice=MagicMock(name="MajDomoDevice")),
        "Modules.tools": _make_stub(
            "Modules.tools",
            checkAndStoreAttributeValue=MagicMock(),
            get_device_config_param=MagicMock(return_value=False),
            get_deviceconf_parameter_value=MagicMock(return_value=None),
            getAttributeValue=MagicMock(),
            store_battery_percentage_time_stamp=MagicMock(),
            store_battery_voltage_time_stamp=MagicMock(),
        ),
        "Modules.zclClusterHelpers": _make_stub(
            "Modules.zclClusterHelpers", decoding_attribute_data=MagicMock(return_value="00"), handle_model_name=MagicMock()
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


NWKID, EP, CLUSTER, ATTR, MODEL = "86e6", "01", "fc11", "501f", "SWV-ZFE"


def _plugin(upd_domo_device_with_cluster):
    p = MagicMock()
    p.log.logging = MagicMock()
    attribute = {"Enabled": True, "Name": "IrrigationScheduleStatus", "DataType": "48", "ActionList": ["upd_domo_device"]}
    if upd_domo_device_with_cluster is not None:
        attribute["UpdDomoDeviceWithCluster"] = upd_domo_device_with_cluster
    p.DeviceConf = {MODEL: {"Ep": {EP: {CLUSTER: {"Attributes": {ATTR: attribute}}}}}}
    p.ListOfDevices = {NWKID: {"Model": MODEL}}
    return p


def _targets(rzc, plugin, value):
    maj_domo = MagicMock(name="MajDomoDevice")
    rzc.MajDomoDevice = maj_domo
    rzc.action_majdomodevice(plugin, {}, NWKID, EP, CLUSTER, ATTR, MODEL, value)
    return [c.args[4] for c in maj_domo.call_args_list], maj_domo


def test_single_cluster_override(rzc):
    plugin = _plugin("TextStatus")
    targets, maj_domo = _targets(rzc, plugin, {"text": "Running"})

    assert targets == ["TextStatus"]
    maj_domo.assert_called_once_with(plugin, {}, NWKID, EP, "TextStatus", {"text": "Running"}, Attribute_="")


def test_slash_separated_clusters_each_get_the_value(rzc):
    value = {"text": "Running", "flow_l_min": 14.4}
    targets, maj_domo = _targets(rzc, _plugin("TextStatus/Flow"), value)

    assert targets == ["TextStatus", "Flow"]
    assert [c.args[5] for c in maj_domo.call_args_list] == [value, value]


def test_list_of_clusters(rzc):
    targets, _ = _targets(rzc, _plugin(["TextStatus", "Flow"]), {"text": "x"})

    assert targets == ["TextStatus", "Flow"]


def test_no_override_uses_the_source_cluster(rzc):
    targets, _ = _targets(rzc, _plugin(None), 1)

    assert targets == [CLUSTER]
