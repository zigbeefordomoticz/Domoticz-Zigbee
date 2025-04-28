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

from Modules.zigateConsts import ZIGATE_EP

NAMRON_MANUFACTURER_ID = "1224"
NAROM_AWAYMODE_ATTRIBUTE = "2002"

def namrom_set_away_mode(self, nwk_id, ep, mode):
    """ Set the Namron Manuifacturer specific attribute. """

    self.log.logging("Namron", "Debug", "namrom_set_away_mode - Nwkid: %s value: %s" % (nwk_id, mode))
    write_attribute(self, nwk_id, ZIGATE_EP, ep, "0201", NAMRON_MANUFACTURER_ID, "01", NAROM_AWAYMODE_ATTRIBUTE, "10", "%02x" %mode, ackIsDisabled=False)
    
    
    
NAMRON_DEVICE_PARAMETERS = {
}