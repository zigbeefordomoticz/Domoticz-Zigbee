#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/thermostats.py:thermostat_Setpoint_SPZB (Eurotronic Spirit, SPZB0001).

Field report (2026-11-22, ZBDongle-E): one Spirit ignored every setpoint sent from
Domoticz, which wrote the manufacturer attribute 0x4003 (manufacturer 0x1037). A raw
write of the standard Occupied Heating Setpoint 0x0012 was accepted (ZCL status 0x00)
by that head and by a second one with the same firmware, and both moved; the second
then reported 0x4003 with the new value. ZHA writes 0x0012 as well.

Coverage:
  - default: standard 0x0012 write, no manufacturer code, int16 centi-degrees;
  - Param EurotronicSetpointAttribute = "4003" (or 4003) keeps the earlier
    manufacturer-specific 0x4003 write;
  - any other Param value falls back to 0x0012;
  - the endpoint hosting 0x0201 is the one written to;
  - thermostat_Setpoint dispatches SPZB0001 to it, after the calibration write.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

NWKID = "4d43"


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def thermo():
    """Import Modules.thermostats with all external deps stubbed out."""
    stubs = {
        "Modules.basicOutputs": _make_stub("Modules.basicOutputs", write_attribute=MagicMock(name="write_attribute")),
        "Modules.casaia": _make_stub(
            "Modules.casaia",
            casaia_check_irPairing=MagicMock(name="casaia_check_irPairing"),
            casaia_setpoint=MagicMock(name="casaia_setpoint"),
        ),
        "Modules.danfoss": _make_stub("Modules.danfoss", thermostat_Setpoint_Danfoss=MagicMock(name="thermostat_Setpoint_Danfoss")),
        "Modules.readAttributes": _make_stub(
            "Modules.readAttributes",
            ReadAttributeRequest_0201=MagicMock(name="ReadAttributeRequest_0201"),
            ReadAttributeRequest_thermostat_cool_setpoint=MagicMock(name="ReadAttributeRequest_thermostat_cool_setpoint"),
            ReadAttributeRequest_thermostat_unoccupied_heat_setpoint=MagicMock(name="ReadAttributeRequest_thermostat_unoccupied_heat_setpoint"),
        ),
        "Modules.schneider_wiser": _make_stub(
            "Modules.schneider_wiser",
            schneider_hact_heater_type_wiser2=MagicMock(name="schneider_hact_heater_type_wiser2"),
            schneider_setpoint=MagicMock(name="schneider_setpoint"),
        ),
        "Modules.tuyaConst": _make_stub("Modules.tuyaConst", TUYA_eTRV_MODEL=()),
        "Modules.tuyaTRV": _make_stub("Modules.tuyaTRV", tuya_setpoint=MagicMock(name="tuya_setpoint")),
        "Modules.tuyaTS0601": _make_stub(
            "Modules.tuyaTS0601",
            ts0601_actuator=MagicMock(name="ts0601_actuator"),
            ts0601_extract_data_point_infos=MagicMock(name="ts0601_extract_data_point_infos", return_value=None),
        ),
    }

    tracked = list(stubs) + ["Modules.thermostats"]
    saved = {name: sys.modules.get(name) for name in tracked}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.thermostats", None)
    module = importlib.import_module("Modules.thermostats")

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


@pytest.fixture
def write(thermo, monkeypatch):
    mock = MagicMock(name="write_attribute")
    monkeypatch.setattr(thermo, "write_attribute", mock)
    return mock


def _plugin(param=None, eps=None):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    device = {"Model": "SPZB0001", "Ep": eps if eps is not None else {"01": {"0201": {}}}}
    if param is not None:
        device["Param"] = param
    p.ListOfDevices = {NWKID: device}
    return p


def test_default_writes_standard_occupied_heating_setpoint(thermo, write):
    p = _plugin()
    thermo.thermostat_Setpoint_SPZB(p, NWKID, 1200)

    write.assert_called_once_with(p, NWKID, "01", "01", "0201", "0000", "00", "0012", "29", "04b0")


def test_param_without_the_key_writes_0012(thermo, write):
    p = _plugin(param={"Disabled": 0})
    thermo.thermostat_Setpoint_SPZB(p, NWKID, 2050)

    write.assert_called_once_with(p, NWKID, "01", "01", "0201", "0000", "00", "0012", "29", "0802")


@pytest.mark.parametrize("value", ["4003", 4003])
def test_param_4003_keeps_manufacturer_specific_write(thermo, write, value):
    p = _plugin(param={"EurotronicSetpointAttribute": value})
    thermo.thermostat_Setpoint_SPZB(p, NWKID, 1200)

    write.assert_called_once_with(p, NWKID, "01", "01", "0201", "1037", "01", "4003", "29", "04b0")


@pytest.mark.parametrize("value", ["0012", 12, "", "garbage"])
def test_other_param_values_write_0012(thermo, write, value):
    p = _plugin(param={"EurotronicSetpointAttribute": value})
    thermo.thermostat_Setpoint_SPZB(p, NWKID, 1200)

    write.assert_called_once_with(p, NWKID, "01", "01", "0201", "0000", "00", "0012", "29", "04b0")


def test_endpoint_hosting_thermostat_cluster_is_used(thermo, write):
    p = _plugin(eps={"01": {"0000": {}}, "02": {"0201": {}}})
    thermo.thermostat_Setpoint_SPZB(p, NWKID, 1200)

    write.assert_called_once_with(p, NWKID, "01", "02", "0201", "0000", "00", "0012", "29", "04b0")


def test_thermostat_setpoint_dispatches_spzb(thermo, write, monkeypatch):
    calibration = MagicMock(name="thermostat_Calibration")
    monkeypatch.setattr(thermo, "thermostat_Calibration", calibration)
    p = _plugin()

    thermo.thermostat_Setpoint(p, NWKID, 1200)

    calibration.assert_called_once_with(p, NWKID)
    write.assert_called_once_with(p, NWKID, "01", "01", "0201", "0000", "00", "0012", "29", "04b0")
