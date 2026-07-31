"""
Tests for Z4D_decoders/z4d_decoder_Data_Indication.py

Decode8002 — APS data indication; parses address modes and dispatches.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Data_Indication"

LQI  = "ff"
ADDR = "abcd"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


def _short_short_msg(src=ADDR, dst="0001", profile="0104", cluster="0006",
                     payload="000100ff"):
    """
    Build a minimal data-indication frame with short src + short dst.
    Layout: reserved(2)+profileId(4)+clusterId(4)+srcEp(2)+dstEp(2)+
            srcAddrMode(2='02')+srcAddr(4)+dstAddrMode(2='02')+dstAddr(4)+payload
    Total before payload: 2+4+4+2+2+2+4+2+4 = 26 chars
    """
    return (
        "00"        # reserved
        + profile   # profileId
        + cluster   # clusterId
        + "01"      # srcEp
        + "01"      # dstEp
        + "02"      # srcAddrMode = short
        + src       # srcAddr (4 chars)
        + "02"      # dstAddrMode = short
        + dst       # dstAddr (4 chars)
        + payload
    )


class TestDecode8002:

    def test_too_short_logs_error(self, mod, plugin):
        mod.Decode8002(plugin, {}, "0102030405", LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_unexpected_src_mode_logs(self, mod, plugin):
        # srcAddrMode = 0xff (unknown)
        msg = (
            "00" + "0104" + "0006" + "01" + "01"
            + "ff"          # unknown srcAddrMode
            + "abcd" + "02" + "0001" + "00000000"
        )
        plugin.log.logging.reset_mock()
        mod.Decode8002(plugin, {}, msg, LQI)
        assert any(c.args[1] in ("Log", "Error") for c in plugin.log.logging.call_args_list)

    def test_unknown_srcnwkid_returns_without_timestamped(self, mod, plugin, monkeypatch):
        """Source address not in ListOfDevices → returns after Debug log."""
        plugin.ListOfDevices = {}
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        msg = _short_short_msg(src="ffff", payload="00000000")
        mod.Decode8002(plugin, {}, msg, LQI)
        ts.assert_not_called()

    def test_known_device_calls_timestamped(self, mod, plugin, monkeypatch):
        """Known srcnwkid → timeStamped and updLQI called."""
        plugin.ListOfDevices = {ADDR: {"Manufacturer": "1234", "Manufacturer Name": "Acme"}}
        ts = MagicMock()
        upd = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        monkeypatch.setattr(mod, "updLQI", upd)
        monkeypatch.setattr(mod, "retreive_cmd_payload_from_8002",
                            MagicMock(return_value=(False, False, "01", "0000", "00", "")))
        monkeypatch.setattr(mod, "set_health_after_message_received", MagicMock())
        monkeypatch.setattr(mod, "inRawAps", MagicMock())
        monkeypatch.setattr(mod, "callbackDeviceAwake", MagicMock())
        msg = _short_short_msg(src=ADDR, payload="00000000")
        mod.Decode8002(plugin, {}, msg, LQI)
        ts.assert_called()

    def test_short_payload_logs_error(self, mod, plugin, monkeypatch):
        """Payload < 4 chars after address parsing → Error log."""
        plugin.ListOfDevices = {ADDR: {}}
        monkeypatch.setattr(mod, "set_health_after_message_received", MagicMock())
        msg = _short_short_msg(src=ADDR, payload="00")   # only 2 chars payload
        plugin.log.logging.reset_mock()
        mod.Decode8002(plugin, {}, msg, LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)
