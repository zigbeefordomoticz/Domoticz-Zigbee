"""
Tests for Z4D_decoders/z4d_decoder_Active_Ep_Rsp.py

Covers Decode8045:
  - Payload length validation
  - Duplicate SQN short-circuit
  - Coordinator address (0000) route
  - Unknown device guard
  - Already-paired device guard (status inDB / erasePDM)
  - Normal device: endpoint registration, LQI/SQN updates,
    interview_state_8045 callback
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Active_Ep_Rsp"

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── Message layout ───────────────────────────────────────────────────────────
#
#   [0:2]   SQN
#   [2:4]   Status
#   [4:8]   ShortAddr
#   [8:10]  EpCount
#   [10:]   EpList (2 chars per endpoint)

SQN    = "01"
STATUS = "00"
ADDR   = "abcd"
LQI    = "a0"

def _make_msg(addr=ADDR, ep_list=("01",), sqn=SQN, status=STATUS):
    ep_count = "%02x" % len(ep_list)
    return sqn + status + addr + ep_count + "".join(ep_list)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestDecode8045PayloadValidation:

    def test_too_short_logs_error(self, mod, plugin):
        mod.Decode8045(plugin, {}, "01ab", LQI)  # 4 chars < 8
        assert any(
            c.args[1] == "Error"
            for c in plugin.log.logging.call_args_list
        )

    def test_too_short_returns_early(self, mod, plugin, monkeypatch):
        called = []
        monkeypatch.setattr(mod, "is_duplicate_sqn", lambda *a: called.append("dup") or False)
        mod.Decode8045(plugin, {}, "01ab", LQI)
        # is_duplicate_sqn should NOT be reached
        assert called == []


class TestDecode8045DuplicateSqn:

    def test_duplicate_sqn_logs_and_returns(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=True))
        updSQN = MagicMock()
        monkeypatch.setattr(mod, "updSQN", updSQN)
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        updSQN.assert_not_called()

    def test_no_duplicate_continues(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        updSQN = MagicMock()
        monkeypatch.setattr(mod, "updSQN", updSQN)
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=True))
        monkeypatch.setattr(mod, "interview_state_8045", MagicMock())
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        updSQN.assert_called()


class TestDecode8045CoordinatorAddress:

    def test_coordinator_addr_calls_receiveZigateEpList(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        recv = MagicMock()
        monkeypatch.setattr(mod, "receiveZigateEpList", recv)
        msg = SQN + STATUS + "0000" + "01" + "01"  # addr=0000
        mod.Decode8045(plugin, {}, msg, LQI)
        recv.assert_called_once()

    def test_coordinator_addr_returns_early(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "receiveZigateEpList", MagicMock())
        interview = MagicMock()
        monkeypatch.setattr(mod, "interview_state_8045", interview)
        msg = SQN + STATUS + "0000" + "01" + "01"
        mod.Decode8045(plugin, {}, msg, LQI)
        interview.assert_not_called()


class TestDecode8045UnknownDevice:

    def test_unknown_device_logs_and_returns(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=False))
        interview = MagicMock()
        monkeypatch.setattr(mod, "interview_state_8045", interview)
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        interview.assert_not_called()


class TestDecode8045AlreadyPairedDevice:

    @pytest.mark.parametrize("status", ["inDB", "erasePDM"])
    def test_already_paired_returns_early(self, mod, plugin, monkeypatch, status):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": status}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=True))
        interview = MagicMock()
        monkeypatch.setattr(mod, "interview_state_8045", interview)
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        interview.assert_not_called()


class TestDecode8045NormalDevice:

    def _setup(self, plugin, monkeypatch, mod):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8043"}
        monkeypatch.setattr(mod, "is_duplicate_sqn", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=True))

    def test_sets_device_status_to_8045(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        monkeypatch.setattr(mod, "interview_state_8045", MagicMock())
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        assert plugin.ListOfDevices[ADDR]["Status"] == "8045"

    def test_updates_lqi(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        ulqi = MagicMock()
        monkeypatch.setattr(mod, "updLQI", ulqi)
        monkeypatch.setattr(mod, "interview_state_8045", MagicMock())
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        ulqi.assert_called_with(plugin, ADDR, LQI)

    def test_registers_endpoint_in_device(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        monkeypatch.setattr(mod, "interview_state_8045", MagicMock())
        mod.Decode8045(plugin, {}, _make_msg(ep_list=["01", "02"]), LQI)
        assert "01" in plugin.ListOfDevices[ADDR]["Ep"]
        assert "02" in plugin.ListOfDevices[ADDR]["Ep"]

    def test_updates_nbep(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        monkeypatch.setattr(mod, "interview_state_8045", MagicMock())
        mod.Decode8045(plugin, {}, _make_msg(ep_list=["01", "02", "03"]), LQI)
        assert plugin.ListOfDevices[ADDR]["NbEp"] == "3"

    def test_calls_interview_state(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        interview = MagicMock()
        monkeypatch.setattr(mod, "interview_state_8045", interview)
        mod.Decode8045(plugin, {}, _make_msg(), LQI)
        interview.assert_called_once_with(plugin, ADDR, RIA=None, status=None)
