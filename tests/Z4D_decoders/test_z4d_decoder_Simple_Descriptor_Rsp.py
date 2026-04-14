"""
Tests for Z4D_decoders/z4d_decoder_Simple_Descriptor_Rsp.py

Covers:
  extract_basic_fields       – field slicing
  should_skip_message        – zero length or non-zero status
  is_valid_device            – ListOfDevices guard
  handle_special_device      – profile 0xC05E / device 0xE15E skip logic
  Decode8043 (integration)   – coordinator route, unknown device, normal flow
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Simple_Descriptor_Rsp"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI  = "a0"
ADDR = "1234"
EP   = "01"

# Message layout (Decode8043):
#   [0:2]   SQN
#   [2:4]   Status
#   [4:8]   ShortAddr
#   [8:10]  Length  (non-zero for valid message)
#   [10:12] Ep
#   [12:16] ProfileID
#   [16:20] DeviceID
#   [20:22] BField
#   [22:24] InClusterCount
#   [24:...]InClusters (4 chars each)
#   ...     OutClusterCount + OutClusters

def _make_8043(sqn="01", status="00", addr=ADDR, ep="01",
               profile="0104", device_id="0100", bfield="00",
               in_clusters=(), out_clusters=()):
    length = "01"  # non-zero to signal valid
    in_count = "%02x" % len(in_clusters)
    out_count = "%02x" % len(out_clusters)
    return (sqn + status + addr + length +
            ep + profile + device_id + bfield +
            in_count + "".join(in_clusters) +
            out_count + "".join(out_clusters))


# ─── Unit tests for helper functions ──────────────────────────────────────────

class TestExtractBasicFields:

    def test_extracts_sqn(self, mod, plugin):
        sqn, status, addr, length = mod.extract_basic_fields(plugin, _make_8043())
        assert sqn == "01"

    def test_extracts_addr(self, mod, plugin):
        _, _, addr, _ = mod.extract_basic_fields(plugin, _make_8043(addr="abcd"))
        assert addr == "abcd"

    def test_extracts_status(self, mod, plugin):
        _, status, _, _ = mod.extract_basic_fields(plugin, _make_8043(status="82"))
        assert status == "82"


class TestShouldSkipMessage:

    def test_zero_length_returns_true(self, mod, plugin):
        assert mod.should_skip_message(plugin, "00", "00") is True

    def test_nonzero_status_returns_true(self, mod, plugin):
        assert mod.should_skip_message(plugin, "01", "82") is True

    def test_valid_message_returns_false(self, mod, plugin):
        assert mod.should_skip_message(plugin, "01", "00") is False


class TestIsValidDevice:

    def test_unknown_device_returns_false(self, mod, plugin):
        plugin.ListOfDevices = {}
        assert mod.is_valid_device(plugin, "9999") is False

    def test_known_device_returns_true(self, mod, plugin):
        plugin.ListOfDevices["1234"] = {}
        assert mod.is_valid_device(plugin, "1234") is True


class TestHandleSpecialDevice:

    def test_profile_c05e_device_e15e_returns_true(self, mod, plugin):
        plugin.ListOfDevices[ADDR] = {"Ep": {"01": {}}, "NbEp": "2"}
        result = mod.handle_special_device(plugin, ADDR, "01", "c05e", "e15e")
        assert result is True

    def test_profile_c05e_removes_ep(self, mod, plugin):
        plugin.ListOfDevices[ADDR] = {"Ep": {"01": {}}, "NbEp": "2"}
        mod.handle_special_device(plugin, ADDR, "01", "c05e", "e15e")
        assert "01" not in plugin.ListOfDevices[ADDR]["Ep"]

    def test_profile_c05e_decrements_nbep(self, mod, plugin):
        plugin.ListOfDevices[ADDR] = {"Ep": {"01": {}}, "NbEp": "2"}
        mod.handle_special_device(plugin, ADDR, "01", "c05e", "e15e")
        assert plugin.ListOfDevices[ADDR]["NbEp"] == 1

    def test_normal_profile_returns_false(self, mod, plugin):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "NbEp": "1"}
        result = mod.handle_special_device(plugin, ADDR, "01", "0104", "0100")
        assert result is False


# ─── Integration: Decode8043 ──────────────────────────────────────────────────

class TestDecode8043Integration:

    def test_duplicate_sqn_returns_early(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=True))
        interview = MagicMock()
        monkeypatch.setattr(mod, "request_next_Ep", interview)
        mod.Decode8043(plugin, {}, _make_8043(), LQI)
        interview.assert_not_called()

    def test_zero_length_returns_early(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "request_next_Ep", MagicMock())
        # Build a message with length=00
        msg = "01" + "00" + ADDR + "00" + EP + "0104" + "0100" + "00" + "00" + "00"
        mod.Decode8043(plugin, {}, msg, LQI)

    def test_unknown_device_logs_and_returns(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "request_next_Ep", MagicMock())
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        mod.Decode8043(plugin, {}, _make_8043(), LQI)

    def test_coordinator_address_calls_receiveZigateEpDescriptor(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = {"Ep": {}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        recv = MagicMock()
        monkeypatch.setattr(mod, "receiveZigateEpDescriptor", recv)
        mod.Decode8043(plugin, {}, _make_8043(addr="0000"), LQI)
        recv.assert_called_once()

    def test_normal_device_populates_ep(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {EP: {}}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "updLQI", MagicMock())
        monkeypatch.setattr(mod, "updSQN", MagicMock())
        monkeypatch.setattr(mod, "request_next_Ep", MagicMock(return_value=False))
        msg = _make_8043(in_clusters=["0006"], out_clusters=["0006"])
        mod.Decode8043(plugin, {}, msg, LQI)
        assert "0006" in plugin.ListOfDevices[ADDR]["Ep"][EP]
