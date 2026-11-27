#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/lumi.py:lumi_private_cluster, the ff01 tag 0x64 (uint8) gate.

Tag 0x64 / type 0x20 carries the on/off of an Aqara bulb (and the lift position of
lumi.curtain). It was applied only when MacCapa == "8e". ReArrangeMacCapaBasedOnModel()
now keeps a MainPoweredDevice model that announced itself as an end device at
MacCapa 84 instead of 8e, and lumi.light.aqcn02 is such a model (it announces 80).
The gate therefore asks mainPoweredDevice(), which also keeps battery devices out,
the Aqara Opple remote (announces 84) included.

Modules.lumi is stubbed by tests/conftest.py for the session, so the real module is
imported in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

NWKID = "1234"
FF01_TAG_64_UINT8_ON = "642001"

# name -> (device record, DeviceConf)
CASES = {
    "aqcn02_kept_at_84": (
        {"Model": "lumi.light.aqcn02", "MacCapa": "84", "PowerSource": "Main"},
        {"lumi.light.aqcn02": {"MainPoweredDevice": True}},
    ),
    "router_8e": ({"Model": "lumi.curtain", "MacCapa": "8e"}, {}),
    "battery_80": ({"Model": "lumi.sensor_smoke", "MacCapa": "80", "PowerSource": "Battery"}, {}),
    "opple_announces_84_but_is_battery": ({"Model": "lumi.remote.b686opcn01", "MacCapa": "84"}, {}),
    "wleak_excluded_by_name": ({"Model": "lumi.sensor_wleak.aq1", "MacCapa": "8e"}, {}),
}

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    import Modules.readAttributes  # noqa: F401  (import order of the plugin: breaks the domoMaj/tuya cycle)
    import Modules.lumi as lumi

    maj_domo_device = MagicMock()
    lumi.MajDomoDevice = maj_domo_device
    lumi.checkAndStoreAttributeValue = MagicMock()

    nwkid, payload, cases = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])

    results = {}
    for name, (device, device_conf) in cases.items():
        maj_domo_device.reset_mock()
        plugin = types.SimpleNamespace(
            ListOfDevices={nwkid: dict(device, Ep={"01": {}})},
            DeviceConf=device_conf,
            pluginconf=types.SimpleNamespace(pluginConf={}),
            log=types.SimpleNamespace(logging=MagicMock()),
        )
        lumi.lumi_private_cluster(plugin, {}, nwkid, "01", "0000", "ff01", payload)
        results[name] = [list(call.args[4:6]) for call in maj_domo_device.call_args_list]

    print(json.dumps(results))
    """
)


@pytest.fixture(scope="module")
def updates():
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, "run", NWKID, FF01_TAG_64_UINT8_ON, json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_main_powered_bulb_kept_at_maccapa_84_gets_its_on_off(updates):
    assert updates["aqcn02_kept_at_84"] == [["0006", "01"]]


def test_maccapa_8e_still_gets_it(updates):
    assert updates["router_8e"] == [["0006", "01"]]


def test_battery_device_does_not(updates):
    assert updates["battery_80"] == []


def test_aqara_opple_does_not(updates):
    """MacCapa 84 alone is not enough: the Opple remote announces 84 on a battery."""
    assert updates["opple_announces_84_but_is_battery"] == []


def test_water_leak_sensor_stays_excluded(updates):
    assert updates["wleak_excluded_by_name"] == []
