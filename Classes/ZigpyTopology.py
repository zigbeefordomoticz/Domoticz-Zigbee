#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import json
import os.path
import time
import traceback
from pathlib import Path

import zigpy.types as t

ZIGPY_TOPOLOGY_REPORT_FILENAME = "Zigpy-Topology-"
class ZigpyTopology:
    
    def __init__(self, zigbee_communitation, PluginConf, ZigateComm, ListOfDevices, IEEE2NWK, Devices, HardwareID, log):
        self.zigbee_communication = zigbee_communitation
        self.pluginconf = PluginConf
        self.ControllerLink = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.IEEE2NWK = IEEE2NWK
        self.Devices = Devices
        self.HardwareID = HardwareID
        self.log = log
        self.FirmwareVersion = None
        self.new_scan_detected = None
        self.neighbors_table = {}


    def copy_zigpy_infos_to_plugin(self, neighbors_list=None, routes_list=None):
        if neighbors_list is None and routes_list is None:
            neighbors, routes = self.ControllerLink.app.get_topology()
            neighbors_list = build_zigpy_neighbors(self, neighbors)
            routes_list = build_zigpy_routes(self, routes)

        self.log.logging("ZigpyTopology", "Log", "copy_zigpy_infos_to_plugin")
        try:
            self.ListOfDevices[ "0000" ][ "ZigpyNeighbors"] = neighbors_list
            self.ListOfDevices[ "0000" ][ "ZigpyRoutes"] = routes_list

        except Exception as e:
            self.log.logging("ZigpyTopology", "Debug", f"Error while requesting get_topology() - {e}")
            self.log.logging("ZigpyTopology", "Debug", f"{(traceback.format_exc())}")


    def save_topology_report(self):
        self.log.logging("ZigpyTopology", "Debug", "save_topology_report")
        neighbors, routes = self.ControllerLink.app.get_topology()
        neighbors_list = build_zigpy_neighbors(self, neighbors)
        routes_list = build_zigpy_routes(self, routes)
        self.copy_zigpy_infos_to_plugin(neighbors_list, routes_list)
        save_report_to_file(self, time.time(), neighbors_list, routes_list)


    def is_zigpy_topology_in_progress(self):
        return self.ControllerLink.app.is_zigpy_topology_in_progress()


def save_report_to_file(self, time_stamp, neighbors, routes):
    self.log.logging("ZigpyTopology", "Debug", "save_report_to_file")
    zigpy_topology_reports_filename = Path( self.pluginconf.pluginConf["pluginReports"] ) / ( ZIGPY_TOPOLOGY_REPORT_FILENAME + "%02d.json" % self.HardwareID)
    if not os.path.isdir( Path(self.pluginconf.pluginConf["pluginReports"]) ):
        self.log.logging("ZigpyTopology", "Error", "save_report_to_file: Unable to get access to directory %s, please check PluginConf.json" % (self.pluginconf.pluginConf["pluginReports"]), )
        return

    new_report = { time_stamp: { "Neighbors": neighbors, "Routes":routes }}
    available_reports = read_topology_report(zigpy_topology_reports_filename)

    available_reports.append(new_report)
    if len(available_reports) > self.pluginconf.pluginConf["numTopologyReports"]:
        available_reports.pop(0)  # Remove the first entry    

    write_json_file(zigpy_topology_reports_filename, available_reports)


def read_topology_report(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    else:
        return []


def write_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
        

def build_zigpy_neighbors(self, neighbors):
    """ Build a list of Neighbor tuples """
    raw_neighbors_set = set()
    ieee2nwk_keys = set(self.IEEE2NWK.keys())

    for ieee, neighbor_list in neighbors.items():
        ieee_parent = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
        if ieee_parent not in ieee2nwk_keys:
            continue
        
        nwkid_parent = self.IEEE2NWK[ ieee_parent ]
        for neighbor in neighbor_list:
            neighbor_info_dict = parse_neigbor_infos(neighbor)
            
            if neighbor_info_dict["ieee_neighbor"] not in ieee2nwk_keys:
                continue

            if neighbor_info_dict["nwkid_neighbor"] not in self.ListOfDevices:
                continue
        
            self.log.logging("ZigpyTopology", "Debug", f"build_zigpy_neighbors adding {nwkid_parent} with {neighbor_info_dict}")
            add_to_neighbors_table( self, ieee_parent, nwkid_parent, neighbor_info_dict)
    return self.neighbors_table


def add_to_neighbors_table( self, ieee_parent, nwkid_parent, neighbor_info_dict):
    nwkid_neighbor = neighbor_info_dict["nwkid_neighbor"]
    ieee_neighbor = neighbor_info_dict["ieee_neighbor"]
    
    if nwkid_parent not in self.neighbors_table:
        self.neighbors_table[ nwkid_parent ] = {
            "ieee": ieee_parent,
            "relationship": [],  # Initialize as empty list
        }
        
    # Check if the relationship exists before adding it
    relationship_exists = any(
        rel["nwkid"] == nwkid_neighbor and rel["ieee"] == ieee_neighbor
        for rel in self.neighbors_table[nwkid_parent]["relationship"]
    )
            
    # Add relationship if it doesn't exist already
    if not relationship_exists:
        self.neighbors_table[nwkid_parent]["relationship"].append(
            { "nwkid": nwkid_neighbor,
                "ieee": ieee_neighbor,
                "relationship": neighbor_info_dict["relationship"],
                "device_type": neighbor_info_dict[ "device_type"],
                "rx_on_when_idle": neighbor_info_dict[ "rx_on_when_idle"],
                "lqi_from_device": neighbor_info_dict[ "lqi"],
                "permit_joining": neighbor_info_dict[ "permit_joining"]}
        )
        self.log.logging("ZigpyTopology", "Debug", f"build_zigpy_neighbors adding relation {self.neighbors_table[nwkid_parent]['relationship']}")
        

def parse_neigbor_infos( neighbor ):
    return {
        "ieee_neighbor": "%016x" % t.uint64_t.deserialize(neighbor.ieee.serialize())[0],
        "nwkid_neighbor": neighbor.nwk.serialize()[::-1].hex(),
        "device_type": convert_device_type_code(neighbor.device_type),
        "rx_on_when_idle": convert_rx_on_when_idle(neighbor.rx_on_when_idle),
        "relationship": convert_relationship_code(neighbor.relationship),
        "permit_joining": convert_permit_joining(neighbor.permit_joining),
        "lqi": neighbor.lqi
    }


def convert_relationship_code(code):
    relationship_mapping = {
        0x00: "parent",
        0x01: "child",
        0x02: "sibling",
        0x03: "none_of_above",
        0x04: "previous_child"
    }
    return relationship_mapping.get(code, "unknown")


def convert_device_type_code(code):
    device_type_mapping = {
        0x00: "coordinator",
        0x01: "router",
        0x02: "end_device",
        0x03: "unknown"
    }
    return device_type_mapping.get(code, "unknown")


def convert_rx_on_when_idle(code):
    rx_on_when_idle_mapping = {
        0x00: "off",
        0x01: "on",
        0x02: "unknown"
    }
    return rx_on_when_idle_mapping.get(code, "unknown")

   
def convert_permit_joining(code):
    permit_joining_mapping = {
        0x00: "off",
        0x01: "on",
        0x02: "unknown"
    }
    return permit_joining_mapping.get(code, "unknown")


def build_zigpy_routes(self, zigpy_routes):
    raw_root = {}
    ieee2nwk_keys = set(self.IEEE2NWK.keys())

    for ieee, route_info in zigpy_routes.items():
        ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
        if ieee not in ieee2nwk_keys:
            continue
        nwkid = self.IEEE2NWK[ ieee ]
        if nwkid not in raw_root:
            raw_root[ nwkid ] = []

        for route in route_info:
            route_dict = parse_route_infos( route)
            dst_nwk = route_dict["dst_nwk"]
            if dst_nwk not in self.ListOfDevices:
                continue
            raw_root[ nwkid ].append( route_dict)
    return raw_root


def parse_route_infos( route):
    return {
        "dst_nwk": route.DstNWK.serialize()[::-1].hex(),
        "route_status": convert_route_status_code(route.RouteStatus),
        "memory_constrained": route.MemoryConstrained,
        "many_to_one": route.RouteRecordRequired,
        "route_record_required": route.RouteRecordRequired,
        "next_hop": route.NextHop.serialize()[::-1].hex()
    }
    

def convert_route_status_code(code):
    route_status_mapping = {
        0x00: "active",
        0x01: "discovery_underway",
        0x02: "discovery_failed",
        0x03: "inactive",
        0x04: "validation_underway",
    }
    return route_status_mapping.get(code, "unknown")


def retreive_relationship( nwkid_parent, neighbor_info_dict):
    nwkid_relationship = neighbor_info_dict["relationship"]
    nwkid_neighbor = neighbor_info_dict["nwkid_neighbor"]

    if nwkid_relationship == 0x00:  # Relationship.Parent
        return (nwkid_neighbor, nwkid_parent, "child")

    elif nwkid_relationship == 0x01:  # Relationship.Child
        return (nwkid_parent, nwkid_neighbor, "child")

    elif nwkid_relationship == 0x02:  # Relationship.Sibling
        return (nwkid_parent, nwkid_neighbor, "sibling")

    return None


def find_parent(node, relationships):
    """
    Helper function to find the parent of a node recursively.
    """
    parent = relationships.get(node)
    return node if parent is None else find_parent(parent, relationships)


def convert_siblings(tuples_set):
    """ convert any Sibling relationship into a Child one. Need to find the Parent of the Sibling"""
    
    relationships = {}
    for node1, node2, relationship in tuples_set:
        if relationship == 'child':
            relationships[node2] = node1
        elif relationship == 'sibling':
            continue

    converted_tuples = set()
    for node1, node2, relationship in tuples_set:
        if relationship == 'child':
            converted_tuples.add( (node1, node2, relationship) )
        elif relationship == 'sibling':
            parent1 = find_parent(node1, relationships)
            parent2 = find_parent(node2, relationships)
            converted_tuples.add( (parent1, node2, 'child') )

    return converted_tuples