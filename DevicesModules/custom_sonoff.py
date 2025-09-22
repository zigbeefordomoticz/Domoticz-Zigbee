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
    "SONOFF_ZBMICRO_RADIO_POWER_TURBO_MODE": zbmicro_radio_power_turbo_mode,
    "SONOFF_TEMP_CALIBRATION": sonoff_temperature_calibration,
    "SONOFF_TEMP_UNIT": sonoff_temperature_unit
}
