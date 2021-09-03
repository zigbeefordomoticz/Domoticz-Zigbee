#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
import os
import os.path
from time import time
from datetime import datetime

from Classes.WebServer.headerResponse import setupHeadersResponse, prepResponseMessage


def rest_req_topologie(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb == "GET":
        action = {"Name": "Req-Topology", "TimeStamp": int(time())}
        _response["Data"] = json.dumps(action, sort_keys=True)

        self.logging("Log", "Request a Start of Network Topology scan")
        if self.networkmap:
            if not self.networkmap.NetworkMapPhase():
                self.networkmap.start_scan()
            else:
                self.logging("Log", "Cannot start Network Topology as one is in progress...")

    return _response


def rest_netTopologie(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

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
            action = {}
            action["Name"] = "File-Removed"
            action["FileName"] = _filename
            _response["Data"] = json.dumps(action, sort_keys=True)

        elif len(parameters) == 1:
            timestamp = parameters[0]
            if timestamp in _topo:
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
                        if len(entry_ts) == 1:
                            if timestamp in entry_ts:
                                self.logging("Debug", "--------> Skiping %s" % timestamp)
                                continue
                        else:
                            continue
                        handle.write(line)
                    handle.truncate()

                action = {}
                action["Name"] = "Report %s removed" % timestamp
                _response["Data"] = json.dumps(action, sort_keys=True)
            else:
                Domoticz.Error("Removing Topo Report %s not found" % timestamp)
                _response["Data"] = json.dumps([], sort_keys=True)
        return _response

    if verb == "GET":
        if len(parameters) == 0:
            # Send list of Time Stamps
            _response["Data"] = json.dumps(_timestamps_lst, sort_keys=True)

        elif len(parameters) == 1:
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
    _check_duplicate = []
    _nwkid_list = []
    _topo = []

    if is_sibling_required(reportLQI) or self.pluginconf.pluginConf["displaySibling"]:
        reportLQI = check_sibbling(self, reportLQI)

    for item in reportLQI:
        self.logging("Debug", "Node: %s" % item)
        if item != "0000" and item not in self.ListOfDevices:
            continue

        if item not in _nwkid_list:
            _nwkid_list.append(item)

        for x in reportLQI[item]["Neighbours"]:
            self.logging("Debug", "---> %s" % x)
            # Report only Child relationship
            if x != "0000" and x not in self.ListOfDevices:
                continue
            if item == x:
                continue
            if "Neighbours" not in reportLQI[item]:
                Domoticz.Error("Missing attribute :%s for (%s,%s)" % ("Neighbours", item, x))
                continue

            for attribute in (
                "_relationshp",
                "_lnkqty",
                "_devicetype",
            ):
                if attribute not in reportLQI[item]["Neighbours"][x]:
                    Domoticz.Error("Missing attribute :%s for (%s,%s)" % (attribute, item, x))
                    continue

            if x not in _nwkid_list:
                _nwkid_list.append(x)

            # We need to reorganise in Father/Child relationship.
            if reportLQI[item]["Neighbours"][x]["_relationshp"] in ("Former Child", "None", "Sibling"):
                continue

            if reportLQI[item]["Neighbours"][x]["_relationshp"] == "Parent":
                _father = item
                _child = x

            elif reportLQI[item]["Neighbours"][x]["_relationshp"] == "Child":
                _father = x
                _child = item

            _relation = {}
            _relation["Father"] = _father
            _relation["Child"] = _child
            _relation["_lnkqty"] = int(reportLQI[item]["Neighbours"][x]["_lnkqty"], 16)
            _relation["DeviceType"] = reportLQI[item]["Neighbours"][x]["_devicetype"]

            if _father != "0000":
                if "ZDeviceName" in self.ListOfDevices[_father]:
                    if (
                        self.ListOfDevices[_father]["ZDeviceName"] != ""
                        and self.ListOfDevices[_father]["ZDeviceName"] != {}
                    ):
                        # _relation[master] = self.ListOfDevices[_father]['ZDeviceName']
                        _relation["Father"] = self.ListOfDevices[_father]["ZDeviceName"]
            else:
                _relation["Father"] = "Zigate"

            if _child != "0000":
                if "ZDeviceName" in self.ListOfDevices[_child]:
                    if (
                        self.ListOfDevices[_child]["ZDeviceName"] != ""
                        and self.ListOfDevices[_child]["ZDeviceName"] != {}
                    ):
                        # _relation[slave] = self.ListOfDevices[_child]['ZDeviceName']
                        _relation["Child"] = self.ListOfDevices[_child]["ZDeviceName"]
            else:
                _relation["Child"] = "Zigate"

            # Sanity check, remove the direct loop
            if (_relation["Child"], _relation["Father"]) in _check_duplicate:
                self.logging(
                    "Debug",
                    "Skip (%s,%s) as there is already ( %s, %s)"
                    % (_relation["Father"], _relation["Child"], _relation["Child"], _relation["Father"]),
                )
                continue

            _check_duplicate.append((_relation["Father"], _relation["Child"]))
            self.logging(
                "Debug",
                "Relationship - %15.15s - %15.15s %3s"
                % (_relation["Father"], _relation["Child"], _relation["_lnkqty"]),
            )
            _topo.append(_relation)

    return _topo


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

            if len(parent1) and len(parent2) == 0:
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
