"""
Tests for Z4D_decoders/z4d_decoder_Complex_Descriptor_Rsp.py

Decode8034 logs the complex descriptor fields.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Complex_Descriptor_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# Status(2 offset via [2:4]) + NetworkAddr(4) + ?(2) + XMLTag(2) + CountField(2) + FieldValues
MSG = "00" + "00" + "1234" + "00" + "01" + "02" + "aabbcc"
LQI = "ff"


class TestDecode8034:

    def test_logs_once(self, mod, plugin):
        mod.Decode8034(plugin, {}, MSG, LQI)
        assert plugin.log.logging.call_count >= 1

    def test_does_not_modify_list_of_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8034(plugin, {}, MSG, LQI)
        assert plugin.ListOfDevices == {}
