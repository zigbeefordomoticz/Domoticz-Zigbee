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

from Modules.bindings import callBackForWebBindIfNeeded
from Modules.legrand_netatmo import callbackDeviceAwake_Legrand
from Modules.schneider_wiser import callbackDeviceAwake_Schneider
from Modules.writeAttributes import callBackForWriteAttributeIfNeeded
from Modules.zigateConsts import MAX_LOAD_ZIGATE

CALLBACK_TABLE = {
    # Manuf : ( callbackDeviceAwake_xxxxx function )
    "105e": callbackDeviceAwake_Schneider,
    "1021": callbackDeviceAwake_Legrand,
}


def callbackDeviceAwake(self, Devices, NwkId, endpoint, cluster):

    # This is fonction is call when receiving a message from a Manufacturer battery based device.
    # The function is called after processing the readCluster part
    #
    # and will call the manufacturer specific one if needed and if existing

    self.log.logging( "inRawAPS", "Debug", "callbackDeviceAwake -  NwkId %s Ep %s Cluster %s " % (NwkId, endpoint, cluster), NwkId)

    if NwkId not in self.ListOfDevices:
        return

    # 09/11/2020: Let's check if we are not in pairing mode for this device, or if the Zigate is not overloaded
    if "PairingInProgress" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["PairingInProgress"]:
        return
    if self.busy or self.ControllerLink.loadTransmit() > 8:
        return
    # Let's check if any WebBind have to be established

    # callBackForBindIfNeeded(self, NwkId)
    callBackForWebBindIfNeeded(self, NwkId)

    callBackForWriteAttributeIfNeeded(self, NwkId)

    # Let's checkfor the Manuf Specific callBacks
    if "Manufacturer" not in self.ListOfDevices[NwkId]:
        return

    if self.ListOfDevices[NwkId]["Manufacturer"] in CALLBACK_TABLE:
        manuf = self.ListOfDevices[NwkId]["Manufacturer"]
        func = CALLBACK_TABLE[manuf]
        func(self, Devices, NwkId, endpoint, cluster)
