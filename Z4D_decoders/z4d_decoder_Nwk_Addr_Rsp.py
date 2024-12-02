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
from Modules.domoTools import lastSeenUpdate
from Modules.errorCodes import DisplayStatusCode
from Modules.tools import (DeviceExist, loggingMessages,
                           zigpy_plugin_sanity_check)
from Modules.zb_tables_management import store_NwkAddr_Associated_Devices
from Z4D_decoders.z4d_decoder_helpers import \
    Network_Address_response_request_next_index


def Decode8040(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8040 - payload %s' % MsgData)
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgIEEE = MsgData[4:20]
    self.log.logging('Input', 'Debug', 'Decode8040 - Reception of Network Address response %s with status %s' % (MsgIEEE, MsgDataStatus))
    if MsgDataStatus != '00':
        return
    MsgShortAddress = MsgData[20:24]
    extendedResponse = False
    
    if len(MsgData) > 26:
        extendedResponse = True
        MsgNumAssocDevices = int(MsgData[24:26], 16)
        MsgStartIndex = int(MsgData[26:28], 16)
        MsgDeviceList = MsgData[28:]
        
    self.log.logging('Input', 'Debug', 'Network Address response, [%s] Status: %s Ieee: %s NwkId: %s' % (MsgSequenceNumber, DisplayStatusCode(MsgDataStatus), MsgIEEE, MsgShortAddress))

    if extendedResponse:
        self.log.logging('Input', 'Debug', '                        , Nb Associated Devices: %s Idx: %s Device List: %s' % (MsgNumAssocDevices, MsgStartIndex, MsgDeviceList))

        if MsgStartIndex + len(MsgDeviceList) // 4 != MsgNumAssocDevices:
            self.log.logging('Input', 'Debug', 'Decode 8040 - Receive an IEEE: %s with a NwkId: %s but would need to continue to get all associated devices' % (MsgIEEE, MsgShortAddress))
            Network_Address_response_request_next_index(self, MsgShortAddress, MsgIEEE, MsgStartIndex, len(MsgDeviceList) // 4)

    if MsgShortAddress in self.ListOfDevices and 'IEEE' in self.ListOfDevices[MsgShortAddress] and (self.ListOfDevices[MsgShortAddress]['IEEE'] == MsgIEEE):
        self.log.logging('Input', 'Debug', 'Decode 8041 - Receive an IEEE: %s with a NwkId: %s' % (MsgIEEE, MsgShortAddress))

        if extendedResponse:
            store_NwkAddr_Associated_Devices(self, MsgShortAddress, MsgStartIndex, MsgDeviceList)

        loggingMessages(self, '8040', MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
        lastSeenUpdate(self, Devices, NwkId=MsgShortAddress)
        return

    if MsgIEEE in self.IEEE2NWK:
        self.log.logging('Input', 'Log', 'Decode 8040 - Receive an IEEE: %s with a NwkId: %s, will try to reconnect' % (MsgIEEE, MsgShortAddress))

        if not DeviceExist(self, Devices, MsgShortAddress, MsgIEEE):

            if not zigpy_plugin_sanity_check(self, MsgShortAddress):
                handle_unknow_device(self, MsgShortAddress)
            self.log.logging('Input', 'Debug', 'Decode 8040 - Not able to reconnect (unknown device)')
            return

        if extendedResponse:
            store_NwkAddr_Associated_Devices(self, MsgShortAddress, MsgStartIndex, MsgDeviceList)

        loggingMessages(self, '8040', MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
        lastSeenUpdate(self, Devices, NwkId=MsgShortAddress)

    self.log.logging('Input', 'Error', 'Decode 8040 - Receive an IEEE: %s with a NwkId: %s, seems not known by the plugin' % (MsgIEEE, MsgShortAddress))