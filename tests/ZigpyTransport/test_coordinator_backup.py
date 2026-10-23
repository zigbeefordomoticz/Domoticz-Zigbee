#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for App*.coordinator_backup(), the scheduled coordinator backup
(plugin.py _trigger_coordinator_backup -> COORDINATOR-BACKUP -> workerLoop).

The scheduled backup must always be a full one (load_devices=True), like the
backup taken on shutdown: a backup without the children, link keys and NWK
addresses restores the network but loses every device's Trust Center link key
and the coordinator's child table.

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
    # (radio library, plugin module, application class)
    ("zigpy_znp", "AppZnp", "App_znp"),
    ("bellows", "AppBellows", "App_bellows"),
    ("zigpy_deconz", "AppDeconz", "App_deconz"),
    ("zigpy_blz", "AppBlz", "App_blz"),
]

HARNESS = textwrap.dedent(
    """
    import asyncio, importlib, json, sys, types
    from unittest.mock import AsyncMock, MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.config as zc

    sc = json.loads(sys.argv[1])
    try:
        importlib.import_module(sc["library"])
    except ImportError:
        print("RESULT=" + json.dumps({"missing": True}))
        sys.exit(0)

    app_class = getattr(importlib.import_module("Classes.ZigpyTransport." + sc["module"]), sc["class"])

    backup = object()
    app = types.SimpleNamespace(
        config={zc.CONF_NWK_BACKUP_ENABLED: sc["backup_enabled"]},
        # No backup setting at all: the call must not depend on PluginConf
        pluginconf=types.SimpleNamespace(pluginConf={}),
        backups=types.SimpleNamespace(create_backup=AsyncMock(return_value=backup)),
        callBackBackup=MagicMock(),
    )
    asyncio.run(app_class.coordinator_backup(app))

    print("RESULT=" + json.dumps({
        "create_backup_calls": [call.kwargs for call in app.backups.create_backup.await_args_list],
        "callback_got_backup": [call.args == (backup,) for call in app.callBackBackup.call_args_list],
    }))
    """
)


def _run(**scenario):
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(scenario)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT="))
    result = json.loads(line[len("RESULT="):])
    if result.get("missing"):
        pytest.skip("requires %s" % scenario["library"])
    return result


@pytest.mark.parametrize("library, module, class_name", RADIOS)
class TestCoordinatorBackup:

    def test_scheduled_backup_is_always_full(self, library, module, class_name):
        result = _run(library=library, module=module, **{"class": class_name}, backup_enabled=True)
        assert result["create_backup_calls"] == [{"load_devices": True}]
        assert result["callback_got_backup"] == [True]

    def test_no_backup_when_disabled_in_zigpy_config(self, library, module, class_name):
        result = _run(library=library, module=module, **{"class": class_name}, backup_enabled=False)
        assert result["create_backup_calls"] == []
        assert result["callback_got_backup"] == []
