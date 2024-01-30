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
                                  ballast_Configuration_min_level,
                                  set_PIROccupiedToUnoccupiedDelay,
                                  set_poweron_afteroffon)
from Modules.danfoss import (danfoss_covered, danfoss_exercise_day_of_week,
                             danfoss_exercise_trigger_time,
                             danfoss_orientation, danfoss_viewdirection)
from Modules.enki import enki_set_poweron_after_offon_device
from Modules.legrand_netatmo import (legrand_Dimmer_by_nwkid,
                                     legrand_enable_Led_IfOn_by_nwkid,
                                     legrand_enable_Led_InDark_by_nwkid,
                                     legrand_enable_Led_Shutter_by_nwkid)
from Modules.lumi import (RTCGQ14LM_trigger_indicator,
                          RTCZCGQ11LM_motion_opple_approach_distance,
                          RTCZCGQ11LM_motion_opple_monitoring_mode,
                          RTCZCGQ11LM_motion_opple_sensitivity,
                          aqara_detection_interval, enable_click_mode_aqara,
                          setXiaomiVibrationSensitivity,
                          xiaomi_aqara_switch_mode_switch,
                          xiaomi_flip_indicator_light,
                          xiaomi_led_disabled_night, xiaomi_opple_mode,
                          xiaomi_switch_operation_mode_opple,
                          xiaomi_switch_power_outage_memory)
from Modules.philips import (philips_led_indication,
                             philips_set_pir_occupancySensibility,
                             philips_set_poweron_after_offon_device)
from Modules.readAttributes import (ReadAttributeRequest_0006_400x,
                                    ReadAttributeRequest_0406_0010)
from Modules.schneider_wiser import (iTRV_open_window_detection,
                                     wiser_home_lockout_thermostat,
                                     wiser_lift_duration)
from Modules.tools import get_deviceconf_parameter_value, getEpForCluster
from Modules.tuya import (SmartRelayStatus01, SmartRelayStatus02,
                          SmartRelayStatus03, SmartRelayStatus04,
                          get_tuya_attribute, ts110e_light_type,
                          ts110e_switch01_type, ts110e_switch02_type,
                          tuya_backlight_command, tuya_cmd_ts004F,
                          tuya_curtain_mode, tuya_energy_childLock,
                          tuya_external_switch_mode, tuya_garage_run_time,
                          tuya_motion_zg204l_keeptime,
                          tuya_motion_zg204l_sensitivity,
                          tuya_pir_keep_time_lookup,
                          tuya_radar_motion_radar_detection_delay,
                          tuya_radar_motion_radar_fading_time,
                          tuya_radar_motion_radar_max_range,
                          tuya_radar_motion_radar_min_range,
                          tuya_radar_motion_sensitivity,
                          tuya_switch_indicate_light, tuya_switch_relay_status,
                          tuya_TS0004_back_light, tuya_TS0004_indicate_light,
                          tuya_window_cover_calibration,
                          tuya_window_cover_motor_reversal)
from Modules.tuyaSiren import (tuya_siren2_alarm_duration,
                               tuya_siren2_alarm_melody,
                               tuya_siren2_alarm_volume)
from Modules.tuyaTRV import (tuya_trv_boost_time, tuya_trv_calibration,
                             tuya_trv_child_lock, tuya_trv_eco_temp,
                             tuya_trv_holiday_setpoint,
                             tuya_trv_set_confort_temperature,
                             tuya_trv_set_eco_temperature,
                             tuya_trv_set_max_setpoint,
                             tuya_trv_set_min_setpoint,
                             tuya_trv_set_opened_window_temp,
                             tuya_trv_thermostat_sensor_mode,
                             tuya_trv_window_detection)
from Modules.tuyaTS011F import (tuya_ts011F_threshold_overCurrentBreaker,
                                tuya_ts011F_threshold_overPowerBreaker,
                                tuya_ts011F_threshold_overTemperatureBreaker,
                                tuya_ts011F_threshold_overVoltageBreaker,
                                tuya_ts011F_threshold_underVoltageBreaker)
from Modules.tuyaTS0601 import (TS0601_COMMANDS, ts0601_actuator,
                                ts0601_extract_data_point_infos)


def Ballast_max_level(self, nwkid, max_level):
    ballast_Configuration_max_level(self, nwkid, max_level)


def Ballast_min_level(self, nwkid, min_level):
    ballast_Configuration_min_level(self, nwkid, min_level)


def param_Occupancy_settings_PIROccupiedToUnoccupiedDelay(self, nwkid, delay):
    # Based on Philips HUE
    # 0x00 default
    # The PIROccupiedToUnoccupiedDelay attribute is 16 bits in length and
    # specifies the time delay, in seconds,before the PIR sensor changes to
    # its unoccupied state after the last detection of movement in the sensed area.

    if self.ListOfDevices[nwkid]["Manufacturer"] == "100b" or self.ListOfDevices[nwkid]["Manufacturer Name"] == "Philips":  # Philips
        if "02" not in self.ListOfDevices[nwkid]["Ep"]:
            return
        if "0406" not in self.ListOfDevices[nwkid]["Ep"]["02"]:
            return
        if "0010" not in self.ListOfDevices[nwkid]["Ep"]["02"]["0406"]:
            set_PIROccupiedToUnoccupiedDelay(self, nwkid, delay)
            ReadAttributeRequest_0406_0010(self, nwkid)
            return
        
        current_delay = int(self.ListOfDevices[nwkid]["Ep"]["02"]["0406"]["0010"], 16) if isinstance( self.ListOfDevices[nwkid]["Ep"]["02"]["0406"]["0010"], str) else self.ListOfDevices[nwkid]["Ep"]["02"]["0406"]["0010"]
        if current_delay != delay:
            set_PIROccupiedToUnoccupiedDelay(self, nwkid, delay)
            ReadAttributeRequest_0406_0010(self, nwkid)

    elif self.ListOfDevices[nwkid]["Manufacturer"] == "1015" or self.ListOfDevices[nwkid]["Manufacturer Name"] == "frient A/S":  # Frientd
        # delay = 10 * delay # Tenth of seconds
        for ep in ["22", "28", "29"]:
            if ep == "28" and "PIROccupiedToUnoccupiedDelay_28" in self.ListOfDevices[nwkid]["Param"]:
                delay = int(self.ListOfDevices[nwkid]["Param"]["PIROccupiedToUnoccupiedDelay_28"])
            elif ep == "29" and "PIROccupiedToUnoccupiedDelay_29" in self.ListOfDevices[nwkid]["Param"]:
                delay = int(self.ListOfDevices[nwkid]["Param"]["PIROccupiedToUnoccupiedDelay_29"])
            if ep not in self.ListOfDevices[nwkid]["Ep"]:
                continue
            if "0406" not in self.ListOfDevices[nwkid]["Ep"][ep]:
                continue
            if "0010" not in self.ListOfDevices[nwkid]["Ep"][ep]["0406"]:
                set_PIROccupiedToUnoccupiedDelay(self, nwkid, delay, ListOfEp=[ep])
                ReadAttributeRequest_0406_0010(self, nwkid)
                return
            current_delay = int(self.ListOfDevices[nwkid]["Ep"][ep]["0406"]["0010"], 16) if isinstance( self.ListOfDevices[nwkid]["Ep"][ep]["0406"]["0010"], str) else self.ListOfDevices[nwkid]["Ep"][ep]["0406"]["0010"]
            if current_delay != delay:
                set_PIROccupiedToUnoccupiedDelay(self, nwkid, delay, ListOfEp=[ep])
                ReadAttributeRequest_0406_0010(self, nwkid)

    else:
        self.log.logging("Heartbeat", "Log", "=====> Unknown Manufacturer/Name")


def param_PowerOnAfterOffOn(self, nwkid, mode):
    # 0 - stay Off after a Off/On
    # 1 - stay On after a Off/On
    # 255 - stay to previous state after a Off/On ( or 2 for BlitzWolf)

    model = ""
    if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"]:
        model = self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"]
        
    self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for %s mode: %s for model: %s " % (nwkid, mode, model), nwkid)
    if int(mode) not in (0, 1, 2, 255):
        return

    if "Manufacturer" not in self.ListOfDevices[nwkid]:
        return

    if (
        self.ListOfDevices[nwkid]["Manufacturer"] == "100b"  # Philips
        or model == "FNB56-ZCW25FB2.1"
    ):
        if not _check_attribute_exist( self, nwkid, "0b", "0006", "4003"):
            return

        if self.ListOfDevices[nwkid]["Ep"]["0b"]["0006"]["4003"] != str(mode):
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for Philips for %s mode: %s" % (nwkid, mode), nwkid)
            philips_set_poweron_after_offon_device(self, mode, nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)

    elif get_deviceconf_parameter_value(self, model, "PowerOnOffStateAttribute8002", return_default=False):
        if not _check_attribute_exist( self, nwkid, "01", "0006", "8002"):
            return
        if self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]["8002"] == "2" and str(mode) == "255":
            return
        if self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]["8002"] != str(mode):
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for Tuya for %s mode: %s" % (nwkid, mode), nwkid)
            set_poweron_afteroffon(self, nwkid, mode)
            ReadAttributeRequest_0006_400x(self, nwkid)
 
    elif self.ListOfDevices[nwkid]["Manufacturer"] == "1277":  # Enki Leroy Merlin
        if not _check_attribute_exist( self, nwkid, "01", "0006", "4003"):
            return

        if self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]["4003"] != str(mode):
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for Enki for %s mode: %s" % (nwkid, mode), nwkid)
            enki_set_poweron_after_offon_device(self, mode, nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)

    elif model in (
        "TS0601-switch",
        "TS0601-2Gangs-switch",
        "TS0601-Energy",
    ):
        if get_tuya_attribute(self, nwkid, "RelayStatus") != mode:
            tuya_switch_relay_status(self, nwkid, mode)

    else:
        # Ikea, Legrand,
        for ep in self.ListOfDevices[nwkid]["Ep"]:
            if not _check_attribute_exist( self, nwkid, ep, "0006", "4003"):
                continue

            if self.ListOfDevices[nwkid]["Ep"][ep]["0006"]["4003"] == str(mode):
                continue
            elif _check_attribute_exist( self, nwkid, ep, "0006", "8002") and self.ListOfDevices[nwkid]["Ep"][ep]["0006"]["8002"] == str(mode):
                continue
            
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for %s mode: %s" % (nwkid, mode), nwkid)
            set_poweron_afteroffon(self, nwkid, mode)
            ReadAttributeRequest_0006_400x(self, nwkid)


def _check_attribute_exist( self, nwkid, ep, cluster, attribute):
    if ep not in self.ListOfDevices[nwkid]["Ep"]:
        self.log.logging("Heartbeat", "Debug", "No ep: %s" %ep, nwkid)
        return False
    if cluster not in self.ListOfDevices[nwkid]["Ep"][ ep ]:
        self.log.logging("Heartbeat", "Debug", "No Cluster: %s" %cluster, nwkid)
        return False
    if attribute not in self.ListOfDevices[nwkid]["Ep"][ ep ][ cluster ]:
        self.log.logging("Heartbeat", "Debug", "No Attribute: %s" %attribute, nwkid)
        return False
    return True
   
   
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
    "PowerOnAfterOffOn": param_PowerOnAfterOffOn,
    "PIROccupiedToUnoccupiedDelay": param_Occupancy_settings_PIROccupiedToUnoccupiedDelay,
    "occupancySensibility": philips_set_pir_occupancySensibility,
    "netatmoLedIfOn": legrand_enable_Led_IfOn_by_nwkid,
    "netatmoLedInDark": legrand_enable_Led_InDark_by_nwkid,
    "netatmoLedShutter": legrand_enable_Led_Shutter_by_nwkid,
    "netatmoEnableDimmer": legrand_Dimmer_by_nwkid,
    "SensorMode": tuya_trv_thermostat_sensor_mode,
    "LightIndicator": tuya_switch_indicate_light,
    "TuyaEnergyChildLock": tuya_energy_childLock,
    "BallastMaxLevel": Ballast_max_level,
    "BallastMinLevel": Ballast_min_level,
    "WiserLockThermostat": wiser_home_lockout_thermostat,
    "WiseriTrvWindowOpen": iTRV_open_window_detection,
    "TuyaMotoReversal": tuya_window_cover_motor_reversal,
    "TuyaBackLight": tuya_backlight_command,
    "TuyaCurtainMode": tuya_curtain_mode,
    "TuyaCalibrationTime": tuya_window_cover_calibration,
    "eTRVExerciseDay": danfoss_exercise_day_of_week,
    "eTRVExerciseTime": danfoss_exercise_trigger_time,
    "DanfossCovered": danfoss_covered,
    "DanfossTRVOrientation": danfoss_orientation,
    "DanfossViewDirection": danfoss_viewdirection,
    "TS004FMode": tuya_cmd_ts004F,
    "vibrationAqarasensitivity": setXiaomiVibrationSensitivity,
    "BRT100WindowsDetection": tuya_trv_window_detection,
    "BRT100ChildLock": tuya_trv_child_lock,
    "TuyaTRV5_ChildLock": tuya_trv_child_lock,
    "TuyaTRV5_EcoTemp": tuya_trv_set_eco_temperature,
    "TuyaTRV5_ConfortTemp": tuya_trv_set_confort_temperature,
    "TuyaTRV5_OpenedWindowTemp": tuya_trv_set_opened_window_temp,
    "BRT100BoostDuration": tuya_trv_boost_time,
    "TuyaTRV5_BoostTime": tuya_trv_boost_time,
    "TuyaTRV5_Calibration": tuya_trv_calibration,
    "TuyaTRV5_HolidaySetPoint": tuya_trv_holiday_setpoint,
    "BRT100Calibration": tuya_trv_calibration,
    "BRT100SetpointEco": tuya_trv_eco_temp,
    "BRT100MaxSetpoint": tuya_trv_set_max_setpoint,
    "BRT100MinSetpoint": tuya_trv_set_min_setpoint,
    "moesCalibrationTime": tuya_window_cover_calibration,
    "TuyaAlarmLevel": tuya_siren2_alarm_volume,
    "TuyaAlarmDuration": tuya_siren2_alarm_duration,
    "TuyaAlarmMelody": tuya_siren2_alarm_melody,
    "SireneMaxAlarmDuration": ias_wd_sirene_max_alarm_dureation,
    "TuyaGarageOpenerRunTime": tuya_garage_run_time,
    "TuyaSwitchMode": tuya_external_switch_mode,
    "SmartSwitchBackLight": tuya_TS0004_back_light,
    "SmartSwitchIndicateLight": tuya_TS0004_indicate_light,  
    "SmartRelayStatus01": SmartRelayStatus01,
    "SmartRelayStatus02": SmartRelayStatus02,
    "SmartRelayStatus03": SmartRelayStatus03,
    "SmartRelayStatus04": SmartRelayStatus04,
    "RTCZCGQ11LMMotionSensibility": RTCZCGQ11LM_motion_opple_sensitivity,
    "RTCZCGQ11LMApproachDistance": RTCZCGQ11LM_motion_opple_approach_distance,
    "RTCZCGQ11LMMonitoringMode": RTCZCGQ11LM_motion_opple_monitoring_mode,
    "ZG204Z_MotionSensivity": tuya_motion_zg204l_sensitivity,
    "ZG204Z_MotionOccupancyTime": tuya_motion_zg204l_keeptime,
    "RadarMotionSensitivity": tuya_radar_motion_sensitivity,
    "RadarMotionMinRange": tuya_radar_motion_radar_min_range,
    "RadarMotionMaxRange": tuya_radar_motion_radar_max_range,
    "RadarMotionDelay": tuya_radar_motion_radar_detection_delay,
    "RadarMotionFading": tuya_radar_motion_radar_fading_time,
    "AqaraOpple_switch_power_outage_memory": xiaomi_switch_power_outage_memory,
    "AqaraOpple_led_disabled_night": xiaomi_led_disabled_night,
    "AqaraOpple_flip_indicator_light": xiaomi_flip_indicator_light,
    "AqaraOpple_switch_operation_mode_opple": xiaomi_switch_operation_mode_opple,
    "AqaraOpple_aqara_switch_mode_switch": xiaomi_aqara_switch_mode_switch,
    "AqaraOppleMode": xiaomi_opple_mode,
    "TuyaPIRKeepTime": tuya_pir_keep_time_lookup,
    "IASsensitivity": ias_sensitivity,
    "RTCGQ14LMTriggerIndicator": RTCGQ14LM_trigger_indicator,
    "AqaraDetectionInterval": aqara_detection_interval,
    "WiserShutterDuration": wiser_lift_duration,
    "AqaraMultiClick": enable_click_mode_aqara,
    "TS110ELightType": ts110e_light_type,
    "TS110ESwitch01Type": ts110e_switch01_type,
    "TS110ESwitch02Type": ts110e_switch02_type,
    "TS011F_overTemperatureBreaker": tuya_ts011F_threshold_overTemperatureBreaker,
    "TS011F_overPowerBreaker": tuya_ts011F_threshold_overPowerBreaker,
    "TS011F_overCurrentBreeaker": tuya_ts011F_threshold_overCurrentBreaker,
    "TS011F_overVoltageBreaker": tuya_ts011F_threshold_overVoltageBreaker,
    "TS011F_underVoltageBreaker": tuya_ts011F_threshold_underVoltageBreaker
}

def sanity_check_of_param(self, NwkId):

    self.log.logging("Heartbeat", "Log", f"sanity_check_of_param  {NwkId}")
    DEVICE_PARAMETERS.update(SONOFF_DEVICE_PARAMETERS)

    param_data = self.ListOfDevices.get(NwkId, {}).get("Param", {})
    model_name = self.ListOfDevices.get(NwkId, {}).get("Model", "")

    for param, value in param_data.items():
        self.log.logging("Heartbeat", "Log", f"sanity_check_of_param  {param}, {value}")
        
        if ts0601_extract_data_point_infos(self, model_name) and param in TS0601_COMMANDS:
            self.log.logging("Heartbeat", "Log", f"sanity_check_of_param  {param} {value}")
            ts0601_actuator(self, NwkId, param, value)

        elif param in DEVICE_PARAMETERS:
            DEVICE_PARAMETERS[param](self, NwkId, value)
