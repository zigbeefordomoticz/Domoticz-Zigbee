#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
    Module: topologyScan.py

    Description: Backend-neutral model of one network topology scan, consumed by
        the /topology-scan REST API (see issue #2106).

        The plugin has three topology backends, each storing a scan in its own
        shape:

          - legacy     Classes/NetworkMap.py, report file NetworkTopology-v3-XX.json
          - topologyv2 Modules/zb_tables_management.py, tables kept in ListOfDevices
          - zigpy      Classes/ZigpyTopology.py, report file Zigpy-Topology-XX.json

        This module reads whichever of them hold data and renders each stored
        scan into one envelope, so a caller never has to know which backend is
        active:

          {
            "timestamp": 1711537200,          # integer seconds, as a number
            "source": "zigpy",                # which backend wrote this scan
            "coordinator": "0000",
            "tables": ["neighbours", "routes"],   # what this backend can fill
            "scan": {"requested": 59, "answered": 54, "timeout": 5, "not_scanned": 0},
            "nodes": [...], "neighbours": [...], "routes": [...]
          }

        Three properties the old /topologie payload did not have:

          - identity is nwkid + ieee; `name` is a display field only, and is
            null when the device has no name, instead of being the nwkid again
          - nothing is deduplicated and nothing is filtered out: both
            directions of a link are reported as the two nodes reported them,
            including `none_of_above` and `previous_child` relationships
          - every node carries a `scan_status`, so a node that never answered
            the scan is no longer indistinguishable from a leaf with no
            neighbours

        Vocabulary is the zigpy one, everywhere. The legacy and TopologyV2
        spellings ("Former Child", "End Device", "Rx-On", "Active (0)", ...) are
        translated on the way out, so the UI has one vocabulary to understand:

          relationship     parent | child | sibling | none_of_above |
                           previous_child | unknown
          device_type      coordinator | router | end_device | unknown
          rx_on_when_idle  on | off | unknown
          permit_joining   on | off | unknown
          route status     active | discovery_underway | discovery_failed |
                           inactive | validation_underway | unknown
          scan_status      ok | timeout | not_supported | not_scanned

        `null` is used where a backend genuinely has no value, rather than 0 or
        "", so the caller can show "unknown" instead of inventing a reading.
"""

import json
import os
import os.path
from collections.abc import Mapping
from pathlib import Path

SOURCE_LEGACY = "legacy"
SOURCE_TOPOLOGY_V2 = "topologyv2"
SOURCE_ZIGPY = "zigpy"

LEGACY_REPORT_FILENAME = "NetworkTopology-v3-%02d.json"
ZIGPY_REPORT_FILENAME = "Zigpy-Topology-%02d.json"

TABLE_NEIGHBOURS = "neighbours"
TABLE_ROUTES = "routes"
TABLE_ASSOCIATED_DEVICES = "associated_devices"

# What each backend is able to collect. A table listed here but empty in a given
# scan means the backend asked and got nothing; a table not listed means the
# backend cannot collect it at all. That distinction is the point of `tables`.
TABLES_PER_SOURCE = {
    SOURCE_LEGACY: (TABLE_NEIGHBOURS,),
    SOURCE_TOPOLOGY_V2: (TABLE_NEIGHBOURS, TABLE_ROUTES, TABLE_ASSOCIATED_DEVICES),
    SOURCE_ZIGPY: (TABLE_NEIGHBOURS, TABLE_ROUTES),
}

# The three per-device tables TopologyV2 keeps in ListOfDevices
V2_TABLES = ("Neighbours", "RoutingTable", "AssociatedDevices")

COORDINATOR_NWKID = "0000"
COORDINATOR_DEFAULT_NAME = "Zigbee Coordinator"

# nwkMaxDepth: the Zigbee tree depth cannot exceed 15
MAX_TREE_DEPTH = 15

SCAN_OK = "ok"
SCAN_TIMEOUT = "timeout"
SCAN_NOT_SUPPORTED = "not_supported"
SCAN_NOT_SCANNED = "not_scanned"

UNKNOWN = "unknown"

# Aliases accept the zigpy spelling (which is the one we emit) plus the legacy
# and TopologyV2 spellings, lowercased.
RELATIONSHIP_ALIASES = {
    "parent": "parent",
    "child": "child",
    "sibling": "sibling",
    "none": "none_of_above",
    "none_of_above": "none_of_above",
    "former child": "previous_child",
    "previous_child": "previous_child",
}

DEVICE_TYPE_ALIASES = {
    "coordinator": "coordinator",
    "router": "router",
    "end device": "end_device",
    "end_device": "end_device",
}

ON_OFF_ALIASES = {
    "on": "on",
    "off": "off",
    "rx-on": "on",
    "rx-off": "off",
}

ROUTE_STATUS_ALIASES = {
    "active": "active",
    "active (0)": "active",
    "discovery_underway": "discovery_underway",
    "discovery underway (1)": "discovery_underway",
    "discovery_failed": "discovery_failed",
    "discovery failed (2)": "discovery_failed",
    "inactive": "inactive",
    "inactive (3)": "inactive",
    "validation_underway": "validation_underway",
    "validation underway (4)": "validation_underway",
}

# NetworkMap keeps a per-node scan state, which the legacy report file stores
LEGACY_SCAN_STATUS = {
    "Completed": SCAN_OK,
    "TimedOut": SCAN_TIMEOUT,
    "NotReachable": SCAN_TIMEOUT,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def active_topology_source(self):
    """Which backend the plugin is currently writing scans with.

    The same condition as rest_req_topologie(): PluginConf already forces
    ZigpyTopologyReport off on a native ZiGate, and the radio is checked here
    too so a stale setting cannot name a backend that is not running.
    """
    if self.pluginconf.pluginConf.get("ZigpyTopologyReport") and self.zigbee_communication == "zigpy":
        return SOURCE_ZIGPY
    if self.pluginconf.pluginConf.get("TopologyV2"):
        return SOURCE_TOPOLOGY_V2
    return SOURCE_LEGACY


def source_priority(self):
    """Source lookup order: the active backend first.

    A single scan can end up in two backends at once -- NetworkMap.finish_scan()
    always fills the TopologyV2 tables, and only the legacy file write is gated
    on the TopologyV2 setting. Reporting the same timestamp twice would be
    noise, so the backend the plugin is actually running wins.
    """
    active = active_topology_source(self)
    return [active] + [x for x in (SOURCE_ZIGPY, SOURCE_TOPOLOGY_V2, SOURCE_LEGACY) if x != active]


def topology_scan_in_progress(self):
    """Timestamp of the scan being collected right now, None if none is."""
    coordinator = self.ListOfDevices.get(COORDINATOR_NWKID) or {}
    return coordinator.get("TopologyStartTime") if isinstance(coordinator, Mapping) else None


def list_topology_scans(self):
    """Summary of every stored scan, oldest first.

    Reports from a backend that is no longer the active one are listed too: a
    setup switched from legacy to zigpy keeps its old reports readable, which is
    why `source` is a per-scan property and not a per-plugin one.
    """
    summaries = []
    seen = set()
    for source in source_priority(self):
        for scan in iter_topology_scans(self, source=source):
            if scan["timestamp"] in seen:
                continue
            seen.add(scan["timestamp"])
            summaries.append(summarize_topology_scan(scan))

    return sorted(summaries, key=lambda summary: summary["timestamp"])


def get_topology_scan(self, timestamp):
    """One stored scan as a full envelope, or None when there is no such scan."""
    for source in source_priority(self):
        for scan in iter_topology_scans(self, timestamp=timestamp, source=source):
            return scan
    return None


def iter_topology_scans(self, timestamp=None, source=None):
    """Yield stored scans, optionally restricted to one timestamp or one source."""
    builders = (
        (SOURCE_ZIGPY, iter_zigpy_scans),
        (SOURCE_TOPOLOGY_V2, iter_topology_v2_scans),
        (SOURCE_LEGACY, iter_legacy_scans),
    )
    for scan_source, builder in builders:
        if source is not None and source != scan_source:
            continue
        yield from builder(self, timestamp)


def summarize_topology_scan(scan):
    """The listing entry for one scan: enough to label it without sending it."""
    return {
        "timestamp": scan["timestamp"],
        "source": scan["source"],
        "tables": scan["tables"],
        "nodes": len(scan["nodes"]),
        "neighbours": len(scan["neighbours"]),
        "routes": len(scan["routes"]),
        "scan": scan["scan"],
    }


def delete_topology_scan(self, timestamp):
    """Remove one scan from every backend holding it, return those sources.

    All of them, not just the active one: a legacy scan also left a copy in the
    TopologyV2 tables, and deleting only one of the two would let the report
    come back from the other.
    """
    removed = []
    for source, deleter in (
        (SOURCE_ZIGPY, delete_zigpy_scan),
        (SOURCE_TOPOLOGY_V2, delete_topology_v2_scan),
        (SOURCE_LEGACY, delete_legacy_scan),
    ):
        if deleter(self, timestamp):
            removed.append(source)
    return removed


def delete_all_topology_scans(self):
    """Remove every stored scan. A scan in progress is not stored yet, so it stays."""
    removed = set()
    for summary in list_topology_scans(self):
        removed.update(delete_topology_scan(self, summary["timestamp"]))
    return sorted(removed)


# ---------------------------------------------------------------------------
# zigpy backend
# ---------------------------------------------------------------------------
def iter_zigpy_scans(self, timestamp=None):
    for raw_timestamp, report in read_zigpy_reports(self):
        scan_timestamp = as_timestamp(raw_timestamp)
        if scan_timestamp is None or (timestamp is not None and scan_timestamp != timestamp):
            continue
        yield build_zigpy_scan(self, scan_timestamp, report)


def read_zigpy_reports(self):
    """Yield (raw timestamp, report) for each entry of the zigpy report file.

    The file is a list of single-key dicts, keyed by a repr of time.time(), so
    the raw key is a float string like "1711537200.123456".
    """
    for entry in read_json_file(self, zigpy_report_path(self)) or []:
        if not isinstance(entry, Mapping) or len(entry) != 1:
            continue
        raw_timestamp = next(iter(entry))
        report = entry[raw_timestamp]
        if isinstance(report, Mapping):
            yield raw_timestamp, report


def build_zigpy_scan(self, timestamp, report):
    neighbours_table = report.get("Neighbors") or {}
    routes_table = report.get("Routes") or {}

    hints = new_hints()
    neighbours = []
    scan_status = {}

    for reporter, reporter_infos in neighbours_table.items():
        if not isinstance(reporter_infos, Mapping):
            continue
        relationships = reporter_infos.get("relationship") or []
        scan_status[reporter] = zigpy_reporter_scan_status(
            reporter_infos.get("neighbors_reported"), relationships
        )
        remember_ieee(hints, reporter, reporter_infos.get("ieee"))

        for neighbour in relationships:
            if not isinstance(neighbour, Mapping) or not neighbour.get("nwkid"):
                continue
            record = {
                "reporter": reporter,
                "neighbor": neighbour["nwkid"],
                "relationship": canonical(neighbour.get("relationship"), RELATIONSHIP_ALIASES),
                "device_type": canonical(neighbour.get("device_type"), DEVICE_TYPE_ALIASES),
                "lqi": as_int(neighbour.get("lqi_from_device")),
                "depth": as_depth(neighbour.get("depth")),
                "rx_on_when_idle": canonical(neighbour.get("rx_on_when_idle"), ON_OFF_ALIASES),
                "permit_joining": canonical(neighbour.get("permit_joining"), ON_OFF_ALIASES),
            }
            neighbours.append(record)
            remember_neighbour(hints, record, neighbour.get("ieee"))

    routes = []
    for reporter, route_list in routes_table.items():
        # A node's presence in Routes says nothing about whether it answered.
        # zigpy leaves an empty list behind for a routing request that timed
        # out, exactly as it does for a neighbour request, so an empty Routes
        # entry is not an answer -- a real scan showed six nodes listed there
        # with nothing in them, two of which had just timed out in the log.
        # The Neighbors table carries the answer, for every node zigpy asked.
        #
        # setdefault, so the node is still reported rather than dropped, while
        # the Neighbors table above keeps the last word on whether it answered.
        scan_status.setdefault(reporter, SCAN_NOT_SCANNED)
        for route in route_list or []:
            if not isinstance(route, Mapping):
                continue
            routes.append({
                "reporter": reporter,
                "destination": route.get("dst_nwk"),
                "next_hop": route.get("next_hop"),
                "status": canonical(route.get("route_status"), ROUTE_STATUS_ALIASES),
                "many_to_one": bool(route.get("many_to_one")),
                "memory_constrained": bool(route.get("memory_constrained")),
                "route_record_required": bool(route.get("route_record_required")),
            })

    return build_scan(self, timestamp, SOURCE_ZIGPY, neighbours, routes, {}, scan_status, hints)


def zigpy_reporter_scan_status(neighbors_reported, relationships):
    """Whether a node listed in the zigpy Neighbors table actually answered.

    Being listed at all means zigpy asked it, which already separates these
    nodes from the ones it skipped. What separates an answer from a timeout is
    `neighbors_reported`: the number of rows the node sent back, counted before
    the rows the plugin cannot resolve are dropped. Zero rows is a node that was
    asked and said nothing -- zigpy records that as an empty list, because a
    delivery timeout leaves `topology.neighbors[ieee]` untouched and the
    defaultdict read that follows creates one.

    A report written before this was recorded has no `neighbors_reported`, and
    the plugin then only listed a node that had at least one resolvable
    neighbour, so such a node answered by definition.
    """
    if relationships:
        return SCAN_OK
    if neighbors_reported is None:
        return SCAN_OK
    return SCAN_TIMEOUT if neighbors_reported == 0 else SCAN_OK


def delete_zigpy_scan(self, timestamp):
    report_path = zigpy_report_path(self)
    reports = read_json_file(self, report_path)
    if not reports:
        return False

    kept = [
        entry for entry in reports
        if not (isinstance(entry, Mapping) and len(entry) == 1 and as_timestamp(next(iter(entry))) == timestamp)
    ]
    if len(kept) == len(reports):
        return False

    return write_json_file(self, report_path, kept)


def read_raw_zigpy_topology_report(self):
    """The zigpy report file, untouched, for /zigpy-topology-raw."""
    return read_json_file(self, zigpy_report_path(self)) or []


# ---------------------------------------------------------------------------
# legacy backend (Classes/NetworkMap.py)
# ---------------------------------------------------------------------------
def iter_legacy_scans(self, timestamp=None):
    for raw_timestamp, report in read_legacy_reports(self):
        scan_timestamp = as_timestamp(raw_timestamp)
        if scan_timestamp is None or (timestamp is not None and scan_timestamp != timestamp):
            continue
        yield build_legacy_scan(self, scan_timestamp, report)


def read_legacy_reports(self):
    """Yield (raw timestamp, report) for each line of NetworkTopology-v3-XX.json.

    The file is one JSON object per line, each a single-key dict of
    {timestamp: {nwkid: NetworkMap.Neighbours entry}}.
    """
    report_path = legacy_report_path(self)
    if not os.path.isfile(report_path):
        return

    try:
        with open(report_path, "rt") as handle:
            lines = handle.readlines()
    except (OSError, UnicodeDecodeError) as error:
        self.logging("Error", "topologyScan: cannot read %s - %s" % (report_path, error))
        return

    for line in lines:
        entry = decode_legacy_line(line)
        if entry is None:
            continue
        raw_timestamp = next(iter(entry))
        report = entry[raw_timestamp]
        if isinstance(report, Mapping):
            yield raw_timestamp, report


def decode_legacy_line(line):
    """One report line of the legacy file, or None for a blank/garbled line."""
    line = line.strip()
    if not line.startswith("{"):
        return None
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, Mapping) and len(entry) == 1 else None


def build_legacy_scan(self, timestamp, report):
    hints = new_hints()
    neighbours = []
    scan_status = {}

    for reporter, node_report in report.items():
        if not isinstance(node_report, Mapping):
            continue
        node_neighbours = node_report.get("Neighbours") or {}
        for neighbour_nwkid, neighbour_infos in node_neighbours.items():
            if not isinstance(neighbour_infos, Mapping):
                continue
            record = build_neighbour_record(reporter, neighbour_nwkid, neighbour_infos)
            neighbours.append(record)
            remember_neighbour(hints, record, neighbour_infos.get("_ieee") or neighbour_infos.get("_IEEE"))

        scan_status[reporter] = legacy_scan_status(node_report.get("Status"), node_neighbours)

    return build_scan(self, timestamp, SOURCE_LEGACY, neighbours, [], {}, scan_status, hints)


def legacy_scan_status(status, node_neighbours):
    """Map a NetworkMap per-node Status onto the API scan_status.

    Anything other than the three terminal states is a scan that never ran to
    the end; it counts as answered only if the node did report something.
    """
    if status in LEGACY_SCAN_STATUS:
        return LEGACY_SCAN_STATUS[status]
    return SCAN_OK if node_neighbours else SCAN_NOT_SCANNED


def delete_legacy_scan(self, timestamp):
    report_path = legacy_report_path(self)
    if not os.path.isfile(report_path):
        return False

    try:
        with open(report_path, "rt") as handle:
            lines = handle.readlines()
    except (OSError, UnicodeDecodeError) as error:
        self.logging("Error", "topologyScan: cannot read %s - %s" % (report_path, error))
        return False

    kept = [line for line in lines if legacy_line_timestamp(line) != timestamp]
    if len(kept) == len(lines):
        return False

    try:
        with open(report_path, "wt") as handle:
            handle.writelines(kept)
    except OSError as error:
        self.logging("Error", "topologyScan: cannot write %s - %s" % (report_path, error))
        return False
    return True


def legacy_line_timestamp(line):
    entry = decode_legacy_line(line)
    return None if entry is None else as_timestamp(next(iter(entry)))


# ---------------------------------------------------------------------------
# TopologyV2 backend (Modules/zb_tables_management.py)
# ---------------------------------------------------------------------------
def iter_topology_v2_scans(self, timestamp=None):
    for scan_timestamp in topology_v2_timestamps(self):
        if timestamp is not None and scan_timestamp != timestamp:
            continue
        yield build_topology_v2_scan(self, scan_timestamp)


def topology_v2_timestamps(self):
    """Timestamps stored in the TopologyV2 tables, the running scan excluded."""
    in_progress = topology_scan_in_progress(self)
    timestamps = set()
    for nwkid in known_nwkids(self):
        for tablename in V2_TABLES:
            for entry in v2_table(self, nwkid, tablename):
                entry_timestamp = entry.get("Time")
                if isinstance(entry_timestamp, int) and entry_timestamp != in_progress:
                    timestamps.add(entry_timestamp)
    return sorted(timestamps)


def v2_table(self, nwkid, tablename):
    """The list of stored entries of one TopologyV2 table, read-only."""
    device = self.ListOfDevices.get(nwkid)
    if not isinstance(device, Mapping):
        return []
    table = device.get(tablename)
    if not isinstance(table, list):
        return []
    return [entry for entry in table if isinstance(entry, Mapping)]


def v2_table_entry(self, nwkid, tablename, timestamp):
    """One stored entry of a TopologyV2 table, or None when the node has none.

    Deliberately not get_table_entry(): that one creates missing entries as a
    side effect, which a GET must never do.
    """
    return next((entry for entry in v2_table(self, nwkid, tablename) if entry.get("Time") == timestamp), None)


def build_topology_v2_scan(self, timestamp):
    hints = new_hints()
    neighbours = []
    routes = []
    associated_devices = {}
    scan_status = {}

    for nwkid in sorted(known_nwkids(self)):
        neighbours_entry = v2_table_entry(self, nwkid, "Neighbours", timestamp)
        if neighbours_entry is not None:
            reported = v2_entry_devices(neighbours_entry)
            for record in reported:
                for neighbour_nwkid, neighbour_infos in record.items():
                    if not isinstance(neighbour_infos, Mapping):
                        continue
                    neighbour = build_neighbour_record(nwkid, neighbour_nwkid, neighbour_infos)
                    neighbours.append(neighbour)
                    remember_neighbour(hints, neighbour, neighbour_infos.get("_IEEE") or neighbour_infos.get("_ieee"))
            # start_new_table_scan() creates the entry when the node is asked, and
            # finish_scan() fills it only for a node that answered, so an entry
            # with no device in it is a node that timed out.
            scan_status[nwkid] = SCAN_OK if reported else SCAN_TIMEOUT

        routes_entry = v2_table_entry(self, nwkid, "RoutingTable", timestamp)
        if routes_entry is not None:
            # setdefault, not assignment: an empty Neighbours entry is an
            # explicit timeout, and that is the stronger signal of the two
            scan_status.setdefault(nwkid, SCAN_OK)
            for record in v2_entry_devices(routes_entry):
                for destination, route_infos in record.items():
                    if not isinstance(route_infos, Mapping):
                        continue
                    routes.append({
                        "reporter": nwkid,
                        "destination": destination,
                        "next_hop": route_infos.get("NextHopNwkId"),
                        "status": canonical(route_infos.get("Status"), ROUTE_STATUS_ALIASES),
                        "many_to_one": bool(route_infos.get("ManyToOne")),
                        "memory_constrained": bool(route_infos.get("MemoryConstrained")),
                        "route_record_required": bool(route_infos.get("RouteRecordRequired")),
                    })

        associated_entry = v2_table_entry(self, nwkid, "AssociatedDevices", timestamp)
        if associated_entry is not None:
            associated_devices[nwkid] = sorted(
                {device for device in associated_entry.get("Devices") or [] if isinstance(device, str)}
            )

    return build_scan(self, timestamp, SOURCE_TOPOLOGY_V2, neighbours, routes, associated_devices, scan_status, hints)


def v2_entry_devices(entry):
    return [record for record in entry.get("Devices") or [] if isinstance(record, Mapping)]


def delete_topology_v2_scan(self, timestamp):
    removed = False
    for nwkid in known_nwkids(self):
        device = self.ListOfDevices.get(nwkid)
        if not isinstance(device, Mapping):
            continue
        for tablename in V2_TABLES:
            table = device.get(tablename)
            if not isinstance(table, list):
                continue
            kept = [
                entry for entry in table
                if not (isinstance(entry, Mapping) and entry.get("Time") == timestamp)
            ]
            if len(kept) != len(table):
                device[tablename] = kept
                removed = True
    return removed


# ---------------------------------------------------------------------------
# Shared record building
# ---------------------------------------------------------------------------
def build_neighbour_record(reporter, neighbour_nwkid, neighbour_infos):
    """One neighbour entry, from the legacy or the TopologyV2 spelling.

    Both store the same keys; they differ only in how numbers are encoded, which
    as_int() handles: the legacy report file keeps the raw hex read off the wire,
    the TopologyV2 tables keep the value already converted.
    """
    return {
        "reporter": reporter,
        "neighbor": neighbour_nwkid,
        "relationship": canonical(neighbour_infos.get("_relationshp"), RELATIONSHIP_ALIASES),
        "device_type": canonical(neighbour_infos.get("_devicetype"), DEVICE_TYPE_ALIASES),
        "lqi": as_int(neighbour_infos.get("_lnkqty")),
        "depth": as_depth(neighbour_infos.get("_depth")),
        "rx_on_when_idle": canonical(neighbour_infos.get("_rxonwhenidl"), ON_OFF_ALIASES),
        "permit_joining": canonical(neighbour_infos.get("_permitjnt"), ON_OFF_ALIASES),
    }


def build_scan(self, timestamp, source, neighbours, routes, associated_devices, scan_status, hints):
    nodes = build_nodes(self, source, neighbours, routes, associated_devices, scan_status, hints)
    return {
        "timestamp": timestamp,
        "source": source,
        "coordinator": COORDINATOR_NWKID,
        "tables": list(TABLES_PER_SOURCE[source]),
        "scan": build_scan_statistics(nodes),
        "nodes": nodes,
        "neighbours": neighbours,
        "routes": routes,
    }


def build_nodes(self, source, neighbours, routes, associated_devices, scan_status, hints):
    """One entry per node, for every device the plugin knows plus every node named
    by the scan.

    Listing the known devices too is what makes a node that never answered
    visible, and saves the caller from joining the report back to /zdevice-name
    by name to recover an IEEE or a model.
    """
    nwkids = known_nwkids(self)
    nwkids.add(COORDINATOR_NWKID)
    nwkids.update(scan_status)
    for neighbour in neighbours:
        nwkids.update((neighbour["reporter"], neighbour["neighbor"]))
    for route in routes:
        nwkids.update(x for x in (route["reporter"], route["destination"], route["next_hop"]) if x)

    carries_associated_devices = TABLE_ASSOCIATED_DEVICES in TABLES_PER_SOURCE[source]

    nodes = []
    for nwkid in sorted(nwkids):
        device = self.ListOfDevices.get(nwkid)
        if not isinstance(device, Mapping):
            device = {}
        logical_type = node_logical_type(nwkid, device, hints["device_type"].get(nwkid))
        nodes.append({
            "nwkid": nwkid,
            "ieee": node_ieee(device, hints["ieee"].get(nwkid)),
            "name": node_name(nwkid, device),
            "logical_type": logical_type,
            "rx_on_when_idle": node_rx_on_when_idle(device, hints["rx_on_when_idle"].get(nwkid)),
            "scan_status": scan_status.get(nwkid) or default_scan_status(logical_type),
            "health": value_or_none(device.get("Health")),
            "model": value_or_none(device.get("Model")),
            "lqi": as_number(device.get("LQI")),
            "rssi": as_number(device.get("RSSI")),
            "battery": as_number(node_battery(device)),
            "associated_devices": associated_devices.get(nwkid, []) if carries_associated_devices else None,
        })
    return nodes


def build_scan_statistics(nodes):
    """How much of the mesh this scan actually covers.

    A node that cannot be scanned at all is not counted as requested, so
    `answered` + `timeout` + `not_scanned` == `requested`.
    """
    counters = {SCAN_OK: 0, SCAN_TIMEOUT: 0, SCAN_NOT_SCANNED: 0, SCAN_NOT_SUPPORTED: 0}
    for node in nodes:
        if node["scan_status"] in counters:
            counters[node["scan_status"]] += 1

    return {
        "requested": counters[SCAN_OK] + counters[SCAN_TIMEOUT] + counters[SCAN_NOT_SCANNED],
        "answered": counters[SCAN_OK],
        "timeout": counters[SCAN_TIMEOUT],
        "not_scanned": counters[SCAN_NOT_SCANNED],
    }


def default_scan_status(logical_type):
    """An end device has no neighbour table to ask for; everything else was simply
    not reached by this scan."""
    return SCAN_NOT_SUPPORTED if logical_type == "end_device" else SCAN_NOT_SCANNED


# ---------------------------------------------------------------------------
# Node attributes
# ---------------------------------------------------------------------------
def node_name(nwkid, device):
    """The display name, or None. Never the nwkid: a name that is secretly an id
    is what made the old payload impossible to join on."""
    name = value_or_none(device.get("ZDeviceName"))
    if name is not None:
        return name
    return COORDINATOR_DEFAULT_NAME if nwkid == COORDINATOR_NWKID else None


def node_ieee(device, reported_ieee):
    """IEEE from ListOfDevices, falling back to what a neighbour reported for a
    node the plugin does not know."""
    return value_or_none(device.get("IEEE")) or value_or_none(reported_ieee)


def node_logical_type(nwkid, device, reported_device_type):
    if nwkid == COORDINATOR_NWKID:
        return "coordinator"

    logical_type = canonical(device.get("LogicalType"), DEVICE_TYPE_ALIASES)
    if logical_type != UNKNOWN:
        return logical_type

    device_type = device.get("DeviceType")
    if device_type == "FFD":
        return "router"
    if device_type == "RFD":
        return "end_device"

    return reported_device_type or UNKNOWN


def node_rx_on_when_idle(device, reported_rx_on_when_idle):
    """From the device MAC capability when known, else from what a neighbour
    reported about it."""
    mac_capability = device.get("MacCapa")
    if isinstance(mac_capability, str) and mac_capability:
        try:
            return "on" if (int(mac_capability, 16) >> 3) & 1 else "off"
        except ValueError:
            pass
    return reported_rx_on_when_idle or UNKNOWN


def node_battery(device):
    battery = value_or_none(device.get("Battery"))
    return device.get("IASBattery") if battery is None else battery


def known_nwkids(self):
    return {nwkid for nwkid, device in self.ListOfDevices.items() if isinstance(device, Mapping)}


# ---------------------------------------------------------------------------
# Hints: what the nodes reported about each other
#
# A node absent from ListOfDevices still shows up in its neighbours' tables, and
# those tables carry its ieee, its device type and its rx-on-when-idle. Keeping
# them lets such a node be reported with something more useful than nulls.
# ---------------------------------------------------------------------------
def new_hints():
    return {"ieee": {}, "device_type": {}, "rx_on_when_idle": {}}


def remember_ieee(hints, nwkid, ieee):
    if nwkid and value_or_none(ieee):
        hints["ieee"].setdefault(nwkid, ieee)


def remember_neighbour(hints, record, ieee):
    neighbour_nwkid = record["neighbor"]
    remember_ieee(hints, neighbour_nwkid, ieee)
    if record["device_type"] != UNKNOWN:
        hints["device_type"].setdefault(neighbour_nwkid, record["device_type"])
    if record["rx_on_when_idle"] != UNKNOWN:
        hints["rx_on_when_idle"].setdefault(neighbour_nwkid, record["rx_on_when_idle"])


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------
def canonical(value, aliases):
    """Translate a backend spelling into the API vocabulary."""
    if value is None:
        return UNKNOWN
    return aliases.get(str(value).strip().lower(), UNKNOWN)


def as_timestamp(value):
    """Integer seconds from any of the three backends.

    zigpy keys its report file with a float time.time(), the other two store
    int(time.time()). The API only ever reports integer seconds.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def as_int(value):
    """LQI and depth, however the backend stored them.

    The legacy report file keeps the raw hex string read off the wire ("c4"),
    TopologyV2 and zigpy keep an int. A string is therefore always hex.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip(), 16)
        except ValueError:
            return None
    return None


def as_depth(value):
    """Tree depth, or None when the radio did not actually report one.

    Zigbee caps the tree depth at 15 (nwkMaxDepth), and a radio with no depth to
    give for a row answers with a sentinel rather than omitting the field: 0xFF
    is common, and shows up mostly on sibling rows, where the depth of the
    neighbour is not something the reporter tracks. An out-of-range value is not
    a reading, so it is reported as unknown instead of being passed on as a
    255-deep node.

    15 is a legal depth and is passed through, even though a radio may well be
    using it as a sentinel too -- the API cannot tell those apart, and
    discarding it would lose the real value on a mesh that is genuinely that
    deep.
    """
    depth = as_int(value)
    return None if depth is None or not 0 <= depth <= MAX_TREE_DEPTH else depth


def as_number(value):
    """A ListOfDevices reading as a number, or None when it holds no reading."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            pass
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def value_or_none(value):
    """None for every way the device database spells "no value".

    ListOfDevices holds "", {} and [] interchangeably for a field that was never
    filled, and a {} stored there comes back as an empty ThreadSafeDeviceDict,
    which does not compare equal to {} -- hence the length test rather than a
    membership test.
    """
    if value is None:
        return None
    if isinstance(value, (str, bytes, Mapping, list, tuple, set)) and len(value) == 0:
        return None
    return value


# ---------------------------------------------------------------------------
# Report files
# ---------------------------------------------------------------------------
def reports_directory(self):
    return Path(self.pluginconf.pluginConf["pluginReports"])


def zigpy_report_path(self):
    return reports_directory(self) / (ZIGPY_REPORT_FILENAME % self.hardwareID)


def legacy_report_path(self):
    return reports_directory(self) / (LEGACY_REPORT_FILENAME % self.hardwareID)


def read_json_file(self, file_path):
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "rt") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        self.logging("Error", "topologyScan: cannot read %s - %s" % (file_path, error))
        return None


def write_json_file(self, file_path, data):
    try:
        with open(file_path, "wt") as handle:
            json.dump(data, handle, indent=4)
    except (OSError, TypeError) as error:
        self.logging("Error", "topologyScan: cannot write %s - %s" % (file_path, error))
        return False
    return True
