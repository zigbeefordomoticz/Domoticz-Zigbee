"""
Tests for Z4D_decoders/z4d_decoder_Power_Descriptor_Rsp.py

Decode8044 logs power descriptor fields.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Power_Descriptor_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# SQN(2)+Status(2)+bit_fields(4) = 8 chars
MSG = "01" + "00" + "1234"
LQI = "ff"


class TestDecode8044:

    def test_logs_debug(self, mod, plugin):
        mod.Decode8044(plugin, {}, MSG, LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)

    def test_does_not_modify_list_of_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8044(plugin, {}, MSG, LQI)
        assert plugin.ListOfDevices == {}
