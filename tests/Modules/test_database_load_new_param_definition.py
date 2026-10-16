#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/database.py - load_new_param_definition()

At start-up, every certified Param a device does not carry yet (device paired
before the certified JSON gained it) is copied from DeviceConf. Coverage:
  - an early exit inside the loop (manufacturer not in a polling table, no
    Manufacturer at all) aborted the whole function, so every device after it
    in ListOfDevices, and the remaining Params of that device, were left out,
    at every restart.
  - the polling Params were then overwritten by a hidden plugin-wide setting
    whose default is 0, which turned polling off where pairing would have
    kept the certified value.
  - "PowerOnAfterOffOn" was matched as a substring, not by name.

Modules.database imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    from Modules.database import load_new_param_definition

    DEVICE_CONF = {
        "TuyaPlug": {"Param": {"PowerPollingFreq": 300, "netatmoLedIfOn": 0}},
        "NoManuf": {"Param": {"PowerOnAfterOffOn": 255, "netatmoLedInDark": 0}},
        "HueBulb": {"Param": {"OnOffPollingFreq": 300, "OffOn": 7}},
        "LumiPlug": {"Param": {"PowerPollingFreq": 300}},
        "AC201": {"Param": {"AC201Polling": 300}},
    }

    def run(plugin_conf, devices):
        p = types.SimpleNamespace()
        p.log = types.SimpleNamespace(logging=lambda *a, **k: None)
        p.DeviceConf = DEVICE_CONF
        conf = {
            "pollingPhilips": 0, "pollingGledopto": 0, "pollingBlitzwolfPower": 0,
            "pollingLumiPower": 0, "pollingCasaiaAC201": 0,
            "PhilipsPowerOnAfterOffOn": 1, "EnableLedIfOn": 1, "EnableLedInDark": 1,
        }
        conf.update(plugin_conf)
        p.pluginconf = types.SimpleNamespace(pluginConf=conf)
        p.ListOfDevices = devices
        load_new_param_definition(p)
        return {k: {"Param": v.get("Param"), "CheckParam": v.get("CheckParam")} for k, v in devices.items()}

    cases = json.loads(sys.argv[1])
    print(json.dumps({name: run(c["conf"], c["devices"]) for name, c in cases.items()}))
    """
)


def _run(cases):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT, json.dumps(cases)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


TUYA_PLUG = {"Model": "TuyaPlug", "Manufacturer": "1002", "Manufacturer Name": "_TZ3000_xxxxxxxx"}
NO_MANUF = {"Model": "NoManuf"}
HUE_BULB = {"Model": "HueBulb", "Manufacturer": "100b", "Manufacturer Name": "Philips"}
LUMI_PLUG = {"Model": "LumiPlug", "Manufacturer": "115f", "Manufacturer Name": "LUMI"}
AC201 = {"Model": "AC201", "Manufacturer": "113c", "Manufacturer Name": "OWON"}

CASES = {
    # A device whose manufacturer has no polling override comes first
    "unmapped_manufacturer_first": {"conf": {}, "devices": {"aaaa": dict(TUYA_PLUG), "bbbb": dict(TUYA_PLUG)}},
    # A device without Manufacturer and a PowerOnAfterOffOn Param comes first
    "no_manufacturer_first": {"conf": {}, "devices": {"aaaa": dict(NO_MANUF), "bbbb": dict(TUYA_PLUG)}},
    # Hidden plugin-wide polling settings left at their default (0)
    "polling_globals_default": {"conf": {}, "devices": {"1111": dict(HUE_BULB), "2222": dict(LUMI_PLUG), "3333": dict(AC201)}},
    # Hidden plugin-wide polling settings set by the user
    "polling_globals_set": {
        "conf": {"pollingPhilips": 600, "pollingLumiPower": 900, "pollingCasaiaAC201": 1200},
        "devices": {"1111": dict(HUE_BULB), "2222": dict(LUMI_PLUG), "3333": dict(AC201)},
    },
    # A Param already on the device is left alone
    "existing_param_kept": {"conf": {"pollingPhilips": 600}, "devices": {"1111": dict(HUE_BULB, Param={"OnOffPollingFreq": 42, "OffOn": 3})}},
}


@pytest.fixture(scope="module")
def results():
    return _run(CASES)


def test_unmapped_manufacturer_does_not_stop_the_loop(results):
    res = results["unmapped_manufacturer_first"]
    assert res["aaaa"]["Param"] == {"PowerPollingFreq": 300, "netatmoLedIfOn": 1}
    assert res["bbbb"]["Param"] == {"PowerPollingFreq": 300, "netatmoLedIfOn": 1}
    assert res["bbbb"]["CheckParam"] is True


def test_device_without_manufacturer_does_not_stop_the_loop(results):
    res = results["no_manufacturer_first"]
    assert res["aaaa"]["Param"] == {"PowerOnAfterOffOn": 255, "netatmoLedInDark": 1}
    assert res["bbbb"]["Param"] == {"PowerPollingFreq": 300, "netatmoLedIfOn": 1}
    assert res["bbbb"]["CheckParam"] is True


def test_default_polling_globals_keep_the_certified_value(results):
    res = results["polling_globals_default"]
    assert res["1111"]["Param"]["OnOffPollingFreq"] == 300
    assert res["2222"]["Param"]["PowerPollingFreq"] == 300
    assert res["3333"]["Param"]["AC201Polling"] == 300


def test_polling_globals_set_by_the_user_still_apply(results):
    res = results["polling_globals_set"]
    assert res["1111"]["Param"]["OnOffPollingFreq"] == 600
    assert res["2222"]["Param"]["PowerPollingFreq"] == 900
    assert res["3333"]["Param"]["AC201Polling"] == 1200


def test_power_on_after_off_on_is_matched_by_name_only(results):
    res = results["polling_globals_default"]
    assert res["1111"]["Param"]["OffOn"] == 7


def test_existing_param_is_not_overwritten(results):
    assert results["existing_param_kept"]["1111"]["Param"] == {"OnOffPollingFreq": 42, "OffOn": 3}
