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

from DevicesModules.custom_Chameleon import chameleon_stge
from DevicesModules.custom_konke import konke_onoff
from DevicesModules.custom_legrand import legrand_operating_time
from DevicesModules.custom_schneider import schneider_touch_screen_cluster
from DevicesModules.custom_zlinky import zlinky_clusters
from Modules.lumi import Lumi_lumi_motion_ac02, lumi_lock, lumi_private_cluster
from Modules.zclClusterHelpers import (CurrentPositionLiftPercentage,
                                       compute_electrical_measurement_conso,
                                       compute_metering_conso)

FUNCTION_WITH_ACTIONS_MODULE = {
    # Lumi 0xfcc
    "Lumi_fcc0": lumi_private_cluster,
    "Lumi_lumi_motion_ac02": Lumi_lumi_motion_ac02,
    
    # Lumi Lock Attribute
    "Lumi_Lock": lumi_lock,
    
    # Schneider
    "schneider_touch_screen_cluster": schneider_touch_screen_cluster,

    # ZLinky
    "zlinky_clusters": zlinky_clusters

}

FUNCTION_MODULE = {
    # 0702 helper
    "compute_metering_conso": compute_metering_conso,

    # 0b04 helper
    "compute_electrical_measurement_conso": compute_electrical_measurement_conso,
    
    # 0102 helper
    "current_position_lift_percent": CurrentPositionLiftPercentage,

    # Legrand Operating Time
    "legrand_operating_time": legrand_operating_time,
    
    # Konke Switch
    "konke_onoff": konke_onoff,
    
    # Chameleon
    # Decode STGE status
    "chameleon_stge": chameleon_stge,
}
