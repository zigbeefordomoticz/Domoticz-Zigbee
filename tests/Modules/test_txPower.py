#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/txPower.py - set_TxPower() on zigpy

TXpower_set defaults to 0, which on zigpy means "keep the radio's own TX
power". Changing it to 0 from the WebUI must not send 0 dBm to the radio;
any other value is still sent in dBm, clamped to +/-22.

Modules.txPower imports the real Modules.* package, which conflicts with the
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
    from Modules.txPower import set_TxPower

    out = {}
    for value in json.loads(sys.argv[1]):
        p = types.SimpleNamespace(zigbee_communication="zigpy", log=MagicMock(), ControllerLink=MagicMock())
        set_TxPower(p, value)
        out[json.dumps(value)] = [c.args[1] for c in p.ControllerLink.sendData.call_args_list]
    print(json.dumps(out))
    """
)


@pytest.fixture(scope="module")
def sent():
    values = [0, "0", None, "", 5, "-9", 30, -40]
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT, json.dumps(values)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    return {json.loads(k): v for k, v in json.loads(result.stdout.strip().splitlines()[-1]).items()}


@pytest.mark.parametrize("value", [0, "0", None, ""])
def test_zero_or_unset_sends_nothing(sent, value):
    assert sent[value] == []


@pytest.mark.parametrize("value, dbm", [(5, 5), ("-9", -9), (30, 22), (-40, -22)])
def test_other_values_are_sent_in_dbm(sent, value, dbm):
    assert sent[value] == [{"Param1": dbm}]
