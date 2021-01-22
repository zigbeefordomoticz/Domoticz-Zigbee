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

import struct

from Classes.LoggingManagement import LoggingManagement

from Modules.tuyaTools import tuya_cmd, store_tuya_attribute, get_tuya_attribute
from Modules.basicOutputs import write_attribute
from Modules.zigateConsts import ZIGATE_EP

from Modules.tools import  checkAndStoreAttributeValue, is_ack_tobe_disabled, get_and_inc_SQN

from Modules.domoMaj import MajDomoDevice








#                   dp  dt  fn len  data
# Switch ON         65  01  00 01   01
# Switch Off        65  01  00 01   00
# Window Detect On  08  01  00 01   00
# Window Detect Off 08  01  00 01   01
# Antifreeze Off    0a  01  00 01   00
# Antifreeze On     0a  01  00 01   01
# Child Lock Off    28  01  00 01   00
# Child Lock On     28  01  00 01   01

# Calibration +6°   1b  02  00 04   00000006
# Calibration -5    1b  02  00 04   fffffffb
# Calibration 0     1b  02  00 04   00000000
# Setpoint 17°      67  02  00 04   000000aa   
# Sepoint  25.5     67  02  00 04   000000ff
# Program Off       6c  01  00 01   00

#       dp dt fn len data
# 00 01 65 01 00 01  00
# 00 17 0a 01 00 01  01
# 00 18 08 01 00 01  01
# 00 19 82 01 00 01  01
# 00 1a 1b 02 00 04  00000000
# 00 16 28 01 00 01  01
# 00 02 66 02 00 04  0000010c
# 00 03 67 02 00 04  00000032
# 00 04 69 05 00 01  00
# 00 05 6a 01 00 01  00
# 00 07 6c 01 00 01  01
# 00 ff 7b 00 00 11  04016800c801e000a0043800c8052800a0
# 01 00 7c 00 00 11  04016800c801e000a0043800c8052800a0
# 01 01 7d 00 00 11  04016800c801e000a0043800c8052800a0















def tuya_eTRV_registration(self, nwkid):
    
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_registration - Nwkid: %s" %nwkid)
    
    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = '01'
    write_attribute( self, nwkid, ZIGATE_EP, EPout, '0000', '0000', '00', 'ffde', '20', '13', ackIsDisabled = False)

def receive_setpoint( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Setpoint: %s" %(NwkId,srcEp ,int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', ( int(data,16) / 10 ), Attribute_ = '0012' )
    checkAndStoreAttributeValue( self, NwkId , '01', '0201', '0012' , int(data,16) )
    store_tuya_attribute( self, NwkId, 'SetPoint', data )

def receive_temperature( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Temperature: %s" %(NwkId,srcEp , int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0402', (int(data,16) / 10 ))
    checkAndStoreAttributeValue( self, NwkId , '01', '0402', '0000' , int(data,16)  )
    store_tuya_attribute( self, NwkId, 'Temperatyure', data )

def receive_preset( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    if data == '00':
        # Offline
        self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Mode to Offline" %(NwkId,srcEp ))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'OffLine' )
    elif data == '01':
        # Auto
        self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Mode to Auto" %(NwkId,srcEp ))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 1, Attribute_ = '001c' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Auto' )
        
    elif data == '02':
        # Manual
        self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )
    store_tuya_attribute( self, NwkId, 'ChangeMode', data )


def receive_childlock( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Child Lock/Unlock: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'ChildLock', data )

def receive_windowdetection( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Window Open: %s" %(NwkId,srcEp ,data))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0500', data )
    store_tuya_attribute( self, NwkId, 'OpenWindow', data )

def receive_valvestate( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Valve Detection: %s %s" %(NwkId,srcEp ,data, int(data,16)))
    store_tuya_attribute( self, NwkId, 'ValveDetection', data)

def receive_battery( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Battery status %s" %(NwkId,srcEp ,int(data,16)))
    checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
    self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)
    store_tuya_attribute( self, NwkId, 'BatteryStatus', data )

def receive_mode( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Mode: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'Mode', data )

def receive_valveposition( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Valve position: %s" %(NwkId,srcEp ,int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', int(data,16) , Attribute_ = '026d')
    store_tuya_attribute( self, NwkId, 'ValvePosition', data )

def receive_batteryalarm( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data ):
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s/%s Low Battery: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'LowBattery', data )


eTRV_MATRIX = {
    '_TZE200_ckud7u2l': { 
        0x67: receive_setpoint,
        0x03: receive_temperature,
        0x04: receive_preset,
        0x07: receive_childlock,
        0x12: receive_windowdetection,
        0x14: receive_valvestate,
        0x15: receive_battery,
        0x6a: receive_mode,
        0x6d: receive_valveposition
    }
}

def tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):

    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x data: %s" %(NwkId, dp, data))

    if _ModelName in eTRV_MATRIX and dp in eTRV_MATRIX[ _ModelName ]:
        eTRV_MATRIX[ _ModelName ][ dp](self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data)


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
    tuya_check_valve_detection( self, nwkid )
    # In Domoticz Setpoint is in ° , In Modules/command.py we multiplied by 100 (as this is the Zigbee standard).
    # Looks like in the Tuya 0xef00 cluster it is only expressed in 10th of degree
    setpoint_value = setpoint_value // 10
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0202'
    data = '%08x' %setpoint_value
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    
def tuya_trv_mode( self, nwkid, mode):
    self.log.logging( "Tuya", 'Debug', "tuya_setpoint - %s tuya_trv_mode: %s" %(nwkid, mode))
    tuya_check_valve_detection( self, nwkid )
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

