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
