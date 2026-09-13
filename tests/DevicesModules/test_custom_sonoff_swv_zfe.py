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


# ─── 0x501f irrigation schedule status (EvalFunc) ────────────────────────────
#
# Payloads are real "Foundation Cluster ... Attribute: 501f Type: 48" log lines from an
# SWV-ZFE (2026-09-09, Europe/Paris): the generic ARRAY decoder leaves the high count
# byte (00) in front of the elements.

def _local_iso(seconds_since_2000):
    from datetime import datetime, timedelta
    return (datetime(2000, 1, 1) + timedelta(seconds=seconds_since_2000)).astimezone().isoformat(timespec="seconds")


def _decode(sonoff_module, plugin, payload):
    return sonoff_module.sonoff_swv_irrigation_schedule_status(plugin, "1234", "01", "fc11", "501f", payload)


def test_schedule_status_running_report(sonoff_module, plugin):
    res = _decode(sonoff_module, plugin, "0002000100323467e932346a413234682d0100000011")

    assert res == {
        "schedule_status": "running",
        "schedule_index": 0,
        "schedule_type": "manual",
        "irrigation_mode": "duration",
        "start_time": _local_iso(0x323467e9),          # 2026-09-09 18:54:33 local
        "expected_end_time": _local_iso(0x32346a41),   # start + 600 s
        "actual_end_time": _local_iso(0x3234682d),     # start + 68 s
        "irrigation_amount_unit": "liter",
        "expected_irrigation_amount": 0,
        "actual_irrigation_amount": 17,
    }
    assert res["start_time"][:19] == "2026-09-09T18:54:33"


def test_schedule_status_end_report(sonoff_module, plugin):
    res = _decode(sonoff_module, plugin, "0001000100323467e932346a41323468480100000018")

    assert res["schedule_status"] == "end"
    assert res["actual_end_time"][:19] == "2026-09-09T18:56:08"
    assert res["actual_irrigation_amount"] == 24


def test_schedule_status_start_report_has_no_actuals(sonoff_module, plugin):
    res = _decode(sonoff_module, plugin, "00000001003234688b32346ae3010000")

    assert res == {
        "schedule_status": "start",
        "schedule_index": 0,
        "schedule_type": "manual",
        "irrigation_mode": "duration",
        "start_time": _local_iso(0x3234688b),
        "expected_end_time": _local_iso(0x32346ae3),
        "actual_end_time": None,
        "irrigation_amount_unit": "liter",
        "expected_irrigation_amount": 0,
        "actual_irrigation_amount": None,
    }


def test_schedule_status_standby_automatic_capacity(sonoff_module, plugin):
    # status=standby, index=3, type=automatic, mode=capacity, unit=us_gallon, expected=0x0064
    res = _decode(sonoff_module, plugin, "00" + "03030001" + "3234688b" + "32346ae3" + "00" + "0064")

    assert (res["schedule_status"], res["schedule_index"], res["schedule_type"], res["irrigation_mode"]) == ("standby", 3, "automatic", "capacity")
    assert (res["irrigation_amount_unit"], res["expected_irrigation_amount"]) == ("us_gallon", 100)


def test_schedule_status_accepts_full_array_and_bare_elements(sonoff_module, plugin):
    elements = "02000100323467e932346a413234682d0100000011"
    bare = _decode(sonoff_module, plugin, elements)
    full = _decode(sonoff_module, plugin, "20" + "1500" + elements)
    stripped = _decode(sonoff_module, plugin, "00" + elements)

    assert bare == full == stripped
    assert bare["actual_irrigation_amount"] == 17


def test_schedule_status_zero_timestamp_is_none(sonoff_module, plugin):
    res = _decode(sonoff_module, plugin, "00" + "00000100" + "00000000" + "32346ae3" + "01" + "0000")

    assert res["start_time"] is None
    assert res["expected_end_time"] == _local_iso(0x32346ae3)


@pytest.mark.parametrize("payload", [
    "zz",                                    # not hex
    "000200",                                # too short for the header
    "0002000100323467e932346a41",            # running report truncated (< 21 bytes)
    "00" + "09000100" + "3234688b" + "32346ae3" + "01" + "0000",   # unknown status
])
def test_schedule_status_rejects_bad_payloads(sonoff_module, plugin, payload):
    assert _decode(sonoff_module, plugin, payload) is None
    assert any(call.args[1] == "Error" for call in plugin.log.logging.call_args_list)
