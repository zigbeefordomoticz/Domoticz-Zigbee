#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/database.py

Coverage:
  - _write_DeviceList_json(): ListOfDevices carries a deque (RollingLQI, see
    Modules/tools_sqn.py), which json.dump() cannot serialise. The JSON export
    (expJsonDatabase) raised TypeError, and as it runs first in
    flush_plugin_listofdevice() the exception also aborted the txt / Domoticz
    flush of the device list.
  - flush_plugin_listofdevice(): a JSON export failure is logged and the txt
    database is still written.
  - import_local_device_conf(): only *.json files of Local-Devices are loaded;
    editor backups or other files are skipped instead of being parsed.

Modules.database imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import json, sys, tempfile, types
    from collections import deque
    from pathlib import Path
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Modules.database as database

    class Log:
        def __init__(self):
            self.records = []
        def logging(self, module, level, message, *args, **kwargs):
            self.records.append((level, message))
        def errors(self):
            return [m for lvl, m in self.records if lvl == "Error"]

    def make_plugin(tmpdir, devices):
        p = types.SimpleNamespace()
        p.log = Log()
        p.pluginconf = types.SimpleNamespace(pluginConf={
            "pluginData": str(tmpdir), "pluginConfig": str(tmpdir),
            "expJsonDatabase": True, "useDomoticzDb": False, "storeDomoticzDb": False,
        })
        p.DeviceListName = "DeviceList-1.txt"
        p.ListOfDevices = devices
        p.DeviceConf = {}
        p.ModelManufMapping = {}
        p.HBcount = 0
        p.flush_list_of_devices = True
        p.VersionNewFashion = False  # no Domoticz DB in this test
        return p
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_json_export_flattens_deque():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            devices = {"1234": {"Model": "x", "RollingLQI": deque([10, 20], maxlen=10)}}
            p = make_plugin(tmp, devices)
            database._write_DeviceList_json(p)
            data = json.loads((Path(tmp) / "DeviceList-1.json").read_text())
            assert data["1234"]["RollingLQI"] == [10, 20], data
            assert isinstance(devices["1234"]["RollingLQI"], deque), "live data must not be modified"
            assert p.log.errors() == [], p.log.errors()
        """
    )


def test_json_export_failure_does_not_block_txt_flush():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            devices = {"1234": {"Model": "x", "Unserializable": {1, 2}}}
            p = make_plugin(tmp, devices)
            database.flush_plugin_listofdevice(p)
            assert any("_write_DeviceList_json" in m for m in p.log.errors()), p.log.records
            assert not (Path(tmp) / "DeviceList-1.json").exists()
            assert not (Path(tmp) / "DeviceList-1.json.tmp").exists()
            assert "1234" in (Path(tmp) / "DeviceList-1.txt").read_text()
            assert p.flush_list_of_devices is False
        """
    )


def test_local_devices_only_json_files_are_loaded():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "Local-Devices"
            local.mkdir()
            (local / "MyModel.json").write_text(json.dumps({"Ep": {}}))
            (local / "Other.JSON").write_text(json.dumps({"Ep": {}}))
            (local / "MyModel.json.bak").write_text("not json")
            (local / "MyModel.json~").write_text("not json")
            (local / ".hidden.json").write_text("not json")
            (local / "README.md").write_text("# readme")
            (local / ".PRECIOUS").write_text("")
            p = make_plugin(tmp, {})
            database.import_local_device_conf(p)
            assert sorted(p.DeviceConf) == ["MyModel", "Other"], p.DeviceConf
            assert p.log.errors() == [], p.log.errors()
        """
    )
