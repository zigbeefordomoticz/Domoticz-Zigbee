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
"""
Zigbee Device ZCL Clusters helpers
----------------------------------------

This module provides utilities for handling Zigbee device pairing, model resolution, 
and metering consumption calculations in Z4D environment.

The key responsibilities of this module include:
0. Zigbee Attribute Decoding Utilities
   - provides helper functions to decode various types of Zigbee attribute
    values received from devices. The functions support boolean, bitmap, unsigned
    integers of various sizes, and signed integers.

    All input values are expected to be hexadecimal strings representing the raw
    attribute data.

1. **Device Model Handling**
   - `_cleanup_model_name`: Cleans and normalizes raw model name strings from devices.
   - `_build_model_name`: Attempts to build a normalized device model name based on
     the device's reported model, manufacturer, and DeviceConf definitions.
   - `_is_device_already_provisioned`: Checks if a device is already provisioned and
     updates its configuration if needed.
   - `handle_model_name`: Main entry point for handling incoming model name attributes,
     performs deduplication, provisioning checks, and updates device structures.

2. **Device Data Structure Management**
   - `_update_data_structutre_based_on_model_name`: Populates the device record
     with parameters, type, and endpoint data from DeviceConf.
   - `_upd_data_strut_based_on_model`: Updates endpoint and cluster structures,
     copies missing attributes from previous data, and handles color mode/type info.

3. **Metering and Consumption**
   - `compute_metering_conso`: Computes electrical consumption or power values
     from raw metering attributes, applying unit conversions, multipliers, and
     divisors defined in DeviceConf or cluster data. Automatically triggers a
     read request if required attributes are missing.

4. **Helper Functions**
   - `get_deviceconf_parameter_value`: Retrieves parameter values from DeviceConf
     for specific models.
   - `plugin_self_identifier` and `check_found_plugin_model`: Utility functions used
     in model resolution for plugin-based devices.


Logging:
--------
All functions log key operations using `self.log.logging` with consistent categories
such as "ZclClusters" and "Pairing" or "Electric" for metering.

Type Safety:
------------
All functions have been refactored with type hints for improved readability
and static analysis.

Notes:
------
- DeviceConf is assumed to be a dictionary containing known device models
  and their configuration.
- Endpoint data and cluster data are stored under `self.ListOfDevices`.
- This module assumes an optional IAS zone management object
  (`self.iaszonemgt`) for registration of security devices.

"""

import binascii
import struct
from typing import Any, Dict, Optional, Union

from Modules.pluginModels import (check_found_plugin_model,
                                  plugin_self_identifier)
from Modules.readAttributes import ReadAttributeRequest_0702_multiplier_divisor
from Modules.tools import get_deviceconf_parameter_value

# Common/ helpers
def decode_boolean(attribute_value: str) -> str:
    """
    Decode a boolean attribute value.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string).

    Returns
    -------
    str
        The first two characters of the attribute, representing the boolean.
    """
    return attribute_value[:2]


def decode_8bit_bitmap(attribute_value: str) -> int:
    """
    Decode an 8-bit bitmap attribute.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string).

    Returns
    -------
    int
        Integer value of the 8-bit bitmap.
    """
    return int(attribute_value[:2], 16)


def decode_16bit_bitmap(attribute_value: str) -> int:
    """
    Decode a 16-bit bitmap attribute.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string).

    Returns
    -------
    int
        Integer value of the 16-bit bitmap.
    """
    return int(attribute_value[:4], 16)


def decode_uint8(attribute_value: str) -> int:
    """
    Decode an unsigned 8-bit integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string).

    Returns
    -------
    int
        Unsigned 8-bit integer value.
    """
    return int(attribute_value[:2], 16)


def decode_16bit_uint(attribute_value: str) -> int:
    """
    Decode a 16-bit unsigned integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string).

    Returns
    -------
    int
        Unsigned 16-bit integer value.
    """
    return struct.unpack("H", struct.pack("H", int(attribute_value[:4], 16)))[0]


def decode_zigbee_24bit_uint(attribute_value: str) -> int:
    """
    Decode a Zigbee 24-bit unsigned integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 6 characters).

    Returns
    -------
    int
        Unsigned 24-bit integer value.
    """
    return struct.unpack("I", struct.pack("I", int("0" + attribute_value, 16)))[0]


def decode_32bit_uint(attribute_value: str) -> int:
    """
    Decode a 32-bit unsigned integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 8 characters).

    Returns
    -------
    int
        Unsigned 32-bit integer value.
    """
    return struct.unpack("I", struct.pack("I", int(attribute_value[:8], 16)))[0]


def decode_zigbee_48bit_uint(attribute_value: str) -> int:
    """
    Decode a Zigbee 48-bit unsigned integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 12 characters).

    Returns
    -------
    int
        Unsigned 48-bit integer value.
    """
    return struct.unpack("Q", struct.pack("Q", int(attribute_value, 16)))[0]


def decode_int8(attribute_value: str) -> int:
    """
    Decode a signed 8-bit integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string).

    Returns
    -------
    int
        Signed 8-bit integer value.
    """
    return int(attribute_value, 16)


def decode_16bit_int(attribute_value: str) -> int:
    """
    Decode a 16-bit signed integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 4 characters).

    Returns
    -------
    int
        Signed 16-bit integer.
    """
    return struct.unpack("h", struct.pack("H", int(attribute_value[:4], 16)))[0]


def decode_zigbee_24bit_int(attribute_value: str) -> int:
    """
    Decode a Zigbee 24-bit signed integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 6 characters).

    Returns
    -------
    int
        Signed 24-bit integer.
    """
    value = int(attribute_value, 16) & 0xFFFFFF  # Mask to 24 bits
    # Check sign bit (0x800000 = 2^23)
    return value - 0x1000000 if value & 0x800000 else value


def decode_32bit_int(attribute_value: str) -> int:
    """
    Decode a 32-bit signed integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 8 characters).

    Returns
    -------
    int
        Signed 32-bit integer.
    """
    return struct.unpack("i", struct.pack("I", int(attribute_value[:8], 16)))[0]


def decode_zigbee_48bit_int(attribute_value: str) -> int:
    """
    Decode a Zigbee 48-bit signed integer.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 12 characters).

    Returns
    -------
    int
        Signed 48-bit integer.
    """
    return struct.unpack("q", struct.pack("Q", int(attribute_value, 16)))[0]


def decode_8bit_enum(attribute_value: str) -> int:
    """
    Decode an 8-bit enumeration value.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 2 characters).

    Returns
    -------
    int
        Enumeration value as integer.
    """
    return int(attribute_value[:2], 16)


def decode_16bit_enum(attribute_value: str) -> int:
    """
    Decode a 16-bit enumeration value.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 4 characters).

    Returns
    -------
    int
        Enumeration value as integer.
    """
    return struct.unpack("h", struct.pack("H", int(attribute_value[:4], 16)))[0]


def decode_xiaomi_float(attribute_value: str) -> float:
    """
    Decode a Xiaomi-specific 32-bit floating-point value.

    Parameters
    ----------
    attribute_value : str
        Raw attribute value (hex string, 8 characters).

    Returns
    -------
    float
        Decoded float value.
    """
    return struct.unpack("f", struct.pack("I", int(attribute_value, 16)))[0]


def _decode_caracter_string(attribute_value: str, handle_errors: bool) -> str:
    """
    Decode a hexadecimal string representing a character string.

    Parameters
    ----------
    attribute_value : str
        The hexadecimal representation of the character string.
    handle_errors : bool
        Whether to handle decoding errors:
        - True: return an empty string on error.
        - False: attempt to decode and replace invalid characters with '?'.

    Returns
    -------
    str
        The decoded character string with trailing null bytes removed.

    Notes
    -----
    - If handle_errors is False, invalid characters are ignored.
    - Trailing null bytes ('\\x00') and surrounding whitespace are stripped.
    """
    try:
        # Attempt standard UTF-8 decoding
        decoded = binascii.unhexlify(attribute_value).decode("utf-8")
    except Exception:
        if handle_errors:
            decoded = ""
        else:
            # Decode ignoring errors and clean up null bytes
            decoded = binascii.unhexlify(attribute_value).decode("utf-8", errors="ignore")

    # Strip trailing nulls and whitespace
    return decoded.replace("\x00", "").strip() if decoded else ""


def decoding_attribute_data(attribute_type: str, attribute_value: str, handle_errors: bool = False) -> Any:
    """
    Decode a Zigbee attribute value based on its attribute type.

    Parameters
    ----------
    attribute_type : str
        Hexadecimal string representing the attribute type.
    attribute_value : str
        Hexadecimal string representing the raw attribute value.
    handle_errors : bool, optional
        Whether to handle errors gracefully (for character strings). Defaults to False.

    Returns
    -------
    Any
        The decoded attribute value. Type depends on attribute type:
        - int for integer/bitmap/enum types
        - float for Xiaomi float
        - str for character strings
        - original hex string if type is unknown

    Notes
    -----
    - Character string types: 0x41, 0x42, 0x43
    - UTC integer types: 0xE1, 0xE2, 0xE3
    - If attribute type is 0x00, the raw value is returned unchanged.
    """
    if not attribute_value:
        return ""

    attr_type_int = int(attribute_type, 16)

    # Mapping of attribute type to decoding functions
    decoding_functions = {
        0x10: decode_boolean,
        0x18: decode_8bit_bitmap,
        0x19: decode_16bit_bitmap,
        0x20: decode_uint8,
        0x21: decode_16bit_uint,
        0x22: decode_zigbee_24bit_uint,
        0x23: decode_32bit_uint,
        0x25: decode_zigbee_48bit_uint,
        0x28: decode_int8,
        0x29: decode_16bit_int,
        0x2A: decode_zigbee_24bit_int,
        0x2B: decode_32bit_int,
        0x2D: decode_zigbee_48bit_int,
        0x30: decode_8bit_enum,
        0x31: decode_16bit_enum,
        0x39: decode_xiaomi_float,
    }

    # Return raw value for type 0x00
    if attr_type_int == 0x00:
        return attribute_value

    # Decode using the corresponding function
    if attr_type_int in decoding_functions:
        return decoding_functions[attr_type_int](attribute_value)

    # Character strings
    if attr_type_int in {0x41, 0x42, 0x43}:
        return _decode_caracter_string(attribute_value, handle_errors)

    # UTC integers
    if attr_type_int in {0xE1, 0xE2, 0xE3}:
        return struct.unpack("i", struct.pack("I", int(attribute_value[:8], 16)))[0]

    # Default: return raw hex string if type not recognized
    return attribute_value


# Used by Cluster 0x0000
def handle_model_name(
    self,
    src_addr: str,
    src_ep: str,
    cluster_id: str,
    attr_id: str,
    attr_type: str,
    attr_size: int,
    device_model: str,
    raw_value: str,
    value: Any,
) -> None:
    """
    Handle a device model name received during Zigbee pairing.

    This function:
        - Cleans up the raw model name.
        - Attempts to normalize it using DeviceConf and plugin logic.
        - Checks if the device is already provisioned.
        - Updates internal device structure and endpoints if necessary.
        - Forces IAS registration if required.

    Parameters
    ----------
    src_addr : str
        Zigbee network address of the device.
    src_ep : str
        Source endpoint ID.
    cluster_id : str
        Cluster ID from which the attribute was received.
    attr_id : str
        Attribute ID for the model name.
    attr_type : str
        Attribute type (used for decoding).
    attr_size : int
        Attribute size in bytes.
    device_model : str
        Model name provided by the device (optional reference).
    raw_value : str
        Raw attribute value from the device.
    value : Any
        Decoded attribute value (may be string or other type).

    Returns
    -------
    None
    """

    log_cat = ["ZclClusters", "Pairing"]

    # Initial log
    self.log.logging(
        log_cat,
        "Debug",
        f"_handle_model_name - {src_addr} / {src_ep} - {cluster_id} {attr_id} "
        f"{attr_type} {attr_size} {value} - {device_model}",
        src_addr,
    )

    # --- 1. Clean and normalize model name
    model_name = _cleanup_model_name(attr_type, raw_value)
    self.log.logging(log_cat, "Debug", f"_handle_model_name - modelName after cleanup: {model_name}")

    model_name = _build_model_name(self, src_addr, model_name)
    self.log.logging(log_cat, "Debug", f"_handle_model_name - modelName after build: {model_name}")

    # --- 2. Initialize Model entry if missing
    self.ListOfDevices.setdefault(src_addr, {}).setdefault("Model", {})

    self.log.logging(
        log_cat,
        "Debug",
        f"_handle_model_name - {cluster_id} / {attr_id} - Reception Model: >{model_name}<",
        src_addr,
    )

    if not model_name:
        return

    # --- 3. Check if device is already provisioned
    if _is_device_already_provisioned(self, src_addr, model_name):
        return

    # --- 4. Handle duplicate or conflicting models
    current_model = self.ListOfDevices[src_addr].get("Model", "")
    if current_model == model_name and current_model in self.DeviceConf:
        self.log.logging(
            log_cat,
            "Debug",
            f"_handle_model_name - {cluster_id} / {attr_id} - no action (duplicate model)",
            src_addr,
        )
        return

    if current_model != model_name and current_model in self.DeviceConf:
        self.log.logging(
            log_cat,
            "Error",
            f"_handle_model_name - {cluster_id} / {attr_id} - no action: "
            f"different model than registered {model_name}",
            src_addr,
        )
        return

    # --- 5. Set model if missing or update from DeviceConf
    if ( current_model in ("", {}) or current_model not in self.DeviceConf and model_name in self.DeviceConf ):
        self.ListOfDevices[src_addr]["Model"] = model_name
    elif current_model in self.DeviceConf:
        model_name = current_model
    # --- 6. Update device structure and force IAS registration if needed
    if _update_data_structutre_based_on_model_name(self, src_addr, model_name) and getattr(self, "iaszonemgt", None):
        self.iaszonemgt.force_IAS_registration_if_needed(src_addr)


def _update_data_structutre_based_on_model_name(
    self,
    src_addr: str,
    model_name: str
) -> bool:
    """
    Update the device data structure based on its model configuration.

    This function:
        - Verifies that the device model exists in DeviceConf.
        - Sets the device's ConfigSource to 'DeviceConf'.
        - Copies Param and Type fields from DeviceConf.
        - Resets existing endpoint data if Type exists.
        - Calls `_upd_data_strut_based_on_model()` to populate endpoint/cluster data.

    Parameters
    ----------
    src_addr : str
        Zigbee network address of the device.
    model_name : str
        Device model identifier (will be normalized from ListOfDevices).

    Returns
    -------
    bool
        True if the device structure is updated, False if the model is unknown.
    """

    log_cat = ["ZclClusters", "Pairing"]

    # Use the model stored in ListOfDevices
    current_model = self.ListOfDevices.get(src_addr, {}).get("Model")
    if current_model not in self.DeviceConf:
        return False

    model_name = current_model
    self.log.logging(
        log_cat,
        "Debug",
        f"_handle_model_name Extract all info from Model: {self.DeviceConf[model_name]}",
        src_addr
    )

    # Avoid re-enrollment if already done from DeviceConf
    if self.ListOfDevices.get(src_addr, {}).get("ConfigSource") == "DeviceConf":
        self.log.logging(
            log_cat,
            "Debug",
            "_handle_model_name Not redoing the DeviceConf enrollment",
            src_addr
        )
        return True

    # Mark config as coming from DeviceConf
    self.ListOfDevices[src_addr]["ConfigSource"] = "DeviceConf"

    # Copy parameters if present
    if "Param" in self.DeviceConf[model_name]:
        self.ListOfDevices[src_addr]["Param"] = dict(self.DeviceConf[model_name]["Param"])

    backup_ep: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None

    # Copy top-level Type if present
    if "Type" in self.DeviceConf[model_name]:
        self.ListOfDevices[src_addr]["Type"] = self.DeviceConf[model_name]["Type"]

        # Reset existing endpoints if any
        if self.ListOfDevices.get(src_addr, {}).get("Ep"):
            self.log.logging(
                log_cat,
                "Debug",
                "_handle_model_name Removing existing received Ep",
                src_addr
            )
            self.ListOfDevices[src_addr]["Ep"] = {}
            self.log.logging(
                log_cat,
                "Debug",
                f"-- Record removed 'Ep': {self.ListOfDevices[src_addr]}",
                src_addr
            )

    # Update the full structure based on the model
    _upd_data_strut_based_on_model(self, src_addr, model_name, backup_ep)

    return True


def _upd_data_strut_based_on_model(
    self,
    src_addr: str,
    model_name: str,
    initial_ep: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
) -> bool:
    """
    Update the device's internal structure based on its model configuration.

    This method:
        - Ensures all endpoints and clusters defined in DeviceConf exist in the device record.
        - Initializes missing attributes from `initial_ep` if provided.
        - Copies endpoint type and color mode information.
        - Logs all updates consistently.

    Parameters
    ----------
    src_addr : str
        Zigbee network address of the device.
    model_name : str
        Device model identifier corresponding to DeviceConf entry.
    initial_ep : dict, optional
        Previously received endpoint data, used to initialize missing attributes.

    Returns
    -------
    bool
        Always returns True to indicate the device structure has been updated.
    """

    log_cat = ["ZclClusters", "Pairing"]

    device_info: Dict[str, Any] = self.ListOfDevices.get(src_addr, {})
    device_conf: Dict[str, Any] = self.DeviceConf.get(model_name, {})

    for ep, ep_conf in device_conf.get("Ep", {}).items():
        # Ensure endpoint exists
        ep_record = device_info.setdefault("Ep", {}).setdefault(ep, {})
        if ep not in device_info["Ep"]:
            self.log.logging(log_cat, "Debug", f"-- Create Endpoint {ep} in record {device_info['Ep']}", src_addr)

        # Process each cluster in endpoint
        for cluster, cluster_conf in ep_conf.items():
            cluster_record = ep_record.setdefault(cluster, {})
            if cluster not in ep_record:
                self.log.logging(log_cat, "Debug", f"----> Cluster: {cluster}", src_addr)

            # Copy initial attributes if missing
            if initial_ep:
                for attr, value in initial_ep.get(ep, {}).get(cluster, {}).items():
                    if not cluster_record.get(attr) or cluster_record[attr] in ("", {}):
                        cluster_record[attr] = value
                        self.log.logging(
                            log_cat,
                            "Debug",
                            f"------> Cluster {cluster} set with Attribute {attr}",
                            src_addr,
                        )

        # Copy endpoint-level properties
        if "Type" in ep_conf:
            ep_record["Type"] = ep_conf["Type"]

        if "ColorMode" in ep_conf:
            color_infos = device_info.setdefault("ColorInfos", {})
            color_infos["ColorMode"] = int(ep_conf["ColorMode"])

    self.log.logging(
        log_cat,
        "Debug",
        f"_handle_model_name Result based on DeviceConf is: {device_info}",
        src_addr,
    )

    return True


def _build_model_name(self, nwk_id: str, model_name: str) -> str:
    """
    Build and normalize a device model name using available information such as:
        - Manufacturer name
        - Manufacturer code
        - Zigbee device ID
        - DeviceConf mappings
        - Plugin identifiers

    The logic attempts several matching strategies in this order:
        1. Special-case models (e.g., "66666")
        2. Direct lookup in DeviceConf using model + manufacturer name
        3. Lookup using concatenation without dash
        4. Lookup using plugin-specific identifiers
        5. Fallback to plugin model detection

    Parameters
    ----------
    nwk_id : str
        The Zigbee network address of the device.
    model_name : str
        The raw or decoded model identifier.

    Returns
    -------
    str
        The best-resolved model name based on heuristics and DeviceConf.
    """

    log_cat = ["ZclClusters", "Pairing"]
    self.log.logging(log_cat, "Debug", f"_build_model_name input: {model_name}", nwk_id)

    # Retrieve known device info safely
    dev_info = self.ListOfDevices.get(nwk_id, {})

    manufacturer_name: str = dev_info.get("Manufacturer Name", "")
    manufacturer_code = dev_info.get("Manufacturer", "")
    zdevice_id = dev_info.get("ZDeviceID")

    # Detail logging
    self.log.logging(log_cat, "Debug", f"manufacturer_name: {manufacturer_name}", nwk_id)
    self.log.logging(log_cat, "Debug", f"manufacturer_code: {manufacturer_code}", nwk_id)
    self.log.logging(log_cat, "Debug", f"zdevice_id: {zdevice_id}", nwk_id)

    # --- 1. Special-case model (Zigbee2MQTT issue reference)
    if model_name in {"66666"}:
        return check_found_plugin_model(
            self,
            model_name,
            manufacturer_name=manufacturer_name,
            manufacturer_code=manufacturer_code,
            device_id=zdevice_id,
        )

    # --- 2. Try direct DeviceConf lookup: "<modelName>-<manufacturer>"
    candidate = f"{model_name}-{manufacturer_name}"
    if candidate in self.DeviceConf:
        return candidate

    # --- 3. Try "<modelName><manufacturer>"
    candidate = f"{model_name}{manufacturer_name}"
    if candidate in self.DeviceConf:
        return candidate

    # --- 4. Try plugin identifiers (custom logic)
    plugin_id = plugin_self_identifier(self, model_name, manufacturer_name)
    if plugin_id:
        return plugin_id

    # --- 5. Fallback to plugin detection logic
    return check_found_plugin_model(
        self,
        model_name,
        manufacturer_name=manufacturer_name,
        manufacturer_code=manufacturer_code,
        device_id=zdevice_id,
    )


def _is_device_already_provisioned(self, nwk_id: str, model_name: str) -> bool:
    """
    Determine whether a device is already provisioned and, if needed,
    update its model and associated configuration.

    A device is considered provisioned if:
      - It exists in ListOfDevices
      - It has one or more endpoints containing a "ClusterType" field

    If the model name differs but the device is provisioned, the model is
    updated and configuration is refreshed using DeviceConf when available.

    Parameters
    ----------
    nwk_id : str
        The Zigbee network address of the device.
    model_name : str
        The model name extracted from incoming attributes.

    Returns
    -------
    bool
        True if the device is already provisioned or updated,
        False if the device looks new/unprovisioned.
    """

    # Retrieve device info or fallback to empty dict
    device_info: Dict[str, Any] = self.ListOfDevices.get(nwk_id, {})

    # Device must have at least one endpoint
    endpoints = device_info.get("Ep")
    if not isinstance(endpoints, dict):
        return False

    # Check each endpoint for provisioning markers
    for ep_id, ep_info in endpoints.items():
        if "ClusterType" not in ep_info:
            continue

        # Log: device is provisioned
        self.log.logging(
            ["ZclClusters", "Pairing"],
            "Debug",
            f"{nwk_id} / Ep {ep_id} - Already provisioned with model '{device_info.get('Model')}'",
            nwk_id,
        )

        # Case 1 — same model: nothing else to do
        if device_info.get("Model") == model_name:
            return True

        # Case 2 — different model: update model name
        self.log.logging(
            ["ZclClusters", "Pairing"],
            "Debug",
            f"{nwk_id} / Ep {ep_id} - Updating model name to '{model_name}'",
            nwk_id,
        )
        device_info["Model"] = model_name

        # Apply configuration if known in DeviceConf
        if model_name in self.DeviceConf:
            model_conf = self.DeviceConf[model_name]

            self.log.logging(
                ["ZclClusters", "Pairing"],
                "Debug",
                f"{nwk_id} / Ep {ep_id} - Applying DeviceConf settings for model '{model_name}'",
                nwk_id,
            )

            device_info["ConfigSource"] = "DeviceConf"
            device_info["Param"] = dict(model_conf.get("Param", {}))
            device_info["CertifiedDevice"] = True

        return True

    # No endpoint qualifies → device not considered provisioned
    return False



def _cleanup_model_name(msg_att_type: str, value: str) -> str:
    """
    Clean and normalize a raw Zigbee model name extracted from an attribute.

    Steps performed:
        - Detects and removes bytes after the first "00" null terminator.
        - Decodes the attribute value using `decoding_attribute_data()`.
        - Removes invalid characters (like '/').
        - Collapses duplicate spaces.
        - Trims surrounding whitespace.

    Parameters
    ----------
    msg_att_type : str
        The ZCL attribute type used for decoding.
    value : str
        The raw hexadecimal or encoded string obtained from the attribute.

    Returns
    -------
    str
        The cleaned model name (may be empty but never None).
    """

    # Defensive: ensure the function *never* crashes on unexpected input.
    value = str(value)

    # Cut the string at the first "00" null-terminator
    null_index = value.find("00")
    if null_index != -1:
        value = value[:null_index]

    # Decode the model name using Zigbee attribute decoding logic
    decoded = decoding_attribute_data(
        msg_att_type,
        value,
        handle_errors=True,
    )

    return (
        (
            decoded.replace("/", "")
            .replace("  ", " ")  # collapse double spaces
            .strip()  # remove leading/trailing whitespace
        )
        if decoded
        else ""
    )


# Used by Cluster 0x0702
def compute_metering_conso(
    self,
    nwk_id: str,
    msg_src_ep: str,
    msg_cluster_id: str,
    msg_attr_id: str,
    raw_value: Union[int, str]
) -> float:
    """
    Compute the metering consumption value for a device.

    Supports multiplier/divisor overrides from DeviceConf and cluster data.

    Parameters
    ----------
    nwk_id : str
        Network ID of the device.
    msg_src_ep : str
        Source endpoint of the message.
    msg_cluster_id : str
        Cluster ID of the message.
    msg_attr_id : str
        Attribute ID indicating type of data (e.g., consumption, power).
    raw_value : int or str
        Raw attribute value (integer or hex string).

    Returns
    -------
    float
        Computed consumption value.
    """

    CONVERSION_FACTORS = {"kW": 1000, "Unitless": 1}

    # --- Normalize raw_value
    if isinstance(raw_value, str):
        raw_value = int(raw_value, 16)

    # --- Retrieve device and cluster data
    device_data = self.ListOfDevices.get(nwk_id, {})
    model_name = device_data.get("Model")
    cluster_data = device_data.get("Ep", {}).get(msg_src_ep, {}).get(msg_cluster_id, {})

    # --- Retrieve device parameters from DeviceConf
    def get_param(key: str, default: int = 1) -> int:
        return int(get_deviceconf_parameter_value(self, model_name, key) or default)

    unit = get_deviceconf_parameter_value(self, model_name, "MeteringUnit") or cluster_data.get("0300", "kW")
    sum_multiplier = get_param("SummationMeteringMultiplier", cluster_data.get("0301", 1))
    sum_divisor = get_param("SummationMeteringDivisor", cluster_data.get("0302", 1))
    power_multiplier = get_param("PowerMeteringMultiplier", cluster_data.get("0301", 1))
    power_divisor = get_param("PowerMeteringDivisor", cluster_data.get("0302", 1))

    # --- Determine multiplier/divisor based on msg_attr_id
    if msg_attr_id == "0000":
        # Summary Metering
        multiplier, divisor = sum_multiplier, sum_divisor
    elif msg_attr_id == "0400":
        # Instant Power
        multiplier, divisor = power_multiplier, power_divisor
    else:
        multiplier, divisor = 1, 1

    # --- Prevent division by zero
    divisor = max(divisor, 1)

    # --- Convert raw value to base units
    conso = (raw_value * CONVERSION_FACTORS.get(unit, 1000)) * multiplier / divisor
    conso = round(conso, 3)

    # --- Log computation
    self.log.logging(
        ["ZclClusters", "Electric"],
        "Debug",
        f"compute_metering_conso - {nwk_id}/{msg_src_ep} Unit: {unit}, "
        f"Multiplier: {multiplier}, Divisor: {divisor}, raw: {raw_value}, result: {conso}",
        nwk_id
    )

    # --- Trigger attribute read if some cluster data missing
    if (
        cluster_data.get("0300") is None and get_deviceconf_parameter_value(self, model_name, "MeteringUnit") is None
        or cluster_data.get("0301") is None and (power_multiplier is None or sum_multiplier is None)
        or cluster_data.get("0302") is None and (power_divisor is None or sum_divisor is None)
    ):
        ReadAttributeRequest_0702_multiplier_divisor(self, nwk_id)

    return conso


def compute_electrical_measurement_conso(self, nwk_id, src_ep, cluster_id, attr_id, raw_value):
    """
    Computes electrical measurement consumption using device-specific multipliers and divisors.

    Parameters:
        nwk_id (str): Network ID of the device.
        src_ep (str): Source endpoint.
        cluster_id (str): Cluster ID.
        attr_id (str): Attribute ID indicating the measurement type.
        raw_value (str | int): Raw measurement value, which may be a hex string.

    Returns:
        float: Computed consumption value, rounded to 3 decimal places.
    """

    self.log.logging(["ZclClusters", "Electric"], "Debug",
                     f"compute_electrical_measurement_conso - {nwk_id}/{src_ep} cluster_id: {cluster_id} attr_id: {attr_id} {raw_value} {type(raw_value)}",
                     nwk_id)

    MULTIPLIER_DIVISOR_MAPPING = {
        '0505': {'multiplier': '0600', 'divisor': '0601', 'custom': 'RMSVoltageDivisor'},   # RMS Voltage
        '0905': {'multiplier': '0600', 'divisor': '0601', 'custom': 'RMSVoltageDivisor'},   # RMS Voltage Phase 2
        '0a05': {'multiplier': '0600', 'divisor': '0601', 'custom': 'RMSVoltageDivisor'},   # RMS Voltage Phase 3

        '0508': {'multiplier': '0602', 'divisor': '0603', 'custom': 'RMSCurrentDivisor'},   # RMS Current
        '0908': {'multiplier': '0602', 'divisor': '0603', 'custom': 'RMSCurrentDivisor'},   # RMS Current Phase 2
        '0a08': {'multiplier': '0602', 'divisor': '0603', 'custom': 'RMSCurrentDivisor'},   # RMS Current Phase 3

        '050b': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Active Power
        '050f': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Puissance soutirée
        '090f': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Puissance soutirée Phase 2
        '0a0f': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Puissance soutirée Phase 3
        
        '0304': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # TotalActivePower 
        '0305': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # TotalReactivePower 
        '0306': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # TotalApparentPower
    }

    if isinstance(raw_value, str):
        raw_value = int(raw_value, 16)

    # Return early if attr_id is not in the mapping
    if attr_id not in MULTIPLIER_DIVISOR_MAPPING:
        self.log.logging(["ZclClusters", "Electric"], "Debug", f"compute_electrical_measurement_conso - {nwk_id}/{src_ep} attr_id: '{attr_id}' not found in Multiplier table", nwk_id)
        return None

    conso = raw_value
    mapping = MULTIPLIER_DIVISOR_MAPPING[attr_id]
    custom_divisor_key = mapping['custom']
    self.log.logging(["ZclClusters", "Electric"], "Debug", f"compute_electrical_measurement_conso - {nwk_id}/{src_ep} conso: {conso} mapping: {mapping} custom_div: {custom_divisor_key}", nwk_id)

    # Retrieve device data
    device_data = self.ListOfDevices.get(nwk_id, {})
    model_name = device_data.get("Model")
    cluster_data = device_data.get("Ep", {}).get(src_ep, {}).get(cluster_id, {})

    # Check for a custom divisor in the device configuration
    custom_divisor = get_deviceconf_parameter_value(self, model_name, custom_divisor_key)
    self.log.logging(["ZclClusters", "Electric"], "Debug", f"compute_electrical_measurement_conso - {nwk_id}/{src_ep} model_name: {model_name} custom_divisor: {custom_divisor}", nwk_id)
     
    if custom_divisor is not None and int(custom_divisor) != 0:
        custom_divisor = int(custom_divisor)
        self.log.logging(["ZclClusters", "Electric"], "Debug",
                         f"compute_electrical_measurement_conso - {nwk_id}/{src_ep} Custom Divisor: {custom_divisor}, raw: {raw_value}, result: {conso}",
                         nwk_id)
        return round(conso / custom_divisor, 3)

    # Retrieve multiplier and divisor from the device attribute list
    multiplier = int(cluster_data.get(mapping['multiplier'], 1))
    divisor = int(cluster_data.get(mapping['divisor'], 1))

    # Ensure multiplier and divisor are not zero (e.g., for Legrand Cable outlets)
    multiplier = multiplier or 1
    divisor = divisor or 1

    conso = round((conso * multiplier) / divisor, 3)

    self.log.logging(["ZclClusters", "Electric"], "Debug",
                     f"compute_electrical_measurement_conso - {nwk_id}/{src_ep} Multiplier: {multiplier}, Divisor: {divisor}, raw: {raw_value}, result: {conso}",
                     nwk_id)

    return conso


# Used by Cluster 0x0102
def CurrentPositionLiftPercentage(self, nwk_id, src_ep, cluster_id, attr_id, raw_value):
    """
    Computes the corrected lift position percentage for a window covering device.

    Parameters:
        nwk_id (str): Network ID of the device.
        src_ep (str): Source endpoint.
        cluster_id (str): Cluster ID.
        attr_id (str): Attribute ID.
        raw_value (str | int): Raw lift percentage value, may be in hexadecimal format.

    Returns:
        int: Corrected lift position percentage (0-100) or None if ignored.
    """

    # Convert raw_value to an integer if it's a hex string
    if isinstance(raw_value, str):
        raw_value = int(raw_value, 16)

    # Retrieve device model
    device_model = self.ListOfDevices.get(nwk_id, {}).get("Model", "")

    # Check if the device configuration specifies to ignore the value ( for TS0302)
    if get_deviceconf_parameter_value(self, device_model, "IgnoreWindowsCoverringValue50"):
        return None

    # Default lift percentage
    lift_percentage = raw_value

    # Check if the shutter position should be inverted (for Legrand "Shutter switch with neutral")
    if get_deviceconf_parameter_value(self, device_model, "WindowsCoverringInverted"):
        lift_percentage = 0 if raw_value > 100 else 100 - raw_value

    # Check if Netatmo shutter inversion setting is enabled
    if self.ListOfDevices.get(nwk_id, {}).get("Param", {}).get("netatmoInvertShutter", False):
        lift_percentage = 0 if raw_value > 100 else 100 - raw_value

    # Log the corrected shutter position
    self.log.logging("ZclClusters", "Debug",
                     f"CurrentPositionLiftPercentage - {cluster_id} - {nwk_id}/{src_ep} - Shutter after correction value: {lift_percentage}",
                     nwk_id)

    return lift_percentage
