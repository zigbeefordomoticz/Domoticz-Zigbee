#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for DELETE /rest-z4d/1/zdevice-name/<nwkid or ieee> ("Remove device"
of the WebUI, Classes/WebServer/rest_DeviceRemoval.py).

On zigpy the plugin only dropped its record and sent nothing: the device kept
the network key and came back without pairing mode. It is now asked to leave
(REMOVE-DEVICE, as when the last widget is deleted), only when it has no widget.

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

COORDINATOR = "00124b00aaaaaaaa"
NO_WIDGET = "00124b000425ea71"
WITH_WIDGET = "00124b000426a0dd"
MOVED = "a4c13892f0e1d2c3"

# "0001" is a stale record of MOVED, which is alive as "9e44"; "3a7f" never gave its IEEE;
# the IEEE of "5b5b" has no IEEE2NWK entry
DEVICES = {
    "0000": {"IEEE": COORDINATOR},
    "8012": {"IEEE": NO_WIDGET},
    "4707": {"IEEE": WITH_WIDGET},
    "9e44": {"IEEE": MOVED},
    "0001": {"IEEE": MOVED},
    "3a7f": {"IEEE": {}},
    "5b5b": {"IEEE": "a4c13800ab12cd34"},
}
IEEE2NWK = {COORDINATOR: "0000", NO_WIDGET: "8012", WITH_WIDGET: "4707", MOVED: "9e44"}
WIDGETS = {WITH_WIDGET: [1, 2], MOVED: [1], "00124b000425ea72": [1]}

CASES = {
    # name: (parameters, zigbee_communication, ControllerLink present)
    "by_nwkid": (["8012"], "zigpy", True),
    "by_ieee": ([NO_WIDGET], "zigpy", True),
    "native": (["8012"], "native", True),
    "no_link": (["8012"], "zigpy", False),
    "with_widgets": (["4707"], "zigpy", True),
    "with_widgets_by_ieee": ([WITH_WIDGET], "zigpy", True),
    "unknown_nwkid": (["beef"], "zigpy", True),
    "unknown_ieee": (["ffffffffffffffff"], "zigpy", True),
    "coordinator": (["0000"], "zigpy", True),
    "coordinator_by_ieee": ([COORDINATOR], "zigpy", True),
    "stale_record": (["0001"], "zigpy", True),
    "no_ieee": (["3a7f"], "zigpy", True),
    "ieee_not_mapped": (["5b5b"], "zigpy", True),
    "no_parameter": ([], "zigpy", True),
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
        from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict
        from Classes.WebServer import rest_DeviceRemoval
        from Classes.WebServer.WebServer import WebServer

        devices, ieee2nwk, widgets, coordinator, cases = json.loads(sys.argv[1])
        native = []
        rest_DeviceRemoval.sendZigateCmd = lambda self, cmd, datas: native.append([cmd, datas])

        class PluginConf:
            pluginConf = {}

        class Plugin:
            def __init__(self, communication, link):
                self.pluginconf = PluginConf()
                self.log = MagicMock()
                self.zigbee_communication = communication
                self.ControllerIEEE = coordinator
                self.ControllerData = {"IEEE": coordinator}
                self.ListOfDevices = ThreadSafeDeviceDict(copy.deepcopy(devices))
                self.IEEE2NWK = ThreadSafeDeviceDict(ieee2nwk)
                self.Devices = {ieee: types.SimpleNamespace(Units={u: None for u in units}) for ieee, units in widgets.items()}
                self.sent = []
                self.ControllerLink = types.SimpleNamespace(sendData=self.send) if link else None
            def send(self, cmd, datas):
                # The request leaves before the record is dropped
                self.sent.append([cmd, "%016x" % datas["Param1"], len(self.ListOfDevices)])

        out = {}
        for name, (parameters, communication, link) in cases.items():
            plugin = Plugin(communication, link)
            native.clear()
            response = WebServer.rest_zDevice_name(plugin, "DELETE", None, parameters)
            out[name] = {
                "status": response["Status"],
                "data": json.loads(response["Data"]) if response["Data"] else None,
                "gone": sorted(set(devices) - set(plugin.ListOfDevices)),
                "unmapped": sorted(set(ieee2nwk) - set(plugin.IEEE2NWK)),
                "sent": plugin.sent,
                "native": list(native),
            }
        print(json.dumps(out))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps([DEVICES, IEEE2NWK, WIDGETS, COORDINATOR, CASES])],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("case", ["by_nwkid", "by_ieee"])
def test_device_without_widget_is_asked_to_leave_then_forgotten(results, case):
    res = results[case]
    assert res["status"] == "200 OK"
    assert res["data"] == {"Name": "Device 8012/%s removed" % NO_WIDGET}
    assert res["sent"] == [["REMOVE-DEVICE", NO_WIDGET, len(DEVICES)]]
    assert res["gone"] == ["8012"]
    assert res["unmapped"] == [NO_WIDGET]


def test_native_sends_the_same_command_as_before(results):
    res = results["native"]
    assert res["native"] == [["0026", COORDINATOR + NO_WIDGET]]
    assert res["sent"] == []
    assert res["gone"] == ["8012"]


def test_record_is_dropped_without_a_controller_link(results):
    res = results["no_link"]
    assert res["status"] == "200 OK"
    assert res["gone"] == ["8012"]


@pytest.mark.parametrize("case", ["with_widgets", "with_widgets_by_ieee"])
def test_device_with_widgets_is_refused(results, case):
    res = results[case]
    assert res["status"].startswith("400")
    assert "widget" in res["data"]["BE_Error"]
    assert (res["sent"], res["gone"], res["unmapped"]) == ([], [], [])


@pytest.mark.parametrize("case", ["coordinator", "coordinator_by_ieee"])
def test_coordinator_is_refused(results, case):
    res = results[case]
    assert res["status"].startswith("400")
    assert "coordinator" in res["data"]["BE_Error"]
    assert (res["sent"], res["gone"], res["unmapped"]) == ([], [], [])


@pytest.mark.parametrize("case", ["unknown_nwkid", "unknown_ieee"])
def test_unknown_device_changes_nothing(results, case):
    res = results[case]
    assert res["data"] == []
    assert (res["sent"], res["gone"], res["unmapped"]) == ([], [], [])


def test_stale_record_leaves_the_live_device_alone(results):
    res = results["stale_record"]
    assert res["status"] == "200 OK"
    assert res["gone"] == ["0001"]
    assert (res["sent"], res["unmapped"]) == ([], [])


def test_record_without_ieee_is_dropped_and_nothing_is_sent(results):
    res = results["no_ieee"]
    assert res["status"] == "200 OK"
    assert res["gone"] == ["3a7f"]
    assert (res["sent"], res["unmapped"]) == ([], [])


def test_ieee_missing_from_ieee2nwk_is_still_asked_to_leave(results):
    res = results["ieee_not_mapped"]
    assert res["status"] == "200 OK"
    assert res["sent"] == [["REMOVE-DEVICE", "a4c13800ab12cd34", len(DEVICES)]]
    assert res["gone"] == ["5b5b"]


def test_no_parameter_changes_nothing(results):
    res = results["no_parameter"]
    assert (res["sent"], res["gone"], res["unmapped"]) == ([], [], [])
