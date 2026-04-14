"""
Tests for Z4D_decoders/z4d_decoder_OTA_Rsp.py

Decode8501 / 8502 / 8503 — delegate to self.OTA methods when OTA is set.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_OTA_Rsp"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
MSG = "0102030405060708"


class TestDecode8501:

    def test_with_ota_calls_block_request(self, mod, plugin):
        plugin.OTA = MagicMock()
        mod.Decode8501(plugin, {}, MSG, LQI)
        plugin.OTA.ota_image_block_request.assert_called_once_with(MSG)

    def test_without_ota_no_crash(self, mod, plugin):
        plugin.OTA = None
        mod.Decode8501(plugin, {}, MSG, LQI)  # must not raise


class TestDecode8502:

    def test_with_ota_calls_page_request(self, mod, plugin):
        plugin.OTA = MagicMock()
        mod.Decode8502(plugin, {}, MSG, LQI)
        plugin.OTA.ota_image_page_request.assert_called_once_with(MSG)

    def test_without_ota_no_crash(self, mod, plugin):
        plugin.OTA = None
        mod.Decode8502(plugin, {}, MSG, LQI)


class TestDecode8503:

    def test_with_ota_calls_upgrade_end(self, mod, plugin):
        plugin.OTA = MagicMock()
        mod.Decode8503(plugin, {}, MSG, LQI)
        plugin.OTA.ota_upgrade_end_request.assert_called_once_with(MSG)

    def test_without_ota_no_crash(self, mod, plugin):
        plugin.OTA = None
        mod.Decode8503(plugin, {}, MSG, LQI)
