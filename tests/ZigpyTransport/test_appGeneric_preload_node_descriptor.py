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
        def __init__(self):
            self.lines = []
        def logging(self, category, level, message, *args, **kwargs):
            self.lines.append((level, message))

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

    out = {"__log__": [list(entry) for entry in app.log.lines]}
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


# --- the two layers together ----------------------------------------------
#
# The tests above hand _preload_devices_from_plugin_db() the field dict
# directly. This one starts from a device record as the plugin keeps it and runs
# the whole chain -- node_descriptor_fields() then _build_node_descriptor() --
# so that a device family the plugin corrects by model name is checked against
# zigpy's own scan gate rather than against our reading of it.
END_TO_END_SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import Classes.ZigpyTransport.AppGeneric as AG
    from Modules.tools_mac_capa import decodeMacCapa, node_descriptor_fields

    out = {}
    for name, nwkid, mac_capa, overrides in json.loads(sys.argv[1]):
        device = {"Capability": decodeMacCapa(mac_capa), "MacCapa": mac_capa}
        device.update(overrides)
        node_desc, _source = AG._build_node_descriptor(node_descriptor_fields(nwkid, device))
        out[name] = None if node_desc is None else {
            "logical_type": node_desc.logical_type.name,
            "would_be_scanned": bool(
                node_desc.is_router or node_desc.is_coordinator
            ),
        }
    print(json.dumps(out))
    """
)


def run_end_to_end(cases):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", END_TO_END_SNIPPET, json.dumps(cases)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_the_whole_chain_decides_scannability_from_the_announced_capability():
    out = run_end_to_end([
        # a genuine mains-powered router
        ["router", "1a2b", "8e", {}],
        # Livolo: announces 0x80, and ReArrangeMacCapaBasedOnModel() rewrites it
        # to Router/FFD/8e. NetworkMap.is_a_router() excludes those models from
        # scanning by name; reading Capability reaches the same answer with no
        # model name involved.
        ["livolo", "7a8b", "80", {"LogicalType": "Router", "DeviceType": "FFD", "MacCapa": "8e"}],
        # the same models, rewritten the other way by mainPoweredDevice()
        ["livolo_other_rewrite", "7a8c", "80", {"LogicalType": "End Device", "DeviceType": "RFD"}],
        # Aqara Opple: 0x84, mains-powered bit set but not full-function
        ["opple", "c6ca", "84", {"LogicalType": "Router"}],
        # the coordinator, which Capability cannot tell from a router
        ["coordinator", "0000", "8e", {}],
    ])

    assert out["router"]["would_be_scanned"] is True
    assert out["coordinator"]["logical_type"] == "Coordinator"
    assert out["coordinator"]["would_be_scanned"] is True

    for name in ("livolo", "livolo_other_rewrite", "opple"):
        assert out[name]["logical_type"] == "EndDevice", name
        assert out[name]["would_be_scanned"] is False, name


# --- the captured descriptor, against the real encoder --------------------
#
# _node_descriptor_from_raw() has to undo two transforms at once: the field
# reordering that Zigbee/zdpDecoders.buildframe_node_descriptor_response()
# applies, and the byte-swapping of each 16-bit field. Testing it against a
# hand-written expectation would only prove it agrees with this file.
#
# So these drive the chain the plugin really uses: a real zigpy NodeDescriptor
# is serialised into the ZDP payload a device sends, that payload goes through
# the real frame builder, _rawNodeDescriptor is sliced out of the result exactly
# as Z4D_decoders/z4d_decoder_Node_Desc_Rsp.py slices it, and the descriptor
# that comes back out has to be the one we started with.
ROUND_TRIP_SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.zdo.types as zdo_t
    import Classes.ZigpyTransport.AppGeneric as AG
    from Zigbee.zdpDecoders import buildframe_node_descriptor_response

    class Log:
        def logging(self, *args, **kwargs):
            pass

    plugin = types.SimpleNamespace(log=Log())

    out = {}
    for name, spec in json.loads(sys.argv[1]).items():
        node_desc = zdo_t.NodeDescriptor(
            logical_type=getattr(zdo_t.LogicalType, spec["logical_type"]),
            complex_descriptor_available=spec["complex_descriptor_available"],
            user_descriptor_available=spec["user_descriptor_available"],
            reserved=0,
            aps_flags=spec["aps_flags"],
            frequency_band=zdo_t.FrequencyBand(spec["frequency_band"]),
            mac_capability_flags=zdo_t.MACCapabilityFlags(spec["mac_capability_flags"]),
            manufacturer_code=spec["manufacturer_code"],
            maximum_buffer_size=spec["maximum_buffer_size"],
            maximum_incoming_transfer_size=spec["maximum_incoming_transfer_size"],
            server_mask=spec["server_mask"],
            maximum_outgoing_transfer_size=spec["maximum_outgoing_transfer_size"],
            descriptor_capability_field=zdo_t.DescriptorCapability(
                spec["descriptor_capability_field"]
            ),
        )

        # The ZDP response a device sends: sqn, status, its nwkid, then the
        # descriptor -- whose layout is NodeDescriptor.serialize() itself
        payload = "01" + "00" + "2b1a" + node_desc.serialize().hex()
        frame = buildframe_node_descriptor_response(plugin, "1a2b", "00", "8002", payload, "0000ff03")

        # encapsulate_plugin_frame(): 01 + msgtype + length + crc + payload + lqi + 03
        msg_data = frame[12:-4]
        raw = msg_data[8:]            # Decode8042's _rawNodeDescriptor

        parsed = AG._node_descriptor_from_raw(raw)
        out[name] = {
            "raw": raw,
            "round_trips": parsed is not None and parsed.serialize() == node_desc.serialize(),
            "logical_type": None if parsed is None else parsed.logical_type.name,
            "as_dict": None if parsed is None else {
                k: int(v) for k, v in parsed.as_dict().items()
            },
            "expected": {k: int(v) for k, v in node_desc.as_dict().items()},
        }
    print(json.dumps(out))
    """
)


def descriptor_spec(**overrides):
    spec = {
        "logical_type": "Router",
        "complex_descriptor_available": 0,
        "user_descriptor_available": 0,
        "aps_flags": 0,
        "frequency_band": 0b01000,      # 2.4 GHz
        "mac_capability_flags": 0x8E,
        "manufacturer_code": 0x1277,
        "maximum_buffer_size": 0x7F,
        "maximum_incoming_transfer_size": 0x0080,
        "server_mask": 0x002C,
        "maximum_outgoing_transfer_size": 0x0080,
        "descriptor_capability_field": 0x00,
    }
    spec.update(overrides)
    return spec


def run_round_trip(specs):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", ROUND_TRIP_SNIPPET, json.dumps(specs)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_a_captured_descriptor_round_trips_through_the_plugin_frame():
    out = run_round_trip({
        "router": descriptor_spec(),
        "coordinator": descriptor_spec(logical_type="Coordinator", mac_capability_flags=0x8F),
        "end_device": descriptor_spec(logical_type="EndDevice", mac_capability_flags=0x80),
    })

    for name, case in out.items():
        assert case["round_trips"] is True, "%s: %s != %s" % (name, case["as_dict"], case["expected"])

    # the logical type is the field zigpy's scan gate reads, and the only one
    # Capability cannot supply
    assert out["coordinator"]["logical_type"] == "Coordinator"
    assert out["router"]["logical_type"] == "Router"
    assert out["end_device"]["logical_type"] == "EndDevice"


def test_every_field_survives_the_reordering_and_the_byte_swapping():
    # Distinct, asymmetric values in every 16-bit field, so a field swapped with
    # its neighbour or a byte order left unreversed cannot pass
    out = run_round_trip({"distinct": descriptor_spec(
        manufacturer_code=0x1234,
        maximum_incoming_transfer_size=0x5678,
        server_mask=0x9ABC,
        maximum_outgoing_transfer_size=0x0DEF,
        maximum_buffer_size=0x45,
        descriptor_capability_field=0x03,
        mac_capability_flags=0x8E,
        aps_flags=0b101,
        complex_descriptor_available=1,
        user_descriptor_available=1,
    )})

    assert out["distinct"]["round_trips"] is True, out["distinct"]
    assert out["distinct"]["as_dict"]["manufacturer_code"] == 0x1234
    assert out["distinct"]["as_dict"]["maximum_incoming_transfer_size"] == 0x5678
    assert out["distinct"]["as_dict"]["server_mask"] == 0x9ABC
    assert out["distinct"]["as_dict"]["maximum_outgoing_transfer_size"] == 0x0DEF


PRECEDENCE_SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import Classes.ZigpyTransport.AppGeneric as AG

    out = {}
    for name, fields in json.loads(sys.argv[1]).items():
        node_desc, source = AG._build_node_descriptor(fields)
        out[name] = None if node_desc is None else {
            "logical_type": node_desc.logical_type.name,
            "manufacturer_code": int(node_desc.manufacturer_code),
            "frequency_band": int(node_desc.frequency_band),
            "source": source,
        }
    print(json.dumps(out))
    """
)


def run_precedence(cases):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PRECEDENCE_SNIPPET, json.dumps(cases)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


# A captured descriptor for a coordinator: manufacturer 0x1277, 2.4 GHz,
# logical type 0. Produced by the round-trip above.
RAW_COORDINATOR = "127700800080002c008f7f4000"


def test_the_captured_descriptor_wins_over_the_decoded_fields():
    # The record says end device; the descriptor the device itself sent says
    # coordinator. The descriptor is not rewritten by anything, so it wins.
    out = run_precedence({"case": dict(ROUTER_FIELDS, raw=RAW_COORDINATOR, logical_type="end_device")})

    assert out["case"]["logical_type"] == "Coordinator"


def test_the_captured_descriptor_brings_fields_the_plugin_does_not_keep():
    # frequency_band is only in the captured descriptor; the fallback path can
    # do no better than assume 2.4 GHz
    out = run_precedence({"case": dict(ROUTER_FIELDS, raw=RAW_COORDINATOR)})

    assert out["case"]["frequency_band"] == 0b01000


@pytest.mark.parametrize("raw", [
    "",                             # nothing captured
    "127700800080002c008e7f40",     # truncated
    "127700800080002c008e7f40zz",   # not hex
    "127700800080002c008e7f4007",   # logical type 7, not a Zigbee device type
])
def test_an_unusable_captured_descriptor_falls_through_to_the_fields(raw):
    out = run_precedence({"case": dict(ROUTER_FIELDS, raw=raw)})

    assert out["case"]["logical_type"] == "Router"
    assert out["case"]["manufacturer_code"] == 0x1277


def test_an_unusable_captured_descriptor_with_no_fields_describes_nothing():
    out = run_precedence({"case": {"raw": "nonsense", "logical_type": None}})

    assert out["case"] is None


# --- what the plugin log says ---------------------------------------------
#
# How much of zigpy's device table rests on a descriptor the device itself sent
# is the number that says whether a topology scan can reach the mesh at all, so
# it goes in the plugin's own log rather than only zigpy's.
def log_lines(out, level=None):
    return [
        message for entry_level, message in out["__log__"]
        if level is None or entry_level == level
    ]


def test_the_pre_load_reports_how_much_of_the_table_is_described():
    out = run([
        (IEEE_ROUTER, "1a2b", dict(ROUTER_FIELDS, raw=RAW_COORDINATOR)),
        (IEEE_END_DEVICE, "c6ca", dict(ROUTER_FIELDS, logical_type="end_device")),
        (IEEE_COORDINATOR, "0000", None),
    ])

    summary = [line for line in log_lines(out, "Status") if "Pre-loaded" in line]
    assert len(summary) == 1, out["__log__"]
    assert "3 device(s)" in summary[0]
    assert "2 with a node descriptor" in summary[0]
    assert "1 from the descriptor captured from the device" in summary[0]
    assert "1 from the plugin's recorded device type" in summary[0]
    assert "1 without" in summary[0]


def test_the_undescribed_devices_are_named():
    # Those are the records to go and look at, and the devices that will be
    # missing from a topology report
    out = run([
        (IEEE_ROUTER, "1a2b", ROUTER_FIELDS),
        (IEEE_END_DEVICE, "c6ca", None),
        (IEEE_COORDINATOR, "0000", None),
    ])

    warning = [line for line in log_lines(out, "Status") if "no node descriptor" in line]
    assert len(warning) == 1, out["__log__"]
    assert "2 device(s)" in warning[0]
    assert "0000" in warning[0]
    assert "c6ca" in warning[0]
    assert "skipped by any zigpy" in warning[0]


def test_nothing_is_said_about_undescribed_devices_when_there_are_none():
    out = run([(IEEE_ROUTER, "1a2b", ROUTER_FIELDS)])

    assert [line for line in log_lines(out, "Status") if "no node descriptor" in line] == []


def test_each_device_says_where_its_descriptor_came_from():
    out = run([
        (IEEE_ROUTER, "1a2b", dict(ROUTER_FIELDS, raw=RAW_COORDINATOR)),
        (IEEE_END_DEVICE, "c6ca", dict(ROUTER_FIELDS, logical_type="end_device")),
    ])

    debug = log_lines(out, "Debug")
    assert any(
        "1a2b" in line and "Coordinator" in line and "captured from the device" in line
        for line in debug
    ), debug
    assert any(
        "c6ca" in line and "EndDevice" in line and "recorded device type" in line
        for line in debug
    ), debug


def test_a_device_left_undescribed_says_so_per_device():
    out = run([(IEEE_ROUTER, "1a2b", None)])

    assert any(
        "1a2b" in line and "no node descriptor known" in line
        for line in log_lines(out, "Debug")
    ), out["__log__"]


def test_keeping_zigpys_own_descriptor_is_logged_too():
    out = run(
        [(IEEE_ROUTER, "1a2b", ROUTER_FIELDS)],
        preexisting=[(IEEE_ROUTER, "1a2b", "Router")],
    )

    assert any(
        "1a2b" in line and "zigpy already has" in line
        for line in log_lines(out, "Debug")
    ), out["__log__"]


def test_a_long_list_of_undescribed_devices_is_summarised():
    # A fresh install can have nothing described at all; the startup line must
    # not become unreadable
    devices = [("%016x" % (0x680ae2fffe7ac000 + i), "%04x" % (0x1000 + i), None) for i in range(14)]
    out = run(devices)

    warning = [line for line in log_lines(out, "Status") if "no node descriptor" in line][0]
    assert "14 device(s)" in warning
    assert "and 4 more" in warning
