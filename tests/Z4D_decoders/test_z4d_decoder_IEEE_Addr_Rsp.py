"""
Tests for Z4D_decoders/z4d_decoder_IEEE_Addr_Rsp.py

Decode8041 — IEEE address response handling.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_IEEE_Addr_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI       = "ff"
CTRL_IEEE = "1122334455667788"
DEV_IEEE  = "aabbccddeeff0011"
DEV_NWKID = "abcd"

# Layout: sqn(2)+status(2)+ieee(16)+nwkid(4)  [+extended fields if present]
def _msg(status="00", ieee=DEV_IEEE, nwkid=DEV_NWKID):
    return "01" + status + ieee + nwkid


class TestDecode8041:

    def test_non_zero_status_returns_early(self, mod, plugin, monkeypatch):
        """Non-zero status → only a Debug log; nothing else happens."""
        plugin.log.logging.reset_mock()
        mod.Decode8041(plugin, {}, _msg(status="81"), LQI)
        assert not any(
            c.args[1] in ("Log", "Error")
            for c in plugin.log.logging.call_args_list
        )

    def test_mismatch_addr_0000_different_ieee_logs_error(self, mod, plugin):
        """NwkId=0000 with IEEE != ControllerIEEE → error log."""
        plugin.ControllerIEEE = CTRL_IEEE
        mod.Decode8041(plugin, {}, _msg(nwkid="0000", ieee=DEV_IEEE), LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_controller_ieee_wrong_nwkid_logs(self, mod, plugin):
        """ControllerIEEE matches but NwkId != 0000 → Log entry."""
        plugin.ControllerIEEE = DEV_IEEE
        mod.Decode8041(plugin, {}, _msg(nwkid=DEV_NWKID, ieee=DEV_IEEE), LQI)
        assert any(c.args[1] == "Log" for c in plugin.log.logging.call_args_list)

    def test_known_ieee2nwk_device_calls_timestamped(self, mod, plugin, monkeypatch):
        """IEEE in IEEE2NWK and DeviceExist succeeds → timeStamped called.

        Note: the ListOfDevices branch (line 36 of the source) checks
        ``ListOfDevices[addr]['IEEE'] == MsgShortAddress`` which can never be
        true in normal operation (64-bit IEEE vs 16-bit NwkID).  The reachable
        path to timeStamped is through IEEE2NWK when DeviceExist returns True.
        """
        plugin.ControllerIEEE = CTRL_IEEE
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {DEV_IEEE: DEV_NWKID}
        de = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "DeviceExist", de)
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8041(plugin, {}, _msg(), LQI)
        ts.assert_called_once()

    def test_ieee_in_ieee2nwk_calls_device_exist(self, mod, plugin, monkeypatch):
        """IEEE known in IEEE2NWK → tries to reconnect via DeviceExist."""
        plugin.ControllerIEEE = CTRL_IEEE
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {DEV_IEEE: DEV_NWKID}
        de = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "DeviceExist", de)
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8041(plugin, {}, _msg(), LQI)
        de.assert_called_once()

    def test_unknown_ieee_logs_warning(self, mod, plugin, monkeypatch):
        """Completely unknown IEEE → warning Log."""
        plugin.ControllerIEEE = CTRL_IEEE
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=False))
        plugin.log.logging.reset_mock()
        mod.Decode8041(plugin, {}, _msg(ieee="ffffffffffffffff"), LQI)
        assert any(c.args[1] == "Log" for c in plugin.log.logging.call_args_list)
