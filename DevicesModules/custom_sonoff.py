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
Sonoff Zigbee Device Control for Domoticz

This module provides specialized support for Sonoff Zigbee devices within the
Domoticz Zigbee plugin. It includes functions for configuring and interacting
with various Sonoff device models, such as smart thermostatic radiator valves
(TRVs), temperature and humidity sensors (e.g., SNZB-02LD), smart valves (e.g., SWV),
and inching controllers (e.g., ZBMicro).

The module enables:
- Setting child lock and window detection modes on TRVs
- Configuring temperature and humidity thresholds
- Handling real-time irrigation parameters (duration, volume)
- Auto-shutdown of valves on water shortage
- SWV-ZFE/ZFU manual irrigation session defaults, valve alarms and flow unit
- Adjusting radio power modes (e.g., Turbo Mode)
- Setting temperature unit (Celsius/Fahrenheit)
- Performing temperature calibration

Functions log debug and error messages using the plugin’s logging mechanism,
and write Zigbee attributes using the `write_attribute` utility.

Constants for manufacturer IDs, cluster IDs, and attribute IDs are defined
for internal use, following the Zigbee specification and Sonoff extensions.

Authors:
    zaraki673, pipiche38 (2015–2024)

License:
    GNU General Public License v3.0 (SPDX: GPL-3.0)

Repository:
    https://github.com/zigbeefordomoticz/Domoticz-Zigbee
"""


from Modules.basicOutputs import write_attribute
from Modules.tools import get_device_config_param
from Modules.zigateConsts import ZIGATE_EP

SONOFF_MAUFACTURER_NAME = "SONOFF"
SONOFF_MANUFACTURER_ID = "1286"
SONOFF_CLUSTER_ID = "fc11"
SONOFF_ILLUMINATION_ATTRIBUTE = "2001"
SONOFF_MAX_TEMP = "0003"
SONOFF_MIN_TEMP = "0004"
SONOFF_MAX_HUMI = "0005"
SONOFF_MIN_HUMI = "0006"

# Sonoff Smart Valve - SWV model
SONOFF_REALTIME_IRRIGATION_DURATION = "5006"
SONOFF_REALTIME_IRRIGATION_VOLUME = "5007"
SONOFF_VALVE_ABNORMAL_STATE = "500c"
SONOFF_IRRIGATIM_START_TIME = "500d"
SONOFF_IRRIGATION_END_TIME = "500e"
SONOFF_DAILY_IRRIGATION_VOLUME = "500F"
SONOFF_VALVE_WORK_STATE = "5010"
SONOFF_WATER_CLOSE_VALVE_TIMEOUT_ATTRIBUTE = "5011"

# Sonoff Smart Valve - SWV-ZFE / SWV-ZFU models (fc11 private attributes, see
# zigbee-herdsman-converters src/devices/sonoff.ts "SWV-ZFE")
SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_ATTRIBUTE = "501d"   # ARRAY(uint8)[12]
SONOFF_SWV_VALVE_ALARM_SETTINGS_ATTRIBUTE = "5020"      # ARRAY(uint8)[4]
SONOFF_SWV_UNIT_OF_WATER_FLOW_ATTRIBUTE = "5021"        # uint8
ZCL_ARRAY_DATA_TYPE = "48"
ZCL_UINT8_DATA_TYPE = "20"

SONOFF_SWV_MAX_IRRIGATION_MINUTES = 719
SONOFF_SWV_IRRIGATION_MODE = {"duration": 0x00, "capacity": 0x01}
# 0x501d amount unit byte (legacy mapping, valid on every firmware): 0 = US gallon, 1 = liter
SONOFF_SWV_AMOUNT_UNIT = {"us_gallon": 0x00, "liter": 0x01}
# 0x5021 unit of water flow (firmware >= 1.1.0): 0 = liter, 1 = US gallon, 2 = imperial gallon
SONOFF_SWV_WATER_FLOW_UNIT = {"liter": 0x00, "us_gallon": 0x01, "imperial_gallon": 0x02}

# Sonoff InchingController - ZBMicro model
SONOFF_RADIO_POWER_TURBO_MODE = "0012"

# Sonoff SNZB-02LD - Temperature Sensor
SONOFF_CALIBRATION_ATTRIBUTE = "2003"
SONOFF_TEMPERATURE_UNIT_ATTRIBUTE = "0007"

def is_sonoff_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == SONOFF_MANUFACTURER_ID or self.ListOfDevices[nwkid]["Manufacturer Name"] == SONOFF_MAUFACTURER_NAME


def sonoff_child_lock(self, nwkid, lock_mode):
    self.log.logging("Sonoff", "Debug", "sonoff_child_lock - Nwkid: %s Mode: %s" % (nwkid, lock_mode), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", "0000", "10", "%02x" %lock_mode, ackIsDisabled=False)


def sonoff_open_window_detection(self, nwkid, detection):
    self.log.logging("Sonoff", "Debug", "sonoff_child_lock - Nwkid: %s Mode: %s" %(nwkid, detection), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", "6000", "10", "%02x" %detection, ackIsDisabled=False)


def sonoff_temp_humi_ranges(self, nwkid, value):
    self.log.logging("Sonoff", "Debug", "sonoff_temp_humi_ranges - Nwkid: %s Mode: %s" %(nwkid, value), nwkid)
    temp_max = get_device_config_param(self, nwkid, "SONOFF_TEMP_MAX")
    temp_min = get_device_config_param(self, nwkid, "SONOFF_TEMP_MIN")
    humi_max = get_device_config_param(self, nwkid, "SONOFF_HUMI_MAX")
    humi_min = get_device_config_param(self, nwkid, "SONOFF_HUMI_MIN")

    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MAX_TEMP, "29", "%04x" %temp_max, ackIsDisabled=False)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MIN_TEMP, "29", "%04x" %temp_min, ackIsDisabled=False)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MAX_HUMI, "21", "%04x" %humi_max, ackIsDisabled=False)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MIN_HUMI, "21", "%04x" %humi_min, ackIsDisabled=False)


def sonoff_realtime_irrigation_duration(self, nwkid, value):
    """ Real-time Irrigation duration """
    self.log.logging("Sonoff", "Debug", "sonoff_realtime_irrigation_duration - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_REALTIME_IRRIGATION_DURATION, "23", "%08x" %value, ackIsDisabled=False)


def sonoff_realtime_irrigation_volume(self, nwkid, value):
    """ Real-time Irrigation volume """
    self.log.logging("Sonoff", "Debug", "sonoff_realtime_irrigation_duration - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_REALTIME_IRRIGATION_VOLUME, "23", "%08x" %value, ackIsDisabled=False)


def sonoff_realtime_irrigation_daily_volume(self, nwkid, value):
    """ Daily irigation volume """
    self.log.logging("Sonoff", "Debug", "sonoff_realtime_irrigation_duration - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_DAILY_IRRIGATION_VOLUME, "23", "%08x" %value, ackIsDisabled=False)


def auto_close_when_water_shortage(self, nwkid, value):
    """ Automatically shut down the water valve after the water shortage exceeds 30 minutes. """

    self.log.logging("Sonoff", "Debug", "auto_close_when_water_shortage - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    water_close_valve_timeout = "%04x" % value
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_WATER_CLOSE_VALVE_TIMEOUT_ATTRIBUTE, "21", water_close_valve_timeout, ackIsDisabled=False)


def _zcl_uint8_array(elements):
    """ Encode a ZCL ARRAY (0x48) of uint8 as hex: element type, count (uint16 LE), elements """
    return ZCL_UINT8_DATA_TYPE + len(elements).to_bytes(2, "little").hex() + bytes(elements).hex()


def _param_int(self, nwkid, param, default, minimum, maximum):
    value = get_device_config_param(self, nwkid, param)
    if value is None:
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        self.log.logging("Sonoff", "Error", "%s invalid value %s, expected an integer" % (param, value), nwkid)
        return default
    return max(minimum, min(value, maximum))


def _param_choice(self, nwkid, param, choices, default):
    value = get_device_config_param(self, nwkid, param)
    if value is None:
        return default
    if value not in choices:
        self.log.logging("Sonoff", "Error", "%s invalid value %s, expected one of %s" % (param, value, sorted(choices)), nwkid)
        return default
    return choices[value]


def sonoff_swv_manual_default_settings(self, nwkid, value):
    """ SWV-ZFE/ZFU: settings applied to a manual 'On' (single irrigation session).

    The valve always closes by itself at the end of the session; the factory default is 2 minutes.
    All SONOFF_SWV_MANUAL_* params are folded into the single 0x501d array, so any of them triggers a full write.
    Layout (big endian): mode, total duration, irrigation duration, interval, amount unit, amount, fail-safe timeout.
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_manual_default_settings - Nwkid: %s value: %s" % (nwkid, value), nwkid)

    duration = _param_int(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_DURATION", 2, 1, SONOFF_SWV_MAX_IRRIGATION_MINUTES)
    mode = _param_choice(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_MODE", SONOFF_SWV_IRRIGATION_MODE, SONOFF_SWV_IRRIGATION_MODE["duration"])
    amount_unit = _param_choice(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT", SONOFF_SWV_AMOUNT_UNIT, SONOFF_SWV_AMOUNT_UNIT["liter"])
    amount = _param_int(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT", 0, 0, 10000)
    # Safety timeout mostly matters in capacity mode; default it to the duration so a session can never run longer than requested
    fail_safe = _param_int(self, nwkid, "SONOFF_SWV_MANUAL_FAIL_SAFE", duration, 0, SONOFF_SWV_MAX_IRRIGATION_MINUTES)
    interval = 10  # fixed upstream

    elements = (
        [mode]
        + list(duration.to_bytes(2, "big"))
        + list(duration.to_bytes(2, "big"))
        + list(interval.to_bytes(2, "big"))
        + [amount_unit]
        + list(amount.to_bytes(2, "big"))
        + list(fail_safe.to_bytes(2, "big"))
    )
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_ATTRIBUTE, ZCL_ARRAY_DATA_TYPE, _zcl_uint8_array(elements), ackIsDisabled=False)


def sonoff_swv_valve_alarm_settings(self, nwkid, value):
    """ SWV-ZFE/ZFU: water shortage / leak alarms and auto-close on shortage (0x5020).

    All SONOFF_SWV_ALARM_* params are folded into the single 0x5020 array, so any of them triggers a full write.
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_valve_alarm_settings - Nwkid: %s value: %s" % (nwkid, value), nwkid)

    enable_bits = 0
    if _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_SHORTAGE", 0, 0, 1):
        enable_bits |= 0b00001
    if _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_LEAK", 0, 0, 1):
        enable_bits |= 0b00010
    if _param_int(self, nwkid, "SONOFF_SWV_WATER_SHORTAGE_AUTO_CLOSE", 0, 0, 1):
        enable_bits |= 0b01000
    shortage_duration = _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_SHORTAGE_DURATION", 5, 1, 10)
    leak_duration = _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_LEAK_DURATION", 1, 1, 3)

    elements = [enable_bits, shortage_duration, leak_duration, 0x00]
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_SWV_VALVE_ALARM_SETTINGS_ATTRIBUTE, ZCL_ARRAY_DATA_TYPE, _zcl_uint8_array(elements), ackIsDisabled=False)


def sonoff_swv_water_flow_unit(self, nwkid, unit):
    """ SWV-ZFE/ZFU: unit used by the flow-meter attributes (0x5021, firmware >= 1.1.0) """
    if unit not in SONOFF_SWV_WATER_FLOW_UNIT:
        self.log.logging("Sonoff", "Error", "SONOFF_SWV_WATER_FLOW_UNIT invalid value %s, expected one of %s" % (unit, sorted(SONOFF_SWV_WATER_FLOW_UNIT)), nwkid)
        return
    self.log.logging("Sonoff", "Debug", "sonoff_swv_water_flow_unit - Nwkid: %s unit: %s" % (nwkid, unit), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_SWV_UNIT_OF_WATER_FLOW_ATTRIBUTE, ZCL_UINT8_DATA_TYPE, "%02x" % SONOFF_SWV_WATER_FLOW_UNIT[unit], ackIsDisabled=False)


def zbmicro_radio_power_turbo_mode(self, nwkid, mode):
    """ Enable/disable Radio Power Turbo Mode """
    RADIO_POWER_MODE = {
        "Normal": 0x09,
        "Turbo": 0x14
    }
    self.log.logging("Sonoff", "Debug", "zbmicro_radio_power_turbo_mode - Nwkid: %s value: %s" % (nwkid, mode), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_RADIO_POWER_TURBO_MODE, "29", "%08x" %RADIO_POWER_MODE.get( mode, 0x09), ackIsDisabled=False)


def sonoff_temperature_unit(self, nwkid, unit):
    """ Set temperature unit for Sonoff SNZB-02LD """
    if unit not in [0, 1]:  # 0 for Celsius, 1 for Fahrenheit
        self.log.logging("Sonoff", "Error", "Invalid temperature unit: %s. Use 0 for Celsius or 1 for Fahrenheit." % unit, nwkid)
        return  # Invalid unit, do not proceed
    self.log.logging("Sonoff", "Debug", "sonoff_temperature_unit - Nwkid: %s Unit: %s" % (nwkid, unit), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, "0000", "00", SONOFF_TEMPERATURE_UNIT_ATTRIBUTE, "21", "%04x" %unit, ackIsDisabled=False)


def sonoff_temperature_calibration(self, nwkid, calibration):
    """ Set temperature calibration for Sonoff SNZB-02LD """
    if not isinstance(calibration, int):
        self.log.logging("Sonoff", "Error", "Invalid calibration value: %s. It should be an integer." % calibration, nwkid)
        return  # Invalid calibration, do not proceed
    if calibration < -50 or calibration > 50:
        self.log.logging("Sonoff", "Error", "Calibration value out of range: %s. It should be between -100 and 100." % calibration, nwkid)
        return  # Calibration out of range, do not proceed
    # Convert calibration to a 16-bit signed integer
    calibration = int(calibration * 100)
    self.log.logging("Sonoff", "Debug", "sonoff_temperature_calibration - Nwkid: %s Calibration: %s" % (nwkid, calibration), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, "0000", "00", SONOFF_CALIBRATION_ATTRIBUTE, "29", "%04x" %calibration, ackIsDisabled=False)


# Dictionary to map Sonoff device parameters to their respective functions
SONOFF_DEVICE_PARAMETERS = {
    "SonOffTRVChildLock": sonoff_child_lock,
    "SonOffTRVWindowDectection": sonoff_open_window_detection,
    "SONOFF_TEMP_MAX": sonoff_temp_humi_ranges,
    "SONOFF_TEMP_MIN": sonoff_temp_humi_ranges,
    "SONOFF_HUMI_MAX": sonoff_temp_humi_ranges,
    "SONOFF_HUMI_MIN": sonoff_temp_humi_ranges,
    "SONOFF_REALTIME_IRRIGATION_DURATION": sonoff_realtime_irrigation_duration,
    "SONOFF_REALTIME_IRRIGATION_VOLUME": sonoff_realtime_irrigation_volume,
    "SONOFF_DAILY_IRRIGATION_VOLUME": sonoff_realtime_irrigation_daily_volume,
    "SONOFF_SWV_WATER_CLOSE_VALVE_TIMEOUT": auto_close_when_water_shortage,
    "SONOFF_CHILD_LOCK": sonoff_child_lock,
    "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_IRRIGATION_MODE": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_FAIL_SAFE": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_ALARM_WATER_SHORTAGE": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_ALARM_WATER_LEAK": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_WATER_SHORTAGE_AUTO_CLOSE": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_ALARM_WATER_SHORTAGE_DURATION": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_ALARM_WATER_LEAK_DURATION": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_WATER_FLOW_UNIT": sonoff_swv_water_flow_unit,
    "SONOFF_ZBMICRO_RADIO_POWER_TURBO_MODE": zbmicro_radio_power_turbo_mode,
    "SONOFF_TEMP_CALIBRATION": sonoff_temperature_calibration,
    "SONOFF_TEMP_UNIT": sonoff_temperature_unit
}
