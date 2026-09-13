#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Sonoff SWV-ZFE / SWV-ZFU Param handlers in
DevicesModules.custom_sonoff.

On these valves a plain On starts a single irrigation session whose length is
the fc11 0x501d "manualDefaultSettings" array (factory default: 2 minutes),
after which the valve closes by itself. The array layout and the 0x5020 /
0x5021 encodings mirror zigbee-herdsman-converters (src/devices/sonoff.ts).
"""

import os
import sys
import types
import importlib

import pytest
from unittest.mock import MagicMock


def _ensure_stub(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def sonoff_module():
    _ensure_stub("Modules.basicOutputs", write_attribute=MagicMock(name="write_attribute"))
    _ensure_stub("Modules.tools", get_device_config_param=MagicMock(name="get_device_config_param", return_value=None))
    _ensure_stub("Modules.zigateConsts", ZIGATE_EP="01")

    # DevicesModules/__init__.py imports every custom_* module (and their real
    # plugin dependencies); register a bare package pointing at the real
    # directory so only custom_sonoff is loaded.
    injected_pkg = "DevicesModules" not in sys.modules
    if injected_pkg:
        pkg = types.ModuleType("DevicesModules")
        pkg.__path__ = [os.path.join(os.path.dirname(__file__), "..", "..", "DevicesModules")]
        sys.modules["DevicesModules"] = pkg

    sys.modules.pop("DevicesModules.custom_sonoff", None)
    mod = importlib.import_module("DevicesModules.custom_sonoff")
    yield mod
    sys.modules.pop("DevicesModules.custom_sonoff", None)
    if injected_pkg:
        sys.modules.pop("DevicesModules", None)


@pytest.fixture
def plugin(sonoff_module):
    self = MagicMock(name="plugin")
    self.log.logging = MagicMock(name="logging")
    sonoff_module.write_attribute.reset_mock()
    return self


def _use_params(sonoff_module, params):
    sonoff_module.get_device_config_param.side_effect = lambda self, nwkid, key: params.get(key)


def _written(sonoff_module):
    assert sonoff_module.write_attribute.call_count == 1
    args = sonoff_module.write_attribute.call_args.args
    # self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data
    return {"cluster": args[4], "manuf_id": args[5], "manuf_spec": args[6], "attribute": args[7], "data_type": args[8], "data": args[9]}


# ─── 0x501d manual default settings ───────────────────────────────────────────

def test_manual_default_settings_only_duration(sonoff_module, plugin):
    _use_params(sonoff_module, {"SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 719})

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 719)

    w = _written(sonoff_module)
    assert (w["cluster"], w["manuf_id"], w["manuf_spec"], w["attribute"], w["data_type"]) == ("fc11", "1286", "01", "501d", "48")
    # elementType uint8, 12 elements (LE count), then: mode=duration, total=719, duration=719,
    # interval=10, unit=liter, amount=0, fail_safe defaults to duration (all big endian)
    assert w["data"] == "20" + "0c00" + "00" + "02cf" + "02cf" + "000a" + "01" + "0000" + "02cf"


def test_manual_default_settings_capacity_mode(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 30,
        "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "capacity",
        "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT": "us_gallon",
        "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT": 100,
        "SONOFF_SWV_MANUAL_FAIL_SAFE": 45,
    })

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", "capacity")

    w = _written(sonoff_module)
    assert w["data"] == "20" + "0c00" + "01" + "001e" + "001e" + "000a" + "00" + "0064" + "002d"


def test_manual_default_settings_clamps_and_rejects_bad_values(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 5000,       # > 719, clamped
        "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "bogus",       # rejected -> duration
        "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT": "abc",       # rejected -> 0
    })

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 5000)

    w = _written(sonoff_module)
    assert w["data"] == "20" + "0c00" + "00" + "02cf" + "02cf" + "000a" + "01" + "0000" + "02cf"
    error_logs = [c for c in plugin.log.logging.call_args_list if c.args[1] == "Error"]
    assert len(error_logs) == 2


# ─── 0x5020 valve alarm settings ──────────────────────────────────────────────

def test_valve_alarm_settings_defaults(sonoff_module, plugin):
    _use_params(sonoff_module, {"SONOFF_SWV_ALARM_WATER_LEAK": 0})

    sonoff_module.sonoff_swv_valve_alarm_settings(plugin, "1234", 0)

    w = _written(sonoff_module)
    assert (w["attribute"], w["data_type"]) == ("5020", "48")
    # no alarms, shortage duration 5 min, leak duration 1 min, reserved 0
    assert w["data"] == "20" + "0400" + "00" + "05" + "01" + "00"


def test_valve_alarm_settings_all_enabled(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_ALARM_WATER_SHORTAGE": 1,
        "SONOFF_SWV_ALARM_WATER_LEAK": 1,
        "SONOFF_SWV_WATER_SHORTAGE_AUTO_CLOSE": 1,
        "SONOFF_SWV_ALARM_WATER_SHORTAGE_DURATION": 10,
        "SONOFF_SWV_ALARM_WATER_LEAK_DURATION": 3,
    })

    sonoff_module.sonoff_swv_valve_alarm_settings(plugin, "1234", 1)

    w = _written(sonoff_module)
    assert w["data"] == "20" + "0400" + "0b" + "0a" + "03" + "00"


# ─── 0x5021 unit of water flow ────────────────────────────────────────────────

@pytest.mark.parametrize("unit,expected", [("liter", "00"), ("us_gallon", "01"), ("imperial_gallon", "02")])
def test_water_flow_unit(sonoff_module, plugin, unit, expected):
    sonoff_module.sonoff_swv_water_flow_unit(plugin, "1234", unit)

    w = _written(sonoff_module)
    assert (w["attribute"], w["data_type"], w["data"]) == ("5021", "20", expected)


def test_water_flow_unit_rejects_unknown(sonoff_module, plugin):
    sonoff_module.sonoff_swv_water_flow_unit(plugin, "1234", "pint")

    assert sonoff_module.write_attribute.call_count == 0


# ─── registry ─────────────────────────────────────────────────────────────────

def test_params_are_registered(sonoff_module):
    reg = sonoff_module.SONOFF_DEVICE_PARAMETERS
    for key in ("SONOFF_SWV_MANUAL_IRRIGATION_DURATION", "SONOFF_SWV_MANUAL_IRRIGATION_MODE",
                "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT", "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT",
                "SONOFF_SWV_MANUAL_FAIL_SAFE"):
        assert reg[key] is sonoff_module.sonoff_swv_manual_default_settings
    for key in ("SONOFF_SWV_ALARM_WATER_SHORTAGE", "SONOFF_SWV_ALARM_WATER_LEAK", "SONOFF_SWV_WATER_SHORTAGE_AUTO_CLOSE",
                "SONOFF_SWV_ALARM_WATER_SHORTAGE_DURATION", "SONOFF_SWV_ALARM_WATER_LEAK_DURATION"):
        assert reg[key] is sonoff_module.sonoff_swv_valve_alarm_settings
    assert reg["SONOFF_SWV_WATER_FLOW_UNIT"] is sonoff_module.sonoff_swv_water_flow_unit
    assert reg["SONOFF_CHILD_LOCK"] is sonoff_module.sonoff_child_lock
