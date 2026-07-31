"""
Tests for Z4D_decoders/z4d_decoder_Rte_Discovery_Performed.py

Decode8701 — route-discovery notification; logs only (no device state changes).
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Rte_Discovery_Performed"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


class TestDecode8701:

    def test_too_short_returns_early(self, mod, plugin):
        """Frame < 4 chars: only one Debug log, no Log-level call."""
        plugin.log.logging.reset_mock()
        mod.Decode8701(plugin, {}, "00", LQI)
        log_levels = [c.args[1] for c in plugin.log.logging.call_args_list]
        assert "Log" not in log_levels

    def test_non_zero_nwk_status_logs(self, mod, plugin):
        """NwkStatus != '00' produces a Log entry."""
        # NwkStatus(2)+Status(2)+SrcAddr(4)
        mod.Decode8701(plugin, {}, "01" + "00" + "abcd", LQI)
        assert any(c.args[1] == "Log" for c in plugin.log.logging.call_args_list)

    def test_zero_nwk_status_no_log(self, mod, plugin):
        """NwkStatus == '00': only Debug entries."""
        plugin.log.logging.reset_mock()
        mod.Decode8701(plugin, {}, "00" + "00" + "abcd", LQI)
        log_levels = [c.args[1] for c in plugin.log.logging.call_args_list]
        assert "Log" not in log_levels

    def test_known_device_ieee_in_debug(self, mod, plugin):
        """When source addr is known, its IEEE appears in the Debug log."""
        plugin.ListOfDevices = {"abcd": {"IEEE": "aabbccddeeff0011"}}
        plugin.log.logging.reset_mock()
        mod.Decode8701(plugin, {}, "00" + "00" + "abcd", LQI)
        full_output = " ".join(str(c) for c in plugin.log.logging.call_args_list)
        assert "aabbccddeeff0011" in full_output
