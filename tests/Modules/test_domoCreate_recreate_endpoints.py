#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Widgets created again must land on the endpoints they had at the pairing.

Field case: a Tuya TS011F plug has its widgets on Ep 01 and none on f2 (Green Power).
After a 'recreate widgets' it had a second set of all of them on f2: at the pairing
CreateDomoDevice stores the Types of the widgets it created as the Type of the device,
and the next run took that one for the Type of any endpoint without its own.

CreateDomoDevice and GetType run for real, twice: the pairing, then the recreation with
part of the widgets removed. Only the Domoticz side is faked. Modules.domoCreate imports
the real Modules.* package, which conflicts with the stubs tests/conftest.py installs for
the session, so the calls run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PLUG = "Plug/Power/Meter/Voltage/Ampere"

CASES = {
    # name: model in DeviceConf, its configuration, the Ep of the record at the pairing,
    # its Type at the pairing, and the Types whose widgets are removed before the recreation
    "tuya_plug": {
        "model": "TS011F-plug",
        "conf": {"Type": "", "Ep": {"01": {"0006": "", "Type": PLUG}, "f2": {"0021": ""}}},
        "ep": {"01": {"0006": {}, "Type": PLUG}, "f2": {"0021": {}}},
        "type": "",
        "keep": ["Plug"],
    },
    # The endpoint without widget comes first
    "untyped_endpoint_first": {
        "model": "AQSZB-110",
        "conf": {"Type": "", "Ep": {"01": {"0000": ""}, "26": {"0402": "", "Type": "Temp/Humi"}}},
        "ep": {"01": {"0000": {}}, "26": {"0402": {}, "Type": "Temp/Humi"}},
        "type": "",
        "keep": [],
    },
    # Some configuration files give {} as the Type of an endpoint without widget
    "empty_dict_type": {
        "model": "EGLO_ZM_RGB_TW",
        "conf": {"Type": "", "Ep": {"01": {"0402": "", "Type": "Temp"}, "03": {"1000": "", "Type": {}}}},
        "ep": {"01": {"0402": {}, "Type": "Temp"}, "03": {"1000": {}, "Type": {}}},
        "type": "",
        "keep": [],
    },
    # The Type of a device configured for the whole device keeps creating on the first endpoint
    "device_level_type": {
        "model": "global",
        "conf": {"Type": "Temp/Humi", "Ep": {"01": {"0402": ""}, "02": {"0405": ""}}},
        "ep": {"01": {"0402": {}}, "02": {"0405": {}}},
        "type": "Temp/Humi",
        "keep": [],
    },
    # A configuration file that came after the pairing: the Ep of the record have no Type
    "configured_after_pairing": {
        "model": "late",
        "conf": {"Type": "", "Ep": {"01": {"0402": "", "Type": "Temp"}, "f2": {"0021": ""}}},
        "ep": {"01": {"0402": {}}, "f2": {"0021": {}}},
        "type": "",
        "keep": [],
    },
    # No configuration file: the Types come from the clusters of each endpoint
    "not_certified": {
        "model": "unknown-model",
        "conf": None,
        "ep": {"01": {"0402": {}}, "02": {"0405": {}}, "f2": {"0021": {}}},
        "type": {},
        "keep": [],
    },
}


@pytest.fixture(scope="module")
def results():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            mod.Configuration = mod.Unit = mod.Device = mod.Connection = MagicMock()
            sys.modules[name] = mod
        import Modules.domoCreate as domoCreate

        IEEE, NWKID = "a4c1380000000001", "6f97"

        def run(case):
            units, idx = {}, [1000]

            def create(self, Devices, ieee, unit, name, widgetType=None, Type_=None, Subtype_=None,
                       Switchtype_=None, widgetOptions=None, **kwargs):
                idx[0] += 1
                t, sub, switch = domoCreate._resolve_widget_trio(
                    widgetType, Type_, Subtype_, Switchtype_, widgetOptions)
                units[unit] = {"ID": idx[0], "Type": t, "SubType": sub, "SwitchType": switch,
                               "Name": "EZSP - " + name}
                return idx[0]

            domoCreate.domo_create_api = create
            domoCreate.retreive_free_unit_for_widget = lambda *a, **k: next(u for u in range(1, 255) if u not in units)
            domoCreate.build_widget_reuse_pool = lambda *a, **k: {u: dict(i) for u, i in units.items()}
            domoCreate.get_unit_counts = lambda *a, **k: {"allocated": len(units), "free": 254 - len(units)}
            domoCreate.set_default_value = lambda *a, **k: None

            plugin = MagicMock()
            plugin.pluginParameters = {"Name": "EZSP"}
            plugin.DeviceConf = {} if case["conf"] is None else {case["model"]: case["conf"]}
            plugin.widget_reuse_pool = {}
            plugin.DomoticzMajor, plugin.DomoticzMinor, plugin.DomoticzBuild = 2025, 2, 0
            device = {
                "IEEE": IEEE, "Model": case["model"], "ProfileID": "0104", "ZDeviceID": "0051",
                "Type": case["type"], "Status": "CreateDB", "Ep": case["ep"],
            }
            plugin.ListOfDevices = {NWKID: device}

            def bound():
                return {ep: sorted(info["ClusterType"].values())
                        for ep, info in device["Ep"].items() if info.get("ClusterType")}

            domoCreate.CreateDomoDevice(plugin, {}, NWKID)
            paired = bound()
            paired_units = len(units)

            # The user removes widgets: Domoticz and the record lose them
            for info in device["Ep"].values():
                for widget_idx, cluster_type in list(info.get("ClusterType", {}).items()):
                    if cluster_type not in case["keep"]:
                        del info["ClusterType"][widget_idx]
                        for unit in [u for u, i in units.items() if str(i["ID"]) == widget_idx]:
                            del units[unit]
            # What recreate-widgets runs
            domoCreate.over_write_type_from_deviceconf(plugin, {}, NWKID)
            domoCreate.CreateDomoDevice(plugin, {}, NWKID)
            return {"paired": paired, "recreated": bound(),
                    "paired_units": paired_units, "recreated_units": len(units)}

        print(json.dumps({name: run(case) for name, case in json.loads(sys.argv[1]).items()}))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("name", sorted(CASES))
def test_recreated_widgets_are_those_of_the_pairing(results, name):
    case = results[name]
    assert case["paired"], "the pairing created no widget"
    assert case["recreated"] == case["paired"]
    assert case["recreated_units"] == case["paired_units"]


def test_tuya_plug_has_no_widget_on_the_green_power_endpoint(results):
    assert results["tuya_plug"]["recreated"] == {"01": ["Ampere", "Meter", "Plug", "Power", "Voltage"]}


def test_widgets_stay_on_their_endpoint_when_an_untyped_one_comes_first(results):
    assert list(results["untyped_endpoint_first"]["recreated"]) == ["26"]


def test_device_level_type_creates_on_the_first_endpoint_only(results):
    assert list(results["device_level_type"]["recreated"]) == ["01"]
