"""
tests/Tools/test_query_hardware_configuration_record.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tools/query_domoticz_hardware_configuration_record.py against what the plugin stores
in the Hardware table. Records are encoded as prepare_dict_for_storage does.

Run with:
    python -m pytest tests/Tools/test_query_hardware_configuration_record.py -v
"""

import base64
import importlib.util
import json
import sqlite3
import zlib
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "Tools" / "query_domoticz_hardware_configuration_record.py"
SCENES = {"0002": {"scenes": {"01": {
    "name": "Cinéma", "createdAt": 1793808000, "updatedAt": 1793808100, "lastRecalled": None,
    "members": {"0017880102a3b4c5-0b": {"status": "synced", "lastCheck": 1793808010, "snapshot": {"onOff": 1, "level": 180}}},
}}}}


def encoded(content):
    return base64.b64encode(zlib.compress(json.dumps(content, ensure_ascii=False).encode("utf-8"))).decode("ascii")


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("query_hardware_configuration_record", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "domoticz.db"
    configuration = {
        "PluginStore-Z4D_Scenes": {"FormatVersion": 1, "TimeStamp": 1793808000.5, "Records": encoded(SCENES), "Version": 2},
        "ListOfDevices": {"Version": 2, "TimeStamp": 1793808000, "b64-devicelist": encoded({"8c11": {"Model": "LCT015"}})},
        "Note": "kept as it is",
    }
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE Hardware (ID INTEGER, Configuration TEXT)")
    connection.execute("INSERT INTO Hardware VALUES (1, ?)", (json.dumps(configuration),))
    connection.commit()
    connection.close()
    return path


def run(tool, capsys, database, entry=None):
    tool.extract_configuration(database, 1, entry, True)
    return json.loads(capsys.readouterr().out)


def test_a_store_record_is_decoded(tool, capsys, database):
    assert "Cinéma" in json.dumps(run(tool, capsys, database)["PluginStore-Z4D_Scenes"]["Records"], ensure_ascii=False)


def test_a_path_reaches_inside_a_store(tool, capsys, database):
    path = "PluginStore-Z4D_Scenes.Records.0002.scenes.01.members.0017880102a3b4c5-0b.snapshot"
    assert run(tool, capsys, database, path) == {"onOff": 1, "level": 180}


def test_the_dates_of_a_scene_are_readable(tool, capsys, database):
    scene = run(tool, capsys, database, "PluginStore-Z4D_Scenes.Records.0002.scenes.01")
    assert scene["createdAt"].startswith("1793808000 (2026-")
    assert scene["members"]["0017880102a3b4c5-0b"]["lastCheck"].startswith("1793808010 (2026-")
    assert scene["lastRecalled"] is None


def test_other_records_decode_as_before(tool, capsys, database):
    decoded = run(tool, capsys, database)
    assert decoded["ListOfDevices"]["b64-devicelist"] == {"8c11": {"Model": "LCT015"}}
    assert decoded["Note"] == "kept as it is"


def test_a_broken_record_is_reported_and_the_rest_still_decodes(tool):
    entry = tool.decode_plugin_config_entry({"Version": 2, "FormatVersion": 1, "TimeStamp": 1, "Records": "not base64 !"})
    assert entry["Records"].startswith("<decode error")
