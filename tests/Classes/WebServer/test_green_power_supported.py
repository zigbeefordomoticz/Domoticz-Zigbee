#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.rest_GreenPower.green_power_supported and what
it gates: on a coordinator that cannot pair Green Power devices, the WebUI gets
no Green Power setting and no Green Power debug module, GET /plugin says
GreenPowerSupported false, and PUT /zgp-pairing is refused.

A ZNP coordinator receives no Green Power frame by itself, only through a router
with full Green Power support in between (zigpy discussion #1955). A native
(ZiGate) coordinator has no zigpy Green Power at all.

rest_Settings and rest_PluginEnv live in Classes/WebServer/WebServer.py, whose
import pulls the real Modules.* package in and breaks the stubs of
tests/conftest.py for the rest of the session: they run in a subprocess, and so
does the check of SETTINGS (Classes/PluginConf.py imports Modules.tools).
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from Classes.WebServer.rest_GreenPower import (green_power_supported,
                                               rest_zgp_pairing)

REPO_ROOT = Path(__file__).resolve().parents[3]

# name -> (zigbee_communication, radio module as Transport._radiomodule holds it)
COORDINATORS = {
    "ezsp": ("zigpy", "ezsp"),
    "deconz": ("zigpy", "deCONZ"),
    "blz": ("zigpy", "blz"),
    "znp": ("zigpy", "znp"),
    "native": ("native", None),
}
SUPPORTED = {"ezsp": True, "deconz": True, "blz": True, "znp": False, "native": False}


def webserver(name):
    communication, radio = COORDINATORS[name]
    return SimpleNamespace(
        zigbee_communication=communication,
        ControllerLink=SimpleNamespace(_radiomodule=radio, sendData=MagicMock()),
        pluginconf=SimpleNamespace(pluginConf={"enableKeepalive": False}),
    )


@pytest.mark.parametrize("name", sorted(COORDINATORS))
def test_green_power_supported(name):
    assert green_power_supported(webserver(name)) is SUPPORTED[name]


def test_zigpy_before_the_transport_is_up_is_not_refused():
    """No ControllerLink yet: nothing says the radio is ZNP."""
    assert green_power_supported(SimpleNamespace(zigbee_communication="zigpy")) is True


def test_put_pairing_refused_on_znp():
    server = webserver("znp")

    response = rest_zgp_pairing(server, "PUT", json.dumps({"Duration": 240}).encode("utf-8"), [])

    assert response["Status"] == "400 BAD REQUEST"
    assert "ZNP" in json.loads(response["Data"])["BE_Error"]
    server.ControllerLink.sendData.assert_not_called()


SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    from Classes.WebServer.WebServer import WebServer

    results = {}
    for name, (communication, radio) in json.loads(sys.argv[1]).items():
        server = types.SimpleNamespace(
            zigbee_communication=communication,
            ControllerLink=types.SimpleNamespace(_radiomodule=radio),
            pluginconf=types.SimpleNamespace(pluginConf={
                "GreenPowerEnable": 0, "GreenPower": 0, "GroupOnBattery": 0, "Groups": 0,
            }),
            pluginParameters={"Mode1": "Zigpy"},
        )
        names = {}
        for debug in (False, True):
            themes = json.loads(WebServer.rest_Settings(server, "GET", None, [], sendDebug=debug)["Data"])
            names[str(debug)] = sorted(s["Name"] for theme in themes for s in theme["ListOfSettings"])
        plugin = json.loads(WebServer.rest_PluginEnv(server, "GET", None, [])["Data"])
        results[name] = {"settings": names["False"], "debug": names["True"], "plugin": plugin["GreenPowerSupported"]}

    from Classes.PluginConf import SETTINGS
    results["_marked"] = sorted(
        param for theme in SETTINGS.values() for param, definition in theme["param"].items() if definition.get("GreenPowerOnly")
    )

    print(json.dumps(results))
    """
)


@pytest.fixture(scope="module")
def rest_results():
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(COORDINATORS)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_both_green_power_settings_are_marked(rest_results):
    assert rest_results["_marked"] == ["GreenPower", "GreenPowerEnable"]


@pytest.mark.parametrize("name", sorted(COORDINATORS))
def test_settings_show_green_power_only_where_supported(rest_results, name):
    assert ("GreenPowerEnable" in rest_results[name]["settings"]) is SUPPORTED[name]
    # Settings of other features stay
    assert "GroupOnBattery" in rest_results[name]["settings"]


@pytest.mark.parametrize("name", sorted(COORDINATORS))
def test_debug_shows_green_power_only_where_supported(rest_results, name):
    assert ("GreenPower" in rest_results[name]["debug"]) is SUPPORTED[name]
    assert "Groups" in rest_results[name]["debug"]


@pytest.mark.parametrize("name", sorted(COORDINATORS))
def test_plugin_tells_the_webui(rest_results, name):
    assert rest_results[name]["plugin"] is SUPPORTED[name]
