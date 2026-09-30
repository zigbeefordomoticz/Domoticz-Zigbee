#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AppGeneric.initialize() and _retrieve_previous_backup().

AppGeneric's functions are monkey-patched onto each radio's
ControllerApplication at runtime; here they are driven against a fake app
whose base class provides form_network(), so that both
`super(type(self), self).form_network()` and `self.form_network()` resolve
to the same recorded call — exactly as with the real radio libraries, none
of which override form_network().

Importing AppGeneric pulls in Classes.ZigpyTransport.Transport and
Classes.ZigateTransport.sqnMgmt, which tests/conftest.py stubs for the rest
of the session. Each scenario therefore runs in a subprocess, fully isolated
from the pytest session. The real zigpy package is required (NetworkBackup
comparisons); the module is skipped when it is not installed.
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

# PAN IDs used to tell apart which backup was picked up / restored
PLUGIN_BACKUP_PAN = 0x1111
DB_BACKUP_PAN = 0x2222

HARNESS = textwrap.dedent(
    """
    import asyncio, json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.config as zc
    import zigpy.exceptions
    import zigpy.types as t
    from zigpy.backups import NetworkBackup

    import Classes.ZigpyTransport.AppGeneric as AG

    sc = json.loads(sys.argv[1])

    def backup_with_pan(pan):
        b = NetworkBackup()
        return b.replace(network_info=b.network_info.replace(pan_id=t.PanId(pan)))

    class Log:
        def __init__(self):
            self.records = []
        def logging(self, category, level, message, *args, **kwargs):
            self.records.append([level, str(message)])

    class FakeBackups:
        def __init__(self, app, db_pans, state_pan, restore_fails):
            self.app = app
            self.backups = [backup_with_pan(p) for p in db_pans]
            self.state = backup_with_pan(state_pan)
            self.restore_fails = restore_fails
        def add_backup(self, backup):
            self.backups.append(backup)
        def most_recent_backup(self):
            return self.backups[-1] if self.backups else None
        def from_network_state(self):
            return self.state
        async def restore_backup(self, backup):
            self.app.calls.append("restore_backup:%04x" % backup.network_info.pan_id)
            if self.restore_fails:
                raise RuntimeError("restore failed")
            self.app.network_formed = True

    class RadioControllerApplication:
        # Stands in for zigpy.application.ControllerApplication, the only
        # class that defines form_network() in every radio library's MRO.
        async def form_network(self):
            self.calls.append("form_network")
            if self.form_fails:
                raise RuntimeError("form failed")
            self.network_formed = True

    class FakeApp(RadioControllerApplication):
        def __init__(self):
            self.calls = []
            self.log = Log()
            self.network_formed = sc.get("network_formed", True)
            self.form_fails = sc.get("form_fails", False)
            self.config = {
                zc.CONF_WATCHDOG_ENABLED: False,
                zc.CONF_NWK_VALIDATE_SETTINGS: sc.get("validate", False),
                zc.CONF_TOPO_SCAN_ENABLED: False,
            }
            self.pluginconf = types.SimpleNamespace(pluginConf={
                "autoRestore": sc.get("autoRestore", 1),
                "OverWriteCoordinatorIEEEOnlyOnce": sc.get("overwrite_ieee", 0),
            })
            self.backups = FakeBackups(
                self, sc.get("db_pans", []), sc.get("state_pan", 0), sc.get("restore_fails", False)
            )
            self.state = types.SimpleNamespace(network_info=None, node_info=None)
            self.callBackGetAllDevices = None
        async def load_network_info(self, *, load_devices=False):
            self.calls.append("load_network_info")
            if not self.network_formed:
                raise zigpy.exceptions.NetworkNotFormed()
        async def start_network(self):
            self.calls.append("start_network")
        async def _get_effective_tx_power(self):
            return None
        async def _get_effective_maximum_tx_power(self):
            return None
        async def set_tx_power(self, power):
            pass
        def _persist_coordinator_model_strings_in_db(self):
            pass

    plugin_pan = sc.get("plugin_pan")
    AG.do_retrieve_backup = lambda self: backup_with_pan(plugin_pan).as_dict() if plugin_pan is not None else None

    app = FakeApp()
    result = {"error": None}
    if sc["mode"] == "retrieve":
        backup = AG._retrieve_previous_backup(app)
        result["backup_pan"] = None if backup is None else int(backup.network_info.pan_id)
        result["overwrite_flag"] = None if backup is None else backup.network_info.stack_specific.get(
            "ezsp", {}).get("i_understand_i_can_update_eui64_only_once_and_i_still_want_to_do_it")
        result["manager_pans"] = [int(b.network_info.pan_id) for b in app.backups.backups]
    else:
        try:
            asyncio.run(AG.initialize(app, auto_form=sc.get("auto_form", True), force_form=sc.get("force_form", False)))
        except Exception as e:
            result["error"] = type(e).__name__
    result["calls"] = app.calls
    result["logs"] = app.log.records
    print("RESULT=" + json.dumps(result))
    """
)


def _run(**scenario):
    scenario.setdefault("mode", "initialize")
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(scenario)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT="))
    return json.loads(line[len("RESULT="):])


def _restores(result):
    return [c for c in result["calls"] if c.startswith("restore_backup")]


def _errors(result):
    return [msg for level, msg in result["logs"] if level == "Error"]


# ─── #1: form OR restore, never both ─────────────────────────────────────────

class TestNetworkNotFormed:

    def test_no_backup_forms_network_exactly_once(self):
        result = _run(network_formed=False)
        assert result["error"] is None
        assert result["calls"].count("form_network") == 1
        assert _restores(result) == []

    def test_backup_is_restored_without_forming_first(self):
        result = _run(network_formed=False, plugin_pan=PLUGIN_BACKUP_PAN, state_pan=PLUGIN_BACKUP_PAN)
        assert result["error"] is None
        assert "form_network" not in result["calls"]
        assert _restores(result) == ["restore_backup:%04x" % PLUGIN_BACKUP_PAN]

    def test_without_auto_form_the_error_propagates(self):
        result = _run(network_formed=False, auto_form=False)
        assert result["error"] == "NetworkNotFormed"
        assert "form_network" not in result["calls"]
        assert "start_network" not in result["calls"]

    def test_formed_network_is_left_untouched(self):
        result = _run(network_formed=True, plugin_pan=PLUGIN_BACKUP_PAN, state_pan=PLUGIN_BACKUP_PAN)
        assert result["error"] is None
        assert "form_network" not in result["calls"]
        assert _restores(result) == []
        assert "start_network" in result["calls"]


# ─── #2: settings validation compares against the retrieved backup ───────────

class TestValidateNetworkSettings:

    def test_compatible_state_starts_the_network(self):
        result = _run(validate=True, plugin_pan=PLUGIN_BACKUP_PAN, state_pan=PLUGIN_BACKUP_PAN)
        assert result["error"] is None
        assert "start_network" in result["calls"]

    def test_incompatible_state_raises_settings_inconsistent(self):
        # Previously compared against the BackupManager and crashed with AttributeError
        result = _run(validate=True, plugin_pan=PLUGIN_BACKUP_PAN, state_pan=0x9999)
        assert result["error"] == "NetworkSettingsInconsistent"
        assert "start_network" not in result["calls"]

    def test_validation_disabled_ignores_incompatible_state(self):
        result = _run(validate=False, plugin_pan=PLUGIN_BACKUP_PAN, state_pan=0x9999)
        assert result["error"] is None
        assert "start_network" in result["calls"]

    def test_no_backup_skips_validation(self):
        result = _run(validate=True, state_pan=0x9999)
        assert result["error"] is None
        assert "start_network" in result["calls"]
