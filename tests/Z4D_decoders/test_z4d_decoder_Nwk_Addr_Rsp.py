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

    # ------------------------------------------------------------------
    # Telling an Associated Devices collection that an answer carried no list
    # ------------------------------------------------------------------
    # Both of these replies are answers, and both used to be dropped before the
    # collector heard them, so a live router that cannot produce an associated
    # device list was filed as a timeout.

    def test_non_zero_status_notifies_the_collection(self, mod, plugin, monkeypatch):
        """INV_REQUESTTYPE is what a stack with no extended response answers."""
        notify = MagicMock()
        monkeypatch.setattr(mod, "notify_associated_devices_no_list", notify)
        mod.Decode8040(plugin, {}, _msg(status="80"), LQI)

        notify.assert_called_once()
        assert notify.call_args.args[1] == DEV_IEEE, "matched on the IEEE asked"
        assert "80" in notify.call_args.args[2]

    def test_single_device_response_notifies_the_collection(self, mod, plugin, monkeypatch):
        """Status 00, address only: no NumAssocDev, no StartIndex, no list."""
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=False))
        notify = MagicMock()
        monkeypatch.setattr(mod, "notify_associated_devices_no_list", notify)
        mod.Decode8040(plugin, {}, _msg(), LQI)

        notify.assert_called_once()
        assert notify.call_args.args[1] == DEV_IEEE
        assert notify.call_args.kwargs["nwkid"] == DEV_NWKID

    def test_an_extended_response_does_not_notify_no_list(self, mod, plugin, monkeypatch):
        """It carries a list, so it goes to response_received() instead."""
        plugin.ListOfDevices = {}
        plugin.IEEE2NWK = {}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "Network_Address_response_request_next_index", MagicMock())
        notify = MagicMock()
        monkeypatch.setattr(mod, "notify_associated_devices_no_list", notify)
        scan = MagicMock()
        monkeypatch.setattr(mod, "notify_associated_devices_scan", scan)
        mod.Decode8040(plugin, {}, _msg(extra="01" + "00" + "abcd"), LQI)

        notify.assert_not_called()
        scan.assert_called_once()
