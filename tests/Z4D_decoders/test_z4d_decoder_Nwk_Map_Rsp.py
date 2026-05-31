"""
Tests for Z4D_decoders/z4d_decoder_Nwk_Map_Rsp.py

Decode804E delegates to self.networkmap.LQIresp when networkmap is set.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Nwk_Map_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
MSG = "deadbeef"


class TestDecode804E:

    def test_with_networkmap_calls_lqiresp(self, mod, plugin):
        plugin.networkmap = MagicMock()
        mod.Decode804E(plugin, {}, MSG, LQI)
        plugin.networkmap.LQIresp.assert_called_once_with(MSG)

    def test_without_networkmap_does_not_crash(self, mod, plugin):
        plugin.networkmap = None
        mod.Decode804E(plugin, {}, MSG, LQI)

    def test_logs_debug(self, mod, plugin):
        plugin.networkmap = None
        mod.Decode804E(plugin, {}, MSG, LQI)
        assert any(c.args[1] == "Debug" for c in plugin.log.logging.call_args_list)
