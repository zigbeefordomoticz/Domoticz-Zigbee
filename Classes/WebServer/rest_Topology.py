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
import os
import os.path
from pathlib import Path
from time import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.zb_tables_management import (get_device_table_entry,
                                          get_list_of_timestamps,
                                          remove_entry_from_all_tables)

ZIGPY_TOPOLOGY_REPORT_FILENAME = "Zigpy-Topology-"

def rest_req_topologie(self, verb, data, parameters):
    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb == "GET":
        action = {"Name": "Req-Topology", "TimeStamp": int(time())}
        _response["Data"] = json.dumps(action, sort_keys=True)

        self.logging("Status", "Request a Start of Network Topology scan")
        if self.networkmap:
            if self.pluginconf.pluginConf["ZigpyTopologyReport"] and self.zigbee_communication == "zigpy":
                # Zigpy Topology report
                self.ListOfDevices["0000"]["ZigpyTopologyRequested"] = True
                self.ControllerLink.sendData( "ZIGPY-TOPOLOGY-SCAN", {})

            elif not self.networkmap.NetworkMapPhase():
                # Legacy Topology
                self.networkmap.start_scan()
            else:
                self.logging("Error", "Cannot start Network Topology as one is in progress...")

    return _response


def dummy_topology_report( ):
    
    return [{"Child": "IAS Sirene", "DeviceType": "Router", "Father": "Zigbee Coordinator", "_lnkqty": 58}, 
            {"Child": "IAS Sirene", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 252}, 
            {"Child": "IAS Sirene", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 241}, 
            {"Child": "OnOff Ikea", "DeviceType": "End Device", "Father": "IAS Sirene", "_lnkqty": 255}, 
            {"Child": "Repeater", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 254}, 
            {"Child": "Repeater", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 196}, 
            {"Child": "Repeater", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 254}, 
            {"Child": "Motion frient", "DeviceType": "End Device", "Father": "Repeater", "_lnkqty": 168}, 
            {"Child": "Dim Ikea", "DeviceType": "End Device", "Father": "Repeater", "_lnkqty": 89}, 
            {"Child": "Led LKex", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 254}, 
            {"Child": "Led LKex", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 244}, 
            {"Child": "Lumi Door", "DeviceType": "End Device", "Father": "Led LKex", "_lnkqty": 211}, 
            {"Child": "Wiser Thermostat", "DeviceType": "End Device", "Father": "Led LKex", "_lnkqty": 223}, 
            {"Child": "Led Ikea", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 60}, 
            {"Child": "Led Ikea", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 101}, 
            {"Child": "Remote Tradfri", "DeviceType": "End Device", "Father": "Led Ikea", "_lnkqty": 194}, 
            {"Child": "Inter Shutter Legrand", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 133},
            {"Child": "Inter Shutter Legrand", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 241}, 
            {"Child": "Inter Shutter Legrand", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 164}, 
            {"Child": "Lumi Motion", "DeviceType": "End Device", "Father": "Inter Shutter Legrand", "_lnkqty": 242},
            {"Child": "Inter Dimmer Legrand", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 254}, 
            {"Child": "Inter Dimmer Legrand", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 215}, 
            {"Child": "Inter Dimmer Legrand", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 254}, 
            {"Child": "Micromodule Legrand", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 252}, 
            {"Child": "Micromodule Legrand", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 252}, 
            {"Child": "Micromodule Legrand", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 252}]


def rest_netTopologie(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _pluginDReports = Path( self.pluginconf.pluginConf["pluginReports"] )
    _filename = _pluginDReports / ("NetworkTopology-v3-%02d.json" % self.hardwareID)
    
    if verb == "DELETE":
        return rest_netTopologie_delete(self, verb, data, parameters, _response, _filename)

    if verb == "GET":
        return rest_netTopologie_get(self, verb, data, parameters, _response, _filename)

    return _response


def rest_netTopologie_delete(self, verb, data, parameters, _response, _filename):
    
    if len(parameters) == 0:
        if self.pluginconf.pluginConf["ZigpyTopologyReport"]:
            # Zigpy Topology
            save_report_to_file_after_deletion(self, [])

        elif not self.pluginconf.pluginConf["TopologyV2"]:
            os.remove(_filename)

        action = {"Name": "File-Removed", "FileName": _filename}
        _response["Data"] = json.dumps(action, sort_keys=True)

    elif len(parameters) == 1:
        timestamp = parameters[0]
        if self.pluginconf.pluginConf["ZigpyTopologyReport"]:
            # Zigpy Topology
            save_report_to_file_after_deletion(self, remove_specific_entry(self, timestamp, read_zigpy_topology_report(self)))
            
        elif self.pluginconf.pluginConf["TopologyV2"] and len(self.ControllerData):
            remove_entry_from_all_tables( self, timestamp )

        else:
            _topo, _timestamps_lst = extract_list_of_legacy_report(self, _response, _filename)
            if timestamp in _topo:
                return rest_netTopologie_delete_legacy(self, verb, data, parameters, _response, timestamp, _topo, _filename)

        action = {"Name": "Report %s removed" % timestamp}
        _response["Data"] = json.dumps(action, sort_keys=True)  
    return _response


def rest_netTopologie_get(self, verb, data, parameters, _response, _filename, ):
    if len(parameters) == 0:
        # Send list of Time Stamps
        if self.fake_mode():
            _timestamps_lst = [1643561599, 1643564628]
        
        elif self.pluginconf.pluginConf["ZigpyTopologyReport"]:
            # Zigpy Report
            _timestamps_lst = return_time_stamps_list(self, read_zigpy_topology_report(self))
            
        elif self.pluginconf.pluginConf["TopologyV2"]:
            _timestamps_lst = get_list_of_timestamps( self, "0000", "Neighbours")
            
        else:
            _topo, _timestamps_lst = extract_list_of_legacy_report(self, _response, _filename)

        _response["Data"] = json.dumps(_timestamps_lst, sort_keys=True)

    elif len(parameters) == 1:

        if self.fake_mode():
            _response["Data"] = json.dumps(dummy_topology_report( ), sort_keys=True)
            
        elif self.pluginconf.pluginConf["ZigpyTopologyReport"]:
            timestamp = parameters[0]
            _response["Data"] = json.dumps(normalized_one_report_for_webui(self, timestamp, read_zigpy_topology_report(self)))
            
        elif self.pluginconf.pluginConf["TopologyV2"]:
            timestamp = parameters[0]
            _response["Data"] = json.dumps(collect_routing_table(self,timestamp ), sort_keys=True)

        else:
            timestamp = parameters[0]
            _topo, _timestamps_lst = extract_list_of_legacy_report(self, _response, _filename)
            if timestamp in _topo:
                self.logging("Debug", "Topology sent: %s" % _topo[timestamp])
                _response["Data"] = json.dumps(_topo[timestamp], sort_keys=True)
            else:
                _response["Data"] = json.dumps([], sort_keys=True)
    return _response


def rest_netTopologie_delete_legacy(self, verb, data, parameters, _response, timestamp, _topo, _filename):
    self.logging("Debug", "Removing Report: %s from %s records" % (timestamp, len(_topo)))
    with open(_filename, "r+") as handle:
        d = handle.readlines()
        handle.seek(0)
        for line in d:
            if line[0] != "{" and line[-1] != "}":
                handle.write(line)
                continue
            entry = json.loads(line)
            entry_ts = entry.keys()
            if len(entry_ts) != 1:
                continue
            if timestamp in entry_ts:
                self.logging("Debug", "--------> Skiping %s" % timestamp)
                continue
            handle.write(line)
        handle.truncate()

    action = {"Name": "Report %s removed" % timestamp}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def extract_list_of_legacy_report(self, _response, _filename):
    self.logging("Debug", "Filename: %s" % _filename)

    if not os.path.isfile(_filename):
        _response["Data"] = json.dumps({}, sort_keys=True)
        self.logging("Debug", "Filename: %s not found !!" % _filename)
        return _response

    # Read the file, as we have anyway to do it
    _topo = {}  # All Topo reports
    _timestamps_lst = []  # Just the list of Timestamps
    with open(_filename, "rt") as handle:
        for line in handle:
            if line[0] != "{" and line[-1] != "}":
                continue
            entry = json.loads(line)
            for _ts in entry:
                _timestamps_lst.append(int(_ts))
                _topo[_ts] = []  # List of Father -> Child relation for one TimeStamp
                reportLQI = entry[_ts]
                _topo[_ts] = extract_legacy_report(self, reportLQI)
    return _topo, _timestamps_lst

    
#def extract_legacy_report(self, reportLQI):
#    _check_duplicate = []  # List of tuble ( item, x) to prevent adding twice the same relation
#
#    _topo = []  # Use to store the list to be send to the Browser
#
#    self.logging("Debug", "RAW report" )
#    for item in reportLQI:
#        for x in reportLQI[item]["Neighbours"]:
#            self.logging("Debug", "%s - %s - %s - %s - %s - %s" %(
#                get_node_name( self, item),
#                reportLQI[item]["Neighbours"][x]["_relationshp"],
#                get_node_name( self, x),
#                reportLQI[item]["Neighbours"][x]["_devicetype"],
#                reportLQI[item]["Neighbours"][x]["_lnkqty"],
#                reportLQI[item]["Neighbours"][x]["_relationshp"]
#            ))
#
#    for node1 in reportLQI:
#        if node1 != "0000" and node1 not in self.ListOfDevices:
#            # We remove nodes which are unknown
#            continue
#
#        # Get the Nickname
#        node1_name = get_node_name( self, item)
#
#        self.logging("Debug", "extract_report - found item: %s - %s" %(node1, node1_name))
#
#        # Let browse the neighbours
#        for node2 in list(reportLQI[node1]["Neighbours"]):
#            # Check it exists
#            if (node1 == node2) or (node2 != "0000" and node2 not in self.ListOfDevices):
#                # We remove nodes which are unknown
#                continue
#
#            # Get nickname
#            node2_name = get_node_name( self, node2)
#
#            if "Neighbours" not in reportLQI[node1]:
#                self.logging("Error", "Missing attribute :%s for (%s,%s)" % ("Neighbours", node1, node2))
#                continue
#
#            for attribute in ( "_relationshp", "_lnkqty", "_devicetype", ):
#                if attribute not in reportLQI[node1]["Neighbours"][node2]:
#                    self.logging("Error", "Missing attribute :%s for (%s,%s)" % (attribute, node1, node2))
#                    continue
#
#            if reportLQI[node1]["Neighbours"][node2]["_relationshp"] in ("Former Child", "None"):
#                continue
#
#            if ( node1, node2) in _check_duplicate or ( node2, node1) in _check_duplicate:
#                self.logging( "Debug", "Skip (%s,%s) as there is already %s" % ( node1, x, str(_check_duplicate)))
#                continue
#
#            _check_duplicate.append(( node1, node2))
#
#            # Build the relation for the graph
#            _relation = {
#                "Father": node1_name,
#                "Child": node2_name,
#                "_lnkqty": int(
#                    reportLQI[item]["Neighbours"][x]["_lnkqty"], 16
#                ),
#                "DeviceType": reportLQI[node1]["Neighbours"][x]["_devicetype"],
#
#            }
#            self.logging( "Debug", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
#                _relation["Father"], node1, _relation["Child"], node2, _relation["_lnkqty"], _relation["DeviceType"]),)
#            _topo.append(_relation)
#
#    self.logging("Debug", "WebUI report" )
#
#    for x in _topo:
#        self.logging( "Debug", "Relationship - %15.15s - %15.15s %3s %s" % (
#            x["Father"], x["Child"], x["_lnkqty"], x["DeviceType"]),)
#
#    del _check_duplicate
#
#    return _topo

def extract_legacy_report(self, reportLQI):
    _check_duplicate = []  # List of tuple (item, x) to prevent adding twice the same relation
    _topo = []  # Use to store the list to be sent to the Browser

    self.logging("Debug", "RAW report")
    for item, neighbours_info in reportLQI.items():
        for x, neighbour_info in neighbours_info.get("Neighbours", {}).items():
            self.logging("Debug", "%s - %s - %s - %s - %s - %s" % (
                get_node_name(self, item),
                neighbour_info.get("_relationshp", "Unknown"),
                get_node_name(self, x),
                neighbour_info.get("_devicetype", "Unknown"),
                neighbour_info.get("_lnkqty", "Unknown"),
                neighbour_info.get("_relationshp", "Unknown")
            ))

    for node1, neighbours_info in reportLQI.items():
        if node1 != "0000" and node1 not in self.ListOfDevices:
            # We remove nodes which are unknown
            continue

        # Get the Nickname for node1
        node1_name = get_node_name(self, node1)

        self.logging("Debug", "extract_report - found item: %s - %s" % (node1, node1_name))

        neighbours = neighbours_info.get("Neighbours", {})
        for node2, neighbour_info in neighbours.items():
            if (node1 == node2) or (node2 != "0000" and node2 not in self.ListOfDevices):
                # We remove nodes which are unknown
                continue

            # Get nickname
            node2_name = get_node_name(self, node2)

            required_attributes = ["_relationshp", "_lnkqty", "_devicetype"]
            if any(attr not in neighbour_info for attr in required_attributes):
                for attr in required_attributes:
                    if attr not in neighbour_info:
                        self.logging("Error", "Missing attribute: %s for (%s, %s)" % (attr, node1, node2))
                continue

            relationshp = neighbour_info["_relationshp"]
            if relationshp in ("Former Child", "None"):
                continue

            if (node1, node2) in _check_duplicate or (node2, node1) in _check_duplicate:
                self.logging("Debug", "Skip (%s,%s) as there is already %s" % (node1, x, str(_check_duplicate)))
                continue

            _check_duplicate.append((node1, node2))

            # Build the relation for the graph
            _relation = {
                "Father": node1_name,
                "Child": node2_name,
                "_lnkqty": int(neighbour_info.get("_lnkqty", "0"), 16),
                "DeviceType": neighbour_info.get("_devicetype", "Unknown"),
            }

            self.logging("Debug", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
                _relation["Father"], node1, _relation["Child"], node2, _relation["_lnkqty"], _relation["DeviceType"]))
            _topo.append(_relation)

    self.logging("Debug", "WebUI report")

    for x in _topo:
        self.logging("Debug", "Relationship - %15.15s - %15.15s %3s %s" % (
            x["Father"], x["Child"], x["_lnkqty"], x["DeviceType"]))

    return _topo

def get_device_type( self, node):
    if node not in self.ListOfDevices:
        return '??'
    if "LogicalType" not in self.ListOfDevices[ node ]:
        return '??'
    return self.ListOfDevices[ node ]["LogicalType"]


def get_node_name( self, node):
    if node == "0000":
        return "Zigbee Coordinator"
    if node not in self.ListOfDevices:
        return node
    if "ZDeviceName" in self.ListOfDevices[node] and self.ListOfDevices[node]["ZDeviceName"] not in ( "",{}):
            return self.ListOfDevices[node]["ZDeviceName"]
    return node

def check_sibbling(self, reportLQI):
    # for node1 in sorted(reportLQI):
    #    for node2 in list(reportLQI[node1]['Neighbours']):
    #        domoticz_log_api("%s %s %s" %(node1, node2,reportLQI[node1]['Neighbours'][node2]['_relationshp'] ))

    for node1 in list(reportLQI):
        for node2 in list(reportLQI[node1]["Neighbours"]):
            if reportLQI[node1]["Neighbours"][node2]["_relationshp"] != "Sibling":
                continue

            # domoticz_log_api("Search parent for sibling %s and %s" %(node1, node2))
            parent1 = find_parent_for_node(reportLQI, node2)
            parent2 = find_parent_for_node(reportLQI, node1)
            # domoticz_log_api("--parents found: %s + %s" %(parent1,parent2))

            if len(parent1) !=0 and len(parent2) == 0:
                continue

            for x in parent1:
                reportLQI = add_relationship(
                    self, reportLQI, node1, node2, x, "Parent", reportLQI[node1]["Neighbours"][node2]["_lnkqty"]
                )
                reportLQI = add_relationship(
                    self, reportLQI, node2, node1, x, "Parent", reportLQI[node1]["Neighbours"][node2]["_lnkqty"]
                )
            for x in parent2:
                reportLQI = add_relationship(
                    self, reportLQI, node1, node2, x, "Parent", reportLQI[node1]["Neighbours"][node2]["_lnkqty"]
                )
                reportLQI = add_relationship(
                    self, reportLQI, node2, node1, x, "Parent", reportLQI[node1]["Neighbours"][node2]["_lnkqty"]
                )

    # for node1 in sorted(reportLQI):
    #    for node2 in list(reportLQI[node1]['Neighbours']):
    #        domoticz_log_api("%s %s %s" %(node1, node2,reportLQI[node1]['Neighbours'][node2]['_relationshp'] ))

    return reportLQI


def find_parent_for_node(reportLQI, node):

    parent = []
    if node not in reportLQI:
        return parent

    if "Neighbours" not in reportLQI[node]:
        return parent

    for y in list(reportLQI[node]["Neighbours"]):
        if reportLQI[node]["Neighbours"][y]["_relationshp"] == "Parent" and y not in parent:
            parent.append(y)

    for x in list(reportLQI):
        if node in reportLQI[x]["Neighbours"] and reportLQI[x]["Neighbours"][node]["_relationshp"] == "Child" and x not in parent:
            parent.append(x)

    return parent


def add_relationship(self, reportLQI, node1, node2, relation_node, relation_ship, _linkqty):

    if node1 == relation_node:
        return reportLQI

    if node1 not in reportLQI:
        reportLQI[node1] = {"Neighbours": {}}
    if (
        relation_node in reportLQI[node1]["Neighbours"]
        and reportLQI[node1]["Neighbours"][relation_node]["_relationshp"] == relation_ship
    ):
        return reportLQI

    if relation_node == "0000":
        # ZiGate
        _devicetype = "Coordinator"

    elif node2 in reportLQI[node1]["Neighbours"]:
        _devicetype = (
            reportLQI[node1]["Neighbours"][node2]["_devicetype"]
            if "_devicetype" in reportLQI[node1]["Neighbours"][node2]
            else find_device_type(self, node2)
        )
    else:
        _devicetype = find_device_type(self, node2)

    reportLQI[node1]["Neighbours"][relation_node] = {
        "_relationshp": relation_ship,
        "_lnkqty": _linkqty,
        "_devicetype": _devicetype,
    }
    return reportLQI


def find_device_type(self, node):

    if node not in self.ListOfDevices:
        return None
    if "LogicalType" in self.ListOfDevices[node]:
        return self.ListOfDevices[node]["LogicalType"]
    if "DeviceType" in self.ListOfDevices[node]:
        if self.ListOfDevices[node]["DeviceType"] == "FFD":
            return "Router"
        if self.ListOfDevices[node]["DeviceType"] == "RFD":
            return "End Device"
    return None


def collect_routing_table(self, time_stamp=None):
    
    self.logging( "Log", "Relationships (Neighbours table)")
    self.logging( "Log", "| %15.15s (%5.5s) | %15.15s (%5.5s) | %4.4s | %11.11s | %9.9s | %5.5s |" % (
        "Node1", "nwkid", "Node2", "nwkid", "LQI", "Dev. Type", "Relation", "Route Flag"),)

    _topo = []
    prevent_duplicate_tuple = []
    self.logging( "Debug", "collect_routing_table - TimeStamp: %s" %time_stamp)
    for node1 in self.ListOfDevices:
        self.logging( "Debug", f"check {node1} child from routing table")

        routes_list = extract_routes(self, node1, time_stamp)
        for node2 in set( collect_neighbours_devices( self, node1, time_stamp) ):
            self.logging( "Debug", f"Found child {node2}") 
            if node2 not in self.ListOfDevices:
                self.logging( "Debug", f"Found child {node2} but not found in ListOfDevices") 
                continue
            

            if ( node1, node2) not in prevent_duplicate_tuple:
                prevent_duplicate_tuple.append( ( node1, node2) )
                new_entry = build_relation_ship_dict(self, node1, node2,)

                if node2 in routes_list:
                    new_entry["Route"] = "Yes"
                    
                self.logging( "Log", "| %15.15s (%5.5s) | %15.15s (%5.5s) | %4.4s | %11.11s | %9.9s | %5.5s |" % (
                    new_entry["Father"], node1, new_entry["Child"], node2, new_entry["_lnkqty"], new_entry["DeviceType"], new_entry["_relationship"], new_entry["Route"]),)
                del new_entry["Route"]
                del new_entry["_relationship"]
                _topo.append( new_entry ) 

    return _topo


def build_relation_ship_dict(self, node1, node2):
    return {
        "Father": get_node_name( self, node1), 
        "Child": get_node_name( self, node2), 
        "_lnkqty": get_lqi_from_neighbours(self, node1, node2), 
        "DeviceType": find_device_type(self, node2),
        "_relationship": get_relationship_neighbours(self, node1, node2),
        "Route": ""
    }


def get_relationship_neighbours(self, node1, node2, time_stamp=None):
    return next(
        (
            neigbor[node2]["_relationshp"]
            for neigbor in get_device_table_entry(
                self, node1, "Neighbours", time_stamp
            )
            if node2 in neigbor
        ),
        "",
    )


def collect_associated_devices( self, node, time_stamp=None):
    last_associated_devices = get_device_table_entry(self, node, "AssociatedDevices", time_stamp)
    self.logging( "Debug", "collect_associated_devices %s -> %s" %(node, str(last_associated_devices)))
    return list(last_associated_devices)


def collect_neighbours_devices( self, node, time_stamp=None):
    last_neighbours_devices = get_device_table_entry(self, node, "Neighbours", time_stamp)
    self.logging( "Debug", "collect_neighbours_devices %s -> %s" %(node, str(last_neighbours_devices)))
    keys_with_child_relation = [key for item in last_neighbours_devices for key, value in item.items()]
    return list(keys_with_child_relation)
    
        
def extract_routes( self, node, time_stamp=None):
    node_routes = []
    for route in get_device_table_entry(self, node, "RoutingTable", time_stamp):
        self.logging( "Debug","---> route: %s" %route)
        node_routes.extend(item for item in route if route[item]["Status"] == "Active (0)")
    return node_routes            
        

def get_lqi_from_neighbours(self, father, child, time_stamp=None):
    # Take the LQI from the latest report
    for item2 in get_device_table_entry(self, father, "Neighbours", time_stamp):
        for node in item2:
            if node != child:
                continue
            return item2[ node ]["_lnkqty"] 
    return 1


# Zigpy Topology helpers
def zigpy_topology_filename(self):
    return Path( self.pluginconf.pluginConf["pluginReports"] ) / ( ZIGPY_TOPOLOGY_REPORT_FILENAME + "%02d.json" % self.hardwareID)


def read_zigpy_topology_report(self):
    """ open the Zigpy Topology Report and return a list of entries (timestamps)"""

    self.logging( "Debug", "read_zigpy_topology_report")
    zigpy_topology_reports_filename = zigpy_topology_filename(self)
    if not os.path.isdir( Path(self.pluginconf.pluginConf["pluginReports"]) ):
        self.logging( "Error", "read_zigpy_topology_report: Unable to get access to directory %s, please check PluginConf.json" % (self.pluginconf.pluginConf["pluginReports"]), )
        return

    if os.path.exists(zigpy_topology_reports_filename):
        with open(zigpy_topology_reports_filename, 'r') as file:
            data = json.load(file)
        return data
    else:
        return []


def save_report_to_file_after_deletion(self, report):
    """ Save a new version of the report (after deletion of one entry)"""
    self.logging("Debug", "save_report_to_file_after_deletion")
    zigpy_topology_reports_filename = zigpy_topology_filename(self)
    if not os.path.isdir( Path(self.pluginconf.pluginConf["pluginReports"]) ):
        self.logging( "Error", "save_report_to_file_after_deletion: Unable to get access to directory %s, please check PluginConf.json" % (self.pluginconf.pluginConf["pluginReports"]), )
        return

    with open(zigpy_topology_reports_filename, 'w') as file:
        json.dump(report, file, indent=4)

    
def return_time_stamps_list(self, zigpy_report_list):
    """ return list of timestamps"""
    return [list(entry.keys())[0] for entry in zigpy_report_list]


def remove_specific_entry(self, timestatmp_to_remove, zigpy_report_list):
    """ remove one specific entry based on timestamp and return the new report list"""
    return [entry for entry in zigpy_report_list if list(entry.keys())[0] != timestatmp_to_remove]


def normalize_device_type(self, device_type):

    if device_type == "end_device":
        return "End Device"
    if device_type == "coordinator":
        return "Coordinator"
    return "Router" if device_type == "router" else None


def normalized_one_report_for_webui(self, timestamp, zigpy_report_list):
    self.logging("Debug", "normalized_one_report_for_webui %s (%s)" %(timestamp, type(timestamp)))

    target_report = next( ( entry for entry in zigpy_report_list if list(entry.keys())[0] == timestamp ), None, )
    neighbors = target_report[ timestamp ].get( "Neighbors",{})
    route = target_report[ timestamp ].get( "Routes",{})
    topology = []
    for node1_nwkid in neighbors:
        self.logging("Debug", "   neighbors %s" %node1_nwkid)
        if node1_nwkid not in self.ListOfDevices:
            self.logging( "Debug", f"Found child {node1_nwkid} but not found in ListOfDevices") 
            continue

        for neigbor_node2 in neighbors[ node1_nwkid]["relationship"]:
            node2_nwkid = neigbor_node2["nwkid"]
            node2_device_type = neigbor_node2["device_type"]
            node2_lqi = neigbor_node2["lqi_from_device"]

            if node2_nwkid not in self.ListOfDevices:
                self.logging( "Log", f"Found child {node2_nwkid} but not found in ListOfDevices") 
                continue

            relation = {
                "Child": get_node_name( self, node2_nwkid),
                "DeviceType": normalize_device_type(self, node2_device_type),
                "Father": get_node_name( self, node1_nwkid), 
                "_lnkqty": node2_lqi,
                }
            self.logging( "Debug", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
                relation["Father"], node1_nwkid, relation["Child"], node2_nwkid, relation["_lnkqty"], relation["DeviceType"]),)

            if relation not in topology:
                topology.append( relation )

    return topology
