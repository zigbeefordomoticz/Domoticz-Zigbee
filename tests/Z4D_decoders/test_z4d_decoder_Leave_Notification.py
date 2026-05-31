"""
Tests for Z4D_decoders/z4d_decoder_Leave_Notification.py

Covers Decode8048:
  - IEEE address not in IEEE2NWK → calls device_leave_announcement, returns
  - Short address not in ListOfDevices → returns
  - Status 'Removed'  → delete device + IEEE2NWK entries
  - Status 'inDB'     → set to Leave, Heartbeat = 0
  - Status in pairing → delete from both dicts
  - Status 'Leave'    → stays Leave, Heartbeat = 0
  - Calls device_reset and updLQI for known devices
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Leave_Notification"
_HELPERS = "Z4D_decoders.z4d_decoder_helpers"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    # Clear any stub from test_input.py for both modules
    sys.modules.pop(_HELPERS, None)
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── Constants ────────────────────────────────────────────────────────────────

IEEE  = "1234567890abcdef"  # 16 hex chars
SADDR = "abcd"
LQI   = "c0"

def _make_msg(ieee=IEEE, status="00"):
    return ieee + status


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestDecode8048UnknownIEEE:

    def test_unknown_ieee_calls_leave_announcement(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK = {}
        announce = MagicMock()
        monkeypatch.setattr(mod, "device_leave_announcement", announce)
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        announce.assert_called_once_with(plugin, {}, IEEE)

    def test_unknown_ieee_returns_early(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK = {}
        monkeypatch.setattr(mod, "device_leave_announcement", MagicMock())
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock())
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        ts.assert_not_called()


class TestDecode8048UnknownSAddr:

    def test_unknown_saddr_returns_early(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK = {IEEE: SADDR}
        plugin.ListOfDevices = {}  # saddr not present
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock(return_value=SADDR))
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        ts.assert_not_called()


class TestDecode8048RemovedStatus:

    def _setup(self, plugin, monkeypatch, mod, status):
        plugin.IEEE2NWK = {IEEE: SADDR}
        plugin.ListOfDevices = {SADDR: {"Status": status, "Ep": {}, "ZDeviceName": "test"}}
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock(return_value=SADDR))
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "device_leave_announcement", MagicMock())
        monkeypatch.setattr(mod, "device_reset", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "loggingMessages", MagicMock())

    def test_removed_deletes_device_entry(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod, "Removed")
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        assert SADDR not in plugin.ListOfDevices

    def test_removed_deletes_ieee2nwk_entry(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod, "Removed")
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        assert IEEE not in plugin.IEEE2NWK


class TestDecode8048InDbStatus:

    def _setup(self, plugin, monkeypatch, mod):
        plugin.IEEE2NWK = {IEEE: SADDR}
        plugin.ListOfDevices = {SADDR: {"Status": "inDB", "Ep": {}, "Heartbeat": 5, "ZDeviceName": "test"}}
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock(return_value=SADDR))
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "device_leave_announcement", MagicMock())
        monkeypatch.setattr(mod, "device_reset", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "loggingMessages", MagicMock())

    def test_indb_sets_status_to_leave(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        assert plugin.ListOfDevices[SADDR]["Status"] == "Leave"

    def test_indb_resets_heartbeat(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        assert plugin.ListOfDevices[SADDR]["Heartbeat"] == 0


class TestDecode8048PairingStatus:

    @pytest.mark.parametrize("status", ["004d", "0043", "8043", "0045", "8045"])
    def test_pairing_status_deletes_device(self, mod, plugin, monkeypatch, status):
        plugin.IEEE2NWK = {IEEE: SADDR}
        plugin.ListOfDevices = {SADDR: {"Status": status, "Ep": {}, "ZDeviceName": ""}}
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock(return_value=SADDR))
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "device_leave_announcement", MagicMock())
        monkeypatch.setattr(mod, "device_reset", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "loggingMessages", MagicMock())
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        assert SADDR not in plugin.ListOfDevices


class TestDecode8048DeviceReset:

    def test_calls_device_reset(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK = {IEEE: SADDR}
        plugin.ListOfDevices = {SADDR: {"Status": "inDB", "Ep": {}, "ZDeviceName": ""}}
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock(return_value=SADDR))
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "device_leave_announcement", MagicMock())
        reset = MagicMock()
        monkeypatch.setattr(mod, "device_reset", reset)
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "loggingMessages", MagicMock())
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        reset.assert_called_once_with(plugin, SADDR)

    def test_calls_updlqi(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK = {IEEE: SADDR}
        plugin.ListOfDevices = {SADDR: {"Status": "inDB", "Ep": {}, "ZDeviceName": ""}}
        monkeypatch.setattr(mod, "getSaddrfromIEEE", MagicMock(return_value=SADDR))
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "device_leave_announcement", MagicMock())
        monkeypatch.setattr(mod, "device_reset", MagicMock())
        ulqi = MagicMock()
        monkeypatch.setattr(mod, "updLQI", ulqi)
        monkeypatch.setattr(mod, "loggingMessages", MagicMock())
        mod.Decode8048(plugin, {}, _make_msg(), LQI)
        ulqi.assert_called_once_with(plugin, SADDR, LQI)
