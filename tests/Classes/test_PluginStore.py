#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/PluginStore.py

Covers:
  records      – get/set/update/delete, copies handed out
  load         – nothing stored, file, Domoticz record, most recent copy wins,
                 unreadable copy, newer version (downgrade), older version
                 with and without upgrade, versioned backup rotation
  flush        – only when changed, never for a store that is not writable,
                 Domoticz record only when enabled and available, write failure
                 retried at the next flush
  logging      – records never appear in the log

The Domoticz helpers are replaced on Classes.PersistedDocument: getConfigItem /
setConfigItem by an in-memory configuration that, like the real storage layer,
stamps its own "Version" on the record; is_domoticz_db_available by a flag.
The real storage layer is exercised in tests/Classes/test_PersistedDocument.py.
"""

import json
import os
import types

import pytest

import Classes.PersistedDocument as persisted_document_module
from Classes.PluginStore import PluginStore

SECRET = "00112233445566778899aabbccddeeff"
RECORD = {"name": "dev1", "key": SECRET, "counter": 7}


class Log:
    def __init__(self):
        self.records = []

    def logging(self, module, level, message, *args, **kwargs):
        self.records.append((level, str(message)))

    def errors(self):
        return [m for level, m in self.records if level == "Error"]

    def text(self):
        return " ".join(m for _, m in self.records)


@pytest.fixture
def domoticz(monkeypatch):
    """In-memory Domoticz configuration and availability flag."""
    state = types.SimpleNamespace(config={}, available=True, rotated=[])

    def get_config_item(Key=None, Attribute="", Default=None):
        return json.loads(json.dumps(state.config.get(Key, {})))

    def set_config_item(Key=None, Attribute="", Value=None):
        record = json.loads(json.dumps(Value))
        # As prepare_dict_for_storage(): the storage layer owns "Version"
        record["Version"] = 2
        state.config[Key] = record
        return state.config

    monkeypatch.setattr(persisted_document_module, "getConfigItem", get_config_item)
    monkeypatch.setattr(persisted_document_module, "setConfigItem", set_config_item)
    monkeypatch.setattr(persisted_document_module, "is_domoticz_db_available", lambda plugin: state.available)
    monkeypatch.setattr(persisted_document_module, "rotate_file_versions", lambda path, nb: state.rotated.append(path))
    return state


@pytest.fixture
def plugin(tmp_path):
    return types.SimpleNamespace(
        log=Log(),
        HardwareID=3,
        pluginconf=types.SimpleNamespace(pluginConf={
            "pluginData": str(tmp_path),
            "useDomoticzDb": False,
            "storeDomoticzDb": False,
            "numDeviceListVersion": 5,
        }),
    )


def store_file(plugin, name="TestStore"):
    return plugin.pluginconf.pluginConf["pluginData"] + "/%s-3.json" % name


def write_payload(path, version=1, timestamp=1000.0, records=None):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"FormatVersion": version, "TimeStamp": timestamp, "Records": records if records is not None else {"k": RECORD}}, handle)


def read_payload(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# ─── Records ─────────────────────────────────────────────────────────────────

class TestRecords:

    def test_set_get_update_delete(self):
        store = PluginStore("TestStore", 1)

        store.set("k", RECORD)
        assert store.update("k", {"counter": 8})
        assert store.get("k")["counter"] == 8
        assert "k" in store and len(store) == 1 and store.keys() == ["k"]

        store.delete("k")
        assert store.get("k") is None and len(store) == 0

    def test_update_of_missing_record_returns_false(self):
        assert PluginStore("TestStore", 1).update("missing", {"a": 1}) is False

    def test_copies_are_handed_out(self):
        store = PluginStore("TestStore", 1)
        record = dict(RECORD)
        store.set("k", record)

        record["counter"] = 99
        store.get("k")["counter"] = 99
        store.snapshot()["k"]["counter"] = 99

        assert store.get("k")["counter"] == 7


# ─── Load ────────────────────────────────────────────────────────────────────

class TestLoad:

    def test_nothing_stored_gives_an_empty_writable_store(self, plugin, domoticz):
        store = PluginStore("TestStore", 1)

        assert store.load(plugin) is True
        assert store.writable and len(store) == 0
        assert domoticz.rotated == []

    def test_loads_the_file_and_rotates_its_versions(self, plugin, domoticz):
        write_payload(store_file(plugin))
        store = PluginStore("TestStore", 1)

        assert store.load(plugin) is True
        assert store.get("k") == RECORD
        assert [str(p) for p in domoticz.rotated] == [store_file(plugin)]

    def test_domoticz_copy_used_when_more_recent(self, plugin, domoticz):
        plugin.pluginconf.pluginConf["useDomoticzDb"] = True
        write_payload(store_file(plugin), timestamp=1000.0, records={"k": {"from": "file"}})
        domoticz.config["PluginStore-TestStore"] = {"FormatVersion": 1, "TimeStamp": 2000.0, "Records": {"k": {"from": "domoticz"}}}
        store = PluginStore("TestStore", 1)

        store.load(plugin)

        assert store.get("k") == {"from": "domoticz"}

    def test_file_used_when_more_recent(self, plugin, domoticz):
        plugin.pluginconf.pluginConf["useDomoticzDb"] = True
        write_payload(store_file(plugin), timestamp=3000.0, records={"k": {"from": "file"}})
        domoticz.config["PluginStore-TestStore"] = {"FormatVersion": 1, "TimeStamp": 2000.0, "Records": {"k": {"from": "domoticz"}}}
        store = PluginStore("TestStore", 1)

        store.load(plugin)

        assert store.get("k") == {"from": "file"}

    def test_domoticz_copy_ignored_when_domoticz_db_not_used(self, plugin, domoticz):
        domoticz.config["PluginStore-TestStore"] = {"FormatVersion": 1, "TimeStamp": 2000.0, "Records": {"k": {"from": "domoticz"}}}
        store = PluginStore("TestStore", 1)

        store.load(plugin)

        assert len(store) == 0

    def test_unreadable_file_without_other_copy_is_left_untouched(self, plugin, domoticz):
        with open(store_file(plugin), "w", encoding="utf-8") as handle:
            handle.write("{ not json")
        store = PluginStore("TestStore", 1)

        assert store.load(plugin) is False
        store.set("k", RECORD)
        store.flush(plugin)

        with open(store_file(plugin), encoding="utf-8") as handle:
            assert handle.read() == "{ not json"
        assert plugin.log.errors()

    def test_unreadable_file_with_a_valid_domoticz_copy_loads_it(self, plugin, domoticz):
        plugin.pluginconf.pluginConf["useDomoticzDb"] = True
        with open(store_file(plugin), "w", encoding="utf-8") as handle:
            handle.write("{ not json")
        domoticz.config["PluginStore-TestStore"] = {"FormatVersion": 1, "TimeStamp": 2000.0, "Records": {"k": RECORD}}
        store = PluginStore("TestStore", 1)

        assert store.load(plugin) is True
        assert store.get("k") == RECORD

    def test_invalid_payload_is_rejected(self, plugin, domoticz):
        with open(store_file(plugin), "w", encoding="utf-8") as handle:
            json.dump({"FormatVersion": "1", "Records": []}, handle)

        assert PluginStore("TestStore", 1).load(plugin) is False

    def test_newer_version_is_left_untouched(self, plugin, domoticz):
        write_payload(store_file(plugin), version=2)
        before = read_payload(store_file(plugin))
        store = PluginStore("TestStore", 1)

        assert store.load(plugin) is False
        store.set("other", {})
        store.flush(plugin)

        assert read_payload(store_file(plugin)) == before
        assert any("newer" in e for e in plugin.log.errors())

    def test_older_version_without_upgrade_is_left_untouched(self, plugin, domoticz):
        write_payload(store_file(plugin), version=1)

        assert PluginStore("TestStore", 2).load(plugin) is False

    def test_older_version_is_upgraded_and_saved_in_the_new_format(self, plugin, domoticz):
        write_payload(store_file(plugin), version=1)

        def upgrade(records, from_version):
            assert from_version == 1
            return {key: dict(record, upgraded=True) for key, record in records.items()}

        store = PluginStore("TestStore", 2, upgrade=upgrade)

        assert store.load(plugin) is True
        assert store.get("k")["upgraded"] is True
        store.flush(plugin)
        payload = read_payload(store_file(plugin))
        assert payload["FormatVersion"] == 2 and payload["Records"]["k"]["upgraded"] is True


# ─── Flush ───────────────────────────────────────────────────────────────────

class TestFlush:

    def test_flush_writes_and_reloads(self, plugin, domoticz):
        store = PluginStore("TestStore", 1)
        store.load(plugin)
        store.set("k", RECORD)

        store.flush(plugin)

        payload = read_payload(store_file(plugin))
        assert payload["FormatVersion"] == 1 and payload["Records"] == {"k": RECORD}
        reloaded = PluginStore("TestStore", 1)
        reloaded.load(plugin)
        assert reloaded.get("k") == RECORD

    def test_flush_skipped_when_nothing_changed(self, plugin, domoticz, monkeypatch):
        store = PluginStore("TestStore", 1)
        store.load(plugin)
        store.set("k", RECORD)
        store.flush(plugin)
        writes = []
        monkeypatch.setattr(store._document, "_write_file", lambda p, payload: writes.append(payload) or True)

        store.flush(plugin)
        assert writes == []

        store.flush(plugin, force=True)
        assert len(writes) == 1

    def test_flush_before_load_writes_nothing(self, plugin, domoticz):
        store = PluginStore("TestStore", 1)
        store.set("k", RECORD)

        store.flush(plugin)

        assert not os.path.exists(store_file(plugin))

    @pytest.mark.parametrize("use, store_db, available, expected", [
        (True, True, True, True),
        (True, False, True, False),
        (False, True, True, False),
        (True, True, False, False),
    ])
    def test_domoticz_record_written_only_when_enabled_and_available(self, plugin, domoticz, use, store_db, available, expected):
        plugin.pluginconf.pluginConf.update({"useDomoticzDb": use, "storeDomoticzDb": store_db})
        domoticz.available = available
        store = PluginStore("TestStore", 1)
        store.load(plugin)
        store.set("k", RECORD)

        store.flush(plugin)

        assert ("PluginStore-TestStore" in domoticz.config) is expected
        if expected:
            assert domoticz.config["PluginStore-TestStore"]["Records"] == {"k": RECORD}

    def test_write_failure_is_retried_at_the_next_flush(self, plugin, domoticz, tmp_path):
        store = PluginStore("TestStore", 1)
        store.load(plugin)
        store.set("k", RECORD)
        plugin.pluginconf.pluginConf["pluginData"] = str(tmp_path / "missing")

        store.flush(plugin)
        assert plugin.log.errors()

        (tmp_path / "missing").mkdir()
        store.flush(plugin)
        assert read_payload(store_file(plugin, "TestStore"))["Records"] == {"k": RECORD}


# ─── Logging ─────────────────────────────────────────────────────────────────

def test_records_are_never_logged(plugin, domoticz):
    plugin.pluginconf.pluginConf.update({"useDomoticzDb": True, "storeDomoticzDb": True})
    store = PluginStore("TestStore", 1)
    store.load(plugin)
    store.set("k", RECORD)
    store.flush(plugin)
    PluginStore("TestStore", 1).load(plugin)

    assert SECRET not in plugin.log.text()
