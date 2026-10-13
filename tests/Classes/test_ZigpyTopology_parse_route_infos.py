#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.ZigpyTopology.parse_route_infos().

parse_route_infos() read `many_to_one` off `route.RouteRecordRequired`, so the
flag reported for a route was whichever value the *route-record* bit happened to
carry. A route from a many-to-one concentrator looked ordinary, and a route
needing a route record looked like a concentrator route. The two bits are
adjacent in the ZDP routing table record, which is why the typo reads as
plausible code.

Every route is built here from a real zigpy wire frame rather than from a mock,
so the bit positions come from zigpy's own Route struct: a mock would have
asserted the typo just as happily.

Classes/ZigpyTopology.py does `import zigpy.types`, so these are skipped where
zigpy is not installed, as tests/Classes/test_scan_classes_deviceconf.py already
does for the same reason. CI installs it.
"""

import pytest

zigpy_zdo_types = pytest.importorskip("zigpy.zdo.types")

from Classes.ZigpyTopology import parse_route_infos  # noqa: E402

DESTINATION = 0x77F0
NEXT_HOP = 0x6FC0

# Bit layout of the flag byte, from zigpy.zdo.types.Route: 3 bits of route
# status, then MemoryConstrained, ManyToOne, RouteRecordRequired, 2 reserved.
STATUS_ACTIVE = 0b000
MEMORY_CONSTRAINED = 1 << 3
MANY_TO_ONE = 1 << 4
ROUTE_RECORD_REQUIRED = 1 << 5


def build_route(flags, status=STATUS_ACTIVE, destination=DESTINATION, next_hop=NEXT_HOP):
    """A zigpy Route deserialised from the bytes a node would really send."""
    frame = (
        destination.to_bytes(2, "little")
        + bytes([status | flags])
        + next_hop.to_bytes(2, "little")
    )
    route, remaining = zigpy_zdo_types.Route.deserialize(frame)
    assert remaining == b""
    return route


def test_a_many_to_one_route_is_reported_as_many_to_one():
    parsed = parse_route_infos(build_route(MANY_TO_ONE))

    assert parsed["many_to_one"] == 1
    assert parsed["route_record_required"] == 0


def test_a_route_needing_a_route_record_is_not_reported_as_many_to_one():
    # The regression: both fields were read off RouteRecordRequired, so this
    # route came back claiming to be a many-to-one concentrator route.
    parsed = parse_route_infos(build_route(ROUTE_RECORD_REQUIRED))

    assert parsed["many_to_one"] == 0
    assert parsed["route_record_required"] == 1


def test_each_flag_is_read_from_its_own_bit():
    for flags, expected in (
        (0, {"memory_constrained": 0, "many_to_one": 0, "route_record_required": 0}),
        (MEMORY_CONSTRAINED, {"memory_constrained": 1, "many_to_one": 0, "route_record_required": 0}),
        (MANY_TO_ONE, {"memory_constrained": 0, "many_to_one": 1, "route_record_required": 0}),
        (ROUTE_RECORD_REQUIRED, {"memory_constrained": 0, "many_to_one": 0, "route_record_required": 1}),
        (
            MEMORY_CONSTRAINED | MANY_TO_ONE | ROUTE_RECORD_REQUIRED,
            {"memory_constrained": 1, "many_to_one": 1, "route_record_required": 1},
        ),
    ):
        parsed = parse_route_infos(build_route(flags))
        assert {key: parsed[key] for key in expected} == expected, "flags=%#04x" % flags


def test_the_addresses_are_reported_as_four_hex_digits():
    parsed = parse_route_infos(build_route(0))

    assert parsed["dst_nwk"] == "77f0"
    assert parsed["next_hop"] == "6fc0"


@pytest.mark.parametrize("status,expected", [
    (0x00, "active"),
    (0x01, "discovery_underway"),
    (0x02, "discovery_failed"),
    (0x03, "inactive"),
    (0x04, "validation_underway"),
])
def test_the_route_status_is_named(status, expected):
    assert parse_route_infos(build_route(0, status=status))["route_status"] == expected
