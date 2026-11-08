#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/database.py - switch_off_one_shot_resets()

resetReadAttributes and resetConfigureReporting were switched off once the
device list had loaded, but resetOTAUpdate stayed on and dropped the OTA state
of every device at every start until the user switched it off by hand. The
three resets now run at one start only.

Modules.database imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    from Modules.database import ONE_SHOT_RESETS, switch_off_one_shot_resets

    def run(conf):
        writes = []
        logs = []
        p = types.SimpleNamespace()
        p.log = types.SimpleNamespace(logging=lambda *a, **k: logs.append(a))
        p.pluginconf = types.SimpleNamespace(pluginConf=dict(conf), write_Settings=lambda: writes.append(1))
        switch_off_one_shot_resets(p)
        return {"conf": p.pluginconf.pluginConf, "writes": len(writes), "logs": len(logs)}

    cases = json.loads(sys.argv[1])
    out = {name: run(conf) for name, conf in cases.items()}
    out["_names"] = list(ONE_SHOT_RESETS)
    print(json.dumps(out))
    """
)


def _run(cases):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT, json.dumps(cases)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


OFF = {"resetReadAttributes": False, "resetConfigureReporting": False, "resetOTAUpdate": False}

CASES = {
    "all_off": dict(OFF),
    "ota_only": dict(OFF, resetOTAUpdate=True),
    "all_on": {"resetReadAttributes": True, "resetConfigureReporting": True, "resetOTAUpdate": 1},
    "missing_keys": {},
}


@pytest.fixture(scope="module")
def results():
    return _run(CASES)


def test_the_three_resets_are_one_shot(results):
    assert results["_names"] == ["resetReadAttributes", "resetConfigureReporting", "resetOTAUpdate"]


def test_nothing_on_nothing_written(results):
    assert results["all_off"] == {"conf": OFF, "writes": 0, "logs": 0}


def test_reset_ota_update_switches_off(results):
    assert results["ota_only"]["conf"] == OFF
    assert results["ota_only"]["writes"] == 1


def test_all_switch_off_with_a_single_write(results):
    assert results["all_on"]["conf"] == OFF
    assert results["all_on"]["writes"] == 1
    assert results["all_on"]["logs"] == 1


def test_missing_settings_are_ignored(results):
    assert results["missing_keys"] == {"conf": {}, "writes": 0, "logs": 0}
