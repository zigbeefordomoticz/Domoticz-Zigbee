"""
Tests for Z4D_decoders/z4d_decoder_Attr_Discovery_Rsp.py

Covers:
  Decode8140
    - f7 prefix → routes to zigpy_Decode8140
    - Early termination for complete=01/type=00/attr=0000
    - Short payload (≤8) returns early
    - Unknown device calls zigpy_plugin_sanity_check + handle_unknow_device
    - Known device: attribute stored in Attributes List
    - Incomplete response calls getListofAttribute for next batch
  zigpy_Decode8140
    - Stores attributes in Attributes List
    - Calls getListofAttribute when MsgComplete != '01'
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Attr_Discovery_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI  = "80"
ADDR = "abcd"
EP   = "01"
CLST = "0006"
ATTR = "0000"
TYPE = "20"


def _make_8140(complete="00", attr_type=TYPE, attr_id=ATTR,
               addr=ADDR, ep=EP, cluster=CLST):
    """Standard Decode8140 message (> 8 chars, non-f7)."""
    return complete + attr_type + attr_id + addr + ep + cluster


def _make_8140_zigpy(complete="00", addr=ADDR, ep=EP, cluster=CLST,
                     attributes=(("0000", "20"),)):
    """zigpy-style message (f7 prefix)."""
    prefix = "f7"
    body = complete + addr + ep + cluster
    for attr_id, attr_type in attributes:
        body += attr_id + attr_type
    return prefix + body


# ─── Decode8140 ───────────────────────────────────────────────────────────────

class TestDecode8140:

    def test_f7_prefix_calls_zigpy_decode(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Attributes List": {"Ep": {}}}
        zigpy_fn = MagicMock()
        monkeypatch.setattr(mod, "zigpy_Decode8140", zigpy_fn)
        mod.Decode8140(plugin, {}, _make_8140_zigpy(), LQI)
        zigpy_fn.assert_called_once()

    def test_early_termination_01_00_0000(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=True))
        monkeypatch.setattr(mod, "getListofAttribute", MagicMock())
        mod.Decode8140(plugin, {}, "01" + "00" + "0000", LQI)
        # Should return early without looking up device
        assert not any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_short_payload_returns_early(self, mod, plugin):
        msg = "00" + "20" + "0000"  # exactly 8 chars
        mod.Decode8140(plugin, {}, msg, LQI)

    def test_unknown_device_calls_sanity_check(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        mod.Decode8140(plugin, {}, _make_8140(), LQI)
        sanity.assert_called_once_with(plugin, ADDR)

    def test_unknown_device_calls_handle_unknown_when_sanity_fails(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=False))
        handle = MagicMock()
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode8140(plugin, {}, _make_8140(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_known_device_stores_attribute(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}
        monkeypatch.setattr(mod, "getListofAttribute", MagicMock())
        mod.Decode8140(plugin, {}, _make_8140(), LQI)
        attrs = plugin.ListOfDevices[ADDR]["Attributes List"]["Ep"][EP][CLST]
        assert ATTR in attrs
        assert attrs[ATTR] == TYPE

    def test_incomplete_response_calls_getlistofattribute(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}
        get_list = MagicMock()
        monkeypatch.setattr(mod, "getListofAttribute", get_list)
        mod.Decode8140(plugin, {}, _make_8140(complete="00"), LQI)
        get_list.assert_called_once()

    def test_complete_response_does_not_call_getlistofattribute(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}
        get_list = MagicMock()
        monkeypatch.setattr(mod, "getListofAttribute", get_list)
        mod.Decode8140(plugin, {}, _make_8140(complete="01"), LQI)
        get_list.assert_not_called()


# ─── zigpy_Decode8140 ─────────────────────────────────────────────────────────

class TestZigpyDecode8140:

    def test_stores_attribute(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Attributes List": {"Ep": {}}}
        monkeypatch.setattr(mod, "getListofAttribute", MagicMock())
        body = "01" + ADDR + EP + CLST + "0001" + "20"
        mod.zigpy_Decode8140(plugin, {}, body, LQI)
        assert "0001" in plugin.ListOfDevices[ADDR]["Attributes List"]["Ep"][EP][CLST]

    def test_incomplete_calls_getlistofattribute(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Attributes List": {"Ep": {}}}
        get_list = MagicMock()
        monkeypatch.setattr(mod, "getListofAttribute", get_list)
        body = "00" + ADDR + EP + CLST + "0001" + "20"
        mod.zigpy_Decode8140(plugin, {}, body, LQI)
        get_list.assert_called_once()
