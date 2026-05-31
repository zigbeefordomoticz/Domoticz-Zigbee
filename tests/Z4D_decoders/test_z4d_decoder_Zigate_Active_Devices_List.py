"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Active_Devices_List.py

Decode8015 — iterates active device entries; logs and updates LQI for known
devices, logs "not found" for unknown ones.  Skips coordinator (saddr=0000)
and zero-IEEE entries.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Active_Devices_List"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"


def _entry(devid="01", saddr="abcd", ieee="1122334455667788",
           power="04", rssi="50"):
    """Build one 26-char active-device entry."""
    return devid + saddr + ieee + power + rssi


class TestDecode8015:

    def test_empty_data_logs_status(self, mod, plugin):
        plugin.ListOfDevices = {}
        mod.Decode8015(plugin, {}, "", LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)

    def test_coordinator_saddr_skipped(self, mod, plugin):
        """saddr == '0000' must be skipped with no device update."""
        plugin.ListOfDevices = {}
        mod.Decode8015(plugin, {}, _entry(saddr="0000"), LQI)
        # No LQI key should have been written to any device
        assert plugin.ListOfDevices == {}

    def test_zero_ieee_skipped(self, mod, plugin):
        """All-zero IEEE must be skipped (continue)."""
        plugin.ListOfDevices = {}
        mod.Decode8015(plugin, {}, _entry(ieee="0000000000000000", saddr="abcd"), LQI)
        # The entry is skipped before DeviceExist; no crash expected

    def test_known_device_updates_lqi(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {"abcd": {"ZDeviceName": "Lamp", "Model": "LAMP01"}}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=True))
        mod.Decode8015(plugin, {}, _entry(saddr="abcd", rssi="50"), LQI)
        assert plugin.ListOfDevices["abcd"]["LQI"] == int("50", 16)

    def test_known_device_logs_status(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {"abcd": {"ZDeviceName": {}, "Model": {}}}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=True))
        mod.Decode8015(plugin, {}, _entry(saddr="abcd"), LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)

    def test_unknown_device_logs_not_found(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "DeviceExist", MagicMock(return_value=False))
        mod.Decode8015(plugin, {}, _entry(saddr="abcd"), LQI)
        assert any(
            "not found" in str(c).lower()
            for c in plugin.log.logging.call_args_list
        )
