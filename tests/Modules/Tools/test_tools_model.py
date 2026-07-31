#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_model.py

Coverage:
  - deviceconf_device               – model found, model missing, device missing
  - getListofType                   – slash-separated, single value, empty/None
  - get_deviceconf_parameter_value  – found, missing model, missing attribute, default
  - get_device_nickname             – has ZDeviceName, empty name → "0x{nwkid}", via IEEE
"""

import pytest
from unittest.mock import MagicMock, patch

from Modules.tools_model import (
    deviceconf_device,
    get_device_nickname,
    get_deviceconf_parameter_value,
    getListofType,
)


def _plugin(devices=None, device_conf=None, ieee2nwk=None):
    p = MagicMock()
    p.ListOfDevices = devices if devices is not None else {}
    p.DeviceConf = device_conf if device_conf is not None else {}
    p.IEEE2NWK = ieee2nwk if ieee2nwk is not None else {}
    return p


# ---------------------------------------------------------------------------
# deviceconf_device
# ---------------------------------------------------------------------------

class TestDeviceconfDevice:
    def test_model_found_returns_conf(self):
        conf = {"TS0001": {"Type": "Switch"}}
        p = _plugin({"1234": {"Model": "TS0001"}}, device_conf=conf)
        assert deviceconf_device(p, "1234") == {"Type": "Switch"}

    def test_model_not_in_conf_returns_empty(self):
        p = _plugin({"1234": {"Model": "unknown"}})
        assert deviceconf_device(p, "1234") == {}

    def test_device_not_in_list_returns_empty(self):
        p = _plugin({})
        assert deviceconf_device(p, "dead") == {}

    def test_no_model_key_returns_empty(self):
        p = _plugin({"1234": {}})
        assert deviceconf_device(p, "1234") == {}


# ---------------------------------------------------------------------------
# getListofType
# ---------------------------------------------------------------------------

class TestGetListofType:
    def test_slash_separated(self):
        p = MagicMock()
        result = getListofType(p, "Plug/Power/Meters")
        assert result == ["Plug", "Power", "Meters"]

    def test_single_value(self):
        p = MagicMock()
        assert getListofType(p, "Switch") == ["Switch"]

    def test_empty_string(self):
        p = MagicMock()
        assert getListofType(p, "") == []

    def test_none_returns_empty(self):
        p = MagicMock()
        assert getListofType(p, None) == []


# ---------------------------------------------------------------------------
# get_deviceconf_parameter_value
# ---------------------------------------------------------------------------

class TestGetDeviceconfParameterValue:
    def test_found(self):
        conf = {"TS0001": {"MainPoweredDevice": True}}
        p = _plugin(device_conf=conf)
        assert get_deviceconf_parameter_value(p, "TS0001", "MainPoweredDevice") is True

    def test_missing_model_returns_default(self):
        p = _plugin()
        assert get_deviceconf_parameter_value(p, "nope", "attr") is None

    def test_missing_attribute_returns_default(self):
        conf = {"TS0001": {}}
        p = _plugin(device_conf=conf)
        assert get_deviceconf_parameter_value(p, "TS0001", "missing", return_default=42) == 42

    def test_explicit_default(self):
        p = _plugin()
        assert get_deviceconf_parameter_value(p, "x", "y", return_default="fallback") == "fallback"


# ---------------------------------------------------------------------------
# get_device_nickname
# ---------------------------------------------------------------------------

class TestGetDeviceNickname:
    def test_has_name(self):
        p = _plugin({"1234": {"ZDeviceName": "Kitchen Light"}})
        assert get_device_nickname(p, NwkId="1234") == "Kitchen Light"

    def test_empty_name_returns_hex(self):
        p = _plugin({"1234": {"ZDeviceName": ""}})
        assert get_device_nickname(p, NwkId="1234") == "0x1234"

    def test_missing_device_returns_hex(self):
        p = _plugin({})
        assert get_device_nickname(p, NwkId="abcd") == "0xabcd"

    def test_via_ieee_resolves_nwkid(self):
        ieee = "aabbccddeeff0011"
        p = _plugin(
            devices={"1234": {"ZDeviceName": "Sensor"}},
            ieee2nwk={ieee: "1234"},
        )
        assert get_device_nickname(p, Ieee=ieee) == "Sensor"
