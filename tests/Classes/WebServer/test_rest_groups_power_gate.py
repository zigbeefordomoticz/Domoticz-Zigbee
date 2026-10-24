#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the power gate of Classes.WebServer.rest_Groups.

_is_ikea_round_remote_or_battery_enabled_or_main_powered() decides which devices the
group WebUI offers. It used to test MacCapa == "8e" itself, which is narrower than
mainPoweredDevice(): that helper also accepts MacCapa 84, honours the DeviceConf
MainPoweredDevice and BatteryPoweredDevice flags, and falls back to PowerSource. A
main-powered light announcing itself as battery -- lumi.light.aqcn02, Tuya TS0011 and
friends, which is precisely what MainPoweredDevice exists for -- was therefore absent
from the group device list unless the user enabled "Group Device on Battery", a setting
that has nothing to do with it.

The gate now delegates to mainPoweredDevice(), so these tests exercise the real helper
rather than a stub. Classes.WebServer.rest_Groups then imports the real Modules.*
package, which conflicts with the stubs tests/conftest.py installs for the session, so
the calls run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

NWKID = "1234"
OPPLE = "lumi.remote.b686opcn01"

# name -> (device record, DeviceConf, GroupOnBattery)
CASES = {
    # --- main powered, must be offered with GroupOnBattery off ---
    "maccapa_8e": ({"MacCapa": "8e"}, {}, 0),
    "maccapa_84": ({"MacCapa": "84"}, {}, 0),
    "deviceconf_main_powered": (
        {"MacCapa": "80", "Model": "lumi.light.aqcn02"},
        {"lumi.light.aqcn02": {"MainPoweredDevice": True}},
        0,
    ),
    "hardcoded_main_powered_model": ({"MacCapa": "80", "Model": "TS0011"}, {}, 0),
    "power_source_main": ({"MacCapa": {}, "PowerSource": "Main"}, {}, 0),

    # --- battery, must stay out with GroupOnBattery off ---
    "maccapa_80": ({"MacCapa": "80"}, {}, 0),
    "no_power_information": ({}, {}, 0),
    "deviceconf_battery_powered": (
        {"MacCapa": "8e", "Model": "some.battery.thing"},
        {"some.battery.thing": {"BatteryPoweredDevice": True}},
        0,
    ),
    "aqara_opple_announces_84_but_is_battery": ({"MacCapa": "84", "Model": OPPLE}, {}, 0),

    # --- the two other ways in, unchanged by this fix ---
    "battery_but_group_on_battery_enabled": ({"MacCapa": "80"}, {}, 1),
    "ikea_round_5b_on_battery": ({"MacCapa": "80", "Type": "Ikea_Round_5b"}, {}, 0),
}

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    from Classes.WebServer.rest_Groups import (
        _is_ikea_round_remote_or_battery_enabled_or_main_powered as gate)

    nwkid, cases = sys.argv[2], json.loads(sys.argv[3])

    results = {}
    for name, (device, device_conf, group_on_battery) in cases.items():
        plugin = types.SimpleNamespace(
            ListOfDevices={nwkid: device},
            DeviceConf=device_conf,
            pluginconf=types.SimpleNamespace(pluginConf={"GroupOnBattery": group_on_battery}),
            log=types.SimpleNamespace(logging=MagicMock()),
        )
        results[name] = bool(gate(plugin, nwkid))

    print(json.dumps(results))
    """
)


@pytest.fixture(scope="module")
def gate_results():
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, "run", NWKID, json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


class TestPowerGateOffersMainPoweredDevices:
    """With "Group Device on Battery" disabled, every main-powered device is offered."""

    def test_maccapa_8e(self, gate_results):
        assert gate_results["maccapa_8e"] is True

    def test_maccapa_84(self, gate_results):
        """84 is main powered too, and the old MacCapa == "8e" test rejected it."""
        assert gate_results["maccapa_84"] is True

    def test_deviceconf_main_powered_flag(self, gate_results):
        """
        The reported case: a mains light that announces itself as battery, which is why
        its z4d config carries MainPoweredDevice.
        """
        assert gate_results["deviceconf_main_powered"] is True

    def test_hardcoded_main_powered_model(self, gate_results):
        assert gate_results["hardcoded_main_powered_model"] is True

    def test_power_source_main_without_usable_maccapa(self, gate_results):
        assert gate_results["power_source_main"] is True


class TestPowerGateKeepsBatteryDevicesOut:
    """GroupOnBattery stays the switch for devices that really are battery powered."""

    def test_maccapa_80(self, gate_results):
        assert gate_results["maccapa_80"] is False

    def test_no_power_information_at_all(self, gate_results):
        assert gate_results["no_power_information"] is False

    def test_deviceconf_battery_powered_flag_wins_over_maccapa(self, gate_results):
        assert gate_results["deviceconf_battery_powered"] is False

    def test_aqara_opple_is_not_treated_as_main_powered(self, gate_results):
        """
        Regression guard on the shape of the fix: an Aqara Opple remote announces
        MacCapa 84 while running on a battery, so widening the gate to
        MacCapa in ("8e", "84") would have been wrong. Delegating to
        mainPoweredDevice() keeps the exclusion.
        """
        assert gate_results["aqara_opple_announces_84_but_is_battery"] is False


class TestPowerGateOtherWaysIn:
    """The two conditions this fix does not touch."""

    def test_group_on_battery_still_admits_battery_devices(self, gate_results):
        assert gate_results["battery_but_group_on_battery_enabled"] is True

    def test_ikea_round_5b_still_admitted_on_battery(self, gate_results):
        assert gate_results["ikea_round_5b_on_battery"] is True
