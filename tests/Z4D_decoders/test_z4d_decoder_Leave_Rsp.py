"""
Tests for Z4D_decoders/z4d_decoder_Leave_Rsp.py

Decode8047 logs a Status message with LQI and status code.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Leave_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# Status at [2:4]
MSG = "00" + "00" + "ff"
LQI = "80"


class TestDecode8047:

    def test_logs_status(self, mod, plugin):
        mod.Decode8047(plugin, {}, MSG, LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)

    def test_does_not_modify_list_of_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8047(plugin, {}, MSG, LQI)
        assert plugin.ListOfDevices == {}
