#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for AppGeneric._build_node_descriptor() and the node descriptor
_preload_devices_from_plugin_db() now attaches.

zigpy's add_device() is a bare constructor, so a pre-loaded device had
node_desc None, and Topology._scan() skips any device whose node_desc is None
before sending a single request. On an existing install that meant a topology
scan reached only the coordinator plus whatever had rejoined since startup —
2 routers out of ~30 on the mesh this was found on (issue #2110).

Importing AppGeneric pulls in Classes.ZigpyTransport.Transport and
Classes.ZigateTransport.sqnMgmt, which tests/conftest.py stubs for the rest of
the session, so each scenario runs in a subprocess as
test_appGeneric_initialize.py does. The real zigpy package is required — the
whole point is that the descriptor satisfies zigpy's own checks, which a stub
could not tell us.
"""

import importlib.util
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("zigpy") is None, reason="requires the real zigpy package"
)

REPO_ROOT = Path(__file__).resolve().parents[2]

ROUTER_FIELDS = {
    "logical_type": "router",
    "mac_capability": 0x8E,
    "manufacturer_code": 0x1277,
    "maximum_buffer_size": 0x7F,
    "maximum_incoming_transfer_size": 0x0080,
    "maximum_outgoing_transfer_size": 0x0080,
    "server_mask": 0x002C,
    "descriptor_capability_field": 0x00,
}

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.types as t
    import zigpy.zdo.types as zdo_t
    import zigpy.topology

    import Classes.ZigpyTransport.AppGeneric as AG

    scenario = json.loads(sys.argv[1])

    class Log:
        def logging(self, category, level, message, *args, **kwargs):
            pass

    class FakeApp:
        def __init__(self, preexisting):
            self.devices = {}
            self.log = Log()
            self.callBackGetAllDevices = lambda: [
                (int(ieee, 16), int(nwk, 16), fields)
                for ieee, nwk, fields in scenario["devices"]
            ]
            for ieee, nwk, logical_type in preexisting:
                dev = self._new_device(t.EUI64(t.uint64_t(int(ieee, 16)).serialize()), int(nwk, 16))
                if logical_type is not None:
                    dev.node_desc = zdo_t.NodeDescriptor(
                        logical_type=getattr(zdo_t.LogicalType, logical_type),
                        complex_descriptor_available=0, user_descriptor_available=0,
                        reserved=0, aps_flags=0,
                        frequency_band=zdo_t.FrequencyBand.Freq2400MHz,
                        mac_capability_flags=zdo_t.MACCapabilityFlags(0x8E),
                        manufacturer_code=0x1234, maximum_buffer_size=0x7F,
                        maximum_incoming_transfer_size=0x80, server_mask=0,
                        maximum_outgoing_transfer_size=0x80,
                        descriptor_capability_field=zdo_t.DescriptorCapability(0),
                    )
                self.devices[dev.ieee] = dev

        def _new_device(self, ieee, nwk):
            dev = types.SimpleNamespace(ieee=ieee, nwk=nwk, node_desc=None)
            return dev

        def add_device(self, ieee, nwk):
            dev = self._new_device(ieee, nwk)
            self.devices[ieee] = dev
            return dev

    app = FakeApp(scenario["preexisting"])
    AG._preload_devices_from_plugin_db(app)

    out = {}
    for dev in app.devices.values():
        ieee = "%016x" % t.uint64_t.deserialize(dev.ieee.serialize())[0]
        if dev.node_desc is None:
            out[ieee] = None
        else:
            out[ieee] = {
                "logical_type": dev.node_desc.logical_type.name,
                "is_router": bool(dev.node_desc.is_router),
                "is_coordinator": bool(dev.node_desc.is_coordinator),
                "is_end_device": bool(dev.node_desc.is_end_device),
                "mac_capability_flags": int(dev.node_desc.mac_capability_flags),
                "manufacturer_code": int(dev.node_desc.manufacturer_code),
                "maximum_incoming_transfer_size": int(dev.node_desc.maximum_incoming_transfer_size),
                # serialisable means appdb can persist it through as_tuple()
                "serialised": dev.node_desc.serialize().hex(),
                # the check Topology._scan() actually applies
                "would_be_scanned": not (
                    dev.node_desc is None
                    or not (dev.node_desc.is_router or dev.node_desc.is_coordinator)
                ),
            }
    print(json.dumps(out))
    """
)


def run(devices, preexisting=()):
    scenario = {
        "devices": [list(entry) for entry in devices],
        "preexisting": [list(entry) for entry in preexisting],
    }
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(scenario)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


IEEE_ROUTER = "680ae2fffe7aca89"
IEEE_END_DEVICE = "000d6ffffea1e6da"
IEEE_COORDINATOR = "00124b00256c1207"


def test_a_pre_loaded_router_is_now_scannable():
    # The regression this fixes: without a descriptor, Topology._scan() skips
    # the device before sending anything
    out = run([(IEEE_ROUTER, "1a2b", ROUTER_FIELDS)])

    assert out[IEEE_ROUTER]["logical_type"] == "Router"
    assert out[IEEE_ROUTER]["is_router"] is True
    assert out[IEEE_ROUTER]["would_be_scanned"] is True


def test_a_pre_loaded_coordinator_is_scannable():
    fields = dict(ROUTER_FIELDS, logical_type="coordinator")
    out = run([(IEEE_COORDINATOR, "0000", fields)])

    assert out[IEEE_COORDINATOR]["is_coordinator"] is True
    assert out[IEEE_COORDINATOR]["would_be_scanned"] is True


def test_an_end_device_is_described_but_still_not_scanned():
    # It has no neighbour table to ask for. Describing it correctly is what
    # keeps the scan away from it, rather than leaving zigpy to guess.
    fields = dict(ROUTER_FIELDS, logical_type="end_device", mac_capability=0x80)
    out = run([(IEEE_END_DEVICE, "c6ca", fields)])

    assert out[IEEE_END_DEVICE]["is_end_device"] is True
    assert out[IEEE_END_DEVICE]["would_be_scanned"] is False


def test_a_device_with_no_known_logical_type_keeps_no_descriptor():
    out = run([(IEEE_ROUTER, "1a2b", None)])

    assert out[IEEE_ROUTER] is None


def test_the_recorded_values_reach_the_descriptor():
    out = run([(IEEE_ROUTER, "1a2b", ROUTER_FIELDS)])

    assert out[IEEE_ROUTER]["mac_capability_flags"] == 0x8E
    assert out[IEEE_ROUTER]["manufacturer_code"] == 0x1277
    assert out[IEEE_ROUTER]["maximum_incoming_transfer_size"] == 0x0080


def test_the_descriptor_is_complete_enough_to_be_persisted():
    # appdb saves a descriptor through NodeDescriptor.as_tuple(), which needs a
    # fully specified struct; a partially built one would break the save
    out = run([(IEEE_ROUTER, "1a2b", ROUTER_FIELDS)])

    assert len(bytes.fromhex(out[IEEE_ROUTER]["serialised"])) == 13


def test_a_descriptor_zigpy_already_had_is_not_overwritten():
    # zigpy interviewed that device itself, which is the better source
    out = run(
        [(IEEE_ROUTER, "1a2b", dict(ROUTER_FIELDS, logical_type="end_device"))],
        preexisting=[(IEEE_ROUTER, "1a2b", "Router")],
    )

    assert out[IEEE_ROUTER]["logical_type"] == "Router"
    assert out[IEEE_ROUTER]["manufacturer_code"] == 0x1234


def test_a_device_restored_without_a_descriptor_gets_one():
    # zigpy's own database can hold a device with no node descriptor, and it is
    # just as unscannable for it
    out = run(
        [(IEEE_ROUTER, "1a2b", ROUTER_FIELDS)],
        preexisting=[(IEEE_ROUTER, "1a2b", None)],
    )

    assert out[IEEE_ROUTER]["logical_type"] == "Router"
    assert out[IEEE_ROUTER]["would_be_scanned"] is True


def test_a_mixed_device_list_is_described_device_by_device():
    out = run([
        (IEEE_ROUTER, "1a2b", ROUTER_FIELDS),
        (IEEE_END_DEVICE, "c6ca", dict(ROUTER_FIELDS, logical_type="end_device")),
        (IEEE_COORDINATOR, "0000", None),
    ])

    assert out[IEEE_ROUTER]["would_be_scanned"] is True
    assert out[IEEE_END_DEVICE]["would_be_scanned"] is False
    assert out[IEEE_COORDINATOR] is None
