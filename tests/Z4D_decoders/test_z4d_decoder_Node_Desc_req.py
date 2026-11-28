"""
Tests for Z4D_decoders/z4d_decoder_Node_Desc_req.py

Covers Decode0042:
  - Non-coordinator nwkid → status '80'
  - Coordinator not in ListOfDevices → status '81'
  - Coordinator without Manufacturer key → status '89'
  - Coordinator with full data → status '00' + calls raw_APS_request
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Node_Desc_req"

# Ensure Modules.sendZigateCommand is stubbed before importing
import types as _types
if "Modules.sendZigateCommand" not in sys.modules:
    _m = _types.ModuleType("Modules.sendZigateCommand")
    _m.raw_APS_request = MagicMock(name="raw_APS_request")
    sys.modules["Modules.sendZigateCommand"] = _m


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"

# Layout: sqn(2)+srcNwkId(4)+srcEp(2)+nwkid(4) = 12 chars
def _make_msg(nwkid="0000", src="abcd"):
    return "01" + src + "01" + nwkid


class TestDecode0042:

    def test_non_coordinator_calls_raw_aps(self, mod, plugin, monkeypatch):
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="1234"), LQI)
        raw.assert_called_once()

    def test_coordinator_not_in_devices_calls_raw_aps(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)
        raw.assert_called_once()

    def test_coordinator_without_manufacturer_calls_raw_aps(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = {"Ep": {}}  # no Manufacturer key
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)
        raw.assert_called_once()

    def test_coordinator_with_full_data_calls_raw_aps(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = {
            "Ep": {}, "Manufacturer": "1234",
            "Max Rx": "0050", "Max Tx": "0050",
            "server_mask": "0000", "descriptor_capability": "00",
            "macapa": "8e", "Max Buffer Size": "52", "bitfield": "4001",
        }
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)
        raw.assert_called_once()


def _payload(raw):
    # raw_APS_request(self, nwkid, ep, cluster, profile, payload, ...)
    return raw.call_args.args[5]


class TestDecode0042Payload:
    """The response is sent as raw ZDP: Node_Desc_rsp layout, little-endian 16-bit fields."""

    # Coordinator record as Decode8042 stores it (big-endian hex, ZiGate 0x8042 field names)
    # for an EZSP coordinator: logical type Coordinator, 2.4 GHz, MAC capability 0x8f,
    # manufacturer 0xabcd, buffer 0x52, max in/out transfer 128, server mask 0x2c41,
    # descriptor capability 0x00.
    EZSP_COORDINATOR = {
        "Ep": {}, "Manufacturer": "abcd",
        "bitfield": "4000", "macapa": "8f", "Max Buffer Size": "52",
        "Max Rx": "0080", "Max Tx": "0080",
        "server_mask": "2c41", "descriptor_capability": "00",
    }

    def test_success_payload_is_in_zdp_order(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = dict(self.EZSP_COORDINATOR)
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)

        # The same bytes as the Node_Desc_rsp the EZSP stack sends itself for this coordinator
        # (ZBDongle-E capture: 0040 8f cdab 52 8000 412c 8000 00).
        expected = (
            "01" "00" "0000"   # sqn, status Success, NWKAddrOfInterest
            "0040"             # logical type Coordinator / 2.4 GHz band
            "8f"               # MAC capability
            "cdab"             # manufacturer code 0xabcd, the coordinator's own
            "52"               # max buffer size
            "8000"             # max incoming transfer size 128
            "412c"             # server mask 0x2c41
            "8000"             # max outgoing transfer size 128
            "00"               # descriptor capability
        )
        assert _payload(raw) == expected

    def test_success_payload_has_node_descriptor_length(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = dict(self.EZSP_COORDINATOR)
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)

        # sqn + status + NWK address = 4 bytes, Node Descriptor = 13 bytes
        assert len(bytes.fromhex(_payload(raw))) == 4 + 13

    def test_response_goes_back_to_the_requester_on_zdo(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = dict(self.EZSP_COORDINATOR)
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000", src="e568"), LQI)

        args = raw.call_args.args
        assert args[1:5] == ("e568", "00", "8002", "0000")
        assert raw.call_args.kwargs["zigpyzqn"] == "01"

    def test_error_payload_has_little_endian_nwk_address(self, mod, plugin, monkeypatch):
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="1234"), LQI)

        assert _payload(raw) == "01" "80" "3412"

    def test_manufacturer_code_is_the_coordinators_own(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices["0000"] = dict(self.EZSP_COORDINATOR, Manufacturer="1037")
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)

        # bytes 7-8 of the payload: after sqn, status, NWK address (4 bytes), bitfield (2) and MAC capability (1)
        assert _payload(raw)[14:18] == "3710"

    @pytest.mark.parametrize("stored", ["", {}, "12", "zzzz", "1 37"])
    def test_unusable_manufacturer_code_is_sent_as_0000(self, mod, plugin, monkeypatch, stored):
        plugin.ListOfDevices["0000"] = dict(self.EZSP_COORDINATOR, Manufacturer=stored)
        raw = MagicMock()
        monkeypatch.setattr(mod, "raw_APS_request", raw)
        mod.Decode0042(plugin, {}, _make_msg(nwkid="0000"), LQI)

        assert _payload(raw)[14:18] == "0000"
        assert len(bytes.fromhex(_payload(raw))) == 4 + 13
