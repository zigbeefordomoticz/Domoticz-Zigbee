#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for PUT /rest-z4d/1/change-model (WebServer.rest_change_model_name).

The handler rejected a body only when both NWKID and Model were missing: with one
of the two it went on and raised a KeyError, an empty Model erased the device's
model, and a list as NWKID raised a TypeError on the device lookup. It now needs
both keys, each a non-empty string, and leaves the device alone otherwise.

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

DEVICES = {"1234": {"Model": "lumi.sensor_switch"}}

CASES = {
    # name: request body
    "valid": {"NWKID": "1234", "Model": "lumi.sensor_switch.aq2"},
    "model_only": {"Model": "lumi.sensor_switch.aq2"},
    "nwkid_only": {"NWKID": "1234"},
    "empty_model": {"NWKID": "1234", "Model": ""},
    "blank_model": {"NWKID": "1234", "Model": "  "},
    "model_not_a_string": {"NWKID": "1234", "Model": 12},
    "nwkid_is_a_list": {"NWKID": ["1234"], "Model": "lumi.sensor_switch.aq2"},
    "body_is_a_list": ["1234", "lumi.sensor_switch.aq2"],
    "unknown_device": {"NWKID": "abcd", "Model": "lumi.sensor_switch.aq2"},
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
        from Classes.WebServer.WebServer import WebServer

        class PluginConf:
            pluginConf = {}

        class Plugin:
            def __init__(self, devices):
                self.pluginconf = PluginConf()
                self.ListOfDevices = devices
                self.log = MagicMock()
                self.errors = []
            def logging(self, level, message):
                if level == "Error":
                    self.errors.append(message)

        devices, cases = json.loads(sys.argv[1]), json.loads(sys.argv[2])
        out = {}
        for name, body in cases.items():
            plugin = Plugin(copy.deepcopy(devices))
            response = {}
            try:
                response = WebServer.rest_change_model_name(plugin, "PUT", json.dumps(body).encode("utf8"), [])
            except Exception as error:
                plugin.errors.append("raised %s: %s" % (type(error).__name__, error))
            out[name] = {
                "devices": plugin.ListOfDevices,
                "queued": sorted(getattr(plugin, "widget_creation_requests", {})),
                "errors": plugin.errors,
                "status": response.get("Status"),
            }
        print(json.dumps(out))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(DEVICES), json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_valid_request_changes_the_model_and_queues_the_widgets(results):
    case = results["valid"]
    assert case["errors"] == []
    assert case["devices"]["1234"]["Model"] == "lumi.sensor_switch.aq2"
    assert case["queued"] == ["1234"]


@pytest.mark.parametrize("name", ["model_only", "nwkid_only", "empty_model", "blank_model", "model_not_a_string", "nwkid_is_a_list"])
def test_incomplete_request_is_refused_and_changes_nothing(results, name):
    case = results[name]
    assert case["status"] == "200 OK", "the handler raised instead of answering: %s" % case["errors"]
    assert len(case["errors"]) == 1 and "NWKID and Model are both required" in case["errors"][0]
    assert case["devices"] == DEVICES
    assert case["queued"] == []


def test_body_that_is_not_an_object_changes_nothing(results):
    # Refused either here or, once request bodies are parsed as JSON objects, before it.
    case = results["body_is_a_list"]
    assert case["status"] == "200 OK", "the handler raised instead of answering: %s" % case["errors"]
    assert case["devices"] == DEVICES
    assert case["queued"] == []


def test_unknown_device_is_refused(results):
    case = results["unknown_device"]
    assert len(case["errors"]) == 1 and "Unknown device abcd" in case["errors"][0]
    assert case["devices"] == DEVICES
    assert case["queued"] == []
