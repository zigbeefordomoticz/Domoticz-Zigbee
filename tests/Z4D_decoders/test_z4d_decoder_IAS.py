"""
Tests for Z4D_decoders/z4d_decoder_IAS.py

Covers:
  Decode0400 – IAS zone enroll response
  Decode8046 – Match Descriptor response (IAS zone mgmt delegation)
  Decode8400 – IAS zone enroll request
  Decode8401 – Zone status change notification
  _extract_zone_status_info – address-mode parsing helper
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_IAS"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI  = "80"
ADDR = "abcd"
EP   = "01"


# ─── Decode0400 ───────────────────────────────────────────────────────────────

class TestDecode0400:
    # Message layout (must be exactly 14 chars):
    #   sqn(2) + SrcAddress(4) + SrcEndpoint(2) + ?(2) + EnrollResponseCode(2) + ZoneId(2)
    VALID_MSG = "01" + "abcd" + "01" + "00" + "00" + "01"  # 14 chars

    def test_wrong_length_returns_early(self, mod, plugin):
        plugin.iaszonemgt = MagicMock()
        mod.Decode0400(plugin, {}, "01abcd0100", LQI)  # 10 chars != 14
        plugin.iaszonemgt.IAS_zone_enroll_request_response.assert_not_called()

    def test_correct_length_without_iaszonemgt(self, mod, plugin):
        plugin.iaszonemgt = None
        mod.Decode0400(plugin, {}, self.VALID_MSG, LQI)  # should not crash

    def test_correct_length_with_iaszonemgt_calls_delegate(self, mod, plugin):
        plugin.iaszonemgt = MagicMock()
        mod.Decode0400(plugin, {}, self.VALID_MSG, LQI)
        plugin.iaszonemgt.IAS_zone_enroll_request_response.assert_called_once()


# ─── Decode8046 ───────────────────────────────────────────────────────────────

class TestDecode8046:
    # SQN(2) + Status(2) + ShAddr(4) + LenList(2) + MatchList
    MSG_NO_MATCH = "01" + "00" + "abcd" + "00"  # LenList=0, no eps
    MSG_WITH_MATCH = "01" + "00" + "abcd" + "01" + "01"  # 1 ep

    def test_no_match_does_not_call_ias(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        plugin.iaszonemgt = MagicMock()
        mod.Decode8046(plugin, {}, self.MSG_NO_MATCH, LQI)
        plugin.iaszonemgt.IAS_write_CIE_after_match_descriptor.assert_not_called()

    def test_with_match_calls_ias_delegate(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        plugin.iaszonemgt = MagicMock()
        mod.Decode8046(plugin, {}, self.MSG_WITH_MATCH, LQI)
        plugin.iaszonemgt.IAS_write_CIE_after_match_descriptor.assert_called_once_with("abcd", "01")

    def test_no_iaszonemgt_does_not_crash(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        plugin.iaszonemgt = None
        mod.Decode8046(plugin, {}, self.MSG_WITH_MATCH, LQI)


# ─── Decode8400 ───────────────────────────────────────────────────────────────

class TestDecode8400:
    # sqn(2) + zonetype(4) + manuf(4) + nwkid(4) + ep(2) = 16 chars
    VALID_MSG = "01" + "0015" + "1234" + "abcd" + "01"

    def test_with_iaszonemgt_calls_enroll_request(self, mod, plugin):
        plugin.iaszonemgt = MagicMock()
        mod.Decode8400(plugin, {}, self.VALID_MSG, LQI)
        plugin.iaszonemgt.IAS_zone_enroll_request.assert_called_once_with(
            "abcd", "01", "0015", "01"
        )

    def test_without_iaszonemgt_does_not_crash(self, mod, plugin):
        plugin.iaszonemgt = None
        mod.Decode8400(plugin, {}, self.VALID_MSG, LQI)


# ─── _extract_zone_status_info ────────────────────────────────────────────────

class TestExtractZoneStatusInfo:
    # Short address mode '02':
    #   sqn(2)+ep(2)+cluster(4)+addrmode(2)+srcaddr(4)+zonestatus(4)+extstatus(2)+zoneid(2)+delay(4)
    MSG_SHORT_MODE = ("01" + "01" + "0500" + "02" +
                      "abcd" + "0001" + "00" + "01" + "0000")

    # IEEE address mode '03':
    #   sqn(2)+ep(2)+cluster(4)+addrmode(2)+ieee(16)+...
    MSG_IEEE_MODE = ("01" + "01" + "0500" + "03" +
                     "1234567890abcdef" + "0001" + "00" + "01" + "0000")

    def test_short_mode_returns_correct_addr(self, mod, plugin):
        result = mod._extract_zone_status_info(plugin, self.MSG_SHORT_MODE)
        assert result is not None
        _, _, _, _, src_addr, _, _, _, _ = result
        assert src_addr == "abcd"

    def test_ieee_mode_returns_correct_addr(self, mod, plugin):
        result = mod._extract_zone_status_info(plugin, self.MSG_IEEE_MODE)
        assert result is not None
        _, _, _, _, src_addr, _, _, _, _ = result
        assert src_addr == "1234567890abcdef"

    def test_unknown_addr_mode_returns_none(self, mod, plugin):
        bad_msg = "01" + "01" + "0500" + "ff" + "abcd" + "0001" + "00" + "01" + "0000"
        result = mod._extract_zone_status_info(plugin, bad_msg)
        assert result is None


# ─── Decode8401 ───────────────────────────────────────────────────────────────

class TestDecode8401:
    # Valid zone status change (short address mode):
    #   sqn(2)+ep(2)+cluster(4)+addrmode(2)+addr(4)+zonestatus(4)+extstatus(2)+zoneid(2)+delay(4)
    MSG = ("01" + "01" + "0500" + "02" +
           "abcd" + "0001" + "00" + "01" + "0000")

    def _setup_device(self, plugin, monkeypatch, mod):
        plugin.ListOfDevices[ADDR] = {
            "Ep": {"01": {"0500": {}}},
            "Health": "Live",
            "Model": "generic",
            "IAS": {"ZoneStatus": {}},
        }
        monkeypatch.setattr(mod, "lastSeenUpdate", MagicMock())
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "get_deviceconf_parameter_value", MagicMock(return_value=None))
        monkeypatch.setattr(mod, "get_device_config_param", MagicMock(return_value=None))
        monkeypatch.setattr(mod, "MajDomoDevice", MagicMock())

    def test_valid_msg_does_not_raise(self, mod, plugin, monkeypatch):
        self._setup_device(plugin, monkeypatch, mod)
        mod.Decode8401(plugin, {}, self.MSG, LQI)

    def test_updates_lqi(self, mod, plugin, monkeypatch):
        self._setup_device(plugin, monkeypatch, mod)
        ulqi = MagicMock()
        monkeypatch.setattr(mod, "updLQI", ulqi)
        mod.Decode8401(plugin, {}, self.MSG, LQI)
        ulqi.assert_called_with(plugin, ADDR, LQI)

    def test_invalid_addr_mode_raises_before_error_log(self, mod, plugin, monkeypatch):
        # The source unpacks zone_status_fields *before* checking for None, so
        # an unknown addr-mode (0xff) causes a TypeError rather than a logged
        # error.  This test documents that current behaviour.
        monkeypatch.setattr(mod, "lastSeenUpdate", MagicMock())
        monkeypatch.setattr(mod, "timeStamped", MagicMock())
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "get_deviceconf_parameter_value", MagicMock(return_value=None))
        bad_msg = "01" + "01" + "0500" + "ff" + "abcd" + "0001" + "00" + "01" + "0000"
        with pytest.raises(TypeError):
            mod.Decode8401(plugin, {}, bad_msg, LQI)

    def test_sets_ias_battery_100_on_no_battery_flag(self, mod, plugin, monkeypatch):
        self._setup_device(plugin, monkeypatch, mod)
        mod.Decode8401(plugin, {}, self.MSG, LQI)  # zonestatus "0001" – bit3=0 → no battery
        assert plugin.ListOfDevices[ADDR]["IASBattery"] == 100

    def test_sets_ias_battery_5_on_battery_flag(self, mod, plugin, monkeypatch):
        self._setup_device(plugin, monkeypatch, mod)
        # Set battery bit (bit 3) in zone status → "0008"
        msg_battery = ("01" + "01" + "0500" + "02" +
                       "abcd" + "0008" + "00" + "01" + "0000")
        mod.Decode8401(plugin, {}, msg_battery, LQI)
        assert plugin.ListOfDevices[ADDR]["IASBattery"] == 5
