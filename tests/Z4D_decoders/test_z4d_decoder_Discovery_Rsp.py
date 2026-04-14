"""
Tests for Z4D_decoders/z4d_decoder_Discovery_Rsp.py

Decode804B logs system server discovery response fields.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Discovery_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# SQN(2) + Status(2) + ServerMask(4)
MSG = "01" + "00" + "1234"
LQI = "ff"


class TestDecode804B:

    def test_logs_once(self, mod, plugin):
        mod.Decode804B(plugin, {}, MSG, LQI)
        assert plugin.log.logging.call_count >= 1

    def test_does_not_modify_list_of_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode804B(plugin, {}, MSG, LQI)
        assert plugin.ListOfDevices == {}
