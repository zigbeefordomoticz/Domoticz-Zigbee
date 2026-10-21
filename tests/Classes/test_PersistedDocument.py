#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/PersistedDocument.py, the persistence engine.

Covers what PluginStore does not exercise (tests/Classes/test_PluginStore.py
covers load/flush rules through the store):
  EnvelopeCodec   – valid / invalid payloads, content type
  options         – default content, read / write record policies, versioned
                    backups off, caller log callable (no plugin logger),
                    upgraded flag, save refused when not writable
  Domoticz record – round trip through the real setConfigItem() /
                    getConfigItem(): the storage layer stamps its own "Version"
                    on the record, the document version survives as
                    "FormatVersion" (subprocess, real modules)
"""

import json
import os
import subprocess  # nosec B404
import sys
import textwrap
import types
from pathlib import Path

import pytest

import Classes.PersistedDocument as persisted_document_module
from Classes.PersistedDocument import EnvelopeCodec, PersistedDocument

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def domoticz(monkeypatch):
    state = types.SimpleNamespace(config={}, rotated=[])

    def set_config_item(Key=None, Attribute="", Value=None):
        record = json.loads(json.dumps(Value))
        record["Version"] = 2
        state.config[Key] = record
        return state.config

    monkeypatch.setattr(persisted_document_module, "getConfigItem", lambda Key=None, Attribute="", Default=None: state.config.get(Key, {}))
    monkeypatch.setattr(persisted_document_module, "setConfigItem", set_config_item)
    monkeypatch.setattr(persisted_document_module, "rotate_file_versions", lambda path, nb: state.rotated.append(path))
    return state


@pytest.fixture
def plugin(tmp_path):
    # No plugin logger: documents log through the callable they are given
    return types.SimpleNamespace(pluginconf=types.SimpleNamespace(pluginConf={"pluginData": str(tmp_path), "numDeviceListVersion": 3}))


def make_document(tmp_path, messages, **options):
    options.setdefault("read_record", lambda plugin: True)
    options.setdefault("write_record", lambda plugin: True)
    return PersistedDocument(
        "TestDoc", 1,
        file_path=lambda plugin: tmp_path / "TestDoc.json",
        config_key="TestDoc",
        codec=EnvelopeCodec("Content", content_type=list),
        log=lambda plugin, level, message: messages.append((level, message)),
        **options,
    )


# ─── EnvelopeCodec ───────────────────────────────────────────────────────────

class TestEnvelopeCodec:

    def test_round_trip(self):
        codec = EnvelopeCodec("Records")
        assert codec.decode(codec.encode(3, 12.5, {"k": 1})) == (3, 12.5, {"k": 1})

    @pytest.mark.parametrize("payload", [
        None,
        [],
        {"FormatVersion": "1", "TimeStamp": 1.0, "Records": {}},
        {"FormatVersion": 1, "TimeStamp": "now", "Records": {}},
        {"FormatVersion": 1, "TimeStamp": 1.0},
        {"FormatVersion": 1, "TimeStamp": 1.0, "Records": []},
        # The storage layer's own key is not the document version
        {"Version": 2, "TimeStamp": 1.0, "Records": {}},
    ])
    def test_invalid_payloads(self, payload):
        assert EnvelopeCodec("Records").decode(payload) is None

    def test_content_type(self):
        codec = EnvelopeCodec("Content", content_type=list)
        assert codec.decode(codec.encode(1, 1.0, [1, 2])) == (1, 1.0, [1, 2])
        assert codec.decode(codec.encode(1, 1.0, {"a": 1})) is None


# ─── Options ─────────────────────────────────────────────────────────────────

class TestOptions:

    def test_default_content_when_nothing_stored(self, plugin, domoticz, tmp_path):
        messages = []
        document = make_document(tmp_path, messages, default=list)

        assert document.load(plugin) == []
        assert document.writable

    def test_record_not_read_when_policy_says_no(self, plugin, domoticz, tmp_path):
        messages = []
        domoticz.config["TestDoc"] = {"FormatVersion": 1, "TimeStamp": 1.0, "Content": [1]}
        document = make_document(tmp_path, messages, read_record=lambda plugin: False, default=list)

        assert document.load(plugin) == []

    def test_record_not_written_when_policy_says_no(self, plugin, domoticz, tmp_path):
        messages = []
        document = make_document(tmp_path, messages, write_record=lambda plugin: False, default=list)
        document.load(plugin)

        assert document.save(plugin, [1])
        assert "TestDoc" not in domoticz.config
        assert (tmp_path / "TestDoc.json").is_file()

    def test_versioned_backups_can_be_turned_off(self, plugin, domoticz, tmp_path):
        messages = []
        (tmp_path / "TestDoc.json").write_text(json.dumps({"FormatVersion": 1, "TimeStamp": 1.0, "Content": [1]}))

        make_document(tmp_path, messages, rotate_versions=False).load(plugin)
        assert domoticz.rotated == []

        make_document(tmp_path, messages).load(plugin)
        assert len(domoticz.rotated) == 1

    def test_messages_go_to_the_log_callable(self, plugin, domoticz, tmp_path):
        messages = []
        (tmp_path / "TestDoc.json").write_text("{ not json")

        assert make_document(tmp_path, messages).load(plugin) is None
        assert messages and messages[0][0] == "Error"

    def test_upgraded_flag(self, plugin, domoticz, tmp_path):
        messages = []
        (tmp_path / "TestDoc.json").write_text(json.dumps({"FormatVersion": 1, "TimeStamp": 1.0, "Content": [1]}))
        document = PersistedDocument(
            "TestDoc", 2, file_path=lambda plugin: tmp_path / "TestDoc.json", config_key="TestDoc",
            codec=EnvelopeCodec("Content", content_type=list), upgrade=lambda content, version: content + [version],
            log=lambda plugin, level, message: messages.append((level, message)),
            read_record=lambda plugin: False, write_record=lambda plugin: False,
        )

        assert document.load(plugin) == [1, 1]
        assert document.upgraded and document.writable

    def test_save_refused_when_not_writable(self, plugin, domoticz, tmp_path):
        messages = []
        (tmp_path / "TestDoc.json").write_text(json.dumps({"FormatVersion": 9, "TimeStamp": 1.0, "Content": [1]}))
        document = make_document(tmp_path, messages)

        assert document.load(plugin) is None
        assert document.save(plugin, [2]) is False
        assert json.loads((tmp_path / "TestDoc.json").read_text())["FormatVersion"] == 9


# ─── Real Domoticz storage layer ─────────────────────────────────────────────

ROUND_TRIP = textwrap.dedent(
    """
    import json, os, sys, tempfile, types
    from pathlib import Path
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

    import Modules.tools  # noqa: F401  (import order as in the plugin)
    from Classes.PersistedDocument import EnvelopeCodec, PersistedDocument

    with tempfile.TemporaryDirectory() as tmp:
        plugin = types.SimpleNamespace(pluginconf=types.SimpleNamespace(pluginConf={"pluginData": tmp, "numDeviceListVersion": 3}))
        messages = []

        def make():
            return PersistedDocument(
                "TestDoc", 3, file_path=lambda p: Path(tmp) / "TestDoc.json", config_key="TestDoc",
                codec=EnvelopeCodec("Records"), log=lambda p, level, message: messages.append((level, message)),
                read_record=lambda p: True, write_record=lambda p: True,
            )

        document = make()
        assert document.load(plugin) == {}
        assert document.save(plugin, {"k": {"secret": "00112233"}})

        # The record holds the content compressed, and the storage layer's own Version
        stored = _config_store["TestDoc"]
        assert stored["FormatVersion"] == 3 and isinstance(stored["Records"], str) and "Version" in stored

        # Only the Domoticz copy left: it is read back with its document version
        os.remove(os.path.join(tmp, "TestDoc.json"))
        reloaded = make()
        assert reloaded.load(plugin) == {"k": {"secret": "00112233"}}, messages
        assert reloaded.writable
        assert not [m for level, m in messages if level == "Error"], messages
        assert "00112233" not in " ".join(m for _, m in messages)
    print("OK")
    """
)


def test_round_trip_through_the_real_domoticz_storage_layer():
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", ROUND_TRIP],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode == 0 and "OK" in result.stdout, "stdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr)
