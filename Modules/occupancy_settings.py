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
from Modules.develco import is_develco_device
from Modules.sonoff import is_sonoff_device, sonoff_set_ultrasonic_occupancySensibility
from Modules.philips import is_philips_device, philips_set_pir_occupancySensibility
from Modules.readAttributes import ReadAttributeRequest_0406_0010, ReadAttributeRequest_0406_0012, ReadAttributeRequest_0406_0020, ReadAttributeRequest_0406_0022
from Modules.tools import getListOfEpForCluster
from Modules.zigateConsts import ZIGATE_EP

OCCUPANCY_CLUSTER_ID = "0406"

PIR_CONFIG_SET = {
    "PIROccupiedToUnoccupiedDelay": ( 0x0010, 0x21),
    "PIRUnoccupiedToOccupiedDelay": ( 0x0011, 0x21),
    "PIRUnoccupiedToOccupiedThreshold": ( 0x0012, 0x20)
}

ULTRASONIC_CONFIG_SET = {
    "UltrasonicOccupiedToUnoccupiedDelay": ( 0x0020, 0x21),
    "UltrasonicUnoccupiedToOccupiedDelay": ( 0x0021, 0x21),
    "UltrasonicUnoccupiedToOccupiedThreshold": ( 0x0022, 0x20)
}

PHYSICAL_CONFIG_SET = {
    
}

# Standard 
def PIR_occupied_to_unoccupied_delay(self, nwkid, ep, value):
    self.log.logging( "BasicOutput", "Log", f"PIR_occupied_to_unoccupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        "%04x" %PIR_CONFIG_SET[ "PIROccupiedToUnoccupiedDelay"][0], 
        "%02x" %PIR_CONFIG_SET[ "PIROccupiedToUnoccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def current_PIR_OccupiedToUnoccupied_Delay(self, nwkid, ep):
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0010 = ep_data.get("0010", None)

    if attribute_0010 is not None:
        return int(attribute_0010, 16) if isinstance(attribute_0010, str) else attribute_0010
    else:
        return None


def PIR_unoccupied_to_occupied_delay(self, nwkid, ep, value):
    self.log.logging( "BasicOutput", "Log", f"PIR_unoccupied_to_occupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        "%04x" %PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedDelay"][0], 
        "%02x" %PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def PIR_unoccupied_to_occupied_threshold(self, nwkid, ep, value):
    self.log.logging( "BasicOutput", "Log", f"PIR_unoccupied_to_occupied_threshold for {nwkid}/{ep} - thershold: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        "%04x" %PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedThreshold"][0], 
        "%02x" %PIR_CONFIG_SET[ "PIRUnoccupiedToOccupiedThreshold"][1], 
        "%02x" %value, 
        ackIsDisabled=False, )


def current_PIR_OccupiedToUnoccupied_Threshold(self, nwkid, ep):
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0012 = ep_data.get("0012", None)

    if attribute_0012 is not None:
        return int(attribute_0012, 16) if isinstance(attribute_0012, str) else attribute_0012

    return None


def Ultrasonic_occupied_to_unoccupied_delay(self, nwkid, ep, value):
    self.log.logging( "BasicOutput", "Log", f"Ultrasonic_occupied_to_unoccupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        "%04x" %PIR_CONFIG_SET[ "UltrasonicOccupiedToUnoccupiedDelay"][0], 
        "%02x" %PIR_CONFIG_SET[ "UltrasonicOccupiedToUnoccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def Ultrasonic_unoccupied_to_occupied_delay(self, nwkid, ep, value):
    self.log.logging( "BasicOutput", "Log", f"Ultrasonic_unoccupied_to_occupied_delay for {nwkid}/{ep} - delay: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        "%04x" %PIR_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedDelay"][0], 
        "%02x" %PIR_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedDelay"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep, value):
    self.log.logging( "BasicOutput", "Log", f"Ultrasonic_unoccupied_to_occupied_threshold for {nwkid}/{ep} - thershold: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        OCCUPANCY_CLUSTER_ID, 
        "0000", 
        "00", 
        "%04x" %PIR_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedThreshold"][0], 
        "%02x" %PIR_CONFIG_SET[ "UltrasonicUnoccupiedToOccupiedThreshold"][1], 
        "%02x" %value, 
        ackIsDisabled=False, )


def current_Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep):
    ep_data = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {}).get(OCCUPANCY_CLUSTER_ID, {})
    attribute_0022 = ep_data.get("0022", None)

    if attribute_0022 is not None:
        return int(attribute_0022, 16) if isinstance(attribute_0022, str) else attribute_0022

    return None

# paramDevice helpers

def common_PIROccupiedToUnoccupiedDelay(self, nwkid, delay):
    self.log.logging( "BasicOutput", "Log", f"common_PIROccupiedToUnoccupiedDelay for {nwkid} - delay: {delay}", nwkid )
    
    # Determine EndPoints
    if is_philips_device(self, nwkid):
        # work on ep 0x02
        ListOfEp = ["02",]
    
    elif is_develco_device(self, nwkid):
        ListOfEp = ["22", "28", "29"]
        
    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)

    self.log.logging( "BasicOutput", "Log", f"common_PIROccupiedToUnoccupiedDelay for {nwkid} - delay: {delay} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_delay = current_PIR_OccupiedToUnoccupied_Delay(self, nwkid, ep)
        if current_delay != delay:
            PIR_occupied_to_unoccupied_delay(self, nwkid, ep, delay)
    ReadAttributeRequest_0406_0010(self, nwkid)


def common_PIR_occupancySensibility(self, nwkid, sensibility):
    self.log.logging( "BasicOutput", "Log", f"common_PIR_occupancySensibility for {nwkid} - sensibility: {sensibility}", nwkid )
    
    if is_philips_device(self, nwkid):
        philips_set_pir_occupancySensibility(self, nwkid, sensibility)
        return

    elif is_develco_device(self, nwkid):
        ListOfEp = ["22", "28", "29"]
        
    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)
        
    self.log.logging( "BasicOutput", "Log", f"common_Ultrasonic_occupancySensibility for {nwkid} - delay: {sensibility} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_sensibility = current_PIR_OccupiedToUnoccupied_Threshold(self, nwkid, ep)
        if current_sensibility != sensibility:
            PIR_unoccupied_to_occupied_threshold(self, nwkid, ep, sensibility)
    ReadAttributeRequest_0406_0012(self, nwkid)


def common_Ultrasnonic_OccupiedToUnoccupiedDelay(self, nwkid, delay):
    self.log.logging( "BasicOutput", "Log", f"common_Ultrasnonic_OccupiedToUnoccupiedDelay for {nwkid} - delay: {delay}", nwkid )
    
    # Determine EndPoints
    ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)

    self.log.logging( "BasicOutput", "Log", f"common_Ultrasnonic_OccupiedToUnoccupiedDelay for {nwkid} - delay: {delay} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_delay = current_PIR_OccupiedToUnoccupied_Delay(self, nwkid, ep)
        if current_delay != delay:
            Ultrasonic_occupied_to_unoccupied_delay(self, nwkid, ep, delay)
    ReadAttributeRequest_0406_0020(self, nwkid)


def common_Ultrasonic_occupancySensibility(self, nwkid, sensibility):
    self.log.logging( "BasicOutput", "Log", f"common_Ultrasonic_occupancySensibility for {nwkid} - sensibility: {sensibility}", nwkid )
    
    # Determine EndPoints
    if is_sonoff_device(self, nwkid):
        ListOfEp = ["01",]

    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, OCCUPANCY_CLUSTER_ID)
        
    self.log.logging( "BasicOutput", "Log", f"common_Ultrasonic_occupancySensibility for {nwkid} - delay: {sensibility} found Endpoint {ListOfEp}", nwkid )
    for ep in ListOfEp:
        current_sensibility = current_Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep)
        if current_sensibility != sensibility:
            Ultrasonic_unoccupied_to_occupied_threshold(self, nwkid, ep, sensibility)
    ReadAttributeRequest_0406_0022(self, nwkid)

    