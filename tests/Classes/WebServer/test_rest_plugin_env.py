#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for GET /rest-z4d/1/plugin (rest_PluginEnv), issue #2212.

The handler answered get_plugin_parameters(self) without its filter, so the
response carried the hardware parameters Mode5 (Domoticz API URL), Username
and Password. The device configuration export already used the filter; /plugin
now does too. The Web UI reads none of these three keys from /plugin.

Classes.WebServer.WebServer imports the real Modules.* package, which
conflicts with the stubs tests/conftest.py installs for the session, so the
call runs in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

PLUGIN_PARAMETERS = {
    "HardwareID": 12,
    "Name": "Zigbee",
    "PluginVersion": "9.1.008",
    "PluginBranch": "stable9",
    "Mode5": "http://admin:secret@127.0.0.1:8080",
    "Username": "admin",
    "Password": "secret",
}
REMOVED = ("Mode5", "Username", "Password")

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    import Classes.WebServer.WebServer as W

    class PluginConf:
        pluginConf = {}

    class Plugin:
        pluginconf = PluginConf()
        pluginParameters = json.loads(sys.argv[1])

    plugin = Plugin()
    response = W.WebServer.rest_PluginEnv(plugin, "GET", None, [])
    print(json.dumps({"data": json.loads(response["Data"]), "after": plugin.pluginParameters}))
    """
)


@pytest.fixture(scope="module")
def result():
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(PLUGIN_PARAMETERS)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return json.loads(proc.stdout)


@pytest.mark.parametrize("key", REMOVED)
def test_hardware_secrets_not_returned(result, key):
    assert key not in result["data"]


def test_other_parameters_still_returned(result):
    for key, value in PLUGIN_PARAMETERS.items():
        if key not in REMOVED:
            assert result["data"][key] == value
    assert "DistributionInfos" in result["data"]


def test_plugin_parameters_left_untouched(result):
    # The filter works on a copy: the plugin still needs Mode5 / Username / Password.
    assert result["after"] == PLUGIN_PARAMETERS
