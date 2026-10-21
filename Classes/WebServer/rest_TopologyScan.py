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
    Module: rest_TopologyScan.py

    Description: The /topology-scan REST API (issue #2106).

        /topologie is left exactly as it is: the two existing WebUI charts
        consume it, and older WebUI builds are deployed against running plugins.
        This is the second, richer contract, next to it.

        GET    /topology-scan                      list of stored scans
        GET    /topology-scan/<timestamp>          one scan, whole
        GET    /topology-scan/<timestamp>/nodes
        GET    /topology-scan/<timestamp>/neighbours
        GET    /topology-scan/<timestamp>/routes
        DELETE /topology-scan                      remove every stored scan
        DELETE /topology-scan/<timestamp>          remove one stored scan

        GET    /zigpy-topology-raw                 Zigpy-Topology-XX.json, untouched

        A graph needs nodes, neighbours and routes at once, so the whole-scan
        call is the one to build a graph from; the sub-resources are a
        convenience for other tooling, and answer with the same envelope
        carrying only the collection asked for -- `source` and `tables` stay, so
        an empty list is still distinguishable from a table the active backend
        cannot fill.

        Modules/topologyScan.py holds the model and documents the payload.
"""

import json

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.topologyScan import (delete_all_topology_scans,
                                  delete_topology_scan, get_topology_scan,
                                  list_topology_scans,
                                  read_raw_zigpy_topology_report,
                                  topology_scan_in_progress)

# Sub-resource path element -> key of the scan envelope. Both spellings of
# "neighbours" are accepted, as the field inside a record is spelled "neighbor".
SUB_RESOURCES = {
    "nodes": "nodes",
    "neighbours": "neighbours",
    "neighbors": "neighbours",
    "routes": "routes",
}

ENVELOPE_METADATA = ("timestamp", "source", "coordinator", "tables", "scan")


def rest_topology_scan(self, verb, data, parameters):
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if verb == "GET":
        return topology_scan_get(self, parameters, _response)

    if verb == "DELETE":
        return topology_scan_delete(self, parameters, _response)

    return _response


def rest_zigpy_topology_raw(self, verb, data, parameters):
    """The zigpy report file as it is on disk, for diagnostics and bug reports.

    Explicitly backend-specific and explicitly not what the graph consumes: an
    empty list on anything but a zigpy setup.
    """
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if verb != "GET":
        return _response

    if self.zigbee_communication != "zigpy":
        _response["Data"] = json.dumps([])
        return _response

    _response["Data"] = json.dumps(read_raw_zigpy_topology_report(self))
    return _response


def topology_scan_get(self, parameters, _response):
    if self.fake_mode():
        return fake_topology_scan_get(self, parameters, _response)

    if len(parameters) == 0:
        _response["Data"] = json.dumps(list_topology_scans(self))
        return _response

    if len(parameters) > 2:
        return respond_with_error(self, _response, "400 BAD REQUEST", "unexpected parameters %s" % parameters[2:])

    timestamp = requested_timestamp(parameters[0])
    if timestamp is None:
        return respond_with_error(self, _response, "400 BAD REQUEST", "invalid timestamp '%s'" % parameters[0])

    sub_resource = None
    if len(parameters) == 2:
        sub_resource = SUB_RESOURCES.get(str(parameters[1]).lower())
        if sub_resource is None:
            return respond_with_error(
                self, _response, "400 BAD REQUEST",
                "unknown sub-resource '%s', expecting one of %s" % (parameters[1], sorted(set(SUB_RESOURCES.values())))
            )

    scan = get_topology_scan(self, timestamp)
    if scan is None:
        return respond_with_error(self, _response, "404 NOT FOUND", "no topology scan with timestamp %s" % timestamp)

    _response["Data"] = json.dumps(scan if sub_resource is None else extract_sub_resource(scan, sub_resource))
    return _response


def extract_sub_resource(scan, sub_resource):
    """The scan envelope, carrying only the collection asked for."""
    partial = {key: scan[key] for key in ENVELOPE_METADATA}
    partial[sub_resource] = scan[sub_resource]
    return partial


def topology_scan_delete(self, parameters, _response):
    if len(parameters) == 0:
        removed = delete_all_topology_scans(self)
        self.logging("Status", "Topology scans removed from: %s" % (", ".join(removed) or "nothing"))
        _response["Data"] = json.dumps({"Name": "All topology scans removed", "sources": removed})
        return _response

    if len(parameters) > 1:
        return respond_with_error(self, _response, "400 BAD REQUEST", "unexpected parameters %s" % parameters[1:])

    timestamp = requested_timestamp(parameters[0])
    if timestamp is None:
        return respond_with_error(self, _response, "400 BAD REQUEST", "invalid timestamp '%s'" % parameters[0])

    if topology_scan_in_progress(self) == timestamp:
        return respond_with_error(
            self, _response, "400 BAD REQUEST", "topology scan %s is still in progress" % timestamp
        )

    removed = delete_topology_scan(self, timestamp)
    if not removed:
        return respond_with_error(self, _response, "404 NOT FOUND", "no topology scan with timestamp %s" % timestamp)

    self.logging("Status", "Topology scan %s removed from: %s" % (timestamp, ", ".join(removed)))
    _response["Data"] = json.dumps({"Name": "Topology scan %s removed" % timestamp, "sources": removed})
    return _response


def requested_timestamp(parameter):
    """A scan is addressed by its integer-seconds timestamp, and by nothing else."""
    parameter = str(parameter).strip()
    return int(parameter) if parameter.isdigit() else None


def respond_with_error(self, _response, status, message):
    self.logging("Debug", "rest_topology_scan - %s: %s" % (status, message))
    _response["Status"] = status
    _response["Data"] = json.dumps({"BE_Error": message})
    return _response


# ---------------------------------------------------------------------------
# Fake mode: the WebUI can be developed against the plugin without a radio
# ---------------------------------------------------------------------------
def fake_topology_scan_get(self, parameters, _response):
    scan = dummy_topology_scan()

    if len(parameters) == 0:
        _response["Data"] = json.dumps([{
            "timestamp": scan["timestamp"],
            "source": scan["source"],
            "tables": scan["tables"],
            "nodes": len(scan["nodes"]),
            "neighbours": len(scan["neighbours"]),
            "routes": len(scan["routes"]),
            "scan": scan["scan"],
        }])
        return _response

    sub_resource = SUB_RESOURCES.get(str(parameters[1]).lower()) if len(parameters) == 2 else None
    _response["Data"] = json.dumps(scan if sub_resource is None else extract_sub_resource(scan, sub_resource))
    return _response


def dummy_topology_scan():
    """A small mesh with everything the envelope can carry: an asymmetric link
    (0000 hears 1a2b at 196, 1a2b hears 0000 at 164), a node that timed out, a
    sleepy end device no router reports, and a two-hop route."""
    return {
        "timestamp": 1711537200,
        "source": "zigpy",
        "coordinator": "0000",
        "tables": ["neighbours", "routes"],
        "scan": {"requested": 3, "answered": 2, "timeout": 1, "not_scanned": 0},
        "nodes": [
            {
                "nwkid": "0000", "ieee": "00124b0022334455", "name": "Zigbee Coordinator",
                "logical_type": "coordinator", "rx_on_when_idle": "on", "scan_status": "ok",
                "health": "Live", "model": None, "lqi": None, "rssi": None, "battery": None,
                "associated_devices": None,
            },
            {
                "nwkid": "1a2b", "ieee": "680ae2fffe7aca89", "name": "Repeater",
                "logical_type": "router", "rx_on_when_idle": "on", "scan_status": "ok",
                "health": "Live", "model": "TRADFRI Signal Repeater", "lqi": 196, "rssi": None,
                "battery": None, "associated_devices": None,
            },
            {
                "nwkid": "7a8b", "ieee": "60a423fffe529d60", "name": "Led LKex",
                "logical_type": "router", "rx_on_when_idle": "on", "scan_status": "timeout",
                "health": "Not seen last 24hours", "model": "LXEK-1", "lqi": 42, "rssi": None,
                "battery": None, "associated_devices": None,
            },
            {
                "nwkid": "c6ca", "ieee": "000d6ffffea1e6da", "name": "OnOff Ikea",
                "logical_type": "end_device", "rx_on_when_idle": "off", "scan_status": "not_supported",
                "health": "Live", "model": "TRADFRI onoff switch", "lqi": 94, "rssi": None,
                "battery": 100, "associated_devices": None,
            },
        ],
        "neighbours": [
            {
                "reporter": "0000", "neighbor": "1a2b", "relationship": "child",
                "device_type": "router", "lqi": 196, "depth": 1,
                "rx_on_when_idle": "on", "permit_joining": "off",
            },
            {
                "reporter": "1a2b", "neighbor": "0000", "relationship": "parent",
                "device_type": "coordinator", "lqi": 164, "depth": 0,
                "rx_on_when_idle": "on", "permit_joining": "off",
            },
            {
                "reporter": "1a2b", "neighbor": "7a8b", "relationship": "sibling",
                "device_type": "router", "lqi": 121, "depth": 1,
                "rx_on_when_idle": "on", "permit_joining": "off",
            },
        ],
        "routes": [
            {
                "reporter": "0000", "destination": "7a8b", "next_hop": "1a2b",
                "status": "active", "many_to_one": False, "memory_constrained": False,
                "route_record_required": False,
            },
        ],
    }
