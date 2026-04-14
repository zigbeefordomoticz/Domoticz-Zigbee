"""
Tests for Z4D_decoders/z4d_decoder_IEEE_addr_req.py

Covers Decode0041:
  - nwkid matches ControllerNWKID → status '00' with coordinator IEEE
  - nwkid in ListOfDevices → status '00' with device IEEE
  - Unknown nwkid → status '81'
  - Always calls raw_APS_request
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_IEEE_addr_req"

import types as _types
if "Modules.sendZigateCommand" not in sys.modules:
    _m = _types.ModuleType("Modules.sendZigateCommand")
    _m.raw_APS_request = MagicMock(name="raw_APS_request")
    sys.modules["Modules.sendZigateCommand"] = _m


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI  = "ff"
CTRL_NWKID = "0000"
CTRL_IEEE  = "1122334455667788"
DEV_NWKID  = "abcd"
DEV_IEEE   = "aabbccddeeff0011"

# Layout: sqn(2)+srcNwkId(4)+srcEp(2)+nwkid(4)+reqType(2)+startIndex(2)
def _make_msg(nwkid=CTRL_NWKID):
    return "01" + "1234" + "01" + nwkid + "00" + "00"


class TestDecode0041:

    def _setup(self, plugin, monkeypatch, mod):
        plugin.ControllerNWKID = CTRL_NWKID
        plugin.ControllerIEEE = CTRL_IEEE
        monkeypatch.setattr(mod, "raw_APS_request", MagicMock())

    def test_coordinator_nwkid_calls_raw_aps(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0041(plugin, {}, _make_msg(nwkid=CTRL_NWKID), LQI)
        raw.assert_called_once()

    def test_known_device_calls_raw_aps(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        plugin.ListOfDevices[DEV_NWKID] = {"IEEE": DEV_IEEE}
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0041(plugin, {}, _make_msg(nwkid=DEV_NWKID), LQI)
        raw.assert_called_once()

    def test_unknown_device_calls_raw_aps_with_status_81(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        plugin.ListOfDevices = {}
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0041(plugin, {}, _make_msg(nwkid="ffff"), LQI)
        raw.assert_called_once()
        # Verify payload contains status '81'
        call_args = raw.call_args
        payload = call_args.args[5] if len(call_args.args) > 5 else call_args.kwargs.get("payload", "")
        assert "81" in payload
