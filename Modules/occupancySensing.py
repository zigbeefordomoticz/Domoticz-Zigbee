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

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN, is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP

OCCUPANCY_CLUSTER = "0406"
OCCUPANCY_ATTRIBUTE = "0000"

def report_occupancy_sensing_occupied(self, nwk_id, ep):
    self.log.logging("Occupancy", "Log", f"Occupancy report to device {nwk_id} with Occupied", nwkid=nwk_id)
    occupancy_attribute_report(self, nwk_id, ep, 1)

def report_occupancy_sensing_unoccupied(self, nwk_id, ep):
    self.log.logging("Occupancy", "Log", f"Occupancy report to device {nwk_id} with Unoccupied", nwkid=nwk_id)
    occupancy_attribute_report(self, nwk_id, ep, 0)
    

def occupancy_attribute_report(self, nwk_id, ep, occupancy):
    """ Report occupancy to device, to simulate a bind with a Motion """

    fcf = "08"  # Frame Control Field ( Server to Client)
    sqn = sqn = get_and_inc_ZCL_SQN(self, nwk_id)
    data_type = "18"
    occupancy = "01" if occupancy else "00"
    cmd = "0a"

    payload = f"{fcf}{sqn}{cmd}{OCCUPANCY_ATTRIBUTE}{data_type}{occupancy}"
    self.log.logging("Occupancy", "Log", f"Occupancy report to device {nwk_id} with value {occupancy} -> payload: {payload}", nwkid=nwk_id)
    raw_APS_request( self, nwk_id, ep, OCCUPANCY_CLUSTER, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, nwk_id) )
