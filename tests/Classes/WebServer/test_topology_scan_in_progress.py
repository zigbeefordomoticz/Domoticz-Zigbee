#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.WebServer.topology_scan_in_progress, which is
what puts "Topology": "In Progress" into /plugin-health and so into the WebUI
footer.

/plugin-health used to read the NetworkMap phase alone. That phase only moves
on a native scan: on a zigpy setup rest_req_topologie() sends
ZIGPY-TOPOLOGY-SCAN and never calls networkmap.start_scan(), so the footer said
nothing for the whole length of a scan on the backend most installs now run.

Classes.WebServer.WebServer imports the real Modules.* package, which conflicts
with the stubs tests/conftest.py installs for the session, so the calls run in
a subprocess — as tests/Classes/WebServer/test_decode_device_param.py does.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# name: (zigbee_communication, NetworkMapPhase, zigpy topology description)
#
# The zigpy description is None for "no object at all", or a dict of
# {app, scanning} where app False means the transport is not up yet.
CASES = {
    "native_idle": ("native", 0, None),
    "native_scanning": ("native", 2, None),
    "zigpy_idle": ("zigpy", 0, {"app": True, "scanning": False}),
    "zigpy_scanning": ("zigpy", 0, {"app": True, "scanning": True}),
    # The phase is authoritative when it moves, whoever moved it.
    "zigpy_networkmap_scanning": ("zigpy", 2, {"app": True, "scanning": False}),
    # Before the transport is up there is nothing to ask, and asking raises.
    "zigpy_no_controller_app": ("zigpy", 0, {"app": False, "scanning": True}),
    # Early in the start-up the object itself does not exist yet.
    "zigpy_no_topology_object": ("zigpy", 0, None),
    # A native install must never reach the zigpy state even if it has one.
    "native_with_a_zigpy_object": ("native", 0, {"app": True, "scanning": True}),
}

EXPECTED = {
    "native_idle": False,
    "native_scanning": True,
    "zigpy_idle": False,
    "zigpy_scanning": True,
    "zigpy_networkmap_scanning": True,
    "zigpy_no_controller_app": False,
    "zigpy_no_topology_object": False,
    "native_with_a_zigpy_object": False,
}


@pytest.fixture(scope="module")
def results():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            sys.modules[name] = mod
        from Classes.WebServer.WebServer import topology_scan_in_progress

        class NetworkMap:
            def __init__(self, phase):
                self._phase = phase
            def NetworkMapPhase(self):
                return self._phase

        class ControllerLink:
            def __init__(self, app):
                self.app = app

        class ZigpyTopology:
            def __init__(self, app, scanning):
                self.ControllerLink = ControllerLink(object() if app else None)
                self._scanning = scanning
            def is_zigpy_topology_in_progress(self):
                if self.ControllerLink.app is None:
                    # What the real one does: it dereferences the application.
                    raise AttributeError("'NoneType' object has no attribute 'is_zigpy_topology_in_progress'")
                return self._scanning

        class Plugin:
            def __init__(self, communication, phase, topology):
                self.zigbee_communication = communication
                self.networkmap = NetworkMap(phase)
                self.zigpy_topology = (
                    ZigpyTopology(topology["app"], topology["scanning"]) if topology else None
                )

        out = {}
        for name, case in json.loads(sys.argv[1]).items():
            communication, phase, topology = case
            out[name] = topology_scan_in_progress(Plugin(communication, phase, topology))
        print(json.dumps(out))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", list(CASES))
def test_topology_scan_in_progress(results, name):
    assert results[name] is EXPECTED[name], (
        "%s: expected %s, got %s" % (name, EXPECTED[name], results[name])
    )
