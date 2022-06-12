#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import json
import os
import os.path
from time import time

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage, setupHeadersResponse)
from Modules.zb_tables_management import get_device_table_entry, get_list_of_timestamps, remove_entry_from_all_tables


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
        _filename = self.pluginconf.pluginConf["pluginReports"] + "NetworkTopology-v3-" + "%02d" % self.hardwareID + ".json"
        self.logging("Debug", "Filename: %s" % _filename)

        if not os.path.isfile(_filename):
            _response["Data"] = json.dumps({}, sort_keys=True)
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
                    _topo[_ts] = extract_report(self, reportLQI)

    if verb == "DELETE":
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
                
            else:
                Domoticz.Error("Removing Topo Report %s not found" % timestamp)
                _response["Data"] = json.dumps([], sort_keys=True)
        return _response

    if verb == "GET":
        if len(parameters) == 0:
            # Send list of Time Stamps
            if len(self.ControllerData) == 0:
                _timestamps_lst = [1643561599, 1643564628]
                
            elif self.pluginconf.pluginConf["TopologyV2"]:
                _timestamps_lst = get_list_of_timestamps( self, "0000", "Neighbours")

            _response["Data"] = json.dumps(_timestamps_lst, sort_keys=True)

        elif len(parameters) == 1:
            if self.pluginconf.pluginConf["TopologyV2"] and len(self.ControllerData):
                timestamp = parameters[0]
                _response["Data"] = json.dumps(collect_routing_table(self,timestamp ), sort_keys=True)

            elif len(self.ControllerData) == 0:
                _response["Data"] = json.dumps(dummy_topology_report( ), sort_keys=True)
            else:
                timestamp = parameters[0]
                if timestamp in _topo:
                    self.logging("Debug", "Topologie sent: %s" % _topo[timestamp])
                    _response["Data"] = json.dumps(_topo[timestamp], sort_keys=True)
                else:
                    _response["Data"] = json.dumps([], sort_keys=True)

    return _response


def is_sibling_required(reportLQI):
    # Do We have a relationship between 2 nodes, but it is not a Parent/Child,
    # let's enable Sibling check to get it.
    for x in reportLQI:
        for y in reportLQI[x]["Neighbours"]:
            if reportLQI[x]["Neighbours"][y]["_relationshp"] == "None":
                return True
    return False


def extract_report(self, reportLQI):
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

    if is_sibling_required(reportLQI) or self.pluginconf.pluginConf["Sibling"]:
        reportLQI = check_sibbling(self, reportLQI)

    self.logging("Debug", "AFTER Sibling report" )
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

    for item in reportLQI:
        
        if item != "0000" and item not in self.ListOfDevices:
            continue

        # Get the Nickname
        item_name = get_node_name( self, item)

        self.logging("Debug", "extract_report - found item: %s - %s" %(item, item_name))

        # Let browse the neighbours
        for x in reportLQI[item]["Neighbours"]:
            # Check it exists
            if x != "0000" and x not in self.ListOfDevices:
                continue

            # Check it is not the main item
            if item == x:
                continue

            # Get nickname
            x_name = get_node_name( self, x)

            self.logging("Debug2", "                     ---> %15s (%s) %s %s %s" % (
                x_name, x, 
                reportLQI[item]["Neighbours"][x]["_relationshp"],
                reportLQI[item]["Neighbours"][x]["_devicetype"],
                int(reportLQI[item]["Neighbours"][x]["_lnkqty"], 16) ))

            # Report only Child relationship
            if "Neighbours" not in reportLQI[item]:
                self.logging("Error", "Missing attribute :%s for (%s,%s)" % ("Neighbours", item, x))
                continue

            for attribute in ( "_relationshp", "_lnkqty", "_devicetype", ):
                if attribute not in reportLQI[item]["Neighbours"][x]:
                    self.logging("Error", "Missing attribute :%s for (%s,%s)" % (attribute, item, x))
                    continue

            # We need to reorganise in Father/Child relationship.
            if reportLQI[item]["Neighbours"][x]["_relationshp"] in ("Former Child", "None", "Sibling"):
                continue

            if reportLQI[item]["Neighbours"][x]["_relationshp"] == "Parent":
                _father = item
                _father_name = item_name
                _child = x
                _devicetype = get_device_type(self, x)
                _child_name = x_name

            elif reportLQI[item]["Neighbours"][x]["_relationshp"] == "Child":
                _father = x
                _father_name = x_name
                _child = item
                _devicetype = get_device_type(self, item)
                _child_name = item_name

            if ( _father, _child) in _check_duplicate or ( _child, _father) in _check_duplicate:
                self.logging( "Debug", "Skip (%s,%s) as there is already %s" % ( item, x, str(_check_duplicate)))
                continue
            
            _check_duplicate.append(( _father, _child))

            # Build the relation for the graph
            _relation = {}
            _relation["Father"] = _father_name
            _relation["Child"] = _child_name
            _relation["_lnkqty"] = int(reportLQI[item]["Neighbours"][x]["_lnkqty"], 16)
            _relation["DeviceType"] = _devicetype
            
            self.logging( "Debug", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
                _relation["Father"], _father, _relation["Child"], _child, _relation["_lnkqty"], _relation["DeviceType"]),)
            _topo.append(_relation)
            
    self.logging("Debug", "WebUI report" )
    for x in _topo:
        self.logging( "Debug", "Relationship - %15.15s - %15.15s %3s %s" % (
            x["Father"], x["Child"], x["_lnkqty"], x["DeviceType"]),)
 
    del _check_duplicate
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
    #        Domoticz.Log("%s %s %s" %(node1, node2,reportLQI[node1]['Neighbours'][node2]['_relationshp'] ))

    for node1 in list(reportLQI):
        for node2 in list(reportLQI[node1]["Neighbours"]):
            if reportLQI[node1]["Neighbours"][node2]["_relationshp"] != "Sibling":
                continue

            # Domoticz.Log("Search parent for sibling %s and %s" %(node1, node2))
            parent1 = find_parent_for_node(reportLQI, node2)
            parent2 = find_parent_for_node(reportLQI, node1)
            # Domoticz.Log("--parents found: %s + %s" %(parent1,parent2))

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
    #        Domoticz.Log("%s %s %s" %(node1, node2,reportLQI[node1]['Neighbours'][node2]['_relationshp'] ))

    return reportLQI


def find_parent_for_node(reportLQI, node):

    parent = []
    if node not in reportLQI:
        return parent

    if "Neighbours" not in reportLQI[node]:
        return parent

    for y in list(reportLQI[node]["Neighbours"]):
        if reportLQI[node]["Neighbours"][y]["_relationshp"] == "Parent":
            # Domoticz.Log("-- -- find %s Parent for %s" %(y, node))
            if y not in parent:
                parent.append(y)

    for x in list(reportLQI):
        if node in reportLQI[x]["Neighbours"]:
            if reportLQI[x]["Neighbours"][node]["_relationshp"] == "Child":
                # Domoticz.Log("-- -- find %s Child for %s" %(y, node))
                if x not in parent:
                    parent.append(x)

    return parent


def add_relationship(self, reportLQI, node1, node2, relation_node, relation_ship, _linkqty):

    if node1 == relation_node:
        return reportLQI

    if node1 not in reportLQI:
        reportLQI[node1] = {}
        reportLQI[node1]["Neighbours"] = {}

    if (
        relation_node in reportLQI[node1]["Neighbours"]
        and reportLQI[node1]["Neighbours"][relation_node]["_relationshp"] == relation_ship
    ):
        return reportLQI

    if relation_node == "0000":
        # ZiGate
        _devicetype = "Coordinator"

    else:
        if node2 in reportLQI[node1]["Neighbours"]:
            if "_devicetype" in reportLQI[node1]["Neighbours"][node2]:
                _devicetype = reportLQI[node1]["Neighbours"][node2]["_devicetype"]
            else:
                _devicetype = find_device_type(self, node2)
        else:
            _devicetype = find_device_type(self, node2)

    reportLQI[node1]["Neighbours"][relation_node] = {}
    reportLQI[node1]["Neighbours"][relation_node]["_relationshp"] = relation_ship
    reportLQI[node1]["Neighbours"][relation_node]["_lnkqty"] = _linkqty
    reportLQI[node1]["Neighbours"][relation_node]["_devicetype"] = _devicetype

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
    
    _topo = []
    self.logging( "Debug", "collect_routing_table - TimeStamp: %s" %time_stamp)
    for father in self.ListOfDevices:
        for child in extract_routes(self, father, time_stamp):
            if child not in self.ListOfDevices:
                continue
            _relation = {
                "Father": get_node_name( self, father), 
                "Child": get_node_name( self, child), 
                "_lnkqty": get_lqi_from_neighbours(self, father, child), 
                "DeviceType": find_device_type(self, child)
                }
            self.logging( "Log", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
                _relation["Father"], father, _relation["Child"], child, _relation["_lnkqty"], _relation["DeviceType"]),)
            _topo.append( _relation ) 
            
        for child in collect_associated_devices( self, father, time_stamp):
            if child not in self.ListOfDevices:
                continue
            _relation = {
                "Father": get_node_name( self, father), 
                "Child": get_node_name( self, child), 
                "_lnkqty": get_lqi_from_neighbours(self, father, child), 
                "DeviceType": find_device_type(self, child)
                }
            self.logging( "Debug", "Relationship - %15.15s (%s) - %15.15s (%s) %3s %s" % (
                _relation["Father"], father, _relation["Child"], child, _relation["_lnkqty"], _relation["DeviceType"]),)
            if _relation not in _topo:
                _topo.append( _relation )
    return _topo

       
def collect_associated_devices( self, node, time_stamp=None):
    last_associated_devices = get_device_table_entry(self, node, "AssociatedDevices", time_stamp)
    self.logging( "Debug", "collect_associated_devices %s -> %s" %(node, str(last_associated_devices)))
    return list(last_associated_devices)
        
        
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