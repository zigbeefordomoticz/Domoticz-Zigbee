#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for what the REST API says of Group Management before it exists.

The web server is up long before the plugin starts Group Management, and it used to take
no GroupsManagement object for a Group Management turned off: a Dashboard open during a
start logged "Looks like Group Management is not enabled" as an error, with the setting on,
and the WebUI said to turn it on.

Classes.WebServer.rest_Groups and WebServer import the real Modules.* package, which
conflicts with the stubs tests/conftest.py installs for the session, so the calls run in a
subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# name -> (a GroupsManagement status or None, enablegroupmanagement, RestartNeeded)
CASES = {
    "starting": (None, 1, 0),
    "off": (None, 0, 0),
    "turned_on_and_waiting_for_the_restart": (None, 1, 1),
    "off_with_another_setting_waiting_for_a_restart": (None, 0, 1),
    "ready": ("ready", 1, 0),
    "scanning": ("scan", 1, 0),
    "turned_off_and_waiting_for_the_restart": ("ready", 0, 1),
}

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    import Classes.WebServer.rest_Groups as rest
    import Classes.WebServer.WebServer as web
    WebServer = web.WebServer

    rest.domoticz_error_api = MagicMock()
    web.a_topology_scan_is_running = lambda server: False
    results = {}
    for name, (status, enabled, restart) in json.loads(sys.argv[1]).items():
        server = WebServer.__new__(WebServer)
        server.groupmgt = types.SimpleNamespace(GroupStatus=status, ListOfGroups={}) if status else None
        server.pluginconf = types.SimpleNamespace(pluginConf={"enablegroupmanagement": enabled})
        server.restart_needed = {"RestartNeeded": restart}
        server.PluginHealth = {"Flag": 1, "Txt": "Ready"}
        server.log = MagicMock()
        server.logging = MagicMock()
        rest.domoticz_error_api.reset_mock()

        health = json.loads(server.rest_plugin_health("GET", None, [])["Data"])
        server.rest_zGroup("GET", None, [])
        results[name] = {
            "status": health.get("GroupStatus"),
            "log": [c.args for c in server.logging.call_args_list if c.args[0] != "Debug"],
            "error": [c.args[0] for c in rest.domoticz_error_api.call_args_list],
        }
    print(json.dumps(results))
    """
)

NOT_READY = ["Log", "Group Management is not yet ready: the plugin is still starting"]
NOT_ENABLED = "Group Management is not enabled"


@pytest.fixture(scope="module")
def results():
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_a_start_is_not_a_group_management_turned_off(results):
    assert results["starting"]["status"] == "Starting"


def test_a_start_says_not_ready_and_is_no_error(results):
    assert results["starting"]["log"] == [NOT_READY]
    assert results["starting"]["error"] == []


def test_the_setting_off_leaves_the_status_out(results):
    assert results["off"]["status"] is None


def test_the_setting_off_says_not_enabled(results):
    assert results["off"]["error"] == [NOT_ENABLED]
    assert results["off"]["log"] == []


def test_the_setting_turned_on_only_counts_after_the_restart(results):
    """Or it would be starting for ever: nothing starts it until the plugin restarts."""
    assert results["turned_on_and_waiting_for_the_restart"]["status"] is None
    assert results["turned_on_and_waiting_for_the_restart"]["error"] == [NOT_ENABLED]


def test_another_setting_waiting_for_a_restart_changes_nothing(results):
    assert results["off_with_another_setting_waiting_for_a_restart"]["status"] is None


@pytest.mark.parametrize("name, status", [
    ("ready", "ready"), ("scanning", "scan"), ("turned_off_and_waiting_for_the_restart", "ready"),
])
def test_once_it_exists_group_management_gives_its_own_status(results, name, status):
    assert results[name]["status"] == status
    assert results[name]["error"] == []
    assert results[name]["log"] == []
