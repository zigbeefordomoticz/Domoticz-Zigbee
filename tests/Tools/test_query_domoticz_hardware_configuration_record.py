#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tools/query_domoticz_hardware_configuration_record.py

Coverage:
  - decode_b64_payload          – V1 (JSON), V1 (Python repr), V2 (zlib+JSON), error paths
  - decode_plugin_config_entry  – decodes b64-* keys, passes through non-b64 keys, no Version
  - format_timestamps           – dict, list, nested, non-timestamp keys
  - extract_json_entry          – dot-notation hit, missing key
  - extract_configuration       – missing hardware ID, empty config, invalid JSON, full flow
"""

import ast
import base64
import json
import sqlite3
import zlib
import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import helpers – the script lives in Tools/ which is not a package
# ---------------------------------------------------------------------------
import importlib.util, os

SCRIPT_PATH = Path(__file__).parents[2] / "Tools" / "query_domoticz_hardware_configuration_record.py"

spec = importlib.util.spec_from_file_location("query_hw_conf", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

decode_b64_payload        = mod.decode_b64_payload
decode_plugin_config_entry = mod.decode_plugin_config_entry
format_timestamps         = mod.format_timestamps
extract_json_entry        = mod.extract_json_entry
extract_configuration     = mod.extract_configuration


# ---------------------------------------------------------------------------
# decode_b64_payload
# ---------------------------------------------------------------------------

class TestDecodeB64Payload:
    def _b64(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    def test_v1_plain_json(self):
        payload = json.dumps({"key": "value"}).encode()
        result = decode_b64_payload(self._b64(payload), version=1)
        assert result == {"key": "value"}

    def test_v1_python_repr(self):
        # Python dict repr that is NOT valid JSON but is valid ast.literal_eval
        data = {"nwk": "1234", "ep": [1, 2]}
        payload = repr(data).encode()
        result = decode_b64_payload(self._b64(payload), version=1)
        assert result == data

    def test_v2_zlib_json(self):
        original = {"devices": [1, 2, 3]}
        compressed = zlib.compress(json.dumps(original).encode())
        result = decode_b64_payload(self._b64(compressed), version=2)
        assert result == original

    def test_invalid_base64_raises(self):
        with pytest.raises(ValueError, match="base64 decode failed"):
            decode_b64_payload("!!!not_b64!!!", version=1)

    def test_v2_bad_zlib_raises(self):
        # Valid base64 but not zlib-compressed
        bad = base64.b64encode(b"this is not compressed").decode()
        with pytest.raises(ValueError, match="zlib decompress failed"):
            decode_b64_payload(bad, version=2)

    def test_v1_not_json_not_literal_raises(self):
        # Valid base64 but content is neither JSON nor Python literal
        payload = base64.b64encode(b"def foo(): pass").decode()
        with pytest.raises(ValueError, match="neither JSON nor Python literal"):
            decode_b64_payload(payload, version=1)


# ---------------------------------------------------------------------------
# decode_plugin_config_entry
# ---------------------------------------------------------------------------

class TestDecodePluginConfigEntry:
    def _make_entry(self, version, **extra):
        return {"Version": version, "TimeStamp": 1234567890, **extra}

    def test_non_b64_keys_pass_through(self):
        entry = self._make_entry(1, SomeKey="hello")
        result = decode_plugin_config_entry(entry)
        assert result["SomeKey"] == "hello"
        assert result["Version"] == 1

    def test_b64_key_v2_decoded(self):
        data = {"list": [1, 2]}
        compressed = zlib.compress(json.dumps(data).encode())
        encoded = base64.b64encode(compressed).decode()
        entry = self._make_entry(2, **{"b64-devices": encoded})
        result = decode_plugin_config_entry(entry)
        assert result["b64-devices"] == data

    def test_b64_decode_error_gives_error_string(self):
        entry = self._make_entry(1, **{"b64-broken": "not_valid_base64!!!"})
        result = decode_plugin_config_entry(entry)
        assert "<decode error:" in result["b64-broken"]

    def test_no_version_key_returns_entry_unchanged(self):
        entry = {"NoVersion": True}
        assert decode_plugin_config_entry(entry) == entry

    def test_non_dict_returns_unchanged(self):
        assert decode_plugin_config_entry("plain string") == "plain string"


# ---------------------------------------------------------------------------
# format_timestamps
# ---------------------------------------------------------------------------

class TestFormatTimestamps:
    def test_numeric_timestamp_formatted(self):
        result = format_timestamps({"timestamp": 0})
        assert "1970" in result["timestamp"]

    def test_non_timestamp_key_unchanged(self):
        result = format_timestamps({"value": 42})
        assert result["value"] == 42

    def test_nested_dict(self):
        result = format_timestamps({"outer": {"timestamp": 0}})
        assert "1970" in result["outer"]["timestamp"]

    def test_list_recursed(self):
        result = format_timestamps([{"timestamp": 0}])
        assert "1970" in result[0]["timestamp"]

    def test_plain_value_returned(self):
        assert format_timestamps("hello") == "hello"


# ---------------------------------------------------------------------------
# extract_json_entry
# ---------------------------------------------------------------------------

class TestExtractJsonEntry:
    def test_single_key(self):
        data = {"devices": {"a": 1}}
        assert extract_json_entry(data, "devices") == {"a": 1}

    def test_dot_notation(self):
        data = {"level1": {"level2": "found"}}
        assert extract_json_entry(data, "level1.level2") == "found"

    def test_missing_key_returns_none(self, capsys):
        result = extract_json_entry({"a": 1}, "b")
        assert result is None
        assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# extract_configuration  (uses a real in-memory SQLite DB)
# ---------------------------------------------------------------------------

class TestExtractConfiguration:
    def _make_db(self, tmp_path, hardware_id=1, config_value=None):
        db = tmp_path / "domoticz.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE Hardware (ID INTEGER PRIMARY KEY, Configuration TEXT)")
        conn.execute("INSERT INTO Hardware VALUES (?, ?)", (hardware_id, config_value))
        conn.commit()
        conn.close()
        return db

    def test_missing_hardware_id(self, tmp_path, capsys):
        db = self._make_db(tmp_path, hardware_id=1, config_value='{"k": "v"}')
        extract_configuration(db, hardware_id=99, entry=None, decode_b64=False)
        assert "No Hardware entry" in capsys.readouterr().out

    def test_empty_config(self, tmp_path, capsys):
        db = self._make_db(tmp_path, config_value=None)
        extract_configuration(db, hardware_id=1, entry=None, decode_b64=False)
        assert "empty" in capsys.readouterr().out

    def test_invalid_json_config(self, tmp_path, capsys):
        db = self._make_db(tmp_path, config_value="not json")
        extract_configuration(db, hardware_id=1, entry=None, decode_b64=False)
        assert "not valid JSON" in capsys.readouterr().out

    def test_valid_config_printed(self, tmp_path, capsys):
        cfg = json.dumps({"Devices": {"Version": 1, "TimeStamp": 0}})
        db = self._make_db(tmp_path, config_value=cfg)
        extract_configuration(db, hardware_id=1, entry=None, decode_b64=False)
        out = capsys.readouterr().out
        assert "Devices" in out

    def test_entry_extraction(self, tmp_path, capsys):
        cfg = json.dumps({"Section": {"inner": "value"}})
        db = self._make_db(tmp_path, config_value=cfg)
        extract_configuration(db, hardware_id=1, entry="Section.inner", decode_b64=False)
        assert "value" in capsys.readouterr().out

    def test_decode_b64_called(self, tmp_path, capsys):
        data = {"x": 1}
        compressed = zlib.compress(json.dumps(data).encode())
        encoded = base64.b64encode(compressed).decode()
        cfg = json.dumps({"Entry": {"Version": 2, "b64-payload": encoded}})
        db = self._make_db(tmp_path, config_value=cfg)
        extract_configuration(db, hardware_id=1, entry=None, decode_b64=True)
        out = capsys.readouterr().out
        assert '"x"' in out or "x" in out
