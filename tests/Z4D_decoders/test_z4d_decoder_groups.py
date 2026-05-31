"""
Tests for Z4D_decoders/z4d_decoder_groups.py

Covers Decode8060–8063 – all delegate to self.groupmgt when set.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_groups"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
MSG = "01001234"


@pytest.mark.parametrize("fn_name,delegate_method", [
    ("Decode8060", "add_group_member_ship_response"),
    ("Decode8061", "check_group_member_ship_response"),
    ("Decode8062", "look_for_group_member_ship_response"),
    ("Decode8063", "remove_group_member_ship_response"),
])
class TestGroupDecoders:

    def test_with_groupmgt_delegates(self, mod, plugin, fn_name, delegate_method):
        plugin.groupmgt = MagicMock()
        fn = getattr(mod, fn_name)
        fn(plugin, {}, MSG, LQI)
        getattr(plugin.groupmgt, delegate_method).assert_called_once_with(MSG)

    def test_without_groupmgt_does_not_crash(self, mod, plugin, fn_name, delegate_method):
        plugin.groupmgt = None
        fn = getattr(mod, fn_name)
        fn(plugin, {}, MSG, LQI)  # should not raise
