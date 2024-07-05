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

from Modules.basicOutputs import write_attribute
from Modules.tools import get_device_config_param
from Modules.zigateConsts import ZIGATE_EP

SUNRICHER_MAUFACTURER_NAME = "SUNRICHER"
SUNRICHER_MANUFACTURER_ID = "1224"
SUNRICHER_PIR_SENSOR_SENSITIVITY = "1000"
SUNRICHER_MOTION_DETECTION_BLIND_TIME = "1001"
SUNRICHER_MOTION_DETECTION_PULSE_COUNTER = "1002"
SUNRICHER_PIR_SENSOR_TRIGGER_TIME_INTERVAL = "1003"

OCCUPANCY_CLUSTERID = "0406"


def is_sunricher_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == SUNRICHER_MANUFACTURER_ID or self.ListOfDevices[nwkid]["Manufacturer Name"] == SUNRICHER_MAUFACTURER_NAME


def sunricher_pir_sensor_sensitivity(self, nwkid, sensitivity):
    self.log.logging("Sunricher", "Debug", "sunricher_pir_sensor_sensitivity - Nwkid: %s Mode: %s" % (nwkid, sensitivity))
    write_attribute(self, nwkid, ZIGATE_EP, "01", OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_PIR_SENSOR_SENSITIVITY, "30", "%02x" %sensitivity, ackIsDisabled=False)


def sunricher_motion_detection_blind_time(self, nwkid, blind_time):
    self.log.logging("Sunricher", "Debug", "sunricher_motion_detection_blind_time - Nwkid: %s Mode: %s" %(nwkid, blind_time))
    write_attribute(self, nwkid, ZIGATE_EP, "01", OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_MOTION_DETECTION_BLIND_TIME, "20", "%02x" %blind_time, ackIsDisabled=False)


def sunricher_motion_detection_pulse_counter(self, nwkid, pulse_setting):
    self.log.logging("Sunricher", "Debug", "sunricher_motion_detection_pulse_counter - Nwkid: %s Mode: %s" %(nwkid, pulse_setting))
    write_attribute(self, nwkid, ZIGATE_EP, "01", OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_MOTION_DETECTION_PULSE_COUNTER, "30", "%02x" %pulse_setting, ackIsDisabled=False)

def sunricher_pir_sensor_trigger_time_interval(self, nwkid, trigger_time_interval):
    self.log.logging("Sunricher", "Debug", "sunricher_pir_sensor_trigger_time_interval - Nwkid: %s Mode: %s" %(nwkid, sunricher_pir_sensor_trigger_time_interval))
    write_attribute(self, nwkid, ZIGATE_EP, "01", OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_PIR_SENSOR_TRIGGER_TIME_INTERVAL, "30", "%02x" %trigger_time_interval, ackIsDisabled=False)


SUNRICHER_DEVICE_PARAMETERS = {
    "Sunricher_PIR_SENSITIVITY": sunricher_pir_sensor_sensitivity,
    "Sunricher_MOTION_BLIND_TIME": sunricher_motion_detection_blind_time,
    "Sunricher_MOTION_PULSE_COUNTER": sunricher_motion_detection_pulse_counter,
    "Sunricher_PIR_TRIGGER_TIME_INTERVAL": sunricher_pir_sensor_trigger_time_interval,
}
