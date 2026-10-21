#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the choice between the json file and the Domoticz record when
loading the group list (Classes/GroupMgtv2/GrpDatabase.py) and the settings
(Classes/PluginConf.py).

Since #1900 both loaders read the record TimeStamp from inside the stored
group list / settings instead of from the record, so it was always 0:
  - the Domoticz copy never won while the json file existed;
  - groups: a missing json file returned before the Domoticz copy was read;
  - groups: with useDomoticzDb off, the json file was read and then dropped.

Records go through the real setConfigItem() / getConfigItem() (b64 + zlib
storage, Version stamping) against an in-memory DomoticzEx.Configuration.
The file is made older or newer than the record with os.utime().

Each scenario runs in a subprocess: the real Modules.domoticzAbstractLayer
and Classes.GroupMgtv2.GrpDatabase are needed, and tests/conftest.py and
other test files stub them for the rest of the session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import json, os, sys, tempfile, time, types
    from unittest.mock import MagicMock

    _config_store = {}

    def _configuration(new_cfg=None):
        if new_cfg is not None:
            _config_store.clear()
            _config_store.update(new_cfg)
        return dict(_config_store)

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = _configuration
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    from Modules.domoticzAbstractLayer import setConfigItem
    import Classes.GroupMgtv2.GrpDatabase as GrpDatabase
    import Classes.PluginConf as PluginConf

    GROUPS_DZ = {"aaaa": {"Name": "From Domoticz"}}
    GROUPS_FILE = {"bbbb": {"Name": "From file"}}

    def make_group_mgt(tmp, use_domoticz_db=True):
        g = types.SimpleNamespace()
        g.GroupListFileName = os.path.join(tmp, "GroupsList-01.json")
        g.pluginconf = types.SimpleNamespace(pluginConf={"useDomoticzDb": use_domoticz_db})
        g.log = MagicMock()
        g.logging = lambda level, message: None
        g.ListOfGroups = {}
        return g

    def store_groups(g, groups, file_groups=None, file_age=None):
        # Record (and file) as write_groups_list() stores them
        g.ListOfGroups = groups
        GrpDatabase.write_groups_list(g)
        if file_groups is not None:
            with open(g.GroupListFileName, "wt") as handle:
                json.dump(file_groups, handle)
        if file_age is not None:
            t = time.time() + file_age
            os.utime(g.GroupListFileName, (t, t))

    def make_conf(tmp, use_domoticz_db=True):
        c = types.SimpleNamespace()
        c.pluginConf = {"useDomoticzDb": use_domoticz_db, "storeDomoticzDb": use_domoticz_db, "pluginConfig": tmp}
        c.hardwareid = 1
        c.zigbee_communication = "zigpy"
        return c

    def store_settings(c, dz_settings, file_settings, file_age):
        setConfigItem(Key="PluginConf", Attribute="b64-settings", Value={"TimeStamp": time.time(), "b64-settings": dz_settings})
        path = os.path.join(c.pluginConf["pluginConfig"], "PluginConf-01.json")
        with open(path, "wt") as handle:
            json.dump(file_settings, handle)
        t = time.time() + file_age
        os.utime(path, (t, t))
    """
)


def _run(snippet):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "stdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr)


# ─── Groups ──────────────────────────────────────────────────────────────────

def test_groups_domoticz_record_more_recent_than_file_wins():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            g = make_group_mgt(tmp)
            store_groups(g, GROUPS_DZ, file_groups=GROUPS_FILE, file_age=-3600)

            GrpDatabase.load_groups_list_from_json(g)

            assert g.ListOfGroups == GROUPS_DZ, g.ListOfGroups
        """
    )


def test_groups_file_more_recent_than_record_wins():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            g = make_group_mgt(tmp)
            store_groups(g, GROUPS_DZ, file_groups=GROUPS_FILE, file_age=+3600)

            GrpDatabase.load_groups_list_from_json(g)

            assert g.ListOfGroups == GROUPS_FILE, g.ListOfGroups
        """
    )


def test_groups_missing_file_loads_the_domoticz_record():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            g = make_group_mgt(tmp)
            store_groups(g, GROUPS_DZ)
            os.remove(g.GroupListFileName)

            GrpDatabase.load_groups_list_from_json(g)

            assert g.ListOfGroups == GROUPS_DZ, g.ListOfGroups
        """
    )


def test_groups_file_loaded_when_domoticz_db_not_used():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            g = make_group_mgt(tmp, use_domoticz_db=False)
            with open(g.GroupListFileName, "wt") as handle:
                json.dump(GROUPS_FILE, handle)

            GrpDatabase.load_groups_list_from_json(g)

            assert g.ListOfGroups == GROUPS_FILE, g.ListOfGroups
        """
    )


def test_groups_nothing_stored_gives_an_empty_list():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            g = make_group_mgt(tmp)

            GrpDatabase.load_groups_list_from_json(g)

            assert g.ListOfGroups == {}
        """
    )


# ─── Settings ────────────────────────────────────────────────────────────────

def test_settings_domoticz_record_more_recent_than_file_wins():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            c = make_conf(tmp)
            store_settings(c, {"Livolo": 1}, {"Livolo": 2}, file_age=-3600)

            PluginConf.load_settings(c)

            assert c.pluginConf["Livolo"] == 1, c.pluginConf
        """
    )


def test_settings_file_more_recent_than_record_wins():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            c = make_conf(tmp)
            store_settings(c, {"Livolo": 1}, {"Livolo": 2}, file_age=+3600)

            PluginConf.load_settings(c)

            assert c.pluginConf["Livolo"] == 2, c.pluginConf
        """
    )


def test_settings_record_timestamp_is_read_from_the_record():
    _run(
        """
        with tempfile.TemporaryDirectory() as tmp:
            c = make_conf(tmp)
            before = time.time()
            setConfigItem(Key="PluginConf", Attribute="b64-settings", Value={"TimeStamp": time.time(), "b64-settings": {"Livolo": 1}})

            dz_timestamp, settings = PluginConf.loading_settings_from_domoticz(c)

            assert settings == {"Livolo": 1}
            assert dz_timestamp >= before, dz_timestamp
        """
    )
