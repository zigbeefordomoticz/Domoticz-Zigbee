#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: tuya.py

    Description: Tuya specific

"""

import Domoticz

from Modules.tuyaTools import tuya_cmd, store_tuya_attribute, get_tuya_attribute
from Modules.basicOutputs import write_attribute
from Modules.zigateConsts import ZIGATE_EP
from Modules.tools import  checkAndStoreAttributeValue, is_ack_tobe_disabled, get_and_inc_SQN
from Modules.domoMaj import MajDomoDevice



def tuya_eTRV_registration(self, nwkid):
    
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_registration - Nwkid: %s" %nwkid)
    
    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = '01'
    write_attribute( self, nwkid, ZIGATE_EP, EPout, '0000', '0000', '00', 'ffde', '20', '13', ackIsDisabled = False)

def receive_setpoint( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_setpoint - Nwkid: %s/%s Setpoint: %s" %(NwkId,srcEp ,int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', ( int(data,16) / 10 ), Attribute_ = '0012' )
    checkAndStoreAttributeValue( self, NwkId , '01', '0201', '0012' , int(data,16) )
    store_tuya_attribute( self, NwkId, 'SetPoint', data )

def receive_temperature( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "receive_temperature - Nwkid: %s/%s Temperature: %s" %(NwkId,srcEp , int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0402', (int(data,16) / 10 ))
    checkAndStoreAttributeValue( self, NwkId , '01', '0402', '0000' , int(data,16)  )
    store_tuya_attribute( self, NwkId, 'Temperatyure', data )

def receive_preset( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    if data == '00':
        # Offline
        self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Offline" %(NwkId,srcEp ))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'OffLine' )
    elif data == '01':
        # Auto
        self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Auto" %(NwkId,srcEp ))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 1, Attribute_ = '001c' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Auto' )
        
    elif data == '02':
        # Manual
        self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )
    store_tuya_attribute( self, NwkId, 'ChangeMode', data )


def receive_childlock( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "receive_childlock - Nwkid: %s/%s Child Lock/Unlock: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'ChildLock', data )

def receive_windowdetection( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "receive_windowdetection - Nwkid: %s/%s Window Open: %s" %(NwkId,srcEp ,data))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0500', data )
    store_tuya_attribute( self, NwkId, 'OpenWindow', data )

def receive_valvestate( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_valvestate - Nwkid: %s/%s Valve Detection: %s %s" %(NwkId,srcEp ,data, int(data,16)))
    store_tuya_attribute( self, NwkId, 'ValveDetection', data)

def receive_battery( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_battery - Nwkid: %s/%s Battery status %s" %(NwkId,srcEp ,int(data,16)))
    checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
    self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)
    store_tuya_attribute( self, NwkId, 'BatteryStatus', data )

def receive_mode( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_mode - Nwkid: %s/%s Mode: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'Mode', data )

def receive_valveposition( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_valveposition - Nwkid: %s/%s Valve position: %s" %(NwkId,srcEp ,int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', int(data,16) , Attribute_ = '026d')
    store_tuya_attribute( self, NwkId, 'ValvePosition', data )

def receive_batteryalarm( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_batteryalarm - Nwkid: %s/%s Low Battery: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'LowBattery', data )

def receive_calibration( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "receive_calibration - Nwkid: %s/%s Low Battery: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'Calibration', data )

def receive_program_mode( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "receive_program_mode - Nwkid: %s/%s Program Mode: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'ProgramMode', data )    

def receive_antifreeze( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "receive_antifreeze - Nwkid: %s/%s AntiFreeze: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'AntiFreeze', data )        


eTRV_MATRIX = {
    '_TZE200_ckud7u2l': { 
        'FromDevice': {
            0x67: receive_setpoint,
            0x03: receive_temperature,
            0x04: receive_preset,
            0x07: receive_childlock,
            0x12: receive_windowdetection,
            0x14: receive_valvestate,
            0x15: receive_battery,
            0x6a: receive_mode,
            0x6d: receive_valveposition
        },
        'ToDevice': {
            'SetPoint': 0x02,
        }
    },
    '_TZE200_c88teujp': { 
        'FromDevice': {
            0x67: receive_setpoint,
            0x03: receive_temperature,
            0x04: receive_preset,
            0x28: receive_childlock,
            0x08: receive_windowdetection,
            0x14: receive_valvestate,
            0x15: receive_battery,
            0x6a: receive_mode,
            0x6d: receive_valveposition,
            0x1b: receive_calibration,
            0x6c: receive_program_mode,
            0x6a: receive_antifreeze
        },
        'ToDevice': {
            'SetPoint': 0x67,
        }
    }
}


def tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x data: %s" %(NwkId, dp, data))
    manuf_name = get_manuf_name( self, NwkId )
    if manuf_name in eTRV_MATRIX:
        if dp in eTRV_MATRIX[ manuf_name ]['FromDevice']:
            eTRV_MATRIX[ manuf_name ]['FromDevice'][ dp](self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data)
        else:
           self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x data: %s UNKNOW dp" %(NwkId, dp, data))
    else:
        self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x data: %s UNKNOW Model %s" %(NwkId, dp, data, _ModelName))


def tuya_trv_valve_detection( self, nwkid, onoff):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_valve_detection - %s ValveDetection: %s" %(nwkid, onoff))
    if onoff not in ( 0x00, 0x01 ):
        return
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0114'
    data = '%02x' %onoff
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_check_valve_detection( self, NwkId ):
    if 'ValveDetection' not in self.ListOfDevices[ NwkId ]['Param']:
        return
    current_valve_detection = get_tuya_attribute( self, NwkId, 'ValveDetection')
    if current_valve_detection != self.ListOfDevices[ NwkId ]['Param']['ValveDetection']:
        tuya_trv_valve_detection( self, NwkId, self.ListOfDevices[ NwkId ]['Param']['ValveDetection'])

def tuya_setpoint( self, nwkid, setpoint_value):
    self.log.logging( "Tuya", 'Debug', "tuya_setpoint - %s setpoint: %s" %(nwkid, setpoint_value))
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'SetPoint')
    self.log.logging( "Tuya", 'Debug', "tuya_setpoint - %s dp for SetPoint: %s" %(nwkid, dp))
    if dp:
        action = '%02x02' %dp
        # In Domoticz Setpoint is in ° , In Modules/command.py we multiplied by 100 (as this is the Zigbee standard).
        # Looks like in the Tuya 0xef00 cluster it is only expressed in 10th of degree
        setpoint_value = setpoint_value // 10
        data = '%08x' %setpoint_value
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_trv_mode( self, nwkid, mode):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_mode - %s tuya_trv_mode: %s" %(nwkid, mode))
    # In Domoticz Setpoint is in ° , In Modules/command.py we multiplied by 100 (as this is the Zigbee standard).
    # Looks like in the Tuya 0xef00 cluster it is only expressed in 10th of degree
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0404' # Mode
    data = '%02x' %( mode // 10 )
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)   

def get_manuf_name( self, nwkid ):
    if 'Manufacturer Name' not in self.ListOfDevices[ nwkid ]:
        return None
    return self.ListOfDevices[ nwkid ]['Manufacturer Name']

def get_datapoint_command( self, nwkid, cmd):
    Manuf_Name = self.ListOfDevices[ nwkid ]['Manufacturer Name']
    if get_manuf_name( self, nwkid ) not in eTRV_MATRIX:
        return None
    if cmd not in eTRV_MATRIX[ Manuf_Name ]['ToDevice']:
        return None
    return eTRV_MATRIX[ Manuf_Name ]['ToDevice'][ cmd ]
