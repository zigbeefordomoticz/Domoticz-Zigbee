#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Data structure helpers extracted from tools.py"""


def get_cluster_attribute_value( self, key, endpoint, clusterId, AttributeId):
    """
    Retrieve the value of a specific attribute within a cluster at a given endpoint for a device.

    Args:
        key: Device identifier (e.g., network ID)
        endpoint: Endpoint identifier within the device
        clusterId: Cluster ID within the endpoint
        AttributeId: Attribute ID within the cluster

    Returns:
        The attribute value if found, else None.
    """
    return (
        self.ListOfDevices
            .get(key, {})
            .get("Ep", {})
            .get(endpoint, {})
            .get(clusterId, {})
            .get(AttributeId)
    )


# Functions to manage Device Attributes infos ( ConfigureReporting)
def check_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    """
    Ensure the nested data structure exists within ListOfDevices for a given device,
    device attribute, endpoint, and clusterId. Initialize missing nodes as empty dicts or default values.

    Args:
        DeviceAttribute (str): The attribute category under the device (e.g., "Ep").
        key: Device identifier (e.g., network ID).
        endpoint: Endpoint identifier within the device.
        clusterId: Cluster identifier within the endpoint.

    Returns:
        True if structure ensured, None if device key not found.
    """
    if key not in self.ListOfDevices:
        return None

    device_attr = self.ListOfDevices[key].setdefault(DeviceAttribute, {})
    ep = device_attr.setdefault("Ep", {})
    endpoint_dict = ep.setdefault(endpoint, {})
    cluster_dict = endpoint_dict.setdefault(clusterId, {})

    if not isinstance(cluster_dict, dict):
        endpoint_dict[clusterId] = cluster_dict = {}

    cluster_dict.setdefault("TimeStamp", 0)
    cluster_dict.setdefault("iSQN", {})
    cluster_dict.setdefault("Attributes", {})
    cluster_dict.setdefault("ZigateRequest", {})

    return True


def is_time_to_perform_work(self, DeviceAttribute, key, endpoint, clusterId, now, timeoutperiod):
    # Based on a timeout period return True or False.
    if key not in self.ListOfDevices:
        return False
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return False
    return now >= (self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["TimeStamp"] + timeoutperiod)


def set_timestamp_datastruct(self, DeviceAttribute, key, endpoint, clusterId, now):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["TimeStamp"] = now


def get_list_isqn_attr_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    if key not in self.ListOfDevices:
        return []
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return []
    return list(list(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"].keys()))

def get_list_isqn_int_attr_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    if key not in self.ListOfDevices:
        return []
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return []
    return [int(x, 16) for x in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"].keys()]

def set_request_datastruct(
    self,
    DeviceAttribute,
    key,
    endpoint,
    clusterId,
    AttributeId,
    datatype,
    EPin,
    EPout,
    manuf_id,
    manuf_spec,
    data,
    ackIsDisabled,
    phase,
):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if AttributeId not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId] = {}

    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["Status"] = phase
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "DataType"
    ] = datatype
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPin"] = EPin
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPout"] = EPout
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "manuf_id"
    ] = manuf_id
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "manuf_spec"
    ] = manuf_spec
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["data"] = data
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "ackIsDisabled"
    ] = ackIsDisabled


def get_request_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    # Return all arguments to make the WriteAttribute
    if key not in self.ListOfDevices:
        return None
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return None
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        return (
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "DataType"
            ],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPin"],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPout"],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "manuf_id"
            ],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "manuf_spec"
            ],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["data"],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "ackIsDisabled"
            ],
        )
    return None


def set_request_phase_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId, phase):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
            "Status"
        ] = phase


def get_list_waiting_request_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    """Return a list of Attributes that are waiting to be written"""

    # Return early if key is not in ListOfDevices
    device = self.ListOfDevices.get(key)
    if not device:
        return []

    # Check if data structure is valid
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return []

    # Navigate safely through nested dictionary
    zigate_request = (
        device.get(DeviceAttribute, {})
        .get("Ep", {})
        .get(endpoint, {})
        .get(clusterId, {})
        .get("ZigateRequest", {})
    )

    # Return attributes where status is "waiting"
    return [attr for attr, data in zigate_request.items() if data.get("Status") == "waiting"]


def set_isqn_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId, isqn):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if isqn is not None:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][AttributeId] = isqn


def get_isqn_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return None
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return None
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"]:
        return self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][AttributeId]
    return None


def set_status_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId, status):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"][AttributeId] = status
    clean_old_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId)


def get_status_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return None
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return None
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"]:
        return self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"][AttributeId]
    return None


def is_attr_unvalid_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    lastStatus = get_status_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId)
    if lastStatus is None:
        return False
    return True if lastStatus in ("86", "8c") else lastStatus != "00"


def reset_attr_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"][AttributeId]
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][AttributeId]
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]


def reset_cluster_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if clusterId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]


def reset_device_attribute(self, Nwkid: str, attribute: str) -> None:
    """Reset a device attribute to an empty dict, no-op if device or attribute unknown."""
    if Nwkid not in self.ListOfDevices:
        return
    self.ListOfDevices[Nwkid][attribute] = {}


def clean_old_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return False
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return False
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId][AttributeId]
    if "TimeStamp" in self.ListOfDevices[key][DeviceAttribute]:
        del self.ListOfDevices[key][DeviceAttribute]["TimeStamp"]