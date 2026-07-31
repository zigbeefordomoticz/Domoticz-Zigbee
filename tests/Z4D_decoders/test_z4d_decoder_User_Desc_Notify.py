"""
Tests for Z4D_decoders/z4d_decoder_User_Desc_Notify.py

Decode802B / Decode802C — log-only decoders; no device state is modified.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_User_Desc_Notify"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"

# sqn(2) + status(2) + nwkid(4)
MSG_802B = "01" + "00" + "1234"
# sqn(2) + status(2) + nwkid(4) + length(2) + data
MSG_802C = "01" + "00" + "1234" + "03" + "414243"


class TestDecode802B:

    def test_logs(self, mod, plugin):
        mod.Decode802B(plugin, {}, MSG_802B, LQI)
        assert plugin.log.logging.called

    def test_does_not_modify_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode802B(plugin, {}, MSG_802B, LQI)
        assert plugin.ListOfDevices == {}


class TestDecode802C:

    def test_logs(self, mod, plugin):
        mod.Decode802C(plugin, {}, MSG_802C, LQI)
        assert plugin.log.logging.called

    def test_does_not_modify_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode802C(plugin, {}, MSG_802C, LQI)
        assert plugin.ListOfDevices == {}
