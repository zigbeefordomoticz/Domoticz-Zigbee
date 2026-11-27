#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readClusters.py:Cluster0201, Eurotronic Spirit (SPZB0001) setpoints.

The widget of a Spirit follows the manufacturer attribute 0x4003 (current heating
setpoint). Every 0x4003 report goes to the widget.

Field bugs:
  - 9.1.010: the 0x4003 handler ran float() on the stored 0x0012, which was the raw
    ZCL hex string: "04b0" -> ValueError, the report was dropped; "0514" -> 514.0,
    always different, so the widget was updated by accident.
  - The head reports 0x0012 and then 0x4003 with the same value when the setpoint is
    changed on the head, so comparing the two never shows a change.

Coverage:
  - a 0x0012 report from a SPZB0001 is stored in °C, no widget update;
  - the field sequence 0x0012 -> 0x4003 -> 0x0012 updates the widget once;
  - a 0x4003 report updates the widget whatever is stored in "0012" (raw hex from a
    saved device list, number, unreadable, nothing).
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def rc():
    """Import Modules.readClusters with all external deps stubbed out."""
    stubs = {
        "Modules.domoMaj": _make_stub(
            "Modules.domoMaj", MajDomoDevice=MagicMock(name="MajDomoDevice")
        ),
        "Modules.ikeaTradfri": _make_stub(
            "Modules.ikeaTradfri", ikea_air_purifier_cluster=MagicMock(name="ikea_air_purifier_cluster")
        ),
        "Modules.lumi": _make_stub(
            "Modules.lumi",
            AqaraOppleDecoding0012=MagicMock(name="AqaraOppleDecoding0012"),
            cube_decode=MagicMock(name="cube_decode"),
            decode_vibr=MagicMock(name="decode_vibr"),
            decode_vibrAngle=MagicMock(name="decode_vibrAngle"),
        ),
        "Modules.philips": _make_stub(
            "Modules.philips", philips_dimmer_switch=MagicMock(name="philips_dimmer_switch")
        ),
        "Modules.readZclClusters": _make_stub(
            "Modules.readZclClusters",
            is_cluster_zcl_config_available=MagicMock(name="is_cluster_zcl_config_available", return_value=False),
            process_cluster_attribute_response=MagicMock(name="process_cluster_attribute_response"),
        ),
        "Modules.schneider_wiser": _make_stub(
            "Modules.schneider_wiser",
            receiving_heatingdemand_attribute=MagicMock(name="receiving_heatingdemand_attribute"),
            receiving_heatingpoint_attribute=MagicMock(name="receiving_heatingpoint_attribute"),
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            DeviceExist=MagicMock(name="DeviceExist", return_value=True),
            checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
            checkAttribute=MagicMock(name="checkAttribute"),
            checkValidValue=MagicMock(name="checkValidValue", return_value=True),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            getEPforClusterType=MagicMock(name="getEPforClusterType", return_value=[]),
            set_status_datastruct=MagicMock(name="set_status_datastruct"),
            set_timestamp_datastruct=MagicMock(name="set_timestamp_datastruct"),
        ),
        "Modules.zclClusterHelpers": _make_stub(
            "Modules.zclClusterHelpers", compute_metering_conso=MagicMock(name="compute_metering_conso")
        ),
        "Modules.zigateConsts": _make_stub("Modules.zigateConsts", ZONE_TYPE={}),
    }

    # Restore whatever was cached before (see test_readClusters_cluster0006.py).
    tracked = list(stubs) + ["Modules.readClusters"]
    saved = {name: sys.modules.get(name) for name in tracked}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.readClusters", None)
    module = importlib.import_module("Modules.readClusters")

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


NWKID = "4d43"
EP = "01"
CLUSTER = "0201"


def _store(self, nwkid, ep, cluster, attribute, value):
    self.ListOfDevices[nwkid]["Ep"][ep].setdefault(cluster, {})[attribute] = value


@pytest.fixture
def spirit(rc, monkeypatch):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {
        NWKID: {
            "Model": "SPZB0001",
            "Manufacturer": "1037",
            "Manufacturer Name": "Eurotronic",
            "Ep": {EP: {CLUSTER: {}}},
        }
    }
    maj_domo = MagicMock(name="MajDomoDevice")
    monkeypatch.setattr(rc, "MajDomoDevice", maj_domo)
    monkeypatch.setattr(rc, "checkAndStoreAttributeValue", _store)
    return p, maj_domo


def _report(rc, p, attribute, data):
    rc.Cluster0201(p, {}, "01", NWKID, EP, CLUSTER, attribute, "29", "0002", data, "8102")


def _stored(p, attribute):
    return p.ListOfDevices[NWKID]["Ep"][EP][CLUSTER][attribute]


def test_0012_report_is_stored_in_celsius(rc, spirit):
    p, maj_domo = spirit
    _report(rc, p, "0012", "04b0")

    assert _stored(p, "0012") == 12.0
    maj_domo.assert_not_called()


def test_setpoint_changed_on_the_head_updates_widget(rc, spirit):
    """Field sequence (4d43, 2026-11-23): 0x0012 = 11.0, 0x4003 = 11.0, 0x0012 = 11.0."""
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", 12.0)
    _store(p, NWKID, EP, CLUSTER, "4003", 12.0)
    _report(rc, p, "0012", "044c")
    _report(rc, p, "4003", "044c")
    _report(rc, p, "0012", "044c")

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, "0201", 11.0, Attribute_="4003")
    assert _stored(p, "0012") == 11.0
    assert _stored(p, "4003") == 11.0


@pytest.mark.parametrize("raw, expected", [("04b0", 12.0), ("07d0", 20.0), ("01f4", 5.0), ("0514", 13.0)])
def test_0012_then_4003_for_each_setpoint(rc, spirit, raw, expected):
    """Values that raised ValueError on 9.1.010, and one that did not."""
    p, maj_domo = spirit
    _report(rc, p, "0012", raw)
    _report(rc, p, "4003", raw)

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, "0201", expected, Attribute_="4003")


@pytest.mark.parametrize("stored", ["04b0", "05DC", "0514", 12.0, 13.0, 1200, "12.0", "", "not-a-setpoint", {}, None])
def test_4003_updates_widget_whatever_is_stored(rc, spirit, stored):
    """Including the raw hex string a device list saved by an earlier version holds."""
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", stored)
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, "0201", 12.0, Attribute_="4003")
    assert _stored(p, "0012") == 12.0
    assert _stored(p, "4003") == 12.0


def test_4003_without_stored_0012_updates_widget(rc, spirit):
    p, maj_domo = spirit
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, "0201", 12.0, Attribute_="4003")


def test_non_spirit_0012_report_unchanged(rc, spirit):
    """Regression guard: other thermostats still store int(value) and update the widget."""
    p, maj_domo = spirit
    p.ListOfDevices[NWKID]["Model"] = "SomeThermostat"
    p.ListOfDevices[NWKID]["Manufacturer"] = "1234"
    p.ListOfDevices[NWKID]["Manufacturer Name"] = "Other"
    _report(rc, p, "0012", "04b0")

    assert _stored(p, "0012") == 1200
    maj_domo.assert_called_once_with(p, {}, NWKID, EP, CLUSTER, 12.0, Attribute_="0012")
