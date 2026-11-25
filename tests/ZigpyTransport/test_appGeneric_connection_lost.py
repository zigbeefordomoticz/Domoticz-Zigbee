#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
connection_lost(): the Error says which recovery the plugin started.

Importing AppGeneric pulls in modules tests/conftest.py stubs for the rest of the session, so each
scenario runs in a subprocess, as in test_appGeneric_initialize.py.
"""

import importlib.util
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("zigpy") is None, reason="requires the real zigpy package"
)

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import json, logging, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.types as t
    import Classes.ZigpyTransport.AppGeneric as AG

    records = []

    class Handler(logging.Handler):
        def emit(self, record):
            records.append([record.levelname, record.getMessage()])

    AG.LOGGER.addHandler(Handler())
    AG.LOGGER.setLevel(logging.DEBUG)
    """
)


def run(body):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(body)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


SCENARIO = """
    import asyncio
    import serial

    app = types.SimpleNamespace(
        shutting_down=False, restarting=False, start_time=0, log=MagicMock(), callBackRestartPlugin=MagicMock()
    )
    if {supervisor}:
        app._supervisor_running = True
        app.zigpy_running_ref = MagicMock(zigpy_running=True)
    AG.connection_lost(app, {exc})
    print(json.dumps({{
        "errors": [m for level, m in records if level == "ERROR"],
        "restarting": app.restarting,
        "plugin_restarts": app.callBackRestartPlugin.call_count,
        "stack_stopped": {supervisor} and app.zigpy_running_ref.zigpy_running is False,
    }}))
"""

EXCEPTIONS = ['OSError(5, "x")', 'serial.serialutil.SerialException("x")', "asyncio.TimeoutError()"]


@pytest.mark.parametrize("exc", EXCEPTIONS)
def test_supervisor_restarts_the_stack(exc):
    out = run(SCENARIO.format(supervisor=True, exc=exc))

    assert len(out["errors"]) == 1
    assert out["errors"][0].startswith("Connection to coordinator lost, ")
    assert out["errors"][0].endswith(", restarting the Zigbee stack")
    assert out["restarting"] and out["stack_stopped"]
    assert out["plugin_restarts"] == 0


@pytest.mark.parametrize("exc", EXCEPTIONS)
def test_no_supervisor_restarts_the_plugin(exc):
    out = run(SCENARIO.format(supervisor=False, exc=exc))

    assert len(out["errors"]) == 1
    assert out["errors"][0].endswith(", restarting the plugin")
    assert out["plugin_restarts"] == 1


def test_ncp_failure_names_the_recovery():
    pytest.importorskip("bellows")
    out = run(
        "from bellows.ash import NcpFailure\nfrom bellows.types.named import NcpResetCode\n"
        + textwrap.dedent(SCENARIO.format(
            supervisor=True, exc="NcpFailure(code=NcpResetCode.ERROR_EXCEEDED_MAXIMUM_ACK_TIMEOUT_COUNT)"))
    )

    assert out["errors"] == ["NCP reset due to exceeded maximum ACK timeout count, restarting the Zigbee stack"]


UNEXPECTED = {
    "None": ("None", "port closed by the remote side"),
    "ControllerException": (
        '__import__("zigpy.exceptions").exceptions.ControllerException("watchdog")',
        "unexpected error ControllerException('watchdog')",
    ),
    "RuntimeError with a percent sign": ('RuntimeError("100%s")', "unexpected error RuntimeError('100%s')"),
}


@pytest.mark.parametrize("exc, text", UNEXPECTED.values(), ids=UNEXPECTED)
def test_unexpected_error_restarts_the_running_stack(exc, text):
    out = run(SCENARIO.format(supervisor=True, exc=exc))

    assert out["errors"] == [f"Connection to coordinator lost, {text}, restarting the Zigbee stack"]
    assert out["restarting"] and out["stack_stopped"]
    assert out["plugin_restarts"] == 0


@pytest.mark.parametrize("exc", [exc for exc, _ in UNEXPECTED.values()], ids=UNEXPECTED)
def test_unexpected_error_during_the_start_is_left_to_the_retries(exc):
    out = run(SCENARIO.format(supervisor=False, exc=exc))

    assert out["errors"] == []
    assert not out["restarting"]
    assert out["plugin_restarts"] == 0


@pytest.mark.parametrize("flag", ["shutting_down", "restarting"])
def test_port_closed_by_the_plugin_is_not_an_error(flag):
    out = run(SCENARIO.format(supervisor=True, exc="None").replace(f"{flag}=False", f"{flag}=True"))

    assert out["errors"] == []
    assert not out["stack_stopped"]
    assert out["plugin_restarts"] == 0


def test_other_ncp_failure_restarts_the_stack():
    pytest.importorskip("bellows")
    out = run(
        "from bellows.ash import NcpFailure\nfrom bellows.types.named import NcpResetCode\n"
        + textwrap.dedent(SCENARIO.format(supervisor=True, exc="NcpFailure(code=NcpResetCode.RESET_WATCHDOG)"))
    )

    assert len(out["errors"]) == 1
    assert "unexpected error <NcpFailure(" in out["errors"][0] and "RESET_WATCHDOG" in out["errors"][0]
    assert out["errors"][0].endswith(", restarting the Zigbee stack")
    assert out["stack_stopped"]
