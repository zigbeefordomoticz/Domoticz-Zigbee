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

import zigpy.types as t
import traceback


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

        self._NetworkMapPhase = 0
        self.LQIreqInProgress = []
        self.LQIticks = 0


    def retreive_infos_from_zigpy(self):
        self.log.logging("ZigpyTopology", "Log", "retreive_infos_from_zigpy")
        try:
            neighbors, routes = self.ControllerLink.app.get_topology()
            self.ListOfDevices[ "0000" ][ "ZigpyNeighbors"] = list( build_zigpy_neighbors(self, neighbors) )
            self.ListOfDevices[ "0000" ][ "ZigpyRoutes"] = list( build_zigpy_routes(self, routes) )
        except Exception as e:
            self.log.logging("ZigpyTopology", "Log", f"Error while requesting get_topology() - {e}")
            self.log.logging("ZigpyTopology", "Log", f"{(traceback.format_exc())}")
    

    def log_zigpy_routes(self):
        self.log.logging("ZigpyTopology", "Log", "Routes Table")
        for ieee, route_info in self.zigpy_routes.items():
            ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
            for route in route_info:
                dst_nwk = route.DstNWK
                self.log.logging("ZigpyTopology", "Log", f" - {ieee}: {dst_nwk}")


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

            ieee_neighbor = "%016x" % t.uint64_t.deserialize(neighbor.ieee.serialize())[0]
            if ieee_neighbor not in ieee2nwk_keys:
                continue

            nwkid_neighbor = neighbor.nwk.serialize()[::-1].hex()
            if nwkid_neighbor not in self.ListOfDevices:
                continue

            relationship = neighbor.relationship
            if relationship == 0x00:  # Relationship.Parent
                raw_neighbors_set.add( (nwkid_neighbor, nwkid_parent, "child") )

            elif relationship == 0x01:  # Relationship.Child
                raw_neighbors_set.add( (nwkid_parent, nwkid_neighbor, "child") )

            elif relationship == 0x02:  # Relationship.Sibling
                raw_neighbors_set.add( (nwkid_parent, nwkid_neighbor, "sibling") )
                
    return convert_siblings( raw_neighbors_set )


def build_zigpy_routes(self, zigpy_routes):
    raw_root = set()
    ieee2nwk_keys = set(self.IEEE2NWK.keys())

    for ieee, route_info in zigpy_routes.items():
        ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
        if ieee not in ieee2nwk_keys:
            continue
        nwkid = self.IEEE2NWK[ ieee ]

        for route in route_info:
            dst_nwk = route.DstNWK.serialize()[::-1].hex()
            if dst_nwk not in self.ListOfDevices:
                continue
            route_tuple = (nwkid, dst_nwk)
            reverse_route_tuple = (dst_nwk, nwkid)
            if route_tuple not in raw_root and reverse_route_tuple not in raw_root:
                raw_root.add(route_tuple)           
    return raw_root



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