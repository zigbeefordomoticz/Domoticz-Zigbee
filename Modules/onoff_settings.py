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
from Modules.enki import is_enky_device
from Modules.philips import is_philips_device
from Modules.readAttributes import ReadAttributeRequest_0006_400x
from Modules.tools import (get_deviceconf_parameter_value,
                           getListOfEpForCluster, is_int)
from Modules.tuya import (get_tuya_attribute, is_tuya_switch_relay,
                          tuya_switch_relay_status)
from Modules.zigateConsts import ZIGATE_EP

ONOFF_CLUSTER_ID = "0006"

ONOFF_CONFIG_SET = {
    "OnTime": ( "4001", "21"),
    "OffWaitTime": ( "4002", "21"),
    "StartupOnOff": ( "4003", "30")
}


def onoff_on_time(self, nwkid, ep, value):
    self.log.logging( "onoffSettings", "Debug", f"onoff_on_time for {nwkid}/{ep} - value: {value}", nwkid )
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

    self.log.logging( "onoffSettings", "Debug", f"onoff_off_wait_time for {nwkid}/{ep} - value: {value}", nwkid )

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

    self.log.logging( "onoffSettings", "Debug", f"onoff_startup_onoff_mode for {nwkid}/{ep} - value: {value}", nwkid )

    if isinstance(value, str):
        if is_int(value):
            old_value = value
            value = int(value)
            self.log.logging( "onoffSettings", "Debug", f"onoff_startup_onoff_mode for {nwkid}/{ep} - value: {old_value} converted to {value}", nwkid )
        else:
            self.log.logging( "onoffSettings", "Error", f"onoff_startup_onoff_mode for {nwkid}/{ep} - value error {value}", nwkid )
            return

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
        self.log.logging("onoffSettings", "Debug", "current_onoff_startup_mode - No ep: %s" % ep, nwkid)
        return None
    
    onoff_cluster_data = ep_data.get(ONOFF_CLUSTER_ID, {})
    
    if get_deviceconf_parameter_value(self, model, "PowerOnOffStateAttribute8002", return_default=False):
        attribute_lookup = "8002"
    else:
        attribute_lookup = ONOFF_CONFIG_SET["StartupOnOff"][0]
        
    if attribute_lookup not in onoff_cluster_data:
        self.log.logging("onoffSettings", "Debug", "current_onoff_startup_mode - No Attribute: %s" % attribute_lookup, nwkid)
        return None
    
    return onoff_cluster_data[attribute_lookup]


def common_onoff_on_time(self, nwkid, mode):
    self.log.logging( "onoffSettings", "Debug", f"common_onoff_on_time for {nwkid} - mode: {mode}", nwkid )
    ListOfEp = getListOfEpForCluster(self, nwkid, ONOFF_CLUSTER_ID)
    for ep in ListOfEp:
        onoff_on_time(self, nwkid, ep, mode)

def common_onoff_off_wait_time(self, nwkid, mode):
    self.log.logging( "onoffSettings", "Debug", f"common_onoff_off_wait_time for {nwkid} - mode: {mode}", nwkid )
    ListOfEp = getListOfEpForCluster(self, nwkid, ONOFF_CLUSTER_ID)
    for ep in ListOfEp:
        onoff_off_wait_time(self, nwkid, ep, mode)
 

def common_onoff_startup_onoff_mode(self, nwkid, mode):
    
    self.log.logging( "onoffSettings", "Debug", f"common_onoff_startup_onoff_mode for {nwkid} - mode: {mode}", nwkid )

    if int(mode) not in (0, 1, 2, 255):
        self.log.logging( "onoffSettings", "Error", f"common_onoff_startup_onoff_mode for {nwkid} - uncorrect mode: {mode}", nwkid )
        return

    # Determine EndPoints
    if is_philips_device(self, nwkid):
        ListOfEp = ["0b",]

    elif is_enky_device(self, nwkid):   # Enki Leroy Merlin
        ListOfEp = ["01",]
    
    elif is_tuya_switch_relay(self, nwkid):
        if get_tuya_attribute(self, nwkid, "RelayStatus") != mode:
            tuya_switch_relay_status(self, nwkid, status=mode)
        return        
        
    else:
        ListOfEp = getListOfEpForCluster(self, nwkid, ONOFF_CLUSTER_ID)

    for ep in ListOfEp:
        current_mode = current_onoff_startup_mode(self, nwkid, ep)
        if current_mode != mode:
            onoff_startup_onoff_mode(self, nwkid, ep, mode)
    ReadAttributeRequest_0006_400x(self, nwkid)


ONOFF_DEVICE_PARAMETERS = {
    "PowerOnAfterOffOn": common_onoff_startup_onoff_mode,
    "OnOffOnTimeDelay": common_onoff_off_wait_time,
    "OnOffOffWaitTime": common_onoff_off_wait_time
}