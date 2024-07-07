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

from Modules.basicOutputs import read_attribute, write_attribute
from Modules.zigateConsts import ZIGATE_EP

SUNRICHER_MAUFACTURER_NAME = "SUNRICHER"
SUNRICHER_MANUFACTURER_ID = "1224"

OCCUPANCY_ENDPOINT = "01"
OCCUPANCY_CLUSTERID = "0406"
SUNRICHER_PIR_SENSOR_SENSITIVITY = "1000"
SUNRICHER_MOTION_DETECTION_BLIND_TIME = "1001"
SUNRICHER_MOTION_DETECTION_PULSE_COUNTER = "1002"
SUNRICHER_PIR_SENSOR_TRIGGER_TIME_INTERVAL = "1003"

TEMPERATURE_ENDPOINT = "03"
TEMPERATURE_CLUSTERID = "0402"
SUNRICHER_TEMPERATURE_COMPENSATION = "1000"   # Int8s

HUMIDITY_ENDPOINT = "04"
HUMIDITY_CLUSTERID = "0405"
SUNRICHER_HUMIDITY_COMPENSATION = "1000"   # Int8s



def is_sunricher_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == SUNRICHER_MANUFACTURER_ID or self.ListOfDevices[nwkid]["Manufacturer Name"] == SUNRICHER_MAUFACTURER_NAME


def sunricher_pir_sensor_sensitivity(self, nwkid, sensitivity):
    self.log.logging("Sunricher", "Debug", "sunricher_pir_sensor_sensitivity - Nwkid: %s Sensitivity: %s" % (nwkid, sensitivity))
    write_attribute(self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_PIR_SENSOR_SENSITIVITY, "30", "%02x" %sensitivity, ackIsDisabled=False)
    read_attribute( self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, "00", "01", SUNRICHER_MANUFACTURER_ID, 0x01, SUNRICHER_PIR_SENSOR_SENSITIVITY, ackIsDisabled=False )


def sunricher_motion_detection_blind_time(self, nwkid, blind_time):
    self.log.logging("Sunricher", "Debug", "sunricher_motion_detection_blind_time - Nwkid: %s Blind Time: %s" %(nwkid, blind_time))
    write_attribute(self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_MOTION_DETECTION_BLIND_TIME, "20", "%02x" %blind_time, ackIsDisabled=False)
    read_attribute( self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, "00", "01", SUNRICHER_MANUFACTURER_ID, 0x01, SUNRICHER_MOTION_DETECTION_BLIND_TIME, ackIsDisabled=False )


def sunricher_motion_detection_pulse_counter(self, nwkid, pulse_setting):
    self.log.logging("Sunricher", "Debug", "sunricher_motion_detection_pulse_counter - Nwkid: %s Pulse Setting: %s" %(nwkid, pulse_setting))
    write_attribute(self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_MOTION_DETECTION_PULSE_COUNTER, "30", "%02x" %pulse_setting, ackIsDisabled=False)
    read_attribute( self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, "00", "01", SUNRICHER_MANUFACTURER_ID, 0x01, SUNRICHER_MOTION_DETECTION_PULSE_COUNTER, ackIsDisabled=False )


def sunricher_pir_sensor_trigger_time_interval(self, nwkid, trigger_time_interval):
    self.log.logging("Sunricher", "Debug", "sunricher_pir_sensor_trigger_time_interval - Nwkid: %s Trigger Time Interval: %s" %(nwkid, sunricher_pir_sensor_trigger_time_interval))
    write_attribute(self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_PIR_SENSOR_TRIGGER_TIME_INTERVAL, "30", "%02x" %trigger_time_interval, ackIsDisabled=False)
    read_attribute( self, nwkid, ZIGATE_EP, OCCUPANCY_ENDPOINT, OCCUPANCY_CLUSTERID, "00", "01", SUNRICHER_MANUFACTURER_ID, 0x01, SUNRICHER_PIR_SENSOR_TRIGGER_TIME_INTERVAL, ackIsDisabled=False )


def sunricher_temperature_compensation(self, nwkid, compensation):
    self.log.logging("Sunricher", "Debug", "sunricher_temperature_compensation - Nwkid: %s compensation: %s" % (nwkid, compensation))
    if compensation < 0:
        compensation = _two_complement( compensation )
        self.log.logging( "Sunricher", "Debug", "sunricher_temperature_compensation - 2 complement form of compensation offset on %s off %s" % (nwkid, compensation), )

    write_attribute(self, nwkid, ZIGATE_EP, TEMPERATURE_ENDPOINT, TEMPERATURE_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_TEMPERATURE_COMPENSATION, "28", "%02x" %compensation, ackIsDisabled=False)
    read_attribute( self, nwkid, ZIGATE_EP, TEMPERATURE_ENDPOINT, TEMPERATURE_CLUSTERID, "00", "01", SUNRICHER_MANUFACTURER_ID, 0x01, SUNRICHER_TEMPERATURE_COMPENSATION, ackIsDisabled=False )


def sunricher_humidity_compensation(self, nwkid, compensation):
    self.log.logging("Sunricher", "Debug", "sunricher_humidity_compensation - Nwkid: %s compensation: %s" % (nwkid, compensation))
    if compensation < 0:
        compensation = _two_complement( compensation )
        self.log.logging( "Sunricher", "Debug", "sunricher_temperature_compensation - 2 complement form of compensation offset on %s off %s" % (nwkid, compensation), )

    write_attribute(self, nwkid, ZIGATE_EP, HUMIDITY_ENDPOINT, HUMIDITY_CLUSTERID, SUNRICHER_MANUFACTURER_ID, "01", SUNRICHER_HUMIDITY_COMPENSATION, "28", "%02x" %compensation, ackIsDisabled=False)
    read_attribute( self, nwkid, ZIGATE_EP, HUMIDITY_ENDPOINT, HUMIDITY_CLUSTERID, "00", "01", SUNRICHER_MANUFACTURER_ID, 0x01, SUNRICHER_HUMIDITY_COMPENSATION, ackIsDisabled=False )


def _two_complement( negative_value ):
    # in two’s complement form
    return int(hex(-negative_value - pow(2, 32))[9:], 16)


SUNRICHER_DEVICE_PARAMETERS = {
    "Sunricher_PIR_SENSITIVITY": sunricher_pir_sensor_sensitivity,
    "Sunricher_MOTION_BLIND_TIME": sunricher_motion_detection_blind_time,
    "Sunricher_MOTION_PULSE_COUNTER": sunricher_motion_detection_pulse_counter,
    "Sunricher_PIR_TRIGGER_TIME_INTERVAL": sunricher_pir_sensor_trigger_time_interval,
    "Sunricher_Temperature_Compensation": sunricher_temperature_compensation,
    "Sunricher_Humidity_Compensation": sunricher_humidity_compensation
}
