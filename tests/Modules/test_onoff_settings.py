#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.onoff_settings.onoff_startup_onoff_mode.

Regression coverage for GitHub issue #1996: certified Tuya profiles that
declare "PowerOnOffStateAttribute8002": true (TS011F family, TS0001-TS0013,
...) must have their power-on-after-restore writes targeted at ZCL attribute
0x8002, not the unconditional 0x4003. The 0x8002 attribute also uses a
different "previous state" sentinel (0x02) than 0x4003 (0xff).
"""

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
def onoff_module():
    stubs = {
        "Modules.basicOutputs": dict(write_attribute=MagicMock(name="write_attribute")),
        "Modules.enki": dict(is_enky_device=MagicMock(name="is_enky_device", return_value=False)),
        "Modules.philips": dict(is_philips_device=MagicMock(name="is_philips_device", return_value=False)),
        "Modules.readAttributes": dict(
            ReadAttributeRequest_0006_400x=MagicMock(name="ReadAttributeRequest_0006_400x")
        ),
        "Modules.tools": dict(
            get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=False),
            getListOfEpForCluster=MagicMock(name="getListOfEpForCluster", return_value=[]),
            is_int=MagicMock(name="is_int", side_effect=lambda v: str(v).lstrip("-").isdigit()),
        ),
        "Modules.tuya": dict(
            get_tuya_attribute=MagicMock(name="get_tuya_attribute"),
            is_tuya_switch_relay=MagicMock(name="is_tuya_switch_relay", return_value=False),
            tuya_switch_relay_status=MagicMock(name="tuya_switch_relay_status"),
        ),
        "Modules.zigateConsts": dict(ZIGATE_EP="01"),
        "Zigbee.zclCommands": dict(
            zcl_onoff_on=MagicMock(name="zcl_onoff_on"),
            zcl_onoff_on_with_timed_off=MagicMock(name="zcl_onoff_on_with_timed_off"),
        ),
    }
    for name, attrs in stubs.items():
        _ensure_stub(name, **attrs)

    sys.modules.pop("Modules.onoff_settings", None)
    mod = importlib.import_module("Modules.onoff_settings")
    yield mod
    sys.modules.pop("Modules.onoff_settings", None)


@pytest.fixture
def plugin():
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {"1234": {"Model": "TS011F-plug"}}
    return p


NWKID = "1234"
EP = "01"


def test_writes_4003_when_flag_disabled(onoff_module, plugin, monkeypatch):
    monkeypatch.setattr(onoff_module, "get_deviceconf_parameter_value", lambda *a, **kw: False)
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)

    onoff_module.onoff_startup_onoff_mode(plugin, NWKID, EP, 1)

    args = write_attribute.call_args.args
    # write_attribute(self, nwkid, ZIGATE_EP, ep, cluster, manuf_id, manuf_spec, attribute, data_type, data, ...)
    assert args[7] == "4003"
    assert args[8] == "30"
    assert args[9] == "01"


def test_writes_8002_when_flag_enabled(onoff_module, plugin, monkeypatch):
    """Regression #1996: the 0x8002 flag must be honored for the write path."""
    monkeypatch.setattr(onoff_module, "get_deviceconf_parameter_value", lambda *a, **kw: True)
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)

    onoff_module.onoff_startup_onoff_mode(plugin, NWKID, EP, 1)

    args = write_attribute.call_args.args
    assert args[7] == "8002"
    assert args[8] == "30"
    assert args[9] == "01"


def test_previous_state_remapped_to_02_for_8002(onoff_module, plugin, monkeypatch):
    monkeypatch.setattr(onoff_module, "get_deviceconf_parameter_value", lambda *a, **kw: True)
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)

    onoff_module.onoff_startup_onoff_mode(plugin, NWKID, EP, 0xFF)

    args = write_attribute.call_args.args
    assert args[7] == "8002"
    assert args[9] == "02"


def test_previous_state_stays_ff_for_4003(onoff_module, plugin, monkeypatch):
    monkeypatch.setattr(onoff_module, "get_deviceconf_parameter_value", lambda *a, **kw: False)
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)

    onoff_module.onoff_startup_onoff_mode(plugin, NWKID, EP, 0xFF)

    args = write_attribute.call_args.args
    assert args[7] == "4003"
    assert args[9] == "ff"


def test_string_value_is_converted(onoff_module, plugin, monkeypatch):
    monkeypatch.setattr(onoff_module, "get_deviceconf_parameter_value", lambda *a, **kw: True)
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)

    onoff_module.onoff_startup_onoff_mode(plugin, NWKID, EP, "1")

    write_attribute.assert_called_once()
    assert write_attribute.call_args.args[9] == "01"


def test_invalid_string_value_does_not_write(onoff_module, plugin, monkeypatch):
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)

    onoff_module.onoff_startup_onoff_mode(plugin, NWKID, EP, "not-a-number")

    write_attribute.assert_not_called()




# ─── OnOffOnTimeDelay / OnOffOffWaitTime → On With Timed Off (0x42) ───────────
#
# The OnTime attribute (0x4001) is the countdown itself: the device decrements it
# while On and an Off resets it to 0, so writing it once when the Param changes
# only covered the next On. The Params now carry the values sent with EVERY On,
# as On With Timed Off. Tuya relays (device conf "TuyaOnOffCountdown") use 0x42
# as a countdown in seconds that does not switch On: On first, then 0x42.


def _params(monkeypatch, onoff_module, params, raw=True, tuya=False):
    monkeypatch.setattr(onoff_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))
    monkeypatch.setattr(onoff_module, "get_deviceconf_parameter_value",
                        lambda self, model, name, return_default=None: tuya if name == "TuyaOnOffCountdown" else return_default)
    on = MagicMock(name="zcl_onoff_on")
    timed = MagicMock(name="zcl_onoff_on_with_timed_off")
    monkeypatch.setattr(onoff_module, "zcl_onoff_on", on)
    monkeypatch.setattr(onoff_module, "zcl_onoff_on_with_timed_off", timed)
    return on, timed


@pytest.fixture
def raw_plugin(plugin):
    plugin.pluginconf.pluginConf = {"ControllerInRawMode": True}
    return plugin


def test_onoff_params_point_at_the_check_callable(onoff_module):
    reg = onoff_module.ONOFF_DEVICE_PARAMETERS
    assert reg["OnOffOnTimeDelay"]["callable"] is onoff_module.check_onoff_timed_off_param
    assert reg["OnOffOffWaitTime"]["callable"] is onoff_module.check_onoff_timed_off_param
    assert reg["PowerOnAfterOffOn"]["callable"] is onoff_module.common_onoff_startup_onoff_mode


def test_param_change_writes_nothing(onoff_module, plugin, monkeypatch):
    write_attribute = MagicMock()
    monkeypatch.setattr(onoff_module, "write_attribute", write_attribute)
    onoff_module.ONOFF_DEVICE_PARAMETERS["OnOffOnTimeDelay"]["callable"](plugin, NWKID, 600)
    onoff_module.ONOFF_DEVICE_PARAMETERS["OnOffOffWaitTime"]["callable"](plugin, NWKID, 100)
    write_attribute.assert_not_called()


@pytest.mark.parametrize("params, expected", [
    ({}, None),
    ({"OnOffOnTimeDelay": 0}, None),
    ({"OnOffOnTimeDelay": 600}, (600, 0)),
    ({"OnOffOnTimeDelay": "600", "OnOffOffWaitTime": "10"}, (600, 10)),
    ({"OnOffOnTimeDelay": "1.5"}, (1.5, 0)),
    ({"OnOffOnTimeDelay": {"01": 600, "02": 300}}, (600, 0)),
    ({"OnOffOnTimeDelay": {"02": 300}}, None),
    ({"OnOffOnTimeDelay": "abc"}, None),
])
def test_timed_off_values(onoff_module, plugin, monkeypatch, params, expected):
    _params(monkeypatch, onoff_module, params)
    assert onoff_module.onoff_timed_off_values(plugin, NWKID, EP) == expected


def test_no_param_lets_the_caller_send_a_plain_on(onoff_module, raw_plugin, monkeypatch):
    on, timed = _params(monkeypatch, onoff_module, {})
    assert onoff_module.onoff_on_with_timed_off(raw_plugin, NWKID, EP) is False
    on.assert_not_called()
    timed.assert_not_called()


def test_zcl_device_gets_on_with_timed_off_in_tenths(onoff_module, raw_plugin, monkeypatch):
    # Params in seconds, ZCL fields in 1/10 s
    on, timed = _params(monkeypatch, onoff_module, {"OnOffOnTimeDelay": 600, "OnOffOffWaitTime": 5})
    assert onoff_module.onoff_on_with_timed_off(raw_plugin, NWKID, EP) is True
    on.assert_not_called()  # 0x42 switches On by itself on a ZCL device
    timed.assert_called_once_with(raw_plugin, NWKID, EP, 6000, 50)


def test_tuya_device_gets_on_then_countdown_in_seconds(onoff_module, raw_plugin, monkeypatch):
    calls = []
    on, timed = _params(monkeypatch, onoff_module, {"OnOffOnTimeDelay": 600.5, "OnOffOffWaitTime": 5}, tuya=True)
    on.side_effect = lambda *a: calls.append(("on",) + a[1:])
    timed.side_effect = lambda *a: calls.append(("timed",) + a[1:])
    assert onoff_module.onoff_on_with_timed_off(raw_plugin, NWKID, EP) is True
    # On first (it cancels a running countdown), 600.5 s rounded up = 601 s, OffWaitTime = OnTime
    assert calls == [("on", NWKID, EP), ("timed", NWKID, EP, 601, 601)]


def test_long_delays_are_capped_per_device_kind(onoff_module, raw_plugin, monkeypatch):
    on, timed = _params(monkeypatch, onoff_module, {"OnOffOnTimeDelay": 99999}, tuya=True)
    onoff_module.onoff_on_with_timed_off(raw_plugin, NWKID, EP)
    assert timed.call_args.args[3:] == (43200, 43200)  # Tuya: 12 h
    on, timed = _params(monkeypatch, onoff_module, {"OnOffOnTimeDelay": 99999})
    onoff_module.onoff_on_with_timed_off(raw_plugin, NWKID, EP)
    assert timed.call_args.args[3:] == (0xFFFE, 0)  # ZCL: uint16 in 1/10 s


def test_native_zigate_falls_back_to_plain_on(onoff_module, plugin, monkeypatch):
    plugin.pluginconf.pluginConf = {"ControllerInRawMode": False}
    on, timed = _params(monkeypatch, onoff_module, {"OnOffOnTimeDelay": 600})
    assert onoff_module.onoff_on_with_timed_off(plugin, NWKID, EP) is False
    timed.assert_not_called()
