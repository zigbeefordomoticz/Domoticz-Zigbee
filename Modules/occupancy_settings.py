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

from DevicesModules.custom_sonoff import is_sonoff_device
from DevicesModules.custom_sunricher import is_sunricher_device
from Modules.basicOutputs import write_attribute
from Modules.develco import is_develco_device
from Modules.philips import (is_philips_device,
                             philips_set_pir_occupancySensibility)
from Modules.readAttributes import (ReadAttributeRequest_0406_0010,
                                    ReadAttributeRequest_0406_0012,
                                    ReadAttributeRequest_0406_0020,
                                    ReadAttributeRequest_0406_0022)
from Modules.tools import getListOfEpForCluster
from Modules.zigateConsts import ZIGATE_EP

OCCUPANCY_CLUSTER_ID = "0406"

PIR_CONFIG_SET = {
    "PIROccupiedToUnoccupiedDelay": ( "0010", "21"),
    "PIRUnoccupiedToOccupiedDelay": ( "0011", "21"),
    "PIRUnoccupiedToOccupiedThreshold": ( "0012", "20")
}

ULTRASONIC_CONFIG_SET = {
    "UltrasonicOccupiedToUnoccupiedDelay": ( "0020", "21"),
    "UltrasonicUnoccupiedToOccupiedDelay": ( "0021", "21"),
    "UltrasonicUnoccupiedToOccupiedThreshold": ( "0022", "20")
}

PHYSICAL_CONFIG_SET = {
    
}

# Standard 
def PIR_occupied_to_unoccupied_delay(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"PIR_occupied_to_unoccupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        PIR_CONFIG_SET[ "PIROccupiedToUnoccupiedDelay"][0], 
        PIR_CONFIG_SET[ "PIROccupiedToUnoccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def current_PIR_OccupiedToUnoccupied_Delay(self, nwkid, ep):
    """ look in the plugin database for the the current value of the OccupiedToUnoccupied_Delay """
    
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0010 = ep_data.get("0010", None)

    if attribute_0010 is not None:
        return int(attribute_0010, 16) if isinstance(attribute_0010, str) else attribute_0010
    else:
        return None


def PIR_unoccupied_to_occupied_delay(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"PIR_unoccupied_to_occupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedDelay"][0], 
        PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def PIR_unoccupied_to_occupied_threshold(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"PIR_unoccupied_to_occupied_threshold for {nwkid}/{ep} - thershold: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedThreshold"][0], 
        PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedThreshold"][1], 
        "%02x" %value, 
        ackIsDisabled=False, )


def current_PIR_OccupiedToUnoccupied_Threshold(self, nwkid, ep):
    """ look in the plugin database for the the current value of the OccupiedToUnoccupied_Threshold """
    
    target_attribute = PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedThreshold"][0]
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0012 = ep_data.get(target_attribute, None)

    if attribute_0012 is not None:
        return int(attribute_0012, 16) if isinstance(attribute_0012, str) else attribute_0012

    return None


def Ultrasonic_occupied_to_unoccupied_delay(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"Ultrasonic_occupied_to_unoccupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        ULTRASONIC_CONFIG_SET[ "UltrasonicOccupiedToUnoccupiedDelay"][0], 
        ULTRASONIC_CONFIG_SET[ "UltrasonicOccupiedToUnoccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def current_Ultrasonic_OccupiedToUnoccupied_Delay(self, nwkid, ep):
    """ look in the plugin database for the the current value of the Ultrasonic_OccupiedToUnoccupied_Delay """
    
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0010 = ep_data.get("0010", None)

    if attribute_0010 is not None:
        return int(attribute_0010, 16) if isinstance(attribute_0010, str) else attribute_0010
    else:
        return None


def Ultrasonic_unoccupied_to_occupied_delay(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"Ultrasonic_unoccupied_to_occupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        ULTRASONIC_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedDelay"][0], 
        ULTRASONIC_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"Ultrasonic_unoccupied_to_occupied_threshold for {nwkid}/{ep} - thershold: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        ULTRASONIC_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedThreshold"][0], 
        ULTRASONIC_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedThreshold"][1], 
        "%02x" %value, 
        ackIsDisabled=False, )


def current_Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep):
    """ look in the plugin database for the the current value of the Ultrasonic_unoccupied_to_occupied_threshold """

    target_attribute = ULTRASONIC_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedThreshold"][0]
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0022 = ep_data.get( target_attribute, None)

    if attribute_0022 is not None:
        return int(attribute_0022, 16) if isinstance(attribute_0022, str) else attribute_0022

    return None

# paramDevice helpers

def common_PIROccupiedToUnoccupiedDelay(self, nwkid, delay):
    
    self.log.logging( "occupancySettings", "Debug", f"common_PIROccupiedToUnoccupiedDelay for {nwkid} - delay: {delay}", nwkid )
    
    # Determine EndPoints
    if is_philips_device(self, nwkid):
        # work on ep 0x02
        ListOfEp = ["02",]
    
    elif is_develco_device(self, nwkid):
        ListOfEp = ["22", "28", "29"]
        
    elif is_sunricher_device(self, nwkid):
        ListOfEp = ["01",]

    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)

    self.log.logging( "occupancySettings", "Debug", f"common_PIROccupiedToUnoccupiedDelay for {nwkid} - delay: {delay} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_delay = current_PIR_OccupiedToUnoccupied_Delay(self, nwkid, ep)
        if current_delay != delay:
            PIR_occupied_to_unoccupied_delay(self, nwkid, ep, delay)
    ReadAttributeRequest_0406_0010(self, nwkid)


def common_PIR_occupancySensibility(self, nwkid, sensibility):
    self.log.logging( "occupancySettings", "Debug", f"common_PIR_occupancySensibility for {nwkid} - sensibility: {sensibility}", nwkid )
    
    if is_philips_device(self, nwkid):
        philips_set_pir_occupancySensibility(self, nwkid, sensibility)
        return

    elif is_develco_device(self, nwkid):
        ListOfEp = ["22", "28", "29"]
        
    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)
        
    self.log.logging( "occupancySettings", "Debug", f"common_Ultrasonic_occupancySensibility for {nwkid} - delay: {sensibility} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_sensibility = current_PIR_OccupiedToUnoccupied_Threshold(self, nwkid, ep)
        if current_sensibility != sensibility:
            PIR_unoccupied_to_occupied_threshold(self, nwkid, ep, sensibility)
    ReadAttributeRequest_0406_0012(self, nwkid)


def common_Ultrasnonic_OccupiedToUnoccupiedDelay(self, nwkid, delay):
    self.log.logging( "occupancySettings", "Debug", f"common_Ultrasnonic_OccupiedToUnoccupiedDelay for {nwkid} - delay: {delay}", nwkid )
    
    # Determine EndPoints
    ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)

    self.log.logging( "occupancySettings", "Debug", f"common_Ultrasnonic_OccupiedToUnoccupiedDelay for {nwkid} - delay: {delay} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_delay = current_Ultrasonic_OccupiedToUnoccupied_Delay(self, nwkid, ep)
        if current_delay != delay:
            Ultrasonic_occupied_to_unoccupied_delay(self, nwkid, ep, delay)
    ReadAttributeRequest_0406_0020(self, nwkid)


def common_Ultrasonic_occupancySensibility(self, nwkid, sensibility):
    self.log.logging( "occupancySettings", "Debug", f"common_Ultrasonic_occupancySensibility for {nwkid} - sensibility: {sensibility}", nwkid )
    
    # Determine EndPoints
    if is_sonoff_device(self, nwkid):
        ListOfEp = ["01",]

    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)
        
    self.log.logging( "occupancySettings", "Debug", f"common_Ultrasonic_occupancySensibility for {nwkid} - delay: {sensibility} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_sensibility = current_Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep)
        if current_sensibility != sensibility:
            Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep, sensibility)
    ReadAttributeRequest_0406_0022(self, nwkid)


OCCUPANCY_DEVICE_PARAMETERS = {
    "PIROccupiedToUnoccupiedDelay": { "callable": common_PIROccupiedToUnoccupiedDelay, "description": "The PIROccupiedToUnoccupiedDelay attribute specifies the time delay, in seconds,before the PIR sensor changes to its unoccupied state after the last detection of movement in the sensed area."},
    "PIRoccupancySensibility": { "callable": common_PIR_occupancySensibility, "description": "Sensitivity level of the Sensor 0 default, 1, High, 2 Max"},
    "occupancySensibility": { "callable": common_PIR_occupancySensibility, "description": "Sensitivity level of the Sensor 0 default, 1, High, 2 Max"},
    "UltrasonicOccupiedToUnoccupiedDelay": { "callable": common_Ultrasnonic_OccupiedToUnoccupiedDelay, "description": "specifies the time delay, in seconds,before the sensor changes to its unoccupied state after the last detection of movement in the sensed area."},
    "UltrasonicOccupancySensibility": { "callable": common_Ultrasonic_occupancySensibility, "description": "Sensitivity level of the Sensor 0 default, 1, High, 2 Max"}
}