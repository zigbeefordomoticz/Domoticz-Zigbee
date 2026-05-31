"""
Tests for Z4D_decoders/z4d_decoder_Nwk_Addr_Rsp.py

Decode8040 — network address response.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Nwk_Addr_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI       = "ff"
CTRL_IEEE = "1122334455667788"
DEV_IEEE  = "aabbccddeeff0011"
DEV_NWKID = "abcd"

# Layout: sqn(2)+status(2)+ieee(16)+nwkid(4)
def _msg(status="00", ieee=DEV_IEEE, nwkid=DEV_NWKID, extra=""):
    return "01" + status + ieee + nwkid + extra


class TestDecode8040:

    def test_non_zero_status_returns_early(self, mod, plugin):
        """Non-zero status → function returns; no Error/Log."""
        plugin.log.logging.reset_mock()
        mod.Decode8040(plugin, {}, _msg(status="81"), LQI)
        levels = [c.args[1] for c in plugin.log.logging.call_args_list]
        assert "Error" not in levels

    def test_known_device_matching_ieee_calls_timestamped(self, mod, plugin, monkeypatch):
        """Device in ListOfDevices with matching IEEE → timeStamped called."""
        plugin.ListOfDevices = {DEV_NWKID: {"IEEE": DEV_IEEE}}
        plugin.IEEE2NWK = {}
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8040(plugin, {}, _msg(), LQI)
        ts.assert_called_once()

    def test_ieee_in_ieee2nwk_calls_device_exist(self, mod, plugin, monkeypatch):
        """IEEE known in IEEE2NWK → DeviceExist called to try reconnect."""
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {DEV_IEEE: DEV_NWKID}
        de = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "DeviceExist", de)
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8040(plugin, {}, _msg(), LQI)
        de.assert_called_once()

    def test_extended_response_calls_network_request_next_when_incomplete(
        self, mod, plugin, monkeypatch
    ):
        """Extended response with fewer devices listed than total → requests next page."""
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {}
        # NumAssocDevices=2, StartIndex=0, only 1 device listed → need another page
        extra = "02" + "00" + "abcd"   # numAssoc(2)+startIdx(2)+1 device(4)
        nri = MagicMock()
        monkeypatch.setattr(mod, "Network_Address_response_request_next_index", nri)
        mod.Decode8040(plugin, {}, _msg(extra=extra), LQI)
        nri.assert_called_once()

    def test_completely_unknown_ieee_logs_error(self, mod, plugin, monkeypatch):
        """Unknown IEEE → Error log."""
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=False))
        plugin.log.logging.reset_mock()
        mod.Decode8040(plugin, {}, _msg(ieee="ffffffffffffffff"), LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)
