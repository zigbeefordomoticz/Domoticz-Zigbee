"""
Tests for Z4D_decoders/z4d_decoder_Pwr_Mgt_Rsp.py

Decode8806 / Decode8807 — TX-power management responses.
Both read TxPower from MsgData[:2], store it in ControllerData, and log Status.
Known power levels also store an attenuation value.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Pwr_Mgt_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"

# 0x00 = 0 dBm → in ATTENUATION_dBm['JN516x'] → known
# 0xab = 171 dec → not in the table → unknown
KNOWN_TX   = "00"   # int 0, attenuation 0 dBm
UNKNOWN_TX = "ab"   # int 171, not in table


class TestDecode8806:

    def test_known_tx_stores_tx_power(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8806(plugin, {}, KNOWN_TX, LQI)
        assert plugin.ControllerData["Tx-Power"] == KNOWN_TX

    def test_known_tx_stores_attenuation(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8806(plugin, {}, KNOWN_TX, LQI)
        assert "Tx-Attenuation" in plugin.ControllerData

    def test_known_tx_logs_status(self, mod, plugin):
        mod.Decode8806(plugin, {}, KNOWN_TX, LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)

    def test_unknown_tx_stores_tx_power(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8806(plugin, {}, UNKNOWN_TX, LQI)
        assert plugin.ControllerData["Tx-Power"] == UNKNOWN_TX

    def test_unknown_tx_no_attenuation(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8806(plugin, {}, UNKNOWN_TX, LQI)
        assert "Tx-Attenuation" not in plugin.ControllerData

    def test_unknown_tx_logs_confirming_status(self, mod, plugin):
        mod.Decode8806(plugin, {}, UNKNOWN_TX, LQI)
        assert any(
            c.args[1] == "Status" and "Confirming" in str(c.args[2])
            for c in plugin.log.logging.call_args_list
        )


class TestDecode8807:

    def test_known_tx_stores_tx_power(self, mod, plugin):
        plugin.ControllerData = {}
        # 0x34 = 52 dec → in JN516x table (attenuation -9)
        mod.Decode8807(plugin, {}, "34", LQI)
        assert plugin.ControllerData["Tx-Power"] == "34"

    def test_known_tx_stores_attenuation(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8807(plugin, {}, "34", LQI)
        assert "Tx-Attenuation" in plugin.ControllerData

    def test_unknown_tx_stores_tx_power(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8807(plugin, {}, UNKNOWN_TX, LQI)
        assert plugin.ControllerData["Tx-Power"] == UNKNOWN_TX

    def test_unknown_tx_logs_status(self, mod, plugin):
        mod.Decode8807(plugin, {}, UNKNOWN_TX, LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)
