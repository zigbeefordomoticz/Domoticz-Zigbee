#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the widget reuse of Modules/domoCreate.py when widgets are (re)created.

Field case (easydomoticz forum, 9.1.010): an Excellux NTCHT01 (Tuya ef00) has an
ambient sensor on Ep 01 (Temp/Humi) and a probe on the fake Ep f1 (Temp). The user
kept two of its widgets and asked the WebUI to recreate the missing ones. The
probe temperature widget, bound to f1, was reused for the ambient temperature of
Ep 01 as well: from then on it showed both temperatures, and a duplicate probe
widget was created.

CreateDomoDevice runs here end to end. Only the Domoticz side is faked: a unit
created by domo_create_api lands in a Devices dict, and the reuse pool is read
back from it, as build_widget_reuse_pool does.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

IEEE = "a4c1380000000001"
NWKID = "76c4"
PLUGIN = "Zigbee"

TRIO = {"Temperature": (80, 5, 0), "Humidity": (81, 1, 0), "Temp+Hum": (82, 1, 0)}


def _ensure_stub(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    return mod


class _FakeDomoticz:
    """The DomoticzEx side: Devices[IEEE].Units, and widget creation into it."""

    def __init__(self):
        self.units = {}   # unit -> {"ID", "Type", "SubType", "SwitchType", "Name"}
        self.next_idx = 1000
        self.created = []

    def add(self, unit, widget_type, name):
        self.next_idx += 1
        t, s, sw = TRIO[widget_type]
        self.units[unit] = {"ID": self.next_idx, "Type": t, "SubType": s, "SwitchType": sw, "Name": name}
        return self.next_idx

    def free_unit(self, *args, **kwargs):
        return next(u for u in range(1, 255) if u not in self.units)

    def create(self, _self, Devices, ieee, unit, name, widgetType=None, **kwargs):
        idx = self.add(unit, widgetType, f"{PLUGIN} - {name}")
        self.created.append((unit, widgetType, name))
        return idx

    def pool(self, _self, Devices, ieee):
        return {unit: dict(info) for unit, info in self.units.items()}


@pytest.fixture
def env(monkeypatch):
    _ensure_stub("DomoticzEx", Configuration=MagicMock(return_value={}), Unit=MagicMock(),
                 Device=MagicMock(), Connection=MagicMock(), Log=MagicMock(),
                 Debug=MagicMock(), Error=MagicMock(), Status=MagicMock())
    _ensure_stub("Modules.domoticzAbstractLayer",
                 retreive_free_unit_for_widget=MagicMock(), domo_create_api=MagicMock(),
                 get_unit_counts=MagicMock(), build_widget_reuse_pool=MagicMock())
    _ensure_stub("Modules.domoTools",
                 GetType=MagicMock(), remove_all_widgets=MagicMock(),
                 subtypeRGB_FromProfile_Device_IDs=MagicMock(),
                 subtypeRGB_FromProfile_Device_IDs_onEp2=MagicMock(),
                 update_domoticz_widget=MagicMock())
    _ensure_stub("Modules.switchSelectorWidgets", SWITCH_SELECTORS={})
    _ensure_stub("Modules.tools",
                 get_deviceconf_parameter_value=MagicMock(return_value=None),
                 is_domoticz_new_blind=MagicMock(return_value=False))

    mod = importlib.import_module("Modules.domoCreate")
    dz = _FakeDomoticz()

    monkeypatch.setattr(mod, "domo_create_api", dz.create)
    monkeypatch.setattr(mod, "retreive_free_unit_for_widget", dz.free_unit)
    monkeypatch.setattr(mod, "build_widget_reuse_pool", dz.pool)
    monkeypatch.setattr(mod, "get_unit_counts", MagicMock(return_value={"allocated": 0, "free": 254}))
    monkeypatch.setattr(mod, "set_default_value", MagicMock())
    monkeypatch.setattr(mod, "is_domoticz_new_blind", MagicMock(return_value=False))
    monkeypatch.setattr(mod, "get_deviceconf_parameter_value", MagicMock(return_value=False))
    return mod, dz


def _plugin(ep01_bindings=None, f1_bindings=None):
    obj = MagicMock()
    obj.pluginParameters = {"Name": PLUGIN}
    obj.DeviceConf = {}
    obj.widget_reuse_pool = {}
    obj.widget_creation_retries = {}
    obj.widget_creation_requests = {}
    obj.ListOfDevices = {
        NWKID: {
            "IEEE": IEEE,
            "Model": "NTCHT01-sonde-temp-humi",
            "Status": "inDB",
            "Ep": {
                "01": {"Type": "Temp/Humi", "ClusterType": dict(ep01_bindings or {})},
                "f1": {"Type": "Temp", "ClusterType": dict(f1_bindings or {})},
            },
        }
    }
    return obj


def _name(cluster_type, ep):
    return f"{PLUGIN} - NTCHT01-sonde-temp-humi_{cluster_type}-{IEEE}-{ep}"


def _recreate(mod, obj):
    mod.request_widget_creation(obj, NWKID, "recreate-widgets requested from the WebUI")
    mod.process_widget_creation_requests(obj, {})
    return obj.ListOfDevices[NWKID]["Ep"]


def _bound_on(eps, idx):
    return sorted(ep for ep, data in eps.items() if str(idx) in data["ClusterType"])


class TestRecreateDoesNotCrossEndpoints:

    def test_probe_widget_is_not_reused_for_the_ambient_temperature(self, env):
        # Kept: probe temperature (f1) and humidity (01). Ambient temp and Temp+Hum deleted.
        mod, dz = env
        probe = dz.add(4, "Temperature", _name("Temp", "f1"))
        humi = dz.add(3, "Humidity", _name("Humi", "01"))
        obj = _plugin(ep01_bindings={str(humi): "Humi"}, f1_bindings={str(probe): "Temp"})

        eps = _recreate(mod, obj)

        assert _bound_on(eps, probe) == ["f1"]
        assert _bound_on(eps, humi) == ["01"]
        assert sorted((w, n[-2:]) for _, w, n in dz.created) == [("Temp+Hum", "01"), ("Temperature", "01")]
        assert len(eps["f1"]["ClusterType"]) == 1

    def test_renamed_widgets_are_reused_on_their_own_endpoint(self, env):
        # Domoticz names changed by the user: the name match fails for every widget.
        mod, dz = env
        combo = dz.add(1, "Temp+Hum", "Jardin")
        ambient = dz.add(2, "Temperature", "Jardin temp")
        humi = dz.add(3, "Humidity", "Jardin humidité")
        probe = dz.add(4, "Temperature", "Sonde bassin")
        obj = _plugin(
            ep01_bindings={str(combo): "Temp+Hum", str(ambient): "Temp", str(humi): "Humi"},
            f1_bindings={str(probe): "Temp"})

        eps = _recreate(mod, obj)

        assert dz.created == []
        assert _bound_on(eps, ambient) == ["01"]
        assert _bound_on(eps, probe) == ["f1"]
        assert eps["01"]["ClusterType"] == {str(combo): "Temp+Hum", str(ambient): "Temp", str(humi): "Humi"}
        assert eps["f1"]["ClusterType"] == {str(probe): "Temp"}

    def test_all_widgets_deleted_creates_the_full_set(self, env):
        mod, dz = env
        obj = _plugin()
        obj.ListOfDevices[NWKID]["Status"] = "Removed"

        eps = _recreate(mod, obj)

        assert sorted((w, n[-2:]) for _, w, n in dz.created) == [
            ("Humidity", "01"), ("Temp+Hum", "01"), ("Temperature", "01"), ("Temperature", "f1")]
        assert obj.ListOfDevices[NWKID]["Status"] == "inDB"
        assert len(eps["01"]["ClusterType"]) == 3 and len(eps["f1"]["ClusterType"]) == 1


class TestRepairingStillReusesUnboundWidgets:
    """#1990: a re-paired device has a new record (nothing bound) but its old widgets
    are still in Domoticz. Those must still be picked up rather than duplicated."""

    def test_unbound_widgets_are_reused(self, env):
        mod, dz = env
        for unit, (wtype, ctype, ep) in enumerate(
                [("Temp+Hum", "Temp+Hum", "01"), ("Temperature", "Temp", "01"),
                 ("Humidity", "Humi", "01"), ("Temperature", "Temp", "f1")], start=1):
            dz.add(unit, wtype, _name(ctype, ep))
        obj = _plugin()

        eps = _recreate(mod, obj)

        assert dz.created == []
        assert sorted(eps["01"]["ClusterType"].values()) == ["Humi", "Temp", "Temp+Hum"]
        assert list(eps["f1"]["ClusterType"].values()) == ["Temp"]

    def test_single_unbound_widget_of_a_type_is_reused_on_any_endpoint(self, env):
        mod, dz = env
        orphan = dz.add(7, "Humidity", "renamed")
        obj = _plugin()

        eps = _recreate(mod, obj)

        assert _bound_on(eps, orphan) == ["01"]


class TestFindReusableWidgetUnit:

    def _pool(self, mod, obj, units):
        obj.widget_reuse_pool = {u: {"ID": i, "Type": 80, "SubType": 5, "SwitchType": 0, "Name": n}
                                 for u, (i, n) in units.items()}

    def test_bound_cluster_type_beats_a_name_match(self, env):
        mod, _ = env
        obj = MagicMock()
        self._pool(mod, obj, {1: (11, "target"), 2: (12, "other")})
        bindings = {"11": {"01": "TempA"}, "12": {"01": "TempB"}}

        unit = mod._find_reusable_widget_unit(obj, (80, 5, 0), "target", ep="01",
                                              cluster_type="TempB", bindings=bindings)

        assert unit == 2

    def test_widget_bound_elsewhere_is_never_a_candidate(self, env):
        mod, _ = env
        obj = MagicMock()
        self._pool(mod, obj, {1: (11, "target")})

        unit = mod._find_reusable_widget_unit(obj, (80, 5, 0), "target", ep="01",
                                              cluster_type="Temp", bindings={"11": {"f1": "Temp"}})

        assert unit is None

    def test_without_bindings_behaviour_is_unchanged(self, env):
        mod, _ = env
        obj = MagicMock()
        self._pool(mod, obj, {1: (11, "a"), 2: (12, "b")})

        assert mod._find_reusable_widget_unit(obj, (80, 5, 0), "b") == 2
        assert mod._find_reusable_widget_unit(obj, (80, 5, 0), "c") is None


class TestWidgetBindings:

    def test_maps_each_idx_to_its_endpoints(self, env):
        mod, _ = env
        obj = _plugin(ep01_bindings={"5": "Temp", "6": "Humi"}, f1_bindings={5: "Temp"})

        assert mod._widget_bindings(obj, NWKID) == {"5": {"01": "Temp", "f1": "Temp"}, "6": {"01": "Humi"}}

    def test_tolerates_missing_or_odd_entries(self, env):
        mod, _ = env
        obj = MagicMock()
        obj.ListOfDevices = {NWKID: {"Ep": {"01": "corrupted", "02": {}}, "ClusterType": {"9": "Temp"}}}

        assert mod._widget_bindings(obj, NWKID) == {}
        assert mod._widget_bindings(obj, "dead") == {}
