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

# curl -X PUT -d '{
#   "auto": true,
#   "oldIEEE": "8c65a3fffe106bd1",
#   "newIEEE": "1234567890abcdef"
# }' http://127.0.0.1:9441/rest-z4d/1/device_replace
# Will replace all matching newIEEE Widgets domoticz references by the one found in oldIEEE

# or

# curl -X PUT -d '{
#   "auto": false,
#   "IEEE": "8c65a3fffe106bd1",
#   "WidgetIdx": "25"
#   "ReplaceByIdx": "35"
# }' http://127.0.0.1:9441/rest-z4d/1/device_replace
# Will overwrite the specified WidgetIdx value by the value of ReplaceByIdx.
# In this case as example "ClusterType": {"25": "Motion"} will become "ClusterType": {"35": "Motion"}


def rest_device_replace(self, verb, data, parameters):
    """
    Handle REST operations for device replacement in Domoticz.
    
    :param verb: HTTP verb indicating the operation (e.g., "GET", "PUT").
    :param data: Data payload for the operation, typically in JSON format.
    :param parameters: Parameters for the operation, such as a device identifier.
    :return: A dictionary response with the operation result.
    """
    self.logging("INFO", f"rest_device_replace --> Verb: {verb}, Data: {data}, Parameters: {parameters}")

    if verb == "GET":
        # Provide the ClusterType entry for each Endpoint of the given IEEE
        return get_device_clustertype_info(self, parameters)
        
    elif verb == "PUT":
        # Perform updates based on the provided JSON data
        if not data:
            self.logging("ERROR", "rest_device_replace - PUT request with no data.")
            response = prepResponseMessage(self, setupHeadersResponse())
            response["Data"] = json.dumps({"error": "No data provided for PUT operation"})
            return response
        return update_device(self, data)
        
    # Handle unsupported HTTP verbs
    self.logging("Error", f"rest_device_replace - Unsupported HTTP verb: {verb}")
    response = prepResponseMessage(self, setupHeadersResponse())
    response["Data"] = json.dumps({"error": f"Unsupported HTTP verb: {verb}"})
    return response


def get_device_clustertype_info(self, parameters):
    """
    Retrieve cluster type information for a device based on its network ID.
    :param parameters: A list with a single network ID as the first element.
    :return: A dictionary response containing device cluster type information.
    """
    _response = prepResponseMessage(self, setupHeadersResponse())

    # Validate parameters
    if not parameters or len(parameters) != 1:
        self.logging("Error", f"get_device_clustertype_info - unexpected parameter: {parameters}")
        _response["Data"] = json.dumps({"error": f"Unexpected parameters: {parameters}"})
        return _response

    nwkid = parameters[0]
    device_info = self.ListOfDevices.get(nwkid)

    if not device_info:
        self.logging("Error", f"get_device_clustertype_info - Unknown device {nwkid}")
        _response["Data"] = json.dumps({"error": f"Unknown device: {nwkid}"})
        return _response

    try:
        build_clustertype_info = {"DeviceIEEE": device_info.get("IEEE", "")}

        # Process endpoints and their cluster types
        for ep, ep_info in device_info.get("Ep", {}).items():
            cluster_type = ep_info.get("ClusterType", {})
            build_clustertype_info[ep] = [
                {"WidgetIdx": widget_idx, "WidgetType": widget_type}
                for widget_idx, widget_type in cluster_type.items()
            ]

        _response["Data"] = json.dumps(build_clustertype_info, sort_keys=False)
        
    except Exception as e:
        self.logging("Error", f"get_device_clustertype_info - Error processing device {nwkid}: {e}")
        _response["Data"] = json.dumps({"error": f"Error processing device {nwkid}: {e}"})

    return _response


def update_device(self, data):
    """
    Enable or disable the provisioning process and update Domoticz device references.

    This function handles two modes:
    1. Automatic mode (`auto: true`): Replaces all widgets referencing `oldIEEE` with `newIEEE`.
    2. Manual mode (`auto: false`): Replaces a specific `WidgetIdx` with `ReplaceByIdx` for a given `IEEE`.

    :param data: JSON-encoded string containing the operation parameters.
    :return: A dictionary response with the result of the operation.
    """
    _response = prepResponseMessage(self, setupHeadersResponse())

    try:
        # Decode and parse the data
        data = data.decode("utf8")
        data = json.loads(data)
        self.logging("Log", f"update_device - Parsed Data: {data}")
    except json.JSONDecodeError:
        self.logging("Error", "update_device - Invalid JSON data")
        _response["Data"] = {"error": "Invalid JSON data"}
        return _response

    except ValueError as e:
        self.logging("Error", f"update_device - {str(e)}")
        _response["Data"] = {"error": str(e)}
        return _response

    except Exception as e:
        self.logging("Error", f"update_device - Unexpected error: {str(e)}")
        _response["Data"] = {"error": "An unexpected error occurred"}
        return _response

    # Determine operation type (automatic or manual)
    auto_processing = data.get("auto")
    if auto_processing is None:
        self.logging("Error", "Missing 'auto' key in data")
        _response["Data"] = {"error": "Missing 'auto' key in data"}
        return _response

    if auto_processing:
        # Automatic processing
        old_ieee = data.get("oldIEEE")
        new_ieee = data.get("newIEEE")
        if not old_ieee or not new_ieee:
            self.logging("Error", "Missing 'oldIEEE' or 'newIEEE' in auto mode")
            _response["Data"] = {"error": "Missing 'oldIEEE' or 'newIEEE' in auto mode"}
            return _response

        _response = update_device_automatically(self, old_ieee, new_ieee, _response)
    else:
        # Manual processing
        ieee = data.get("IEEE")
        nwkid = self.ieee2nwk.get(ieee)
        if nwkid is None:
            # ieee not found
            self.logging("Error", f"'IEEE' {ieee} not found")
            _response["Data"] = {"error": f"'IEEE' {ieee} not found"}
            return _response
        _response = update_device_manually(self, ieee, nwkid, data, _response)

    return _response


def update_device_automatically(self, old_ieee, new_ieee, _response):
    pass


def update_device_manually(self, ieee, nwkid, data, _response):
    """
    Updates the widget index for a specific device based on the provided data.
    
    This function checks if the necessary fields ('IEEE', 'WidgetIdx', and 'ReplaceByIdx') 
    are provided. If any of the fields are missing, it logs an error and returns a response 
    indicating the missing fields. If all required fields are present, it attempts to update 
    the widget index for the device and returns a response with the result.

    Parameters:
        ieee (str): The IEEE address of the device to update.
        nwkid (str): The network ID of the device to update.
        data (dict): A dictionary containing the 'WidgetIdx' (current widget index) 
                     and 'ReplaceByIdx' (new widget index).
        _response (dict): A dictionary that will be updated with the status or error message.

    Returns:
        dict: The updated response dictionary, containing either the success status or an error message.
    """
    # Retrieve WidgetIdx and ReplaceByIdx from the data
    target_widget_idx = data.get("WidgetIdx")
    new_widget_idx = data.get("ReplaceByIdx")
    
    # Check for missing required fields
    if not ieee or not target_widget_idx or not new_widget_idx:
        self.logging("Error", "Missing 'IEEE', 'WidgetIdx', or 'ReplaceByIdx' in manual mode")
        _response["Data"] = {"error": "Missing 'IEEE', 'WidgetIdx', or 'ReplaceByIdx' in manual mode"}
        return _response

    # Attempt to update the device widget index
    update_successful = update_device_widgetidx(self, nwkid, target_widget_idx, new_widget_idx)
    
    if update_successful:
        _response["Data"] = {"status": "success"}
    else:
        self.logging("Error", f"WidgetIdx {target_widget_idx} not found for this device {ieee}/{nwkid}")
        _response["Data"] = {"status": f"WidgetIdx {target_widget_idx} not found for this device {ieee}/{nwkid}"}

    return _response


def update_device_widgetidx(self, nwkid, target_widget_idx, new_widget_idx):
    # Get device information for the provided nwkid
    device_infos = self.ListOfDevices.get(nwkid)
    
    # If device information doesn't exist, return or handle the error
    if device_infos is None:
        self.logging("Error", f"Device with nwkid {nwkid} not found.")
        return False

    # Iterate over all endpoints (Ep) in the device information
    for ep, ep_info in device_infos.get("Ep", {}).items():
        cluster_type = ep_info.get("ClusterType")
        
        # If ClusterType exists, try to update the WidgetIdx
        if cluster_type:
            # Check if target_widget_idx is present in ClusterType before updating
            if target_widget_idx in cluster_type:
                if update_widget_idx(cluster_type, target_widget_idx, new_widget_idx):
                    # we break as we do not expect several references per design
                    return True
            else:
                self.logging("Log", f"WidgetIdx {target_widget_idx} not found in ClusterType for endpoint {ep}.")
    return False


def update_widget_idx(cluster_type, current_idx, new_idx):
    """
    Updates the WidgetIdx key in the ClusterType dictionary.
    
    Parameters:
        cluster_type (dict): The dictionary containing WidgetIdx and Type mappings.
        current_idx (str): The current WidgetIdx to be updated.
        new_idx (str): The new WidgetIdx to replace the current one.
    
    Returns:
        bool: True if the update was successful, False if the current_idx doesn't exist.
    """
    if current_idx in cluster_type:
        # Preserve the value and remove the old key
        cluster_type[new_idx] = cluster_type.pop(current_idx)
        return True
    return False
