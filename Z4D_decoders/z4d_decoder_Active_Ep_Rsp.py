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

from Modules.zigbeeController import receiveZigateEpList
from Modules.tools import DeviceExist, updSQN, updLQI
from Modules.pairingProcess import interview_state_8045
from Modules.errorCodes import DisplayStatusCode


def Decode8045(self, Devices, MsgData, MsgLQI):
    MsgDataSQN, MsgDataStatus, MsgDataShAddr, MsgDataEpCount, MsgDataEPlist = (
        MsgData[:2], MsgData[2:4], MsgData[4:8], MsgData[8:10], MsgData[10:]
    )

    self.log.logging('Pairing', 'Debug', f'Decode8045 - Reception Active endpoint response: SQN: {MsgDataSQN} Status: {DisplayStatusCode(MsgDataStatus)} Short Addr: {MsgDataShAddr} List: {MsgDataEpCount} Ep List: {MsgDataEPlist}')

    if MsgDataShAddr == '0000':
        receiveZigateEpList(self, MsgDataEpCount, MsgDataEPlist)
        return

    if not DeviceExist(self, Devices, MsgDataShAddr):
        self.log.logging('Input', 'Log', f'Decode8045 - KeyError: MsgDataShAddr = {MsgDataShAddr}')
        return

    device = self.ListOfDevices[MsgDataShAddr]

    if device['Status'] == 'inDB':
        return

    device['Status'] = '8045'
    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)

    for i in range(0, 2 * int(MsgDataEpCount, 16), 2):
        tmpEp = MsgDataEPlist[i:i + 2]
        device['Ep'].setdefault(tmpEp, {})
        device.setdefault('Epv2', {})

        log_msg = f'[-] NEW OBJECT: {MsgDataShAddr} Active Endpoint Response Ep: {tmpEp} LQI: {int(MsgLQI, 16)}'
        self.log.logging('Input', 'Status', log_msg)

        if device['Status'] != '8045':
            log_msg = f'[-] NEW OBJECT: {MsgDataShAddr}/{tmpEp} receiving 0x8043 while in status: {device["Status"]}'
            self.log.logging('Input', 'Log', log_msg)

    device['NbEp'] = str(int(MsgDataEpCount, 16))
    interview_state_8045(self, MsgDataShAddr, RIA=None, status=None)

    self.log.logging('Pairing', 'Debug', f'Decode8045 - Device: {MsgDataShAddr} updated ListofDevices with {device["Ep"]}')
