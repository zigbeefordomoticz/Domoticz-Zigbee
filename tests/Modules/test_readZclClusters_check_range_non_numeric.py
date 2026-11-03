#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for Modules/readZclClusters.py:_check_range

Context (production error log, plugin 9.1.008):
  "_decode_message - unhandled exception while processing MsgType 8100:
   '<=' not supported between instances of 'int' and 'str'"
  raised from _check_range: `return _range1 <= value <= _range2`.

  Some ZclDefinitions ranges are JSON integers (e.g. 0x0102/0x0008
  CurrentPositionLiftPercentage [0, 100], 0x0b04 ActivePower [-32768, 32768]).
  decoding_attribute_data() returns a string, not a number, when the payload is
  empty or the device reports a data type it does not decode into a number. The
  comparison then raised TypeError and aborted the whole Read Attribute Response.

  A value that is not a number cannot be within a numeric range: _check_range
  must return False (value dropped as out of range) instead of raising.
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


def _decoding_attribute_data(attribute_type, attribute_value, handle_errors=False):
    # Mirrors the real decoder: numeric types are decoded, an empty payload or an
    # undecoded type (here 0x1a, bitmap24) is returned as a string.
    if len(attribute_value) == 0:
        return ""
    if attribute_type in ("20", "21", "30"):
        return int(attribute_value, 16)
    return attribute_value


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
            decoding_attribute_data=MagicMock(name="decoding_attribute_data", side_effect=_decoding_attribute_data),
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


NWKID = "1234"
EP = "01"
CLUSTER = "0102"
ATTR_LIFT_PERCENT = "0008"


def _plugin():
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {"TrackingEraticValue": False, "trackZclClustersIn": False}
    p.ListOfDevices = {NWKID: {"Model": "TestBlind"}}
    p.DeviceConf = {
        "TestBlind": {
            "Ep": {
                EP: {
                    CLUSTER: {
                        "Attributes": {
                            ATTR_LIFT_PERCENT: {
                                "Name": "CurrentPositionLiftPercentage",
                                "DataType": "20",
                                "Range": [0, 100],
                                "ActionList": ["check_store_value", "upd_domo_device"],
                            }
                        }
                    }
                }
            }
        }
    }
    p.readZclClusters = {}
    return p


@pytest.mark.parametrize("value", ["", "000064", "abc"])
def test_check_range_int_range_non_numeric_value(rzc, value):
    """A string value against an integer range is out of range, not a TypeError."""
    assert rzc._check_range(_plugin(), value, "1a", [0, 100]) is False


@pytest.mark.parametrize("value, expected", [(0, True), (50, True), (100, True), (101, False), (-1, False)])
def test_check_range_int_range_numeric_value_unchanged(rzc, value, expected):
    assert rzc._check_range(_plugin(), value, "20", [0, 100]) is expected


def test_check_range_hex_range_unchanged(rzc):
    assert rzc._check_range(_plugin(), 0x10, "21", ["0000", "ffff"]) is True


def test_check_range_string_range_and_string_value_unchanged(rzc):
    """Undecoded type on both sides: comparison stays between strings, as before."""
    assert rzc._check_range(_plugin(), "0010", "1a", ["0000", "ffff"]) is True


@pytest.mark.parametrize("att_type, att_size, data", [("20", "0000", ""), ("1a", "0003", "000064")])
def test_non_numeric_value_dropped_without_exception(rzc, monkeypatch, att_type, att_size, data):
    """End to end: the report is dropped, the widget is not updated, nothing raises."""
    maj_domo = MagicMock()
    monkeypatch.setattr(rzc, "MajDomoDevice", maj_domo)

    rzc.process_cluster_attribute_response(
        _plugin(), {}, "01", NWKID, EP, CLUSTER, ATTR_LIFT_PERCENT, att_type, att_size, data, Source="8100",
    )

    maj_domo.assert_not_called()


def test_numeric_value_in_range_still_processed(rzc, monkeypatch):
    maj_domo = MagicMock()
    monkeypatch.setattr(rzc, "MajDomoDevice", maj_domo)

    rzc.process_cluster_attribute_response(
        _plugin(), {}, "01", NWKID, EP, CLUSTER, ATTR_LIFT_PERCENT, "20", "0001", "32", Source="8100",
    )

    maj_domo.assert_called_once()
    assert maj_domo.call_args.args[5] == 50
