#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for AppBellows.App_bellows.set_zigpy_tx_power() - the TX power change sent
from the WebUI (SET-TX-POWER) on an EZSP coordinator.

The value is applied in dBm through zigpy's set_tx_power(), as bellows does at
start; the EZSP power mode (CONFIG_TX_POWER_MODE) is no longer touched.

Classes.ZigpyTransport.AppBellows imports the real Modules.* package, which
conflicts with the stubs tests/conftest.py installs for the rest of the session.
The checks are therefore executed in a subprocess, fully isolated from the
pytest session. The real bellows package is required.
"""

import importlib.util
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("bellows") is None, reason="requires the real bellows package"
)

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = textwrap.dedent(
    """
    import asyncio, json, sys, types
    from unittest.mock import AsyncMock, MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    from Classes.ZigpyTransport.AppBellows import App_bellows

    out = {}
    for power in json.loads(sys.argv[1]):
        app = types.SimpleNamespace(log=MagicMock(), set_tx_power=AsyncMock(), _ezsp=MagicMock())
        app._ezsp.setConfigurationValue = AsyncMock()
        asyncio.run(App_bellows.set_zigpy_tx_power(app, power))
        out[str(power)] = {
            "set_tx_power": [list(c.args) for c in app.set_tx_power.await_args_list],
            "setConfigurationValue": app._ezsp.setConfigurationValue.await_count,
        }
    print("RESULT=" + json.dumps(out))
    """
)


@pytest.fixture(scope="module")
def applied():
    powers = [5, -9, 0]
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT, json.dumps(powers)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    line = next(ln for ln in result.stdout.splitlines() if ln.startswith("RESULT="))
    return json.loads(line[len("RESULT="):])


@pytest.mark.parametrize("power", [5, -9, 0])
def test_tx_power_is_applied_in_dbm(applied, power):
    assert applied[str(power)]["set_tx_power"] == [[power]]


@pytest.mark.parametrize("power", [5, -9, 0])
def test_tx_power_mode_is_not_touched(applied, power):
    assert applied[str(power)]["setConfigurationValue"] == 0
