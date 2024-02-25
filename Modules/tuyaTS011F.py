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

from Modules.basicOutputs import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN, get_device_config_param
from Modules.zigateConsts import ZIGATE_EP
from Modules.tuyaTools import store_tuya_attribute


# Command 0xe6
#          Temp in °/ Power
# Payload: 05000064/0701000d 
# Over & Under Voltage; Over current
# Command0xe7
#           Current   Over V   Under V
# Payload: /01000041/030000fa/04000064 All Off 65A, 250V, 100V
# Payload: /01010041/030100fa/04010064 All On 65A, 250V, 100V
#          

DATA_POINTS = {
    "01": "overCurrent",
    "03": "overVoltage",
    "04": "underVoltage",
    "05": "overTemperature",
    "07": "overPower"
}

def tuya_read_cluster_e001(self, Devices, NwkId, source_ep, clusterId, target_nwkid, target_ep, payload):
    self.log.logging("TuyaTS011F", "Log", f"tuya_read_cluster_e001 - {clusterId} - {payload}")
    #'tuya_read_cluster_e001 - e001 - 09/4a/e6/05/01/0064 /0701000d'
    #'tuya_read_cluster_e001 - e001 - 09/4b/e6/05/01/0064 /0701000d'
    #'tuya_read_cluster_e001 - e001 - 09/4c/e7/01/01/0041 /030100fa040100c8'
    #'tuya_read_cluster_e001 - e001 - 09/4d/e7/01/01/0041 /030100fa040100c8'
    
    fcf = payload[:2]
    sqn = payload[2:4]
    cmd = payload[4:6]

    
    if cmd in ("e6", "e7"):
        data = payload[6:]
        ts011f_params = _extract_enabled_and_value( self, data)
        for value_type, enabled, threshold_value in ts011f_params:
            self.log.logging("TuyaTS011F", "Debug", f"tuya_read_cluster_e001 {value_type} {enabled} {threshold_value}")
            if value_type in DATA_POINTS:
                store_tuya_attribute(self, NwkId, DATA_POINTS[ value_type ] + "Breaker", enabled)
                store_tuya_attribute(self, NwkId, DATA_POINTS[ value_type ] + "Threshold", threshold_value)
            else:
                self.log.logging("TuyaTS011F", "Debug", f"tuya_read_cluster_e001 - unknown data point {value_type} {enabled} {threshold_value}")
                
                                     
def _extract_enabled_and_value( self, data ):
    self.log.logging("TuyaTS011F", "Debug", f"_extract_enabled_and_value {data}")

    tuples = []
    for i in range(0, len(data), 8):
        value_type = data[i:i + 2]
        enabled = int(data[i + 2:i + 4], 16)
        threshold = int(data[i + 4:i + 8], 16)
        data_tuple = (value_type, enabled, threshold)
        tuples.append(data_tuple)
    return tuples

def tuya_ts011F_threshold_overTemperatureBreaker( self, NwkId, enablement):
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overTemperatureBreaker %s %s" %(NwkId, enablement), NwkId)
    tuya_ts011F_e6(self, NwkId, )


def tuya_ts011F_threshold_overPowerBreaker( self, NwkId, enablement):
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overPowerBreaker %s %s" %(NwkId, enablement), NwkId)
    tuya_ts011F_e6(self, NwkId, )


def tuya_ts011F_threshold_overCurrentBreaker( self, NwkId, enablement):
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overCurrentBreaker %s %s" %(NwkId, enablement), NwkId)
    tuya_ts011F_e7(self, NwkId, )


def tuya_ts011F_threshold_overVoltageBreaker( self, NwkId, enablement):
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overVoltageBreaker %s %s" %(NwkId, enablement), NwkId)
    tuya_ts011F_e7(self, NwkId, )


def tuya_ts011F_threshold_underVoltageBreaker( self, NwkId, enablement):
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_underVoltageBreaker %s %s" %(NwkId, enablement), NwkId)
    tuya_ts011F_e7(self, NwkId, )


def tuya_ts011F_e6(self, NwkId, ):
    power_threshold = int(get_device_config_param( self, NwkId, "TS011F_overPowerThreshold"))
    temp_threshold = int(get_device_config_param( self, NwkId, "TS011F_overTemperatureThreshold"))
    power_breaker = int(get_device_config_param( self, NwkId, "TS011F_overPowerBreaker"))
    temp_breaker = int(get_device_config_param( self, NwkId, "TS011F_overTemperatureBreaker"))

    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e6"
    for threshold_idx, threshold_value, breaker in ( 
        ("05", temp_threshold, temp_breaker), 
        ("07", power_threshold, power_breaker),
    ):
        payload += threshold_idx + "%02x" %breaker + "%04x" % threshold_value
    
    self.log.logging("TuyaTS011F", "Debug", f"tuya_ts011F_e6 {temp_breaker} {temp_threshold} {power_breaker} {power_threshold}", NwkId)
    self.log.logging("TuyaTS011F", "Debug", f"tuya_ts011F_e6 {payload}", NwkId)
    
    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_ts011F_e7(self, NwkId, ):

    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    under_volt_threshold = int(get_device_config_param( self, NwkId, "TS011F_underVoltageThreshold"))
    over_volt_threshold = int(get_device_config_param( self, NwkId, "TS011F_overVoltageThreshold"))
    current_threshold = int(get_device_config_param( self, NwkId, "TS011F_overCurrentThreshold"))
    under_volt_breaker = int(get_device_config_param( self, NwkId, "TS011F_underVoltageBreaker"))
    over_volt_breaker = int(get_device_config_param( self, NwkId, "TS011F_overVoltageBreaker"))
    current_breaker = int(get_device_config_param( self, NwkId, "TS011F_overCurrentBreaker"))

    payload = "11" + sqn + "e7"
    for threshold_idx, threshold_value, breaker in ( 
        ("01", current_threshold, current_breaker),
        ("03", over_volt_threshold, over_volt_breaker),
        ("04", under_volt_threshold, under_volt_breaker),
    ):
        payload += threshold_idx + "%02x" %breaker + "%04x" % threshold_value
    
    self.log.logging("TuyaTS011F", "Debug", f"tuya_ts011F_e6 {current_breaker} {current_threshold} {over_volt_breaker} {over_volt_threshold} {under_volt_breaker} {under_volt_threshold}", NwkId)
    self.log.logging("TuyaTS011F", "Debug", f"tuya_ts011F_e7 {payload}", NwkId)

    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


TUYA_TS011F_DEVICE_PARAMETERS = {
    "TS011F_overTemperatureBreaker": tuya_ts011F_threshold_overTemperatureBreaker,
    "TS011F_overPowerBreaker": tuya_ts011F_threshold_overPowerBreaker,
    "TS011F_overCurrentBreeaker": tuya_ts011F_threshold_overCurrentBreaker,
    "TS011F_overVoltageBreaker": tuya_ts011F_threshold_overVoltageBreaker,
    "TS011F_underVoltageBreaker": tuya_ts011F_threshold_underVoltageBreaker
}
