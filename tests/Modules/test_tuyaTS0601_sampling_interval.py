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
        "get_deviceconf_parameter_value", "getAttributeValue", "mainPoweredDevice", "twos_complement"),
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
    obj.tuya_sampling_requests = {}
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


# ── ts0601_resend_sampling_interval ───────────────────────────────────────────
#
# Field case: the parameter was changed to 120, 300 then 5 s, the device kept 60 s,
# and 600 s after each rejoin: the only command sent was lost.

class _Clock:
    def __init__(self):
        self.now = 1_795_452_390.0

    def time(self):
        return self.now


@pytest.fixture
def clock(ts0601, monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(ts0601, "time", clock)
    return clock


@pytest.fixture
def awake(ts0601, plugin, clock):
    """ The device sends a frame, after `elapsed` seconds. Returns the number of commands sent since then """
    ts0601.mainPoweredDevice.return_value = False
    ts0601.get_tuya_attribute.side_effect = lambda self, nwkid, name: self.ListOfDevices[nwkid].get("Tuya", {}).get(name)

    def _awake(elapsed=60):
        clock.now += elapsed
        before = len(_sent(ts0601))
        ts0601.ts0601_resend_sampling_interval(plugin, NWKID)
        return len(_sent(ts0601)) - before

    return _awake


def _device(plugin, wanted=None, reported=None, **extra):
    device = plugin.ListOfDevices[NWKID]
    if wanted is not None:
        device["Param"]["SamplingInterval"] = wanted
    if reported is not None:
        device["Tuya"] = {"sampling_interval": "%08x" % reported}
    device.update(extra)
    return device


def test_resent_until_the_device_reports_it(ts0601, plugin, awake):
    _device(plugin, wanted=300, reported=600)
    assert [awake(), awake(), awake()] == [1, 1, 1]
    assert set(_sent(ts0601)) == {("6502", "0000012c")}

    _device(plugin, reported=300)
    assert [awake(), awake()] == [0, 0]
    assert plugin.tuya_sampling_requests == {}


def test_sent_once_per_burst_of_reports(plugin, awake):
    _device(plugin, wanted=300, reported=600)
    assert [awake(0.1) for _ in range(11)] == [1] + [0] * 10


def test_not_resent_right_after_the_parameter_was_sent(ts0601, plugin, awake):
    _device(plugin, wanted=300, reported=600)
    ts0601.ts0601_sampling_interval(plugin, NWKID, "01", DP_SAMPLING, 300)
    assert awake(1) == 0
    assert awake(60) == 1


def test_compared_with_the_value_really_sent(plugin, awake):
    # 5000 is sent as 1200: the device reporting 1200 has applied it
    _device(plugin, wanted=5000, reported=1200)
    assert awake() == 0


def test_gives_up_and_says_so_once(ts0601, plugin, awake):
    _device(plugin, wanted=300, reported=600)
    sent = sum(awake() for _ in range(ts0601.SAMPLING_RESEND_ATTEMPTS + 20))
    assert sent == ts0601.SAMPLING_RESEND_ATTEMPTS
    assert len(_logged(plugin, "Log")) == 1
    assert _logged(plugin, "Error") == []


def test_starts_again_when_the_parameter_changes(ts0601, plugin, awake):
    _device(plugin, wanted=300, reported=600)
    for _ in range(ts0601.SAMPLING_RESEND_ATTEMPTS + 1):
        awake()
    assert awake() == 0

    _device(plugin, wanted=120)
    assert awake() == 1
    assert _sent(ts0601)[-1] == ("6502", "00000078")


def test_starts_again_when_the_same_value_is_saved_again(ts0601, plugin, awake):
    _device(plugin, wanted=300, reported=600)
    for _ in range(ts0601.SAMPLING_RESEND_ATTEMPTS + 1):
        awake()
    ts0601.ts0601_sampling_interval(plugin, NWKID, "01", DP_SAMPLING, 300)
    assert awake() == 1


def test_rejoin_puts_the_device_back_to_its_own_interval(plugin, awake):
    _device(plugin, wanted=60, reported=60)
    assert awake() == 0
    _device(plugin, reported=600)
    assert awake() == 1


@pytest.mark.parametrize("setup", [
    dict(reported=600),                                         # no parameter
    dict(wanted=300),                                           # the device never reported it
    dict(wanted="abc", reported=600),                           # unusable parameter
    dict(wanted=300, reported=600, Health="Disabled"),
    dict(wanted=300, reported=600, Model="another model"),
    dict(wanted=300, reported=600, Param=None),
    dict(wanted=300, reported=600, Tuya={"sampling_interval": ""}),
])
def test_nothing_to_resend(plugin, awake, setup):
    _device(plugin, **setup)
    assert awake() == 0
    assert _logged(plugin, "Error") == []


def test_main_powered_device_is_left_alone(ts0601, plugin, awake):
    _device(plugin, wanted=300, reported=600)
    ts0601.mainPoweredDevice.return_value = True
    assert awake() == 0


def test_unknown_device(ts0601, plugin):
    ts0601.ts0601_resend_sampling_interval(plugin, "ffff")
    assert _sent(ts0601) == []


def test_a_device_without_the_datapoint(plugin, awake):
    _device(plugin, wanted=300, reported=600)
    plugin.DeviceConf[MODEL]["TS0601_DP"] = {"05": {"sensor_type": "temperature"}}
    assert awake() == 0
