"""
tests/Classes/Groups/test_group_list_write.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for write_groups_list() in Classes/GroupMgtv2/GrpDatabase.py.

write_groups_list() is called after every mutation of ListOfGroups, because nothing
tells the plugin when a group membership scan is over. These tests cover the guard
that skips the dump when the serialized groups list has not changed since the last
write, and make sure a real change, a missing file or a failed write still write.

The module is imported in isolation against a minimal stub so no Domoticz
framework or radio backend is required.

Run with:
    pytest tests/Classes/Groups/test_group_list_write.py -v
"""

import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

_GRP_DB_DEPS = ("Modules.domoticzAbstractLayer",)


@pytest.fixture
def grp_db():
    """
    Load GrpDatabase directly from its file path, with Modules.domoticzAbstractLayer
    stubbed, so the test is immune to whatever package state is in sys.modules.
    Function scoped, as the tests assert on the stub's setConfigItem calls.
    """
    import importlib.util
    import pathlib

    module_path = pathlib.Path(__file__).parents[3] / "Classes" / "GroupMgtv2" / "GrpDatabase.py"

    saved = {name: sys.modules.pop(name, None) for name in _GRP_DB_DEPS}
    stub = types.ModuleType("Modules.domoticzAbstractLayer")
    stub.domoticz_log_api = MagicMock()
    stub.getConfigItem = MagicMock(return_value={})
    stub.setConfigItem = MagicMock()
    sys.modules["Modules.domoticzAbstractLayer"] = stub

    spec = importlib.util.spec_from_file_location("Classes.GroupMgtv2.GrpDatabase", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    yield module

    for name in _GRP_DB_DEPS:
        sys.modules.pop(name, None)
        if saved.get(name) is not None:
            sys.modules[name] = saved[name]


class _FakeSelf:
    """Minimal stand-in for the GroupsManagement instance."""

    def __init__(self, filename, list_of_groups=None, use_domoticz_db=False):
        self.ListOfGroups = list_of_groups if list_of_groups is not None else {}
        self.GroupListFileName = str(filename)
        self.last_written_groups_list = None
        self.pluginconf = types.SimpleNamespace(pluginConf={"useDomoticzDb": use_domoticz_db})
        self.log = types.SimpleNamespace(logging=MagicMock())
        self.logging = MagicMock()


SENTINEL = "-- not rewritten --"


def _poison(path):
    """Overwrite the file so any later real write is visible."""
    with open(path, "wt") as handle:
        handle.write(SENTINEL)


def _content(path):
    with open(path) as handle:
        return handle.read()


class TestWriteGroupsList:

    def test_first_call_writes_the_file(self, grp_db, tmp_path):
        target = tmp_path / "GroupsList-03.json"
        plugin = _FakeSelf(target, {"4001": {"Name": "Kitchen", "Devices": []}})

        grp_db.write_groups_list(plugin)

        assert target.is_file()
        assert json.loads(_content(target)) == {"4001": {"Name": "Kitchen", "Devices": []}}

    def test_unchanged_groups_list_is_not_rewritten(self, grp_db, tmp_path):
        """The case seen during a membership scan: repeated calls, nothing changed."""
        target = tmp_path / "GroupsList-03.json"
        plugin = _FakeSelf(target, {})

        grp_db.write_groups_list(plugin)
        _poison(target)
        grp_db.write_groups_list(plugin)
        grp_db.write_groups_list(plugin)

        assert _content(target) == SENTINEL

    def test_mutated_groups_list_is_written_again(self, grp_db, tmp_path):
        target = tmp_path / "GroupsList-03.json"
        plugin = _FakeSelf(target, {})

        grp_db.write_groups_list(plugin)
        _poison(target)
        plugin.ListOfGroups["4001"] = {"Name": "Kitchen", "Devices": []}
        grp_db.write_groups_list(plugin)

        assert json.loads(_content(target)) == {"4001": {"Name": "Kitchen", "Devices": []}}

    def test_in_place_mutation_is_detected(self, grp_db, tmp_path):
        """ListOfGroups is mutated in place, so the guard must compare serialized content."""
        target = tmp_path / "GroupsList-03.json"
        groups = {"4001": {"Name": "Kitchen", "Devices": []}}
        plugin = _FakeSelf(target, groups)

        grp_db.write_groups_list(plugin)
        _poison(target)
        groups["4001"]["Devices"].append(["e99a", "01", "00158d0001abcdef"])
        grp_db.write_groups_list(plugin)

        assert json.loads(_content(target))["4001"]["Devices"] == [["e99a", "01", "00158d0001abcdef"]]

    def test_missing_file_is_rewritten_even_when_unchanged(self, grp_db, tmp_path):
        """Someone clearing the plugin Data directory must not be left without a file."""
        target = tmp_path / "GroupsList-03.json"
        plugin = _FakeSelf(target, {"4001": {"Name": "Kitchen", "Devices": []}})

        grp_db.write_groups_list(plugin)
        os.remove(target)
        grp_db.write_groups_list(plugin)

        assert target.is_file()
        assert json.loads(_content(target)) == {"4001": {"Name": "Kitchen", "Devices": []}}

    def test_output_is_unchanged_from_json_dump(self, grp_db, tmp_path):
        """Regression guard: switching to handle.write() must keep the file format."""
        groups = {"4002": {"Name": "Living", "Devices": [["1234", "01", "00158d0001abcdef"]]}}
        target = tmp_path / "GroupsList-03.json"
        reference = tmp_path / "reference.json"
        with open(reference, "wt") as handle:
            json.dump(groups, handle, sort_keys=True, indent=2)

        grp_db.write_groups_list(_FakeSelf(target, groups))

        assert _content(target) == _content(reference)


class TestWriteGroupsListDomoticzDb:

    def test_domoticz_db_is_written_on_a_real_change(self, grp_db, tmp_path):
        target = tmp_path / "GroupsList-03.json"
        plugin = _FakeSelf(target, {"4001": {"Name": "Kitchen"}}, use_domoticz_db=True)

        grp_db.write_groups_list(plugin)

        assert sys.modules["Modules.domoticzAbstractLayer"].setConfigItem.call_count == 1

    def test_domoticz_db_is_skipped_when_unchanged(self, grp_db, tmp_path):
        """The redundant dumps also cost a Domoticz Db write, so they must be skipped too."""
        target = tmp_path / "GroupsList-03.json"
        plugin = _FakeSelf(target, {"4001": {"Name": "Kitchen"}}, use_domoticz_db=True)

        grp_db.write_groups_list(plugin)
        grp_db.write_groups_list(plugin)
        grp_db.write_groups_list(plugin)

        assert sys.modules["Modules.domoticzAbstractLayer"].setConfigItem.call_count == 1

    def test_failed_file_write_does_not_mark_the_payload_as_written(self, grp_db, tmp_path):
        """A write that raised must be retried on the next call, not skipped as unchanged."""
        unwritable = tmp_path / "no-such-directory" / "GroupsList-03.json"
        plugin = _FakeSelf(unwritable, {"4001": {"Name": "Kitchen"}})

        with pytest.raises(OSError):
            grp_db.write_groups_list(plugin)

        assert plugin.last_written_groups_list is None
