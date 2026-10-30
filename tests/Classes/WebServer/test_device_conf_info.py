#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.WebServer.device_conf_info.

GET /zdevice-raw/<nwkid> adds "DeviceConfInfo" for the WebUI device details: the
top-level keys of the model's configuration that start with "_" (_comment,
_description, _blakadder...). The rest of the configuration (Ep, ClusterToBind,
ConfigureReporting, Param...) stays out, and so do "_" keys nested in it.

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

DEVICE_CONF = {
    "TS011F-plug": {
        "_comment": "https://zigbee.blakadder.com/Tuya_TS011F_plug_1.html",
        "_description": "Smart plug with power monitoring",
        "_blakadder": "",
        "Ep": {"01": {"0006": "", "_comment": "nested, not documentation of the model"}},
        "Type": "Switch",
        "Param": {"PowerOnAfterOffOn": 255},
    },
    "NoNotes": {"Ep": {"01": {"0006": ""}}, "Type": "Switch"},
    "Broken": ["not", "a", "dict"],
}

CASES = {
    # name: (DeviceConf, model, expected)
    "underscore_keys_only": (DEVICE_CONF, "TS011F-plug", {
        "_comment": "https://zigbee.blakadder.com/Tuya_TS011F_plug_1.html",
        "_description": "Smart plug with power monitoring",
        "_blakadder": "",
    }),
    "model_without_notes": (DEVICE_CONF, "NoNotes", {}),
    "unknown_model": (DEVICE_CONF, "lumi.unknown", {}),
    "model_not_a_string": (DEVICE_CONF, {}, {}),
    "model_missing": (DEVICE_CONF, None, {}),
    "configuration_not_a_dict": (DEVICE_CONF, "Broken", {}),
    "no_device_conf": (None, "TS011F-plug", {}),
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
        from Classes.WebServer.WebServer import device_conf_info

        cases = json.loads(sys.argv[1])
        print(json.dumps({name: device_conf_info(conf, model) for name, (conf, model, _) in cases.items()}))
        """
    )
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(CASES)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("name", sorted(CASES))
def test_device_conf_info(results, name):
    assert results[name] == CASES[name][2]
