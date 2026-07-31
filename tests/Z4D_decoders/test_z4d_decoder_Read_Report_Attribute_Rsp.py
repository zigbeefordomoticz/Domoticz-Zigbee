"""
Tests for Z4D_decoders/z4d_decoder_Read_Report_Attribute_Rsp.py

Decode8102 — attribute report; updates timestamp/LQI and delegates to
scan_attribute_reponse (which calls ReadCluster for known devices).
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Read_Report_Attribute_Rsp"

LQI  = "ff"
ADDR = "abcd"
EP   = "01"

# sqn(2)+addr(4)+ep(2)+cluster(4)+attrId(4)+status(2)+type(2)+size(4)+data(0)
# = 24 chars minimum; status "00" means valid attribute
def _msg(cluster="0006", attr="0000", status="86"):
    # status != "00" → no type/size/data needed
    return "01" + ADDR + EP + cluster + attr + status + "0000"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


class TestDecode8102:

    def test_calls_timestamped(self, mod, plugin, monkeypatch):
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        # Stub scan_attribute_reponse to avoid calling into debug_LQI
        # which requires ListOfDevices[addr]["LQI"] to be set.
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8102(plugin, {}, _msg(), LQI)
        ts.assert_called_once()

    def test_calls_upd_lqi(self, mod, plugin, monkeypatch):
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8102(plugin, {}, _msg(), LQI)
        upd.assert_called()

    def test_non_pluzzy_does_not_call_pluzzy(self, mod, plugin, monkeypatch):
        plugin.PluzzyFirmware = False
        pluzzy = MagicMock()
        monkeypatch.setattr(mod, "pluzzyDecode8102", pluzzy)
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8102(plugin, {}, _msg(), LQI)
        pluzzy.assert_not_called()

    def test_pluzzy_firmware_calls_pluzzy(self, mod, plugin, monkeypatch):
        plugin.PluzzyFirmware = True
        pluzzy = MagicMock()
        monkeypatch.setattr(mod, "pluzzyDecode8102", pluzzy)
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8102(plugin, {}, _msg(), LQI)
        pluzzy.assert_called_once()

    def test_logs_debug(self, mod, plugin, monkeypatch):
        plugin.PluzzyFirmware = False
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8102(plugin, {}, _msg(), LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)
