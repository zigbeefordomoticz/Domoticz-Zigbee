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

from Modules.basicOutputs import handle_unknow_device
from Modules.errorCodes import DisplayStatusCode
from Modules.tools import (DeviceExist, loggingMessages,
                           zigpy_plugin_sanity_check)


def Decode8041(self, Devices, MsgData, MsgLQI):
    """
    Decode an 8041 IEEE Address response and process the received information.

    Args:
        Devices (dict): Dictionary of devices managed by the system.
        MsgData (str): The raw message data received from the network.
        MsgLQI (str): Link Quality Indicator (LQI) of the received message.

    This method:
    - Extracts and parses the IEEE address response.
    - Logs the details of the response.
    - Validates the response data against known devices.
    - Updates timestamps and device records or handles unknown devices.
    """
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgIEEE = MsgData[4:20]

    # Log and exit on invalid status
    if MsgDataStatus != '00':
        self.log.logging( 'Input', 'Debug', f"Decode8041 - Reception of IEEE Address response for {MsgIEEE} with status {MsgDataStatus}" )
        return

    MsgShortAddress = MsgData[20:24]
    extendedResponse = len(MsgData) > 24

    if extendedResponse:
        MsgNumAssocDevices = MsgData[24:26]
        MsgStartIndex = MsgData[26:28]
        MsgDeviceList = MsgData[28:]
        self.log.logging(
            'Input', 'Debug',
            f"Decode8041 - IEEE Address response, Sequence number: {MsgSequenceNumber}, "
            f"Status: {DisplayStatusCode(MsgDataStatus)}, IEEE: {MsgIEEE}, NwkId: {MsgShortAddress}, "
            f"nbAssociated Devices: {MsgNumAssocDevices}, StartIdx: {MsgStartIndex}, DeviceList: {MsgDeviceList}"
        )

    # Validate addresses and log inconsistencies
    if MsgShortAddress == '0000' and self.ControllerIEEE and MsgIEEE != self.ControllerIEEE:
        self.log.logging(
            'Input', 'Error',
            f"Decode8041 - Received an IEEE: {MsgIEEE} with NwkId: {MsgShortAddress} - something is wrong!"
        )
        return
    elif self.ControllerIEEE and MsgIEEE == self.ControllerIEEE and MsgShortAddress != '0000':
        self.log.logging(
            'Input', 'Log',
            f"Decode8041 - Received an IEEE: {MsgIEEE} with NwkId: {MsgShortAddress} - something is wrong!"
        )
        return

    # Handle known devices
    if (MsgShortAddress in self.ListOfDevices 
        and 'IEEE' in self.ListOfDevices[MsgShortAddress] 
        and self.ListOfDevices[MsgShortAddress]['IEEE'] == MsgIEEE
        ):
        self.log.logging(
            'Input', 'Debug',
            f"Decode8041 - Received an IEEE: {MsgIEEE} with NwkId: {MsgShortAddress}"
        )
        loggingMessages(self, '8041', MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
        return

    # Handle reconnection for devices known by IEEE
    if MsgIEEE in self.IEEE2NWK:
        self.log.logging(
            'Input', 'Debug',
            f"Decode8041 - Received an IEEE: {MsgIEEE} with NwkId: {MsgShortAddress}, will try to reconnect"
        )
        if not DeviceExist(self, Devices, MsgShortAddress, MsgIEEE):
            if not zigpy_plugin_sanity_check(self, MsgShortAddress):
                handle_unknow_device(self, MsgShortAddress)
            self.log.logging(
                'Input', 'Log',
                f"Decode8041 - Unable to reconnect (unknown device) {MsgIEEE} {MsgShortAddress}"
            )
            return

        loggingMessages(self, '8041', MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
        return

    # Handle unknown devices
    self.log.logging(
        'Input', 'Log',
        f"WARNING - Decode8041 - Received an IEEE: {MsgIEEE} with NwkId: {MsgShortAddress}, not known by the plugin"
    )
