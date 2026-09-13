#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.WebServer.decode_device_param.

The Device Management page is given each device's Param as str(dict) — a Python
literal with single quotes and True/False/None — and sends it back unchanged
for every device on save. decode_device_param only tolerated the quotes, so the
first Param holding a boolean (Sonoff SWV-ZFE "SONOFF_SWV_IRRIGATION_PLAN":
{"enable": false}) made the whole save fail with "Expecting value ... Make sure
to use JSON syntax". It now accepts JSON and Python literals alike.

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

PLAN = {"plan_index": 0, "enable": False, "loop_type_week_days": ["monday", "friday"], "start_time": "06:30", "fail_safe": None}
PARAM = {"Disabled": 0, "SONOFF_SWV_MANUAL_IRRIGATION_MODE": "duration_with_interval", "SONOFF_SWV_IRRIGATION_PLAN": PLAN}

CASES = {
    # name: (page input, expected dict or None for "rejected")
    "json": (json.dumps(PARAM), PARAM),
    "python_repr_from_str_dict": (str(PARAM), PARAM),
    "python_repr_trailing_comma": ("{'Disabled': 0, 'PowerOnAfterOffOn': 255, }", {"Disabled": 0, "PowerOnAfterOffOn": 255}),
    "single_quoted_json_values": ("{'Disabled': 0, 'enable': false, 'x': null}", {"Disabled": 0, "enable": False, "x": None}),
    "already_a_dict": (PARAM, PARAM),
    "empty": ("", {}),
    "garbage": ("{'Disabled': 0, 'enable': Fals}", None),
    "not_a_dict": ("[1, 2, 3]", None),
    "expression_is_not_evaluated": ("{'x': __import__('os').getcwd()}", None),
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
        from Classes.WebServer.WebServer import decode_device_param

        class Plugin:
            def __init__(self):
                self.errors = []
                self.ListOfDevices = {"1234": {"ZDeviceName": "valve", "IEEE": "00"}}
            def logging(self, level, message):
                if level == "Error":
                    self.errors.append(message)

        out = {}
        for name, param in json.loads(sys.argv[1]).items():
            plugin = Plugin()
            out[name] = {"value": decode_device_param(plugin, "1234", param), "errors": plugin.errors}
        print(json.dumps(out))
        """
    )
    inputs = {name: case[0] for name, case in CASES.items()}
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(inputs)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", list(CASES))
def test_decode_device_param(results, name):
    _, expected = CASES[name]
    got = results[name]

    if expected is None:
        assert got["value"] == {}
        assert len(got["errors"]) == 1 and "wrong Parameter syntax" in got["errors"][0]
    else:
        assert got["value"] == expected
        assert got["errors"] == []
