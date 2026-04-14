"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Heartbeat.py

Decode8008 logs a Debug message and does nothing else.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Heartbeat"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


class TestDecode8008:

    def test_logs_debug(self, mod, plugin):
        mod.Decode8008(plugin, {}, "heartbeat_data", LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)

    def test_does_not_raise_on_empty_data(self, mod, plugin):
        mod.Decode8008(plugin, {}, "", LQI)

    def test_does_not_modify_list_of_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8008(plugin, {}, "data", LQI)
        assert plugin.ListOfDevices == {}
