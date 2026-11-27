#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The Zigbee keys never reach the log. All the keys below are made up."""

import importlib
import importlib.util
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from Modules.maskKeys import MASKED_KEY, mask_keys

REPO_ROOT = Path(__file__).resolve().parents[2]
KEY = ":".join(["1f"] * 16)


def logged(log):
    return "\n".join(str(call.args[2]) for call in log.logging.call_args_list)


@pytest.mark.parametrize("key", [KEY, KEY.upper(), "1f" * 16])
def test_key_is_masked(key):
    assert mask_keys(f"Key(key={key}, seq=0)") == f"Key(key={MASKED_KEY}, seq=0)"


def test_every_key_is_masked():
    assert mask_keys({"network_key": KEY, "key_table": [KEY, "1f" * 16]}).count(MASKED_KEY) == 3


@pytest.mark.parametrize("text", [
    "00:11:22:33:44:55:66:77",
    "0011223344556677",
    "PAN ID: 0xAF57, channel 11",
    ":".join(["1f"] * 20),
    "1f" * 20,
    "",
])
def test_anything_else_is_left_alone(text):
    assert mask_keys(text) == text


def test_network_settings_do_not_show_the_key():
    radioStart = importlib.import_module("Classes.ZigpyTransport.radioStart")
    key = SimpleNamespace(key=bytes([0x1F] * 16), seq=3, tx_counter=1234)
    network = SimpleNamespace(
        pan_id=0x1234, extended_pan_id="x", channel=11, channel_mask=[11], nwk_update_id=0, network_key=key,
        tx_power=8, security_level=5, children=[], route_table={},
    )
    transport = SimpleNamespace(log=MagicMock(), app=SimpleNamespace(state=SimpleNamespace(
        network_info=network, network_information=network, node_info=SimpleNamespace(ieee="x", nwk=0))))

    radioStart.display_network_infos(transport)

    text = logged(transport.log)
    assert KEY not in text
    assert f"Network key:           {MASKED_KEY}" in text
    assert "Network key counter:   1234" in text


def test_frame_8015_debug_does_not_show_the_key():
    encoders = importlib.import_module("Classes.ZigpyTransport.plugin_encoders")

    class Info:
        nwk_addresses = {}

        def __str__(self):
            return f"NetworkInfo(network_key=Key(key={KEY}))"

    transport = SimpleNamespace(log=MagicMock())
    encoders.build_plugin_8015_frame_content(transport, Info())

    assert MASKED_KEY in logged(transport.log)
    assert KEY not in logged(transport.log)


def test_backup_debug_does_not_show_the_key_and_the_file_keeps_it(tmp_path):
    # In a subprocess: tests/conftest.py stubs the modules zigpyBackup imports
    if importlib.util.find_spec("zigpy") is None:
        pytest.skip("requires the real zigpy package")
    snippet = textwrap.dedent(f"""
        import sys, types
        from unittest.mock import MagicMock
        d = types.ModuleType("DomoticzEx")
        for n in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
            setattr(d, n, MagicMock())
        sys.modules["DomoticzEx"] = d
        import zigpy.backups, zigpy.state, zigpy.types as t
        from Modules.zigpyBackup import handle_zigpy_backup
        key = zigpy.state.Key(key=t.KeyData([0x1F] * 16))
        backup = zigpy.backups.NetworkBackup(
            network_info=zigpy.state.NetworkInfo(network_key=key), node_info=zigpy.state.NodeInfo())
        plugin = MagicMock(HardwareID=1)
        plugin.pluginconf.pluginConf = {{"pluginData": {str(tmp_path)!r}, "numDeviceListVersion": 1}}
        handle_zigpy_backup(plugin, backup)
        print([str(c.args[2]) for c in plugin.log.logging.call_args_list])
    """)
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr

    assert MASKED_KEY in result.stdout and KEY not in result.stdout
    assert KEY in (tmp_path / "Coordinator-01.backup").read_text()
