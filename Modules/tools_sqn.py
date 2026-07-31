#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""SQN and attribute helpers extracted from tools.py"""

import datetime
import time
from collections import deque

from Modules.tools_primitives import is_hex


def get_and_inc_ZDP_SQN(self, key):
    """Get and increment ZDP sequence number for the device identified by key."""
    return get_and_increment_generic_SQN(self, key, "ZDPSQN")


def get_and_inc_ZCL_SQN(self, key):
    """Get and increment ZCL sequence number for the device identified by key."""
    return get_and_increment_generic_SQN(self, key, "ZCLSQN")


def get_and_inc_TUYA_POLLING_SQN(self, key):
    """Get and increment TUYA polling sequence number for the device identified by key."""
    return get_and_increment_generic_SQN(self, key, "TUYA_POLLING_SQN")


def get_and_increment_generic_SQN(self, nwkid, sqn_type):
    """
    Retrieve and increment a sequence number (SQN) of given type for a device.

    SQNs are stored as zero-padded 2-digit hex strings and wrap at 0xFF.

    Args:
        nwkid (str): Network ID of the device.
        sqn_type (str): The sequence number type/key.

    Returns:
        str: The incremented SQN as a zero-padded 2-digit hex string.
    """
    if nwkid not in self.ListOfDevices: 
        return "%02x" %0x00

    current_sqn = self.ListOfDevices[nwkid].get(sqn_type, "00")
    if not current_sqn or current_sqn == {}:
        current_sqn = "00"

    try:
        next_sqn = (int(current_sqn, 16) + 1) % 256
    except ValueError:
        next_sqn = 0  # Reset if malformed

    sqn_str = f"{next_sqn:02x}"
    self.ListOfDevices[nwkid][sqn_type] = sqn_str

    return sqn_str


def updSQN(self, key, newSQN):
    """Update the sequence number (SQN) for the given device key in the ListOfDevices."""

    # Log function entry with important details
    self.log.logging('Input', 'Debug', f'Entering updSQN with key={key} newSQN={newSQN}')

    # Safely retrieve the device entry using .get() and update the SQN if the key exists and newSQN is valid
    device = self.ListOfDevices.get(key)
    if device and newSQN:
        # Log the updated sequence number for traceability
        self.log.logging('Input', 'Debug', f'Updated SQN for device {key} from {device.get("SQN", "")} to {newSQN}')
        device["SQN"] = newSQN


def is_duplicate_sqn(self, MsgDataShAddr, MsgDataSQN):
    """Check if the message sequence number (SQN) is a duplicate."""

    # Log function entry with key information
    self.log.logging('Input', 'Debug', f'Checking duplicate SQN for device {MsgDataShAddr} with SQN {MsgDataSQN}')

    # Safely retrieve the device from ListOfDevices
    device = self.ListOfDevices.get(MsgDataShAddr)

    # If device exists and has an SQN, check if it's a duplicate
    if device and 'SQN' in device and MsgDataSQN == device['SQN']:
        self.log.logging('Input', 'Debug', f'SQN {MsgDataSQN} is a duplicate for device {MsgDataShAddr}')
        return True
    return False


def updLQI(self, key, LQI):
    device = self.ListOfDevices.get(key)
    if not device:
        return

    if LQI == "00" or not is_hex(LQI):
        return

    lqi_value = int(LQI, 16)

    device["LQI"] = lqi_value

    rolling = device.setdefault("RollingLQI", deque(maxlen=10))
    rolling.append(lqi_value)


def upd_RSSI(self, nwkid, rssi_value):
    # Ensure the device exists in the dictionary
    if nwkid not in self.ListOfDevices:
        return
    
    # Update RSSI value directly
    self.ListOfDevices[nwkid]["RSSI"] = rssi_value

    # Initialize RollingRSSI list if it doesn't exist
    self.ListOfDevices[nwkid].setdefault("RollingRSSI", [])

    # Add RSSI to RollingRSSI list
    self.ListOfDevices[nwkid]["RollingRSSI"].append(rssi_value)

    # Keep RollingRSSI list size at most 10 elements
    self.ListOfDevices[nwkid]["RollingRSSI"] = self.ListOfDevices[nwkid]["RollingRSSI"][-10:]


def timeStamped(self, key, Type):
    """
    Update the timestamp information for a given device in ListOfDevices.

    Ensures the 'Stamp' dictionary exists for the device, then updates:
    - 'time': current Unix timestamp (float)
    - 'Time': human-readable timestamp (YYYY-MM-DD HH:MM:SS)
    - 'MsgType': message type formatted as a 4-digit hex string

    Parameters:
        key (str): The device key (e.g., NwkId) in ListOfDevices.
        Type (int): Numeric message type to store (formatted as hex).

    Returns:
        None
    """
    if key not in self.ListOfDevices:
        return

    stamps = self.ListOfDevices[key].setdefault(
        "Stamp", {"LasteSeen": {}, "Time": {}, "MsgType": {}}
    )

    now = time.time()
    stamps["time"] = now
    stamps["Time"] = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
    stamps["MsgType"] = f"{Type:04x}"


def store_battery_percentage_time_stamp( self, MsgSrcAddr):
    self.ListOfDevices[MsgSrcAddr]["BatteryPercentage_TimeStamp"] = time.time()


def store_battery_voltage_time_stamp( self, MsgSrcAddr):
    self.ListOfDevices[MsgSrcAddr]["BatteryVoltage_TimeStamp"] = time.time()


def checkAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID):
    """
    Ensure nested dictionaries exist for the given device address, endpoint, cluster ID, and attribute ID.

    Creates empty dicts as needed to guarantee the path:
    ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID]

    Args:
        MsgSrcAddr: Device network address
        MsgSrcEp: Endpoint identifier
        MsgClusterId: Cluster identifier
        MsgAttrID: Attribute identifier
    """
    device = self.ListOfDevices.setdefault(MsgSrcAddr, {})
    ep = device.setdefault("Ep", {})
    cluster = ep.setdefault(MsgSrcEp, {}).setdefault(MsgClusterId, {})

    # Ensure the attribute ID is set
    if MsgAttrID not in cluster or not isinstance(cluster[MsgAttrID], dict):
        cluster[MsgAttrID] = {}


def checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, Value):
    """
    Ensure the attribute structure exists and store the given value.

    Args:
        MsgSrcAddr: Device network address
        MsgSrcEp: Endpoint identifier
        MsgClusterId: Cluster identifier
        MsgAttrID: Attribute identifier
        Value: Value to store for the attribute
    """
    checkAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID)
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = Value


def checkValidValue(self, MsgSrcAddr, AttType, Data ):
    if int(AttType, 16) == 0xE2 and Data == "ffffffff":
        return False

    model = self.ListOfDevices.get(MsgSrcAddr, {}).get("Model")
    return not (model == "lumi.airmonitor.acn01" and Data in {"8000", "0000"})


def getAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID):
    """
    Retrieve the value of a specific attribute from the device list.

    Args:
        MsgSrcAddr: Network address of the device.
        MsgSrcEp: Endpoint of the device.
        MsgClusterId: Cluster ID.
        MsgAttrID: Attribute ID.

    Returns:
        The attribute value if found, otherwise None.
    """
    device = self.ListOfDevices.get(MsgSrcAddr)
    if device is None:
        self.log.logging("PluginTools", "Debug", f"getAttributeValue - Unknown {MsgSrcAddr}")
        return None

    ep = device.get("Ep", {}).get(MsgSrcEp)
    if ep is None:
        self.log.logging("PluginTools", "Debug", f"getAttributeValue - Unknown {MsgSrcAddr}/{MsgSrcEp}")
        return None

    cluster = ep.get(MsgClusterId)
    if not isinstance(cluster, dict):
        self.log.logging("PluginTools", "Debug", f"getAttributeValue - Not dict {MsgSrcAddr}/{MsgSrcEp} {MsgClusterId}")
        return None

    if MsgAttrID not in cluster:
        self.log.logging("PluginTools", "Debug", f"getAttributeValue - Unknown {MsgSrcAddr}/{MsgSrcEp} {MsgClusterId} {MsgAttrID}")
        return None

    return cluster[MsgAttrID]