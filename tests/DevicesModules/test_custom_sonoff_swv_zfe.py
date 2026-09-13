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
    _ensure_stub("Modules.sendZigateCommand", raw_APS_request=MagicMock(name="raw_APS_request"))
    _ensure_stub("Modules.tools",
                 get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
                 get_and_inc_ZCL_SQN=MagicMock(name="get_and_inc_ZCL_SQN", return_value="2a"),
                 is_ack_tobe_disabled=MagicMock(name="is_ack_tobe_disabled", return_value=False),
                 retreive_cmd_payload_from_8002=MagicMock(name="retreive_cmd_payload_from_8002"))
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
    sonoff_module._swv_last_array_write.clear()
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


def test_manual_default_settings_duration_with_interval(sonoff_module, plugin):
    # 2 h session: 10 min bursts, 5 min pauses
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "duration_with_interval",
        "SONOFF_SWV_MANUAL_IRRIGATION_TOTAL_DURATION": 120,
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 10,
        "SONOFF_SWV_MANUAL_IRRIGATION_INTERVAL": 5,
    })

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 5)

    w = _written(sonoff_module)
    # mode=2, total=120, burst=10, interval=5, liter, amount 0, fail-safe defaults to the total
    assert w["data"] == "20" + "0c00" + "02" + "0078" + "000a" + "0005" + "01" + "0000" + "0078"


def test_manual_default_settings_interval_mode_limits(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "duration_with_interval",
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 90,       # burst > 60, clamped
        "SONOFF_SWV_MANUAL_IRRIGATION_TOTAL_DURATION": 30,  # < burst, raised to the burst
        "SONOFF_SWV_MANUAL_IRRIGATION_INTERVAL": 0,        # < 1, clamped
    })

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", "duration_with_interval")

    w = _written(sonoff_module)
    assert w["data"] == "20" + "0c00" + "02" + "003c" + "003c" + "0001" + "01" + "0000" + "003c"


def test_manual_default_settings_interval_mode_burst_floor(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "duration_with_interval",
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 2,        # below the 3-min firmware floor, raised
        "SONOFF_SWV_MANUAL_IRRIGATION_TOTAL_DURATION": 30,
        "SONOFF_SWV_MANUAL_IRRIGATION_INTERVAL": 5,
    })

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 2)

    w = _written(sonoff_module)
    assert w["data"] == "20" + "0c00" + "02" + "001e" + "0003" + "0005" + "01" + "0000" + "001e"


def test_manual_default_settings_written_once_per_param_save(sonoff_module, plugin):
    # sanity_check_of_param calls the writer once per SONOFF_SWV_MANUAL_* key; identical payloads collapse to one write
    _use_params(sonoff_module, {"SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 719, "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "duration"})

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 719)
    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", "duration")

    assert sonoff_module.write_attribute.call_count == 1

    # a different payload (or another device) is written
    _use_params(sonoff_module, {"SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 30})
    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 30)
    sonoff_module.sonoff_swv_manual_default_settings(plugin, "5678", 30)

    assert sonoff_module.write_attribute.call_count == 3


def test_manual_default_settings_total_and_interval_ignored_in_duration_mode(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 719,
        "SONOFF_SWV_MANUAL_IRRIGATION_TOTAL_DURATION": 30,
    })

    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", 719)

    w = _written(sonoff_module)
    assert w["data"] == "20" + "0c00" + "00" + "02cf" + "02cf" + "000a" + "01" + "0000" + "02cf"


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


# ─── 0x501d manual default settings read-back (EvalFunc) ─────────────────────

def test_decode_manual_default_settings_read_from_device(sonoff_module, plugin):
    # Real read: mode=duration, total=10 min, irrigation duration/interval zeroed, liter, 0 L, no fail-safe
    res = sonoff_module.sonoff_swv_decode_manual_default_settings(plugin, "1234", "01", "fc11", "501d", "0000000a000000000100000000")

    assert res == {
        "irrigation_mode": "duration",
        "irrigation_duration": 10,
        "irrigation_amount_unit": "liter",
        "irrigation_amount": 0,
        "fail_safe": 0,
    }


def test_decode_manual_default_settings_round_trips_our_write(sonoff_module, plugin):
    _use_params(sonoff_module, {
        "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": 30,
        "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "capacity",
        "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT": "us_gallon",
        "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT": 100,
        "SONOFF_SWV_MANUAL_FAIL_SAFE": 45,
    })
    sonoff_module.sonoff_swv_manual_default_settings(plugin, "1234", "capacity")
    written = _written(sonoff_module)["data"]   # full array: 20 + 0c00 + elements

    res = sonoff_module.sonoff_swv_decode_manual_default_settings(plugin, "1234", "01", "fc11", "501d", written)

    assert res == {
        "irrigation_mode": "capacity",
        "irrigation_duration": 30,
        "irrigation_amount_unit": "us_gallon",
        "irrigation_amount": 100,
        "fail_safe": 45,
    }


@pytest.mark.parametrize("payload", ["zz", "00" + "00000a"])
def test_decode_manual_default_settings_rejects_bad_payloads(sonoff_module, plugin, payload):
    assert sonoff_module.sonoff_swv_decode_manual_default_settings(plugin, "1234", "01", "fc11", "501d", payload) is None
    assert any(call.args[1] == "Error" for call in plugin.log.logging.call_args_list)


# ─── fc11 command 0x06 / 0x07 irrigation plans ───────────────────────────────

@pytest.fixture
def raw_aps(sonoff_module, monkeypatch):
    mock = MagicMock(name="raw_APS_request")
    monkeypatch.setattr(sonoff_module, "raw_APS_request", mock)
    monkeypatch.setattr(sonoff_module, "get_and_inc_ZCL_SQN", MagicMock(return_value="2a"))
    monkeypatch.setattr(sonoff_module, "is_ack_tobe_disabled", MagicMock(return_value=False))
    return mock


def _sent(raw_aps):
    assert raw_aps.call_count == 1
    args = raw_aps.call_args.args
    # self, nwkid, ep, cluster, profile, payload
    assert (args[2], args[3], args[4]) == ("01", "fc11", "0104")
    return args[5]


def test_irrigation_plan_full_dict(sonoff_module, plugin, raw_aps):
    plan = {
        "plan_index": 2,
        "enable": True,
        "loop_type_mode": "weekdays",
        "loop_type_week_days": ["monday", "wednesday", "friday"],
        "enable_date": "2026-09-13",
        "start_time": "06:30",
        "irrigation_mode": "duration_with_interval",
        "irrigation_total_duration": 120,
        "irrigation_duration": 10,
        "interval_duration": 5,
        "irrigation_amount_unit": "liter",
        "irrigation_amount": 200,
        "fail_safe": 0,
        "create_datetime": "2026-09-13T12:00:00+00:00",
    }

    sonoff_module.sonoff_swv_irrigation_plan_settings(plugin, "1234", plan)

    payload = _sent(raw_aps)
    # ZCL header: manufacturer-specific cluster command, manuf 0x1286 LE, sqn, cmd 0x06
    assert payload[:10] == "05" + "8612" + "2a" + "06"
    data = bytes.fromhex(payload[10:])
    assert len(data) == 28
    enable_seconds = int((sonoff_module.datetime(2026, 9, 13) - sonoff_module.ZIGBEE_EPOCH_LOCAL).total_seconds())
    assert data == bytes(
        [0x02, 0x01, 0x03, 0x02 | 0x08 | 0x20]
        + list(enable_seconds.to_bytes(4, "big"))
        + [0x02]
        + list((6 * 3600 + 30 * 60).to_bytes(4, "big"))
        + [0x00, 0x78, 0x00, 0x0a, 0x00, 0x05, 0x01, 0x00, 0xc8, 0x00, 0x00]
        + list(int(sonoff_module.datetime(2026, 9, 13, 12, 0, 0, tzinfo=sonoff_module.timezone.utc).timestamp()).to_bytes(4, "big"))
    )


def test_irrigation_plan_defaults_and_day_interval(sonoff_module, plugin, raw_aps):
    sonoff_module.sonoff_swv_irrigation_plan_settings(plugin, "1234", {"start_time": "21:00", "loop_type_mode": "day_interval", "loop_type_interval_days": 3})

    data = bytes.fromhex(_sent(raw_aps)[10:])
    assert data[0:4] == bytes([0x00, 0x01, 0x02, 0x03])           # index 0, enabled, day_interval every 3 days
    assert data[8] == 0x00                                         # duration mode
    assert int.from_bytes(data[9:13], "big") == 21 * 3600
    # upstream defaults, except the irrigation duration raised to the 3-minute firmware floor
    assert data[13:24] == bytes([0x00, 0x0a, 0x00, 0x03, 0x00, 0x03, 0x01, 0x00, 0x1e, 0x00, 0x0a])
    assert abs(int.from_bytes(data[24:28], "big") - int(sonoff_module.time.time())) < 5


def test_irrigation_plan_list_sends_each_plan(sonoff_module, plugin, raw_aps):
    sonoff_module.sonoff_swv_irrigation_plan_settings(plugin, "1234", [
        {"plan_index": 0, "start_time": "06:00"},
        {"plan_index": 1, "start_time": "20:00", "enable": False},
    ])

    assert raw_aps.call_count == 2
    first, second = (bytes.fromhex(c.args[5][10:]) for c in raw_aps.call_args_list)
    assert (first[0], first[1]) == (0, 1)
    assert (second[0], second[1]) == (1, 0)


@pytest.mark.parametrize("plan", [
    {"start_time": "25:00"},                                   # bad time
    {},                                                        # start_time missing
    {"start_time": "06:00", "plan_index": 6},                  # index out of range
    {"start_time": "06:00", "irrigation_duration": 61},        # > 60
    {"start_time": "06:00", "irrigation_duration": 2},         # < 3: dropped silently by the firmware
    {"start_time": "06:00", "loop_type_mode": "monthly"},      # unknown loop type
    {"start_time": "06:00", "loop_type_mode": "weekdays", "loop_type_week_days": ["funday"]},
    {"start_time": "06:00", "enable_date": "13/09/2026"},
    {"start_time": "06:00", "irrigation_mode": "flood"},
    "not a dict",
])
def test_irrigation_plan_rejects_invalid(sonoff_module, plugin, raw_aps, plan):
    sonoff_module.sonoff_swv_irrigation_plan_settings(plugin, "1234", plan)

    assert raw_aps.call_count == 0
    assert any(call.args[1] == "Error" for call in plugin.log.logging.call_args_list)


def test_irrigation_plan_remove(sonoff_module, plugin, raw_aps):
    sonoff_module.sonoff_swv_irrigation_plan_remove(plugin, "1234", [1, 4])

    payloads = [c.args[5] for c in raw_aps.call_args_list]
    assert payloads == ["05" + "8612" + "2a" + "07" + "01", "05" + "8612" + "2a" + "07" + "04"]


def test_irrigation_plan_remove_rejects_bad_index(sonoff_module, plugin, raw_aps):
    sonoff_module.sonoff_swv_irrigation_plan_remove(plugin, "1234", 9)

    assert raw_aps.call_count == 0


# ─── fc11 command 0x06 status / 0x09 plan report ─────────────────────────────

def _raw_aps_payload(command, data):
    return "0d" + "8612" + "2a" + command + data   # server -> client, manufacturer specific


def test_read_raw_aps_stores_plan_report(sonoff_module, plugin, monkeypatch):
    plugin.ListOfDevices = {"1234": {"Sonoff": 5}}   # pre-existing scalar from a level-1-only config
    # index 1, enabled, weekdays mon+fri, enable date 2026-09-13, duration_with_interval, 06:30,
    # total 120, duration 10, interval 5, liter, 200, fail-safe 0, created 2026-09-13T12:00:00Z
    enable_seconds = int((sonoff_module.datetime(2026, 9, 13) - sonoff_module.ZIGBEE_EPOCH_LOCAL).total_seconds())
    created = int(sonoff_module.datetime(2026, 9, 13, 12, 0, 0, tzinfo=sonoff_module.timezone.utc).timestamp())
    record = bytes([0x01, 0x01, 0x03, 0x22] + list(enable_seconds.to_bytes(4, "big")) + [0x02]
                   + list((6 * 3600 + 30 * 60).to_bytes(4, "big"))
                   + [0x00, 0x78, 0x00, 0x0a, 0x00, 0x05, 0x01, 0x00, 0xc8, 0x00, 0x00]
                   + list(created.to_bytes(4, "big"))).hex()
    monkeypatch.setattr(sonoff_module, "retreive_cmd_payload_from_8002", lambda payload: (None, False, "2a", "1286", "09", record))

    sonoff_module.sonoffReadRawAPS(plugin, None, "1234", "01", "fc11", "0000", "01", _raw_aps_payload("09", record))

    stored = plugin.ListOfDevices["1234"]["Sonoff"]["IrrigationPlans"]["1"]
    assert stored == {
        "plan_index": 1,
        "enable": True,
        "loop_type_mode": "weekdays",
        "loop_type_interval_days": 0,
        "loop_type_week_days": ["monday", "friday"],
        "enable_date": "2026-09-13",
        "irrigation_mode": "duration_with_interval",
        "start_time": "06:30",
        "irrigation_total_duration": 120,
        "irrigation_duration": 10,
        "interval_duration": 5,
        "irrigation_amount_unit": "liter",
        "irrigation_amount": 200,
        "fail_safe": 0,
        "create_datetime": sonoff_module.datetime.fromtimestamp(created, sonoff_module.timezone.utc).astimezone().isoformat(timespec="seconds"),
    }


def test_read_raw_aps_plan_settings_status(sonoff_module, plugin, monkeypatch):
    plugin.ListOfDevices = {"1234": {}}
    monkeypatch.setattr(sonoff_module, "retreive_cmd_payload_from_8002", lambda payload: (None, False, "2a", "1286", "06", "01"))

    sonoff_module.sonoffReadRawAPS(plugin, None, "1234", "01", "fc11", "0000", "01", _raw_aps_payload("06", "01"))

    assert any(call.args[1] == "Error" and "status: 01" in call.args[2] for call in plugin.log.logging.call_args_list)


@pytest.mark.parametrize("data, level", [("0600", "Log"), ("0700", "Log"), ("0687", "Error")])
def test_read_raw_aps_default_response_to_plan_commands(sonoff_module, plugin, monkeypatch, data, level):
    # Real frame from an SWV-ZFE after a 0x06 write: 1c 8612 05 0b 0600 (global Default Response, manufacturer specific)
    plugin.ListOfDevices = {"1234": {}}
    monkeypatch.setattr(sonoff_module, "retreive_cmd_payload_from_8002", lambda payload: (True, True, "05", "1286", "0b", data))

    sonoff_module.sonoffReadRawAPS(plugin, None, "1234", "01", "fc11", "0000", "01", "1c8612050b" + data)

    assert any(call.args[1] == level and "command 0x%s status: %s" % (data[:2], data[2:]) in call.args[2] for call in plugin.log.logging.call_args_list)


def test_read_raw_aps_ignores_other_global_commands(sonoff_module, plugin, monkeypatch):
    plugin.ListOfDevices = {"1234": {}}
    monkeypatch.setattr(sonoff_module, "retreive_cmd_payload_from_8002", lambda payload: (False, True, "05", "1286", "01", "1d5000"))

    sonoff_module.sonoffReadRawAPS(plugin, None, "1234", "01", "fc11", "0000", "01", "1c8612050b0600")

    assert not any(call.args[1] in ("Log", "Error") for call in plugin.log.logging.call_args_list)


def test_read_raw_aps_ignores_other_clusters(sonoff_module, plugin, monkeypatch):
    plugin.ListOfDevices = {"1234": {}}
    spy = MagicMock()
    monkeypatch.setattr(sonoff_module, "retreive_cmd_payload_from_8002", spy)

    sonoff_module.sonoffReadRawAPS(plugin, None, "1234", "01", "0006", "0000", "01", "010a00")

    assert spy.call_count == 0
