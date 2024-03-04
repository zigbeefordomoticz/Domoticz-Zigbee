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

import time

from Classes.ZigateTransport.sqnMgmt import TYPE_APP_ZCL
from Modules.basicOutputs import handle_unknow_device
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import lastSeenUpdate
from Modules.tools import (get_device_config_param,
                           get_deviceconf_parameter_value, timeStamped, updLQI,
                           updSQN, zigpy_plugin_sanity_check)


def Decode0400(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0400 - message: %s' % MsgData)
    if len(MsgData) != 14:
        return
    
    sqn = MsgData[:2]
    SrcAddress = MsgData[2:6]
    SrcEndPoint = MsgData[6:8]
    EnrollResponseCode = MsgData[10:12]
    ZoneId = MsgData[12:14]
    
    self.log.logging('Input', 'Log', 'Decode0400 - Source Address: %s Source Ep: %s EnrollmentResponseCode: %s ZoneId: %s' % (SrcAddress, SrcEndPoint, EnrollResponseCode, ZoneId))
    if self.iaszonemgt:
        self.iaszonemgt.IAS_zone_enroll_request_response(SrcAddress, SrcEndPoint, EnrollResponseCode, ZoneId)
        
def Decode8046(self, Devices, MsgData, MsgLQI):
    MsgDataSQN = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataLenList = MsgData[8:10]
    MsgDataMatchList = MsgData[10:]
    
    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)
    
    self.log.logging('Input', 'Log', 'Decode8046 - Match Descriptor response: SQN: %s Status: %s Nwkid: %s Lenght: %s List: %s' % (MsgDataSQN, MsgDataStatus, MsgDataShAddr, MsgDataLenList, MsgDataMatchList))
    if MsgDataStatus == '00' and MsgDataLenList != '00' and self.iaszonemgt:
        idx = 0
        while idx < int(MsgDataLenList, 16):
            ep = MsgDataMatchList[idx:idx + 2]
            idx += 2
            self.log.logging('Input', 'Log', 'Decode8046 - Match Descriptor response Nwkid: %sfound Ep: %s Matching 0500' % (MsgDataShAddr, ep))
            self.iaszonemgt.IAS_write_CIE_after_match_descriptor(MsgDataShAddr, ep)

    
def Decode8400(self, Devices, MsgData, MsgLQI):
    sqn = MsgData[:2]
    zonetype = MsgData[2:6]
    manufacturercode = MsgData[6:10]
    nwkid = MsgData[10:14]
    ep = MsgData[14:16]
    self.log.logging('Input', 'Log', 'Decode8400 - IAS Zone Enroll Request NwkId: %s/%s Sqn: %s ZoneType: %s Manuf: %s' % (nwkid, ep, sqn, zonetype, manufacturercode))
    if self.iaszonemgt:
        self.iaszonemgt.IAS_zone_enroll_request(nwkid, ep, zonetype, sqn)
    
def Decode8401(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8401 - Reception Zone status change notification: ' + MsgData)
    
    zone_status_fields =_extract_zone_status_info(self, MsgData)
    MsgSQN, MsgEp, MsgClusterId, MsgSrcAddrMode, MsgSrcAddr, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay = zone_status_fields
    if zone_status_fields is None:
        error_message = f'Decode8401 - Reception Zone status change notification but incorrect Address Mode: {MsgSrcAddrMode} with MsgData {MsgData}'
        self.log.logging('Input', 'Error', error_message)
        return
    
    ias_dic = self.ListOfDevices[MsgSrcAddr].setdefault('Ep', {}).setdefault(MsgEp, {}).setdefault(MsgClusterId, {})
    ias_dic.setdefault('0002', {})

    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    
    if MsgSrcAddr not in self.ListOfDevices:
        self.log.logging('Input', 'Error', 'Decode8401 - unknown IAS device %s from plugin' % MsgSrcAddr)
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    
    if 'Health' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Health'] not in ('Disabled',):
        self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
        
    timeStamped(self, MsgSrcAddr, 33793)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    
    Model = ''
    if 'Model' in self.ListOfDevices[MsgSrcAddr]:
        Model = self.ListOfDevices[MsgSrcAddr]['Model']
        
    self.log.logging('Input', 'Debug', 'Decode8401 - MsgSQN: %s MsgSrcAddr: %s MsgEp:%s MsgClusterId: %s MsgZoneStatus: %s MsgExtStatus: %s MsgZoneID: %s MsgDelay: %s' % (MsgSQN, MsgSrcAddr, MsgEp, MsgClusterId, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay), MsgSrcAddr)

    if Model == 'PST03A-v2.2.5':
        Decode8401_PST03Av225(self, Devices, MsgSrcAddr, MsgEp, Model, MsgZoneStatus)
        return
    
    status_bits = [int(MsgZoneStatus, 16) >> i & 1 for i in range(10)]
    alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef = status_bits

    _ensure_ep_cluster_structure(self, MsgSrcAddr, MsgEp, MsgClusterId)
    
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002'] = 'alarm1: %s, alarm2: %s, tamper: %s, battery: %s, Support Reporting: %s, restore Reporting: %s, trouble: %s, acmain: %s, test: %s, battdef: %s' % (alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef)
    self.log.logging('Input', 'Debug', 'IAS Zone for device:%s  - %s' % (MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002']), MsgSrcAddr)
    self.log.logging('Input', 'Debug', 'Decode8401 MsgZoneStatus: %s ' % MsgZoneStatus[2:4], MsgSrcAddr)
    
    value = MsgZoneStatus[2:4]
    
    if get_device_config_param(self, MsgSrcAddr, 'HeimanDoorBellBuuton'):
        self.log.logging('Input', 'Debug',f"Decode8401 HeimanDoorBellBuuton: {MsgSrcAddr} {zone_status_fields}", MsgSrcAddr)

        button_pressed = ( 8000, 8004 )
        if int(zone_status_fields,16) in button_pressed:
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', '01')
            tamper = int(zone_status_fields,16) & 1 << 2
            if tamper:
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0009', '01')
        return
        
    motion_via_IAS_alarm = get_device_config_param(self, MsgSrcAddr, 'MotionViaIASAlarm1')
    
    self.log.logging('Input', 'Debug', 'MotionViaIASAlarm1 = %s' % motion_via_IAS_alarm)
    
    ias_alarm1_2_merged = get_deviceconf_parameter_value(self, Model, 'IASAlarmMerge', return_default=None)
    
    self.log.logging('Input', 'Debug', 'IASAlarmMerge = %s' % ias_alarm1_2_merged)
    
    if ias_alarm1_2_merged:
        self.log.logging('Input', 'Debug', 'IASAlarmMerge alarm1 %s alarm2 %s' % (alarm1, alarm2))
        combined_alarm = alarm2 << 1 | alarm1
        self.log.logging('Input', 'Debug', 'IASAlarmMerge combined value = %02d' % combined_alarm)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', '%02d' % combined_alarm)
        
    elif motion_via_IAS_alarm is not None and motion_via_IAS_alarm == 1:
        self.log.logging('Input', 'Debug', 'Motion detected sending to MajDomo %s/%s %s' % (MsgSrcAddr, MsgEp, alarm1 or alarm2))
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0406', '%02d' % (alarm1 or alarm2))

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ('lumi.sensor_magnet', 'lumi.sensor_magnet.aq2', 'lumi.sensor_magnet.acn001', 'lumi.magnet.acn001'):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', '%02d' % alarm1)

    elif Model not in ('RC-EF-3.0', 'RC-EM'):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, MsgClusterId, '%02d' % (alarm1 or alarm2))

    if tamper:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0009', '01')

    else:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0009', '00')

    if battery:
        self.log.logging('Input', 'Log', 'Decode8401 Low Battery or defective battery: Device: %s %s/%s' % (MsgSrcAddr, battdef, battery), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['IASBattery'] = 5

    else:
        self.ListOfDevices[MsgSrcAddr]['IASBattery'] = 100

    if 'IAS' in self.ListOfDevices[MsgSrcAddr] and 'ZoneStatus' in self.ListOfDevices[MsgSrcAddr]['IAS']:
        if not isinstance(self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'], dict):
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = {}

        _update_ias_zone_status(self, MsgSrcAddr, MsgEp, MsgZoneStatus)

def _extract_zone_status_info(self, msg_data):
    MsgSQN = msg_data[:2]
    MsgEp = msg_data[2:4]
    MsgClusterId = msg_data[4:8]
    MsgSrcAddrMode = msg_data[8:10]

    if MsgSrcAddrMode == '02':
        MsgSrcAddr = msg_data[10:14]
        MsgZoneStatus = msg_data[14:18]
        MsgExtStatus = msg_data[18:20]
        MsgZoneID = msg_data[20:22]
        MsgDelay = msg_data[22:26]

    elif MsgSrcAddrMode == '03':
        MsgSrcAddr = msg_data[10:26]
        MsgZoneStatus = msg_data[26:30]
        MsgExtStatus = msg_data[30:32]
        MsgZoneID = msg_data[32:34]
        MsgDelay = msg_data[34:38]

    else:
        return None  # Or raise an exception if appropriate

    return MsgSQN, MsgEp, MsgClusterId, MsgSrcAddrMode, MsgSrcAddr, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay

def _ensure_ep_cluster_structure(self, msg_src_addr, msg_ep, msg_cluster_id):
    ep_cluster = self.ListOfDevices.get(msg_src_addr, {}).get('Ep', {}).get(msg_ep, {})

    if 'Ep' not in ep_cluster or msg_ep not in ep_cluster:
        return

    ep_0500 = ep_cluster[msg_ep].setdefault('0500', {})

    if not isinstance(ep_0500, dict):
        ep_cluster[msg_ep][msg_cluster_id]['0500'] = {}

    ep_0500['0002'] = ep_0500.get('0002', {})

def _update_ias_zone_status(self, msg_src_addr, msg_ep, msg_zone_status):
    status_bits = [int(msg_zone_status, 16) >> i & 1 for i in range(10)]

    zone_status_names = ['alarm1', 'alarm2', 'tamper', 'battery', 'suprrprt', 'restrprt', 'trouble', 'acmain', 'test', 'battdef']

    zone_status_values = dict(zip(zone_status_names, status_bits))

    ias_device = self.ListOfDevices.get(msg_src_addr, {}).setdefault('IAS', {})
    zone_status = ias_device.setdefault('ZoneStatus', {})

    for status_name, status_value in zone_status_values.items():
        zone_status[status_name] = status_value

    zone_status['GlobalInfos'] = self.ListOfDevices.get(msg_src_addr, {}).get('Ep', {}).get(msg_ep, {}).get('0500', {}).get('0002', {})
    zone_status['TimeStamp'] = int(time.time())

       
def Decode8401_PST03Av225(self, Devices, MsgSrcAddr, MsgEp, Model, MsgZoneStatus):
    iData = int(MsgZoneStatus, 16) & 8 >> 3
    self.ListOfDevices[MsgSrcAddr]['IASBattery'] = '100' if iData == 0 else '0'
    
    if MsgEp == '02':
        iData = int(MsgZoneStatus, 16) & 1
        value = '%02d' % iData
        self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-v2.2.5 door/windows status: ' + value, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0500', value)

    elif MsgEp == '01':
        iData = int(MsgZoneStatus, 16) & 1
        if iData == 1:
            value = '%02d' % iData
            self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-v2.2.5 mouvements alarm', MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0406', value)

        iData = (int(MsgZoneStatus, 16) & 4) >> 2

        if iData == 1:
            value = '%02d' % iData
            self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-V2.2.5  tamper alarm', MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', value)

    else:
        self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-v2.2.5, unknown EndPoint: ' + MsgEp, MsgSrcAddr)

    return