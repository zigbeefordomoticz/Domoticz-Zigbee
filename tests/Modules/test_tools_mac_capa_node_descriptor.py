#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.tools_mac_capa.node_descriptor_fields().

zigpy fills Device.node_desc only for a device it interviewed itself, and the
plugin registers its own devices with add_device(), which leaves it None. A
device with no node_desc is skipped by zigpy's topology scan before any request
is sent, so on an existing install a scan reaches almost nothing (issue #2110).

This function hands over what the plugin already knows. Two things it must get
right:

- it must not guess. A device wrongly presented as a router is one zigpy will
  interrogate on every scan, and a delivery failure -- unlike a refusal -- does
  not get it blacklisted, so it would be retried forever.
- it must read "Capability", the capability the device announced, rather than
  LogicalType / DeviceType / MacCapa, which are rewritten per model afterwards.
  ReArrangeMacCapaBasedOnModel() marks TI0001 and the TS06xx switches
  Router/FFD while mainPoweredDevice() marks the very same models End
  Device/RFD, so LogicalType holds whichever ran last.

Capability is built here with the real decodeMacCapa(), so the bit positions
come from the decoder rather than from this file's idea of them.

Modules/tools_mac_capa.py has no module-level imports, so it is imported
directly and the stubs tests/conftest.py installs for the session never come
into play.
"""

import pytest

from Modules.tools_mac_capa import decodeMacCapa, node_descriptor_fields

NWKID = "1a2b"

MAC_CAPA_ROUTER = "8e"          # FFD, mains powered, rx on when idle
MAC_CAPA_END_DEVICE = "80"      # RFD, battery — what Livolo announces
MAC_CAPA_OPPLE = "84"           # RFD but claiming mains power — Aqara Opple


def record(mac_capa=MAC_CAPA_ROUTER, **overrides):
    """A device record as the plugin keeps it, Capability included."""
    device = {
        "IEEE": "680ae2fffe7aca89",
        "Capability": decodeMacCapa(mac_capa),
        "MacCapa": mac_capa,
        "Manufacturer": "1277",
        "Max Buffer Size": "7f",
        "Max Rx": "0080",
        "Max Tx": "0080",
        "server_mask": "002c",
        "descriptor_capability": "00",
    }
    device.update(overrides)
    return device


# --- Capability is the source of truth ------------------------------------
def test_an_announced_full_function_device_is_a_router():
    assert node_descriptor_fields(NWKID, record(MAC_CAPA_ROUTER))["logical_type"] == "router"


def test_an_announced_reduced_function_device_is_an_end_device():
    assert node_descriptor_fields(NWKID, record(MAC_CAPA_END_DEVICE))["logical_type"] == "end_device"


def test_the_announced_capability_wins_over_a_rewritten_logical_type():
    # ReArrangeMacCapaBasedOnModel() rewrites a Livolo switch to Router/FFD/8e.
    # It announced 0x80, and NetworkMap.is_a_router() excludes those models from
    # topology scanning by name, so end_device is the right answer.
    livolo = record(MAC_CAPA_END_DEVICE, LogicalType="Router", DeviceType="FFD", MacCapa="8e")

    assert node_descriptor_fields(NWKID, livolo)["logical_type"] == "end_device"


def test_the_announced_capability_wins_over_the_opposite_rewrite_too():
    # mainPoweredDevice() rewrites the same models the other way, to
    # End Device/RFD. Capability gives the same answer either way, which is the
    # point of reading it.
    livolo = record(MAC_CAPA_END_DEVICE, LogicalType="End Device", DeviceType="RFD")

    assert node_descriptor_fields(NWKID, livolo)["logical_type"] == "end_device"


def test_an_aqara_opple_is_an_end_device_despite_claiming_mains_power():
    # 0x84: mains-powered bit set, full-function bit not. The plugin corrects
    # its MacCapa to 0x80 by model name; reading Capability needs no model name.
    opple = record(MAC_CAPA_OPPLE, LogicalType="Router")

    assert node_descriptor_fields(NWKID, opple)["logical_type"] == "end_device"


def test_a_genuine_router_with_no_logical_type_recorded_is_still_a_router():
    # record() carries no LogicalType at all, so this is Capability alone
    assert node_descriptor_fields(NWKID, record(MAC_CAPA_ROUTER))["logical_type"] == "router"


def test_the_coordinator_is_a_coordinator_whatever_the_record_says():
    # Capability cannot tell a coordinator from a router: both are full-function
    assert node_descriptor_fields("0000", record(MAC_CAPA_ROUTER))["logical_type"] == "coordinator"
    assert node_descriptor_fields("0000", {"LogicalType": "Router"})["logical_type"] == "coordinator"


# --- the fallback chain, for records with no announced capability ----------
@pytest.mark.parametrize("logical_type,expected", [
    ("Coordinator", "coordinator"),
    ("Router", "router"),
    ("End Device", "end_device"),
    ("end_device", "end_device"),
    ("ROUTER", "router"),
])
def test_logical_type_is_the_first_fallback(logical_type, expected):
    assert node_descriptor_fields(NWKID, {"LogicalType": logical_type})["logical_type"] == expected


@pytest.mark.parametrize("device_type,expected", [
    ("FFD", "router"),
    ("RFD", "end_device"),
])
def test_device_type_is_the_second_fallback(device_type, expected):
    assert node_descriptor_fields(NWKID, {"DeviceType": device_type})["logical_type"] == expected


@pytest.mark.parametrize("mac_capa,expected", [
    ("8e", "router"),
    ("80", "end_device"),
    ("84", "end_device"),
])
def test_mac_capa_is_the_last_fallback(mac_capa, expected):
    assert node_descriptor_fields(NWKID, {"MacCapa": mac_capa})["logical_type"] == expected


@pytest.mark.parametrize("capability", ["", {}, None, "Full-Function Device"])
def test_an_unusable_capability_falls_through_to_the_rest(capability):
    # A string would match "Full-Function Device" by substring, which is not a
    # capability list and must not be read as one
    device = {"Capability": capability, "LogicalType": "End Device"}

    assert node_descriptor_fields(NWKID, device)["logical_type"] == "end_device"


@pytest.mark.parametrize("device", [
    {},
    None,
    {"IEEE": "680ae2fffe7aca89"},
    {"Capability": []},
    {"LogicalType": "", "DeviceType": "", "MacCapa": ""},
    {"LogicalType": "Sleepy", "DeviceType": "???"},
    {"Capability": ["Main Powered", "Standard security"]},
])
def test_nothing_is_invented_when_the_device_type_is_unknown(device):
    # None means "register the device the way we do today, without a
    # descriptor". A guess here costs a failed interrogation on every scan.
    assert node_descriptor_fields(NWKID, device) is None


# --- the MAC capability byte ----------------------------------------------
# decodeMacCapa() reads bits 0-3, 6 and 7; bits 4 and 5 are reserved in the
# Zigbee MAC capability field and it does not look at them
DEFINED_MAC_CAPABILITY_BITS = 0b11001111


@pytest.mark.parametrize("mac_capa", ["8e", "80", "84", "00", "ff"])
def test_the_mac_capability_byte_round_trips_through_capability(mac_capa):
    # Re-encoding the announced Capability must give back every defined bit of
    # the byte it was decoded from
    fields = node_descriptor_fields(NWKID, record(mac_capa, LogicalType="Router"))

    assert fields["mac_capability"] == int(mac_capa, 16) & DEFINED_MAC_CAPABILITY_BITS


def test_the_reserved_bits_do_not_survive_the_round_trip():
    # decodeMacCapa() never reads them, so they cannot be re-encoded. No real
    # device sets them -- every MacCapa the plugin sees (0x8e, 0x84, 0x80) has
    # them clear -- and they are reserved, so nothing reads them either.
    fields = node_descriptor_fields(NWKID, record("ff", LogicalType="Router"))

    assert fields["mac_capability"] == 0xCF


def test_the_re_encoded_byte_ignores_a_rewritten_maccapa():
    livolo = record(MAC_CAPA_END_DEVICE, MacCapa="8e")

    assert node_descriptor_fields(NWKID, livolo)["mac_capability"] == 0x80


def test_maccapa_is_used_when_there_is_no_announced_capability():
    assert node_descriptor_fields(NWKID, {"MacCapa": "8e"})["mac_capability"] == 0x8E


# --- the other fields ------------------------------------------------------
def test_the_recorded_values_are_carried_through():
    assert node_descriptor_fields(NWKID, record(MAC_CAPA_ROUTER)) == {
        "raw": None,
        "logical_type": "router",
        "mac_capability": 0x8E,
        "manufacturer_code": 0x1277,
        "maximum_buffer_size": 0x7F,
        "maximum_incoming_transfer_size": 0x0080,
        "maximum_outgoing_transfer_size": 0x0080,
        "server_mask": 0x002C,
        "descriptor_capability_field": 0x00,
    }


def test_a_manufacturer_name_is_not_read_as_a_manufacturer_code():
    # Some device modules put a name in "Manufacturer" (Modules/readAttributes.py
    # compares it against "Legrand"), so it cannot be trusted to be a code
    device = record(MAC_CAPA_ROUTER, Manufacturer="Legrand")

    assert node_descriptor_fields(NWKID, device)["manufacturer_code"] == 0


@pytest.mark.parametrize("value", ["", None, {}, "zz", "1ffff", -1, True])
def test_an_unusable_field_falls_back_to_zero(value):
    device = record(MAC_CAPA_ROUTER, **{"Max Rx": value})

    assert node_descriptor_fields(NWKID, device)["maximum_incoming_transfer_size"] == 0


def test_an_out_of_range_value_falls_back_to_zero():
    device = {"MacCapa": "8e", "LogicalType": "Router", "Max Buffer Size": "1ff"}

    assert node_descriptor_fields(NWKID, device)["maximum_buffer_size"] == 0


def test_an_integer_already_stored_as_a_number_is_kept():
    device = record(MAC_CAPA_ROUTER, **{"Max Rx": 128})

    assert node_descriptor_fields(NWKID, device)["maximum_incoming_transfer_size"] == 128


def test_a_thread_safe_device_dict_record_reads_the_same():
    # ListOfDevices wraps every device entry in a ThreadSafeDeviceDict, which is
    # a MutableMapping and not a dict instance. Its list values are left alone,
    # so Capability stays a list.
    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict

    wrapped = ThreadSafeDeviceDict({NWKID: record(MAC_CAPA_ROUTER)})[NWKID]
    assert not isinstance(wrapped, dict)

    assert node_descriptor_fields(NWKID, wrapped) == node_descriptor_fields(NWKID, record(MAC_CAPA_ROUTER))


# --- the captured descriptor is carried through for the transport to parse -
#
# The transport prefers it over everything else here: it is the descriptor
# itself, it is never rewritten, and it is the only source that can tell a
# coordinator from a router. Parsing it needs zigpy, so it is passed along as
# the raw string and the reordering is tested in
# tests/ZigpyTransport/test_appGeneric_preload_node_descriptor.py.
RAW_NODE_DESCRIPTOR = "127700800080002c008e7f4001"


def test_the_captured_descriptor_is_passed_along():
    device = record(MAC_CAPA_ROUTER, _rawNodeDescriptor=RAW_NODE_DESCRIPTOR)

    assert node_descriptor_fields(NWKID, device)["raw"] == RAW_NODE_DESCRIPTOR


def test_a_captured_descriptor_is_enough_on_its_own():
    # No Capability, no LogicalType, no DeviceType, no MacCapa: the descriptor
    # alone is a complete answer, so the device must not be left undescribed
    device = {"_rawNodeDescriptor": RAW_NODE_DESCRIPTOR}

    fields = node_descriptor_fields(NWKID, device)

    assert fields is not None
    assert fields["raw"] == RAW_NODE_DESCRIPTOR
    assert fields["logical_type"] is None


@pytest.mark.parametrize("raw", ["", "   ", None, {}, 0])
def test_an_empty_captured_descriptor_is_not_passed_along(raw):
    device = record(MAC_CAPA_ROUTER, _rawNodeDescriptor=raw)

    fields = node_descriptor_fields(NWKID, device)

    assert fields["raw"] is None
    assert fields["logical_type"] == "router"


def test_a_device_with_neither_a_descriptor_nor_a_type_is_left_alone():
    assert node_descriptor_fields(NWKID, {"_rawNodeDescriptor": ""}) is None
