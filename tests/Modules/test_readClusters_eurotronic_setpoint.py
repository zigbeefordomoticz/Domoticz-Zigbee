#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readClusters.py:Cluster0201, Eurotronic Spirit (SPZB0001) setpoints.

The widget of a Spirit follows the manufacturer attribute 0x4003 (current heating
setpoint). Its handler compares the reported value with the stored 0x0012 to decide
whether the setpoint changed on the head.

Field bug: for SPZB0001 the 0x0012 branch left the raw ZCL hex string in "0012"
(e.g. "04b0" for 12.0 °C), and the 0x4003 handler ran float() on it:
  - "04b0", "07d0", "01f4" ... -> ValueError, the report was dropped;
  - "0514" -> 514.0, compared against 13.0 by accident.

Coverage:
  - a 0x0012 report from a SPZB0001 is stored in °C, no widget update;
  - the 0x4003 handler accepts a stored raw hex string (saved device lists),
    a number, and an unreadable value, without raising;
  - the widget is updated only when 0x4003 differs from the stored setpoint,
    and not at all when no 0x0012 was ever stored (unchanged behaviour).
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


def test_0012_then_4003_same_value_does_not_raise(rc, spirit):
    """Field sequence (7c53, 2026-11-22): 0x0012 = 12.0 report, then 0x4003 = 12.0."""
    p, maj_domo = spirit
    _report(rc, p, "0012", "04b0")
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_not_called()


@pytest.mark.parametrize("raw", ["04b0", "07d0", "01f4", "05DC"])
def test_4003_with_legacy_raw_hex_equal_does_not_raise(rc, spirit, raw):
    """A device list saved by an earlier version holds the raw hex string."""
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", raw)
    _report(rc, p, "4003", raw.lower())

    maj_domo.assert_not_called()


def test_4003_with_legacy_raw_hex_different_updates_widget(rc, spirit):
    """Stored 13.0 °C as raw hex, head now at 12.0 °C: the widget follows 0x4003."""
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", "0514")
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, "0201", 12.0, Attribute_="4003")
    assert _stored(p, "0012") == 12.0
    assert _stored(p, "4003") == 12.0


def test_4003_with_celsius_different_updates_widget(rc, spirit):
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", 13.0)
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, "0201", 12.0, Attribute_="4003")


def test_4003_with_celsius_equal_no_update(rc, spirit):
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", 12.0)
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_not_called()


def test_4003_without_stored_0012_no_update(rc, spirit):
    """Unchanged behaviour: nothing to compare against, no widget update."""
    p, maj_domo = spirit
    _report(rc, p, "4003", "04b0")

    maj_domo.assert_not_called()


def test_4003_with_unreadable_stored_value_updates_widget(rc, spirit):
    p, maj_domo = spirit
    _store(p, NWKID, EP, CLUSTER, "0012", "not-a-setpoint")
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
