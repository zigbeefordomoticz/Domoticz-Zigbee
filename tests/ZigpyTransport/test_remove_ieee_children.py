#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for App*.remove_ieee() (REMOVE-DEVICE: last widget of a device deleted).

zigpy's remove() defaults to remove_children=True: the Mgmt_Leave_req sent to a
router also asks its children to leave, although only the router is removed. The
children must stay, so the leave goes out without RemoveChildren.

Runs zigpy's own remove()/_remove_device()/ZDO.leave() on a fake device, in a
subprocess (see test_coordinator_backup.py); a radio whose library is missing
there is skipped.
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

RADIOS = [
    # (radio library, plugin module, application class)
    ("zigpy_znp", "AppZnp", "App_znp"),
    ("bellows", "AppBellows", "App_bellows"),
    ("zigpy_blz", "AppBlz", "App_blz"),
]

HARNESS = textwrap.dedent(
    """
    import asyncio, importlib, json, sys, types
    from unittest.mock import AsyncMock, MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    library, module, class_name = json.loads(sys.argv[1])
    try:
        importlib.import_module(library)
    except ImportError:
        print("RESULT=" + json.dumps({"missing": True}))
        sys.exit(0)

    import zigpy.application, zigpy.types as t, zigpy.zdo
    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    App = getattr(importlib.import_module("Classes.ZigpyTransport." + module), class_name)

    ieee = t.EUI64.convert("00:12:4b:00:04:25:ea:71")
    dev = MagicMock(ieee=ieee, nwk=0x8012)
    dev.node_desc.is_end_device = False
    dev.zdo = types.SimpleNamespace(
        _device=dev, LeaveOptions=zigpy.zdo.ZDO.LeaveOptions, Mgmt_Leave_req=AsyncMock())
    dev.zdo.leave = types.MethodType(zigpy.zdo.ZDO.leave, dev.zdo)

    async def main():
        tasks = []
        app = types.SimpleNamespace(devices={ieee: dev}, listener_event=MagicMock(), topology=MagicMock(),
                                    create_task=lambda coro, name=None: tasks.append(asyncio.create_task(coro)))
        for name in ("remove", "_remove_device"):
            setattr(app, name, types.MethodType(getattr(zigpy.application.ControllerApplication, name), app))
        await App.remove_ieee(app, ieee)
        await asyncio.gather(*tasks)
        return app

    app = asyncio.run(main())
    print("RESULT=" + json.dumps({
        "leaves": [[str(c.args[0]), int(c.args[1])] for c in dev.zdo.Mgmt_Leave_req.await_args_list],
        "left": len(app.devices),
    }))
    """
)


@pytest.mark.parametrize("radio", RADIOS, ids=[radio[0] for radio in RADIOS])
def test_router_leaves_without_its_children(radio):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(radio)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    line = next(ln for ln in result.stdout.splitlines() if ln.startswith("RESULT="))
    res = json.loads(line[len("RESULT="):])
    if res.get("missing"):
        pytest.skip("%s not installed" % radio[0])

    # LeaveOptions.NONE: neither RemoveChildren nor Rejoin
    assert res["leaves"] == [["00:12:4b:00:04:25:ea:71", 0]]
    assert res["left"] == 0
