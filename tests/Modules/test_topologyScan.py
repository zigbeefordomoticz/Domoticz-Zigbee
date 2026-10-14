#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.topologyScan, the backend-neutral model behind
/topology-scan (issue #2106).

What is worth pinning down here is not that the three backends are read, but
that they are read into *one* contract. The old /topologie payload lost
relationship, routes, node identity and dead nodes on the way out; each test
below holds one of those open.

Modules/topologyScan.py imports nothing from Modules.* on purpose, so these
tests can import it directly: the session stubs tests/conftest.py installs for
Modules.tools & co. never come into play.
"""

import json

import pytest

from Modules.topologyScan import (SCAN_NOT_SUPPORTED, SCAN_OK, SCAN_TIMEOUT,
                                  SOURCE_LEGACY, SOURCE_TOPOLOGY_V2,
                                  SOURCE_ZIGPY, as_int,
                                  associated_devices_scan_status, canonical,
                                  delete_topology_scan, get_topology_scan,
                                  list_topology_scans, read_json_file,
                                  value_or_none)

HARDWARE_ID = 1

COORDINATOR_IEEE = "00124b0022334455"
ROUTER_IEEE = "680ae2fffe7aca89"
SECOND_ROUTER_IEEE = "60a423fffe529d60"
END_DEVICE_IEEE = "000d6ffffea1e6da"


class FakePluginConf:
    def __init__(self, reports_directory, zigpy_report, topology_v2):
        self.pluginConf = {
            "pluginReports": str(reports_directory),
            "ZigpyTopologyReport": zigpy_report,
            "TopologyV2": topology_v2,
            "numTopologyReports": 4,
        }


class FakePlugin:
    """Just enough of the WebServer instance for the model to read."""

    def __init__(self, reports_directory, list_of_devices=None, zigpy_report=False, topology_v2=False):
        self.pluginconf = FakePluginConf(reports_directory, zigpy_report, topology_v2)
        self.hardwareID = HARDWARE_ID
        self.zigbee_communication = "zigpy" if zigpy_report else "native"
        self.ListOfDevices = list_of_devices if list_of_devices is not None else {}
        self.logs = []

    def logging(self, level, message):
        self.logs.append((level, message))


def list_of_devices():
    return {
        "0000": {"IEEE": COORDINATOR_IEEE, "LogicalType": "Coordinator", "MacCapa": "8e", "Health": "Live"},
        "1a2b": {
            "IEEE": ROUTER_IEEE, "ZDeviceName": "Repeater", "LogicalType": "Router", "MacCapa": "8e",
            "Model": "TRADFRI Signal Repeater", "Health": "Live", "LQI": 196, "Battery": "",
        },
        "7a8b": {
            "IEEE": SECOND_ROUTER_IEEE, "ZDeviceName": "Led LKex", "LogicalType": "Router", "MacCapa": "8e",
            "Model": "LXEK-1", "Health": "Not seen last 24hours", "LQI": 42,
        },
        "c6ca": {
            "IEEE": END_DEVICE_IEEE, "ZDeviceName": "OnOff Ikea", "LogicalType": "End Device", "MacCapa": "80",
            "Model": "TRADFRI onoff switch", "Health": "Live", "Battery": 100,
        },
    }


def write_zigpy_report(reports_directory, entries):
    path = reports_directory / ("Zigpy-Topology-%02d.json" % HARDWARE_ID)
    path.write_text(json.dumps(entries, indent=4))
    return path


def write_legacy_report(reports_directory, reports):
    """The legacy file is one JSON object per line, written after a bare newline."""
    path = reports_directory / ("NetworkTopology-v3-%02d.json" % HARDWARE_ID)
    path.write_text("".join("\n" + json.dumps(report) for report in reports) + "\n")
    return path


def zigpy_report():
    """One scan as Classes/ZigpyTopology.py stores it, keyed by a float time.time()."""
    return [{
        "1711537200.123456": {
            "Neighbors": {
                "0000": {
                    "ieee": COORDINATOR_IEEE,
                    "relationship": [
                        {
                            "nwkid": "1a2b", "ieee": ROUTER_IEEE, "relationship": "child",
                            "device_type": "router", "rx_on_when_idle": "on",
                            "lqi_from_device": 196, "depth": 1, "permit_joining": "off",
                        },
                        {
                            "nwkid": "7a8b", "ieee": SECOND_ROUTER_IEEE, "relationship": "none_of_above",
                            "device_type": "router", "rx_on_when_idle": "on",
                            "lqi_from_device": 42, "depth": 1, "permit_joining": "off",
                        },
                    ],
                },
                "1a2b": {
                    "ieee": ROUTER_IEEE,
                    "relationship": [
                        {
                            "nwkid": "0000", "ieee": COORDINATOR_IEEE, "relationship": "parent",
                            "device_type": "coordinator", "rx_on_when_idle": "on",
                            "lqi_from_device": 164, "depth": 0, "permit_joining": "off",
                        },
                    ],
                },
            },
            "Routes": {
                "0000": [{
                    "dst_nwk": "7a8b", "route_status": "active", "memory_constrained": 0,
                    "many_to_one": 0, "route_record_required": 0, "next_hop": "1a2b",
                }],
            },
        }
    }]


def legacy_report(timestamp=1711537200):
    """One scan as Classes/NetworkMap.py stores it: raw hex, legacy vocabulary."""
    return {
        str(timestamp): {
            "0000": {
                "Status": "Completed", "TableMaxSize": 2, "TableCurSize": 2,
                "Neighbours": {
                    "1a2b": {
                        "_ieee": ROUTER_IEEE, "_depth": "01", "_lnkqty": "c4",
                        "_devicetype": "Router", "_permitjnt": "Off",
                        "_relationshp": "Child", "_rxonwhenidl": "Rx-On",
                    },
                    "c6ca": {
                        "_ieee": END_DEVICE_IEEE, "_depth": "01", "_lnkqty": "5e",
                        "_devicetype": "End Device", "_permitjnt": "Off",
                        "_relationshp": "Former Child", "_rxonwhenidl": "Rx-Off",
                    },
                },
            },
            "7a8b": {"Status": "TimedOut", "TableMaxSize": 0, "TableCurSize": 0, "Neighbours": {}},
        }
    }


def topology_v2_devices(timestamp=1711537200):
    """ListOfDevices as Modules/zb_tables_management.py leaves it: numbers already
    converted, one table entry per scanned node."""
    devices = list_of_devices()
    devices["0000"]["Neighbours"] = [{
        "Devices": [{"1a2b": {
            "_relationshp": "Child", "_devicetype": "Router", "_depth": 1, "_lnkqty": 196,
            "_rxonwhenidl": "Rx-On", "_IEEE": ROUTER_IEEE, "_permitjnt": "Off",
        }}],
        "SQN": 0, "Status": "", "TimeStamp": timestamp, "Time": timestamp,
    }]
    devices["0000"]["RoutingTable"] = [{
        "Devices": [{"7a8b": {
            "Status": "Active (0)", "MemoryConstrained": 0, "ManyToOne": 1,
            "RouteRecordRequired": 0, "NextHopNwkId": "1a2b",
        }}],
        "SQN": 0, "Status": "", "TimeStamp": timestamp, "Time": timestamp,
    }]
    devices["0000"]["AssociatedDevices"] = [{
        "Devices": ["1a2b", "c6ca"], "SQN": 0, "Status": "", "TimeStamp": timestamp, "Time": timestamp,
    }]
    # Asked, never answered: start_new_table_scan() left the entry empty
    devices["7a8b"]["Neighbours"] = [{
        "Devices": [], "SQN": 0, "Status": "", "TimeStamp": timestamp, "Time": timestamp,
    }]
    return devices


@pytest.fixture
def zigpy_plugin(tmp_path):
    write_zigpy_report(tmp_path, zigpy_report())
    return FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)


@pytest.fixture
def legacy_plugin(tmp_path):
    write_legacy_report(tmp_path, [legacy_report()])
    return FakePlugin(tmp_path, list_of_devices())


@pytest.fixture
def v2_plugin(tmp_path):
    return FakePlugin(tmp_path, topology_v2_devices(), topology_v2=True)


def neighbour(scan, reporter, neighbor):
    return next(
        (entry for entry in scan["neighbours"] if entry["reporter"] == reporter and entry["neighbor"] == neighbor),
        None,
    )


def node(scan, nwkid):
    return next((entry for entry in scan["nodes"] if entry["nwkid"] == nwkid), None)


# --- the listing ----------------------------------------------------------
def test_listing_labels_each_scan_with_its_source_and_tables(zigpy_plugin):
    summaries = list_topology_scans(zigpy_plugin)

    assert len(summaries) == 1
    assert summaries[0]["source"] == SOURCE_ZIGPY
    assert summaries[0]["tables"] == ["neighbours", "routes"]
    assert summaries[0]["neighbours"] == 3
    assert summaries[0]["routes"] == 1


def test_legacy_listing_does_not_claim_a_routes_table(legacy_plugin):
    summaries = list_topology_scans(legacy_plugin)

    # The legacy backend has no routing table at all, which is why `tables` is
    # not the same for every source: missing is fine, silently empty is not.
    assert summaries[0]["source"] == SOURCE_LEGACY
    assert summaries[0]["tables"] == ["neighbours"]
    assert summaries[0]["routes"] == 0


def test_zigpy_float_report_key_is_reported_as_integer_seconds(zigpy_plugin):
    summaries = list_topology_scans(zigpy_plugin)

    assert summaries[0]["timestamp"] == 1711537200
    assert isinstance(summaries[0]["timestamp"], int)


def test_a_scan_written_by_two_backends_is_listed_once_by_the_active_one(tmp_path):
    # NetworkMap.finish_scan() always fills the TopologyV2 tables; only the
    # legacy file write is gated on the setting. The same scan therefore sits in
    # two backends, and must not be offered twice.
    write_legacy_report(tmp_path, [legacy_report()])
    plugin = FakePlugin(tmp_path, topology_v2_devices(), topology_v2=True)

    summaries = list_topology_scans(plugin)

    assert [summary["source"] for summary in summaries] == [SOURCE_TOPOLOGY_V2]


def test_reports_of_an_inactive_backend_stay_readable(tmp_path):
    # Switching a setup from legacy to zigpy must not hide the reports already
    # on disk: `source` is a per-scan property, not a per-plugin one.
    write_legacy_report(tmp_path, [legacy_report(timestamp=1711530000)])
    write_zigpy_report(tmp_path, zigpy_report())
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    summaries = list_topology_scans(plugin)

    assert [(summary["timestamp"], summary["source"]) for summary in summaries] == [
        (1711530000, SOURCE_LEGACY),
        (1711537200, SOURCE_ZIGPY),
    ]


def test_an_unknown_timestamp_has_no_scan(zigpy_plugin):
    assert get_topology_scan(zigpy_plugin, 1234567890) is None


# --- identity -------------------------------------------------------------
def test_nodes_are_keyed_on_nwkid_and_carry_ieee(zigpy_plugin):
    scan = get_topology_scan(zigpy_plugin, 1711537200)

    assert node(scan, "1a2b")["ieee"] == ROUTER_IEEE
    assert node(scan, "1a2b")["name"] == "Repeater"


def test_two_devices_sharing_a_name_stay_two_nodes(tmp_path):
    devices = list_of_devices()
    devices["7a8b"]["ZDeviceName"] = "Repeater"
    write_zigpy_report(tmp_path, zigpy_report())
    plugin = FakePlugin(tmp_path, devices, zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)

    assert node(scan, "1a2b")["nwkid"] != node(scan, "7a8b")["nwkid"]
    assert node(scan, "1a2b")["ieee"] != node(scan, "7a8b")["ieee"]


def test_a_node_with_no_name_reports_a_null_name_not_its_nwkid(tmp_path):
    devices = list_of_devices()
    del devices["1a2b"]["ZDeviceName"]
    write_zigpy_report(tmp_path, zigpy_report())
    plugin = FakePlugin(tmp_path, devices, zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)

    assert node(scan, "1a2b")["name"] is None
    assert node(scan, "1a2b")["nwkid"] == "1a2b"


def test_a_node_the_plugin_does_not_know_keeps_what_its_neighbour_reported(tmp_path):
    devices = list_of_devices()
    del devices["7a8b"]
    write_zigpy_report(tmp_path, zigpy_report())
    plugin = FakePlugin(tmp_path, devices, zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)

    unknown = node(scan, "7a8b")
    assert unknown is not None
    assert unknown["ieee"] == SECOND_ROUTER_IEEE
    assert unknown["logical_type"] == "router"
    assert unknown["model"] is None


def test_a_reading_the_device_never_sent_is_null_rather_than_zero(zigpy_plugin):
    scan = get_topology_scan(zigpy_plugin, 1711537200)

    assert node(scan, "1a2b")["battery"] is None
    assert node(scan, "1a2b")["rssi"] is None
    assert node(scan, "1a2b")["lqi"] == 196


# --- relationship, both directions, no filtering --------------------------
def test_both_directions_of_a_link_are_reported_with_their_own_lqi(zigpy_plugin):
    scan = get_topology_scan(zigpy_plugin, 1711537200)

    # A hears B at 196, B hears A at 164: the asymmetry is how a node that is
    # heard well but does not hear back gets spotted, so neither side is dropped.
    assert neighbour(scan, "0000", "1a2b")["lqi"] == 196
    assert neighbour(scan, "1a2b", "0000")["lqi"] == 164
    assert neighbour(scan, "0000", "1a2b")["relationship"] == "child"
    assert neighbour(scan, "1a2b", "0000")["relationship"] == "parent"


def test_relationships_the_old_payload_dropped_are_carried_through(zigpy_plugin, legacy_plugin):
    zigpy_scan = get_topology_scan(zigpy_plugin, 1711537200)
    legacy_scan = get_topology_scan(legacy_plugin, 1711537200)

    assert neighbour(zigpy_scan, "0000", "7a8b")["relationship"] == "none_of_above"
    assert neighbour(legacy_scan, "0000", "c6ca")["relationship"] == "previous_child"


def test_legacy_vocabulary_is_translated_to_the_zigpy_one(legacy_plugin):
    scan = get_topology_scan(legacy_plugin, 1711537200)

    entry = neighbour(scan, "0000", "1a2b")
    assert entry["relationship"] == "child"
    assert entry["device_type"] == "router"
    assert entry["rx_on_when_idle"] == "on"
    assert entry["permit_joining"] == "off"


def test_legacy_hex_link_quality_is_converted(legacy_plugin):
    scan = get_topology_scan(legacy_plugin, 1711537200)

    assert neighbour(scan, "0000", "1a2b")["lqi"] == 196
    assert neighbour(scan, "0000", "1a2b")["depth"] == 1


def test_topology_v2_numbers_are_taken_as_they_are_stored(v2_plugin):
    scan = get_topology_scan(v2_plugin, 1711537200)

    # TopologyV2 stores LQI and depth already converted, the legacy file does not
    assert neighbour(scan, "0000", "1a2b")["lqi"] == 196
    assert neighbour(scan, "0000", "1a2b")["depth"] == 1


# --- routes ---------------------------------------------------------------
def test_zigpy_routes_carry_the_next_hop(zigpy_plugin):
    scan = get_topology_scan(zigpy_plugin, 1711537200)

    assert scan["routes"] == [{
        "reporter": "0000", "destination": "7a8b", "next_hop": "1a2b", "status": "active",
        "many_to_one": False, "memory_constrained": False, "route_record_required": False,
    }]


def test_topology_v2_routes_carry_the_next_hop_and_the_many_to_one_flag(v2_plugin):
    scan = get_topology_scan(v2_plugin, 1711537200)

    assert scan["routes"] == [{
        "reporter": "0000", "destination": "7a8b", "next_hop": "1a2b", "status": "active",
        "many_to_one": True, "memory_constrained": False, "route_record_required": False,
    }]


def test_topology_v2_exposes_associated_devices(v2_plugin):
    scan = get_topology_scan(v2_plugin, 1711537200)

    assert node(scan, "0000")["associated_devices"] == ["1a2b", "c6ca"]


def test_a_backend_without_an_associated_devices_table_reports_null(zigpy_plugin):
    scan = get_topology_scan(zigpy_plugin, 1711537200)

    # null, not []: zigpy cannot collect them at all, which is not the same
    # thing as a node having no child
    assert node(scan, "0000")["associated_devices"] is None


# --- dead nodes -----------------------------------------------------------
def test_a_node_that_timed_out_is_not_a_leaf_with_no_neighbours(legacy_plugin):
    scan = get_topology_scan(legacy_plugin, 1711537200)

    assert node(scan, "7a8b")["scan_status"] == "timeout"
    assert node(scan, "0000")["scan_status"] == "ok"


def test_topology_v2_reads_an_empty_table_entry_as_a_timeout(v2_plugin):
    scan = get_topology_scan(v2_plugin, 1711537200)

    assert node(scan, "7a8b")["scan_status"] == "timeout"
    assert node(scan, "0000")["scan_status"] == "ok"


def test_an_end_device_is_not_counted_as_an_unanswered_scan(legacy_plugin):
    scan = get_topology_scan(legacy_plugin, 1711537200)

    assert node(scan, "c6ca")["scan_status"] == "not_supported"
    assert scan["scan"] == {"requested": 3, "answered": 1, "timeout": 1, "not_scanned": 1}


def test_a_router_absent_from_the_report_is_still_listed(tmp_path):
    devices = list_of_devices()
    devices["dead"] = {"IEEE": "00158d0003021601", "ZDeviceName": "Dead Router", "LogicalType": "Router"}
    write_zigpy_report(tmp_path, zigpy_report())
    plugin = FakePlugin(tmp_path, devices, zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)

    assert node(scan, "dead")["scan_status"] == "not_scanned"


# --- deletion -------------------------------------------------------------
def test_deleting_a_scan_removes_it_from_every_backend_holding_it(tmp_path):
    write_legacy_report(tmp_path, [legacy_report()])
    plugin = FakePlugin(tmp_path, topology_v2_devices(), topology_v2=True)

    removed = delete_topology_scan(plugin, 1711537200)

    assert sorted(removed) == [SOURCE_LEGACY, SOURCE_TOPOLOGY_V2]
    assert list_topology_scans(plugin) == []


def test_deleting_one_zigpy_scan_leaves_the_others(tmp_path):
    reports = zigpy_report()
    reports.append({"1711540000.0": {"Neighbors": {}, "Routes": {}}})
    write_zigpy_report(tmp_path, reports)
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert delete_topology_scan(plugin, 1711537200) == [SOURCE_ZIGPY]
    assert [summary["timestamp"] for summary in list_topology_scans(plugin)] == [1711540000]


def test_deleting_an_unknown_scan_changes_nothing(zigpy_plugin):
    assert delete_topology_scan(zigpy_plugin, 1234567890) == []
    assert len(list_topology_scans(zigpy_plugin)) == 1


# --- the running scan -----------------------------------------------------
def test_the_scan_being_collected_is_not_offered_yet(tmp_path):
    devices = topology_v2_devices(timestamp=1711540000)
    devices["0000"]["TopologyStartTime"] = 1711540000
    plugin = FakePlugin(tmp_path, devices, topology_v2=True)

    assert list_topology_scans(plugin) == []


# --- reading is never a write --------------------------------------------
def test_reading_a_scan_does_not_create_table_entries(tmp_path):
    devices = topology_v2_devices()
    plugin = FakePlugin(tmp_path, devices, topology_v2=True)

    get_topology_scan(plugin, 1711537200)

    assert "Neighbours" not in devices["1a2b"]
    assert "RoutingTable" not in devices["c6ca"]


def test_a_missing_report_file_is_not_an_error(tmp_path):
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert list_topology_scans(plugin) == []
    assert plugin.logs == []


def test_a_garbled_report_file_is_reported_and_not_raised(tmp_path):
    (tmp_path / ("Zigpy-Topology-%02d.json" % HARDWARE_ID)).write_text("{not json")
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert list_topology_scans(plugin) == []
    assert [level for level, _ in plugin.logs] == ["Error"]


def test_a_garbled_legacy_line_does_not_discard_the_other_reports(tmp_path):
    path = tmp_path / ("NetworkTopology-v3-%02d.json" % HARDWARE_ID)
    path.write_text("\n{truncated\n" + json.dumps(legacy_report()) + "\n")
    plugin = FakePlugin(tmp_path, list_of_devices())

    assert [summary["timestamp"] for summary in list_topology_scans(plugin)] == [1711537200]


# --- value helpers --------------------------------------------------------
@pytest.mark.parametrize("value,expected", [
    ("Former Child", "previous_child"),
    ("None", "none_of_above"),
    ("sibling", "sibling"),
    ("", "unknown"),
    (None, "unknown"),
    (5, "unknown"),
])
def test_canonical_relationship(value, expected):
    from Modules.topologyScan import RELATIONSHIP_ALIASES
    assert canonical(value, RELATIONSHIP_ALIASES) == expected


@pytest.mark.parametrize("value,expected", [
    ("c4", 196),      # legacy keeps the raw hex read off the wire
    (196, 196),       # TopologyV2 and zigpy keep it converted
    ("", None),
    (None, None),
    ("zz", None),
    (True, None),
])
def test_as_int(value, expected):
    assert as_int(value) == expected


@pytest.mark.parametrize("value", ["", {}, [], None])
def test_value_or_none_treats_every_empty_marker_alike(value):
    assert value_or_none(value) is None


def test_read_json_file_returns_none_when_there_is_no_file(tmp_path):
    plugin = FakePlugin(tmp_path)

    assert read_json_file(plugin, tmp_path / "missing.json") is None


# --- the real ListOfDevices ----------------------------------------------
def test_the_model_reads_a_thread_safe_device_dict(tmp_path):
    """plugin.py holds ListOfDevices in a ThreadSafeDeviceDict, which wraps every
    device entry in one too.

    That wrapper is a MutableMapping and *not* a dict instance, so a model
    guarding its reads with isinstance(..., dict) silently sees an empty device
    database in production while every test built on plain dicts passes.
    """
    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict

    write_zigpy_report(tmp_path, zigpy_report())
    devices = ThreadSafeDeviceDict(list_of_devices())
    assert not isinstance(devices["1a2b"], dict)

    plugin = FakePlugin(tmp_path, devices, zigpy_report=True)
    scan = get_topology_scan(plugin, 1711537200)

    assert node(scan, "1a2b")["name"] == "Repeater"
    assert node(scan, "1a2b")["ieee"] == ROUTER_IEEE
    assert node(scan, "1a2b")["model"] == "TRADFRI Signal Repeater"
    assert node(scan, "c6ca")["scan_status"] == "not_supported"


def test_an_empty_wrapped_value_is_reported_as_null(tmp_path):
    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict

    write_zigpy_report(tmp_path, zigpy_report())
    devices = ThreadSafeDeviceDict(list_of_devices())
    # A {} stored in the device database comes back wrapped, and a wrapped {}
    # does not compare equal to {}
    devices["1a2b"]["ZDeviceName"] = {}
    devices["1a2b"]["Battery"] = {}

    plugin = FakePlugin(tmp_path, devices, zigpy_report=True)
    scan = get_topology_scan(plugin, 1711537200)

    assert node(scan, "1a2b")["name"] is None
    assert node(scan, "1a2b")["battery"] is None
    json.dumps(scan)


def test_topology_v2_tables_are_read_and_deleted_through_the_wrapper(tmp_path):
    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict

    devices = ThreadSafeDeviceDict(topology_v2_devices())
    plugin = FakePlugin(tmp_path, devices, topology_v2=True)

    scan = get_topology_scan(plugin, 1711537200)
    assert neighbour(scan, "0000", "1a2b")["lqi"] == 196
    assert node(scan, "0000")["associated_devices"] == ["1a2b", "c6ca"]

    assert delete_topology_scan(plugin, 1711537200) == [SOURCE_TOPOLOGY_V2]
    assert list_topology_scans(plugin) == []


def test_the_running_scan_is_recognised_through_the_wrapper(tmp_path):
    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict

    devices = ThreadSafeDeviceDict(topology_v2_devices(timestamp=1711540000))
    devices["0000"]["TopologyStartTime"] = 1711540000
    plugin = FakePlugin(tmp_path, devices, topology_v2=True)

    assert list_topology_scans(plugin) == []


# --- shapes seen in a real report -----------------------------------------
#
# Modelled on a Zigpy-Topology-XX.json off a running ZNP setup: that radio
# reports permit_joining as unknown for every neighbour and rx_on_when_idle as
# unknown for a third of them, one neighbour came back with an LQI of 0, one
# node answered the routing request but is missing from the Neighbors section,
# and the file predates depth collection. IEEEs here are synthetic.
def real_world_zigpy_report():
    return [{
        "1791824584.1646256": {
            "Neighbors": {
                "0000": {
                    "ieee": COORDINATOR_IEEE,
                    "relationship": [
                        {
                            "nwkid": "1a2b", "ieee": ROUTER_IEEE, "relationship": "child",
                            "device_type": "router", "rx_on_when_idle": "on",
                            "lqi_from_device": 204, "permit_joining": "unknown",
                        },
                        {
                            "nwkid": "7a8b", "ieee": SECOND_ROUTER_IEEE, "relationship": "sibling",
                            "device_type": "router", "rx_on_when_idle": "unknown",
                            "lqi_from_device": 0, "permit_joining": "unknown",
                        },
                    ],
                },
            },
            "Routes": {
                "0000": [{
                    "dst_nwk": "0ee7", "route_status": "active", "memory_constrained": 0,
                    "many_to_one": 0, "route_record_required": 0, "next_hop": "1a2b",
                }],
                # Answered the routing request with an empty table, and never
                # turned up in Neighbors at all
                "6477": [],
            },
        }
    }]


@pytest.fixture
def real_world_plugin(tmp_path):
    write_zigpy_report(tmp_path, real_world_zigpy_report())
    return FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)


def test_a_radio_that_reports_nothing_useful_is_reported_as_unknown(real_world_plugin):
    scan = get_topology_scan(real_world_plugin, 1791824584)

    # ZNP answers permit_joining with 0x02; "unknown" is the honest value for it,
    # and is not the same statement as "off"
    assert neighbour(scan, "0000", "1a2b")["permit_joining"] == "unknown"
    assert neighbour(scan, "0000", "7a8b")["rx_on_when_idle"] == "unknown"


def test_a_link_quality_of_zero_is_a_reading_and_not_a_missing_value(real_world_plugin):
    scan = get_topology_scan(real_world_plugin, 1791824584)

    assert neighbour(scan, "0000", "7a8b")["lqi"] == 0


def test_a_report_written_before_depth_was_collected_reports_a_null_depth(real_world_plugin):
    scan = get_topology_scan(real_world_plugin, 1791824584)

    assert neighbour(scan, "0000", "1a2b")["depth"] is None


def test_a_node_that_answered_only_the_routing_request_still_counts_as_answered(real_world_plugin):
    scan = get_topology_scan(real_world_plugin, 1791824584)

    # It demonstrably responded, so "not_scanned" would be wrong even though it
    # contributed no neighbour
    assert node(scan, "6477")["scan_status"] == "ok"


def test_a_node_known_only_as_a_route_destination_is_still_a_node(real_world_plugin):
    scan = get_topology_scan(real_world_plugin, 1791824584)

    destination = node(scan, "0ee7")
    assert destination is not None
    assert destination["ieee"] is None
    assert destination["logical_type"] == "unknown"


def test_the_same_scan_stored_twice_is_listed_as_two_reports(tmp_path):
    # ZigpyTopology.save_topology_report() dumps the same accumulating
    # neighbors_table on every scan, so two consecutive reports can hold
    # byte-identical data under two timestamps. Both are still two reports, and
    # the listing is what makes that visible.
    reports = real_world_zigpy_report()
    body = reports[0]["1791824584.1646256"]
    reports.append({"1791824769.114375": body})
    write_zigpy_report(tmp_path, reports)
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    summaries = list_topology_scans(plugin)

    assert [summary["timestamp"] for summary in summaries] == [1791824584, 1791824769]
    assert summaries[0]["neighbours"] == summaries[1]["neighbours"] == 2


# --- depth sentinels ------------------------------------------------------
#
# A real ZNP report came back with depth 0xFF on 19 of 48 neighbour rows and
# 0x0F on 22 more, against 6 child rows and 42 sibling ones: the radio reports a
# depth for parent/child rows and a sentinel for siblings, whose depth it does
# not track. 255 is outside the Zigbee range, so it is not a reading.
@pytest.mark.parametrize("reported,expected", [
    (0, 0),
    (1, 1),
    (15, 15),      # nwkMaxDepth: legal, so passed through
    (16, None),    # out of range
    (255, None),   # the common "not tracked" sentinel
    (None, None),
])
def test_an_out_of_range_depth_is_reported_as_unknown(tmp_path, reported, expected):
    report = zigpy_report()
    report[0]["1711537200.123456"]["Neighbors"]["0000"]["relationship"][0]["depth"] = reported
    write_zigpy_report(tmp_path, report)
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)

    assert neighbour(scan, "0000", "1a2b")["depth"] == expected


def test_a_legacy_hex_depth_sentinel_is_reported_as_unknown(tmp_path):
    report = legacy_report()
    report["1711537200"]["0000"]["Neighbours"]["1a2b"]["_depth"] = "ff"
    write_legacy_report(tmp_path, [report])
    plugin = FakePlugin(tmp_path, list_of_devices())

    scan = get_topology_scan(plugin, 1711537200)

    assert neighbour(scan, "0000", "1a2b")["depth"] is None


def test_a_sentinel_depth_does_not_disturb_the_other_fields(tmp_path):
    report = zigpy_report()
    report[0]["1711537200.123456"]["Neighbors"]["0000"]["relationship"][0]["depth"] = 255
    write_zigpy_report(tmp_path, report)
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)

    entry = neighbour(scan, "0000", "1a2b")
    assert entry["depth"] is None
    assert entry["lqi"] == 196
    assert entry["relationship"] == "child"


# --- the Associated Devices table on a zigpy scan -------------------------
#
# zigpy collects neighbours and routes; the Associated Devices table is
# collected by the plugin afterwards, and only when it is switched on. So the
# zigpy source is the one backend whose `tables` is a property of the scan in
# hand rather than of the backend.
def zigpy_report_with_associated_devices(associated_devices):
    report = zigpy_report()
    report[0]["1711537200.123456"]["AssociatedDevices"] = associated_devices
    return report


@pytest.fixture
def zigpy_plugin_with_associated_devices(tmp_path):
    write_zigpy_report(tmp_path, zigpy_report_with_associated_devices({
        "0000": ["c6ca", "1a2b"],
        "1a2b": [],
    }))
    return FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)


def test_a_zigpy_scan_without_the_section_does_not_claim_the_table(zigpy_plugin):
    """Every report written before the collection existed, and every scan run
    with it off. Claiming the table would say those routers have no children."""
    scan = get_topology_scan(zigpy_plugin, 1711537200)

    assert scan["tables"] == ["neighbours", "routes"]
    assert node(scan, "0000")["associated_devices"] is None


def test_a_zigpy_scan_with_the_section_claims_the_table(zigpy_plugin_with_associated_devices):
    scan = get_topology_scan(zigpy_plugin_with_associated_devices, 1711537200)

    assert scan["tables"] == ["neighbours", "routes", "associated_devices"]
    assert node(scan, "0000")["associated_devices"] == ["1a2b", "c6ca"]


def test_a_node_that_reported_no_child_is_distinguished_from_one_never_asked(
    zigpy_plugin_with_associated_devices,
):
    scan = get_topology_scan(zigpy_plugin_with_associated_devices, 1711537200)

    # Asked, answered, parents nobody.
    assert node(scan, "1a2b")["associated_devices"] == []
    # Never asked -- an end device is not asked at all. It reads as empty too,
    # which is the known limit of a flat table: the per-node answer is not
    # recorded, only the children. scan_status covers the neighbour request.
    assert node(scan, "c6ca")["associated_devices"] == []


def test_an_empty_associated_devices_section_still_claims_the_table(tmp_path):
    """A collection that ran and found no child anywhere: the table was asked
    for, so it is listed, and that is the whole point of listing it."""
    write_zigpy_report(tmp_path, zigpy_report_with_associated_devices({}))
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)
    assert scan["tables"] == ["neighbours", "routes", "associated_devices"]
    assert node(scan, "0000")["associated_devices"] == []


def test_associated_devices_are_deduplicated_and_sorted(tmp_path):
    write_zigpy_report(tmp_path, zigpy_report_with_associated_devices({
        "0000": ["c6ca", "1a2b", "c6ca"],
    }))
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert node(get_topology_scan(plugin, 1711537200), "0000")["associated_devices"] == ["1a2b", "c6ca"]


def test_a_malformed_associated_devices_entry_is_ignored(tmp_path):
    """The report file is read back off disk and is not trusted to be well shaped."""
    write_zigpy_report(tmp_path, zigpy_report_with_associated_devices({
        "0000": ["1a2b", None, 42, {"nwkid": "c6ca"}],
    }))
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert node(get_topology_scan(plugin, 1711537200), "0000")["associated_devices"] == ["1a2b"]


def test_the_listing_reports_the_associated_devices_table(zigpy_plugin_with_associated_devices):
    summaries = list_topology_scans(zigpy_plugin_with_associated_devices)

    assert summaries[0]["tables"] == ["neighbours", "routes", "associated_devices"]


# --- a standalone Associated Devices collection ---------------------------
#
# GET /topology-scan-associated-devices runs the collection on its own, so the
# report entry carries that one section. Neither Neighbors nor Routes was asked
# for, and an absent section is how the payload says a table was not collected.
def associated_devices_only_report(associated_devices, outcome=None):
    entry = {"AssociatedDevices": associated_devices}
    if outcome is not None:
        entry["AssociatedDevicesScan"] = outcome
    return [{"1711537200.123456": entry}]


@pytest.fixture
def standalone_plugin(tmp_path):
    write_zigpy_report(tmp_path, associated_devices_only_report(
        {"0000": ["c6ca"], "1a2b": []},
        {"0000": "ok", "1a2b": "ok", "7a8b": "timeout"},
    ))
    return FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)


def test_a_standalone_collection_claims_only_its_own_table(standalone_plugin):
    scan = get_topology_scan(standalone_plugin, 1711537200)

    assert scan["tables"] == ["associated_devices"]
    assert scan["neighbours"] == []
    assert scan["routes"] == []
    assert node(scan, "0000")["associated_devices"] == ["c6ca"]


def test_a_standalone_collection_reports_its_own_coverage(standalone_plugin):
    """Nothing asked for a neighbour table here, so the coverage reported has to
    be the collection's. Reading it off the absent neighbour table instead would
    make every router not_scanned and the scan look like a total failure."""
    scan = get_topology_scan(standalone_plugin, 1711537200)

    assert node(scan, "0000")["scan_status"] == "ok"
    assert node(scan, "1a2b")["scan_status"] == "ok"
    assert node(scan, "7a8b")["scan_status"] == "timeout"
    assert scan["scan"]["answered"] == 2
    assert scan["scan"]["timeout"] == 1


def test_a_standalone_collection_without_its_outcome_section(tmp_path):
    """Defensive: the section is written by the same code that writes the table,
    but the file is read back off disk and is not trusted to be well shaped."""
    write_zigpy_report(tmp_path, associated_devices_only_report({"0000": ["c6ca"]}))
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)
    assert scan["tables"] == ["associated_devices"]
    # No claim either way about who answered: back to the per-node default.
    assert node(scan, "0000")["scan_status"] == "not_scanned"


def test_a_malformed_outcome_section_is_ignored(tmp_path):
    write_zigpy_report(tmp_path, associated_devices_only_report({"0000": ["c6ca"]}, outcome="broken"))
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert get_topology_scan(plugin, 1711537200)["tables"] == ["associated_devices"]


def test_an_unknown_outcome_value_is_not_read_as_an_answer(tmp_path):
    """Only "ok" is an answer; anything else is a node that did not answer."""
    write_zigpy_report(tmp_path, associated_devices_only_report(
        {"0000": []}, {"0000": "something-else"}
    ))
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    assert node(get_topology_scan(plugin, 1711537200), "0000")["scan_status"] == "timeout"


def test_the_outcome_section_does_not_override_a_neighbour_scan(tmp_path):
    """On a full scan the Neighbors table keeps the last word on scan_status:
    the two sections answer different questions, and mixing them would make the
    field mean neither."""
    report = zigpy_report()
    report[0]["1711537200.123456"]["AssociatedDevices"] = {"0000": ["c6ca"]}
    report[0]["1711537200.123456"]["AssociatedDevicesScan"] = {"0000": "timeout"}
    write_zigpy_report(tmp_path, report)
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    scan = get_topology_scan(plugin, 1711537200)
    assert scan["tables"] == ["neighbours", "routes", "associated_devices"]
    assert node(scan, "0000")["scan_status"] == "ok", "the node answered its neighbour table"


def test_the_listing_shows_a_standalone_collection_beside_a_full_scan(tmp_path):
    reports = zigpy_report()
    reports.append(associated_devices_only_report({"0000": ["c6ca"]}, {"0000": "ok"})[0])
    reports[-1][str(1711540000.5)] = reports[-1].pop("1711537200.123456")
    write_zigpy_report(tmp_path, reports)
    plugin = FakePlugin(tmp_path, list_of_devices(), zigpy_report=True)

    summaries = list_topology_scans(plugin)
    assert [summary["tables"] for summary in summaries] == [
        ["neighbours", "routes"],
        ["associated_devices"],
    ]


# ---------------------------------------------------------------------------
# associated_devices_scan_status - not_supported survives the way out
# ---------------------------------------------------------------------------
def test_associated_devices_outcome_keeps_not_supported():
    """A node that answered without a list is a permanent gap, not a timeout."""
    status = associated_devices_scan_status({
        "AssociatedDevicesScan": {"1111": "ok", "2222": "timeout", "3333": "not_supported"},
    })
    assert status == {
        "1111": SCAN_OK,
        "2222": SCAN_TIMEOUT,
        "3333": SCAN_NOT_SUPPORTED,
    }


def test_associated_devices_outcome_falls_back_to_timeout():
    """An older or unknown spelling reads as "not in the table, reason unknown"."""
    status = associated_devices_scan_status({
        "AssociatedDevicesScan": {"1111": "Received", "2222": ""},
    })
    assert status == {"1111": SCAN_TIMEOUT, "2222": SCAN_TIMEOUT}
