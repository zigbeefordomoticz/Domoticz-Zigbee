#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for DELETE on /rest-z4d/1/zdevice (dispatcher and WebServer.rest_zDevice).

The handler used self.ListOfDevice instead of self.ListOfDevices, so deleting a
known device always raised. No page calls it: the WebUI removes a device with
DELETE /zdevice-name. The route no longer accepts DELETE; /zdevice-name stays
the only device removal.

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

DEVICES = {
    "8012": {"IEEE": "00124b000425ea71", "ZDeviceName": "BT Bureau", "Health": "Live"},
    "4707": {"IEEE": "00124b000426a0dd", "ZDeviceName": "BT Parents", "Health": "Live"},
}
IEEE2NWK = {device["IEEE"]: nwkid for nwkid, device in DEVICES.items()}

CASES = {
    # name: verb, command, parameters
    "zdevice_by_nwkid": ["DELETE", "zdevice", ["8012"]],
    "zdevice_by_ieee": ["DELETE", "zdevice", ["00124b000425ea71"]],
    "zdevice_unknown": ["DELETE", "zdevice", ["ffff"]],
    "zdevice_get": ["GET", "zdevice", []],
    "zdevice_name_by_nwkid": ["DELETE", "zdevice-name", ["8012"]],
    "zdevice_name_by_ieee": ["DELETE", "zdevice-name", ["00124b000425ea71"]],
}


@pytest.fixture(scope="module")
def results():
    snippet = textwrap.dedent(
        """
        import collections, copy, functools, json, sys, types
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            sys.modules[name] = mod
        from Classes.WebServer.WebServer import WebServer
        from Classes.WebServer.dispatcher import do_rest, setup_list_rest_commands

        devices, ieee2nwk, cases = (json.loads(arg) for arg in sys.argv[1:4])
        out = {}
        for name, (verb, command, parameters) in cases.items():
            # A MagicMock answers for the other routes of setup_list_rest_commands
            plugin = MagicMock()
            plugin.REST_COMMANDS = {}
            plugin.pluginconf.pluginConf = collections.defaultdict(int)
            plugin.Devices = {1: "widget"}
            plugin.ListOfDevices = copy.deepcopy(devices)
            plugin.IEEE2NWK = dict(ieee2nwk)
            plugin.ControllerData = {}
            plugin.zigbee_communication = "zigpy"
            plugin.rest_zDevice = functools.partial(WebServer.rest_zDevice, plugin)
            plugin.rest_zDevice_name = functools.partial(WebServer.rest_zDevice_name, plugin)
            setup_list_rest_commands(plugin)
            do_rest(plugin, None, verb, b"", "1", command, parameters)
            (_, response), _ = plugin.sendResponse.call_args
            out[name] = {
                "status": response["Status"],
                "data": response["Data"],
                "devices": plugin.ListOfDevices,
                "ieee2nwk": plugin.IEEE2NWK,
            }
        print(json.dumps(out))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(DEVICES), json.dumps(IEEE2NWK), json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("case", ["zdevice_by_nwkid", "zdevice_by_ieee", "zdevice_unknown"])
def test_zdevice_refuses_delete(results, case):
    assert results[case]["status"] == "400 BAD REQUEST"
    assert results[case]["devices"] == DEVICES
    assert results[case]["ieee2nwk"] == IEEE2NWK


def test_zdevice_get_still_lists_the_devices(results):
    assert results["zdevice_get"]["status"] == "200 OK"
    assert sorted(device["_NwkId"] for device in json.loads(results["zdevice_get"]["data"])) == sorted(DEVICES)


@pytest.mark.parametrize("case", ["zdevice_name_by_nwkid", "zdevice_name_by_ieee"])
def test_zdevice_name_still_removes_a_device(results, case):
    assert results[case]["status"] == "200 OK"
    assert results[case]["devices"] == {"4707": DEVICES["4707"]}
    assert results[case]["ieee2nwk"] == {"00124b000426a0dd": "4707"}
