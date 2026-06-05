#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_mac_capa.py

Coverage:
  - decodeMacCapa         – FFD/RFD, main/battery, coordinator, security bits
  - mainPoweredDevice     – MacCapa "8e"/"84" → True, "80" → False, PowerSource fallback,
                            known battery models → False, known main-powered models → True,
                            unknown device → False
  - full_function_device  – Capability-based, DeviceConf MainPowered, unknown device → True
  - device_listening_on_iddle – Reduced-Function Device in Capability, unknown → True
  - is_ack_tobe_disabled  – FFD and not idle-listening → True; battery device → False;
                            pairing in progress → False; unknown device → False
"""

import pytest
from unittest.mock import MagicMock, patch

from Modules.tools_mac_capa import (
    decodeMacCapa,
    device_listening_on_iddle,
    full_function_device,
    is_ack_tobe_disabled,
    mainPoweredDevice,
)


def _plugin(devices=None, device_conf=None):
    p = MagicMock()
    p.ListOfDevices = devices if devices is not None else {}
    p.DeviceConf = device_conf if device_conf is not None else {}
    return p


# ---------------------------------------------------------------------------
# decodeMacCapa
# ---------------------------------------------------------------------------

class TestDecodeMacCapa:
    def test_0x8e_main_powered_ffd(self):
        caps = decodeMacCapa("8e")
        assert "Main Powered" in caps
        assert "Full-Function Device" in caps
        assert "Receiver during Idle" in caps

    def test_0x80_battery_rfd(self):
        caps = decodeMacCapa("80")
        assert "Reduced-Function Device" in caps
        assert "Main Powered" not in caps

    def test_coordinator_bit(self):
        # bit 0 = 1 → coordinator
        caps = decodeMacCapa("01")
        assert "Able to act Coordinator" in caps

    def test_security_bit(self):
        # bit 6 = 1 → high security (0x40)
        caps = decodeMacCapa("40")
        assert "High security" in caps

    def test_standard_security_default(self):
        caps = decodeMacCapa("00")
        assert "Standard security" in caps

    def test_nwkaddr_allocation_bits(self):
        # bit 7 = 1 → should allocate
        caps_alloc = decodeMacCapa("80")
        assert "NwkAddr should be allocated" in caps_alloc

        caps_no_alloc = decodeMacCapa("00")
        assert "NwkAddr need to be allocated" in caps_no_alloc


# ---------------------------------------------------------------------------
# mainPoweredDevice
# ---------------------------------------------------------------------------

class TestMainPoweredDevice:
    def test_unknown_device_returns_false(self):
        p = _plugin({})
        assert mainPoweredDevice(p, "dead") is False

    def test_maccapa_8e_is_main_powered(self):
        p = _plugin({"1234": {"MacCapa": "8e", "Model": "generic"}})
        assert mainPoweredDevice(p, "1234") is True

    def test_maccapa_84_is_main_powered(self):
        p = _plugin({"1234": {"MacCapa": "84", "Model": "generic"}})
        assert mainPoweredDevice(p, "1234") is True

    def test_maccapa_80_is_battery(self):
        p = _plugin({"1234": {"MacCapa": "80", "Model": "generic"}})
        assert mainPoweredDevice(p, "1234") is False

    def test_powersource_main_fallback(self):
        p = _plugin({"1234": {"MacCapa": "00", "Model": "generic", "PowerSource": "Main"}})
        assert mainPoweredDevice(p, "1234") is True

    def test_known_battery_model_overrides_maccapa(self):
        model = "lumi.remote.b686opcn01"
        p = _plugin({"1234": {"MacCapa": "8e", "Model": model}})
        assert mainPoweredDevice(p, "1234") is False

    def test_known_main_powered_model_overrides_maccapa(self):
        model = "TS0011"
        p = _plugin({"1234": {"MacCapa": "80", "Model": model}})
        assert mainPoweredDevice(p, "1234") is True


# ---------------------------------------------------------------------------
# full_function_device
# ---------------------------------------------------------------------------

class TestFullFunctionDevice:
    def test_unknown_device_returns_true(self):
        p = _plugin({})
        assert full_function_device(p, "dead") is True

    def test_ffd_via_capability(self):
        p = _plugin({"1234": {"Model": "generic", "Capability": ["Full-Function Device"]}})
        assert full_function_device(p, "1234") is True

    def test_rfd_only_in_capability(self):
        p = _plugin({"1234": {"Model": "generic", "Capability": ["Reduced-Function Device"]}})
        assert full_function_device(p, "1234") is False

    def test_main_powered_in_deviceconf_is_ffd(self):
        p = _plugin(
            {"1234": {"Model": "mymodel", "Capability": []}},
            device_conf={"mymodel": {"MainPowered": True}},
        )
        assert full_function_device(p, "1234") is True


# ---------------------------------------------------------------------------
# device_listening_on_iddle
# ---------------------------------------------------------------------------

class TestDeviceListeningOnIdle:
    def test_unknown_device_returns_true(self):
        p = _plugin({})
        assert device_listening_on_iddle(p, "dead") is True

    def test_rfd_listens_on_idle(self):
        p = _plugin({"1234": {"Model": "generic", "Capability": ["Reduced-Function Device"]}})
        assert device_listening_on_iddle(p, "1234") is True

    def test_ffd_does_not_listen_on_idle(self):
        p = _plugin({"1234": {"Model": "generic", "Capability": ["Full-Function Device"]}})
        assert device_listening_on_iddle(p, "1234") is False


# ---------------------------------------------------------------------------
# is_ack_tobe_disabled
# ---------------------------------------------------------------------------

class TestIsAckToBeDisabled:
    def test_unknown_device_returns_false(self):
        p = _plugin({})
        assert is_ack_tobe_disabled(p, "dead") is False

    def test_battery_device_no_ack_disable(self):
        p = _plugin({"1234": {"Model": "generic", "PowerSource": "Battery", "MacCapa": "80",
                               "Capability": ["Reduced-Function Device"]}})
        assert is_ack_tobe_disabled(p, "1234") is False

    def test_pairing_in_progress_no_disable(self):
        p = _plugin({"1234": {"Model": "generic", "PairingInProgress": True,
                               "Capability": ["Reduced-Function Device"]}})
        assert is_ack_tobe_disabled(p, "1234") is False

    def test_ffd_not_listening_on_idle_disables_ack(self):
        p = _plugin(
            {"1234": {"Model": "mymodel", "Capability": ["Full-Function Device"]}},
            device_conf={"mymodel": {"ReceiveOnIdle": False}},
        )
        assert is_ack_tobe_disabled(p, "1234") is True
