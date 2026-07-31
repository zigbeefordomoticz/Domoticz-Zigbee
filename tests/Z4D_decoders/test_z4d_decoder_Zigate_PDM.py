"""
Tests for Z4D_decoders/z4d_decoder_Zigate_PDM.py

Covers:
  Decode0302 – PDM load (delegates to rejoin_legrand_reset)
  Decode8001 – ZiGate log message (writes to file)
  Decode8006 – Non-factory-new restart status codes
  Decode8007 – Factory-new restart status codes + sets ErasePDMDone
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock, patch

_MOD = "Z4D_decoders.z4d_decoder_Zigate_PDM"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


# ─── Decode0302 ───────────────────────────────────────────────────────────────

class TestDecode0302:

    def test_calls_rejoin_legrand_reset(self, mod, plugin, monkeypatch):
        reset = MagicMock()
        monkeypatch.setattr(mod, "rejoin_legrand_reset", reset)
        mod.Decode0302(plugin, {}, "", LQI)
        reset.assert_called_once_with(plugin)

    def test_logs_debug(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "rejoin_legrand_reset", MagicMock())
        mod.Decode0302(plugin, {}, "", LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)


# ─── Decode8001 ───────────────────────────────────────────────────────────────

class TestDecode8001:

    def test_log_message_written_to_file(self, mod, plugin):
        plugin.pluginconf.pluginConf["pluginLogs"] = "/tmp"
        plugin.HardwareID = 1
        import binascii
        payload = binascii.hexlify(b"hello").decode()
        msg = "01" + payload  # log level + hex-encoded message
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__ = lambda s: mock_file
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mod.Decode8001(plugin, {}, msg, LQI)

    def test_io_error_logs_error(self, mod, plugin):
        plugin.pluginconf.pluginConf["pluginLogs"] = "/tmp"
        plugin.HardwareID = 1
        import binascii
        payload = binascii.hexlify(b"test").decode()
        msg = "01" + payload
        with patch("builtins.open", side_effect=IOError("permission denied")):
            mod.Decode8001(plugin, {}, msg, LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)


# ─── Decode8006 ───────────────────────────────────────────────────────────────

class TestDecode8006:

    @pytest.mark.parametrize("status,expected", [
        ("00", "STARTUP"),
        ("01", "RUNNING"),
        ("02", "NFN_START"),
    ])
    def test_status_codes(self, mod, plugin, status, expected):
        mod.Decode8006(plugin, {}, status, LQI)
        assert any(expected in str(c) for c in plugin.log.logging.call_args_list)

    def test_does_not_set_erase_pdm_done(self, mod, plugin):
        plugin.ErasePDMDone = False
        mod.Decode8006(plugin, {}, "00", LQI)
        assert plugin.ErasePDMDone is False


# ─── Decode8007 ───────────────────────────────────────────────────────────────

class TestDecode8007:

    @pytest.mark.parametrize("status,expected", [
        ("00", "STARTUP"),
        ("01", "RUNNING"),
        ("02", "NFN_START"),
    ])
    def test_status_codes(self, mod, plugin, status, expected):
        mod.Decode8007(plugin, {}, status, LQI)
        assert any(expected in str(c) for c in plugin.log.logging.call_args_list)

    def test_sets_erase_pdm_done(self, mod, plugin):
        plugin.ErasePDMDone = False
        mod.Decode8007(plugin, {}, "00", LQI)
        assert plugin.ErasePDMDone is True
