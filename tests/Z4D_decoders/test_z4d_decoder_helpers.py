"""
Tests for Z4D_decoders/z4d_decoder_helpers.py

Covers:
  - extract_message_infos   – frame parsing
  - set_health_state        – NACK health update
  - device_reset            – per-attribute cleanup on leave
  - check_duplicate_sqn     – SQN deduplication helper
  - set_health_after_message_received – Live/inDB promotion
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_helpers"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    # Also clear any stale helpers stub left by test_input.py
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── extract_message_infos ────────────────────────────────────────────────────

class TestExtractMessageInfos:

    # Real frame layout (Zigate protocol):
    #   frame_start(2) + msg_type(4) + length+chksum(6) + payload + lqi(2) + frame_stop(2)
    # data[12:-4] = payload, data[-4:-2] = lqi, data[-2:] = frame_stop
    # Valid frame with payload "aabbcc" and lqi "ff":
    #   "01" "8045" "000000" "aabbcc" "ff" "03"  → 2+4+6+6+2+2 = 22 chars
    VALID = "01" + "8045" + "000000" + "aabbcc" + "ff" + "03"

    def test_valid_frame_returns_type(self, mod, plugin):
        msg_type, _, _ = mod.extract_message_infos(plugin, self.VALID)
        assert msg_type == "8045"

    def test_valid_frame_returns_payload(self, mod, plugin):
        _, msg_data, _ = mod.extract_message_infos(plugin, self.VALID)
        assert msg_data == "aabbcc"

    def test_valid_frame_returns_lqi(self, mod, plugin):
        _, _, msg_lqi = mod.extract_message_infos(plugin, self.VALID)
        assert msg_lqi == "ff"

    def test_both_bytes_wrong_returns_none_triple(self, mod, plugin):
        # Condition is AND: BOTH start AND stop must be wrong to return None
        bad = "02" + "8045" + "000000" + "aabbcc" + "ff" + "04"
        result = mod.extract_message_infos(plugin, bad)
        assert result == (None, None, None)

    def test_only_start_wrong_still_processes(self, mod, plugin):
        # Only start byte wrong → condition is AND, so frame is still processed
        bad = "02" + "8045" + "000000" + "aabbcc" + "ff" + "03"
        msg_type, msg_data, msg_lqi = mod.extract_message_infos(plugin, bad)
        assert msg_type == "8045"

    def test_only_stop_wrong_still_processes(self, mod, plugin):
        # Only stop byte wrong → condition is AND, so frame is still processed
        bad = "01" + "8045" + "000000" + "aabbcc" + "ff" + "04"
        msg_type, msg_data, msg_lqi = mod.extract_message_infos(plugin, bad)
        assert msg_type == "8045"

    def test_invalid_frame_logs_error(self, mod, plugin):
        # Both start and stop wrong → logs Error and returns None
        bad = "02" + "8045" + "000000" + "aabbcc" + "ff" + "04"
        mod.extract_message_infos(plugin, bad)
        assert any(
            c.args[1] == "Error"
            for c in plugin.log.logging.call_args_list
        )

    def test_short_frame_returns_empty_payload(self, mod, plugin):
        # Exactly 12 chars or fewer → no payload
        short = "01" + "8045" + "000000"  # 12 chars, no payload
        _, msg_data, msg_lqi = mod.extract_message_infos(plugin, short)
        assert msg_data == ""
        assert msg_lqi == "00"


# ─── set_health_state ─────────────────────────────────────────────────────────

class TestSetHealthState:

    def test_no_health_key_does_nothing(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Ep": {}}
        # should not crash, health unchanged
        mod.set_health_state(plugin, "1234", "0006", "82")
        assert "Health" not in plugin.ListOfDevices["1234"]

    def test_disabled_device_is_unchanged(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Health": "Disabled", "Ep": {}}
        mod.set_health_state(plugin, "1234", "0006", "82")
        assert plugin.ListOfDevices["1234"]["Health"] == "Disabled"

    def test_reachable_device_becomes_not_reachable(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Health": "Live", "Ep": {}}
        mod.set_health_state(plugin, "1234", "0006", "82")
        assert plugin.ListOfDevices["1234"]["Health"] == "Not Reachable"

    def test_already_not_reachable_stays(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Health": "Not Reachable", "Ep": {}}
        mod.set_health_state(plugin, "1234", "0006", "82")
        assert plugin.ListOfDevices["1234"]["Health"] == "Not Reachable"

    def test_device_off_on_timeout_clears_cluster_0006(self, mod, plugin):
        plugin.pluginconf.pluginConf["deviceOffWhenTimeOut"] = True
        plugin.ListOfDevices["1234"] = {
            "Health": "Live",
            "Ep": {"01": {"0006": {"0000": "01"}}},
        }
        mod.set_health_state(plugin, "1234", "0006", "82")
        assert plugin.ListOfDevices["1234"]["Ep"]["01"]["0006"]["0000"] == "00"


# ─── device_reset ─────────────────────────────────────────────────────────────

class TestDeviceReset:

    def test_unknown_nwk_id_does_nothing(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.device_reset(plugin, "9999")  # should not crash

    def test_removes_bind_attribute(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Bind": {"01": {}}, "Ep": {}}
        mod.device_reset(plugin, "1234")
        assert "Bind" not in plugin.ListOfDevices["1234"]

    def test_removes_configure_reporting(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Configure Reporting": {}, "Ep": {}}
        mod.device_reset(plugin, "1234")
        assert "Configure Reporting" not in plugin.ListOfDevices["1234"]

    def test_removes_read_attributes(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"ReadAttributes": {}, "Ep": {}}
        mod.device_reset(plugin, "1234")
        assert "ReadAttributes" not in plugin.ListOfDevices["1234"]

    def test_ias_cluster_data_cleared(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {
            "IAS": {"ZoneStatus": {}},
            "Ep": {"01": {"0500": {"0002": "alarm"}, "0502": {}}},
        }
        mod.device_reset(plugin, "1234")
        # IAS key should be gone; ep cluster data should be reset to {}
        assert "IAS" not in plugin.ListOfDevices["1234"]
        assert plugin.ListOfDevices["1234"]["Ep"]["01"]["0500"] == {}
        assert plugin.ListOfDevices["1234"]["Ep"]["01"]["0502"] == {}


# ─── check_duplicate_sqn ─────────────────────────────────────────────────────

class TestCheckDuplicateSqn:

    def test_no_ep_returns_false(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {}
        assert mod.check_duplicate_sqn(plugin, "1234", "01", "0006", "aa") is False

    def test_ep_not_present_returns_false(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Ep": {}}
        assert mod.check_duplicate_sqn(plugin, "1234", "01", "0006", "aa") is False

    def test_different_sqn_returns_false(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Ep": {"01": {}}, "SQN": "bb"}
        assert mod.check_duplicate_sqn(plugin, "1234", "01", "0006", "aa") is False

    def test_same_sqn_returns_true(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Ep": {"01": {}}, "SQN": "aa"}
        assert mod.check_duplicate_sqn(plugin, "1234", "01", "0006", "aa") is True

    def test_sqn_00_returns_false(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Ep": {"01": {}}, "SQN": "00"}
        assert mod.check_duplicate_sqn(plugin, "1234", "01", "0006", "00") is False


# ─── set_health_after_message_received ───────────────────────────────────────

class TestSetHealthAfterMessageReceived:

    @pytest.mark.parametrize("status", ["004d", "0043", "0045", "8045", "8043"])
    def test_pairing_status_does_nothing(self, mod, plugin, status):
        plugin.ListOfDevices["1234"] = {"Status": status}
        mod.set_health_after_message_received(plugin, "1234")
        # Health should NOT have been set
        assert "Health" not in plugin.ListOfDevices["1234"]

    def test_no_health_key_sets_live(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Status": "inDB"}
        mod.set_health_after_message_received(plugin, "1234")
        assert plugin.ListOfDevices["1234"]["Health"] == "Live"

    def test_disabled_health_unchanged(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Status": "inDB", "Health": "Disabled"}
        mod.set_health_after_message_received(plugin, "1234")
        assert plugin.ListOfDevices["1234"]["Health"] == "Disabled"

    def test_non_indb_status_updated(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {"Status": "Leave", "Health": "Live"}
        mod.set_health_after_message_received(plugin, "1234")
        assert plugin.ListOfDevices["1234"]["Status"] == "inDB"

    def test_unknown_device_does_not_crash(self, mod, plugin):
        plugin.ListOfDevices = {}
        # get() returns {} for unknown device, should not crash
        mod.set_health_after_message_received(plugin, "9999")
