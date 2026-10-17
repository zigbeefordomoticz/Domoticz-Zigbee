#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
A Domoticz command to a device the plugin has recorded as gone.

Such a device is no longer pre-loaded into zigpy's device table
(Modules/zigpy_preload.py), so a command reaching the transport fails there
with a bare "process_raw_command: unknown destination: None", which names
neither the widget nor the reason. Found on a real mesh: a Domoticz timer kept
switching 0xE079, a plug recorded as "Leave", every evening at 18:00.

domoticz_command() must drop the command itself and say why.

Modules.command imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import collections.abc, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.command as command

    class DeviceRecord(collections.abc.MutableMapping):
        # ListOfDevices entries are Mappings, not dicts (ThreadSafeDeviceDict)
        def __init__(self, data):
            self._data = dict(data)
        def __getitem__(self, key):
            return self._data[key]
        def __setitem__(self, key, value):
            self._data[key] = value
        def __delitem__(self, key):
            del self._data[key]
        def __iter__(self):
            return iter(self._data)
        def __len__(self):
            return len(self._data)

    class Log:
        def __init__(self):
            self.lines = []
        def logging(self, module, level, message, *args, **kwargs):
            self.lines.append((level, message))

    def run_command(status, command_name="On"):
        plugin = types.SimpleNamespace(
            ListOfDevices={"e079": DeviceRecord({"Status": status, "IEEE": "540f57fffe2b231a", "Health": "Live"})},
            pluginconf=types.SimpleNamespace(pluginConf={}),
            log=Log(),
        )
        command.domo_read_Name = lambda *a: "Salon Plug"
        command.RetreiveSignalLvlBattery = lambda *a: (100, 100)
        command.retrieve_widget_type_list = lambda *a: [("01", "1", "Plug")]
        sent = MagicMock(name="handle_command_on")
        command.handle_command_on = sent
        command.handle_command_off = sent
        command.domoticz_command(plugin, {}, "540f57fffe2b231a", 1, "e079", command_name, 0, "")
        return plugin, sent
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


@pytest.mark.parametrize("status", ["Leave", "Removed"])
@pytest.mark.parametrize("command_name", ["On", "Off"])
def test_a_command_to_a_departed_device_is_dropped(status, command_name):
    _run(
        f"""
        plugin, sent = run_command({status!r}, {command_name!r})
        assert not sent.called, "the command reached the transport"
        """
    )


def test_the_drop_is_logged_once_naming_the_widget_and_the_reason():
    _run(
        """
        plugin, sent = run_command("Leave")
        errors = [message for level, message in plugin.log.lines if level == "Error"]
        assert len(errors) == 1, errors
        assert "Salon Plug/e079" in errors[0], errors
        assert "left the network" in errors[0], errors
        assert "Status Leave" in errors[0], errors
        """
    )


@pytest.mark.parametrize("status", ["inDB", "UNKNOW", ""])
def test_a_command_to_a_device_still_present_goes_through(status):
    _run(
        f"""
        plugin, sent = run_command({status!r})
        assert sent.called, "the command was dropped"
        assert not [m for level, m in plugin.log.lines if level == "Error"], plugin.log.lines
        """
    )
