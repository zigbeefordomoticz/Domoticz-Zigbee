#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Green Power group on ZNP (Classes/ZigpyTransport/AppZnp.py):
register_green_power_group(), znp_add_endpoint_to_group() and
App_znp._subscribe_to_multicast_group().

On ZNP the coordinator's Green Power endpoint (0xF2) must be in the Green
Power group (0x0B84) to receive the Green Power notifications. zigpy-znp has
no implementation of zigpy's subscribe hook, so the plugin adds it with
ZDO.ExtFindGroup / ZDO.ExtAddGroup, as zigbee-herdsman does.

Importing AppZnp pulls in modules that tests/conftest.py stubs for the rest of
the session: each scenario runs in a subprocess, isolated from the pytest
session (as tests/ZigpyTransport/test_coordinator_backup.py does).
"""

import importlib.util
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("zigpy_znp") is None, reason="requires the real zigpy-znp package"
)

REPO_ROOT = Path(__file__).resolve().parents[2]

HARNESS = textwrap.dedent(
    """
    import asyncio, json, sys, types
    from unittest.mock import AsyncMock, MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy_znp.commands as c
    import Classes.ZigpyTransport.AppZnp as app_znp

    sc = json.loads(sys.argv[1])
    requests = []

    async def request(req, **kwargs):
        requests.append({
            "command": type(req).__qualname__,
            "Endpoint": int(req.Endpoint),
            "GroupId": int(req.GroupId),
            "kwargs": sorted(kwargs),
        })
        if sc.get("raise"):
            raise RuntimeError("radio timeout")
        if isinstance(req, c.ZDO.ExtFindGroup.Req):
            return types.SimpleNamespace(Group=bytes.fromhex(sc["find_answer"]))
        return types.SimpleNamespace(Status=0)

    log = MagicMock()
    app = types.SimpleNamespace(
        _znp=types.SimpleNamespace(request=AsyncMock(side_effect=request)),
        log=log,
    )
    if sc.get("green_power", True):
        app.green_power = object()

    if sc["call"] == "register":
        asyncio.run(app_znp.register_green_power_group(app))
    else:
        asyncio.run(app_znp.App_znp._subscribe_to_multicast_group(app, 0x1234, 0x01))

    print("RESULT=" + json.dumps({
        "requests": requests,
        "errors": [call.args[4] for call in log.logging.call_args_list if call.args[1] == "Error"],
    }))
    """
)

# ZDO.ExtFindGroup answer: status, group id, name length (and name)
IN_GROUP = "00840b00"
NOT_IN_GROUP = "01"


def _run(**scenario):
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(scenario)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT="))
    return json.loads(line[len("RESULT="):])


class TestRegisterGreenPowerGroup:

    def test_adds_gp_endpoint_to_gp_group_when_missing(self):
        result = _run(call="register", find_answer=NOT_IN_GROUP)
        assert result["requests"] == [
            {"command": "ZDO.ExtFindGroup.Req", "Endpoint": 0xF2, "GroupId": 0x0B84, "kwargs": []},
            {"command": "ZDO.ExtAddGroup.Req", "Endpoint": 0xF2, "GroupId": 0x0B84, "kwargs": ["RspStatus"]},
        ]
        assert result["errors"] == []

    def test_nothing_added_when_already_in_group(self):
        result = _run(call="register", find_answer=IN_GROUP)
        assert [r["command"] for r in result["requests"]] == ["ZDO.ExtFindGroup.Req"]
        assert result["errors"] == []

    def test_nothing_sent_with_a_zigpy_without_green_power(self):
        result = _run(call="register", find_answer=NOT_IN_GROUP, green_power=False)
        assert result["requests"] == []

    def test_radio_error_is_logged_not_raised(self):
        result = _run(call="register", find_answer=NOT_IN_GROUP, **{"raise": True})
        assert len(result["requests"]) == 1
        assert result["errors"] == [{"Error code": "ZNPGRP-ADD-01", "Endpoint": "0xf2", "Group": "0x0b84"}]


class TestSubscribeToMulticastGroup:

    def test_zigpy_subscription_reaches_the_radio(self):
        result = _run(call="subscribe", find_answer=NOT_IN_GROUP)
        assert [(r["command"], r["Endpoint"], r["GroupId"]) for r in result["requests"]] == [
            ("ZDO.ExtFindGroup.Req", 0x01, 0x1234),
            ("ZDO.ExtAddGroup.Req", 0x01, 0x1234),
        ]
