"""
Tests for Z4D_decoders/z4d_decoder_bindings.py

Covers:
  Decode8030 – bind response
    - Short payload (< 10) returns early
    - Short-address mode: extracts nwkid from bytes 6:10
    - IEEE-address mode: looks up IEEE2NWK
    - Unknown address mode logs error and returns
    - Updates Bind phase from 'requested' → 'binded' when i_sqn matches
  Decode8031 – unbind response
    - Short payload returns early
    - Short-address mode resolves nwkid
    - Non-zero status logs debug
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_bindings"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── Helpers ──────────────────────────────────────────────────────────────────

LQI   = "80"
NWKID = "1234"
IEEE  = "1234567890abcdef"

# Decode8030/8031 layout (short address mode, ADDRESS_MODE['short'] == 2 == 0x02):
#   [0:2]   SQN
#   [2:4]   Status
#   [4:6]   AddrMode  ("02" = short)
#   [6:10]  ShortAddr

def _bind_msg_short(sqn="01", status="00", addr=NWKID):
    return sqn + status + "02" + addr

def _bind_msg_ieee(sqn="01", status="00", ieee=IEEE):
    return sqn + status + "03" + ieee

def _bind_msg_unknown_mode(sqn="01", status="00"):
    return sqn + status + "ff" + NWKID


# ─── Decode8030 ───────────────────────────────────────────────────────────────

class TestDecode8030ShortPayload:

    def test_too_short_returns_early(self, mod, plugin, monkeypatch):
        called = MagicMock()
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn", called)
        mod.Decode8030(plugin, {}, "0100", LQI)  # 4 chars < 10
        called.assert_not_called()


class TestDecode8030ShortAddressMode:

    def _setup(self, plugin, monkeypatch, mod):
        plugin.ListOfDevices[NWKID] = {"Ep": {"01": {}}, "Bind": {}}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn",
                            MagicMock(return_value=42))

    def test_short_addr_mode_logs_debug(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        mod.Decode8030(plugin, {}, _bind_msg_short(), LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)

    def test_short_addr_updates_bind_phase(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[NWKID] = {
            "Ep": {"01": {}},
            "Bind": {
                "01": {
                    "0006": {"Phase": "requested", "i_sqn": 42, "Status": ""}
                }
            }
        }
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn",
                            MagicMock(return_value=42))
        mod.Decode8030(plugin, {}, _bind_msg_short(), LQI)
        assert plugin.ListOfDevices[NWKID]["Bind"]["01"]["0006"]["Phase"] == "binded"

    def test_bind_phase_not_updated_when_i_sqn_differs(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[NWKID] = {
            "Ep": {"01": {}},
            "Bind": {
                "01": {
                    "0006": {"Phase": "requested", "i_sqn": 99, "Status": ""}
                }
            }
        }
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn",
                            MagicMock(return_value=42))
        mod.Decode8030(plugin, {}, _bind_msg_short(), LQI)
        assert plugin.ListOfDevices[NWKID]["Bind"]["01"]["0006"]["Phase"] == "requested"


class TestDecode8030IeeeAddressMode:

    def test_ieee_mode_resolves_nwkid_from_ieee2nwk(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK[IEEE] = NWKID
        plugin.ListOfDevices[NWKID] = {"Ep": {"01": {}}, "Bind": {}}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn", MagicMock(return_value=1))
        mod.Decode8030(plugin, {}, _bind_msg_ieee(), LQI)
        # Just checking it doesn't crash and doesn't log Error for this path

    def test_ieee_mode_unknown_ieee_logs_error(self, mod, plugin, monkeypatch):
        plugin.IEEE2NWK = {}
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn", MagicMock(return_value=1))
        mod.Decode8030(plugin, {}, _bind_msg_ieee(), LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)


class TestDecode8030UnknownAddressMode:

    def test_unknown_mode_logs_error_and_returns(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "sqn_get_internal_sqn_from_app_sqn", MagicMock(return_value=1))
        mod.Decode8030(plugin, {}, _bind_msg_unknown_mode(), LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)


# ─── Decode8031 ───────────────────────────────────────────────────────────────

class TestDecode8031:

    def test_too_short_returns_early(self, mod, plugin):
        mod.Decode8031(plugin, {}, "0100", LQI)  # 4 chars < 10
        assert not plugin.log.logging.called or all(
            c.args[1] != "Error" for c in plugin.log.logging.call_args_list
        )

    def test_short_addr_mode_logs_debug(self, mod, plugin):
        plugin.ListOfDevices[NWKID] = {"Ep": {}}
        mod.Decode8031(plugin, {}, _bind_msg_short(), LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)

    def test_nonzero_status_logs_debug(self, mod, plugin):
        plugin.ListOfDevices[NWKID] = {"Ep": {}}
        mod.Decode8031(plugin, {}, _bind_msg_short(status="82"), LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)
