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
from Modules.ballast_settings import BALLAST_DEVICE_PARAMETERS
from Modules.danfoss import DANFOSS_DEVICE_PARAMETERS
from Modules.ias_settings import IAS_DEVICE_PARAMETERS
from Modules.legrand_netatmo import LEGRAND_DEVICE_PARAMETERS
from Modules.lumi import LUMI_DEVICE_PARAMETERS
from Modules.occupancy_settings import OCCUPANCY_DEVICE_PARAMETERS
from Modules.onoff_settings import ONOFF_DEVICE_PARAMETERS
from Modules.philips import PHILIPS_DEVICE_PARAMETERS
from Modules.schneider_wiser import SCHNEIDER_DEVICE_PARAMETERS
from Modules.tuya import TUYA_DEVICE_PARAMETERS
from Modules.tuyaSiren import TUYA_SIREN_DEVICE_PARAMETERS
from Modules.tuyaTRV import TUYA_TRV_DEVICE_PARAMETERS
from Modules.tuyaTS011F import TUYA_TS011F_DEVICE_PARAMETERS
from Modules.tuyaTS0601 import ts0601_extract_data_point_infos, ts0601_settings

DEVICE_PARAMETERS = {
}


def sanity_check_of_param(self, NwkId):

    self.log.logging("Heartbeat", "Debug", f"sanity_check_of_param  {NwkId}")
    
    # Load specific settings
    DEVICE_PARAMETERS.update(ONOFF_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(OCCUPANCY_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(IAS_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(BALLAST_DEVICE_PARAMETERS)

    # Load Manufacturer specific settings
    DEVICE_PARAMETERS.update(DANFOSS_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(LEGRAND_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(LUMI_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(PHILIPS_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(SONOFF_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(TUYA_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(TUYA_TS011F_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(TUYA_TRV_DEVICE_PARAMETERS)
    DEVICE_PARAMETERS.update(TUYA_SIREN_DEVICE_PARAMETERS)

    DEVICE_PARAMETERS.update(SCHNEIDER_DEVICE_PARAMETERS)

    param_data = self.ListOfDevices.get(NwkId, {}).get("Param", {})
    model_name = self.ListOfDevices.get(NwkId, {}).get("Model", "")

    for param, value in param_data.items():
        self.log.logging("Heartbeat", "Debug", f"sanity_check_of_param  {param}, {value}")
        
        dps_mapping = ts0601_extract_data_point_infos( self, model_name) 
        if dps_mapping:
            ts0601_settings( self, NwkId, dps_mapping, param, value)

        elif param in DEVICE_PARAMETERS:
            if callable( DEVICE_PARAMETERS[param] ):
                DEVICE_PARAMETERS[param](self, NwkId, value)

            elif "callable" in DEVICE_PARAMETERS[param]:
                DEVICE_PARAMETERS[param]["callable"](self, NwkId, value)