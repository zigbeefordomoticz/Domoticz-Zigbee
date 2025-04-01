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

import binascii
import struct

from Modules.pluginModels import (check_found_plugin_model,
                                  plugin_self_identifier)
from Modules.readAttributes import ReadAttributeRequest_0702_multiplier_divisor
from Modules.tools import get_deviceconf_parameter_value

# Common/ helpers

def decode_boolean(attribute_value):
    return attribute_value[:2]


def decode_8bit_bitmap(attribute_value):
    return int(attribute_value[:8], 16)


def decode_16bit_bitmap(attribute_value):
    return int(attribute_value[:4], 16)


def decode_uint8(attribute_value):
    return int(attribute_value[:2], 16)


def decode_16bit_uint(attribute_value):
    return struct.unpack("H", struct.pack("H", int(attribute_value[:4], 16)))[0]


def decode_zigbee_24bit_uint(attribute_value):
    return struct.unpack("I", struct.pack("I", int("0" + attribute_value, 16)))[0]


def decode_32bit_uint(attribute_value):
    return struct.unpack("I", struct.pack("I", int(attribute_value[:8], 16)))[0]


def decode_zigbee_48bit_uint(attribute_value):
    return struct.unpack("Q", struct.pack("Q", int(attribute_value, 16)))[0]


def decode_int8(attribute_value):
    return int(attribute_value, 16)


def decode_16bit_int(attribute_value):
    return struct.unpack("h", struct.pack("H", int(attribute_value[:4], 16)))[0]


def decode_zigbee_24bit_int(attribute_value):
    signed_int = struct.unpack("i", struct.pack("I", int("0" + attribute_value, 16)))[0]
    if (signed_int & 0x00800000) != 0:
        signed_int -= 0x01000000
    return signed_int


def decode_32bit_int(attribute_value):
    return struct.unpack("i", struct.pack("I", int(attribute_value[:8], 16)))[0]


def decode_zigbee_48bit_int(attribute_value):
    return struct.unpack("q", struct.pack("Q", int(attribute_value, 16)))[0]


def decode_8bit_enum(attribute_value):
    return int(attribute_value[:2], 16)


def decode_16bit_enum(attribute_value):
    return struct.unpack("h", struct.pack("H", int(attribute_value[:4], 16)))[0]


def decode_xiaomi_float(attribute_value):
    return struct.unpack("f", struct.pack("I", int(attribute_value, 16)))[0]


def _decode_caracter_string( attribute_value, handle_errors):
    """
    Decode a hexadecimal string representing a character string.

    Args:
        attribute_value (str): The hexadecimal representation of the character string.
        handle_errors (bool): Whether to handle decoding errors. If True, returns an empty string on error.
                             If False, attempts to decode and replaces invalid characters with '?'.

    Returns:
        str: The decoded character string.

    Notes:
        - If handle_errors is False, invalid characters are replaced with '?' in the decoded string.
        - Any trailing null bytes ('\x00') are stripped from the decoded string.
    """

    try:
        decode = binascii.unhexlify(attribute_value).decode("utf-8")
        
    except Exception as _:
        if handle_errors:  # If there is an error we force the result to '' This is used for 0x0000/0x0005
            decode = ""
        else:
            decode = binascii.unhexlify(attribute_value).decode("utf-8", errors="ignore").replace("\x00", "").strip()

    return decode.strip("\x00").strip() if decode else ""


def decoding_attribute_data( attribute_type, attribute_value, handle_errors=False):
    """
    Decode attribute values based on their attribute type.

    Args:
        attribute_type (str): The hexadecimal representation of the attribute type.
        attribute_value (str): The hexadecimal representation of the attribute value.
        handle_errors (bool, optional): Whether to handle errors gracefully. Defaults to False.

    Returns:
        Any: The decoded attribute value.

    Raises:
        NotImplementedError: If the attribute type is not supported.
    """

    if len(attribute_value) == 0:
        return ""
 
    decoding_functions = {
        0x00: attribute_value,
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
        0x39: decode_xiaomi_float
    }
   
    if int(attribute_type, 16) == 0x00:
        return attribute_value

    if int(attribute_type, 16) in decoding_functions:
        return decoding_functions[int(attribute_type, 16)](attribute_value)
    
    if int(attribute_type, 16) in {0x41, 0x42, 0x43}:  # CharacterString
        return _decode_caracter_string( attribute_value, handle_errors)
    
    if int(attribute_type, 16) in { 0xe1, 0xe2, 0xe3 } :  # UTC
        return struct.unpack("i", struct.pack("I", int(attribute_value[:8], 16)))[0]
    return attribute_value


# Used by Cluster 0x0000

def handle_model_name( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, device_model, rawvalue, value ):
    self.log.logging( [ "ZclClusters", "Pairing"], "Debug", "_handle_model_name - %s / %s - %s %s %s %s %s - %s" % (
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, value, device_model), MsgSrcAddr, )
    
    modelName = _cleanup_model_name( MsgAttType, rawvalue)
    self.log.logging( [ "ZclClusters", "Pairing"], "Debug", "_handle_model_name - modelName after cleanup %s" % modelName)
    
    modelName = _build_model_name( self, MsgSrcAddr, modelName)
    self.log.logging( [ "ZclClusters", "Pairing"], "Debug", "_handle_model_name - modelName after build model name %s" % modelName)
    
    # Here the Device is not yet provisioned
    self.ListOfDevices[MsgSrcAddr].setdefault("Model", {})

    self.log.logging( [ "ZclClusters", "Pairing"], "Debug", "_handle_model_name - %s / %s - Recepion Model: >%s<" % (
        MsgClusterId, MsgAttrID, modelName), MsgSrcAddr, )
    if modelName == "":
        return

    if _is_device_already_provisioned( self, MsgSrcAddr, modelName):
        return

    if self.ListOfDevices[MsgSrcAddr]["Model"] == modelName and self.ListOfDevices[MsgSrcAddr]["Model"] in self.DeviceConf:
        # This looks like a Duplicate, just drop
        self.log.logging([ "ZclClusters", "Pairing"], "Debug", "_handle_model_name - %s / %s - no action" % (
            MsgClusterId, MsgAttrID), MsgSrcAddr)
        return

    if self.ListOfDevices[MsgSrcAddr]["Model"] != modelName and self.ListOfDevices[MsgSrcAddr]["Model"] in self.DeviceConf:
        # We ae getting a different Model Name, let's log an drop
        self.log.logging( [ "ZclClusters", "Pairing"], "Error", "_handle_model_name - %s / %s - no action as it is a different Model Name than registered %s" % (
            MsgClusterId, MsgAttrID, modelName), MsgSrcAddr, )
        return

    if self.ListOfDevices[MsgSrcAddr]["Model"] in ( "", {}):
        self.ListOfDevices[MsgSrcAddr]["Model"] = modelName
        
    elif self.ListOfDevices[MsgSrcAddr]["Model"] in self.DeviceConf:
        modelName = self.ListOfDevices[MsgSrcAddr]["Model"]
        
    elif modelName in self.DeviceConf:
        self.ListOfDevices[MsgSrcAddr]["Model"] = modelName

    if _update_data_structutre_based_on_model_name( self, MsgSrcAddr, modelName) and self.iaszonemgt:
        self.iaszonemgt.force_IAS_registration_if_needed(MsgSrcAddr)


def _update_data_structutre_based_on_model_name( self, MsgSrcAddr, modelName):
    # Let's see if this model is known in DeviceConf. If so then we will retreive already the Eps
    if self.ListOfDevices[MsgSrcAddr]["Model"] not in self.DeviceConf: 
        return False

    modelName = self.ListOfDevices[MsgSrcAddr]["Model"]
    self.log.logging([ "ZclClusters", "Pairing"], "Debug", "_handle_model_name Extract all info from Model : %s" % self.DeviceConf[modelName], MsgSrcAddr)

    if "ConfigSource" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["ConfigSource"] == "DeviceConf":
        self.log.logging([ "ZclClusters", "Pairing"], "Debug", "_handle_model_name Not redoing the DeviceConf enrollement", MsgSrcAddr)
        return True

    self.ListOfDevices[MsgSrcAddr]["ConfigSource"] = "DeviceConf"
    if "Param" in self.DeviceConf[modelName]:
        self.ListOfDevices[MsgSrcAddr]["Param"] = dict(self.DeviceConf[modelName]["Param"])

    _BackupEp = None
    if "Type" in self.DeviceConf[modelName]:  # If type exist at top level : copy it
        self.ListOfDevices[MsgSrcAddr]["Type"] = self.DeviceConf[modelName]["Type"]

        if "Ep" in self.ListOfDevices.get(MsgSrcAddr, {}):
            self.log.logging([ "ZclClusters", "Pairing"], "Debug", "_handle_model_name Removing existing received Ep", MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]["Ep"] = {}  # Reset the "Ep" key
            self.log.logging([ "ZclClusters", "Pairing"], "Debug", "-- Record removed 'Ep' %s" % (self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

    _upd_data_strut_based_on_model(self, MsgSrcAddr, modelName, _BackupEp)


def _upd_data_strut_based_on_model(self, MsgSrcAddr, modelName, initial_ep):
    device_info = self.ListOfDevices[MsgSrcAddr]
    device_conf = self.DeviceConf[modelName]

    for ep, ep_info in device_conf.get("Ep", {}).items():
        if ep not in device_info["Ep"]:
            device_info["Ep"][ep] = {}
            self.log.logging([ "ZclClusters", "Pairing"], "Debug", "-- Create Endpoint %s in record %s" % (ep, device_info["Ep"]), MsgSrcAddr)

        for cluster, cluster_info in ep_info.items():
            if cluster not in device_info["Ep"][ep]:
                device_info["Ep"][ep][cluster] = {}
                self.log.logging([ "ZclClusters", "Pairing"], "Debug", "----> Cluster: %s" % cluster, MsgSrcAddr)

            if initial_ep and ep in initial_ep and cluster in initial_ep[ep]:
                for attr, value in initial_ep[ep][cluster].items():
                    if not device_info["Ep"][ep][cluster].get(attr) or device_info["Ep"][ep][cluster][attr] in ["", {}]:
                        device_info["Ep"][ep][cluster][attr] = value
                        self.log.logging([ "ZclClusters", "Pairing"], "Debug", "------> Cluster %s set with Attribute %s" % (cluster, attr), MsgSrcAddr)

        if "Type" in ep_info:
            device_info["Ep"][ep]["Type"] = ep_info["Type"]
        if "ColorMode" in ep_info:
            if "ColorInfos" not in device_info:
                device_info["ColorInfos"] = {}
            device_info["ColorInfos"]["ColorMode"] = int(ep_info["ColorMode"])

    self.log.logging([ "ZclClusters", "Pairing"], "Debug", "_handle_model_name Result based on DeviceConf is: %s" % str(device_info), MsgSrcAddr)
    return True


def _build_model_name( self, nwkid, modelName):

    self.log.logging([ "ZclClusters", "Pairing"], "Debug", f"_build_model_name  {modelName}", nwkid)

    manufacturer_name = self.ListOfDevices[nwkid].get("Manufacturer Name", "")
    manuf_code = self.ListOfDevices[nwkid].get("Manufacturer", "")
    zdevice_id = self.ListOfDevices[nwkid].get("ZDeviceID", None)

    self.log.logging([ "ZclClusters", "Pairing"], "Debug", f"_build_model_name  manufacturer_name: {manufacturer_name}", nwkid)
    self.log.logging([ "ZclClusters", "Pairing"], "Debug", f"_build_model_name  manuf_code: {manuf_code}", nwkid)
    self.log.logging([ "ZclClusters", "Pairing"], "Debug", f"_build_model_name  zdevice_id: {zdevice_id}", nwkid)

    if modelName in ( '66666', ):
        #  https://github.com/Koenkk/zigbee2mqtt/issues/4338
        return check_found_plugin_model( self, modelName, manufacturer_name=manufacturer_name, manufacturer_code=manuf_code, device_id=zdevice_id)

    # Try to check if the Model name is in the DeviceConf list ( optimised devices)
    if modelName + '-' + manufacturer_name in self.DeviceConf:
        return modelName + '-' + manufacturer_name

    if modelName + manufacturer_name in self.DeviceConf:
        return modelName + manufacturer_name

    # If not found, let see if the model name can be extracted from the (ModelName, ManufacturerName) tuple set in the Conf file as Identifier
    plugin_identifier = plugin_self_identifier( self, modelName, manufacturer_name)
    if plugin_identifier:
        return plugin_identifier

    return check_found_plugin_model( self, modelName, manufacturer_name=manufacturer_name, manufacturer_code=manuf_code, device_id=zdevice_id)


def _is_device_already_provisioned(self, nwk_id, model_name):
    """
    Checks if the device is already provisioned in the system. If the device exists, updates its model name and configuration if necessary.

    Parameters:
        nwk_id (str): The network ID of the device.
        model_name (str): The model name of the device.

    Returns:
        bool: True if the device is provisioned (or updated), False otherwise.
    """

    # Get device info using the network ID
    device_info = self.ListOfDevices.get(nwk_id, {})

    # If the device has no endpoints, it's not provisioned
    if "Ep" not in device_info:
        return False

    # Iterate over each endpoint to check the device's provisioning status
    for ep_id, ep_info in device_info["Ep"].items():
        if "ClusterType" in ep_info:
            self.log.logging(
                ["ZclClusters", "Pairing"],
                "Debug",
                f"{nwk_id} / {ep_id} - {model_name} is already provisioned in Domoticz",
                nwk_id
            )

            # If the device model matches, it's considered provisioned
            if device_info.get("Model") == model_name:
                return True

            # Log the model name update and apply the new configuration
            self.log.logging(
                ["ZclClusters", "Pairing"],
                "Debug",
                f"{nwk_id} / {ep_id} - Update Model Name {model_name}",
                nwk_id
            )

            # Update device information with the new model name
            device_info["Model"] = model_name

            # If the model is in DeviceConf, update its configuration
            if model_name in self.DeviceConf:
                device_info["ConfigSource"] = "DeviceConf"
                device_info["Param"] = dict(self.DeviceConf[model_name].get("Param", {}))
                device_info["CertifiedDevice"] = True

            return True

    # If no matching endpoint found or model was not updated
    return False


def _cleanup_model_name(msg_att_type, value):
    """
    Cleans up the model name by decoding attribute data and removing any null values or extra spaces.

    Parameters:
        msg_att_type (str): The message attribute type for decoding.
        value (str): The raw attribute value as a string.

    Returns:
        str: The cleaned-up model name.
    """

    # Find the index of the first "00" (null) in the value string
    null_index = value.find("00")

    # If no "00" found, use the entire string
    if null_index != -1:
        value = value[:null_index]

    # Decode the attribute data before processing
    attr_model_name = decoding_attribute_data(msg_att_type, value, handle_errors=True)

    return attr_model_name.replace("/", "").replace("  ", " ")


# Used by Cluster 0x0702
def compute_metering_conso(self, nwk_id, msg_src_ep, msg_cluster_id, msg_attr_id, raw_value):
    """
    Compute the metering consumption value based on device configuration.

    Parameters:
    - nwk_id (str): Network ID of the device.
    - msg_src_ep (str): Source endpoint of the message.
    - msg_cluster_id (str): Cluster ID of the message.
    - msg_attr_id (str): Attribute ID indicating the type of data.
    - raw_value (int or str): Raw metering value (hex string or integer).

    Returns:
    - float: Computed consumption value.
    """

    CONVERSION_FACTORS = {
        "kW": 1000,  # Convert to Watts
        "Unitless": 1  # No conversion needed
    }

    if isinstance(raw_value, str):
        raw_value = int(raw_value, 16)

    # Retrieve device data
    device_data = self.ListOfDevices.get(nwk_id, {})
    model_name = device_data.get("Model")
    cluster_data = device_data.get("Ep", {}).get(msg_src_ep, {}).get(msg_cluster_id, {})

    # Checking if we have some setting to overwrite the "0300", "0301", "0302" attributes
    unit_metering = get_deviceconf_parameter_value(self, model_name, "MeteringUnit")  # 0x0300
    sum_multiplier = get_deviceconf_parameter_value(self, model_name, "SummationMeteringMultiplier")  # 0x0301
    sum_divisor = get_deviceconf_parameter_value(self, model_name, "SummationMeteringDivisor")    # 0x0302

    power_multiplier = get_deviceconf_parameter_value(self, model_name, "PowerMeteringMultiplier")    # 0x0301
    power_divisor = get_deviceconf_parameter_value(self, model_name, "PowerMeteringDivisor")    # 0x0302


    # Determine unit of measurement, defaulting to "kW"
    unit = unit_metering or cluster_data.get("0300", "kW")

    conso = raw_value * CONVERSION_FACTORS.get(unit, 1000)  # Default to kW conversion
    if unit not in CONVERSION_FACTORS:
        self.log.logging(["ZclClusters", "Electric"], "Log", f"compute_metering_conso - Unknown {nwk_id}/{msg_src_ep} assuming kW", nwk_id)

    # Check for device-specific multiplier/divisor overrides
    multiplier, divisor = None, None
    if model_name:
        if msg_attr_id == "0000":
            multiplier = sum_multiplier
            divisor = sum_divisor

        elif msg_attr_id == "0400":
            multiplier = power_multiplier
            divisor = power_divisor

    # Retrieve default multiplier and divisor if not set
    multiplier = int(cluster_data.get("0301", 1)) if multiplier is None else multiplier
    divisor = int(cluster_data.get("0302", 1)) if divisor is None else divisor

    # Compute final consumption value
    conso = round((conso * multiplier) / divisor, 3)

    self.log.logging(["ZclClusters", "Electric"], "Debug",
                     f"compute_metering_conso - {nwk_id}/{msg_src_ep} Unit: {unit}, "
                     f"Multiplier: {multiplier}, Divisor: {divisor}, raw: {raw_value}, result: {conso}", nwk_id)

    if (
        cluster_data.get("0300") is None and unit_metering is None
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
        '0508': {'multiplier': '0602', 'divisor': '0603', 'custom': 'RMSCurrentDivisor'},   # RMS Current
        '050b': {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Active Power
        "050f": {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Puissance soutirée
        "090b": {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Puissance soutirée Phase 2
        "050a": {'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},  # Puissance soutirée Phase 3
    }

    if isinstance(raw_value, str):
        raw_value = int(raw_value, 16)

    # Return early if attr_id is not in the mapping
    if attr_id not in MULTIPLIER_DIVISOR_MAPPING:
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