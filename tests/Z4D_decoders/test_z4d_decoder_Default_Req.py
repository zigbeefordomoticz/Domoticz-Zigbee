"""
Tests for Z4D_decoders/z4d_decoder_Default_Req.py

Covers Decode7000:
  - Unknown device returns without sending response
  - Known device with bDisableDefaultResponse == '00' sends response
  - Known device with bDisableDefaultResponse != '00' does NOT send response
  - Logs debug for known devices
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Default_Req"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── Message layout ───────────────────────────────────────────────────────────
#
#   [0:4]   uSrcAddress
#   [4:6]   u8SrcEndpoint
#   [6:10]  u16ClusterId
#   [10:12] bDirection
#   [12:14] bDisableDefaultResponse
#   [14:16] bManufacturerSpecific
#   [16:18] eFrameType
#   [18:22] u16ManufacturerCode
#   [22:24] u8CommandIdentifier
#   [24:26] u8TransactionSequenceNumber

ADDR = "1234"
LQI  = "ff"

def _make_msg(addr=ADDR, disable_default="00", cluster="0006"):
    return (addr + "01" + cluster + "00" + disable_default +
            "00" + "01" + "0000" + "01" + "01")


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestDecode7000:

    def test_unknown_device_does_not_call_send_default_response(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        send = MagicMock()
        monkeypatch.setattr(mod, "send_default_response", send)
        mod.Decode7000(plugin, {}, _make_msg(), LQI)
        send.assert_not_called()

    def test_unknown_device_no_log(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "send_default_response", MagicMock())
        mod.Decode7000(plugin, {}, _make_msg(), LQI)
        plugin.log.logging.assert_not_called()

    def test_known_device_with_response_enabled_calls_send(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        send = MagicMock()
        monkeypatch.setattr(mod, "send_default_response", send)
        mod.Decode7000(plugin, {}, _make_msg(disable_default="00"), LQI)
        send.assert_called_once()

    def test_known_device_with_response_disabled_no_send(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        send = MagicMock()
        monkeypatch.setattr(mod, "send_default_response", send)
        mod.Decode7000(plugin, {}, _make_msg(disable_default="01"), LQI)
        send.assert_not_called()

    def test_known_device_logs_debug(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        monkeypatch.setattr(mod, "send_default_response", MagicMock())
        mod.Decode7000(plugin, {}, _make_msg(), LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)
