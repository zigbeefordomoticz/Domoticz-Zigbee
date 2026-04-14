"""
Tests for Z4D_decoders/z4d_decoder_Default_Rsp.py

Decode8101 logs a Debug message with parsed fields.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Default_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# SQN(2)+EP(2)+Cluster(4)+Command(2)+Status(2) = 12 chars
MSG = "01" + "01" + "0006" + "01" + "00"
LQI = "ff"


class TestDecode8101:

    def test_logs_debug(self, mod, plugin):
        mod.Decode8101(plugin, {}, MSG, LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)

    def test_does_not_log_error(self, mod, plugin):
        mod.Decode8101(plugin, {}, MSG, LQI)
        assert not any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_does_not_modify_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8101(plugin, {}, MSG, LQI)
        assert plugin.ListOfDevices == {}
