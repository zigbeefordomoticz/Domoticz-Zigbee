"""
Tests for Z4D_decoders/z4d_decoder_Attr_Discovery_Extended_Rsp.py

Covers Decode8141:
  - Short message (≤10 chars) logs but doesn't update ListOfDevices
  - Long message with unknown device calls sanity check / handle_unknow
  - Known device: attribute info stored with correct flags
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Attr_Discovery_Extended_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI  = "ff"
ADDR = "abcd"
EP   = "01"
CLST = "0006"
ATTR = "0000"

# Short message (≤10 chars): just basic fields
SHORT_MSG = "00" + "20" + ATTR + "01"  # 10 chars

# Long message (>10 chars): complete with address info
def _make_long(complete="01", attr_type="20", attr_id=ATTR, flag="01",
               addr=ADDR, ep=EP, cluster=CLST):
    return complete + attr_type + attr_id + flag + addr + ep + cluster


class TestDecode8141:

    def test_short_msg_logs_but_no_device_update(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8141(plugin, {}, SHORT_MSG, LQI)
        assert plugin.ListOfDevices == {}

    def test_long_msg_unknown_device_calls_sanity_check(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        mod.Decode8141(plugin, {}, _make_long(), LQI)
        sanity.assert_called_once_with(plugin, ADDR)

    def test_long_msg_unknown_device_handle_unknown_when_sanity_fails(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=False))
        handle = MagicMock()
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode8141(plugin, {}, _make_long(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_known_device_stores_attribute_type(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}
        mod.Decode8141(plugin, {}, _make_long(attr_type="20", flag="0f"), LQI)
        info = (plugin.ListOfDevices[ADDR]
                .get("Attributes List Extended", {})
                .get("Ep", {}).get(EP, {}).get(CLST, {}).get(ATTR, {}))
        assert info.get("Type") == "20"

    def test_known_device_stores_read_flag(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}
        # flag "01" → Read=1, Write=0, Reportable=0
        mod.Decode8141(plugin, {}, _make_long(flag="01"), LQI)
        info = (plugin.ListOfDevices[ADDR]
                .get("Attributes List Extended", {})
                .get("Ep", {}).get(EP, {}).get(CLST, {}).get(ATTR, {}))
        assert info.get("Read") == 1

    def test_known_device_stores_write_flag(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}
        # flag "02" → Read=0, Write=1
        mod.Decode8141(plugin, {}, _make_long(flag="02"), LQI)
        info = (plugin.ListOfDevices[ADDR]
                .get("Attributes List Extended", {})
                .get("Ep", {}).get(EP, {}).get(CLST, {}).get(ATTR, {}))
        assert info.get("Write") == 1
