"""
Tests for Z4D_decoders/z4d_decoder_Device_Annoucement.py

Decode004D simply delegates to device_annoucementv2.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Device_Annoucement"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
MSG = "1234567890abcdef00"


class TestDecode004D:

    def test_delegates_to_device_annoucementv2(self, mod, plugin, monkeypatch):
        fn = MagicMock()
        monkeypatch.setattr(mod, "device_annoucementv2", fn)
        mod.Decode004D(plugin, {}, MSG, LQI)
        fn.assert_called_once_with(plugin, {}, MSG, LQI)

    def test_passes_all_args(self, mod, plugin, monkeypatch):
        fn = MagicMock()
        monkeypatch.setattr(mod, "device_annoucementv2", fn)
        devices = {"unit": "test"}
        mod.Decode004D(plugin, devices, MSG, LQI)
        fn.assert_called_once_with(plugin, devices, MSG, LQI)
