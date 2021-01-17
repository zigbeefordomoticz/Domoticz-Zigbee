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

from Modules.tools import  checkAndStoreAttributeValue, is_ack_tobe_disabled, get_and_inc_SQN

from Modules.domoMaj import MajDomoDevice



def tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):

    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x data: %s" %(NwkId, dp, data))

    if dp == 0x02: # Setpoint Change target temp
        # data is setpoint
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Setpoint: %s" %(NwkId,srcEp ,int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', ( int(data,16) / 10 ), Attribute_ = '0012' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '0012' , int(data,16) )
        store_tuya_attribute( self, NwkId, 'SetPoint', data )

    elif dp in (0x03): # 0x0203 Thermostat temperature
        # Temperature notification
        # data is the temp
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Temperature: %s" %(NwkId,srcEp , int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0402', (int(data,16) / 10 ))
        checkAndStoreAttributeValue( self, NwkId , '01', '0402', '0000' , int(data,16)  )
        store_tuya_attribute( self, NwkId, 'Temperatyure', data )

    elif dp == 0x04: # Change mode
        if data == '00':
            # Offline
            self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Offline" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'OffLine' )
        elif data == '01':
            # Auto
            self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Auto" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 1, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Auto' )
            
        elif data == '02':
            # Manual
            self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )
        store_tuya_attribute( self, NwkId, 'ChangeMode', data )

    elif dp == 0x07: # Child Lock unlocked/locked
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Child Lock/Unlock: %s" %(NwkId,srcEp ,data))
        store_tuya_attribute( self, NwkId, 'ChildLock', data )

    elif dp == 0x12: # Open Window
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Window Open: %s" %(NwkId,srcEp ,data))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0500', data )
        store_tuya_attribute( self, NwkId, 'OpenWindow', data )

    elif dp == 0x14: # Valve detection state
        # Use Dimer to report On/Off
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Valve Detection: %s" %(NwkId,srcEp ,data))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0006', data , Attribute_ = '0014')
        store_tuya_attribute( self, NwkId, 'ValveDetection', data )

    elif dp == 0x15: # Battery status
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Battery status %s" %(NwkId,srcEp ,int(data,16)))
        checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
        self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)
        store_tuya_attribute( self, NwkId, 'BatteryStatus', data )

    elif dp == 0x6a: # Mode
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode: %s" %(NwkId,srcEp ,data))
        store_tuya_attribute( self, NwkId, 'Mode', data )

    elif dp == 0x6d: # Valve position in %
        # Use Dimer to report %
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Valve position: %s" %(NwkId,srcEp ,int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0008', int(data,16) , Attribute_ = '026d')
        store_tuya_attribute( self, NwkId, 'ValvePsotion', data )





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

