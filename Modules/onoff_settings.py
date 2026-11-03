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

import math

from Modules.basicOutputs import write_attribute
from Modules.enki import is_enky_device
from Modules.philips import is_philips_device
from Modules.readAttributes import ReadAttributeRequest_0006_400x
from Modules.tools import (get_device_config_param,
                           get_deviceconf_parameter_value,
                           getListOfEpForCluster, is_int)
from Modules.tuya import (get_tuya_attribute, is_tuya_switch_relay,
                          tuya_switch_relay_status)
from Modules.zigateConsts import ZIGATE_EP
from Zigbee.zclCommands import zcl_onoff_on, zcl_onoff_on_with_timed_off

ONOFF_CLUSTER_ID = "0006"

ONOFF_CONFIG_SET = {
    "OnTime": ( "4001", "21"),
    "OffWaitTime": ( "4002", "21"),
    "StartupOnOff": ( "4003", "30")
}

# On With Timed Off (0x42) - see https://github.com/zigbeefordomoticz/wiki/blob/master/en-eng/Technical/OnOff-timed-off.md
# The Params are in seconds; the ZCL fields are in 1/10 s, the Tuya countdown in seconds.
TIMED_OFF_MAX = 0xFFFE        # OnTime / OffWaitTime: uint16 in 1/10 s (6553.4 s), 0xFFFF is reserved
TUYA_COUNTDOWN_MAX = 43200    # Tuya documented countdown maximum, in seconds (12 h)


def _timed_off_param(self, nwkid, ep, param):
    """Value of a timed-off device Param for one endpoint, in seconds. The Param is either one value
    for every endpoint ( 600 ) or a value per endpoint ( {"01": 600, "02": 300} ). 0 when unset."""

    value = get_device_config_param(self, nwkid, param)
    if isinstance(value, dict):
        value = value.get(ep)
    if value in (None, ""):
        return 0
    try:
        value = float(value)
    except (TypeError, ValueError):
        self.log.logging( "onoffSettings", "Error", f"{param} for {nwkid}/{ep} - invalid value: {value}", nwkid )
        return 0
    return max(0, value)


def onoff_timed_off_values(self, nwkid, ep):
    """(OnTime, OffWaitTime) in seconds from the OnOffOnTimeDelay / OnOffOffWaitTime Params,
    or None when OnOffOnTimeDelay is not set for that endpoint."""

    on_time = _timed_off_param(self, nwkid, ep, "OnOffOnTimeDelay")
    if not on_time:
        return None
    return on_time, _timed_off_param(self, nwkid, ep, "OnOffOffWaitTime")


def _tenths(seconds):
    """Seconds to the ZCL OnTime / OffWaitTime unit (1/10 s), capped at 0xFFFE."""
    return min(int(round(seconds * 10)), TIMED_OFF_MAX)


def is_tuya_onoff_countdown(self, nwkid):
    """Device conf flag "TuyaOnOffCountdown": the device implements 0x42 as a Tuya countdown
    (does not switch On, counts in seconds, toggles the relay when it expires)."""

    model = self.ListOfDevices.get(nwkid, {}).get("Model", "")
    return bool(get_deviceconf_parameter_value(self, model, "TuyaOnOffCountdown", return_default=False))


def onoff_on_with_timed_off(self, nwkid, ep):
    """Switch On with a device-side auto-off when OnOffOnTimeDelay is set.
    Returns True when the On was sent, False when the caller must send a plain On."""

    values = onoff_timed_off_values(self, nwkid, ep)
    if values is None:
        return False

    if not self.pluginconf.pluginConf.get("ControllerInRawMode"):
        self.log.logging( "onoffSettings", "Error", f"onoff_on_with_timed_off for {nwkid}/{ep} - On With Timed Off needs a zigpy coordinator, sending a plain On", nwkid )
        return False

    on_seconds, off_wait_seconds = values

    if is_tuya_onoff_countdown(self, nwkid):
        # Tuya: 0x42 only starts a countdown in seconds, and On/Off/Toggle cancel it, so On goes first.
        # OffWaitTime = OnTime as Tuya documents (and zigbee-herdsman-converters sends).
        seconds = min(max(1, math.ceil(on_seconds)), TUYA_COUNTDOWN_MAX)
        self.log.logging( "onoffSettings", "Debug", f"onoff_on_with_timed_off for {nwkid}/{ep} - Tuya countdown {seconds}s", nwkid )
        zcl_onoff_on(self, nwkid, ep)
        zcl_onoff_on_with_timed_off(self, nwkid, ep, seconds, seconds)
        return True

    on_time, off_wait_time = max(1, _tenths(on_seconds)), _tenths(off_wait_seconds)
    self.log.logging( "onoffSettings", "Debug", f"onoff_on_with_timed_off for {nwkid}/{ep} - OnTime {on_time} OffWaitTime {off_wait_time} (1/10 s)", nwkid )
    zcl_onoff_on_with_timed_off(self, nwkid, ep, on_time, off_wait_time)
    return True


def check_onoff_timed_off_param(self, nwkid, value):
    """Device Param callback for OnOffOnTimeDelay / OnOffOffWaitTime. Nothing is written to the device:
    the values are sent with every On (On With Timed Off), because the OnTime attribute is consumed
    by the countdown and reset by Off, so a one-time write would only cover the next On."""

    self.log.logging( "onoffSettings", "Debug", f"check_onoff_timed_off_param for {nwkid} - value: {value}", nwkid )


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

    model = self.ListOfDevices[nwkid].get("Model", "")
    attribute, data_type = ONOFF_CONFIG_SET[ "StartupOnOff"]
    if get_deviceconf_parameter_value(self, model, "PowerOnOffStateAttribute8002", return_default=False):
        # Tuya 0x8002 uses 0x00 Off, 0x01 On, 0x02 Previous (instead of 0xff for 0x4003)
        attribute = "8002"
        if value == 0xFF:
            value = 0x02

    write_attribute(
        self,
        nwkid,
        ZIGATE_EP,
        ep,
        ONOFF_CLUSTER_ID,
        "0000",
        "00",
        attribute,
        data_type,
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
    "PowerOnAfterOffOn": { "callable": common_onoff_startup_onoff_mode, "description": "If managed by the device, the device will go to a desired state after an electric Off/On. 0 stands for stay Off, 1 stands for switch On, 255 stands for previous state" },
    "OnOffOnTimeDelay": { "callable": check_onoff_timed_off_param, "description": "Auto-off handled by the device, in seconds (600 = 10 min), one value or one per endpoint {\"01\": 600}. Sent with every On as On With Timed Off. 0 or unset = plain On. Max 6553 s (12 h on Tuya countdown devices)" },
    "OnOffOffWaitTime": { "callable": check_onoff_timed_off_param, "description": "Used with OnOffOnTimeDelay, in seconds: after an Off command ends the timed On early, the device ignores On With Timed Off (not a plain On) for this time. 0 = no guard. Ignored for Tuya countdown devices" }
}