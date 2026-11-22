#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ReArrangeMacCapaBasedOnModel() and main-powered end devices.

A no-neutral switch (Sonoff ZBMINI-L*, Livolo, TS0011) announces MAC capability
0x80: reduced-function device, power-source bit clear. The MainPoweredDevice flag
must correct the power source only. Rewriting it to 0x8e made NetworkMap,
NetworkEnergy, how_many_devices() and the WebUI take the end device for a router.
"""

from unittest.mock import MagicMock

from Modules.tools_mac_capa import (ReArrangeMacCapaBasedOnModel,
                                    decodeMacCapa, mainPoweredDevice)

NWKID = "1603"


def _plugin(device, model="ZBMINIL2", flagged=True):
    device = dict(device, Model=model)
    p = MagicMock()
    p.ListOfDevices = {NWKID: device}
    p.DeviceConf = {model: {"MainPoweredDevice": True}} if flagged else {}
    return p


def _announced(mac_capa, **overrides):
    device = {"MacCapa": mac_capa, "Capability": decodeMacCapa(mac_capa), "PowerSource": "Battery",
              "LogicalType": "End Device", "DeviceType": "RFD"}
    device.update(overrides)
    return device


def test_no_neutral_end_device_only_gets_the_mains_bit():
    p = _plugin(_announced("80"))

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "80") == "84"
    device = p.ListOfDevices[NWKID]
    assert device["MacCapa"] == "84"
    assert device["PowerSource"] == "Main"
    assert device["LogicalType"] == "End Device"
    assert device["DeviceType"] == "RFD"
    assert mainPoweredDevice(p, NWKID) is True


def test_an_earlier_router_rewrite_is_repaired_from_the_announced_capability():
    # what an install holds after a heartbeat with the previous code
    p = _plugin(_announced("80", MacCapa="8e", LogicalType="Router", DeviceType="FFD", PowerSource="Main"))

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "8e") == "84"
    assert p.ListOfDevices[NWKID]["LogicalType"] == "End Device"
    assert p.ListOfDevices[NWKID]["DeviceType"] == "RFD"


def test_receiver_on_idle_is_kept():
    p = _plugin(_announced("88"))

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "88") == "8c"


def test_hard_coded_no_neutral_model_is_an_end_device_too():
    p = _plugin(_announced("80"), model="TS0011", flagged=False)

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "80") == "84"
    assert p.ListOfDevices[NWKID]["LogicalType"] == "End Device"


def test_announced_full_function_device_stays_a_router():
    p = _plugin(_announced("8e"))

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "8e") == "8e"
    assert p.ListOfDevices[NWKID]["LogicalType"] == "Router"
    assert p.ListOfDevices[NWKID]["DeviceType"] == "FFD"


def test_without_capability_the_node_descriptor_mac_capability_is_used():
    # paired before Capability was recorded, already rewritten to 8e
    p = _plugin({"MacCapa": "8e", "macapa": "80", "LogicalType": "Router", "DeviceType": "FFD"})

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "8e") == "84"
    assert p.ListOfDevices[NWKID]["LogicalType"] == "End Device"


def test_without_announced_capability_the_previous_rewrite_is_kept():
    p = _plugin({"MacCapa": "80", "PowerSource": "Battery"})

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "80") == "8e"
    assert p.ListOfDevices[NWKID]["LogicalType"] == "Router"
    assert p.ListOfDevices[NWKID]["PowerSource"] == "Main"


def test_device_without_the_flag_is_untouched():
    p = _plugin(_announced("80"), flagged=False)

    assert ReArrangeMacCapaBasedOnModel(p, NWKID, "80") == "80"
    assert p.ListOfDevices[NWKID]["MacCapa"] == "80"
    assert p.ListOfDevices[NWKID]["LogicalType"] == "End Device"
