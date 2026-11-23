#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ts0601_sampling_interval (Modules/tuyaTS0601.py).

The value was snapped to 5 s and clamped to 5..1200 s, then the result was dropped
and the raw value sent to the device.

Modules/tuyaTS0601.py is loaded from its file under a private name, on stubbed
dependencies: other test files leave a stub of it in sys.modules.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "Modules" / "tuyaTS0601.py"
NWKID = "bee7"
MODEL = "NTCHT01-sonde-temp-humi"
DP_SAMPLING = 0x65

DEPENDENCIES = {
    "Modules.domoMaj": ("MajDomoDevice",),
    "Modules.domoTools": ("Update_Battery_Device",),
    "Modules.tools": (
        "checkAndStoreAttributeValue", "get_and_inc_ZCL_SQN", "get_device_config_param",
        "get_deviceconf_parameter_value", "getAttributeValue", "twos_complement"),
    "Modules.tuyaTools": ("get_tuya_attribute", "store_tuya_attribute", "tuya_cmd"),
}


@pytest.fixture
def ts0601(monkeypatch):
    for name, attrs in DEPENDENCIES.items():
        stub = types.ModuleType(name)
        for attr in attrs:
            setattr(stub, attr, MagicMock(name=attr))
        monkeypatch.setitem(sys.modules, name, stub)

    spec = importlib.util.spec_from_file_location("tuyaTS0601_under_test", SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.get_and_inc_ZCL_SQN.return_value = "18"
    return mod


@pytest.fixture
def plugin():
    obj = MagicMock()
    obj.ListOfDevices = {NWKID: {"Model": MODEL, "Param": {}}}
    obj.DeviceConf = {MODEL: {"TS0601_DP": {
        "65": {"store_tuya_attribute": "sampling_interval", "action_type": "SamplingInterval"}}}}
    return obj


def _sent(mod):
    """ The (action, data) of each Tuya command sent """
    return [call.args[6:8] for call in mod.tuya_cmd.call_args_list]


def _logged(plugin, level):
    return [call for call in plugin.log.logging.call_args_list if call.args[1] == level]


@pytest.mark.parametrize("value, expected", [
    (5, 5), (60, 60), (300, 300), (1200, 1200),     # valid, sent unchanged
    (1, 5), (3, 5),                                 # below the minimum
    (1201, 1200), (5000, 1200),                     # above the maximum
    (62, 60), (63, 65),                             # snapped on the 5 s grid
    ("120", 120), (59.9, 60),                       # as they can come from the WebUI
])
def test_value_sent_to_the_device(ts0601, plugin, value, expected):
    ts0601.ts0601_sampling_interval(plugin, NWKID, "01", DP_SAMPLING, value)
    assert _sent(ts0601) == [("6502", "%08x" % expected)]


@pytest.mark.parametrize("value", [0, -60, "", "abc", [], {}, float("inf"), float("nan")])
def test_unusable_value_is_not_sent_and_is_reported(ts0601, plugin, value):
    ts0601.ts0601_sampling_interval(plugin, NWKID, "01", DP_SAMPLING, value)

    assert _sent(ts0601) == []
    (error,) = _logged(plugin, "Error")
    assert error.args[3] == NWKID
    assert error.args[4]["Error code"] == "TS0601-SAMPLING-01"


def test_no_value_is_not_sent(ts0601, plugin):
    ts0601.ts0601_sampling_interval(plugin, NWKID, "01", DP_SAMPLING, None)
    assert _sent(ts0601) == []
    assert _logged(plugin, "Error") == []


@pytest.mark.parametrize("value, logged", [(60, 0), ("60", 0), (7, 1), (5000, 1)])
def test_an_adjusted_value_is_logged(ts0601, plugin, value, logged):
    ts0601.ts0601_sampling_interval(plugin, NWKID, "01", DP_SAMPLING, value)
    assert len(_logged(plugin, "Log")) == logged


def test_through_the_device_parameter(ts0601, plugin):
    # The path of a Param change: sanity_check_of_param -> ts0601_settings -> ts0601_actuator
    mapping = plugin.DeviceConf[MODEL]["TS0601_DP"]
    ts0601.ts0601_settings(plugin, NWKID, mapping, "SamplingInterval", 5000)
    assert _sent(ts0601) == [("6502", "000004b0")]
