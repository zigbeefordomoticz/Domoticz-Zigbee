"""
Tests for Z4D_decoders/z4d_decoder_Nwk_Scan_Rsp.py

Decode804A delegates to networkenergy.NwkScanResponse when set.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Nwk_Scan_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
MSG = "deadbeef"


@pytest.fixture(scope="module")
def _stub_networkenergy(mod):
    """Ensure networkenergy is available as an attribute on the module (if needed)."""
    return mod


class TestDecode804A:

    def test_with_networkenergy_calls_delegate(self, mod, plugin):
        plugin.networkenergy = MagicMock()
        mod.Decode804A(plugin, {}, MSG, LQI)
        plugin.networkenergy.NwkScanResponse.assert_called_once_with(MSG)

    def test_without_networkenergy_does_not_crash(self, mod, plugin):
        plugin.networkenergy = None
        mod.Decode804A(plugin, {}, MSG, LQI)
