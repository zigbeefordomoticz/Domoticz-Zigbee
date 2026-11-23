#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for App*.remove_ieee(), the removal of a device from the network
(zigate_remove_device / remove_green_power_device -> REMOVE-DEVICE -> workerLoop).

Every radio must hand the removal over to zigpy's ControllerApplication.remove(),
which sends the ZDO Leave and drops the device, or unpairs a Green Power device.
On deCONZ it did nothing.

REMOVE-DEVICE is dispatched by the real workerLoop, with the parameter the plugin
sends, down to the real zigpy remove(); only the device and the Green Power manager
are mocked.

Importing the radio App modules pulls in Classes.ZigpyTransport.Transport and
Classes.ZigateTransport.sqnMgmt, which tests/conftest.py stubs for the rest of
the session, together with any radio library that is not installed. Each
scenario therefore runs in a subprocess, fully isolated from the pytest
session; a radio whose library is missing there is skipped.
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
    ("zigpy_znp", "AppZnp", "App_znp"),
    ("bellows", "AppBellows", "App_bellows"),
    ("zigpy_deconz", "AppDeconz", "App_deconz"),
    ("zigpy_blz", "AppBlz", "App_blz"),
]

IEEE = "00158d0001a2b3c4"
OTHER_IEEE = "00158d0001ffffff"

HARNESS = textwrap.dedent(
    """
    import asyncio, importlib, json, sys, types
    from collections import defaultdict
    from unittest.mock import AsyncMock, MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.application
    import zigpy.device
    import zigpy.exceptions
    import zigpy.types as t

    sc = json.loads(sys.argv[1])
    try:
        importlib.import_module(sc["library"])
        # Imports zigpy_znp whatever the radio
        workerLoop = importlib.import_module("Classes.ZigpyTransport.workerLoop")
    except ImportError:
        print("RESULT=" + json.dumps({"missing": True}))
        sys.exit(0)
    if sc["kind"] == "gpd" and not hasattr(zigpy.application.ControllerApplication, "permit_gp"):
        print("RESULT=" + json.dumps({"missing": True}))
        sys.exit(0)

    app_class = getattr(importlib.import_module("Classes.ZigpyTransport." + sc["module"]), sc["class"])


    async def main():
        ieee = t.EUI64.convert(sc["in_table"])
        # spec= for the isinstance() of remove()
        if sc["kind"] == "gpd":
            dev = MagicMock(spec=zigpy.device.GreenPowerDevice, ieee=ieee, nwk=t.NWK(0x1234))
        else:
            dev = MagicMock(spec=zigpy.device.ZigbeeDevice, ieee=ieee, nwk=t.NWK(0x1234))
            dev.node_desc = MagicMock(is_end_device=sc["end_device"])
            dev.zdo = MagicMock(leave=AsyncMock(
                side_effect=zigpy.exceptions.DeliveryError("no ack") if sc["leave_fails"] else None))

        tasks = []
        app = types.SimpleNamespace(
            devices={ieee: dev},
            topology=types.SimpleNamespace(neighbors=defaultdict(list)),
            listener_event=MagicMock(),
            green_power=types.SimpleNamespace(unpair=AsyncMock()),
            create_task=lambda coro, name=None: tasks.append(asyncio.ensure_future(coro)),
        )
        for name in ("remove_ieee", "remove", "_remove_device"):
            setattr(app, name, types.MethodType(getattr(app_class, name), app))

        transport = MagicMock(app=app)
        await workerLoop.dispatch_command(
            transport, {"cmd": "REMOVE-DEVICE", "datas": {"Param1": int(sc["removed"], 16)}})
        await asyncio.gather(*tasks)

        print("RESULT=" + json.dumps({
            "left_in_table": len(app.devices),
            "leaves": 0 if sc["kind"] == "gpd" else dev.zdo.leave.await_count,
            "unpaired": [call.args == (dev,) for call in app.green_power.unpair.await_args_list],
            "events": [call.args[0] for call in app.listener_event.call_args_list],
        }))


    asyncio.run(main())
    """
)


def _run(radio, kind="zigbee", end_device=False, leave_fails=False, in_table=IEEE, removed=IEEE):
    library, module, class_name = radio
    scenario = {
        "library": library, "module": module, "class": class_name, "kind": kind,
        "end_device": end_device, "leave_fails": leave_fails, "removed": removed,
        "in_table": ":".join(in_table[i:i + 2] for i in range(0, 16, 2)),
    }
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(scenario)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT="))
    result = json.loads(line[len("RESULT="):])
    if result.get("missing"):
        pytest.skip("requires %s%s" % (library, " and zigpy Green Power" if kind == "gpd" else ""))
    return result


@pytest.mark.parametrize("radio", RADIOS, ids=[r[1] for r in RADIOS])
class TestRemoveIeee:

    @pytest.mark.parametrize("end_device", [False, True])
    def test_device_is_asked_to_leave_and_dropped(self, radio, end_device):
        assert _run(radio, end_device=end_device) == {
            "left_in_table": 0, "leaves": 1, "unpaired": [], "events": ["device_removed"]}

    def test_device_is_dropped_when_the_leave_fails(self, radio):
        assert _run(radio, leave_fails=True) == {
            "left_in_table": 0, "leaves": 1, "unpaired": [], "events": ["device_removed"]}

    def test_green_power_device_is_unpaired(self, radio):
        assert _run(radio, kind="gpd") == {
            "left_in_table": 0, "leaves": 0, "unpaired": [True], "events": ["device_removed"]}

    def test_device_unknown_to_zigpy_is_ignored(self, radio):
        assert _run(radio, removed=OTHER_IEEE) == {
            "left_in_table": 1, "leaves": 0, "unpaired": [], "events": []}
