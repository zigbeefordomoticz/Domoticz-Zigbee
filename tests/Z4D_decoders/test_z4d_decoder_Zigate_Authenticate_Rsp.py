"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Authenticate_Rsp.py

Decode8028 — log-only; parses authentication response fields and logs them.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Authenticate_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
# gatewayIEEE(16)+encKey(16)+mic(8)+nodeIEEE(16)+keySeq(2)+chan(2)+shortPAN(4)+extPAN(16)
MSG = (
    "1122334455667788"   # gateway IEEE
    + "aabbccddeeff0011"  # encrypt key
    + "00112233"          # mic
    + "ffeeddccbbaa9988"  # node IEEE
    + "01"                # active key seq
    + "0f"                # channel
    + "beef"              # short PAN id
    + "0011223344556677"  # extended PAN id
)


class TestDecode8028:

    def test_logs(self, mod, plugin):
        mod.Decode8028(plugin, {}, MSG, LQI)
        assert plugin.log.logging.called

    def test_does_not_modify_list_of_devices(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8028(plugin, {}, MSG, LQI)
        assert plugin.ListOfDevices == {}
