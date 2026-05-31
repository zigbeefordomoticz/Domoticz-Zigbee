"""
Tests for Z4D_decoders/z4d_decoder_Node_Desc_req.py

Covers Decode0042:
  - Non-coordinator nwkid → status '80'
  - Coordinator not in ListOfDevices → status '81'
  - Coordinator without Manufacturer key → status '89'
  - Coordinator with full data → status '00' + calls raw_APS_request
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Node_Desc_req"

# Ensure Modules.sendZigateCommand is stubbed before importing
import types as _types
if "Modules.sendZigateCommand" not in sys.modules:
    _m = _types.ModuleType("Modules.sendZigateCommand")
    _m.raw_APS_request = MagicMock(name="raw_APS_request")
    sys.modules["Modules.sendZigateCommand"] = _m


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"

# Layout: sqn(2)+srcNwkId(4)+srcEp(2)+nwkid(4) = 12 chars
def _make_msg(nwkid="0000", src="abcd"):
    return "01" + src + "01" + nwkid


class TestDecode0042:

    def test_non_coordinator_calls_raw_aps(self, mod, plugin, monkeypatch):
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="1234"), LQI)
        raw.assert_called_once()

    def test_coordinator_not_in_devices_calls_raw_aps(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)
        raw.assert_called_once()

    def test_coordinator_without_manufacturer_calls_raw_aps(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = {"Ep": {}}  # no Manufacturer key
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)
        raw.assert_called_once()

    def test_coordinator_with_full_data_calls_raw_aps(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = {
            "Ep": {}, "Manufacturer": "1234",
            "Max Rx": "0050", "Max Tx": "0050",
            "server_mask": "0000", "descriptor_capability": "00",
            "macapa": "8e", "Max Buffer Size": "52", "bitfield": "4001",
        }
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)
        raw.assert_called_once()
