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


def _decode_caracter_string( attribute_value, handleErrors):
    """
    Decode a hexadecimal string representing a character string.

    Args:
        attribute_value (str): The hexadecimal representation of the character string.
        handleErrors (bool): Whether to handle decoding errors. If True, returns an empty string on error. 
                             If False, attempts to decode and replaces invalid characters with '?'.

    Returns:
        str: The decoded character string.

    Notes:
        - If handleErrors is False, invalid characters are replaced with '?' in the decoded string.
        - Any trailing null bytes ('\x00') are stripped from the decoded string.
    """

    try:
        decode = binascii.unhexlify(attribute_value).decode("utf-8")
        
    except Exception as e:
        if handleErrors:  # If there is an error we force the result to '' This is used for 0x0000/0x0005
            decode = ""
        else:
            decode = binascii.unhexlify(attribute_value).decode("utf-8", errors="ignore").replace("\x00", "").strip()

    return decode.strip("\x00").strip() if decode else ""


def decoding_attribute_data( AttType, attribute_value, handleErrors=False):
    """
    Decode attribute values based on their attribute type.

    Args:
        AttType (str): The hexadecimal representation of the attribute type.
        attribute_value (str): The hexadecimal representation of the attribute value.
        handleErrors (bool, optional): Whether to handle errors gracefully. Defaults to False.

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
   
    if int(AttType, 16) == 0x00:
        return attribute_value

    if int(AttType, 16) in decoding_functions:
        return decoding_functions[int(AttType, 16)](attribute_value)
    
    if int(AttType, 16) in {0x41, 0x42, 0x43}:  # CharacterString
        return _decode_caracter_string( attribute_value, handleErrors)
    
    if int(AttType, 16) in { 0xe1, 0xe2, 0xe3 } :  # UTC
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


def _is_device_already_provisioned(self, nwkid, modelName):
    # sourcery skip: extract-method, use-next
    device_info = self.ListOfDevices.get(nwkid, {})
    if "Ep" not in device_info:
        return False

    for iterEp, ep_info in device_info["Ep"].items():
        if "ClusterType" in ep_info:
            self.log.logging(["ZclClusters", "Pairing"], "Debug", "%s / %s - %s is already provisioned in Domoticz" % (nwkid, iterEp, modelName), nwkid)
            if device_info.get("Model") == modelName:
                return True

            self.log.logging(["ZclClusters", "Pairing"], "Debug", "%s / %s - Update Model Name %s" % (nwkid, iterEp, modelName), nwkid)
            device_info["Model"] = modelName
            if modelName in self.DeviceConf:
                device_info["ConfigSource"] = "DeviceConf"
                device_info["Param"] = dict(self.DeviceConf[modelName].get("Param", {}))
                device_info["CertifiedDevice"] = True
            return True
    return False
   

def _cleanup_model_name( MsgAttType, value):
    # Stop at the first Null
    idx = 0
    for _ in value:
        if value[idx : idx + 2] == "00":
            break
        idx += 2
    AttrModelName = decoding_attribute_data( MsgAttType, value[:idx], handleErrors=True) 
    modelName = AttrModelName.replace("/", "")
    modelName = modelName.replace("  ", " ")
    return modelName


# Used by Cluster 0x0702
def compute_metering_conso(self, NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value):
    # For Instant Power
    # Device Configuration PowerMeteringMultiplier can overwrite the Multiplier
    # Device Configuration PowerMeteringDivisor can overwrite the Divisor
    # For Summation 
    # Device Configuration SummationMeteringMultiplier can overwrite the Multiplier
    # Device Configuration SummationMeteringDivisor can overwrite the Divisor

    if isinstance(raw_value, str):
        raw_value = int(raw_value,16)

    # Get the Unit, to see if we have Kilo, so then multiply by 1000.
    unit = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "MeteringUnit")
    if unit is None:
        unit = ( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]["0300"] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and "0300" in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else "kW" )
    if unit == "kW":
        # Domoticz expect in Watts
        conso = raw_value * 1000
    elif unit == "Unitless":
        conso = raw_value
    else:
        # We assumed default as kW
        self.log.logging("ZclClusters", "Log", "compute_metering_conso - Unknown %s/%s assuming kW" %( 
            NwkId, MsgSrcEp ), NwkId)
        conso = raw_value * 1000
        
    multiplier = None
    divisor = None
    modelName = self.ListOfDevices[NwkId]["Model"] if "Model" in self.ListOfDevices[NwkId] else None
    # Check if we have a Device configuration overwrite
    if modelName and modelName not in ( '', {} ):
        if MsgAttrID == "0400":
            # Instant Power
            multiplier = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "PowerMeteringMultiplier")
            divisor = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "PowerMeteringDivisor")
        elif MsgAttrID == "0000":
            # Summation
            multiplier = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "SummationMeteringMultiplier")
            divisor = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "SummationMeteringDivisor")

    if multiplier is None:
        # By default Multiplier is assumed to be 1
        multiplier = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]["0301"] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and "0301" in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
    if divisor is None:
        # By default Multiplier is assumed to be 1
        divisor = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]["0302"] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and "0302" in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
    # mulCheck if we have a Device configuration overwrite      
 
    conso = round( (( conso * multiplier ) / divisor ), 3)
    self.log.logging("ZclClusters", "Debug", "compute_metering_conso - %s/%s Unit: %s Multiplier: %s , Divisor: %s , raw: %s result: %s" % (
        NwkId, MsgSrcEp, unit, multiplier, divisor, raw_value, conso), NwkId)
    if ( 
        MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] 
        and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] 
        and ("0301" not in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] or "0302" not in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]
             or "0300" not in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId])
    ):
        ReadAttributeRequest_0702_multiplier_divisor(self,NwkId )
    return conso


def compute_electrical_measurement_conso(self, NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value):
    # ActivePowerDivisor 	
    # RMSVoltageDivisor
    # RMSCurrentDivisor
    self.log.logging("Cluster", "Debug", "compute_electrical_measurement_conso - %s/%s %s %s %s %s" % (
        NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value, type(raw_value)), NwkId)

    MULTIPLIER_DIVISOR_MATRIX = {
        '0505': { 'multiplier': '0600', 'divisor': '0601', 'custom': 'RMSVoltageDivisor'},    # RMSVoltage
        '0508': { 'multiplier': '0602', 'divisor': '0603', 'custom': 'RMSCurrentDivisor'},    # RMSCurrent
        '050b': { 'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},   # ActivePower
    }
    if isinstance( raw_value, str):
        raw_value = int(raw_value,16)

    conso = raw_value
    multiplier = None
    divisor = None

    if MsgAttrID not in MULTIPLIER_DIVISOR_MATRIX:
        return
    
    # Check if we have a Custom divisor, we assumed multiplier = 1
    custom = MULTIPLIER_DIVISOR_MATRIX[ MsgAttrID ]['custom']
    divisor = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], custom)
    if divisor is not None and int(divisor ) != 0:
        divisor = int(divisor )
        self.log.logging("ZclClusters", "Debug", "compute_electrical_measurement_conso - %s/%s Custom Divisor: %s , raw: %s result: %s" % (
            NwkId, MsgSrcEp, divisor, raw_value, conso), NwkId)
        return round( (( conso ) / divisor ), 3)
        
    multiplier_attribute = MULTIPLIER_DIVISOR_MATRIX[ MsgAttrID ]['multiplier']
    divisor_attribute = MULTIPLIER_DIVISOR_MATRIX[ MsgAttrID ]['divisor']
        
    # By default Multiplier is assumed to be 1
    multiplier = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId][ multiplier_attribute ] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and multiplier_attribute in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
    # By default Multiplier is assumed to be 1
    divisor = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId][ divisor_attribute ] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and divisor_attribute in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )

    # compute_electrical_measurement_conso Sometimes device Attributes are 0 Exemple Legrand Cable outlet Attributes 0600,0601,0602,0603 Default to 1 to avoid conso=0 or division by 0
    if multiplier==0:
        multiplier=1
    if divisor==0:
        divisor=1
    conso = round( (( conso * multiplier ) / divisor ), 3)

    self.log.logging("ZclClusters", "Debug", "compute_electrical_measurement_conso - %s/%s Multiplier: %s , Divisor: %s , raw: %s result: %s" % (
        NwkId, MsgSrcEp, multiplier, divisor, raw_value, conso), NwkId)

    return conso

# Used by Cluster 0x0102

def CurrentPositionLiftPercentage(self, NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value):
    if isinstance( raw_value, str):
        raw_value = int(raw_value,16)

    if get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "IgnoreWindowsCoverringValue50"):
        # TS0302
        return
    
    value = raw_value
    if get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "WindowsCoverringInverted"):
        # "TS0302", "1GANGSHUTTER1", "NHPBSHUTTER1"
        value = 0 if raw_value > 100 else 100 - raw_value
        
    if "Param" in self.ListOfDevices[NwkId] and "netatmoInvertShutter" in self.ListOfDevices[NwkId]["Param"] and self.ListOfDevices[NwkId]["Param"]["netatmoInvertShutter"]:
        # "Shutter switch with neutral"
        value = 0 if raw_value > 100 else 100 - raw_value

    self.log.logging( "ZclClusters", "Debug", "CurrentPositionLiftPercentage - %s - %s/%s - Shutter after correction value: %s" % (
        MsgClusterId, NwkId, MsgSrcEp, value), NwkId, )

    return value
