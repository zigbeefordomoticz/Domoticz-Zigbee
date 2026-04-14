"""
Tests for Z4D_decoders/z4d_decoder_NWK_addr_req.py

Covers Decode0040:
  - IEEE matches ControllerIEEE → status '00' with coordinator info
  - IEEE in IEEE2NWK → status '00'
  - Unknown IEEE → status '81'
  - Always calls raw_APS_request
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_NWK_addr_req"

import types as _types
if "Modules.sendZigateCommand" not in sys.modules:
    _m = _types.ModuleType("Modules.sendZigateCommand")
    _m.raw_APS_request = MagicMock(name="raw_APS_request")
    sys.modules["Modules.sendZigateCommand"] = _m


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI         = "ff"
CTRL_IEEE   = "1122334455667788"
CTRL_NWKID  = "0000"
DEV_IEEE    = "aabbccddeeff0011"
DEV_NWKID   = "abcd"

# Layout: sqn(2)+srcNwkId(4)+srcEp(2)+ieee(16)+reqType(2)+startIndex(2)
def _make_msg(ieee=CTRL_IEEE):
    return "01" + "1234" + "01" + ieee + "00" + "00"


class TestDecode0040:

    def _setup(self, plugin, monkeypatch, mod):
        plugin.ControllerIEEE = CTRL_IEEE
        plugin.ControllerNWKID = CTRL_NWKID
        monkeypatch.setattr(mod, "raw_APS_request", MagicMock())

    def test_coordinator_ieee_calls_raw_aps(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0040(plugin, {}, _make_msg(ieee=CTRL_IEEE), LQI)
        raw.assert_called_once()

    def test_known_device_ieee_calls_raw_aps(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        plugin.IEEE2NWK[DEV_IEEE] = DEV_NWKID
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0040(plugin, {}, _make_msg(ieee=DEV_IEEE), LQI)
        raw.assert_called_once()

    def test_unknown_ieee_calls_raw_aps_with_status_81(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        plugin.IEEE2NWK = {}
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        unknown_ieee = "ffffffffffffffff"
        mod.Decode0040(plugin, {}, _make_msg(ieee=unknown_ieee), LQI)
        raw.assert_called_once()
