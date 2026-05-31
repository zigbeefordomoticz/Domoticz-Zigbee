"""
Tests for Z4D_decoders/z4d_decoder_Read_Attribute_Rsp.py

Decode8100 — read attribute response; updates timestamp/LQI and delegates
attribute parsing to scan_attribute_reponse.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Read_Attribute_Rsp"

LQI  = "ff"
ADDR = "abcd"
EP   = "01"

# sqn(2)+addr(4)+ep(2)+cluster(4) = 12 chars minimum
def _msg(cluster="0006"):
    return "01" + ADDR + EP + cluster


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


class TestDecode8100:

    def test_calls_timestamped(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Model": "x"}}
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8100(plugin, {}, _msg(), LQI)
        ts.assert_called_once()

    def test_calls_upd_lqi(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Model": "x"}}
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        mod.Decode8100(plugin, {}, _msg(), LQI)
        upd.assert_called()

    def test_ias_cluster_calls_service_discovery_response(self, mod, plugin, monkeypatch):
        """Cluster 0500 → iaszonemgt.IAS_CIE_service_discovery_response called."""
        plugin.ListOfDevices = {ADDR: {"Model": "x"}}
        monkeypatch.setattr(mod, "scan_attribute_reponse", MagicMock())
        msg = _msg(cluster="0500")
        mod.Decode8100(plugin, {}, msg, LQI)
        plugin.iaszonemgt.IAS_CIE_service_discovery_response.assert_called_once_with(
            ADDR, EP, msg
        )

    def test_calls_scan_attribute_reponse(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Model": "x"}}
        scan = MagicMock()
        monkeypatch.setattr(mod, "scan_attribute_reponse", scan)
        mod.Decode8100(plugin, {}, _msg(), LQI)
        scan.assert_called_once()
