#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the "Value" of PUT /rest-z4d/1/dev-command (issue #2213).

rest_dev_command used to convert Value with str() and then read it as
hexadecimal whenever the text held hex digits only. Every decimal number
qualifies, so a level of 60 sent as a JSON number was applied as 0x60 = 96,
and a setpoint of 20 as 32.

A JSON number is now taken as is. A hex string is still read as hexadecimal,
which is what the Web UI sends ("3c" for 60), so the UI keeps working.

Classes.WebServer.WebServer imports the real Modules.* package, which
conflicts with the stubs tests/conftest.py installs for the session, so the
calls run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    import Classes.WebServer.WebServer as W

    cases = json.loads(sys.argv[1])
    out = {"levels": {}, "handler": {}}

    for name, value in cases["levels"].items():
        try:
            out["levels"][name] = W.dev_command_level(value)
        except Exception as exc:
            out["levels"][name] = "raised %s" % type(exc).__name__

    class PluginConf:
        pluginConf = {}

    class Plugin:
        def __init__(self):
            self.pluginconf = PluginConf()
            self.ListOfDevices = {"1234": {"Ep": {"01": {"0006": {}, "0008": {}}, "02": {"0201": {}}}}}
        def logging(self, *args, **kwargs):
            pass

    for name, body in cases["handler"].items():
        W.actuators = MagicMock(name="actuators")
        W.WebServer.rest_dev_command(Plugin(), "PUT", json.dumps(body).encode("utf8"), [])
        call = W.actuators.call_args
        out["handler"][name] = {"args": list(call.args[1:]), "value": call.kwargs.get("value")}

    print(json.dumps(out))
    """
)

# name -> (Value as sent in the JSON body, Level expected)
LEVELS = {
    "json_int": (60, 60),
    "json_int_99": (99, 99),
    "json_int_10": (10, 10),
    "json_zero": (0, 0),
    "json_float": (20.5, 20),
    "hex_string_ui": ("3c", 60),
    "hex_string_upper": ("3C", 60),
    "digits_string_is_hex": ("60", 96),
    "signed_string": ("-5", -5),
    "empty_string": ("", 0),
    "null": (None, 0),
}

HANDLER = {
    "setlevel_number": {"NwkId": "1234", "Command": "SetLevel", "Value": 60, "Color": "", "Type": "LvlControl"},
    "setlevel_hex_string": {"NwkId": "1234", "Command": "SetLevel", "Value": "3c", "Color": "", "Type": "LvlControl"},
    "setpoint_number": {"NwkId": "1234", "Command": "SetLevel", "Value": 20, "Color": "", "Type": "ThermoSetpoint"},
}
HANDLER_EXPECTED = {
    "setlevel_number": ("01", "LvlControl", 60),
    "setlevel_hex_string": ("01", "LvlControl", 60),
    "setpoint_number": ("02", "ThermoSetpoint", 20),
}


@pytest.fixture(scope="module")
def results():
    cases = {"levels": {name: sent for name, (sent, _) in LEVELS.items()}, "handler": HANDLER}
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(cases)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", list(LEVELS))
def test_dev_command_level(results, name):
    assert results["levels"][name] == LEVELS[name][1]


@pytest.mark.parametrize("name", list(HANDLER))
def test_handler_passes_decimal_level_to_actuators(results, name):
    epout, device_type, level = HANDLER_EXPECTED[name]
    got = results["handler"][name]
    # actuators(self, Command, NwkId, epout, Type, value=Level, color=Color), self left out
    assert got["args"] == ["SetLevel", "1234", epout, device_type]
    assert got["value"] == level
