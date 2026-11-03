#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for PUT /rest-z4d/1/zdevice-name (WebServer.rest_zDevice_name).

The Device Management page is given each device's Param as str(dict) and sends
every device back on save. The handler compared that string with the stored
dict, which never matched, so renaming one device re-decoded the Param of every
device, set CheckParam (the next heartbeat re-applies all its parameters) and,
for each Param holding 'Disabled': 0, reset Health to "unknown".

The decoded Param is now compared with the stored one: an unchanged device is
left alone, and Health only follows a change of the Disabled flag.

A Param with a syntax error was decoded to {} and replaced the stored one,
wiping the device's parameters; it is now reported and the stored Param kept.

Classes.WebServer.WebServer imports the real Modules.* package, which conflicts
with the stubs tests/conftest.py installs for the session, so the calls run in
a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

PARAM = {"Disabled": 0, "BatteryPollingFreq": 21600, "Calibration": 0}

DEVICES = {
    "8012": {"IEEE": "00124b000425ea71", "ZDeviceName": "BT Bureau", "Health": "Live", "Param": dict(PARAM)},
    "4707": {"IEEE": "00124b000426a0dd", "ZDeviceName": "BT Parents", "Health": "Live", "Param": dict(PARAM)},
    "9e44": {"IEEE": "a4c13892f0e1d2c3", "ZDeviceName": "Fuite Cave", "Health": "Disabled", "Param": {"Disabled": 1}},
    "3a7f": {"IEEE": "a4c13800ab12cd34", "ZDeviceName": "", "Health": "Live"},
}


def page_rows():
    """What the page sends back untouched: Param as the str(dict) GET gave it ("" when the device has none)."""
    return [{"_NwkId": nwkid, "IEEE": dev["IEEE"], "ZDeviceName": dev["ZDeviceName"], "Param": str(dev["Param"]) if "Param" in dev else ""} for nwkid, dev in DEVICES.items()]


def with_changes(changes):
    rows = page_rows()
    for row in rows:
        row.update(changes.get(row["_NwkId"], {}))
    return rows


CASES = {
    # name: rows sent by the page
    "unchanged": page_rows(),
    "rename_one": with_changes({"8012": {"ZDeviceName": "Bureau"}}),
    "param_changed": with_changes({"4707": {"Param": "{'Disabled': 0, 'BatteryPollingFreq': 21600, 'Calibration': 1}"}}),
    "param_as_json": with_changes({"4707": {"Param": json.dumps(PARAM)}}),
    "disable": with_changes({"8012": {"Param": "{'Disabled': 1, 'BatteryPollingFreq': 21600, 'Calibration': 0}"}}),
    "enable": with_changes({"9e44": {"Param": "{'Disabled': 0}"}}),
    "no_param_key": [{"IEEE": DEVICES["8012"]["IEEE"], "ZDeviceName": "Bureau"}],
    "param_typo": with_changes({"4707": {"ZDeviceName": "Parents", "Param": "{'Disabled': 0, 'BatteryPollingFreq': 21600, 'Calibration': 1"}}),
}


@pytest.fixture(scope="module")
def results():
    snippet = textwrap.dedent(
        """
        import copy, json, sys, types
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            sys.modules[name] = mod
        from Classes.WebServer.WebServer import WebServer

        class PluginConf:
            pluginConf = {}

        class Plugin:
            def __init__(self, devices):
                self.pluginconf = PluginConf()
                self.ListOfDevices = devices
                self.errors = []
            def logging(self, level, message):
                if level == "Error":
                    self.errors.append(message)

        devices, cases = json.loads(sys.argv[1]), json.loads(sys.argv[2])
        out = {}
        for name, rows in cases.items():
            plugin = Plugin(copy.deepcopy(devices))
            try:
                WebServer.rest_zDevice_name(plugin, "PUT", json.dumps(rows).encode("utf8"), [])
            except Exception as error:
                plugin.errors.append("%s: %s" % (type(error).__name__, error))
            out[name] = {"devices": plugin.ListOfDevices, "errors": plugin.errors}
        print(json.dumps(out))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(DEVICES), json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def check_param_flagged(devices):
    return sorted(nwkid for nwkid, dev in devices.items() if dev.get("CheckParam"))


def test_unchanged_page_touches_no_device(results):
    devices = results["unchanged"]["devices"]
    assert devices == DEVICES
    assert results["unchanged"]["errors"] == []


def test_rename_only_changes_the_name(results):
    devices = results["rename_one"]["devices"]
    assert devices["8012"]["ZDeviceName"] == "Bureau"
    assert check_param_flagged(devices) == []
    assert {nwkid: dev["Health"] for nwkid, dev in devices.items()} == {nwkid: dev["Health"] for nwkid, dev in DEVICES.items()}
    assert "Param" not in devices["3a7f"]


def test_changed_param_is_applied_and_health_kept(results):
    devices = results["param_changed"]["devices"]
    assert devices["4707"]["Param"] == {"Disabled": 0, "BatteryPollingFreq": 21600, "Calibration": 1}
    assert check_param_flagged(devices) == ["4707"]
    assert devices["4707"]["Health"] == "Live"


def test_same_param_sent_as_json_is_unchanged(results):
    assert check_param_flagged(results["param_as_json"]["devices"]) == []


def test_disable_sets_health_disabled(results):
    devices = results["disable"]["devices"]
    assert devices["8012"]["Health"] == "Disabled"
    assert check_param_flagged(devices) == ["8012"]


def test_enable_leaves_disabled_health(results):
    devices = results["enable"]["devices"]
    assert devices["9e44"]["Health"] == "unknown"
    assert devices["9e44"]["Param"] == {"Disabled": 0}
    assert check_param_flagged(devices) == ["9e44"]


def test_row_without_param_only_renames(results):
    assert results["no_param_key"]["errors"] == []
    devices = results["no_param_key"]["devices"]
    assert devices["8012"]["ZDeviceName"] == "Bureau"
    assert devices["8012"]["Param"] == PARAM
    assert check_param_flagged(devices) == []


def test_param_with_syntax_error_keeps_the_stored_param(results):
    devices = results["param_typo"]["devices"]
    assert devices["4707"]["Param"] == PARAM
    assert devices["4707"]["ZDeviceName"] == "Parents"
    assert devices["4707"]["Health"] == "Live"
    assert check_param_flagged(devices) == []
    assert len(results["param_typo"]["errors"]) == 1 and "wrong Parameter syntax" in results["param_typo"]["errors"][0]
