#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: tuyaTS0601.py

    Description: play around the Config file.

"""

import struct

from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import Update_Battery_Device
from Modules.tools import (checkAndStoreAttributeValue, get_and_inc_ZCL_SQN,
                           getAttributeValue)
from Modules.tuyaTools import (get_tuya_attribute, store_tuya_attribute,
                               tuya_cmd)

# Generic functions

def ts0601_response(self, Devices, model_name, NwkId, Ep, dp, datatype, data):
    self.log.logging("Tuya0601", "Debug", "ts0601_response - %s %s %s %s %s" % (
        NwkId, model_name, dp, datatype, data), NwkId)
    
    dps_mapping = ts0601_extract_data_point_infos( self, model_name) 
    if dps_mapping is None:
        return False
    
    str_dp = "%02x" %dp
    if str_dp not in dps_mapping:
        self.log.logging("Tuya0601", "Log", "ts0601_response - unknow dp %s %s %s %s %s" % (
            NwkId, str_dp, datatype, data, str(dps_mapping)), NwkId)
        store_tuya_attribute(self, NwkId, "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype) , data)
        return False
    
    value = int(data, 16)
    self.log.logging("Tuya0601", "Debug", "                - value: %s" % (value), NwkId)
    
    self.log.logging("Tuya0601", "Debug", "                - dps_mapping[ %s ]: %s (%s)" % (
        str_dp, dps_mapping[ str_dp ], type(dps_mapping[ str_dp ])), NwkId)
    if not isinstance( dps_mapping[ str_dp ], list):
        # We complex data point which provide multiple value
        return process_dp_item( self, Devices, model_name, NwkId, Ep, dp, datatype, data, dps_mapping[ str_dp ], value)

    for dps_mapping_item in dps_mapping[ str_dp ]:
        process_dp_item( self, Devices, model_name, NwkId, Ep, dp, datatype, data, dps_mapping_item, value)
    return True 

def process_dp_item( self, Devices, model_name, NwkId, Ep, dp, datatype, data, dps_mapping_item, value):
    if "EvalExp" in dps_mapping_item:
        value = evaluate_expression_with_data(self, dps_mapping_item[ "EvalExp"], value)
    self.log.logging("Tuya0601", "Debug", "                - after evaluate_expression_with_data() value: %s" % (value), NwkId)

    if "store_tuya_attribute" in dps_mapping_item:
        store_tuya_attribute(self, NwkId, dps_mapping_item["store_tuya_attribute"], data)
    
    return sensor_type( self, Devices, NwkId, Ep, value, dp, datatype, data, dps_mapping_item )
   
    
def sensor_type( self, Devices, NwkId, Ep, value, dp, datatype, data, dps_mapping_item ):
    self.log.logging("Tuya0601", "Debug", "sensor_type - %s %s %s %s %s %s %s" % (
        NwkId, Ep, value, dp, datatype, data, dps_mapping_item), NwkId)

    if "sensor_type" not in dps_mapping_item:
        if "store_tuya_attribute" not in dps_mapping_item:
            store_tuya_attribute(self, NwkId, "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype) , data)
        return True
    
    divisor = dps_mapping_item["domo_divisor"] if "domo_divisor" in dps_mapping_item else 1
    value = value / divisor
    rounding = dps_mapping_item["domo_round"] if "domo_round" in dps_mapping_item else 0
    value = round( value, rounding ) if rounding else int(value)

    self.log.logging("Tuya0601", "Debug", "                - after sensor_type() value: %s divisor: %s rounding: %s" % (value, divisor, rounding), NwkId)
   
    sensor_type = dps_mapping_item[ "sensor_type"]
    if sensor_type in DP_SENSOR_FUNCTION:
        value = check_domo_format_req( self, dps_mapping_item, value)
        func = DP_SENSOR_FUNCTION[ sensor_type ]
        func(self, Devices, NwkId, Ep, value  )
        return True
    
    return False

def ts0601_actuator( self, NwkId, command, value=None):
    self.log.logging("Tuya0601", "Debug", "ts0601_actuator - requesting %s %s" %(
        command, value))

    model_name = self.ListOfDevices[ NwkId ]["Model"] if "Model" in self.ListOfDevices[ NwkId ] else None
    if model_name is None:
        return
    
    dps_mapping = ts0601_extract_data_point_infos( self, model_name) 
    if dps_mapping is None:
        self.log.logging("Tuya0601", "Error", "ts0601_actuator - No DPS stanza in config file for %s %s" %(NwkId, command))
        return False
    
    if command not in DP_ACTION_FUNCTION and command not in TS0601_COMMANDS:
        self.log.logging("Tuya0601", "Error", "ts0601_actuator - unknow command %s in core plugin" % command)
        return False
    
    str_dp = ts0601_actuator_dp( command, dps_mapping)
    if str_dp is None:
        self.log.logging("Tuya0601", "Error", "ts0601_actuator - unknow command %s in config file" % command)
        return False
    
    if "action_Exp" in dps_mapping[ str_dp ]:
        # Correct Value to proper format
        value = evaluate_expression_with_data(self, dps_mapping[ str_dp ]["action_Exp"], value)
        self.log.logging("Tuya0601", "Debug", "      corrected value: %s" % ( value ))
        
    dp = int(str_dp, 16)
    
    self.log.logging("Tuya0601", "Debug", "ts0601_actuator - requesting %s %s %s" %(
        command, dp, value))

    if command in TS0601_COMMANDS:
        func = TS0601_COMMANDS[ command ]
    else:
        func = DP_ACTION_FUNCTION[ command ]
    if value is not None:
        func(self, NwkId, "01", dp, value )
    else:
        func(self, NwkId, "01", dp )


# Helpers        
def read_uint16_be(data, offset):
    # Use the format '>H' to specify big-endian (>) and 'H' for 16-bit unsigned integer.
    return struct.unpack_from('>H', data, offset)[0]

def read_uint8(data, offset):
    # Use indexing to get the byte at the specified offset
    # and convert it to an unsigned integer using ord().
    return ord(data[offset])

def evaluate_expression_with_data(self, expression, value):
    try:
        return eval( expression )
        
    except NameError as e:
        self.log.logging("ZclClusters", "Error", "Undefined variable, please check the formula %s or value %s" %(
            expression, value))
    
    except SyntaxError as e:
        self.log.logging("ZclClusters", "Error", "Syntax error, please check the formula %s or value %s" %(
            expression, value))

    except ValueError as e:
        self.log.logging("ZclClusters", "Error", "Value Error, please check the formula %s or value %s. Error: %s" %(
            expression, value, e))
        
    return value

def check_domo_format_req( self, dp_informations, value):
    
    if "DomoDeviceFormat" not in dp_informations:
        return value
    if dp_informations[ "DomoDeviceFormat" ] == "str":
        value = str(value)
    elif dp_informations[ "DomoDeviceFormat" ] == "strhex":
        value = "%x" %value
    
    return value

def ts0601_extract_data_point_infos( self, model_name):
    
    if model_name not in self.DeviceConf:
        return None
    if "TS0601_DP" not in self.DeviceConf[model_name ]:
        return None
    return self.DeviceConf[model_name ][ "TS0601_DP" ]

def ts0601_actuator_dp( command, dps_mapping):
    return next( ( dp for dp in dps_mapping if "action_type" in dps_mapping[dp] and command == dps_mapping[dp]["action_type"] ), None, )

    
# Sensors responses

def ts0601_motion(self, Devices, nwkid, ep, value):
    # Occupancy
    self.log.logging("Tuya0601", "Debug", "ts0601_motion - Occupancy %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Occupancy", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0406", value )
    checkAndStoreAttributeValue(self, nwkid, "01", "0406", "0000", value)


def ts0601_illuminance(self, Devices, nwkid, ep, value):
    # Illuminance
    self.log.logging("Tuya0601", "Debug", "ts0601_illuminance - Illuminance %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Illuminance", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0400", value)
    checkAndStoreAttributeValue(self, nwkid, "01", "0400", "0000", value)


def ts0601_temperature(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_temperature - Temperature %s %s %s " % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Temp", value)
    checkAndStoreAttributeValue(self, nwkid, "01", "0402", "0000", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value)
    
    
def ts0601_humidity(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_humidity - humidity %s %s %s " % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Humi", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0405", value)


def ts0601_distance(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_distance - Distance %s %s %s " % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Distance", value)
    MajDomoDevice(self, Devices, nwkid, ep, "Distance", value)


def ts0601_battery(self, Devices, nwkid, ep, value ):
    self.log.logging("Tuya0601", "Debug", "ts0601_battery - Battery %s %s %s" % (nwkid, ep, value), nwkid)
        
    store_tuya_attribute(self, nwkid, "Battery", value)
    checkAndStoreAttributeValue(self, nwkid, "01", "0001", "0000", value)
    self.ListOfDevices[nwkid]["Battery"] = value
    Update_Battery_Device(self, Devices, nwkid, value)
    store_tuya_attribute(self, nwkid, "BatteryStatus", value)

def ts0601_battery_state(self, Devices, nwkid, ep, value ):
    self.log.logging("Tuya0601", "Debug", "ts0601_battery_state - Battery %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "BatteryState", value)


def ts0601_tamper(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_tamper - Tamper %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Tamper", value)
    state = "01" if value != 0 else "00"
    MajDomoDevice(self, Devices, nwkid, ep, "0009", state)


def ts0601_switch(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_switch - Switch%s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Switch", value)
    state = "01" if value != 0 else "00"
    MajDomoDevice(self, Devices, nwkid, ep, "0006", state)


def ts0601_level_percentage(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_level_percentage - Percentage%s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute(self, nwkid, "PercentState", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0008", "%02x" %value)


def ts0601_door(self, Devices, nwkid, ep, value):
    # Door Contact: 0x00 => Closed, 0x01 => Open
    self.log.logging( "Tuya0601", "Debug", "ts0601_door - Door Contact%s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, "01", "0500", "%02x" %value )
    store_tuya_attribute(self, nwkid, "DoorContact", value)


def ts0601_co2ppm(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_co2ppm - CO2 ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute( self, nwkid, "CO2 ppm", value, )
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value, Attribute_="0005")


def ts0601_mp25(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_mp25 - MP25 ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute( self, nwkid, "MP25", value, )
    MajDomoDevice(self, Devices, nwkid, ep, "042a", value,)


def ts0601_voc(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_voc - VOC ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute(self, nwkid, "VOC ppm", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value, Attribute_="0003")


def ts0601_ch20(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_ch20 - CH2O ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute(self, nwkid, "CH2O ppm", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value, Attribute_="0004")


def ts0601_current(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_current - Current %s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0b04", value, Attribute_="0508")
    checkAndStoreAttributeValue(self, nwkid, ep, "0b04", "0508", value)  # Store int
    store_tuya_attribute(self, nwkid, "Current", value)


def ts0601_summation_energy(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_summation_energy - Current Summation %s %s %s" % (nwkid, ep, value), nwkid, )
    previous_summation = getAttributeValue(self, nwkid, ep, "0702", "0000")
    current_summation = (previous_summation + value) if previous_summation else value
    self.log.logging( "Tuya0601", "Debug", "ts0601_summation_energy - Current Summation %s %s %s Prev Summation %s Total Summation %s" % (
        nwkid, ep, value, previous_summation, current_summation), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0702", current_summation, Attribute_="0000")
    checkAndStoreAttributeValue(self, nwkid, ep, "0702", "0000", current_summation)  # Store int
    store_tuya_attribute(self, nwkid, "Energy", value)

def ts0601_summation_energy_raw(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_summation_energy - Current Summation %s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0702", value, Attribute_="0000")
    checkAndStoreAttributeValue(self, nwkid, ep, "0702", "0000", value)  # Store int
    store_tuya_attribute(self, nwkid, "ConsumedEnergy", value)

def ts0601_production_energy(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_production_energy - Production Energy %s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0702", value, Attribute_="0001")
    checkAndStoreAttributeValue(self, nwkid, ep, "0702", "0001", value)  # Store int
    store_tuya_attribute(self, nwkid, "ProducedEnergy", value)


def ts0601_instant_power(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_instant_power - Instant Power %s %s %s" % (nwkid, ep, value), nwkid, )
    # Given Zigbee 24-bit integer and tuya store in two's complement form
    signed_int = int( value )
    if (signed_int & 0x00800000) != 0:  # Check the sign bit
        signed_int -= 0x01000000  # If negative, adjust to two's complement

    checkAndStoreAttributeValue(self, nwkid, ep, "0702", "0400", signed_int)
    MajDomoDevice(self, Devices, nwkid, ep, "0702", signed_int)
    store_tuya_attribute(self, nwkid, "InstantPower", signed_int)  # Store str

def ts0601_voltage(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_voltage - Voltage %s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0001", value)
    store_tuya_attribute(self, nwkid, "Voltage", value)

def ts0601_trv7_system_mode(self, Devices, nwkid, ep, value):
    # Auto 0, Manual 1, Off 2
    # Widget 0: Off, 1: Auto, 2: Manual
    DEVICE_WIDGET_MAP = {
        0: 1,
        1: 2,
        2: 0
    }
    if value > 2:
        self.log.logging("Tuya0601", "Error", "ts0601_trv7_system_mode - After Nwkid: %s/%s Invalid SystemMode: %s" % (nwkid, ep, value))
        return
    
    self.log.logging("Tuya0601", "Debug", "ts0601_trv7_system_mode - After Nwkid: %s/%s SystemMode: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "SystemModel", value)
    if value not in DEVICE_WIDGET_MAP:
        self.log.logging("Tuya0601", "Error", "ts0601_trv7_system_mode - unexepected mode %s/%s mode: %s (%s)" %(
            nwkid, ep, value, type(value))
        )
    widget_value = DEVICE_WIDGET_MAP[ value ]
    MajDomoDevice(self, Devices, nwkid, ep, "0201", widget_value, Attribute_="001c")
    checkAndStoreAttributeValue(self, nwkid, "01", "0201", "0012", widget_value)
    
def ts0601_trv6_system_mode(self, Devices, nwkid, ep, value):
    # Auto 0, Manual 1, Off 2
    # Widget 0: Off, 1: Auto, 2: Manual
    
    if value > 2:
        self.log.logging("Tuya0601", "Error", "ts0601_trv6_system_mode - After Nwkid: %s/%s Invalid SystemMode: %s" % (nwkid, ep, value))
        return
    
    self.log.logging("Tuya0601", "Debug", "ts0601_trv6_system_mode - After Nwkid: %s/%s SystemMode: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "SystemModel", value)
   
    MajDomoDevice(self, Devices, nwkid, ep, "0201", value, Attribute_="001c")
    checkAndStoreAttributeValue(self, nwkid, "01", "0201", "0012", value)

def ts0601_sirene_switch(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_sirene_switch - After Nwkid: %s/%s Alarm: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "Alarm", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0006", value)
    
def ts0601_tamper_switch(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_sirene_switch - After Nwkid: %s/%s Alarm: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "Alarm", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0006", value)
    
def ts0601_sirene_level(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_sirene_level - Sound Level: %s" % value, nwkid)
    store_tuya_attribute(self, nwkid, "AlarmLevel", value)


def ts0601_sirene_duration(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_sirene_duration - After Nwkid: %s/%s Alarm: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "AlarmDuration", value)
    
def ts0601_sirene_melody(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_sirene_melody - After Nwkid: %s/%s Alarm: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "AlarmMelody", value)


def ts0601_setpoint(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_setpoint - After Nwkid: %s/%s Setpoint: %s" % (nwkid, ep, value))
    MajDomoDevice(self, Devices, nwkid, ep, "0201", value, Attribute_="0012")
    checkAndStoreAttributeValue(self, nwkid, "01", "0201", "0012", value)
    store_tuya_attribute(self, nwkid, "SetPoint", value)


def ts0601_heatingstatus(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_heatingstatus - After Nwkid: %s/%s HeatingStatus: %s" % (nwkid, ep, value))
    MajDomoDevice(self, Devices, nwkid, ep, "0201", value, Attribute_="0124")
    store_tuya_attribute(self, nwkid, "HeatingMode", value)


def ts0601_valveposition(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_valveposition - Nwkid: %s/%s Valve position: %s" % (nwkid, ep, value))
    MajDomoDevice(self, Devices, nwkid, ep, "0201", value, Attribute_="026d")
    store_tuya_attribute(self, nwkid, "ValvePosition", value)


def ts0601_calibration(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya0601", "Debug", "ts0601_calibration - Nwkid: %s/%s Calibration: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "Calibration", value)


def ts0601_windowdetection(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "receive_windowdetection - Nwkid: %s/%s Window Open: %s" % (nwkid, ep, value))
    MajDomoDevice(self, Devices, nwkid, ep, "0500", value)
    store_tuya_attribute(self, nwkid, "OpenWindow", value)

def ts0601_smoke_detection(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_smoke_detection - Nwkid: %s/%s Smoke State: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "SmokeState", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0500", value)

def ts0601_smoke_concentration(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Debug", "ts0601_smoke_concentration - Nwkid: %s/%s Smoke Concentration: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "SmokePPM", value)
    MajDomoDevice(self, Devices, nwkid, ep, "042a", value)

def ts0601_water_consumption(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Log", "ts0601_water_consumption - Nwkid: %s/%s WaterConsumtpion: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "WaterConsumtpion", value)
    # The counter will be treated with the divider which is defined in the parameters in the application settings 
    # (menu setup-settings, tab counters). 
    # For example if the counter is set to "Water" and the value is passed as liters, 
    # the divider must set to 1000 (as the unit is m3). The device displays 2 values:
    # The status is the overall total volume (or counter).
    # The volume (or counter) of the day (in the top right corner).
    MajDomoDevice(self, Devices, nwkid, ep, "WaterCounter", value)

def ts0601_sensor_irrigation_mode(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya0601", "Log", "ts0601_sensor_irrigation_mode - Nwkid: %s/%s Mode: %s" % (nwkid, ep, value))
    store_tuya_attribute(self, nwkid, "Mode", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0008", value)
   
DP_SENSOR_FUNCTION = {
    "motion": ts0601_motion,
    "illuminance": ts0601_illuminance,
    "temperature": ts0601_temperature,
    "setpoint": ts0601_setpoint,
    "humidity": ts0601_humidity,
    "distance": ts0601_distance,
    "battery": ts0601_battery,
    "batteryState": ts0601_battery_state,
    "tamper": ts0601_tamper,
    "switch": ts0601_switch,
    "door": ts0601_door,
    "lvl_percentage": ts0601_level_percentage,
    "co2": ts0601_co2ppm,
    "voc": ts0601_voc,
    "ch20": ts0601_ch20,
    "mp25": ts0601_mp25,
    "current": ts0601_current,
    "metering": ts0601_summation_energy,
    "cons_metering": ts0601_summation_energy_raw,
    "prod_metering": ts0601_production_energy,
    "power": ts0601_instant_power,
    "voltage": ts0601_voltage,
    "heatingstatus": ts0601_heatingstatus,
    "valveposition": ts0601_valveposition,
    "calibration": ts0601_calibration,
    "windowsopened": ts0601_windowdetection,
    "TRV6SystemMode": ts0601_trv6_system_mode,
    "TRV7SystemMode": ts0601_trv7_system_mode,
    "TuyaAlarmDuration": ts0601_sirene_duration,
    "TuyaAlarmMelody": ts0601_sirene_melody,
    "TuyaAlarmLevel": ts0601_sirene_level,
    "TuyaAlarmSwitch": ts0601_sirene_switch,
    "TuyaTamperSwitch": ts0601_tamper_switch,
    "smoke_state": ts0601_smoke_detection,
    "smoke_ppm": ts0601_smoke_concentration,
    "water_consumption": ts0601_water_consumption,
}

def ts0601_tuya_cmd(self, NwkId, Ep, action, data):
    self.log.logging("Tuya0601", "Debug", "ts0601_tuya_cmd - %s %s %s %s" % (NwkId, Ep, action, data))
    
    cluster_frame = "11"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    tuya_cmd(self, NwkId, Ep, cluster_frame, sqn, "00", action, data)
   
def ts0601_action_setpoint(self, NwkId, Ep, dp, value):
    # The Setpoint is coming in centi-degre (default)
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_action_setpoint - %s Setpoint: %s" % (NwkId, value))
    
    action = "%02x02" % dp
    data = "%08x" % value
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)
   
def ts0601_action_calibration(self, NwkId, Ep, dp, value=None):
    
    self.log.logging("Tuya0601", "Debug", "ts0601_action_calibration - %s Calibration: %s" % (NwkId, value))

    target_calibration = 0
    if (
        "Param" in self.ListOfDevices[NwkId]
        and "Calibration" in self.ListOfDevices[NwkId]["Param"]
        and isinstance(self.ListOfDevices[NwkId]["Param"]["Calibration"], (float, int))
    ):
        target_calibration = int(self.ListOfDevices[NwkId]["Param"]["Calibration"])

    value = target_calibration if value is None else value
    
    action = "%02x02" % dp
    # determine which Endpoint
    if value < 0:
        value = ( 0xffffffff - value + 1 )
        #calibration = abs(int(hex(-calibration - pow(2, 32)), 16))
    data = "%08x" % value
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_window_detection_mode( self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_window_detection_mode - %s Window Detection mode: %s" % (NwkId, value))
    action = "%02x01" % dp
    data = "%02x" % value
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)


def ts0601_child_lock_mode( self, NwkId, Ep, dp, value=None):
    if value is None:
        return
    self.log.logging("Tuya0601", "Debug", "ts0601_child_lock_mode - %s ChildLock mode: %s" % (NwkId, value))
    action = "%02x01" % dp
    data = "%02x" % value
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_action_trv7_system_mode(self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_action_trv7_system_mode - %s System mode: %s" % (NwkId, value))
    WIDGET_DEVICE_MAP = {
        1: 0,
        2: 1,
        0: 2
    }
    if value not in WIDGET_DEVICE_MAP:
        self.log.logging("Tuya0601", "Error", "ts0601_trv7_system_mode - unexepected mode %s/%s mode: %s (%s)" %(
            NwkId, Ep, value, type(value))
        )
    device_value = WIDGET_DEVICE_MAP[ value ]
   
    action = "%02x04" % dp  # Mode
    data = "%02x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)
    
def ts0601_action_trv6_system_mode(self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_action_trv6_system_mode - %s System mode: %s" % (NwkId, value))
    WIDGET_DEVICE_MAP = {
        0: 2,
        1: 1,
        2: 0
    }
    if value not in WIDGET_DEVICE_MAP:
        self.log.logging("Tuya0601", "Error", "ts0601_action_trv6_system_mode - unexepected mode %s/%s mode: %s (%s)" %(
            NwkId, Ep, value, type(value))
        )
    device_value = WIDGET_DEVICE_MAP[ value ]
   
    action = "%02x04" % dp  # Mode
    data = "%02x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_action_siren_switch(self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_action_siren_switch - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, value))
    device_value = value
   
    action = "%02x01" % dp  # Mode
    data = "%02x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_tamper_siren_switch(self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_tamper_siren_switch - %s Tamper Switch Action: dp:%s value: %s" % (
        NwkId, dp, value))
    device_value = value
   
    action = "%02x01" % dp  # Mode
    data = "%02x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)


def ts0601_action_switch(self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_action_switch - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, value))
    device_value = value
   
    action = "%02x01" % dp  # State
    data = "%02x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_irrigation_mode(self, NwkId, Ep, dp, value=None):
    # 0 Capacity ( Litter )
    # 1 Duration ( Seconds)

    if value is None:
        return

    self.log.logging("Tuya0601", "Debug", "ts0601_action_switch - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, value))
    device_value = value
   
    action = "%02x01" % dp  # Mode
    data = "%02x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

SAFETY_MIN_SECS = 10
DURATION = 1
   
def check_irrigation_valve_target_value(value, mode):
    if value > 0 and value < SAFETY_MIN_SECS and mode == DURATION:
        return SAFETY_MIN_SECS
    else:
        return value
    
def ts0601_irrigation_valve_target( self, NwkId, Ep, dp, value=None):
    if value is None:
        return

    self.log.logging("Tuya0601", "Log", "ts0601_irrigation_valve_target - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, value))

    mode = get_tuya_attribute(self, NwkId, 'Mode')
    if mode:
        mode = 1
    device_value = check_irrigation_valve_target_value(value, mode)

    action = "%02x02" % dp  # Irrigation Target (Time or Litters)
    data = "%08x" % (device_value)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)
    
def ts0601_solar_siren_alarm_melody( self, NwkId, Ep, dp, melody=None):
    if melody is None:
        return
    self.log.logging("Tuya0601", "Log", "ts0601_solar_siren_alarm_melody - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, melody))
    if melody is None:
        return
    action = "%02x04" % dp  # I
    data = "%02x" % (melody)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_solar_siren_alarm_mode( self, NwkId, Ep, dp, mode=None):
    if mode is None:
        return
    self.log.logging("Tuya0601", "Log", "ts0601_solar_siren_alarm_mode - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, mode))
    if mode is None:
        return
    action = "%02x04" % dp  # I
    data = "%02x" % (mode)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

def ts0601_solar_siren_alarm_duration( self, NwkId, Ep, dp, duration=None):
    if duration is None:
        return
    self.log.logging("Tuya0601", "Log", "ts0601_solar_siren_alarm_duration - %s Switch Action: dp:%s value: %s" % (
        NwkId, dp, duration))
    action = "%02x02" % dp  # I
    data = "%08x" % (duration)
    ts0601_tuya_cmd(self, NwkId, Ep, action, data)

TS0601_COMMANDS = {
    "TRV7WindowDetection": ts0601_window_detection_mode,
    "TRV7ChildLock": ts0601_child_lock_mode,
    "TuyaIrrigationTarget": ts0601_irrigation_valve_target,
    "TuyaIrrigationMode": ts0601_irrigation_mode,
    "TuyaAlarmMelody": ts0601_solar_siren_alarm_melody,
    "TuyaAlarmMode": ts0601_solar_siren_alarm_mode,
    "TuyaAlarmDuration": ts0601_solar_siren_alarm_duration
}

DP_ACTION_FUNCTION = {
    "switch": ts0601_action_switch,
    "setpoint": ts0601_action_setpoint,
    "calibration": ts0601_action_calibration,
    "TRV6SystemMode": ts0601_action_trv6_system_mode,
    "TRV7SystemMode": ts0601_action_trv7_system_mode,
    "TuyaAlarmSwitch": ts0601_action_siren_switch,
    "TuyaTamperSwitch": ts0601_tamper_siren_switch
}
