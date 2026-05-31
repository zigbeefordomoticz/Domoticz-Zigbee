"""
Tests for Z4D_decoders/z4d_decoder_Remotes.py

Covers Decode8085, Decode8095, Decode80A7 core control-flow paths:
  - Unknown device → handle_unknow_device
  - Non-inDB device → handle_unknow_device
  - inDB device, no model → early return after logging
  - inDB device with model → updLQI / updSQN called
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Remotes"

ADDR = "abcd"
EP   = "01"
CLST = "0006"
LQI  = "ff"

# Decode8085/8095: sqn(2)+ep(2)+cluster(4)+unknown(2)+srcAddr(4)+cmd(2)
def _msg85(addr=ADDR, cmd="01"):
    return "01" + EP + CLST + "00" + addr + cmd

# Decode80A7: sqn(2)+ep(2)+cluster(4)+cmd(2)+dir(2)+unknown(6)+srcAddr(4)
def _msg80a7(addr=ADDR):
    return "01" + EP + CLST + "01" + "00" + "000000" + addr


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


class TestDecode8085:

    def test_unknown_device_calls_handle_unknow(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=False)
        handle = MagicMock()
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode8085(plugin, {}, _msg85(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_non_indb_device_calls_handle_unknow(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Status": "joining"}}
        sanity = MagicMock(return_value=False)
        handle = MagicMock()
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode8085(plugin, {}, _msg85(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_indb_no_model_logs_and_returns(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Status": "inDB", "Model": None}}
        monkeypatch.setattr(mod, "check_duplicate_sqn", MagicMock(return_value=False))
        upd = MagicMock()
        monkeypatch.setattr(mod, "updSQN", upd)
        mod.Decode8085(plugin, {}, _msg85(), LQI)
        assert any("No Model" in str(c) for c in plugin.log.logging.call_args_list)

    def test_indb_with_model_calls_upd_sqn(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {
            "Status": "inDB", "Model": "TRADFRI remote control",
        }}
        monkeypatch.setattr(mod, "check_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "get_deviceconf_parameter_value", MagicMock(return_value=None))
        upd = MagicMock()
        monkeypatch.setattr(mod, "updSQN", upd)
        mod.Decode8085(plugin, {}, _msg85(), LQI)
        upd.assert_called_once()

    def test_duplicate_sqn_returns_early(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Status": "inDB", "Model": "SomeRemote"}}
        monkeypatch.setattr(mod, "check_duplicate_sqn", MagicMock(return_value=True))
        upd = MagicMock()
        monkeypatch.setattr(mod, "updSQN", upd)
        mod.Decode8085(plugin, {}, _msg85(), LQI)
        upd.assert_not_called()


class TestDecode8095:

    def test_unknown_device_calls_handle_unknow(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=False)
        handle = MagicMock()
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode8095(plugin, {}, _msg85(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_indb_none_model_returns_early(self, mod, plugin, monkeypatch):
        # In Decode8095 updSQN is called *before* the model check, so it is
        # always invoked for a valid inDB device.  The early return when model
        # is None happens afterwards — verify by checking that
        # get_deviceconf_parameter_value (called only past the model guard) is
        # NOT reached.
        plugin.ListOfDevices = {ADDR: {"Status": "inDB", "Model": None}}
        monkeypatch.setattr(mod, "check_duplicate_sqn", MagicMock(return_value=False))
        gcp = MagicMock()
        monkeypatch.setattr(mod, "get_deviceconf_parameter_value", gcp)
        mod.Decode8095(plugin, {}, _msg85(), LQI)
        gcp.assert_not_called()

    def test_indb_with_model_calls_upd_sqn(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {
            "Status": "inDB", "Model": "WB01",
        }}
        monkeypatch.setattr(mod, "check_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "get_deviceconf_parameter_value", MagicMock(return_value=None))
        upd = MagicMock()
        monkeypatch.setattr(mod, "updSQN", upd)
        mod.Decode8095(plugin, {}, _msg85(), LQI)
        upd.assert_called_once()


class TestDecode80A7:

    def test_indb_unknown_model_stores_cluster_data(self, mod, plugin, monkeypatch):
        """Non-TRADFRI inDB device falls to else → stores Cmd in Ep cluster."""
        plugin.ListOfDevices = {ADDR: {
            "Status": "inDB",
            "Model": "UnknownRemote",
            "Ep": {EP: {CLST: {"0000": ""}}},
        }}
        monkeypatch.setattr(mod, "check_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "get_deviceconf_parameter_value", MagicMock(return_value=None))
        monkeypatch.setattr(mod, "missing_scene_mapping", MagicMock())
        mod.Decode80A7(plugin, {}, _msg80a7(), LQI)
        assert plugin.ListOfDevices[ADDR]["Ep"][EP][CLST]["0000"] != ""
