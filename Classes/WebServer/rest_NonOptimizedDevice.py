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
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)


# curl  http://127.0.0.1:9440/rest-zigate/1/non-optimized-device-configuration/xyxz

def rest_non_optimized_device_configuration(self, verb, data, parameters):
    """ REST API to respond with a JSON Device Configuration structure with what have been collected"""

    _response = prepResponseMessage(self, setupHeadersResponse())
    
    self.logging("Debug", f"rest_non_optimized_device_configuration  {verb} {data} {parameters}")
    
    if verb != "GET" or len(parameters) != 1:
        self.logging("Error", f"rest_non_optimized_device_configuration incorrect request {verb} {data} {parameters}")
        return _response

    if self.ControllerData and parameters[0] not in self.ListOfDevices:
        self.logging("Error", "rest_non_optimized_device_configuration requested on %s doesn't exist" % parameters[0])
        return _response

    self.logging("Debug", f"rest_non_optimized_device_configuration requested on {parameters[0]}")

    _response["Data"] = json.dumps(construct_configuration_file(self, parameters[0]))
    
    self.logging("Debug", f"rest_non_optimized_device_configuration response_data {_response['Data']}")
    return _response


def construct_configuration_file(self, Nwkid):
    self.logging("Debug", f"construct_configuration_file {Nwkid}")
    
    if Nwkid not in self.ListOfDevices:
        self.logging("Error", f"rest_non_optimized_device_configuration - unknow device {Nwkid}")
        return {}
    
    if "Model" not in self.ListOfDevices[ Nwkid ] or self.ListOfDevices[ Nwkid ]["Model"] in ( '', {}):
        # Unknow model
        self.logging("Error", f"rest_non_optimized_device_configuration - unknow Zigbee model {Nwkid}")
        return {}
    
    model_name = self.ListOfDevices[ Nwkid ]["Model"]
    self.logging("Debug", f"construct_configuration_file model_name {model_name}")
    device = self.ListOfDevices[ Nwkid ]
    
    return {
        "Filename": f"{model_name}.json",
        "_comment": "",
        "_version": "",
        "_blakadder": "",
        "_source": "",
        "Ep": _analyse_ep_infos(self, device.get("Ep", {})),
        "Type": "",
        "ClusterToBind": _analyse_bind_infos(self, device.get("BindingTable", {}), device.get("Bind", {})),
        "ConfigureReporting": _analyse_read_configure_reporting_infos(self, device.get("ReadConfigureReporting", {}), device.get("ConfigureReporting", {})),
        "ReadAttributes": _analyse_read_attributes_infos(self, device["ReadAttributes"] ),
        "Param": {},
        "GroupMembership": {},
    }


def _analyse_ep_infos(self, endpoint):
    self.logging("Debug", f"_analyse_ep_infos  {endpoint}")

    _ep_config = {"Ep": {}}

    for ep_id, ep_content in endpoint.items():
        _list_clusters, _cluster_type, _type = _process_one_endpoint(self, ep_content)
        _ep_config[ "Ep"][ ep_id ] = _list_clusters
        _ep_config[ "Ep"][ ep_id ]["Type"] = _type or _cluster_type
    return _ep_config
    
                          
def _process_one_endpoint(self, ep_content):
    self.logging("Debug", f"_process_one_endpoint  {ep_content}")

    list_of_cluster = {}
    attribute_cluster_type = {}
    attribute_type = None

    for key, attribute in ep_content.items():
        self.logging("Debug", f"_process_one_endpoint  {key} {attribute}")

        if key == "ClusterType":
            attribute_cluster_type = "/".join(attribute.values())

        elif key == "Type":
            attribute_type = attribute

        else:
            list_of_cluster.setdefault(key, "")

    return list_of_cluster, attribute_cluster_type, attribute_type
            
        
def _analyse_read_attributes_infos(self, read_attributes_input):
    self.logging("Debug", f"_analyse_read_attributes_infos  {read_attributes_input}")

    read_attributes = {}

    for _, ep_data in read_attributes_input.get("Ep", {}).items():
        for cluster, cluster_data in ep_data.items():
            read_attributes[cluster] = []
            for key, attribute_data in cluster_data.items():
                if key == "Attributes":
                    for attribute, status in attribute_data.items():
                        if status == "00" and attribute not in read_attributes[cluster]:
                            read_attributes[cluster].append( attribute )
            
    return read_attributes


def _analyse_bind_infos(self, read_bind_infos, binding_infos): 
    self.logging("Debug", f"_analyse_bind_infos  {read_bind_infos}")

    cluster_to_bind = set()
    binded_list = read_bind_infos.get("Devices", [])

    for entry in binded_list:
        cluster = entry.get("Cluster")
        if cluster:
            cluster_to_bind.add(cluster)

    return list(cluster_to_bind)

                
def _analyse_read_configure_reporting_infos(self, read_configure_reporting_infos, configure_reporting_infos):
    self.logging("Debug", f"_analyse_read_configure_reporting_infos  {read_configure_reporting_infos}")

    configure_resporting = {}
    
    for ep, ep_data in read_configure_reporting_infos.get("Ep", {}).items():
        for cluster, cluster_data in ep_data.items():
            configure_resporting[cluster] = {}
            for attribute, attribute_data in cluster_data.items():
                configure_resporting[cluster][attribute] = {
                    "Change": attribute_data.get("Change", {}),
                    "DataType": attribute_data.get("DataType", {}),
                    "MaxInterval": attribute_data.get("MaxInterval", {}),
                    "MinInterval": attribute_data.get("MinInterval", {}),
                    "TimeOut": "0000"
                }
                
    return configure_resporting
        
            
                
                
                    
