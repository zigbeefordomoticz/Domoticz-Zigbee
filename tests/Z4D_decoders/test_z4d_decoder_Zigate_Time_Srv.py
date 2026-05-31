"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Time_Srv.py

Decode8017 — compares UTC time with the coordinator's reported time.
If abs(UTC - ZigateTime) > 5 seconds, calls setTimeServer(self).
"""

import sys
import importlib
import struct
from datetime import datetime
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Time_Srv"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


def _encode_zigate_time(seconds_from_2000: int) -> str:
    """Pack an integer into the 8-hex-char little-endian format Decode8017 expects."""
    return "%08x" % struct.unpack("I", struct.pack("I", seconds_from_2000))[0]


class TestDecode8017:

    def test_in_sync_does_not_call_set_time_server(self, mod, plugin, monkeypatch):
        """Deviation ≤ 5 s → setTimeServer must NOT be called."""
        set_time = MagicMock()
        monkeypatch.setattr(mod, "setTimeServer", set_time)

        epoc = datetime(2000, 1, 1)
        utc_now = int((datetime.now() - epoc).total_seconds())
        # Send a time only 2 seconds off — well within tolerance
        zigate_hex = _encode_zigate_time(utc_now + 2)

        mod.Decode8017(plugin, {}, zigate_hex, LQI)
        set_time.assert_not_called()

    def test_out_of_sync_calls_set_time_server(self, mod, plugin, monkeypatch):
        """Deviation > 5 s (epoch 0 is always far from now) → setTimeServer called."""
        set_time = MagicMock()
        monkeypatch.setattr(mod, "setTimeServer", set_time)

        mod.Decode8017(plugin, {}, "00000000", LQI)
        set_time.assert_called_once_with(plugin)

    def test_logs_debug(self, mod, plugin, monkeypatch):
        monkeypatch.setattr(mod, "setTimeServer", MagicMock())
        mod.Decode8017(plugin, {}, "00000000", LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)
