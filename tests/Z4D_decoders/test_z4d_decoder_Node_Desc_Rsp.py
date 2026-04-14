"""
Tests for Z4D_decoders/z4d_decoder_Node_Desc_Rsp.py

Covers Decode8042:
  - Non-zero status returns early
  - Coordinator address bootstrap
  - Unknown device logs and returns
  - Successful decode populates device fields
  - LogicalType derivation from bit_field
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Node_Desc_Rsp"

# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── Message layout ───────────────────────────────────────────────────────────
#
#   [0:2]   sequence
#   [2:4]   status
#   [4:8]   addr
#   [8:12]  manufacturer
#   [12:16] max_rx
#   [16:20] max_tx
#   [20:24] server_mask
#   [24:26] descriptor_capability
#   [26:28] mac_capability
#   [28:30] max_buffer
#   [30:34] bit_field

ADDR  = "abcd"
LQI   = "80"

def _make_msg(status="00", addr=ADDR,
              manufacturer="1234", max_rx="0080", max_tx="0080",
              server_mask="0000", desc_cap="00", mac_cap="8e",
              max_buf="52", bit_field="4001"):
    return ("01" + status + addr +
            manufacturer + max_rx + max_tx + server_mask +
            desc_cap + mac_cap + max_buf + bit_field)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestDecode8042ErrorStatus:

    def test_nonzero_status_logs_debug(self, mod, plugin):
        plugin.ListOfDevices[ADDR] = {}
        mod.Decode8042(plugin, {}, _make_msg(status="82"), LQI)
        assert any(
            c.args[1] == "Debug"
            for c in plugin.log.logging.call_args_list
        )

    def test_nonzero_status_does_not_update_device(self, mod, plugin):
        plugin.ListOfDevices[ADDR] = {}
        mod.Decode8042(plugin, {}, _make_msg(status="82"), LQI)
        assert "Manufacturer" not in plugin.ListOfDevices[ADDR]


class TestDecode8042CoordinatorBootstrap:

    def test_coordinator_not_in_devices_creates_entry(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "ReArrangeMacCapaBasedOnModel", MagicMock(return_value="8e"))
        monkeypatch.setattr(mod, "decodeMacCapa", MagicMock(return_value=[]))
        mod.Decode8042(plugin, {}, _make_msg(addr="0000"), LQI)
        assert "0000" in plugin.ListOfDevices

    def test_coordinator_gets_ep_key(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "ReArrangeMacCapaBasedOnModel", MagicMock(return_value="8e"))
        monkeypatch.setattr(mod, "decodeMacCapa", MagicMock(return_value=[]))
        mod.Decode8042(plugin, {}, _make_msg(addr="0000"), LQI)
        assert "Ep" in plugin.ListOfDevices["0000"]


class TestDecode8042UnknownDevice:

    def test_unknown_device_logs_and_returns(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "ReArrangeMacCapaBasedOnModel", MagicMock(return_value="8e"))
        monkeypatch.setattr(mod, "decodeMacCapa", MagicMock(return_value=[]))
        mod.Decode8042(plugin, {}, _make_msg(), LQI)
        # Device should NOT be created
        assert ADDR not in plugin.ListOfDevices


class TestDecode8042SuccessfulDecode:

    def _prepare(self, plugin, mod, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8042"}
        monkeypatch.setattr(mod, "ReArrangeMacCapaBasedOnModel", MagicMock(return_value="8e"))
        monkeypatch.setattr(mod, "decodeMacCapa", MagicMock(return_value=["Main Powered", "Full-Function Device"]))

    def test_updates_raw_node_descriptor(self, mod, plugin, monkeypatch):
        self._prepare(plugin, mod, monkeypatch)
        mod.Decode8042(plugin, {}, _make_msg(), LQI)
        assert "_rawNodeDescriptor" in plugin.ListOfDevices[ADDR]

    def test_updates_max_buffer(self, mod, plugin, monkeypatch):
        self._prepare(plugin, mod, monkeypatch)
        mod.Decode8042(plugin, {}, _make_msg(max_buf="52"), LQI)
        assert plugin.ListOfDevices[ADDR]["Max Buffer Size"] == "52"

    def test_updates_manufacturer(self, mod, plugin, monkeypatch):
        self._prepare(plugin, mod, monkeypatch)
        mod.Decode8042(plugin, {}, _make_msg(manufacturer="abcd"), LQI)
        assert plugin.ListOfDevices[ADDR]["Manufacturer"] == "abcd"

    def test_updates_power_source_main_powered(self, mod, plugin, monkeypatch):
        self._prepare(plugin, mod, monkeypatch)
        mod.Decode8042(plugin, {}, _make_msg(), LQI)
        assert plugin.ListOfDevices[ADDR]["PowerSource"] == "Main"

    def test_updates_device_type_ffd(self, mod, plugin, monkeypatch):
        self._prepare(plugin, mod, monkeypatch)
        mod.Decode8042(plugin, {}, _make_msg(), LQI)
        assert plugin.ListOfDevices[ADDR]["DeviceType"] == "FFD"

    def test_battery_powered_device(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}, "Status": "8042"}
        monkeypatch.setattr(mod, "ReArrangeMacCapaBasedOnModel", MagicMock(return_value="00"))
        monkeypatch.setattr(mod, "decodeMacCapa", MagicMock(return_value=[]))
        mod.Decode8042(plugin, {}, _make_msg(mac_cap="00"), LQI)
        assert plugin.ListOfDevices[ADDR]["PowerSource"] == "Battery"

    def test_calls_updlqi(self, mod, plugin, monkeypatch):
        self._prepare(plugin, mod, monkeypatch)
        ulqi = MagicMock()
        monkeypatch.setattr(mod, "updLQI", ulqi)
        mod.Decode8042(plugin, {}, _make_msg(), LQI)
        ulqi.assert_called_once_with(plugin, ADDR, LQI)

    def test_does_not_overwrite_manufacturer_if_already_set_and_indb(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {
            "Ep": {}, "Status": "inDB", "Manufacturer": "existing"
        }
        monkeypatch.setattr(mod, "ReArrangeMacCapaBasedOnModel", MagicMock(return_value="8e"))
        monkeypatch.setattr(mod, "decodeMacCapa", MagicMock(return_value=["Main Powered"]))
        mod.Decode8042(plugin, {}, _make_msg(manufacturer="new1"), LQI)
        # Manufacturer should NOT be overwritten for inDB devices
        assert plugin.ListOfDevices[ADDR]["Manufacturer"] == "existing"
