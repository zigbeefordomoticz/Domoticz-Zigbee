#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.pluginHelpers.py, focused on the constraints-parsing
and Python-module version-checking helpers (parse_constraints,
check_requirements, check_python_modules_version, list_all_modules_loaded).

Modules.pluginHelpers imports the real Modules.tools / Modules.domoticzAbstractLayer
package chain, which conflicts with the session-wide stubs installed by
tests/conftest.py for the rest of the suite. As documented for the sibling
tests in tests/Classes/test_scan_classes_deviceconf.py, these checks are
therefore executed in a subprocess, fully isolated from the pytest session,
with only DomoticzEx faked (the only piece of the chain that is genuinely
unavailable outside a real Domoticz install).
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types, tempfile
    from pathlib import Path
    from unittest.mock import MagicMock

    ERRORS = []
    STATUSES = []

    domoticz = types.ModuleType("DomoticzEx")
    domoticz.Error = lambda msg: ERRORS.append(msg)
    domoticz.Status = lambda msg: STATUSES.append(msg)
    domoticz.Log = MagicMock(name="Log")
    domoticz.Debug = MagicMock(name="Debug")
    domoticz.Unit = MagicMock(name="Unit")
    domoticz.Connection = MagicMock(name="Connection")
    sys.modules["DomoticzEx"] = domoticz

    import importlib.metadata as im
    import Modules.pluginHelpers as ph

    def make_home(constraints_text):
        home = tempfile.mkdtemp()
        (Path(home) / "constraints.txt").write_text(constraints_text)
        return home

    def fake_versions(mapping):
        im.version = lambda name: mapping[name]

    def fake_missing_package():
        def _raise(name):
            raise im.PackageNotFoundError(name)
        im.version = _raise

    def make_self(home_folder, internet_access=False):
        return types.SimpleNamespace(
            pluginconf=types.SimpleNamespace(pluginConf={"internetAccess": internet_access}),
            pluginParameters={"HomeFolder": home_folder},
            log=types.SimpleNamespace(logging=lambda *a, **k: LOGS.append(a)),
        )

    LOGS = []
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) pluginHelpers module."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Regression guard: the ImportError that broke plugin.py
# ---------------------------------------------------------------------------

def test_all_symbols_imported_by_plugin_are_exported():
    """
    plugin.py does:
        from Modules.pluginHelpers import (check_firmware_level,
            check_python_modules_version, check_requirements, decodeConnection,
            get_domoticz_version, list_all_modules_loaded, networksize_update,
            update_DB_device_status_to_reinit)

    A prior revision removed check_python_modules_version and
    list_all_modules_loaded while leaving these imports in plugin.py, which
    made the whole plugin fail to import at startup. Guard against a repeat.
    """
    assert _run(
        """
        names = [
            "check_firmware_level", "check_python_modules_version",
            "check_requirements", "decodeConnection", "get_domoticz_version",
            "list_all_modules_loaded", "networksize_update",
            "update_DB_device_status_to_reinit",
        ]
        for name in names:
            assert callable(getattr(ph, name)), name
        print("ok")
        """
    ) == "ok"


# ---------------------------------------------------------------------------
# parse_constraints
# ---------------------------------------------------------------------------

def test_parse_constraints_returns_every_entry_by_default():
    assert _run(
        """
        home = make_home("\\n".join([
            "zigpy==2.1.0",
            "zigpy_znp>=1.0.0,<2.0.0",
            "unrelated-package==9.9.9",
            "# a comment line",
            "bellows~=1.0",
            "",
        ]))
        constraints = ph.parse_constraints(home)
        assert set(constraints) == {"zigpy", "zigpy_znp", "unrelated-package", "bellows"}, constraints
        print("ok")
        """
    ) == "ok"


def test_parse_constraints_filters_to_given_packages():
    assert _run(
        """
        home = make_home("\\n".join([
            "zigpy==2.1.0",
            "unrelated-package==9.9.9",
            "bellows~=1.0",
        ]))
        constraints = ph.parse_constraints(home, ph.PYTHON_MODULES)
        assert set(constraints) == {"zigpy", "bellows"}, constraints
        print("ok")
        """
    ) == "ok"


def test_parse_constraints_builds_usable_specifiers():
    assert _run(
        """
        from packaging.version import Version
        home = make_home("\\n".join([
            "zigpy==2.1.0",
            "zigpy_znp>=1.0.0,<2.0.0",
        ]))
        constraints = ph.parse_constraints(home)
        assert Version("2.1.0") in constraints["zigpy"]
        assert Version("2.0.0") not in constraints["zigpy"]
        assert Version("1.5.0") in constraints["zigpy_znp"]
        assert Version("2.5.0") not in constraints["zigpy_znp"]
        print("ok")
        """
    ) == "ok"


def test_parse_constraints_bare_package_matches_any_version():
    assert _run(
        """
        from packaging.version import Version
        home = make_home("bellows\\n")
        constraints = ph.parse_constraints(home)
        assert Version("0.0.1") in constraints["bellows"]
        print("ok")
        """
    ) == "ok"


# ---------------------------------------------------------------------------
# check_requirements
# ---------------------------------------------------------------------------

def test_check_requirements_true_when_all_satisfied():
    assert _run(
        """
        home = make_home("\\n".join([
            "zigpy==2.1.0",
            "bellows>=1.0.0",
        ]))
        fake_versions({"zigpy": "2.1.0", "bellows": "1.2.0"})
        assert ph.check_requirements(home) is True
        assert not ERRORS, ERRORS
        print("ok")
        """
    ) == "ok"


def test_check_requirements_false_on_version_mismatch():
    assert _run(
        """
        home = make_home("zigpy==2.1.0\\n")
        fake_versions({"zigpy": "1.0.0"})
        assert ph.check_requirements(home) is False
        assert any("does not satisfy" in e for e in ERRORS), ERRORS
        print("ok")
        """
    ) == "ok"


def test_check_requirements_false_when_package_not_installed():
    assert _run(
        """
        home = make_home("zigpy==2.1.0\\n")
        fake_missing_package()
        assert ph.check_requirements(home) is False
        assert any("not installed" in e for e in ERRORS), ERRORS
        print("ok")
        """
    ) == "ok"


def test_check_requirements_false_on_invalid_constraint():
    assert _run(
        """
        home = make_home("zigpy~1.0\\n")
        fake_versions({"zigpy": "2.1.0"})
        assert ph.check_requirements(home) is False
        assert any("Invalid version constraint" in e for e in ERRORS), ERRORS
        print("ok")
        """
    ) == "ok"


def test_check_requirements_ignores_comments_and_blank_lines():
    assert _run(
        """
        home = make_home("\\n".join([
            "# top comment",
            "",
            "zigpy==2.1.0  # inline comment",
            "",
        ]))
        fake_versions({"zigpy": "2.1.0"})
        assert ph.check_requirements(home) is True
        print("ok")
        """
    ) == "ok"


# ---------------------------------------------------------------------------
# check_python_modules_version
# ---------------------------------------------------------------------------

def test_check_python_modules_version_skips_when_internet_access_enabled():
    assert _run(
        """
        self = types.SimpleNamespace(
            pluginconf=types.SimpleNamespace(pluginConf={"internetAccess": True}),
            pluginParameters={},
            log=types.SimpleNamespace(logging=lambda *a, **k: LOGS.append(a)),
        )
        assert ph.check_python_modules_version(self) is True
        assert LOGS == []
        print("ok")
        """
    ) == "ok"


def test_check_python_modules_version_true_when_compatible():
    assert _run(
        """
        home = make_home("zigpy==2.1.0\\n")
        fake_versions({"zigpy": "2.1.0"})
        self = make_self(home)
        assert ph.check_python_modules_version(self) is True
        assert LOGS == []
        print("ok")
        """
    ) == "ok"


def test_check_python_modules_version_false_when_incompatible():
    assert _run(
        """
        home = make_home("zigpy==2.1.0\\n")
        fake_versions({"zigpy": "1.0.0"})
        self = make_self(home)
        assert ph.check_python_modules_version(self) is False
        assert any("not compatible" in str(entry) for entry in LOGS), LOGS
        print("ok")
        """
    ) == "ok"


# ---------------------------------------------------------------------------
# list_all_modules_loaded
# ---------------------------------------------------------------------------

def test_list_all_modules_loaded_runs_and_logs():
    assert _run(
        """
        self = types.SimpleNamespace(log=types.SimpleNamespace(logging=lambda *a, **k: LOGS.append(a)))
        ph.list_all_modules_loaded(self)
        assert len(LOGS) >= 2
        print("ok")
        """
    ) == "ok"
