#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import json

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.bindings import webBind, webUnBind, bindGroup
from Modules.zigateConsts import ZCL_CLUSTERS_ACT


def rest_bindLSTcluster(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    bindCluster = []
    for key in self.ListOfDevices:
        if key == "0000":
            continue

        for ep in self.ListOfDevices[key]["Ep"]:
            for cluster in self.ListOfDevices[key]["Ep"][ep]:
                if cluster in ZCL_CLUSTERS_ACT:
                    item = {"ClusterId": cluster, "ClusterDesc": ZCL_CLUSTERS_ACT[cluster]}
                    if item not in bindCluster:
                        bindCluster.append(item)
    _response["Data"] = json.dumps(bindCluster)

    return _response


def rest_bindLSTdevice(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if len(parameters) != 1:
        Domoticz.Error("Must have 1 argument. %s" % parameters)
        return _response

    listofdevices = []
    clustertobind = parameters[0]

    for key in self.ListOfDevices:
        if key == "0000":
            dev = {
                "IEEE": self.ListOfDevices[key]["IEEE"],
                "NwkId": key,
                "Ep": "01",
                "ZDeviceName": self.ListOfDevices[key]["ZDeviceName"],
            }
            listofdevices.append(dev)
            continue

        for ep in self.ListOfDevices[key]["Ep"]:
            if clustertobind in self.ListOfDevices[key]["Ep"][ep]:
                dev = {
                    "IEEE": self.ListOfDevices[key]["IEEE"],
                    "NwkId": key,
                    "Ep": ep,
                    "ZDeviceName": self.ListOfDevices[key]["ZDeviceName"],
                }

                if dev not in listofdevices:
                    listofdevices.append(dev)
    _response["Data"] = json.dumps(listofdevices)
    return _response


def rest_binding(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb != "PUT" or len(parameters) != 0:
        return _response

    _response["Data"] = None

    data = data.decode("utf8")
    data = json.loads(data)

    if (
        "sourceIeee" not in data
        and "sourceEp" not in data
        and "destIeee" not in data
        and "destEp" not in data
        and "cluster" not in data
    ):
        Domoticz.Error("-----> uncomplet json %s" % data)
        _response["Data"] = json.dumps("uncomplet json %s" % data)
        return _response

    self.logging(
        "Debug",
        "rest_binding - Source: %s/%s Dest: %s/%s Cluster: %s"
        % (data["sourceIeee"], data["sourceEp"], data["destIeee"], data["destEp"], data["cluster"]),
    )
    webBind(self, data["sourceIeee"], data["sourceEp"], data["destIeee"], data["destEp"], data["cluster"])
    _response["Data"] = json.dumps(
        "Binding cluster %s between %s/%s and %s/%s"
        % (data["cluster"], data["sourceIeee"], data["sourceEp"], data["destIeee"], data["destEp"])
    )
    return _response

def rest_group_binding(self, verb, data, parameters):

    # curl -X PUT -d '{"sourceIeee":" 84fd27fffe17e4c5", "sourceEp": "01", "groupId": " 4ca3", "cluster": "0006"}' http://127.0.0.1:9441/rest-zigate/1/binding-group
    
    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb != "PUT" or len(parameters) != 0:
        return _response

    _response["Data"] = None

    data = data.decode("utf8")
    data = json.loads(data)

    if (
        "sourceIeee" not in data
        and "sourceEp" not in data
        and "groupId" not in data
        and "cluster" not in data
    ):
        Domoticz.Error("-----> uncomplet json %s" % data)
        _response["Data"] = json.dumps("uncomplet json %s" % data)
        return _response

    self.logging(
        "Debug",
        "rest_binding - Source: %s/%s Dest: %s Cluster: %s"
        % (data["sourceIeee"], data["sourceEp"], data["groupId"], data["cluster"]),
    )
    bindGroup(self, data["sourceIeee"], data["sourceEp"], data["cluster"], data["groupId"])

    _response["Data"] = json.dumps(
        "Binding cluster %s between %s/%s and %s"
        % (data["cluster"], data["sourceIeee"], data["sourceEp"], data["groupId"])
    )
    return _response


def rest_unbinding(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb != "PUT" or len(parameters) != 0:
        return _response

    _response["Data"] = None

    data = data.decode("utf8")
    data = json.loads(data)

    if (
        "sourceIeee" not in data
        and "sourceEp" not in data
        and "destIeee" not in data
        and "destEp" not in data
        and "cluster" not in data
    ):
        Domoticz.Log("-----> uncomplet json %s" % data)
        _response["Data"] = json.dumps("uncomplet json %s" % data)
        return _response

    self.logging(
        "Debug",
        "rest_unbinding - Source: %s/%s Dest: %s/%s Cluster: %s"
        % (data["sourceIeee"], data["sourceEp"], data["destIeee"], data["destEp"], data["cluster"]),
    )
    webUnBind(self, data["sourceIeee"], data["sourceEp"], data["destIeee"], data["destEp"], data["cluster"])
    _response["Data"] = json.dumps(
        "Binding cluster %s between %s/%s and %s/%s"
        % (data["cluster"], data["sourceIeee"], data["sourceEp"], data["destIeee"], data["destEp"])
    )
    return _response
