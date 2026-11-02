#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AppGeneric.permit_gp(), which keeps Green Power commissioning
closed until the plugin hands Green Power devices to zigpy.

Driven against a fake app whose base class records permit_gp() calls, so
a call reaching zigpy's ControllerApplication.permit_gp() would show up.
These tests do not depend on the installed zigpy version.

Importing AppGeneric pulls in Classes.ZigpyTransport.Transport and
Classes.ZigateTransport.sqnMgmt, which tests/conftest.py stubs for the rest
of the session. Each scenario therefore runs in a subprocess, as in
test_appGeneric_initialize.py.
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

HARNESS = textwrap.dedent(
    """
    import asyncio, json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import Classes.ZigpyTransport.AppGeneric as AG

    sc = json.loads(sys.argv[1])

    class Log:
        def __init__(self):
            self.records = []
        def logging(self, category, level, message, *args, **kwargs):
            self.records.append([level, str(message)])

    class RadioControllerApplication:
        # Stands in for zigpy.application.ControllerApplication.permit_gp()
        async def permit_gp(self, time_s):
            self.calls.append(time_s)

    class FakeApp(RadioControllerApplication):
        def __init__(self):
            self.calls = []
            self.log = Log()
            self.pluginconf = types.SimpleNamespace(pluginConf={})
            self.green_power = types.SimpleNamespace(is_commissioning=False)

    app = FakeApp()
    asyncio.run(AG.permit_gp(app, sc["time_s"]))
    print("RESULT=" + json.dumps({"calls": app.calls, "logs": app.log.records}))
    """
)


def _run(**scenario):
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(scenario)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT="))
    return json.loads(line[len("RESULT="):])


class TestGreenPowerCommissioningStaysClosed:

    def test_permit_join_does_not_open(self):
        result = _run(time_s=60)
        assert result["calls"] == []

    def test_startup_close_sends_nothing(self):
        # The startup permit(0) must not broadcast to proxies
        result = _run(time_s=0)
        assert result["calls"] == []

    def test_skip_is_logged_at_debug_only(self):
        result = _run(time_s=60)
        assert [level for level, _ in result["logs"]] == ["Debug"]
