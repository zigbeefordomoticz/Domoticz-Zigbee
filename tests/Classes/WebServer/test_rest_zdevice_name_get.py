#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for GET /rest-z4d/1/zdevice-name (WebServer.rest_zDevice_name).

For a device without Param, the "Param" default ("{}") was overwritten by the
else branch of the following "if item == 'CheckParam'", so the Device
Management page got Param: "" instead of an empty parameter set to edit.

Classes.WebServer.WebServer imports the real Modules.* package, which conflicts
with the stubs tests/conftest.py installs for the session, so the call runs in
a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

DEVICES = {
    "8012": {"IEEE": "00124b000425ea71", "ZDeviceName": "BT Bureau", "Health": "Live", "MacCapa": "80", "Ep": {}, "Param": {"Disabled": 0}, "CheckParam": True},
    "3a7f": {"IEEE": "a4c13800ab12cd34", "ZDeviceName": "", "Health": "Live", "MacCapa": "8e", "Ep": {}},
}


@pytest.fixture(scope="module")
def devices():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            sys.modules[name] = mod
        from Classes.WebServer.WebServer import WebServer

        class PluginConf:
            pluginConf = {}

        class Plugin:
            ListOfDomoticzWidget = {}
            def __init__(self, devices):
                self.pluginconf = PluginConf()
                self.ListOfDevices = devices
            def fake_mode(self):
                return False
            def logging(self, level, message):
                pass

        response = WebServer.rest_zDevice_name(Plugin(json.loads(sys.argv[1])), "GET", None, [])
        print(response["Data"])
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(DEVICES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return {device["_NwkId"]: device for device in json.loads(result.stdout.strip().splitlines()[-1])}


def test_device_without_param_gets_an_empty_param(devices):
    assert devices["3a7f"]["Param"] == "{}"
    assert devices["3a7f"]["CheckParam"] is False


def test_device_with_param_is_unchanged(devices):
    assert devices["8012"]["Param"] == "{'Disabled': 0}"
    assert devices["8012"]["CheckParam"] is True


def test_other_missing_fields_stay_empty(devices):
    assert devices["3a7f"]["Model"] == ""
    assert devices["3a7f"]["Battery"] == ""
