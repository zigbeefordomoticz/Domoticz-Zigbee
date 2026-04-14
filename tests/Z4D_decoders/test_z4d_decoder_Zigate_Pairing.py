"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Pairing.py

Covers:
  Decode8014 – permit-join status
    - Status '00' → Ping['Permit'] = 'Off', Duration = 0
    - Status '01' → Ping['Permit'] = 'On', Duration set if was 0
    - Unexpected status → logs Error
    - Always updates Ping['TimeStamp'] and Ping['Status']
  Decode8049 – pairing command executed
    - Status '00' → logs Status message
    - Other status → logs Debug
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Pairing"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


# ─── Decode8014 ───────────────────────────────────────────────────────────────

class TestDecode8014:

    def _setup(self, plugin):
        plugin.Ping = {}
        plugin.permitTojoin = {"Duration": 0, "Starttime": 0}

    def test_off_status_sets_permit_off(self, mod, plugin):
        self._setup(plugin)
        mod.Decode8014(plugin, {}, "00", LQI)
        assert plugin.Ping["Permit"] == "Off"

    def test_off_status_sets_duration_zero(self, mod, plugin):
        self._setup(plugin)
        mod.Decode8014(plugin, {}, "00", LQI)
        assert plugin.permitTojoin["Duration"] == 0

    def test_on_status_sets_permit_on(self, mod, plugin):
        self._setup(plugin)
        mod.Decode8014(plugin, {}, "01", LQI)
        assert plugin.Ping["Permit"] == "On"

    def test_on_status_sets_duration_when_zero(self, mod, plugin):
        self._setup(plugin)
        plugin.permitTojoin["Duration"] = 0
        mod.Decode8014(plugin, {}, "01", LQI)
        assert plugin.permitTojoin["Duration"] == 254

    def test_on_status_preserves_existing_duration(self, mod, plugin):
        self._setup(plugin)
        plugin.permitTojoin["Duration"] = 60
        mod.Decode8014(plugin, {}, "01", LQI)
        assert plugin.permitTojoin["Duration"] == 60

    def test_unexpected_status_logs_error(self, mod, plugin):
        self._setup(plugin)
        mod.Decode8014(plugin, {}, "ff", LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_always_updates_ping_status(self, mod, plugin):
        self._setup(plugin)
        mod.Decode8014(plugin, {}, "00", LQI)
        assert plugin.Ping["Status"] == "Receive"

    def test_always_updates_ping_timestamp(self, mod, plugin):
        self._setup(plugin)
        mod.Decode8014(plugin, {}, "00", LQI)
        assert "TimeStamp" in plugin.Ping

    def test_permit_key_initialised_if_missing(self, mod, plugin):
        plugin.Ping = {}  # no 'Permit' key
        plugin.permitTojoin = {"Duration": 0, "Starttime": 0}
        mod.Decode8014(plugin, {}, "00", LQI)
        assert "Permit" in plugin.Ping


# ─── Decode8049 ───────────────────────────────────────────────────────────────

class TestDecode8049:

    def test_success_status_logs_status(self, mod, plugin):
        mod.Decode8049(plugin, {}, "0100", LQI)  # status at [2:4] = '00'
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)

    def test_failure_status_logs_debug(self, mod, plugin):
        mod.Decode8049(plugin, {}, "0182", LQI)  # status at [2:4] = '82'
        # No Status log for non-00 status
        assert not any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)
