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
        self.zigpy_neighbors = None  # Table of Neighbors
        self.zigpy_routes = None


    def retreive_infos_from_zigpy(self):
        neighbors, zigpy_routes = self.zigbee_communication.app.get_topology()
        build_zigpy_neighbors(self, neighbors)
        
        

        
        
    def log_zigpy_neighbors(self):
        
        self.log.logging("TransportZigpy", "Log", "Neighbors Table")
        for ieee, neighbor_list in self.zigpy_neighbors.items():
            ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
            for neighbor in neighbor_list:
                ieee_neighbor = "%016x" % t.uint64_t.deserialize(neighbor.serialize())[0]
                nwkid = neighbor.nwk
                relationship = neighbor.relationship
                self.log.logging("TransportZigpy", "Log", f" - {ieee}: {nwkid} {relationship}")

    def log_zigpy_routes(self):
        self.log.logging("TransportZigpy", "Log", "Routes Table")
        for ieee, route_info in self.zigpy_routes.items():
            ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
            for route in route_info:
                dst_nwk = route.DstNWK
                self.log.logging("TransportZigpy", "Log", f" - {ieee}: {dst_nwk}")




def build_zigpy_neighbors(self, neighbors):
    self.zigpy_neighbors = set()
    for ieee, neighbor_list in neighbors.items():
        ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
        if ieee not in self.IEEE2NWK:
            continue
        nwkid = self.IEEE2NWK[ ieee ]
        for neighbor in neighbor_list:
            ieee_neighbor = "%016x" % t.uint64_t.deserialize(neighbor.serialize())[0]
            nwkid_neighbor = neighbor.nwk
            relationship = neighbor.relationship
            if relationship == 0x00:  # Relationship.Parent
                self.zigpy_neighbors.append( nwkid_neighbor, nwkid, "Child")

            elif relationship == 0x01:  # Relationship.Child
                self.zigpy_neighbors.append( nwkid, nwkid_neighbor, "Child")

            elif relationship == 0x02:  # Relationship.Sibling
                self.zigpy_neighbors.append( nwkid, nwkid_neighbor, "Sibling")
                
            self.log.logging("TransportZigpy", "Log", f" - {ieee}: {nwkid_neighbor} {relationship}")
