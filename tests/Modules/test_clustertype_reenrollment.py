#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression tests for issue #1987: a Model Name re-announcement must never wipe the
per-endpoint ``ClusterType`` cross-reference.

Coverage:
  - _cluster_type_pairs                          – snapshot helper
  - _update_data_structutre_based_on_model_name  – ClusterType preserved on re-enrollment
                                                   – missing DeviceConf clusters are added (superset)
                                                   – empty ClusterType handled without crashing
                                                   – already-DeviceConf config short-circuits
                                                   – invariant tripwire logs an Error if ClusterType shrinks
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
def zclch():
    """Import Modules.zclClusterHelpers with its external deps stubbed out."""
    stubs = {
        "Modules.pluginModels": _make_stub(
            "Modules.pluginModels",
            check_found_plugin_model=MagicMock(name="check_found_plugin_model"),
            plugin_self_identifier=MagicMock(name="plugin_self_identifier"),
        ),
        "Modules.readAttributes": _make_stub(
            "Modules.readAttributes",
            ReadAttributeRequest_0702_multiplier_divisor=MagicMock(),
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            get_deviceconf_parameter_value=MagicMock(return_value=None),
        ),
    }
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    sys.modules.pop("Modules.zclClusterHelpers", None)
    module = importlib.import_module("Modules.zclClusterHelpers")
    yield module
    for name, original in saved.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original
    sys.modules.pop("Modules.zclClusterHelpers", None)


class _FakeLog:
    def __init__(self):
        self.entries = []

    def logging(self, module, level, message, nwkid=None, *args, **kwargs):
        self.entries.append((level, message))

    def levels(self):
        return [level for level, _ in self.entries]


class _FakeSelf:
    def __init__(self):
        self.ListOfDevices = {}
        self.DeviceConf = {}
        self.log = _FakeLog()
        self.iaszonemgt = None


NWK = "1234"
MODEL = "MY-PLUG"


def _deviceconf():
    return {
        MODEL: {
            "Type": ["Switch"],
            "Ep": {
                "01": {"0006": {}, "0008": {}, "Type": ["Switch", "LvlControl"]},
            },
        }
    }


# ── _cluster_type_pairs ───────────────────────────────────────────────────────

def test_cluster_type_pairs(zclch):
    device = {"Ep": {
        "01": {"ClusterType": {"576": "ColorControl", "577": "LvlControl"}},
        "02": {"ClusterType": {"600": "Switch"}},
        "03": {"ClusterType": {}},     # empty, contributes nothing
        "04": {"0006": {}},            # no ClusterType key
    }}
    assert zclch._cluster_type_pairs(device) == {
        ("01", "576"), ("01", "577"), ("02", "600"),
    }


# ── _update_data_structutre_based_on_model_name ──────────────────────────────

def test_reenrollment_preserves_clustertype_and_adds_missing_clusters(zclch):
    self = _FakeSelf()
    self.DeviceConf = _deviceconf()
    self.ListOfDevices[NWK] = {
        "Model": MODEL,
        "ConfigSource": "??",
        "Ep": {"01": {"ClusterType": {"576": "ColorControl"}, "0006": {}}},
    }

    result = zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL)

    assert result is True
    ep01 = self.ListOfDevices[NWK]["Ep"]["01"]
    # ClusterType is untouched
    assert ep01["ClusterType"] == {"576": "ColorControl"}
    # DeviceConf clusters merged in as a superset (0008 added, 0006 kept)
    assert "0006" in ep01 and "0008" in ep01
    assert self.ListOfDevices[NWK]["ConfigSource"] == "DeviceConf"
    # No Error logged
    assert "Error" not in self.log.levels()


def test_reenrollment_with_empty_clustertype_does_not_crash(zclch):
    self = _FakeSelf()
    self.DeviceConf = _deviceconf()
    self.ListOfDevices[NWK] = {
        "Model": MODEL,
        "ConfigSource": "??",
        "Ep": {"01": {"ClusterType": {}}},
    }

    result = zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL)

    assert result is True
    assert self.ListOfDevices[NWK]["Ep"]["01"]["ClusterType"] == {}
    assert "0008" in self.ListOfDevices[NWK]["Ep"]["01"]
    assert "Error" not in self.log.levels()


def test_already_deviceconf_short_circuits(zclch):
    self = _FakeSelf()
    self.DeviceConf = _deviceconf()
    self.ListOfDevices[NWK] = {
        "Model": MODEL,
        "ConfigSource": "DeviceConf",
        "Ep": {"01": {"ClusterType": {"576": "ColorControl"}}},
    }

    result = zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL)

    assert result is True
    # Nothing enrolled: 0008 not added because we short-circuited
    assert "0008" not in self.ListOfDevices[NWK]["Ep"]["01"]
    assert self.ListOfDevices[NWK]["Ep"]["01"]["ClusterType"] == {"576": "ColorControl"}


def test_unknown_model_returns_false(zclch):
    self = _FakeSelf()
    self.DeviceConf = {}
    self.ListOfDevices[NWK] = {"Model": MODEL, "Ep": {}}
    assert zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL) is False


def test_invariant_tripwire_fires_when_clustertype_shrinks(zclch, monkeypatch):
    """If a future regression drops ClusterType during the merge, an Error must be logged."""
    self = _FakeSelf()
    self.DeviceConf = _deviceconf()
    self.ListOfDevices[NWK] = {
        "Model": MODEL,
        "ConfigSource": "??",
        "Ep": {"01": {"ClusterType": {"576": "ColorControl"}}},
    }

    def _destructive(self_, nwk, model, initial_ep):
        # Simulate the historical bug: wipe the endpoint structure.
        self_.ListOfDevices[nwk]["Ep"]["01"]["ClusterType"] = {}
        return True

    monkeypatch.setattr(zclch, "_upd_data_strut_based_on_model", _destructive)

    zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL)

    assert "Error" in self.log.levels()
    assert any("shrank" in message for _, message in self.log.entries)
