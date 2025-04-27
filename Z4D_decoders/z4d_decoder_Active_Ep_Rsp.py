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

from Modules.errorCodes import DisplayStatusCode
from Modules.pairingProcess import interview_state_8045
from Modules.tools import DeviceExist, updLQI, updSQN, is_duplicate_sqn
from Modules.zigbeeController import receiveZigateEpList


def Decode8045(self, Devices, MsgData, MsgLQI):
    """Decode and process the 0x8045 Active Endpoint Response message."""

    # Log entry with important details
    self.log.logging('Input', 'Debug', f'Entering Decode8045 with args: MsgDataShAddr={MsgData[4:8]}, MsgDataLen={len(MsgData)}, MsgLQI={MsgLQI}')

    # Check for payload validity
    if len(MsgData) < 8:
        self.log.logging('Pairing', 'Error', f'Decode8045 - received invalid payload {MsgData}')
        return  

    MsgDataSQN, MsgDataStatus, MsgDataShAddr = MsgData[:2], MsgData[2:4], MsgData[4:8]

    if is_duplicate_sqn(self, MsgDataShAddr, MsgDataSQN):
        self.log.logging([ "Pairing", "Input"], 'Log', f'Decode8045 - Duplicate SQN: {MsgDataSQN} for device {MsgDataShAddr}')
        return
    # Update SQN
    updSQN(self, MsgDataShAddr, MsgDataSQN)

    if MsgDataShAddr == '0000':
        # If the short address is '0000', handle Zigbee coordinator endpoint list
        MsgDataEpCount, MsgDataEPlist = MsgData[8:10], MsgData[10:]
        receiveZigateEpList(self, MsgDataEpCount, MsgDataEPlist)
        return

    # Check if the device exists in the ListOfDevices
    if not DeviceExist(self, Devices, MsgDataShAddr):
        self.log.logging('Input', 'Log', f'Decode8045 - KeyError: MsgDataShAddr = {MsgDataShAddr}')
        return

    device = self.ListOfDevices[MsgDataShAddr]

    # If the device is already in the database, do nothing
    if device['Status'] in ( 'inDB', 'erasePDM'):
        self.log.logging('Pairing', 'Log', f'Decode8045 - already paired and discovered device {MsgDataShAddr}')
        return

    # Update device status and sequence number
    device['Status'] = '8045'
    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)

    # Validate the length of the data
    if len(MsgData) < 10:
        self.log.logging('Pairing', 'Error', f'Decode8045 - received invalid payload from {MsgDataShAddr} {MsgData}')
        return

    # Extract endpoint count and endpoint list
    MsgDataEpCount, MsgDataEPlist = MsgData[8:10], MsgData[10:]

    self.log.logging('Pairing', 'Debug', f'Decode8045 - Reception Active endpoint response: SQN: {MsgDataSQN} Status: {DisplayStatusCode(MsgDataStatus)} Short Addr: {MsgDataShAddr} List: {MsgDataEpCount} Ep List: {MsgDataEPlist}')

    # Process each endpoint
    for i in range(0, 2 * int(MsgDataEpCount, 16), 2):
        tmpEp = MsgDataEPlist[i:i + 2]
        device['Ep'].setdefault(tmpEp, {})
        device.setdefault('Epv2', {})

        # Log new endpoint creation
        log_msg = f'[-] NEW OBJECT: {MsgDataShAddr} Active Endpoint Response Ep: {tmpEp} LQI: {int(MsgLQI, 16)}'
        self.log.logging('Input', 'Status', log_msg)

        # Log if a device is in an unexpected status
        if device['Status'] != '8045':
            log_msg = f'[-] NEW OBJECT: {MsgDataShAddr}/{tmpEp} receiving 0x8043 while in status: {device["Status"]}'
            self.log.logging('Input', 'Log', log_msg)

    # Update the number of endpoints
    device['NbEp'] = str(int(MsgDataEpCount, 16))

    # Call to interview state function
    interview_state_8045(self, MsgDataShAddr, RIA=None, status=None)

    # Log the final updated device info
    self.log.logging('Pairing', 'Debug', f'Decode8045 - Device: {MsgDataShAddr} updated ListofDevices with {device["Ep"]}')