"""
Tests for Z4D_decoders/z4d_decoder_Wrt_Attribute_Rsp.py

Decode8110 — write-attribute response; updates SQN/LQI/timestamp and
optionally notifies IAS zone management for cluster 0x0500.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Wrt_Attribute_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
ADDR = "abcd"
EP   = "01"

# len != 24 → MsgAttrStatus = MsgData[12:14], MsgAttrID = None
def _msg(cluster="0006", status="00"):
    # sqn(2)+addr(4)+ep(2)+cluster(4)+status(2) = 14 chars (len != 24)
    return "01" + ADDR + EP + cluster + status


class TestDecode8110:

    def test_no_firmware_version_returns_early(self, mod, plugin, monkeypatch):
        plugin.FirmwareVersion = ""
        upd = MagicMock()
        monkeypatch.setattr(mod, "updSQN", upd)
        mod.Decode8110(plugin, {}, _msg(), LQI)
        upd.assert_not_called()

    def test_with_firmware_calls_upd_sqn(self, mod, plugin, monkeypatch):
        plugin.FirmwareVersion = "031d"
        upd = MagicMock()
        monkeypatch.setattr(mod, "updSQN", upd)
        mod.Decode8110(plugin, {}, _msg(), LQI)
        upd.assert_called()

    def test_with_firmware_calls_upd_lqi(self, mod, plugin, monkeypatch):
        plugin.FirmwareVersion = "031d"
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        mod.Decode8110(plugin, {}, _msg(), LQI)
        upd.assert_called()

    def test_ias_cluster_calls_write_response(self, mod, plugin):
        plugin.FirmwareVersion = "031d"
        mod.Decode8110(plugin, {}, _msg(cluster="0500", status="00"), LQI)
        plugin.iaszonemgt.IAS_CIE_write_response.assert_called_once_with(
            ADDR, EP, "00"
        )
