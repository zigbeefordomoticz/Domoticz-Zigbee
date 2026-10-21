#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AppGeneric.permit_gp(), the 'GreenPowerEnable' gate on Green
Power commissioning.

Driven against a fake app whose base class records permit_gp() calls, so
that `super(type(self), self).permit_gp()` resolves to it as it resolves to
zigpy's ControllerApplication.permit_gp() with the real radio libraries. The
fake base also stands in for zigpy releases without Green Power support
(no `green_power` attribute), so these tests do not depend on the installed
zigpy version.

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
            if "enabled" in sc:
                self.pluginconf.pluginConf["GreenPowerEnable"] = sc["enabled"]
            if sc.get("green_power", True):
                self.green_power = types.SimpleNamespace(is_commissioning=sc.get("commissioning", False))

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


def _status(result):
    return [msg for level, msg in result["logs"] if level == "Status"]


class TestGreenPowerDisabled:

    def test_setting_absent_does_not_open(self):
        result = _run(time_s=60)
        assert result["calls"] == []
        assert _status(result) == []

    def test_setting_off_does_not_open(self):
        result = _run(time_s=60, enabled=0)
        assert result["calls"] == []

    def test_close_without_open_window_is_silent(self):
        # The startup permit(0) must not broadcast to proxies
        result = _run(time_s=0, enabled=0, commissioning=False)
        assert result["calls"] == []

    def test_close_of_open_window_is_passed_on(self):
        # Setting switched off while a window was open
        result = _run(time_s=0, enabled=0, commissioning=True)
        assert result["calls"] == [0]


class TestGreenPowerEnabled:

    def test_open_is_passed_on(self):
        result = _run(time_s=60, enabled=1)
        assert result["calls"] == [60]
        assert any("opening Green Power commissioning for 60" in msg for msg in _status(result))

    def test_close_is_passed_on(self):
        result = _run(time_s=0, enabled=1)
        assert result["calls"] == [0]
        assert any("closing Green Power commissioning" in msg for msg in _status(result))


class TestZigpyWithoutGreenPower:

    def test_nothing_called(self):
        result = _run(time_s=60, enabled=1, green_power=False)
        assert result["calls"] == []
