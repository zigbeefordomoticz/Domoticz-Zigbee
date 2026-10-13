#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.tools_mac_capa.node_descriptor_fields().

zigpy fills Device.node_desc only for a device it interviewed itself, and the
plugin registers its own devices with add_device(), which leaves it None. A
device with no node_desc is skipped by zigpy's topology scan before any request
is sent, so on an existing install a scan reaches almost nothing (issue #2110).

This function hands over what the plugin already knows. What it must not do is
guess: a device wrongly presented as a router is one zigpy will interrogate on
every scan, for nothing.

Modules/tools_mac_capa.py has no module-level imports, so it is imported
directly here and the stubs tests/conftest.py installs for the session never
come into play.
"""

import pytest

from Modules.tools_mac_capa import node_descriptor_fields


def router_record():
    return {
        "IEEE": "680ae2fffe7aca89",
        "LogicalType": "Router",
        "DeviceType": "FFD",
        "MacCapa": "8e",
        "Manufacturer": "1277",
        "Max Buffer Size": "7f",
        "Max Rx": "0080",
        "Max Tx": "0080",
        "server_mask": "002c",
        "descriptor_capability": "00",
    }


# --- the logical type, which is what the scan gate reads -------------------
@pytest.mark.parametrize("logical_type,expected", [
    ("Coordinator", "coordinator"),
    ("Router", "router"),
    ("End Device", "end_device"),
    ("end_device", "end_device"),
    ("router", "router"),
    ("ROUTER", "router"),
])
def test_the_plugin_logical_type_is_translated(logical_type, expected):
    record = router_record()
    record["LogicalType"] = logical_type

    assert node_descriptor_fields(record)["logical_type"] == expected


@pytest.mark.parametrize("device_type,expected", [
    ("FFD", "router"),
    ("RFD", "end_device"),
])
def test_device_type_is_the_fallback_when_there_is_no_logical_type(device_type, expected):
    # Older device records predate LogicalType being stored
    record = router_record()
    del record["LogicalType"]
    record["DeviceType"] = device_type

    assert node_descriptor_fields(record)["logical_type"] == expected


def test_a_known_logical_type_wins_over_the_device_type():
    # ReArrangeMacCapaBasedOnModel() corrects LogicalType for devices that
    # misreport their own power source, and that correction must be the one
    # that reaches zigpy
    record = router_record()
    record["LogicalType"] = "Router"
    record["DeviceType"] = "RFD"

    assert node_descriptor_fields(record)["logical_type"] == "router"


@pytest.mark.parametrize("record", [
    {},
    None,
    {"IEEE": "680ae2fffe7aca89"},
    {"LogicalType": "", "DeviceType": ""},
    {"LogicalType": "Sleepy", "DeviceType": "???"},
    {"LogicalType": None},
])
def test_nothing_is_invented_when_the_logical_type_is_unknown(record):
    # None means "register the device the way we do today, without a
    # descriptor". A guess here costs a failed interrogation on every scan.
    assert node_descriptor_fields(record) is None


# --- the other fields ------------------------------------------------------
def test_the_recorded_values_are_carried_through():
    assert node_descriptor_fields(router_record()) == {
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
    record = router_record()
    record["Manufacturer"] = "Legrand"

    assert node_descriptor_fields(record)["manufacturer_code"] == 0


@pytest.mark.parametrize("value", ["", None, {}, "zz", "1ffff", -1, True])
def test_an_unusable_field_falls_back_to_zero(value):
    record = router_record()
    record["Max Rx"] = value

    assert node_descriptor_fields(record)["maximum_incoming_transfer_size"] == 0


def test_an_out_of_range_value_falls_back_to_zero():
    record = router_record()
    record["MacCapa"] = "1ff"        # wider than the one byte it has to fit

    assert node_descriptor_fields(record)["mac_capability"] == 0


def test_a_missing_field_is_zero_and_not_an_error():
    record = {"LogicalType": "Router"}

    fields = node_descriptor_fields(record)

    assert fields["logical_type"] == "router"
    assert fields["mac_capability"] == 0
    assert fields["manufacturer_code"] == 0


def test_an_integer_already_stored_as_a_number_is_kept():
    record = router_record()
    record["Max Rx"] = 128

    assert node_descriptor_fields(record)["maximum_incoming_transfer_size"] == 128


def test_a_thread_safe_device_dict_record_reads_the_same():
    # ListOfDevices wraps every device entry in a ThreadSafeDeviceDict, which is
    # a MutableMapping and not a dict instance
    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict

    wrapped = ThreadSafeDeviceDict({"0000": router_record()})["0000"]
    assert not isinstance(wrapped, dict)

    assert node_descriptor_fields(wrapped) == node_descriptor_fields(router_record())
