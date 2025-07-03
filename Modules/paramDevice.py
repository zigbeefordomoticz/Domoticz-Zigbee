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


from DevicesModules.custom_sonoff import SONOFF_DEVICE_PARAMETERS
from DevicesModules.custom_sunricher import SUNRICHER_DEVICE_PARAMETERS
from DevicesModules.custom_GammaTroniques import GMMS_TIC_METER_DEVICE_PARAMETERS
from Modules.ballast_settings import BALLAST_DEVICE_PARAMETERS
from Modules.danfoss import DANFOSS_DEVICE_PARAMETERS
from Modules.ias_settings import IAS_DEVICE_PARAMETERS
from Modules.legrand_netatmo import LEGRAND_DEVICE_PARAMETERS
from Modules.lumi import LUMI_DEVICE_PARAMETERS
from Modules.occupancy_settings import OCCUPANCY_DEVICE_PARAMETERS
from Modules.onoff_settings import ONOFF_DEVICE_PARAMETERS
from Modules.philips import PHILIPS_DEVICE_PARAMETERS
from Modules.schneider_wiser import SCHNEIDER_DEVICE_PARAMETERS
from Modules.thermo_settings import THERMOSTAT_DEVICE_PARAMETERS
from Modules.thermo_ui_setting import THERMOSTAT_UI_DEVICE_PARAMETERS
from Modules.tuya import TUYA_DEVICE_PARAMETERS
from Modules.tuyaSiren import TUYA_SIREN_DEVICE_PARAMETERS
from Modules.tuyaTRV import TUYA_TRV_DEVICE_PARAMETERS
from Modules.tuyaTS011F import TUYA_TS011F_DEVICE_PARAMETERS
from Modules.tuyaTS0601 import ts0601_extract_data_point_infos, ts0601_settings
from DevicesModules.custom_namron import NAMRON_DEVICE_PARAMETERS

def initialize_device_settings(self):
    """Initializes device settings by loading general and manufacturer-specific parameters."""
    self.device_settings = {}

    # General device parameters
    general_parameters = [
        ONOFF_DEVICE_PARAMETERS,
        OCCUPANCY_DEVICE_PARAMETERS,
        IAS_DEVICE_PARAMETERS,
        BALLAST_DEVICE_PARAMETERS,
        THERMOSTAT_DEVICE_PARAMETERS,
    ]

    # Manufacturer-specific device parameters
    manufacturer_parameters = [
        DANFOSS_DEVICE_PARAMETERS,
        LEGRAND_DEVICE_PARAMETERS,
        LUMI_DEVICE_PARAMETERS,
        PHILIPS_DEVICE_PARAMETERS,
        SONOFF_DEVICE_PARAMETERS,
        SUNRICHER_DEVICE_PARAMETERS,
        TUYA_DEVICE_PARAMETERS,
        TUYA_TS011F_DEVICE_PARAMETERS,
        TUYA_TRV_DEVICE_PARAMETERS,
        TUYA_SIREN_DEVICE_PARAMETERS,
        SCHNEIDER_DEVICE_PARAMETERS,
        GMMS_TIC_METER_DEVICE_PARAMETERS,
    ]

    # Update device settings in a single loop
    for param_group in general_parameters + manufacturer_parameters:
        self.device_settings.update(param_group)


def sanity_check_of_param(self, NwkId):
    """Performs a sanity check on device parameters and applies relevant settings."""

    self.log.logging("DeviceParameter", "Debug", f"sanity_check_of_param {NwkId}", NwkId)

    device_data = self.ListOfDevices.get(NwkId, {})
    param_data = device_data.get("Param", {})
    model_name = device_data.get("Model", "")
    dps_mapping = ts0601_extract_data_point_infos(self, model_name)

    self.log.logging("DeviceParameter", "Debug", f"sanity_check_of_param {NwkId} model_name: {model_name}, param_data: {param_data}, Tuya dps_mapping: {dps_mapping}", NwkId)

    for param, value in param_data.items():
        self.log.logging("DeviceParameter", "Debug", f"Checking param: {param}, Value: {value}", NwkId)

        if dps_mapping:
            ts0601_settings(self, NwkId, dps_mapping, param, value)
            continue

        param_setting = self.device_settings.get(param)
        if callable(param_setting):
            param_setting(self, NwkId, value)

        elif isinstance(param_setting, dict) and "callable" in param_setting and callable(param_setting["callable"]):
            param_setting["callable"](self, NwkId, value)
