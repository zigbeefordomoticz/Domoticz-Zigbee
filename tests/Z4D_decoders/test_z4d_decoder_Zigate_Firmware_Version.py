"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Firmware_Version.py

Covers:
  Decode8010    – firmware version dispatch
  _zigate_firmware – Zigate-format parsing
  zigpy_firmware   – Zigpy-format parsing
  handle_firmware_branch – version-family dispatch
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock, patch

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Firmware_Version"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


# ─── _zigate_firmware ─────────────────────────────────────────────────────────

class TestZigateFirmware:

    def test_sets_major_version(self, mod, plugin):
        mod._zigate_firmware(plugin, "03" + "04" + "31c8")
        assert plugin.FirmwareMajorVersion == "04"

    def test_sets_firmware_version(self, mod, plugin):
        mod._zigate_firmware(plugin, "03" + "04" + "31c8")
        assert plugin.FirmwareVersion == "31c8"


# ─── zigpy_firmware ───────────────────────────────────────────────────────────

class TestZigpyFirmware:

    def test_sets_major_version(self, mod, plugin):
        mod.zigpy_firmware(plugin, "04" + "00" + "0002" + "20220101")
        assert plugin.FirmwareMajorVersion == "04"

    def test_sets_firmware_version(self, mod, plugin):
        mod.zigpy_firmware(plugin, "04" + "00" + "0002" + "20220101")
        assert plugin.FirmwareVersion == "20220101"


# ─── Decode8010 ───────────────────────────────────────────────────────────────

class TestDecode8010:

    def _setup(self, plugin, monkeypatch, mod):
        plugin.FirmwareBranch = "03"
        plugin.ListOfDevices.setdefault("0000", {"Model": {}})
        monkeypatch.setattr(mod, "set_display_firmware_version", MagicMock())

    def test_zigate_8char_msg_calls_zigate_firmware(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        fn = MagicMock()
        monkeypatch.setattr(mod, "_zigate_firmware", fn)
        mod.Decode8010(plugin, {}, "03" + "04" + "31c8", LQI)  # 8 chars = Zigate
        fn.assert_called_once()

    def test_zigpy_longer_msg_calls_zigpy_firmware(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        fn = MagicMock()
        monkeypatch.setattr(mod, "zigpy_firmware", fn)
        monkeypatch.setattr(mod, "_zigate_firmware", MagicMock())
        long_msg = "04" + "00" + "0002" + "20220101"  # 16 chars != 8
        mod.Decode8010(plugin, {}, long_msg, LQI)
        fn.assert_called_once()

    def test_sets_pdm_ready(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        monkeypatch.setattr(mod, "_zigate_firmware", MagicMock())
        plugin.PDMready = False
        mod.Decode8010(plugin, {}, "03" + "04" + "31c8", LQI)
        assert plugin.PDMready is True

    def test_creates_0000_entry_if_missing(self, mod, plugin, monkeypatch):
        self._setup(plugin, monkeypatch, mod)
        monkeypatch.setattr(mod, "_zigate_firmware", MagicMock())
        plugin.ListOfDevices = {}
        mod.Decode8010(plugin, {}, "03" + "04" + "31c8", LQI)
        assert "0000" in plugin.ListOfDevices


# ─── handle_firmware_branch ───────────────────────────────────────────────────

class TestHandleFirmwareBranch:

    def test_branch_98_logs_untested(self, mod, plugin):
        plugin.FirmwareBranch = "98"
        plugin.FirmwareMajorVersion = "03"
        plugin.FirmwareVersion = "1234"
        mod.handle_firmware_branch(plugin)
        assert any("Untested" in str(c) for c in plugin.log.logging.call_args_list)

    def test_branch_03_major_04_sets_model(self, mod, plugin):
        plugin.FirmwareBranch = "03"
        plugin.FirmwareMajorVersion = "04"
        plugin.FirmwareVersion = "31c8"
        plugin.ListOfDevices["0000"] = {"Model": {}}
        mod.handle_firmware_branch(plugin)
        assert "OptiPDM" in plugin.ListOfDevices["0000"]["Model"]
