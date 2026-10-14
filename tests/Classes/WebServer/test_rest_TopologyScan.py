#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.rest_TopologyScan, the /topology-scan endpoint
(issue #2106).

Modules/topologyScan.py is covered on its own in tests/Modules; what is checked
here is the HTTP contract around it: the status a caller gets back, the shape of
a sub-resource answer, and that /topologie is not what answers any of this.

Both this module and the model import nothing from Modules.* beyond
Modules.topologyScan, which is stdlib-only, so no subprocess is needed.
"""

import json

import pytest

from Classes.WebServer.rest_TopologyScan import (
    rest_topology_scan, rest_topology_scan_associated_devices,
    rest_zigpy_topology_raw)

HARDWARE_ID = 1
TIMESTAMP = 1711537200


class FakePluginConf:
    def __init__(self, reports_directory):
        self.pluginConf = {
            "pluginReports": str(reports_directory),
            "ZigpyTopologyReport": True,
            "TopologyV2": False,
            "numTopologyReports": 4,
            "enableKeepalive": False,
            "enableCache": False,
        }


class FakePlugin:
    def __init__(self, reports_directory, fake=False):
        self.pluginconf = FakePluginConf(reports_directory)
        self.hardwareID = HARDWARE_ID
        self.zigbee_communication = "zigpy"
        self.ListOfDevices = {
            "0000": {"IEEE": "00124b0022334455", "LogicalType": "Coordinator", "MacCapa": "8e"},
            "1a2b": {"IEEE": "680ae2fffe7aca89", "ZDeviceName": "Repeater", "LogicalType": "Router"},
        }
        self.logs = []
        self._fake = fake

    def fake_mode(self):
        return self._fake

    def logging(self, level, message):
        self.logs.append((level, message))


def report_entry():
    return {
        "%s.123456" % TIMESTAMP: {
            "Neighbors": {
                "0000": {
                    "ieee": "00124b0022334455",
                    "relationship": [{
                        "nwkid": "1a2b", "ieee": "680ae2fffe7aca89", "relationship": "child",
                        "device_type": "router", "rx_on_when_idle": "on",
                        "lqi_from_device": 196, "depth": 1, "permit_joining": "off",
                    }],
                },
            },
            "Routes": {
                "0000": [{
                    "dst_nwk": "1a2b", "route_status": "active", "memory_constrained": 0,
                    "many_to_one": 0, "route_record_required": 0, "next_hop": "1a2b",
                }],
            },
        }
    }


@pytest.fixture
def plugin(tmp_path):
    (tmp_path / ("Zigpy-Topology-%02d.json" % HARDWARE_ID)).write_text(json.dumps([report_entry()]))
    return FakePlugin(tmp_path)


def call(plugin, verb, parameters):
    response = rest_topology_scan(plugin, verb, None, parameters)
    return response, json.loads(response["Data"])


def test_get_without_parameter_lists_the_stored_scans(plugin):
    response, payload = call(plugin, "GET", [])

    assert response["Status"] == "200 OK"
    assert payload == [{
        "timestamp": TIMESTAMP,
        "source": "zigpy",
        "tables": ["neighbours", "routes"],
        "nodes": 2,
        "neighbours": 1,
        "routes": 1,
        "scan": {"requested": 2, "answered": 1, "timeout": 0, "not_scanned": 1},
    }]


def test_get_one_scan_answers_nodes_neighbours_and_routes_in_one_call(plugin):
    # A graph needs all three at once; three round trips is three chances to
    # draw a half-built graph.
    _, payload = call(plugin, "GET", [str(TIMESTAMP)])

    assert payload["timestamp"] == TIMESTAMP
    assert payload["coordinator"] == "0000"
    assert [entry["nwkid"] for entry in payload["nodes"]] == ["0000", "1a2b"]
    assert payload["neighbours"][0]["reporter"] == "0000"
    assert payload["routes"][0]["next_hop"] == "1a2b"


@pytest.mark.parametrize("sub_resource,other", [
    ("nodes", "neighbours"),
    ("neighbours", "routes"),
    ("neighbors", "routes"),
    ("routes", "nodes"),
])
def test_a_sub_resource_keeps_the_envelope_metadata(plugin, sub_resource, other):
    _, payload = call(plugin, "GET", [str(TIMESTAMP), sub_resource])

    expected_key = "neighbours" if sub_resource == "neighbors" else sub_resource
    assert expected_key in payload
    assert other not in payload
    # `source` and `tables` stay, so an empty list is still distinguishable from
    # a table this backend cannot fill at all
    assert payload["source"] == "zigpy"
    assert payload["tables"] == ["neighbours", "routes"]
    assert payload["timestamp"] == TIMESTAMP


def test_an_unknown_timestamp_is_a_404(plugin):
    response, payload = call(plugin, "GET", ["1234567890"])

    assert response["Status"] == "404 NOT FOUND"
    assert "1234567890" in payload["BE_Error"]


@pytest.mark.parametrize("parameters", [
    ["not-a-timestamp"],
    ["1711537200.123456"],
    ["-1711537200"],
])
def test_a_scan_is_addressed_by_integer_seconds_only(plugin, parameters):
    response, payload = call(plugin, "GET", parameters)

    assert response["Status"] == "400 BAD REQUEST"
    assert "invalid timestamp" in payload["BE_Error"]


def test_an_unknown_sub_resource_is_a_400(plugin):
    response, payload = call(plugin, "GET", [str(TIMESTAMP), "bindings"])

    assert response["Status"] == "400 BAD REQUEST"
    assert "bindings" in payload["BE_Error"]


def test_a_deeper_path_is_a_400(plugin):
    response, _ = call(plugin, "GET", [str(TIMESTAMP), "routes", "0000"])

    assert response["Status"] == "400 BAD REQUEST"


def test_delete_removes_the_scan_and_says_from_where(plugin):
    response, payload = call(plugin, "DELETE", [str(TIMESTAMP)])

    assert response["Status"] == "200 OK"
    assert payload["sources"] == ["zigpy"]
    assert call(plugin, "GET", [])[1] == []


def test_delete_of_an_unknown_scan_is_a_404(plugin):
    response, _ = call(plugin, "DELETE", ["1234567890"])

    assert response["Status"] == "404 NOT FOUND"


def test_delete_without_parameter_removes_every_scan(plugin):
    response, payload = call(plugin, "DELETE", [])

    assert response["Status"] == "200 OK"
    assert payload["sources"] == ["zigpy"]
    assert call(plugin, "GET", [])[1] == []


def test_the_running_scan_cannot_be_deleted(plugin):
    plugin.ListOfDevices["0000"]["TopologyStartTime"] = TIMESTAMP

    response, payload = call(plugin, "DELETE", [str(TIMESTAMP)])

    assert response["Status"] == "400 BAD REQUEST"
    assert "in progress" in payload["BE_Error"]


def test_fake_mode_answers_a_complete_envelope(tmp_path):
    plugin = FakePlugin(tmp_path, fake=True)

    _, summaries = call(plugin, "GET", [])
    _, scan = call(plugin, "GET", [str(summaries[0]["timestamp"])])

    assert summaries[0]["nodes"] == len(scan["nodes"])
    assert {entry["scan_status"] for entry in scan["nodes"]} == {"ok", "timeout", "not_supported"}
    assert scan["routes"][0]["next_hop"] == "1a2b"


def test_an_unsupported_verb_answers_no_data(plugin):
    response = rest_topology_scan(plugin, "PUT", None, [])

    assert response["Data"] == {}


# --- /zigpy-topology-raw --------------------------------------------------
def test_the_raw_passthrough_is_the_report_file_untouched(plugin):
    response = rest_zigpy_topology_raw(plugin, "GET", None, [])

    assert json.loads(response["Data"]) == [report_entry()]


def test_the_raw_passthrough_is_empty_on_a_non_zigpy_setup(plugin):
    plugin.zigbee_communication = "native"

    response = rest_zigpy_topology_raw(plugin, "GET", None, [])

    assert json.loads(response["Data"]) == []


# ---------------------------------------------------------------------------
# GET /topology-scan-associated-devices
# ---------------------------------------------------------------------------
class FakeCollector:
    """The collector, as far as this endpoint is concerned."""

    def __init__(self, nodes_to_ask=1, collecting=False):
        self.nodes_to_ask = nodes_to_ask
        self.collecting = collecting
        self.starts = 0

    def in_progress(self):
        return self.collecting

    def start_scan(self):
        self.starts += 1
        return bool(self.nodes_to_ask)


class FakeNetworkMap:
    def __init__(self, phase=0):
        self.phase = phase

    def NetworkMapPhase(self):
        return self.phase


class FakeZigpyTopology:
    def __init__(self, scanning=False):
        self.ControllerLink = type("ControllerLink", (), {"app": object()})()
        self.scanning = scanning

    def is_zigpy_topology_in_progress(self):
        return self.scanning


@pytest.fixture
def collect_plugin(tmp_path):
    plugin = FakePlugin(tmp_path)
    plugin.networkmap = FakeNetworkMap()
    plugin.zigpy_topology = FakeZigpyTopology()
    plugin.associated_devices_scan = FakeCollector()
    return plugin


def collect(plugin, parameters=None):
    response = rest_topology_scan_associated_devices(plugin, "GET", None, parameters or [])
    return response, json.loads(response["Data"])


def test_the_collection_starts_and_answers_immediately(collect_plugin):
    """The collection takes minutes; the caller polls /plugin-health."""
    response, payload = collect(collect_plugin)

    assert response["Status"] == "200 OK"
    assert payload["Name"] == "Req-Topology-AssociatedDevices"
    assert collect_plugin.associated_devices_scan.starts == 1


def test_the_setting_is_not_required_to_ask_for_the_table_explicitly(collect_plugin):
    """ZigpyTopologyAssociatedDevices decides whether a *topology scan* collects
    the table as well. Asking for the table is the request itself."""
    collect_plugin.pluginconf.pluginConf["ZigpyTopologyAssociatedDevices"] = False

    response, _ = collect(collect_plugin)
    assert response["Status"] == "200 OK"
    assert collect_plugin.associated_devices_scan.starts == 1


def test_a_second_collection_is_refused_while_one_runs(collect_plugin):
    collect_plugin.associated_devices_scan.collecting = True

    response, payload = collect(collect_plugin)
    assert response["Status"] == "400 BAD REQUEST"
    assert "already in progress" in payload["BE_Error"]
    assert collect_plugin.associated_devices_scan.starts == 0


def test_it_is_refused_while_a_zigpy_scan_runs(collect_plugin):
    """Two scanners on the same routers at once is what the whole design avoids."""
    collect_plugin.zigpy_topology.scanning = True

    response, payload = collect(collect_plugin)
    assert response["Status"] == "400 BAD REQUEST"
    assert collect_plugin.associated_devices_scan.starts == 0


def test_it_is_refused_while_a_native_scan_runs(collect_plugin):
    collect_plugin.networkmap.phase = 2

    response, _ = collect(collect_plugin)
    assert collect_plugin.associated_devices_scan.starts == 0


def test_it_is_refused_on_a_native_coordinator(collect_plugin):
    """A TopologyV2 scan collects the same table with every scan there."""
    collect_plugin.zigbee_communication = "native"

    response, payload = collect(collect_plugin)
    assert response["Status"] == "400 BAD REQUEST"
    assert "zigpy" in payload["BE_Error"]
    assert collect_plugin.associated_devices_scan.starts == 0


def test_it_is_refused_when_the_zigpy_topology_report_is_off(collect_plugin):
    """The collection is ticked from the zigpy topology lifecycle, which does not
    run with ZigpyTopologyReport off -- starting it would hang."""
    collect_plugin.pluginconf.pluginConf["ZigpyTopologyReport"] = False

    response, payload = collect(collect_plugin)
    assert response["Status"] == "400 BAD REQUEST"
    assert "ZigpyTopologyReport" in payload["BE_Error"]
    assert collect_plugin.associated_devices_scan.starts == 0


def test_it_is_refused_before_the_collector_exists(collect_plugin):
    collect_plugin.associated_devices_scan = None

    response, payload = collect(collect_plugin)
    assert response["Status"] == "503 SERVICE UNAVAILABLE"


def test_it_is_refused_when_there_is_nothing_to_ask(collect_plugin):
    collect_plugin.associated_devices_scan.nodes_to_ask = 0

    response, payload = collect(collect_plugin)
    assert response["Status"] == "400 BAD REQUEST"
    assert "no coordinator or router" in payload["BE_Error"]


def test_unexpected_parameters_are_refused(collect_plugin):
    response, payload = collect(collect_plugin, ["1711537200"])

    assert response["Status"] == "400 BAD REQUEST"
    assert collect_plugin.associated_devices_scan.starts == 0


def test_only_get_starts_a_collection(collect_plugin):
    for verb in ("PUT", "DELETE", "POST"):
        response = rest_topology_scan_associated_devices(collect_plugin, verb, None, [])
        assert response["Status"] == "200 OK"
        assert collect_plugin.associated_devices_scan.starts == 0
