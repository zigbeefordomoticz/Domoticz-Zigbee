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
import json
from os import listdir
from os.path import isdir, isfile, join
from pathlib import Path

from DevicesModules import FUNCTION_MODULE, FUNCTION_WITH_ACTIONS_MODULE
from Modules.batterieManagement import UpdateBatteryAttribute
from Modules.domoMaj import MajDomoDevice
from Modules.tools import (checkAndStoreAttributeValue,
                           get_device_config_param, get_deviceconf_parameter_value,
                           getAttributeValue,
                           store_battery_percentage_time_stamp,
                           store_battery_voltage_time_stamp)
from Modules.zclClusterHelpers import (decoding_attribute_data,
                                       handle_model_name)

# "ActionList":
#   check_store_value - check the value and store in the corresponding data strcuture entry
#   upd_domo_device - trigger update request in domoticz
#   store_specif_attribute - Store the data value in self.ListOfDevices[ nwkid ][_storage_specificlvl1 ][_storage_specificlvl2][_storage_specificlvl3]

# "ActionList":
#   check_store_value - check the value and store in the corresponding data strcuture entry
#   upd_domo_device - trigger update request in domoticz
#   store_specif_attribute - Store the data value in self.ListOfDevices[ nwkid ][_storage_specificlvl1 ][_storage_specificlvl2][_storage_specificlvl3]

CHECK_AND_STORE = "check_store_value"
CHECK_AND_STORE_RAW = "check_store_raw_value"
STORE_SPECIFIC_ATTRIBUTE = "store_specif_attribute"
BASIC_MODEL_NAME = "basic_model_name"

STORE_SPECIFIC_PLACE_LVL1 = "SpecifStoragelvl1"
STORE_SPECIFIC_PLACE_LVL2 = "SpecifStoragelvl2"
STORE_SPECIFIC_PLACE_LVL3 = "SpecifStoragelvl3"
UPDATE_DOMO_DEVICE = "upd_domo_device"
UPDATE_BATTERY = "update_battery"
UPDATE_BATTERY_VOLTAGE = "update_battery_voltage"
UPDATE_BATTERY_PERCENTAGE = "update_battery_percentage"

ACTIONS_TO_FUNCTIONS = {
    CHECK_AND_STORE: checkAndStoreAttributeValue,
    UPDATE_DOMO_DEVICE: MajDomoDevice
}

def process_cluster_attribute_response( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, ):
    
    self.log.logging("ZclClusters", "Debug", "Foundation Cluster - Nwkid: %s Ep: %s Cluster: %s Attribute: %s Type: %s Data: %s Source: %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgClusterData, Source), nwkid=MsgSrcAddr)

    device_model = _get_model_name( self, MsgSrcAddr)
    raw_value = decoding_attribute_data( MsgAttType, MsgClusterData)
    value = raw_value
    _name = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Name", model=device_model)
    _datatype = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DataType", model=device_model)
    _manuf_specific_cluster = _cluster_manufacturer_function(self, MsgSrcEp, MsgClusterId, MsgAttrID, model=device_model)
    
    if _manuf_specific_cluster is None and _datatype and _datatype != MsgAttType:
        # When ManufSpecificCluster, do not check DataType as we don't have the info
        self.log.logging("ZclClusters", "Log", "process_cluster_attribute_response - %s/%s %s - %s DataType: %s miss-match with expected %s" %( 
            MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, _datatype ), nwkid=MsgSrcAddr)
    
    
    # Do we have to use a manufacturer specific function, and then skip everything else
    _we_need_raw_data = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ManufRawData", model=device_model)  # Mainly for Xiaomi
    if _manuf_specific_cluster is not None and _manuf_specific_cluster in FUNCTION_WITH_ACTIONS_MODULE:
        if _we_need_raw_data:
            value = MsgClusterData
        func = FUNCTION_WITH_ACTIONS_MODULE[ _manuf_specific_cluster ]
        func( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value )
        formated_logging( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, device_model, _name, _datatype, "", "", "", _manuf_specific_cluster, "", "", value)
        return

    # More standard
    _force_value = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ValueOverwrite", model=device_model)
    if _force_value is not None:
        value = _force_value
    
    _special_values = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecialValues", model=device_model)
    if _special_values is not None:
        check_special_values( self, value, MsgAttType, _special_values )
    
    _ranges = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Range", model=device_model )
    if _ranges is not None:
        checking_ranges = _check_range( self, value, MsgAttType, _ranges, )
        if checking_ranges is not None and not checking_ranges:
            _context = {
                "Source": str(Source),
                "Model": str(device_model),
                "MsgClusterId": str(MsgClusterId),
                "MsgSrcEp": str(MsgSrcEp),
                "MsgAttrID": str(MsgAttrID),
                "MsgAttType": str(MsgAttType),
                "MsgAttSize": str(MsgAttSize),
                "MsgClusterData": str(MsgClusterData),
                "checking_ranges": str(checking_ranges),
                "ranges": str(_ranges),
            }
            if self.pluginconf.pluginConf["TrackingEraticValue"]:
                self.log.logging("ZclClusters", "Error", "Warning - %s/%s %s %s . value out of ranges : %s -> %s" %(
                    MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value, str(_ranges) ),nwkid=MsgSrcAddr, context=_context )

            # As the value is out of range, it is not a valid value , so just stop the processing here
            return
    
    _eval_inputs = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalExpCustomVariables", model=device_model)
    _function = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalFunc", model=device_model)
    _eval_formula = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalExp", model=device_model )
    _manuf_specific_function = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ManufSpecificFunc", model=device_model)
    _decoding_value = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DecodedValueList", model=device_model)
    self.log.logging("ZclClusters", "Debug", "compute_attribute_value - _decoding_value: %s  value: %s" %( _decoding_value, str(value) ))
    
    if _decoding_value is not None and str(value) in _decoding_value:
        value = _decoding_value[ str(value) ]

    elif _manuf_specific_function is not None and _manuf_specific_function in FUNCTION_WITH_ACTIONS_MODULE:
        func = FUNCTION_WITH_ACTIONS_MODULE[ _manuf_specific_function ]
        func( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value )

    elif _eval_formula is not None or _function is not None:
        value = compute_attribute_value( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value, _eval_inputs, _eval_formula, _function)

    _action_list = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ActionList", model=device_model )
    formated_logging( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, device_model, _name, _datatype, _ranges, _special_values, _eval_formula, _action_list, _eval_inputs, _force_value, value)
    debug_logging(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value)
    
    if value is None:
        self.log.logging("ZclClusters", "Debug", "---> Value is None while raw: %s decoding: %s eval_function: %s , eval_formula: %s" %(raw_value, _decoding_value, _function, _eval_formula), nwkid=MsgSrcAddr)
        return
    
    if _action_list is None:
        self.log.logging("ZclClusters", "Debug", "---> No Action", nwkid=MsgSrcAddr)
        return
    
    for data_action in _action_list:
        self.log.logging("ZclClusters", "Debug", "---> Data Action: %s" %data_action, nwkid=MsgSrcAddr)
        
        if data_action == CHECK_AND_STORE_RAW:
            # This is particularly true for Battery Voltage, where the UpdateBatteryAttribute() relys on deci-volts
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value)
            
        elif data_action == CHECK_AND_STORE:
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
            
        elif data_action in ( UPDATE_BATTERY, UPDATE_BATTERY_VOLTAGE, UPDATE_BATTERY_PERCENTAGE):
            UpdateBatteryAttribute(self, Devices, MsgSrcAddr, MsgSrcEp)
            if data_action == UPDATE_BATTERY_PERCENTAGE:
                store_battery_percentage_time_stamp( self, MsgSrcAddr)
            elif data_action == UPDATE_BATTERY_VOLTAGE:
                store_battery_voltage_time_stamp( self, MsgSrcAddr)

        elif data_action == UPDATE_DOMO_DEVICE and majdomodevice_possiblevalues( self, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ):
            if (
                MsgClusterId == "0006"
                and MsgAttrID == "0000"
                and get_deviceconf_parameter_value(self, device_model, "TUYA_REMOTE", return_default=None)
            ):
                # Stateless Tuya button remotes (TS0041/TS0042/TS0043/TS0044/TS004F...) report their
                # real clicks exclusively via the manufacturer-specific 0xFD/0xFC commands (handled in
                # Decode8095), never via a plain OnOff attribute report. This report is just the
                # device's own idle heartbeat and carries no new information; forwarding it would force
                # a spurious Domoticz widget update (and re-fire any bound automation) on every report.
                self.log.logging(
                    "ZclClusters",
                    "Debug",
                    "process_cluster_attribute_response - dropping OnOff attribute report from Tuya remote %s/%s (Value: %s)" % (MsgSrcAddr, MsgSrcEp, value),
                    nwkid=MsgSrcAddr,
                )
            else:
                action_majdomodevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value )
            
        elif data_action == STORE_SPECIFIC_ATTRIBUTE:
            _storage_specificlvl1 = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, STORE_SPECIFIC_PLACE_LVL1, model=device_model )
            _storage_specificlvl2 = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, STORE_SPECIFIC_PLACE_LVL2, model=device_model )
            _storage_specificlvl3 = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, STORE_SPECIFIC_PLACE_LVL3, model=device_model )
            store_value_in_specif_storage( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value, _storage_specificlvl1, _storage_specificlvl2, _storage_specificlvl3)
            
        elif data_action == BASIC_MODEL_NAME:
            handle_model_name( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, device_model, MsgClusterData, value )


def _read_zcl_cluster( self, cluster_filename ):
    with open(cluster_filename, "rt", encoding='utf-8') as handle:
        try:
            return json.load(handle)
        except ValueError as e:
            self.log.logging("ZclClusters", "Error", "--> JSON readZclClusters: %s load failed with error: %s" % (cluster_filename, str(e)))
            return None
            
        except Exception as e:
            self.log.logging("ZclClusters", "Error", "--> JSON readZclClusters: %s load general error: %s" % (cluster_filename, str(e)))
            return None
    return None


def _check_range( self, value, datatype, _range):
    if len(_range) != 2:
        self.log.logging("ZclClusters", "Error", " . Incorrect range %s" %str(_range))
        return None
    
    if isinstance(_range[0], int) and isinstance(_range[1], int):
        _range1 = _range[0]
        _range2 = _range[1]
    else:
        _range1 = decoding_attribute_data( datatype, _range[0])
        _range2 = decoding_attribute_data( datatype, _range[1])
    
    if _range1 < _range2:
        return _range1 <= value <= _range2
    
    if _range1 > _range2:
        return _range1 >= value >= _range2


def _get_model_name( self, nwkid):

    if "Model" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Model"] not in ( '', {}):
        return self.ListOfDevices[ nwkid ]["Model"]
    return None


def _cluster_manufacturer_function(self, ep, cluster, attribute, model):

    if is_cluster_specific_config(self, model, ep, cluster):
        manuf_specific_function = _cluster_specific_attribute_retrieval( self, model, ep, cluster, attribute, "ManufSpecificFunc" )
        if manuf_specific_function:
            return manuf_specific_function
        
        if "ManufSpecificCluster" in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]:
            return self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["ManufSpecificCluster"]

    # Let's try in the Generic cluster
    if cluster in self.readZclClusters and "ManufSpecificCluster" in self.readZclClusters[ cluster ]:
        # We have a Manufacturer Specific cluster
        return self.readZclClusters[ cluster ]["ManufSpecificCluster"]

    return None
 
    
def _cluster_zcl_attribute_retrieval( self, cluster, attribute, parameter, MsgSrcAddr=None ):

    #self.log.logging("ZclClusters", "Debug", " . _cluster_zcl_attribute_retrieval %s %s %s" %(
        # cluster, attribute, parameter), nwkid = MsgSrcAddr)

    if cluster not in self.readZclClusters:
        self.log.logging("ZclClusters", "Error", " . _cluster_zcl_attribute_retrieval %s not found in %s" %(
            cluster, str(self.readZclClusters)), nwkid=MsgSrcAddr)
        return None
    
    if (
        attribute in self.readZclClusters[ cluster ]["Attributes"] 
        and parameter in self.readZclClusters[ cluster ]["Attributes"][ attribute ]
    ):
        #self.log.logging("ZclClusters", "Debug", " . %s %s %s --> %s" %(
            # cluster, attribute, parameter, self.readZclClusters[ cluster ]["Attributes"][ attribute ][ parameter ]), nwkid = MsgSrcAddr) 
        return self.readZclClusters[ cluster ]["Attributes"][ attribute ][ parameter ]
    return None


def _cluster_specific_attribute_retrieval( self, model, ep, cluster, attribute, parameter, MsgSrcAddr=None ):

    #self.log.logging("ZclClusters", "Debug", " . _cluster_specific_attribute_retrieval %s %s %s %s %s" %(
        # model, ep, cluster, attribute, parameter), nwkid = MsgSrcAddr)

    if (
        ep in self.DeviceConf[ model ]['Ep']
        and cluster in self.DeviceConf[ model ]['Ep'][ ep ]
        and isinstance(self.DeviceConf[ model ]['Ep'][ ep ][cluster], dict )
        and "Attributes" in self.DeviceConf[ model ]['Ep'][ ep ][cluster]
        and attribute in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"] 
        and parameter in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ]
    ):

        #self.log.logging("ZclClusters", "Debug", " . %s %s %s --> %s" %(
            # cluster, attribute, parameter, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ])) 

        return self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ]
    return None


def _update_eval_formula( self, formula, input_variable, variable_name):

    self.log.logging("ZclClusters", "Debug", " . _update_eval_formula( %s, %s, %s" %( formula, input_variable, variable_name))

    return formula.replace( input_variable, variable_name )

    
def load_zcl_cluster(self):
    """Loads ZCL Cluster definitions from the plugin configuration directory."""

    zcl_cluster_path = Path(self.pluginconf.pluginConf["pluginConfig"]) / "ZclDefinitions"
    if not zcl_cluster_path.is_dir():
        return  # No directory found, exit early

    self.log.logging("ZclClusters", "Status", "Z4D loads ZCL Cluster definitions")

    for cluster_filename in sorted(zcl_cluster_path.iterdir()):
        if not cluster_filename.is_file():
            continue  # Skip directories

        cluster_definition = _read_zcl_cluster(self, cluster_filename)
        if not cluster_definition:
            continue  # Skip if file could not be read

        # Extract required fields safely
        cluster_id = cluster_definition.get("ClusterId")
        enabled = cluster_definition.get("Enabled", False)
        description = cluster_definition.get("Description")
        version = cluster_definition.get("Version")
        attributes = cluster_definition.get("Attributes", {})

        # Validation: Ensure required fields exist and are enabled
        if not (cluster_id and enabled and description):
            continue

        # Avoid duplicate cluster definitions
        if cluster_id in self.readZclClusters:
            continue

        # Store cluster data
        self.readZclClusters[cluster_id] = {
            "Description": description,
            "Version": version,
            "Attributes": attributes,
        }

        # Optional Debug field
        if "Debug" in cluster_definition:
            self.readZclClusters[cluster_id]["Debug"] = cluster_definition["Debug"]

        # Logging
        self.log.logging(
            "ZclClusters",
            "Debug",
            f" - ZCL Cluster {cluster_id} - (V{version}) {description} loaded"
        )


def is_cluster_specific_config(self, model, ep, cluster, attribute=None):
    if model not in self.DeviceConf:
        return False
    if 'Ep' not in self.DeviceConf[ model ]:
        return False
    if ep not in self.DeviceConf[ model ]['Ep']:
        return False
    if cluster not in self.DeviceConf[ model ]['Ep'][ ep ]:
        return False
    if self.DeviceConf[ model ]['Ep'][ ep ][ cluster ] in ( '', {} ):
        return False
    if attribute is None:
        self.log.logging("ZclClusters", "Debug", "is_cluster_specific_config %s and definition %s" %( 
            cluster, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ] ))
        return True
    
    if "Attributes" not in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]:
        return False
    if attribute not in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"]:
        return False

    self.log.logging("ZclClusters", "Debug", "is_cluster_specific_config %s/%s and definition %s" %( 
        cluster, attribute, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ] ))

    return True


def is_cluster_zcl_config_available( self, nwkid, ep, cluster, attribute=None):
    """ Is this cluster is handle via the ZclCluster , is this cluster + attribute hanlde via ZclCluster """

    if is_manufacturer_specific_cluster( self, nwkid, ep, cluster):
        return True

    if is_cluster_specific_config(self, _get_model_name( self, nwkid), ep, cluster, attribute):
        return True

    return is_generic_zcl_cluster( self, cluster, attribute)
    
    
def is_manufacturer_specific_cluster(self, nwkid, ep, cluster):
    cluster_info = self.readZclClusters.get(cluster, {}).get("ManufSpecificCluster", False)

    if cluster_info:
        return True

    device_info = self.DeviceConf.get(_get_model_name(self, nwkid), {}).get('Ep', {}).get(ep, {}).get(cluster, {})
    return device_info and 'ManufSpecificCluster' in device_info


def is_generic_zcl_cluster( self, cluster, attribute=None):
    if cluster not in self.readZclClusters:
        return False

    if (
        attribute is None 
        or attribute not in self.readZclClusters[ cluster ]["Attributes"] 
        or "Enabled" not in self.readZclClusters[ cluster ]["Attributes"][ attribute ]
        or not self.readZclClusters[ cluster ]["Attributes"][ attribute ]["Enabled"]
    ):
        return False

    self.log.logging("ZclClusters", "Debug", "is_generic_zcl_cluster %s/%s and definition %s" %( 
        cluster, attribute, self.readZclClusters[ cluster ]["Attributes"][ attribute ] ))
    
    return True


def cluster_attribute_retrieval(self, ep, cluster, attribute, parameter, model=None, MsgSrcAddr=None):
    if model and is_cluster_specific_config(self, model, ep, cluster, attribute=attribute):
        return _cluster_specific_attribute_retrieval( self, model, ep, cluster, attribute, parameter, MsgSrcAddr )
    return _cluster_zcl_attribute_retrieval( self, cluster, attribute, parameter, MsgSrcAddr )

  
def action_majdomodevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ):
    
    DOMO_DEVICE_FORMATER = {
        "str": str,
        "str_2digits": lambda x: "%02d" % int(x),
        "str_4digits": lambda x: "%04d" % int(x),
        "strhex": lambda x: "%x" % x,
        "str2hex": lambda x: "%02x" % x,
        "str4hex": lambda x: "%04x" % x
    }

    self.log.logging( "ZclClusters", "Debug", "action_majdomodevice - %s/%s %s %s %s %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ), nwkid=MsgSrcAddr)

    _majdomo_formater = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DomoDeviceFormat", model=device_model)
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_formater: %s" %_majdomo_formater, nwkid=MsgSrcAddr)

    if get_device_config_param( self, MsgSrcAddr, "disableBinaryInputCluster") and MsgClusterId == "000f":
        return

    majValue = DOMO_DEVICE_FORMATER[ _majdomo_formater ](value) if (_majdomo_formater and _majdomo_formater in DOMO_DEVICE_FORMATER) else value
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_formater: %s %s -> %s" %(_majdomo_formater, value, majValue), nwkid=MsgSrcAddr)

    _majdomo_cluster = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithCluster", model=device_model)
    majCluster = _majdomo_cluster if _majdomo_cluster is not None else MsgClusterId
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_cluster: %s" %_majdomo_cluster, nwkid=MsgSrcAddr)

    _majdomo_attribute = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithAttribute", model=device_model)
    majAttribute = _majdomo_attribute if _majdomo_attribute is not None else ""
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_attribute: %s -> %s" %(_majdomo_attribute, majAttribute), nwkid=MsgSrcAddr)

    _majdomo_endpoint = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithEp", model=device_model)
    target_ep = _majdomo_endpoint if _majdomo_endpoint is not None else MsgSrcEp
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_ep: %s -> %s" %(_majdomo_endpoint, target_ep), nwkid=MsgSrcAddr)

    MajDomoDevice(self, Devices, MsgSrcAddr, target_ep, majCluster, majValue, Attribute_=majAttribute)


def majdomodevice_possiblevalues( self, MsgSrcEp, MsgClusterId, MsgAttrID, model, value):

    _majdomodeviceValidValues = cluster_attribute_retrieval( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ValidValuesDomoDevices", model=model)
    if _majdomodeviceValidValues is None:
        return True
    eval_result = eval( _majdomodeviceValidValues )  # nosec B307

    self.log.logging("ZclClusters", "Debug", " . majdomodevice_possiblevalues: >%s<(%s) %s -> %s" %(
        value, type(value), eval_result, _majdomodeviceValidValues))
    return eval_result


def check_special_values( self, value, data_type, _special_values ):
    flag = False
    for x in _special_values:
        if value == decoding_attribute_data( data_type, x):
            self.log.logging("ZclClusters", "Debug", " . found %s as %s" %( value, _special_values[ x ] ))
            flag = True
    return flag

  
def compute_attribute_value( self, nwkid, ep, cluster, attribut, value, _eval_inputs, _eval_formula, _function):

    self.log.logging("ZclClusters", "Debug", "compute_attribute_value - _function: %s FUNCTION_MODULE: %s" %( _function, str(FUNCTION_MODULE) ), nwkid)

    if _function and _function in FUNCTION_MODULE:
        func = FUNCTION_MODULE[ _function ]
        return func( self, nwkid, ep, cluster, attribut, value )
        
    evaluation_result = value
    custom_variable = {}
    if _eval_inputs is not None:
        for idx, x in enumerate(_eval_inputs):
            #  "EvalExpCustomVariables": {"scale": { "ClusterId": "0403", "AttributeId": "0014"}},
            if "ClusterId" in _eval_inputs[x] and "AttributeId" in _eval_inputs[x]:
                cluster = _eval_inputs[x][ "ClusterId" ]
                attribute = _eval_inputs[x][ "AttributeId" ]
                custom_value = getAttributeValue(self, nwkid, ep, cluster, attribute)

                self.log.logging("ZclClusters", "Debug", " EvalExpCustomVariables . %s/%s = %s" %( cluster, attribute, custom_value ), nwkid)
                if custom_value is None:
                    self.log.logging("ZclClusters", "Error", "process_cluster_attribute_response - unable to found Input variable: %s Cluster: %s Attribute: %s" %(
                        x, cluster, attribute), nwkid)
                    continue
                custom_variable[ idx ] = custom_value
                _eval_formula = _update_eval_formula( self, _eval_formula, x, "custom_variable[ %s ]" % idx)
                self.log.logging("ZclClusters", "Debug", " . Updated formula: %s" %_eval_formula, nwkid)

        for x in custom_variable:
            self.log.logging("ZclClusters", "Debug", " . custom_variable[ %s ] = %s" %( idx, custom_variable[ idx ]), nwkid)
        
    if _eval_formula is not None and _eval_formula != "":
        try:
            evaluation_result = eval( _eval_formula )  # nosec B307
            self.log.logging("ZclClusters", "Debug", " . after evaluation value: %s -> %s" %( value, evaluation_result), nwkid)
            return evaluation_result

        except NameError as e:
            self.log.logging("ZclClusters", "Error", "Undefined variable, please check the formula %s/%s %s %s" %(
                nwkid, ep, cluster, attribut))
            _log_error_formula( self, e, _eval_formula, custom_variable)
        
        except SyntaxError as e:
            self.log.logging("ZclClusters", "Error", "Syntax error, please check the formula")
            _log_error_formula( self, e, _eval_formula, custom_variable)
            
        except ValueError as e:
            self.log.logging("ZclClusters", "Error", "Value Error, please check the formula")
            _log_error_formula( self, e, _eval_formula, custom_variable)
            
    return None

def _log_error_formula( self, e, _eval_formula, custom_variable):
    self.log.logging("ZclClusters", "Error", "   - Error: %s" % e)
    self.log.logging("ZclClusters", "Error", "   - formula: %s" % _eval_formula)
    self.log.logging("ZclClusters", "Error", "   - variables: %s" % custom_variable)


def store_value_in_specif_storage(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value,
                                  _storage_specificlvl1, _storage_specificlvl2=None, _storage_specificlvl3=None):
    """ Stores value in a hierarchical storage structure inside self.ListOfDevices """

    self.log.logging("ZclClusters", "Debug",
                     f"store_value_in_specif_storage - {MsgSrcAddr}/{MsgSrcEp} {_storage_specificlvl1} "
                     f"{_storage_specificlvl2} {_storage_specificlvl3} {value}")

    if _storage_specificlvl1 is None:
        return  # No valid storage level

    device_data = self.ListOfDevices.setdefault(MsgSrcAddr, {})

    # Ensure _storage_specificlvl1 is always a dictionary
    if not isinstance(device_data.get(_storage_specificlvl1), dict):
        device_data[_storage_specificlvl1] = {}

    if _storage_specificlvl2 is None:
        self.log.logging("ZclClusters", "Debug", f"     store_value_in_specif_storage [{_storage_specificlvl1}] = {value}")
        device_data[_storage_specificlvl1] = value
        return

    level1_data = device_data[_storage_specificlvl1]

    # Ensure _storage_specificlvl2 is always a dictionary
    if not isinstance(level1_data.get(_storage_specificlvl2), dict):
        level1_data[_storage_specificlvl2] = {}

    if _storage_specificlvl3 is None:
        self.log.logging("ZclClusters", "Debug", f"     store_value_in_specif_storage [{_storage_specificlvl1}][{_storage_specificlvl2}] = {value}")
        level1_data[_storage_specificlvl2] = value
        return

    level2_data = level1_data[_storage_specificlvl2]

    # Ensure _storage_specificlvl3 is always a dictionary
    if not isinstance(level2_data.get(_storage_specificlvl3), dict):
        level2_data[_storage_specificlvl3] = {}

    self.log.logging("ZclClusters", "Debug", f"     store_value_in_specif_storage [{_storage_specificlvl1}][{_storage_specificlvl2}][{_storage_specificlvl3}] = {value}")
    level2_data[_storage_specificlvl3] = value


def formated_logging( self, nwkid, ep, cluster, attribute, dt, dz, d, Source, device_model, attr_name, exp_dt, _ranges, _special_values, eval_formula, action_list, eval_inputs, force_value, value):

    if not self.pluginconf.pluginConf["trackZclClustersIn"]:
        return

    lqi = self.ListOfDevices[nwkid]["LQI"] if "LQI" in self.ListOfDevices[nwkid] else 0
    cluster_description = self.readZclClusters[ cluster ]["Description"] if self.readZclClusters and cluster in self.readZclClusters else "Unknown cluster"
    self.log.logging( "ZclClusters", "Log", "Attribute Report | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s " %(
        nwkid, ep, cluster, cluster_description, attribute, attr_name, dt, dz, device_model, eval_formula, eval_inputs, action_list, force_value, d, value, lqi ), nwkid)

def debug_logging(self, nwkid, ep, cluster, attribute, dtype, attsize, raw_data, value):
    
    if not is_cluster_debug_mode(self, cluster):
        return
    
    cluster_description = self.readZclClusters.get(cluster, {}).get("Description", "Unknown cluster")
    attribute_description = None
    
    model = _get_model_name( self, nwkid)
    if model is not None and model in self.DeviceConf:
        # Debug each step
        conf = self.DeviceConf[model]
        cluster_data = conf.get("Ep", {}).get(ep, {}).get(cluster, {})
        if isinstance(cluster_data, dict):
            attribute_description = cluster_data.get("Attributes", {}).get(attribute, {}).get("Name", None)

    if attribute_description is None:
        attribute_description = self.readZclClusters.get(cluster, {}).get("Attributes", {}).get(attribute, {}).get("Name", "Unknown Zcl standard attribute")

    self.log.logging( "ZclClusters", "Log", f"readZclCluster - Ox{nwkid}/{ep} 0x{cluster} {cluster_description} - attribute: 0x{attribute} {attribute_description} raw_data: {raw_data} value: {value}", nwkid)


def is_cluster_debug_mode(self, cluster):
    if cluster not in self.readZclClusters:
        self.log.logging( "ZclClusters", "Debug", f"readZclCluster {cluster} not found !")
        return

    if "Debug" not in self.readZclClusters[ cluster ]:
        return False

    debug_flag = self.readZclClusters[ cluster ]["Debug"]
    if debug_flag in self.pluginconf.pluginConf:
        return self.pluginconf.pluginConf[ debug_flag ]
    return False
