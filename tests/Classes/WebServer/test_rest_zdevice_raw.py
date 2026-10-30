#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.WebServer.rest_zDevice_raw.

RollingLQI is a deque (Modules/tools_sqn.updLQI). GET /zdevice-raw/<nwkid> serialised
its answer twice, first with a plain json.dumps, so a device that had received an LQI
since the plugin started raised "TypeError: Object of type deque is not JSON
serializable" and the WebUI device details got no answer. The list form, which only
used ZigbeeJSONEncoder, worked.

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

NWKID = "b1b7"
IEEE = "000474000082a54f"
LQI = [252, 252, 248]
RSSI = [-40, -38]


@pytest.fixture(scope="module")
def answers():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        from collections import deque
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            sys.modules[name] = mod
        import Classes.WebServer.WebServer as webserver

        # Not under test: the plugin parameters attached to a single-device answer
        webserver.get_plugin_parameters = lambda self, filter=False: {"Mode": "zigpy"}

        NWKID, IEEE, LQI, RSSI = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), json.loads(sys.argv[4])

        class PluginConf:
            pluginConf = {"PluginAnalytics": False}

        class Plugin:
            def __init__(self):
                self.pluginconf = PluginConf()
                self.Devices = {1: object()}
                self.DeviceConf = {}
                self.IEEE2NWK = {IEEE: NWKID}
                self.ListOfDevices = {NWKID: {
                    "IEEE": IEEE, "Model": "Dimmer switch wo neutral",
                    "RollingLQI": deque(LQI, maxlen=10), "RollingRSSI": list(RSSI),
                }}

        answers = {}
        for name, parameters in (("by_nwkid", [NWKID]), ("by_ieee", [IEEE]), ("list", [])):
            try:
                answers[name] = json.loads(webserver.WebServer.rest_zDevice_raw(Plugin(), "GET", None, parameters)["Data"])
            except Exception as error:
                answers[name] = {"raised": "%s: %s" % (type(error).__name__, error)}
        print(json.dumps(answers))
        """
    )
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, NWKID, IEEE, json.dumps(LQI), json.dumps(RSSI)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("name", ["by_nwkid", "by_ieee"])
def test_single_device_answer_serialises_the_rolling_lqi_deque(answers, name):
    answer = answers[name]
    assert "raised" not in answer, answer["raised"]
    assert answer["Device"]["RollingLQI"] == LQI
    assert answer["Device"]["RollingRSSI"] == RSSI


def test_list_answer_serialises_the_rolling_lqi_deque(answers):
    answer = answers["list"]
    assert "raised" not in answer, answer
    assert answer[0]["NwkID"] == NWKID
    assert answer[0]["RollingLQI"] == LQI
