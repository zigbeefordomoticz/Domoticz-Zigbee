#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression tests for issue #1987: a Model Name re-announcement must never wipe the
per-endpoint ``ClusterType`` cross-reference.

The protection strategy in the current code is *blocking* (not merging): when an
endpoint already carries a non-empty ``ClusterType`` (real Domoticz widgets are
provisioned), ``_update_data_structutre_based_on_model_name`` refuses to touch the
``Ep`` structure at all and returns ``False``. Only when no provisioned ClusterType
is present does it reset ``Ep`` and rebuild it from ``DeviceConf``.

Coverage:
  - _has_non_empty_cluster_type                  – endpoint provisioning probe
  - _has_provisioned_endpoint                    – endpoint provisioning probe
  - _update_data_structutre_based_on_model_name
        – provisioned ClusterType blocks the Ep reset (Ep preserved, returns False)
        – empty ClusterType allows the Ep reset/rebuild from DeviceConf
        – already-DeviceConf config short-circuits untouched
        – unknown model returns False
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


# ── provisioning probes ──────────────────────────────────────────────────────

def test_has_non_empty_cluster_type(zclch):
    assert zclch._has_non_empty_cluster_type(
        {"Ep": {"01": {"ClusterType": {"576": "ColorControl"}}}}) is True
    # empty / missing ClusterType are NOT provisioned
    assert zclch._has_non_empty_cluster_type({"Ep": {"01": {"ClusterType": {}}}}) is False
    assert zclch._has_non_empty_cluster_type({"Ep": {"01": {"0006": {}}}}) is False
    assert zclch._has_non_empty_cluster_type({"Ep": {}}) is False
    # malformed record: a non-dict endpoint value must not raise (fail-safe probe)
    assert zclch._has_non_empty_cluster_type({"Ep": {"01": "bogus"}}) is False
    assert zclch._has_non_empty_cluster_type(
        {"Ep": {"01": "bogus", "02": {"ClusterType": {"576": "ColorControl"}}}}) is True


def test_has_provisioned_endpoint(zclch):
    assert zclch._has_provisioned_endpoint(
        {"Ep": {"01": {"ClusterType": {"576": "ColorControl"}}}}) is True
    # an empty ClusterType mapping is falsy -> not provisioned
    assert bool(zclch._has_provisioned_endpoint({"Ep": {"01": {"ClusterType": {}}}})) is False
    assert bool(zclch._has_provisioned_endpoint({"Ep": {"01": {"0006": {}}}})) is False


# ── _update_data_structutre_based_on_model_name ──────────────────────────────

def test_reenrollment_with_provisioned_clustertype_is_blocked(zclch):
    """A non-empty ClusterType must block the Ep reset: Ep is left fully intact
    (missing DeviceConf clusters are NOT merged in) and the call returns False."""
    self = _FakeSelf()
    self.DeviceConf = _deviceconf()
    self.ListOfDevices[NWK] = {
        "Model": MODEL,
        "ConfigSource": "??",
        "Ep": {"01": {"ClusterType": {"576": "ColorControl"}, "0006": {}}},
    }

    result = zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL)

    assert result is False
    ep01 = self.ListOfDevices[NWK]["Ep"]["01"]
    # ClusterType is untouched and the Ep is not rebuilt from DeviceConf
    assert ep01["ClusterType"] == {"576": "ColorControl"}
    assert "0006" in ep01
    assert "0008" not in ep01          # DeviceConf cluster NOT merged because we bailed out
    # ConfigSource is still flipped to DeviceConf before the guard
    assert self.ListOfDevices[NWK]["ConfigSource"] == "DeviceConf"
    # The protective bail-out is logged as a Warning mentioning the block
    assert "Warning" in self.log.levels()
    assert any("BLOCKED" in message for _, message in self.log.entries)


def test_reenrollment_with_empty_clustertype_resets_and_rebuilds(zclch):
    """With no provisioned ClusterType, Ep is reset and rebuilt from DeviceConf."""
    self = _FakeSelf()
    self.DeviceConf = _deviceconf()
    self.ListOfDevices[NWK] = {
        "Model": MODEL,
        "ConfigSource": "??",
        "Ep": {"01": {"ClusterType": {}}},
    }

    result = zclch._update_data_structutre_based_on_model_name(self, NWK, MODEL)

    # Successful reset/rebuild returns True (gates IAS re-registration in the caller).
    assert result is True
    ep01 = self.ListOfDevices[NWK]["Ep"]["01"]
    # Ep was wiped and rebuilt: DeviceConf clusters are present, the placeholder
    # (empty) ClusterType key was dropped by the reset.
    assert "0006" in ep01 and "0008" in ep01
    assert "ClusterType" not in ep01
    assert ep01["Type"] == ["Switch", "LvlControl"]
    assert self.ListOfDevices[NWK]["ConfigSource"] == "DeviceConf"
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
