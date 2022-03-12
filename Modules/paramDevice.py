#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: paramDevice.py

    Description: implement the parameter device specific

"""

import Domoticz

from Modules.basicOutputs import (ballast_Configuration_max_level,
                                  ballast_Configuration_min_level,
                                  set_PIROccupiedToUnoccupiedDelay,
                                  set_poweron_afteroffon)
from Modules.danfoss import (danfoss_exercise_day_of_week,
                             danfoss_exercise_trigger_time,
                             danfoss_orientation, danfoss_viewdirection)
from Modules.enki import enki_set_poweron_after_offon_device
from Modules.legrand_netatmo import (legrand_Dimmer_by_nwkid,
                                     legrand_enable_Led_IfOn_by_nwkid,
                                     legrand_enable_Led_InDark_by_nwkid,
                                     legrand_enable_Led_Shutter_by_nwkid)
from Modules.lumi import setXiaomiVibrationSensitivity
from Modules.philips import (philips_set_pir_occupancySensibility,
                             philips_set_poweron_after_offon_device)
from Modules.readAttributes import (ReadAttributeRequest_0006_400x,
                                    ReadAttributeRequest_0406_0010)
from Modules.schneider_wiser import (iTRV_open_window_detection,
                                     wiser_home_lockout_thermostat)
from Modules.tuya import (get_tuya_attribute, tuya_backlight_command,
                          tuya_cmd_ts004F, tuya_energy_childLock,
                          tuya_switch_indicate_light, tuya_switch_relay_status,
                          tuya_window_cover_motor_reversal, tuya_window_cover_calibration)
from Modules.tuyaTRV import (tuya_trv_boost_time, tuya_trv_calibration,
                             tuya_trv_child_lock, tuya_trv_eco_temp,
                             tuya_trv_set_max_setpoint,
                             tuya_trv_set_min_setpoint,
                             tuya_trv_thermostat_sensor_mode,
                             tuya_trv_window_detection)


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

    # Domoticz.Log("param_Occupancy_settings_PIROccupiedToUnoccupiedDelay %s -> delay: %s" %(nwkid, delay))

    if self.ListOfDevices[nwkid]["Manufacturer"] == "100b" or self.ListOfDevices[nwkid]["Manufacturer Name"] == "Philips":  # Philips
        if "02" not in self.ListOfDevices[nwkid]["Ep"]:
            return
        if "0406" not in self.ListOfDevices[nwkid]["Ep"]["02"]:
            return
        if "0010" not in self.ListOfDevices[nwkid]["Ep"]["02"]["0406"]:
            set_PIROccupiedToUnoccupiedDelay(self, nwkid, delay)
            ReadAttributeRequest_0406_0010(self, nwkid)
        elif int(self.ListOfDevices[nwkid]["Ep"]["02"]["0406"]["0010"], 16) != delay:
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
            elif int(self.ListOfDevices[nwkid]["Ep"][ep]["0406"]["0010"], 16) != delay:
                set_PIROccupiedToUnoccupiedDelay(self, nwkid, delay, ListOfEp=[ep])
        ReadAttributeRequest_0406_0010(self, nwkid)
    else:
        Domoticz.Log("=====> Unknown Manufacturer/Name")


def param_PowerOnAfterOffOn(self, nwkid, mode):
    # 0 - stay Off after a Off/On
    # 1 - stay On after a Off/On
    # 255 - stay to previous state after a Off/On ( or 2 for BlitzWolf)

    self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for %s mode: %s" % (nwkid, mode), nwkid)
    if mode not in (0, 1, 2, 255):
        return

    if "Manufacturer" not in self.ListOfDevices[nwkid]:
        return

    if self.ListOfDevices[nwkid]["Manufacturer"] == "100b":  # Philips
        if "0b" not in self.ListOfDevices[nwkid]["Ep"]:
            return
        if "0006" not in self.ListOfDevices[nwkid]["Ep"]["0b"]:
            return
        if "4003" not in self.ListOfDevices[nwkid]["Ep"]["0b"]["0006"]:
            return
        if self.ListOfDevices[nwkid]["Ep"]["0b"]["0006"]["4003"] != str(mode):
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for Philips for %s mode: %s" % (nwkid, mode), nwkid)
            philips_set_poweron_after_offon_device(self, mode, nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)

    elif "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in (
        "TS0121",
        "TS0115",
        "TS011F-multiprise",
        "TS011F-2Gang-switches",
        "TS011F-plug"
    ):
        self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for %s mode: %s TUYA Manufacturer" % (nwkid, mode), nwkid)
        # Tuya ( 'TS0121' BlitzWolf )
        if "01" not in self.ListOfDevices[nwkid]["Ep"]:
            return
        if "0006" not in self.ListOfDevices[nwkid]["Ep"]["01"]:
            return
        if "8002" not in self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]:
            return

        if self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]["8002"] == "2" and str(mode) == "255":
            return
        if self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]["8002"] != str(mode):
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for Tuya for %s mode: %s" % (nwkid, mode), nwkid)
            set_poweron_afteroffon(self, nwkid, mode)
            ReadAttributeRequest_0006_400x(self, nwkid)

    elif self.ListOfDevices[nwkid]["Manufacturer"] == "1277":  # Enki Leroy Merlin
        if "01" not in self.ListOfDevices[nwkid]["Ep"]:
            return
        if "0006" not in self.ListOfDevices[nwkid]["Ep"]["01"]:
            return
        if "4003" not in self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]:
            return
        if self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]["4003"] != str(mode):
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for Enki for %s mode: %s" % (nwkid, mode), nwkid)
            enki_set_poweron_after_offon_device(self, mode, nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)

    elif "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in (
        "TS0601-switch",
        "TS0601-2Gangs-switch",
        "TS0601-Energy",
    ):
        if get_tuya_attribute(self, nwkid, "RelayStatus") != mode:
            tuya_switch_relay_status(self, nwkid, mode)

    else:
        # Ikea, Legrand,
        for ep in self.ListOfDevices[nwkid]["Ep"]:
            if "0006" not in self.ListOfDevices[nwkid]["Ep"][ep]:
                continue
            if "4003" in self.ListOfDevices[nwkid]["Ep"][ep]["0006"] and self.ListOfDevices[nwkid]["Ep"][ep]["0006"]["4003"] == str(mode):
                continue
            elif "8002" in self.ListOfDevices[nwkid]["Ep"][ep]["0006"] and self.ListOfDevices[nwkid]["Ep"][ep]["0006"]["8002"] == str(mode):
                continue
            self.log.logging("Heartbeat", "Debug", "param_PowerOnAfterOffOn for %s mode: %s" % (nwkid, mode), nwkid)
            set_poweron_afteroffon(self, nwkid, mode)
            ReadAttributeRequest_0006_400x(self, nwkid)


DEVICE_PARAMETERS = {
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
    "eTRVExerciseDay": danfoss_exercise_day_of_week,
    "eTRVExerciseTime": danfoss_exercise_trigger_time,
    "DanfossTRVOrientation": danfoss_orientation,
    "DanfossViewDirection": danfoss_viewdirection,
    "TS004FMode": tuya_cmd_ts004F,
    "vibrationAqarasensitivity": setXiaomiVibrationSensitivity,
    "BRT100WindowsDetection": tuya_trv_window_detection,
    "BRT100ChildLock": tuya_trv_child_lock,
    "BRT100BoostDuration": tuya_trv_boost_time,
    "BRT100Calibration": tuya_trv_calibration,
    "BRT100SetpointEco": tuya_trv_eco_temp,
    "BRT100MaxSetpoint": tuya_trv_set_max_setpoint,
    "BRT100MinSetpoint": tuya_trv_set_min_setpoint,
    "moesCalibrationTime": tuya_window_cover_calibration,
}



def sanity_check_of_param(self, NwkId):
    # Domoticz.Log("sanity_check_of_param for %s" %NwkId)

    if "Param" not in self.ListOfDevices[NwkId]:
        return

    for param in self.ListOfDevices[NwkId]["Param"]:
        value = self.ListOfDevices[NwkId]["Param"][param]
        if param in DEVICE_PARAMETERS:
            # Domoticz.Log("sanity_check_of_param - calling %s" %param)
            func = DEVICE_PARAMETERS[param]
            func(self, NwkId, value)
