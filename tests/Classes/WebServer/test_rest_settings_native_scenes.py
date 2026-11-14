#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
enableNativeScenes through the real rest_Settings, as the WebUI reads and saves it.

The Scenes section of the Groups page only shows once this setting is on, so it has
to be where a user finds it: in Available services next to Enable Groups, off the
Advanced list, and flagged as needing a restart. It first shipped as an Advanced
setting of the GroupManagement theme, which left no visible way to reach scenes.

The WebUI's check is on the Name and current_value of the /setting answer
(group-scenes.component.ts), so these two are part of the contract tested here.

plugin.py imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so this runs in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SCRIPT = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status", "Device"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    domoticz.Parameters = {}
    domoticz.Devices = {}
    sys.modules["DomoticzEx"] = domoticz

    import plugin  # noqa: F401  (loads the modules in the order they need)
    from Classes.PluginConf import SETTINGS
    from Classes.WebServer.WebServer import WebServer

    server = MagicMock()
    server.pluginconf.pluginConf = {
        param: definition["default"]
        for theme in SETTINGS.values()
        for param, definition in theme["param"].items()
    }
    server.zigbee_communication = "zigpy"
    server.restart_needed = {"RestartNeeded": 0}

    def read():
        response = WebServer.rest_Settings(server, "GET", None, [])
        themes = json.loads(response["Data"])
        found = [
            (theme["_Theme"], setting)
            for theme in themes
            for setting in theme["ListOfSettings"]
            if setting["Name"] == "enableNativeScenes"
        ]
        assert len(found) == 1, found
        return found[0]
    """
)


def _run(snippet):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_it_is_next_to_enable_groups_and_not_advanced():
    _run(
        """
        theme, setting = read()
        assert theme == "Services", theme
        assert setting["Advanced"] is False, setting
        assert setting["DataType"] == "bool", setting
        """
    )


def test_it_needs_a_restart_like_enable_groups():
    _run(
        """
        _, setting = read()
        assert setting["restart_need"] == 1, setting
        assert SETTINGS["Services"]["param"]["enablegroupmanagement"]["restart"] == 1
        """
    )


def test_it_is_off_by_default():
    _run(
        """
        _, setting = read()
        assert not setting["current_value"], setting
        assert setting["default_value"] == 0, setting
        """
    )


def test_saving_it_turns_it_on_and_asks_for_a_restart():
    _run(
        """
        body = json.dumps({"enableNativeScenes": {"current": True}}).encode()
        WebServer.rest_Settings(server, "PUT", body, [])
        assert server.restart_needed["RestartNeeded"] == 1, server.restart_needed
        _, setting = read()
        assert setting["current_value"], setting
        assert str(setting["current_value"]) not in ("0", "false"), setting
        """
    )
