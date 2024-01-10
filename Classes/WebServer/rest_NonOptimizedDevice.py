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

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)


def rest_non_optimized_device_configuration(self, verb, data, parameters):
    """ REST API to respond with a JSON Device Configuration structure with what have been collected"""

    _response = prepResponseMessage(self, setupHeadersResponse())
    if self.ControllerData and self.configureReporting is None or verb != "GET" or len(parameters) != 1:
        self.logging("Error", f"rest_non_optimized_device_configuration incorrect request {verb} {data} {parameters}")
        return _response

    if self.ControllerData and parameters[0] not in self.ListOfDevices:
        self.logging("Error", "rest_non_optimized_device_configuration requested on %s doesn't exist" % parameters[0])
        return _response

    if self.ControllerData:
        self.configureReporting.check_and_redo_configure_reporting_if_needed( parameters[0] )
        
    self.logging("Debug", f"rest_non_optimized_device_configuration requested on {parameters[0]}")

    _response["Data"] = construct_configuration_file(self, parameters[0])
    return _response


def construct_configuration_file(self, Nwkid):
    
    if Nwkid not in self.ListOfDevices:
        self.logging("Error", f"rest_non_optimized_device_configuration - unknow devic {Nwkid}")
        return {}
    
    if "Model" not in self.ListOfDevices[ Nwkid ] or self.ListOfDevices[ Nwkid ]["Model"] in ( '', {}):
        # Unknow model
        self.logging("Error", f"rest_non_optimized_device_configuration - unknow Zigbee model {Nwkid}")
        return {}
    model_name = self.ListOfDevices[ Nwkid ]["Model"]
    
    configuration_file={
        "Filename": f"{model_name}.json",
        "_comment": "",
        "_version": "",
        "_blakadder": "",
        "_source": "",
        "Type": "",
        "ClusterToBind": [],
        "ConfigureReporting": {},
        "ReadAttributes": {},
        "Param": {},
        "GroupMembership": {}
    }
    
    device = self.ListOfDevices[ Nwkid ]
    endpoint = device.get(["Ep"], {})
    for ep_id, ep_content in endpoint.items():
        _list_clusters, _cluster_type, _type = _process_one_endpoint(self, ep_content)
        configuration_file[ "Ep"][ ep_id ] = _list_clusters
        configuration_file[ "Ep"][ ep_id ]["Type"] = _type or _cluster_type
        
    configuration_file["ReadAttributes"] = _analyse_read_attributes_infos(self, device["ReadAttributes"] )
   
                          
def _process_one_endpoint(self, ep_content):

    list_of_cluster = {}
    attribute_cluster_type = {}
    attribute_type = None

    for key, attribute in ep_content.items():
        if key == "ClusterType":
            attribute_cluster_type = "/".join(_type for _, _type in attribute)

        elif key == "Type":
            attribute_type = attribute

        else:
            list_of_cluster.setdefault(key, "")

    if attribute_cluster_type:
        # Remove the last "/"
        attribute_cluster_type = attribute_cluster_type.rsplit("/", 1)[0]

    return list_of_cluster, attribute_cluster_type, attribute_type
            
        
def _analyse_read_attributes_infos(self, read_attributes_input):
    read_attributes = {}

    for _, clusters in read_attributes_input.items():
        for cluster, cluster_info in clusters.items():
            attribute_list = read_attributes.setdefault(cluster, [])
            attribute_list.extend(attribute for attribute, status in cluster_info.get("Attributes", []) if status == "00" and attribute not in attribute_list)
       
                
                
                
                
                
                    
