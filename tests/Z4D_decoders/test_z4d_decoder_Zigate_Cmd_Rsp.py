"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Cmd_Rsp.py

Covers:
  Decode8000_v2 – command status response
    - Short payload (< 8) → logs and returns
    - Status '00' → internalError = 0
    - Non-zero status → internalError incremented
    - Group packet types delegate to groupmgt
  Decode8011 – APS ACK
    - Unknown device → sanity check + handle_unknow_device
    - Status '00' (ACK) → updates LQI, Health=Live
    - Non-zero status (NACK) on mains-powered → timedOutDevice + set_health_state
  Decode8012/Decode8702 – stubs that always return
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Cmd_Rsp"
_HELPERS = "Z4D_decoders.z4d_decoder_helpers"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_HELPERS, None)
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI  = "80"
ADDR = "1234"


# ─── Decode8000_v2 ────────────────────────────────────────────────────────────

class TestDecode8000v2:
    # Layout: Status(2) + sqn_app(2) + PacketType(4) [+ optional type_sqn(2) + sqn_aps(2)]

    def test_too_short_logs_and_returns(self, mod, plugin):
        mod.Decode8000_v2(plugin, {}, "0100", LQI)  # 4 chars < 8
        assert any(c.args[1] == "Log" for c in plugin.log.logging.call_args_list)

    def test_success_status_zeros_internal_error(self, mod, plugin):
        plugin.internalError = 5
        plugin.pluginconf.pluginConf["coordinatorCmd"] = False
        mod.Decode8000_v2(plugin, {}, "00" + "01" + "0100", LQI)
        assert plugin.internalError == 0

    def test_nonzero_status_increments_internal_error(self, mod, plugin):
        # Status codes '01'–'05' are excluded from the internalError counter.
        # Use '10' (outside that range) to trigger the increment.
        plugin.internalError = 0
        plugin.pluginconf.pluginConf["coordinatorCmd"] = False
        mod.Decode8000_v2(plugin, {}, "10" + "01" + "0100", LQI)
        assert plugin.internalError == 1

    def test_group_packet_type_delegates_to_groupmgt(self, mod, plugin):
        plugin.groupmgt = MagicMock()
        plugin.pluginconf.pluginConf["coordinatorCmd"] = False
        mod.Decode8000_v2(plugin, {}, "00" + "01" + "0060", LQI)
        plugin.groupmgt.statusGroupRequest.assert_called_once()

    def test_no_groupmgt_does_not_crash(self, mod, plugin):
        plugin.groupmgt = None
        plugin.pluginconf.pluginConf["coordinatorCmd"] = False
        mod.Decode8000_v2(plugin, {}, "00" + "01" + "0060", LQI)


# ─── Decode8011 ───────────────────────────────────────────────────────────────

class TestDecode8011:
    # Layout: Status(2) + SrcAddr(4) + ?(4) + ?(2) + ?(2) + ?(2) ...
    # Minimal 14+ chars for MsgSEQ:
    # Status(2) + SrcAddr(4) + cluster(4) + ?(2) + SQN(2)

    def _make_msg(self, addr=ADDR, status="00"):
        return status + addr + "0006" + "00" + "01"  # 14 chars

    def test_unknown_device_calls_sanity_check(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_aps_sqn", MagicMock(return_value=1))
        mod.Decode8011(plugin, {}, self._make_msg(), LQI)
        sanity.assert_called_once_with(plugin, ADDR)

    def test_unknown_device_calls_handle_unknown_when_sanity_fails(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=False))
        handle = MagicMock()
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_aps_sqn", MagicMock(return_value=1))
        mod.Decode8011(plugin, {}, self._make_msg(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_ack_updates_lqi(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Health": "Live"}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_aps_sqn", MagicMock(return_value=1))
        monkeypatch.setattr(mod, "lastSeenUpdate", MagicMock())
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        ulqi = MagicMock()
        monkeypatch.setattr(mod, "updLQI", ulqi)
        mod.Decode8011(plugin, {}, self._make_msg(status="00"), LQI)
        ulqi.assert_called_with(plugin, ADDR, LQI)

    def test_ack_restores_health_to_live(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Health": "Not Reachable"}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_aps_sqn", MagicMock(return_value=1))
        monkeypatch.setattr(mod, "lastSeenUpdate", MagicMock())
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        mod.Decode8011(plugin, {}, self._make_msg(status="00"), LQI)
        assert plugin.ListOfDevices[ADDR]["Health"] == "Live"

    def test_nack_on_battery_device_does_not_call_timedout(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Health": "Live"}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_aps_sqn", MagicMock(return_value=1))
        monkeypatch.setattr(mod, "mainPoweredDevice", MagicMock(return_value=False))
        timedout = MagicMock()
        monkeypatch.setattr(mod, "timedOutDevice", timedout)
        mod.Decode8011(plugin, {}, self._make_msg(status="82"), LQI)
        timedout.assert_not_called()

    def test_nack_on_main_powered_calls_timedout(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Health": "Live"}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_aps_sqn", MagicMock(return_value=1))
        monkeypatch.setattr(mod, "mainPoweredDevice", MagicMock(return_value=True))
        timedout = MagicMock()
        monkeypatch.setattr(mod, "timedOutDevice", timedout)
        monkeypatch.setattr(mod, "set_health_state", MagicMock())
        monkeypatch.setattr(mod, "lastSeenUpdate", MagicMock())
        mod.Decode8011(plugin, {}, self._make_msg(status="82"), LQI)
        timedout.assert_called_once()


# ─── Decode8012 / Decode8702 ─────────────────────────────────────────────────

class TestDecodeStubs:

    def test_decode8012_returns_none(self, mod, plugin):
        result = mod.Decode8012(plugin, {}, "00aabbcc", LQI)
        assert result is None

    def test_decode8702_returns_none(self, mod, plugin):
        result = mod.Decode8702(plugin, {}, "00aabbcc", LQI)
        assert result is None
