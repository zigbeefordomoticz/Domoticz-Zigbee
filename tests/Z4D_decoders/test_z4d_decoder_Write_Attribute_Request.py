"""
Tests for Z4D_decoders/z4d_decoder_Write_Attribute_Request.py

Decode0110 — write attribute request; logs each attribute, calls updLQI.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Write_Attribute_Request"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"

# Valid message layout:
# sqn(2)+srcAddr(4)+srcEp(2)+dstEp(2)+clusterId(4)+direction(2)+manufFlag(2)+
# manufCode(4)+nbAttr(2) = 24 chars, then attribute entries
# Each attribute: attrId(4)+dataType(2)+length(4)+value(length*2)
def _msg(clusterId="0006", nb="01", attr_data="0000" + "20" + "0001" + "ff"):
    return (
        "01"       # sqn
        + "abcd"   # srcAddr
        + "01"     # srcEp
        + "01"     # dstEp
        + clusterId
        + "00"     # direction
        + "00"     # manufFlag
        + "0000"   # manufCode
        + nb
        + attr_data
    )


class TestDecode0110:

    def test_short_message_logs_error(self, mod, plugin):
        mod.Decode0110(plugin, {}, "0102", LQI)
        assert any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)

    def test_short_message_returns_early(self, mod, plugin, monkeypatch):
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        mod.Decode0110(plugin, {}, "0102", LQI)
        upd.assert_not_called()

    def test_valid_message_calls_upd_lqi(self, mod, plugin, monkeypatch):
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        mod.Decode0110(plugin, {}, _msg(), LQI)
        upd.assert_called()

    def test_valid_message_logs_attribute(self, mod, plugin):
        mod.Decode0110(plugin, {}, _msg(), LQI)
        # Should log at least one Debug entry mentioning attribute info
        assert plugin.log.logging.called
