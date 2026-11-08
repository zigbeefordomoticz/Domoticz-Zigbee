#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coverage for Modules.domoTools.lastSeenUpdate, the path that refreshes a device's
"Last Seen" in Domoticz when a frame is received.

- A device whose TimedOut flag is set gets the flag cleared AND its widgets touched.
  Domoticz keeps TimedOut in memory only, so clearing it does not refresh LastUpdate,
  and Stamp.LastSeen holds the next touch back for DELAY_BETWEEN_TOUCH: without the
  touch, a quiet device (Aqara, ~50 min heartbeat) kept a stale Last Seen.
- A frame within DELAY_BETWEEN_TOUCH of the previous touch does not touch.
- The WidgetTouch debug category exists in PluginConf, off by default.

Modules.domoTools imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so the checks run in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, time, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    from Modules.domoTools import lastSeenUpdate

    class Unit:
        Type, SubType, SwitchType = 244, 73, 7
        def __init__(self):
            self.LastUpdate = "2000-01-01 00:00:00"
            self.touched = 0
        def Touch(self):
            self.touched += 1

    class Device:
        def __init__(self):
            self.TimedOut = 0
            self.Units = {1: Unit()}

    def make_plugin(stamp_last_seen=0):
        plugin = MagicMock()
        plugin.VersionNewFashion = True
        plugin.DomoticzMajor = 2025
        plugin.pluginconf.pluginConf = {"deviceOffWhenTimeOut": False}
        plugin.IEEE2NWK = {"00158d00023e7918": "1f55"}
        plugin.ListOfDevices = {
            "1f55": {"IEEE": "00158d00023e7918", "Health": "TimedOut",
                     "Stamp": {"LastSeen": stamp_last_seen}},
        }
        return plugin
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


def test_timed_out_device_is_cleared_and_touched():
    out = _run(
        """
        plugin = make_plugin()
        devices = {"00158d00023e7918": Device()}
        devices["00158d00023e7918"].TimedOut = 1
        lastSeenUpdate(plugin, devices, NwkId="1f55")
        print(devices["00158d00023e7918"].TimedOut, devices["00158d00023e7918"].Units[1].touched)
        """
    )
    assert out == "0 1"


def test_live_device_is_touched():
    out = _run(
        """
        plugin = make_plugin()
        devices = {"00158d00023e7918": Device()}
        lastSeenUpdate(plugin, devices, NwkId="1f55")
        print(devices["00158d00023e7918"].Units[1].touched)
        """
    )
    assert out == "1"


def test_frame_within_delay_is_not_touched():
    out = _run(
        """
        plugin = make_plugin(stamp_last_seen=int(time.time()) - 10)
        devices = {"00158d00023e7918": Device()}
        lastSeenUpdate(plugin, devices, NwkId="1f55")
        print(devices["00158d00023e7918"].Units[1].touched)
        """
    )
    assert out == "0"


def test_lastseen_logs_go_to_widgettouch_category():
    out = _run(
        """
        plugin = make_plugin()
        devices = {"00158d00023e7918": Device()}
        lastSeenUpdate(plugin, devices, NwkId="1f55")
        calls = [c for c in plugin.log.logging.call_args_list if "lastSeenUpdate" in c.args[2]]
        print(all(c.args[0] == ["WidgetLevel3", "WidgetTouch"] and c.args[3] == "1f55" for c in calls), len(calls))
        """
    )
    assert out == "True 1"


def test_widgettouch_debug_setting_exists_off_by_default():
    out = _run(
        """
        from Classes.PluginConf import SETTINGS
        entry = SETTINGS["VerboseLogging"]["param"]["WidgetTouch"]
        print(entry["type"], entry["default"], entry["Advanced"])
        """
    )
    assert out == "bool 0 True"
