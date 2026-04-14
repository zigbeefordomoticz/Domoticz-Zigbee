"""
Tests for Z4D_decoders/z4d_decoder_Read_Attribute_Request.py

Decode0100 — read attribute request; dispatches to model-specific handlers
or responds with a default value for standard attributes.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Read_Attribute_Request"

LQI  = "ff"
ADDR = "abcd"
EP   = "01"

# Layout: sqn(2)+srcAddr(4)+srcEp(2)+dstEp(2)+clusterId(4)+dir(2)+
#         manufSpec(2)+manufCode(4)+nbAttr(2)+attributes(4 each)
def _msg(addr=ADDR, cluster="0000", attr="0000", nb="01", manuf_name=""):
    return (
        "01"      # sqn
        + addr    # srcAddr
        + EP      # srcEp
        + EP      # dstEp
        + cluster
        + "00"    # direction
        + "00"    # manufSpec
        + "0000"  # manufCode
        + nb
        + attr
    )


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


class TestDecode0100:

    def test_unknown_device_calls_handle_unknow(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=False)
        handle = MagicMock()
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode0100(plugin, {}, _msg(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_livolo_model_calls_livolo_handler(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Model": "TI0001", "Manufacturer Name": ""}}
        livolo = MagicMock()
        monkeypatch.setattr(mod, "livolo_read_attribute_request", livolo)
        mod.Decode0100(plugin, {}, _msg(addr=ADDR), LQI)
        livolo.assert_called_once()

    def test_basic_cluster_attr_0000_calls_read_attr_response(self, mod, plugin, monkeypatch):
        """Cluster 0000 / attribute 0000 → read_attribute_response called."""
        plugin.ListOfDevices = {ADDR: {"Model": "SomeModel", "Manufacturer Name": "",
                                       "Manufacturer": ""}}
        rar = MagicMock()
        monkeypatch.setattr(mod, "read_attribute_response", rar)
        mod.Decode0100(plugin, {}, _msg(cluster="0000", attr="0000"), LQI)
        rar.assert_called_once()

    def test_other_cluster_logs(self, mod, plugin, monkeypatch):
        """Unknown cluster/attribute → logs Read Attribute Request."""
        plugin.ListOfDevices = {ADDR: {"Model": "SomeModel", "Manufacturer Name": "",
                                       "Manufacturer": ""}}
        monkeypatch.setattr(mod, "read_attribute_response", MagicMock())
        plugin.log.logging.reset_mock()
        mod.Decode0100(plugin, {}, _msg(cluster="ffff", attr="ffff"), LQI)
        assert plugin.log.logging.called

    def test_upd_lqi_called_even_for_unknown_device(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "handle_unknow_device", MagicMock())
        mod.Decode0100(plugin, {}, _msg(), LQI)
        upd.assert_called()
