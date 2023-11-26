#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

from Modules.zigbeeController import receiveZigateEpList
from Modules.tools import DeviceExist, updSQN, updLQI
from Modules.pairingProcess import interview_state_8045
from Modules.errorCodes import DisplayStatusCode

def Decode8045(self, Devices, MsgData, MsgLQI):
    MsgDataSQN = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataEpCount = MsgData[8:10]
    MsgDataEPlist = MsgData[10:]

    self.log.logging('Pairing', 'Debug', 'Decode8045 - Reception Active endpoint response: SQN: %s Status: %s Short Addr: %s List: %s Ep List:  %s' % (
        MsgDataSQN, DisplayStatusCode(MsgDataStatus), MsgDataShAddr, MsgDataEpCount, MsgDataEPlist))

    if MsgDataShAddr == '0000':
        receiveZigateEpList(self, MsgDataEpCount, MsgDataEPlist)
        return

    if not DeviceExist(self, Devices, MsgDataShAddr):
        self.log.logging('Input', 'Error', 'Decode8045 - KeyError: MsgDataShAddr = ' + MsgDataShAddr)
        return

    if self.ListOfDevices[MsgDataShAddr]['Status'] == 'inDB':
        return

    self.ListOfDevices[MsgDataShAddr]['Status'] = '8045'
    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)

    for i in range(0, 2 * int(MsgDataEpCount, 16), 2):
        tmpEp = MsgDataEPlist[i:i + 2]
        if not self.ListOfDevices[MsgDataShAddr]['Ep'].get(tmpEp):
            self.ListOfDevices[MsgDataShAddr]['Ep'][tmpEp] = {}
            
        if not self.ListOfDevices[MsgDataShAddr].get('Epv2'):
            self.ListOfDevices[MsgDataShAddr]['Epv2'] = {}
            
        self.log.logging('Input', 'Status', '[%s] NEW OBJECT: %s Active Endpoint Response Ep: %s LQI: %s' % (
            '-', MsgDataShAddr, tmpEp, int(MsgLQI, 16)))
        
        if self.ListOfDevices[MsgDataShAddr]['Status'] != '8045':
            self.log.logging('Input', 'Log', '[%s] NEW OBJECT: %s/%s receiving 0x8043 while in status: %s' % (
                '-', MsgDataShAddr, tmpEp, self.ListOfDevices[MsgDataShAddr]['Status']))
            
    self.ListOfDevices[MsgDataShAddr]['NbEp'] = str(int(MsgDataEpCount, 16))
    interview_state_8045(self, MsgDataShAddr, RIA=None, status=None)

    self.log.logging('Pairing', 'Debug', 'Decode8045 - Device: ' + str(MsgDataShAddr) + ' updated ListofDevices with ' + str(self.ListOfDevices[MsgDataShAddr]['Ep']))
