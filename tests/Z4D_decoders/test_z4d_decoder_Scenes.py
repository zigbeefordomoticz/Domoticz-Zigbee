"""
Tests for Z4D_decoders/z4d_decoder_Scenes.py

Covers Decode80A0–80A4 (log-only scene responses) and Decode80A5/80A6
which have lightweight conditional logic.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Scenes"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
ADDR = "1234"


# ─── Decode80A0–80A4: log-only responses ──────────────────────────────────────

@pytest.mark.parametrize("fn_name,msg", [
    ("Decode80A0", "01" + "01" + "0005" + "00" + "0001"),             # 14 chars
    ("Decode80A1", "01" + "01" + "0005" + "00" + "0001" + "01"),      # 16 chars
    ("Decode80A2", "01" + "01" + "0005" + "00" + "0001" + "01"),
    ("Decode80A3", "01" + "01" + "0005" + "00" + "0001"),
    ("Decode80A4", "01" + "01" + "0005" + "00" + "0001" + "01"),
])
class TestSceneLogOnlyDecoders:

    def test_logs_once(self, mod, plugin, fn_name, msg):
        fn = getattr(mod, fn_name)
        fn(plugin, {}, msg, LQI)
        assert plugin.log.logging.call_count >= 1

    def test_does_not_modify_devices(self, mod, plugin, fn_name, msg):
        plugin.ListOfDevices = {}
        fn = getattr(mod, fn_name)
        fn(plugin, {}, msg, LQI)
        assert plugin.ListOfDevices == {}


# ─── Decode80A5 – recall scene ────────────────────────────────────────────────

class TestDecode80A5:
    # Layout: ?(10) + SrcAddr(4) + ?(2) + GroupID(4) + SceneID(2)
    MSG_BASE = "00" * 5 + ADDR + "00" + "fff4" + "01"  # GroupID=fff4

    def test_unknown_device_returns_early(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        mj = MagicMock()
        monkeypatch.setattr(mod, "MajDomoDevice", mj)
        mod.Decode80A5(plugin, {}, self.MSG_BASE, LQI)
        mj.assert_not_called()

    def test_known_device_no_model_returns_early(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {}  # no 'Model' key
        mj = MagicMock()
        monkeypatch.setattr(mod, "MajDomoDevice", mj)
        mod.Decode80A5(plugin, {}, self.MSG_BASE, LQI)
        mj.assert_not_called()

    def test_wake_sleep_model_fff4_sends_off(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Model": "Remote switch Wake up Sleep"}
        mj = MagicMock()
        monkeypatch.setattr(mod, "MajDomoDevice", mj)
        mod.Decode80A5(plugin, {}, self.MSG_BASE, LQI)
        mj.assert_called_once_with(plugin, {}, ADDR, "01", "0008", "00")


# ─── Decode80A6 – scene membership response ──────────────────────────────────

class TestDecode80A6:
    # Layout: SQN(2)+EP(2)+Cluster(4)+Status(2)+Capacity(2)+GroupID(4)+SceneCount(2)+SceneList+SrcAddr(4)
    def _make_msg(self, status="00", capacity="0a", scene_count="00",
                  scene_list="", src_addr=ADDR):
        return ("01" + "01" + "0005" + status + capacity +
                "0001" + scene_count + scene_list + src_addr)

    def test_nonzero_status_logs_and_returns(self, mod, plugin):
        mod.Decode80A6(plugin, {}, self._make_msg(status="82"), LQI)
        assert any(c.args[1] == "Log" for c in plugin.log.logging.call_args_list)

    def test_scene_count_over_capacity_logs_and_returns(self, mod, plugin):
        mod.Decode80A6(plugin, {}, self._make_msg(capacity="01", scene_count="05"), LQI)
        assert any("MsgSceneCount" in str(c) or ">" in str(c)
                   for c in plugin.log.logging.call_args_list)

    def test_valid_empty_scene_list_logs(self, mod, plugin):
        mod.Decode80A6(plugin, {}, self._make_msg(), LQI)
        assert any(c.args[1] == "Log" for c in plugin.log.logging.call_args_list)
