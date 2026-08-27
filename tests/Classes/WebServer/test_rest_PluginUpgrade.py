#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.rest_PluginUpgrade.

Covers two regressions:
- certified_devices_update() / rest_plugin_upgrade() used to log/return only
  process.stdout, silently dropping process.stderr (where pip normally
  writes its failure reason).
- certified_devices_update() used to pick the pip upgrade command with
  ``distro.version() >= '12'``, a *string* comparison. Lexicographically
  '9' >= '12' is True, so Debian 9 wrongly took the Debian-12+
  --break-system-packages branch.
"""

import subprocess
import sys
import types
from unittest.mock import MagicMock

import pytest


def _ensure_attr(module_name, **attrs):
    """Add attributes to a stub (or create one) without replacing existing modules."""
    mod = sys.modules.get(module_name)
    if mod is None:
        mod = types.ModuleType(module_name)
        sys.modules[module_name] = mod
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture
def rpu():
    """Import Classes.WebServer.rest_PluginUpgrade fresh, with heavy deps stubbed."""
    _ensure_attr("Modules.database", import_local_device_conf=MagicMock(name="import_local_device_conf"))
    _ensure_attr("Modules.matomo_request", matomo_plugin_update=MagicMock(name="matomo_plugin_update"))

    sys.modules.pop("Classes.WebServer.rest_PluginUpgrade", None)
    import Classes.WebServer.rest_PluginUpgrade as m
    return m


@pytest.fixture
def plugin():
    p = MagicMock()
    p.logging = MagicMock()
    p.pluginParameters = {"HomeFolder": "/tmp/plugin"}
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {
        "internetAccess": True,
        "MatomoOptIn": False,
        "enableCache": False,
        "enableKeepalive": False,
    }
    return p


def _fake_process(stdout="", stderr="", returncode=0):
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# certified_devices_update()
# ---------------------------------------------------------------------------

class TestCertifiedDevicesUpdateNoInternet:
    def test_internet_disabled_skips_subprocess(self, rpu, plugin, monkeypatch):
        plugin.pluginconf.pluginConf["internetAccess"] = False
        run_mock = MagicMock()
        monkeypatch.setattr(rpu.subprocess, "run", run_mock)

        result = rpu.certified_devices_update(plugin)

        run_mock.assert_not_called()
        assert result["ReturnCode"] == -1


class TestCertifiedDevicesUpdateStderrCapture:
    def test_failure_stderr_is_included_in_result(self, rpu, plugin, monkeypatch):
        proc = _fake_process(stdout="", stderr="ERROR: externally-managed-environment", returncode=1)
        monkeypatch.setattr(rpu.subprocess, "run", MagicMock(return_value=proc))
        monkeypatch.setattr(rpu.distro, "id", lambda: "debian")
        monkeypatch.setattr(rpu.distro, "version", lambda: "12")

        result = rpu.certified_devices_update(plugin)

        assert "externally-managed-environment" in result["result"]
        assert result["ReturnCode"] == 1

    def test_failure_stderr_is_logged_at_error_level(self, rpu, plugin, monkeypatch):
        proc = _fake_process(stdout="", stderr="ERROR: network unreachable", returncode=1)
        monkeypatch.setattr(rpu.subprocess, "run", MagicMock(return_value=proc))
        monkeypatch.setattr(rpu.distro, "id", lambda: "debian")
        monkeypatch.setattr(rpu.distro, "version", lambda: "12")

        rpu.certified_devices_update(plugin)

        logged_messages = [c.args[1] for c in plugin.logging.call_args_list]
        assert any("network unreachable" in m for m in logged_messages)
        error_calls = [c for c in plugin.logging.call_args_list if c.args[0] == "Error"]
        assert any("network unreachable" in c.args[1] for c in error_calls)

    def test_success_logs_at_log_level(self, rpu, plugin, monkeypatch):
        proc = _fake_process(stdout="Successfully installed z4d-certified-devices", stderr="", returncode=0)
        monkeypatch.setattr(rpu.subprocess, "run", MagicMock(return_value=proc))
        monkeypatch.setattr(rpu.distro, "id", lambda: "debian")
        monkeypatch.setattr(rpu.distro, "version", lambda: "12")

        result = rpu.certified_devices_update(plugin)

        assert result["ReturnCode"] == 0
        error_calls = [c for c in plugin.logging.call_args_list if c.args[0] == "Error"]
        assert not error_calls


class TestCertifiedDevicesUpdateDistroVersion:
    """distro.version() must be compared numerically, not lexicographically."""

    @pytest.mark.parametrize(
        "distro_id, distro_version, expect_break_system_packages",
        [
            ("debian", "9", False),     # regression: '9' >= '12' is True as strings
            ("debian", "9.13", False),
            ("debian", "10", False),
            ("debian", "11", False),
            ("debian", "12", True),
            ("debian", "12.5", True),
            ("debian", "13", True),
            ("raspbian", "12", True),
            ("raspbian", "11", False),
            ("fedora", "40", False),    # not debian/raspbian: never break-system-packages
            ("debian", "", False),      # unparsable version: safe fallback
            ("debian", "unknown", False),
        ],
    )
    def test_upgrade_cmd_selection(
        self, rpu, plugin, monkeypatch, distro_id, distro_version, expect_break_system_packages
    ):
        proc = _fake_process(stdout="ok", stderr="", returncode=0)
        run_mock = MagicMock(return_value=proc)
        monkeypatch.setattr(rpu.subprocess, "run", run_mock)
        monkeypatch.setattr(rpu.distro, "id", lambda: distro_id)
        monkeypatch.setattr(rpu.distro, "version", lambda: distro_version)

        rpu.certified_devices_update(plugin)

        used_cmd = run_mock.call_args.args[0]
        assert ("--break-system-packages" in used_cmd) is expect_break_system_packages


# ---------------------------------------------------------------------------
# rest_plugin_upgrade()
# ---------------------------------------------------------------------------

class TestRestPluginUpgradeStderrCapture:
    def test_failure_stderr_is_included_in_response_and_log(self, rpu, plugin, monkeypatch):
        proc = _fake_process(stdout="", stderr="permission denied", returncode=1)
        monkeypatch.setattr(rpu.subprocess, "run", MagicMock(return_value=proc))

        response = rpu.rest_plugin_upgrade(plugin, "GET", {}, {})

        assert "permission denied" in response["Data"]
        error_calls = [c for c in plugin.logging.call_args_list if c.args[0] == "Error"]
        assert any("permission denied" in c.args[1] for c in error_calls)

    def test_non_get_verb_short_circuits(self, rpu, plugin, monkeypatch):
        run_mock = MagicMock()
        monkeypatch.setattr(rpu.subprocess, "run", run_mock)

        rpu.rest_plugin_upgrade(plugin, "POST", {}, {})

        run_mock.assert_not_called()
