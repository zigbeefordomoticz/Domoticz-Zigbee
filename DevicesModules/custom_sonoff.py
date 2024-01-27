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

from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import write_attribute
SONOFF_CLUSTER_ID = "fc11"
SONOFF_MANUF_ID = "1286"

def sonoff_child_lock(self, nwkid, lock_mode):
    self.log.logging("Sonoff", "Debug", "sonoff_child_lock - Nwkid: %s Mode: %s" % (nwkid, lock_mode))
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUF_ID, "01", "0000", "10", "%02x" %lock_mode, ackIsDisabled=False)

  
def sonoff_open_window_detection(self, nwkid, detection):
    self.log.logging("Sonoff", "Debug", "sonoff_child_lock - Nwkid: %s Mode: %s" %(nwkid, detection))
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUF_ID, "01", "6000", "10", "%02x" %detection, ackIsDisabled=False)


SONOFF_DEVICE_PARAMETERS = {
    "SonOffTRVChildLock": sonoff_child_lock,
    "SonOffTRVWindowDectection": sonoff_open_window_detection

}
