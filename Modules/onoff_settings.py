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
from Modules.basicOutputs import write_attribute
from Modules.enki import enki_set_poweron_after_offon_device
from Modules.philips import is_philips_device
from Modules.readAttributes import ReadAttributeRequest_0006_400x
from Modules.tools import getListOfEpForCluster, get_deviceconf_parameter_value
from Modules.tuya import get_tuya_attribute, tuya_switch_relay_status
from Modules.zigateConsts import ZIGATE_EP

ONOFF_CLUSTER_ID = "0006"

ONOFF_CONFIG_SET = {
    "OnTime": ( "4001", "21"),
    "OffWaitTime": ( "4002", "21"),
    "StartupOnOff": ( "4003", "30")
}


def onoff_on_time(self, nwkid, ep, value):
    self.log.logging( "occupancySettings", "Debug", f"onoff_on_time for {nwkid}/{ep} - value: {value}", nwkid )
    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        ONOFF_CLUSTER_ID, 
        "0000", 
        "00", 
        ONOFF_CONFIG_SET[ "OnTime"][0], 
        ONOFF_CONFIG_SET[ "OnTime"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )


def onoff_off_wait_time(self, nwkid, ep, value):

    self.log.logging( "occupancySettings", "Debug", f"onoff_off_wait_time for {nwkid}/{ep} - value: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        ONOFF_CLUSTER_ID, 
        "0000", 
        "00", 
        ONOFF_CONFIG_SET[ "OffWaitTime"][0], 
        ONOFF_CONFIG_SET[ "OffWaitTime"][1], 
        "%04x" %value, 
        ackIsDisabled=False, )

 
def onoff_startup_onoff_mode(self, nwkid, ep, value):

    self.log.logging( "occupancySettings", "Debug", f"onoff_startup_onoff_mode for {nwkid}/{ep} - value: {value}", nwkid )

    write_attribute( 
        self, 
        nwkid,
        ZIGATE_EP, 
        ep, 
        ONOFF_CLUSTER_ID, 
        "0000", 
        "00", 
        ONOFF_CONFIG_SET[ "StartupOnOff"][0], 
        ONOFF_CONFIG_SET[ "StartupOnOff"][1], 
        "%02x" %value, 
        ackIsDisabled=False, )


def current_onoff_startup_mode(self, nwkid, ep):

    model = self.ListOfDevices[nwkid].get("Model", "")
    device = self.ListOfDevices.get(nwkid, {})
    ep_data = device.get("Ep", {}).get(ep, {})
    
    if ep not in ep_data:
        self.log.logging("Heartbeat", "Debug", "current_onoff_startup_mode - No ep: %s" % ep, nwkid)
        return None
    
    onoff_cluster_data = ep_data.get(ONOFF_CLUSTER_ID, {})
    
    if get_deviceconf_parameter_value(self, model, "PowerOnOffStateAttribute8002", return_default=False):
        attribute_lookup = "8002"
    else:
        attribute_lookup = ONOFF_CONFIG_SET["StartupOnOff"][0]
        
    if attribute_lookup not in onoff_cluster_data:
        self.log.logging("Heartbeat", "Debug", "current_onoff_startup_mode - No Attribute: %s" % attribute_lookup, nwkid)
        return None
    
    return onoff_cluster_data[attribute_lookup]


def common_onoff_startup_onoff_mode(self, nwkid, ep, mode):
    
    self.log.logging( "occupancySettings", "Debug", f"common_onoff_startup_onoff_mode for {nwkid} - mode: {mode}", nwkid )

    if int(mode) not in (0, 1, 2, 255):
        self.log.logging( "occupancySettings", "Error", f"common_onoff_startup_onoff_mode for {nwkid} - uncorrect mode: {mode}", nwkid )
        return

    # Determine EndPoints
    if is_philips_device(self, nwkid):
        ListOfEp = ["0b",]

    elif is_enky_device(self, nwkid):   # Enki Leroy Merlin
        enki_set_poweron_after_offon_device(self, mode, nwkid)
        return
    
    elif is_tuya_switch_relay(self, nwkid):
        if get_tuya_attribute(self, nwkid, "RelayStatus") != mode:
            tuya_switch_relay_status(self, nwkid, mode)
        return        
        
    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, ONOFF_CLUSTER_ID)

    for ep in ListOfEp:
        current_mode = current_onoff_startup_mode(self, nwkid, ep)
        if current_mode != mode:
            onoff_startup_onoff_mode(self, nwkid, ep, mode)
    ReadAttributeRequest_0006_400x(self, nwkid)


ONOFF_DEVICE_PARAMETERS = {
    "PowerOnAfterOffOn": common_onoff_startup_onoff_mode
}



def is_enky_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == "1277"


def is_tuya_switch_relay(self, nwkid):
    model = self.ListOfDevices[nwkid].get("Model", "")
    return model in ( "TS0601-switch", "TS0601-2Gangs-switch", "TS0601-Energy", )

