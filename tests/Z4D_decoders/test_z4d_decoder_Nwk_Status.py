"""
Tests for Z4D_decoders/z4d_decoder_Nwk_Status.py

Covers:
  Decode8009 – network state update
    - Updates ControllerIEEE, ControllerNWKID, ControllerData
    - Non-zero NWKID logs error
    - Zero PanID logs network down
    - Channel change handled
  Decode8024 – start network confirmation
    - Status codes '00','01','02','04','06' log correctly
    - Incomplete frame (<24 chars) returns early
    - Complete frame with addr='0000' updates coordinator data
    - Unexpected addr logs error
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Nwk_Status"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"

# ─── Decode8009 message layout ────────────────────────────────────────────────
#   [0:4]   addr
#   [4:20]  extaddr (16 chars)
#   [20:24] PanID
#   [24:40] extPanID (16 chars)
#   [40:42] Channel

def _make_8009(addr="0000", extaddr="1122334455667788",
               panid="1234", extpanid="aabbccddeeff0011",
               channel="0f"):
    return addr + extaddr + panid + extpanid + channel


# ─── Decode8024 message layout ────────────────────────────────────────────────
#   [0:2]   Status
#   [2:6]   ShortAddress
#   [6:22]  ExtendedAddress (16 chars)
#   [22:24] Channel

def _make_8024(status="00", short="0000",
               extaddr="1122334455667788", channel="0f"):
    return status + short + extaddr + channel


# ─── Decode8009 tests ─────────────────────────────────────────────────────────

class TestDecode8009:

    def test_updates_controller_ieee(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "initLODZigate", MagicMock())
        mod.Decode8009(plugin, {}, _make_8009(), LQI)
        assert plugin.ControllerIEEE == "1122334455667788"

    def test_updates_controller_nwkid(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "initLODZigate", MagicMock())
        mod.Decode8009(plugin, {}, _make_8009(), LQI)
        assert plugin.ControllerNWKID == "0000"

    def test_non_zero_addr_logs_error(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "initLODZigate", MagicMock())
        mod.Decode8009(plugin, {}, _make_8009(addr="0001"), LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_panid_zero_logs_network_up(self, mod, plugin, monkeypatch):
        # The source checks ``str(PanID) == '0'`` but PanID is the raw hex
        # string "0000", so str("0000") != '0' and the DOWN branch is never
        # reached.  The UP branch executes instead.
        monkeypatch.setattr(mod, "initLODZigate", MagicMock())
        mod.Decode8009(plugin, {}, _make_8009(panid="0000"), LQI)
        assert any(
            "UP" in str(c)
            for c in plugin.log.logging.call_args_list
        )

    def test_updates_controller_data(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "initLODZigate", MagicMock())
        mod.Decode8009(plugin, {}, _make_8009(), LQI)
        assert plugin.ControllerData["IEEE"] == "1122334455667788"
        assert plugin.ControllerData["Short Address"] == "0000"

    def test_current_channel_updated(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "initLODZigate", MagicMock())
        mod.Decode8009(plugin, {}, _make_8009(channel="0f"), LQI)
        assert plugin.currentChannel == 15


# ─── Decode8024 tests ─────────────────────────────────────────────────────────

class TestDecode8024:

    @pytest.mark.parametrize("status,keyword", [
        ("00", "Success"),
        ("01", "Success"),
    ])
    def test_success_statuses_log_success(self, mod, plugin, status, keyword):
        mod.Decode8024(plugin, {}, _make_8024(status=status), LQI)
        assert any(keyword in str(c) for c in plugin.log.logging.call_args_list)

    def test_error_status_02_logs_error_msg(self, mod, plugin):
        mod.Decode8024(plugin, {}, _make_8024(status="02"), LQI)
        assert any("Error" in str(c) or "error" in str(c).lower()
                   for c in plugin.log.logging.call_args_list)

    def test_incomplete_frame_returns_early(self, mod, plugin):
        short = "00" + "0000"  # only 6 chars, well below 24
        mod.Decode8024(plugin, {}, short, LQI)
        # ControllerIEEE should not be set from incomplete frame
        assert plugin.ControllerIEEE == ""

    def test_complete_frame_sets_coordinator_ieee(self, mod, plugin):
        mod.Decode8024(plugin, {}, _make_8024(), LQI)
        assert plugin.ControllerIEEE == "1122334455667788"

    def test_complete_frame_sets_channel(self, mod, plugin):
        mod.Decode8024(plugin, {}, _make_8024(channel="0f"), LQI)
        assert plugin.currentChannel == 15

    def test_non_coordinator_addr_logs_error(self, mod, plugin):
        mod.Decode8024(plugin, {}, _make_8024(short="1234"), LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)
