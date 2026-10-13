#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.ZigpyTopology.build_zigpy_neighbors().

The neighbours table was an instance attribute initialised once in __init__ and
never reset, and add_to_neighbors_table() appends a pair only when the table
does not already hold it. Every scan after the first therefore threw away the
readings zigpy had just collected: a pair kept the LQI, relationship, device
type and rx-on-when-idle it had the first time it was ever seen, and a device
that had left the network kept its links forever.

Observed on a real Zigpy-Topology-XX.json: two reports 185 seconds apart, 74
neighbour entries each, all 74 LQI values identical, 64 distinct values in play.

zigpy's own side was never the problem -- zigpy/topology.py assigns
`self.neighbors[device.ieee] = await self._scan_neighbors(device)`, a fresh list
per scanned device -- so the readings were there to be used.

Classes/ZigpyTopology.py does `import zigpy.types`, so these are skipped where
zigpy is not installed, as tests/Classes/test_scan_classes_deviceconf.py already
does for the same reason. CI installs it.
"""

import json

import pytest

zigpy_types = pytest.importorskip("zigpy.types")
zigpy_zdo_types = pytest.importorskip("zigpy.zdo.types")

from Classes.ZigpyTopology import build_zigpy_neighbors  # noqa: E402

COORDINATOR_NWKID = "0000"
COORDINATOR_IEEE = "00124b00256c1207"
ROUTER_NWKID = "cbc4"
ROUTER_IEEE = "90fd9ffffe1fb2c1"
SECOND_ROUTER_NWKID = "edd6"
SECOND_ROUTER_IEEE = "680ae2fffe7aca89"


class Log:
    def logging(self, module, level, message, *args, **kwargs):
        pass


class FakeZigpyTopology:
    """Just the attributes build_zigpy_neighbors() touches."""

    def __init__(self):
        self.IEEE2NWK = {
            COORDINATOR_IEEE: COORDINATOR_NWKID,
            ROUTER_IEEE: ROUTER_NWKID,
            SECOND_ROUTER_IEEE: SECOND_ROUTER_NWKID,
        }
        self.ListOfDevices = {
            COORDINATOR_NWKID: {"IEEE": COORDINATOR_IEEE},
            ROUTER_NWKID: {"IEEE": ROUTER_IEEE},
            SECOND_ROUTER_NWKID: {"IEEE": SECOND_ROUTER_IEEE},
        }
        self.log = Log()
        # As ZigpyTopology.__init__ leaves it
        self.neighbors_table = {}


def as_ieee(ieee):
    """The EUI64 object zigpy keys its topology dict with."""
    return zigpy_types.EUI64.convert(":".join(ieee[i:i + 2] for i in range(0, 16, 2)))


def neighbour(
    ieee,
    nwkid,
    lqi,
    relationship=zigpy_zdo_types.Relationship.Child,
    device_type=zigpy_zdo_types.DeviceType.Router,
    rx_on_when_idle=zigpy_zdo_types.RxOnWhenIdle.On,
):
    """A real zigpy Neighbor, so the field names and types are zigpy's own."""
    return zigpy_zdo_types.Neighbor(
        extended_pan_id=zigpy_types.ExtendedPanId.convert("aa:bb:cc:dd:ee:ff:00:11"),
        ieee=as_ieee(ieee),
        nwk=zigpy_types.NWK(int(nwkid, 16)),
        device_type=device_type,
        rx_on_when_idle=rx_on_when_idle,
        relationship=relationship,
        reserved1=0,
        permit_joining=zigpy_zdo_types.PermitJoins.Unknown,
        reserved2=0,
        depth=1,
        lqi=lqi,
    )


def scan(**reporters):
    """{reporter ieee: [Neighbor, ...]}, the shape app.get_topology() returns."""
    return {as_ieee(ieee): neighbours for ieee, neighbours in reporters.items()}


def snapshot(table):
    """A detached copy, which also proves the table is JSON-serialisable -- it
    gets written straight into the topology report file."""
    return json.loads(json.dumps(table))


def reported(table, reporter_nwkid, neighbour_nwkid):
    return next(
        (
            entry for entry in table.get(reporter_nwkid, {}).get("relationship", [])
            if entry["nwkid"] == neighbour_nwkid
        ),
        None,
    )


def test_a_scan_reports_what_the_nodes_just_said():
    topology = FakeZigpyTopology()

    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
    }))

    assert reported(table, COORDINATOR_NWKID, ROUTER_NWKID)["lqi_from_device"] == 204


def test_a_second_scan_reports_the_new_link_quality():
    # The regression: the pair was already in the table, so the new reading was
    # discarded and the report still said 204.
    topology = FakeZigpyTopology()

    build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
    }))
    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=97)],
    }))

    assert reported(table, COORDINATOR_NWKID, ROUTER_NWKID)["lqi_from_device"] == 97


def test_a_second_scan_reports_a_changed_relationship():
    topology = FakeZigpyTopology()

    build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(
            ROUTER_IEEE, ROUTER_NWKID, lqi=204,
            relationship=zigpy_zdo_types.Relationship.Child,
        )],
    }))
    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(
            ROUTER_IEEE, ROUTER_NWKID, lqi=204,
            relationship=zigpy_zdo_types.Relationship.PreviousChild,
        )],
    }))

    assert reported(table, COORDINATOR_NWKID, ROUTER_NWKID)["relationship"] == "previous_child"


def test_a_link_the_scan_no_longer_reports_is_gone():
    # A device that left the network used to keep its links in every later
    # report, for the life of the plugin process.
    topology = FakeZigpyTopology()

    build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [
            neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204),
            neighbour(SECOND_ROUTER_IEEE, SECOND_ROUTER_NWKID, lqi=142),
        ],
    }))
    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
    }))

    assert reported(table, COORDINATOR_NWKID, ROUTER_NWKID) is not None
    assert reported(table, COORDINATOR_NWKID, SECOND_ROUTER_NWKID) is None


def test_a_reporter_the_scan_no_longer_reaches_is_gone():
    topology = FakeZigpyTopology()

    build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
        ROUTER_IEEE: [neighbour(COORDINATOR_IEEE, COORDINATOR_NWKID, lqi=164)],
    }))
    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
    }))

    assert sorted(table) == [COORDINATOR_NWKID]


def test_two_consecutive_scans_of_an_unchanged_mesh_still_agree():
    # The fix must not make a stable mesh look unstable
    topology = FakeZigpyTopology()
    one_scan = scan(**{
        COORDINATOR_IEEE: [
            neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204),
            neighbour(SECOND_ROUTER_IEEE, SECOND_ROUTER_NWKID, lqi=142),
        ],
    })

    first = snapshot(build_zigpy_neighbors(topology, one_scan))
    second = snapshot(build_zigpy_neighbors(topology, one_scan))

    assert first == second


def test_the_table_does_not_grow_scan_after_scan():
    topology = FakeZigpyTopology()
    one_scan = scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
    })

    for _ in range(5):
        table = build_zigpy_neighbors(topology, one_scan)

    assert len(table[COORDINATOR_NWKID]["relationship"]) == 1


def test_the_same_pair_twice_in_one_scan_is_reported_once():
    topology = FakeZigpyTopology()

    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [
            neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204),
            neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=97),
        ],
    }))

    assert len(table[COORDINATOR_NWKID]["relationship"]) == 1


def test_a_node_the_plugin_does_not_know_is_left_out():
    # Unchanged behaviour, pinned so the reset is not read as a licence to send
    # neighbours the plugin cannot resolve
    topology = FakeZigpyTopology()
    del topology.IEEE2NWK[SECOND_ROUTER_IEEE]
    del topology.ListOfDevices[SECOND_ROUTER_NWKID]

    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [
            neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204),
            neighbour(SECOND_ROUTER_IEEE, SECOND_ROUTER_NWKID, lqi=142),
        ],
    }))

    assert reported(table, COORDINATOR_NWKID, SECOND_ROUTER_NWKID) is None


def test_the_flags_are_carried_through():
    topology = FakeZigpyTopology()

    table = build_zigpy_neighbors(topology, scan(**{
        COORDINATOR_IEEE: [neighbour(
            ROUTER_IEEE, ROUTER_NWKID, lqi=204,
            rx_on_when_idle=zigpy_zdo_types.RxOnWhenIdle.Off,
            device_type=zigpy_zdo_types.DeviceType.EndDevice,
        )],
    }))

    entry = reported(table, COORDINATOR_NWKID, ROUTER_NWKID)
    assert entry["rx_on_when_idle"] == "off"
    assert entry["device_type"] == "end_device"
    assert entry["permit_joining"] == "unknown"


def test_each_scan_builds_its_own_table_object():
    # Replaced, not cleared in place. copy_zigpy_infos_to_plugin() stores the
    # returned table in ListOfDevices["0000"]["ZigpyNeighbors"], which lives
    # between scans: emptying the table in place would wipe that stored copy as
    # a side effect of the next scan.
    topology = FakeZigpyTopology()
    one_scan = scan(**{
        COORDINATOR_IEEE: [neighbour(ROUTER_IEEE, ROUTER_NWKID, lqi=204)],
    })

    first = build_zigpy_neighbors(topology, one_scan)
    second = build_zigpy_neighbors(topology, one_scan)

    assert first is not second
    assert first == second
