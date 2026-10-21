#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the PluginStore wiring in Modules/database.py

Coverage:
  - load_plugin_stores(): creates and loads every store of PLUGIN_STORES.
  - flush_plugin_listofdevice(): also writes the stores, so they follow the
    device list on every flush (periodic, requested, onStop).
  - With no store declared (stable9 today) the device list flush is unchanged
    and no store file appears.
  - A flush on a plugin whose stores were never loaded (onStop after a failed
    start) writes no store.

Modules.database imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, as in
test_database_json_export_local_devices.py.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import json, os, sys, tempfile, types
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

    def make_plugin(tmpdir):
        p = types.SimpleNamespace()
        p.log = Log()
        p.pluginconf = types.SimpleNamespace(pluginConf={
            "pluginData": str(tmpdir), "pluginConfig": str(tmpdir),
            "expJsonDatabase": False, "useDomoticzDb": False, "storeDomoticzDb": False,
            "numDeviceListVersion": 3,
        })
        p.DeviceListName = "DeviceList-1.txt"
        p.HardwareID = 1
        p.ListOfDevices = {"1234": {"Version": "3", "Status": "inDB"}}
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
    assert result.returncode == 0, "stdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr)
    return result.stdout


def test_declared_store_is_loaded_flushed_with_the_device_list_and_reloaded():
    _run(
        """
        database.PLUGIN_STORES = (("TestStore", 1, None),)
        with tempfile.TemporaryDirectory() as tmp:
            p = make_plugin(tmp)
            database.load_plugin_stores(p)
            assert p.PluginStores["TestStore"].writable
            p.PluginStores["TestStore"].set("k", {"v": 1})

            database.flush_plugin_listofdevice(p)

            assert os.path.isfile(os.path.join(tmp, "DeviceList-1.txt"))
            with open(os.path.join(tmp, "TestStore-1.json")) as f:
                assert json.load(f)["Records"] == {"k": {"v": 1}}

            q = make_plugin(tmp)
            database.load_plugin_stores(q)
            assert q.PluginStores["TestStore"].get("k") == {"v": 1}
            assert p.log.errors() == [] and q.log.errors() == []
        """
    )


def test_no_store_declared_leaves_the_flush_unchanged():
    _run(
        """
        assert database.PLUGIN_STORES == ()
        with tempfile.TemporaryDirectory() as tmp:
            p = make_plugin(tmp)
            database.load_plugin_stores(p)
            assert p.PluginStores == {}

            database.flush_plugin_listofdevice(p)

            assert sorted(os.listdir(tmp)) == ["DeviceList-1.txt"]
            assert p.log.errors() == []
        """
    )


def test_flush_without_loaded_stores_writes_no_store():
    _run(
        """
        database.PLUGIN_STORES = (("TestStore", 1, None),)
        with tempfile.TemporaryDirectory() as tmp:
            p = make_plugin(tmp)  # stores never loaded

            database.flush_plugin_listofdevice(p)

            assert sorted(os.listdir(tmp)) == ["DeviceList-1.txt"]
            assert p.log.errors() == []
        """
    )
