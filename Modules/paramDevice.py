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
    Module: paramDevice.py

    Description: implement the parameter device specific

"""

from DevicesModules.custom_sonoff import SONOFF_DEVICE_PARAMETERS
from Modules.basicOutputs import (ballast_Configuration_max_level,
                                  ballast_Configuration_min_level)
from Modules.danfoss import (danfoss_covered, danfoss_exercise_day_of_week,
                             danfoss_exercise_trigger_time,
                             danfoss_orientation, danfoss_viewdirection)
from Modules.legrand_netatmo import (legrand_Dimmer_by_nwkid,
                                     legrand_enable_Led_IfOn_by_nwkid,
                                     legrand_enable_Led_InDark_by_nwkid,
                                     legrand_enable_Led_Shutter_by_nwkid)
from Modules.lumi import LUMI_DEVICE_PARAMETERS
from Modules.occupancy_settings import OCCUPANCY_DEVICE_PARAMETERS
from Modules.onoff_settings import ONOFF_DEVICE_PARAMETERS
from Modules.philips import philips_led_indication
from Modules.schneider_wiser import SCHNEIDER_DEVICE_PARAMETERS
from Modules.tools import getEpForCluster
from Modules.tuya import TUYA_DEVICE_PARAMETERS
from Modules.tuyaSiren import TUYA_SIREN_DEVICE_PARAMETERS
from Modules.tuyaTRV import TUYA_TRV_DEVICE_PARAMETERS
from Modules.tuyaTS011F import TUYA_TS011F_DEVICE_PARAMETERS
from Modules.tuyaTS0601 import ts0601_extract_data_point_infos, ts0601_settings


def Ballast_max_level(self, nwkid, max_level):
    ballast_Configuration_max_level(self, nwkid, max_level)


def Ballast_min_level(self, nwkid, min_level):
    ballast_Configuration_min_level(self, nwkid, min_level)


def ias_wd_sirene_max_alarm_dureation( self, nwkid, duration):
    if self.iaszonemgt:
        Epout = getEpForCluster(self, nwkid, "0502", strict=True)
        
        if Epout is not None and len(Epout) == 1:
            self.iaszonemgt.IAS_WD_Maximum_duration( nwkid, Epout[0], duration)

def ias_sensitivity(self, nwkid, sensitivity):
    if self.iaszonemgt:
        self.iaszonemgt.ias_sensitivity( nwkid, sensitivity)



DEVICE_PARAMETERS = {
    "HueLedIndication": philips_led_indication,
    "netatmoLedIfOn": legrand_enable_Led_IfOn_by_nwkid,
    "netatmoLedInDark": legrand_enable_Led_InDark_by_nwkid,
    "netatmoLedShutter": legrand_enable_Led_Shutter_by_nwkid,
    "netatmoEnableDimmer": legrand_Dimmer_by_nwkid,
    "BallastMaxLevel": Ballast_max_level,
    "BallastMinLevel": Ballast_min_level,
    "eTRVExerciseDay": danfoss_exercise_day_of_week,
    "eTRVExerciseTime": danfoss_exercise_trigger_time,
    "DanfossCovered": danfoss_covered,
    "DanfossTRVOrientation": danfoss_orientation,
    "DanfossViewDirection": danfoss_viewdirection,
    "SireneMaxAlarmDuration": ias_wd_sirene_max_alarm_dureation,
    "IASsensitivity": ias_sensitivity,
}

    


def sanity_check_of_param(self, NwkId):

    self.log.logging("Heartbeat", "Debug", f"sanity_check_of_param  {NwkId}")
    
    # Load specific settings
    DEVICE_PARAMETERS.update(ONOFF_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(OCCUPANCY_DEVICE_PARAMETERS)
    
    # Load Manufacturer specific settings
    DEVICE_PARAMETERS.update(SONOFF_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(TUYA_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(TUYA_TS011F_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(TUYA_TRV_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(TUYA_SIREN_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(SCHNEIDER_DEVICE_PARAMETERS)
    
    DEVICE_PARAMETERS.update(LUMI_DEVICE_PARAMETERS)

    param_data = self.ListOfDevices.get(NwkId, {}).get("Param", {})
    model_name = self.ListOfDevices.get(NwkId, {}).get("Model", "")

    for param, value in param_data.items():
        self.log.logging("Heartbeat", "Debug", f"sanity_check_of_param  {param}, {value}")
        
        dps_mapping = ts0601_extract_data_point_infos( self, model_name) 
        if dps_mapping:
            ts0601_settings( self, NwkId, dps_mapping, param, value)

        elif param in DEVICE_PARAMETERS:
            DEVICE_PARAMETERS[param](self, NwkId, value)