#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import json
import os
import os.path
from pathlib import Path
from time import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)
from Modules.zb_tables_management import (get_device_table_entry,
                                          get_list_of_timestamps,
                                          remove_entry_from_all_tables)


def rest_req_topologie(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb == "GET":
        action = {"Name": "Req-Topology", "TimeStamp": int(time())}
        _response["Data"] = json.dumps(action, sort_keys=True)

        self.logging("Status", "Request a Start of Network Topology scan")
        if self.networkmap:
            if not self.networkmap.NetworkMapPhase():
                self.networkmap.start_scan()
            else:
                self.logging("Error", "Cannot start Network Topology as one is in progress...")

    return _response


def dummy_topology_report( ):
    
    return [{"Child": "IAS Sirene", "DeviceType": "Router", "Father": "Zigbee Coordinator", "_lnkqty": 58}, {"Child": "IAS Sirene", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 252}, {"Child": "IAS Sirene", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 241}, {"Child": "OnOff Ikea", "DeviceType": "End Device", "Father": "IAS Sirene", "_lnkqty": 255}, {"Child": "Repeater", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 254}, {"Child": "Repeater", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 196}, {"Child": "Repeater", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 254}, {"Child": "Motion frient", "DeviceType": "End Device", "Father": "Repeater", "_lnkqty": 168}, {"Child": "Dim Ikea", "DeviceType": "End Device", "Father": "Repeater", "_lnkqty": 89}, {"Child": "Led LKex", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 254}, {"Child": "Led LKex", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 244}, {"Child": "Lumi Door", "DeviceType": "End Device", "Father": "Led LKex", "_lnkqty": 211}, {"Child": "Wiser Thermostat", "DeviceType": "End Device", "Father": "Led LKex", "_lnkqty": 223}, {"Child": "Led Ikea", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 60}, {"Child": "Led Ikea", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 101}, {"Child": "Remote Tradfri", "DeviceType": "End Device", "Father": "Led Ikea", "_lnkqty": 194}, {"Child": "Inter Shutter Legrand", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 133}, {"Child": "Inter Shutter Legrand", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 241}, {"Child": "Inter Shutter Legrand", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 164}, {"Child": "Lumi Motion", "DeviceType": "End Device", "Father": "Inter Shutter Legrand", "_lnkqty": 242}, {"Child": "Inter Dimmer Legrand", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 254}, {"Child": "Inter Dimmer Legrand", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 215}, {"Child": "Inter Dimmer Legrand", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 254}, {"Child": "Micromodule Legrand", "DeviceType": "Coordinator", "Father": "Zigbee Coordinator", "_lnkqty": 252}, {"Child": "Micromodule Legrand", "DeviceType": "Router", "Father": "Led LKex", "_lnkqty": 252}, {"Child": "Micromodule Legrand", "DeviceType": "Router", "Father": "Led Ikea", "_lnkqty": 252}]


def rest_netTopologie(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if not self.pluginconf.pluginConf["TopologyV2"]:
        _pluginDReports = Path( self.pluginconf.pluginConf["pluginReports"] )
        _filename = _pluginDReports / ("NetworkTopology-v3-%02d.json" % self.hardwareID)

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

    if verb == "DELETE":
        return rest_netTopologie_delete(self, verb, data, parameters, _response, _topo, _filename)

    if verb == "GET":
        if not self.pluginconf.pluginConf["TopologyV2"]:
            return rest_netTopologie_get(self, verb, data, parameters, _response, _topo)
        return rest_netTopologie_get(self, verb, data, parameters, _response)


def rest_netTopologie_delete(self, verb, data, parameters, _response, _topo, _filename):
    if len(parameters) == 0:
        os.remove(_filename)
        action = {"Name": "File-Removed", "FileName": _filename}
        _response["Data"] = json.dumps(action, sort_keys=True)

    elif len(parameters) == 1:
        timestamp = parameters[0]
        if self.pluginconf.pluginConf["TopologyV2"] and len(self.ControllerData):
            remove_entry_from_all_tables( self, timestamp )
            action = {"Name": "Report %s removed" % timestamp}
            _response["Data"] = json.dumps(action, sort_keys=True)

        elif timestamp in _topo:
            return rest_netTopologie_delete_legacy(self, verb, data, parameters, _response, timestamp, _topo, _filename)
            
        else:
            domoticz_error_api("Removing Topo Report %s not found" % timestamp)
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
    
    
def rest_netTopologie_get(self, verb, data, parameters, _response, _topo=None):
    if len(parameters) == 0:
        if self.fake_mode():
            _timestamps_lst = [1643561599, 1643564628]
        elif self.pluginconf.pluginConf["TopologyV2"]:
            _timestamps_lst = get_list_of_timestamps(self, "0000", "Neighbours")
        _response["Data"] = json.dumps(_timestamps_lst, sort_keys=True)

    elif len(parameters) == 1:
        if self.fake_mode():
            _response["Data"] = json.dumps(dummy_topology_report(), sort_keys=True)

        elif self.pluginconf.pluginConf["TopologyV2"]:
            timestamp = parameters[0]
            _response["Data"] = json.dumps(collect_routing_table(self, timestamp), sort_keys=True)

        elif _topo:
            timestamp = parameters[0]
            _response["Data"] = json.dumps(_topo.get(timestamp, []), sort_keys=True)

    return _response


def extract_legacy_report(self, reportLQI):
    _check_duplicate = []  # List of tuble ( item, x) to prevent adding twice the same relation

    _topo = []  # Use to store the list to be send to the Browser

    self.logging("Debug", "RAW report" )
    for item in reportLQI:
        for x in reportLQI[item]["Neighbours"]:
            self.logging("Debug", "%s - %s - %s - %s - %s - %s" %(
                get_node_name( self, item),
                reportLQI[item]["Neighbours"][x]["_relationshp"],
                get_node_name( self, x),
                reportLQI[item]["Neighbours"][x]["_devicetype"],
                reportLQI[item]["Neighbours"][x]["_lnkqty"],
                reportLQI[item]["Neighbours"][x]["_relationshp"]
            ))

    for node1 in reportLQI:
        if node1 != "0000" and node1 not in self.ListOfDevices:
            # We remove nodes which are unknown
            continue

        # Get the Nickname
        node1_name = get_node_name( self, item)

        self.logging("Debug", "extract_report - found item: %s - %s" %(node1, node1_name))

        # Let browse the neighbours
        for node2 in reportLQI[node1]["Neighbours"]:
            # Check it exists
            if (node1 == node2) or (node2 != "0000" and node2 not in self.ListOfDevices):
                # We remove nodes which are unknown
                continue

            # Get nickname
            node2_name = get_node_name( self, node2)

            self.logging("Debug2", "                     ---> %15s (%s) %s %s %s" % (
                node2_name, node2, 
                reportLQI[node1]["Neighbours"][x]["_relationshp"],
                reportLQI[node1]["Neighbours"][x]["_devicetype"],
                int(reportLQI[node1]["Neighbours"][node2]["_lnkqty"], 16) ))

            if "Neighbours" not in reportLQI[node1]:
                self.logging("Error", "Missing attribute :%s for (%s,%s)" % ("Neighbours", node1, node2))
                continue

            for attribute in ( "_relationshp", "_lnkqty", "_devicetype", ):
                if attribute not in reportLQI[node1]["Neighbours"][node2]:
                    self.logging("Error", "Missing attribute :%s for (%s,%s)" % (attribute, node1, node2))
                    continue

            if reportLQI[node1]["Neighbours"][node2]["_relationshp"] in ("Former Child", "None"):
                continue

            if ( node1, node2) in _check_duplicate or ( node2, node1) in _check_duplicate:
                self.logging( "Debug", "Skip (%s,%s) as there is already %s" % ( node1, x, str(_check_duplicate)))
                continue

            _check_duplicate.append(( node1, node2))

            # Build the relation for the graph
            _relation = {
                "Father": node1_name,
                "Child": node2_name,
                "_lnkqty": int( reportLQI[node1]["Neighbours"][node2]["_lnkqty"], 16 ),
                "_relationshp": reportLQI[node1]["Neighbours"][node2][ "_relationshp" ],
                "DeviceType": get_device_type(self, node2),
            }
            self.logging( "Debug", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
                _relation["Father"], node1, _relation["Child"], node2, _relation["_lnkqty"], _relation["DeviceType"]),)
            _topo.append(_relation)

    self.logging("Debug", "WebUI report" )
    for item in _topo:
        self.logging( "Debug", "Relationship - %15.15s - %15.15s %3s %s %s" % (
            item["Father"], item["Child"], item["_lnkqty"], item["DeviceType"], item["_relationshp"]),)

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
    
    _topo = []
    prevent_duplicate_tuple = []
    self.logging( "Debug", "collect_routing_table - TimeStamp: %s" %time_stamp)
    for node1 in self.ListOfDevices:
        self.logging( "Debug", f"check {node1} child from routing table")
        routes_list = extract_routes(self, node1, time_stamp) 
        
        for node2 in set( collect_neighbours_devices( self, node1, time_stamp) ):
            self.logging( "Debug", f"Neighbor relation {node2}") 
            if node2 not in self.ListOfDevices:
                self.logging( "Debug", f"Found relation {node2} but not found in ListOfDevices") 
                continue

            if ( node1, node2) not in prevent_duplicate_tuple:
                prevent_duplicate_tuple.append( ( node1, node2) )
                new_entry = build_relation_ship_dict(self, node1, node2,)

                if node2 in routes_list:
                    new_entry["Route"] = "Route"
                    
                self.logging( "Log", "Relationship (Neighbours) - %15.15s (%s) - %15.15s (%s) %3s %11s %5s %s" % (
                    new_entry["Father"], node1, new_entry["Child"], node2, new_entry["_lnkqty"], new_entry["DeviceType"], new_entry["_relationship"], new_entry["Route"]),)
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
        

def get_lqi_from_neighbours(self, node1, node2, time_stamp=None):
    return next(
        (
            neighbor[node2]["_lnkqty"]
            for neighbor in get_device_table_entry(
                self, node1, "Neighbours", time_stamp
            )
            if node2 in neighbor
        ),
        1,
    )

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
