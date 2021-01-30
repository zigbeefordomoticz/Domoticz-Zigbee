#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: tuya.py

    Description: Tuya specific

"""
# https://github.com/zigpy/zha-device-handlers/issues/357

import Domoticz

from Modules.tuyaTools import tuya_cmd, store_tuya_attribute, get_tuya_attribute
from Modules.basicOutputs import write_attribute, raw_APS_request
from Modules.zigateConsts import ZIGATE_EP
from Modules.tools import  checkAndStoreAttributeValue, is_ack_tobe_disabled, get_and_inc_SQN
from Modules.domoMaj import MajDomoDevice

def tuya_eTRV_registration(self, nwkid):
    
    self.log.logging( "Tuya", 'Debug', "tuya_eTRV_registration - Nwkid: %s" %nwkid)
    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = '01'
    write_attribute( self, nwkid, ZIGATE_EP, EPout, '0000', '0000', '00', 'ffde', '20', '13', ackIsDisabled = False)

    # (3) Cmd 0x03 on Cluster 0xef00  (Cluster Specific)
    payload = '11' + get_and_inc_SQN( self, nwkid ) + '03'
    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, nwkid))


def receive_setpoint( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):

    self.log.logging( "Tuya", 'Debug', "receive_setpoint - Nwkid: %s/%s Setpoint: %s" %(NwkId,srcEp ,int(data,16)))
    if model_target == 'TS0601-thermostat':
        setpoint = int(data,16)
    else:
        setpoint = int(data,16) / 10 
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', setpoint, Attribute_ = '0012' )
    checkAndStoreAttributeValue( self, NwkId , '01', '0201', '0012' , int(data,16) * 10 )
    store_tuya_attribute( self, NwkId, 'SetPoint', data )

def receive_temperature( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_temperature - Nwkid: %s/%s Temperature: %s" %(NwkId,srcEp , int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0402', (int(data,16) / 10 ))
    checkAndStoreAttributeValue( self, NwkId , '01', '0402', '0000' , int(data,16)  )
    store_tuya_attribute( self, NwkId, 'Temperature', data )

def receive_onoff( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_onoff - Nwkid: %s/%s Mode to OffOn: %s" %(NwkId,srcEp, data ))
    if model_target == 'TS0601-eTRV3':
        if data == '00':
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'OffLine' )
        else:
            
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c')
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )
        store_tuya_attribute( self, NwkId, 'Switch', data )
        return


    if data == '00':
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c')
    else:
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c')
    checkAndStoreAttributeValue( self, NwkId , '01', '0006', '0000' , data )
    store_tuya_attribute( self, NwkId, 'Switch', data )    

def receive_preset( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    if data == '00':
        if model_target == 'TS0601-thermostat':
            # Manual
            self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )
        else:
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
        if model_target == 'TS0601-thermostat':
            self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Offline" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Offline' )
        else:
            # Manual
            self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )
    store_tuya_attribute( self, NwkId, 'ChangeMode', data )

def receive_childlock( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_childlock - Nwkid: %s/%s Child Lock/Unlock: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'ChildLock', data )

def receive_windowdetection( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_windowdetection - Nwkid: %s/%s Window Open: %s" %(NwkId,srcEp ,data))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0500', data )
    store_tuya_attribute( self, NwkId, 'OpenWindow', data )

def receive_windowdetection_status( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_windowdetection_status - Nwkid: %s/%s Window Open: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'OpenWindowDetection', data )

def receive_valvestate( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):
    self.log.logging( "Tuya", 'Debug', "receive_valvestate - Nwkid: %s/%s Valve Detection: %s %s" %(NwkId,srcEp ,data, int(data,16)))
    store_tuya_attribute( self, NwkId, 'ValveDetection', data)

def receive_battery( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):
    # Works for ivfvd7h model , _TYST11_zivfvd7h Manufacturer
    self.log.logging( "Tuya", 'Debug', "receive_battery - Nwkid: %s/%s Battery status %s" %(NwkId,srcEp ,int(data,16)))
    checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
    self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)
    store_tuya_attribute( self, NwkId, 'BatteryStatus', data )

def receive_lowbattery(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receice_lowbattery - Nwkid: %s/%s DataType: %s Battery status %s" %(NwkId,srcEp ,datatype ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'LowBattery', data )

def receive_mode( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):
    self.log.logging( "Tuya", 'Debug', "receive_mode - Nwkid: %s/%s Mode: %s" %(NwkId,srcEp ,data))
    store_tuya_attribute( self, NwkId, 'Mode', data )

def receive_schedule_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    if model_target == 'TS0601-thermostat':
        # Manual
        if data == '00':
            self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Auto" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 1, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Auto' )   
        #elif data == '01':
        #    self.log.logging( "Tuya", 'Debug', "receive_preset - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
        #    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
        #    checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Auto' )                    

def receive_heating_state(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Thermostat
    self.log.logging( "Tuya", 'Debug', "receive_mode - Nwkid: %s/%s Mode: %s" %(NwkId,srcEp ,data))
    # Value inverted
    if data == '00':
        value = '01'
    else:
        value = '00:'
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', value , Attribute_ = '0124')

    store_tuya_attribute( self, NwkId, 'HeatingMode', data )

def receive_valveposition( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):
    self.log.logging( "Tuya", 'Debug', "receive_valveposition - Nwkid: %s/%s Valve position: %s" %(NwkId,srcEp ,int(data,16)))
    MajDomoDevice(self, Devices, NwkId, srcEp, '0201', int(data,16) , Attribute_ = '026d')
    store_tuya_attribute( self, NwkId, 'ValvePosition', data )

def receive_calibration( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):
    self.log.logging( "Tuya", 'Debug', "receive_calibration - Nwkid: %s/%s Low Battery: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'Calibration', data )

def receive_program_mode( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_program_mode - Nwkid: %s/%s Program Mode: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'TrvMode', data )    

def receive_antifreeze( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug', "receive_antifreeze - Nwkid: %s/%s AntiFreeze: %s" %(NwkId,srcEp ,int(data,16)))
    store_tuya_attribute( self, NwkId, 'AntiFreeze', data )        
 
def receive_dumy( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):
    self.log.logging( "Tuya", 'Debug', "receive and unknown data point - Nwkid: %s/%s dp: %s datatype: %s data: 0x%s" %(NwkId,srcEp ,dp, datatype, data))
    pass


eTRV_MODELS = {
    # Siterwell GS361A-H04 
    'ivfvd7h': 'TS0601-eTRV1',
    'fvq6avy': 'TS0601-eTRV1',
    'eaxp72v': 'TS0601-eTRV1',
    'TS0601-eTRV1': 'TS0601-eTRV1',

    # Moes HY368 / HY369
    'kud7u2l': 'TS0601-eTRV2',
    'TS0601-eTRV2': 'TS0601-eTRV2',

    # Saswell SEA802 / SEA801 Zigbee versions
    '88teujp': 'TS0601-eTRV3',
    'GbxAXL2': 'TS0601-eTRV3',
    'uhszj9s': 'TS0601-eTRV3',
    'TS0601-eTRV3': 'TS0601-eTRV3',
}

TUYA_eTRV_MODEL =  'ivfvd7h', 'fvq6avy', 'eaxp72v', 'kud7u2l', '88teujp', 'GbxAXL2', 'uhszj9s', 'TS0601-eTRV1', 'TS0601-eTRV2', 'TS0601-eTRV3', 'TS0601-eTRV'

eTRV_MATRIX = {
    'TS0601-thermostat': {  'FromDevice': {     # @d2e2n2o / Electric
                            0x02: receive_preset,
                            0x03: receive_schedule_mode,
                            0x10: receive_setpoint,
                            0x18: receive_temperature,   # Ok
                            0x24: receive_heating_state,
                            0x28: receive_childlock,
                            },
                        'ToDevice': {
                            'Switch': 0x01,    # Ok
                            'SetPoint': 0x10,
                            'ChildLock': 0x28,
                            }
                        },
    # eTRV
    'TS0601-eTRV1': {   'FromDevice': {         # Confirmed with @d2e2n2o _TYST11_zivfvd7h
                            0x02: receive_setpoint,
                            0x03: receive_temperature, 
                            0x04: receive_preset,  
                            0x15: receive_battery,         
                        },
                        'ToDevice': {
                            'SetPoint': 0x02, 'TrvMode': 0x04
                            } 
                        },

    'TS0601-eTRV2': {   'FromDevice': {        #     # https://github.com/pipiche38/Domoticz-Zigate/issues/779 ( @waltervl)
                            0x02: receive_setpoint,
                            0x03: receive_temperature, 
                            0x04: receive_preset,
                            0x07: receive_childlock, 
                            0x12: receive_windowdetection, 
                            0x15: receive_battery,  
                            0x14: receive_valvestate,
                            0x6d: receive_valveposition,     
                            0x6e: receive_lowbattery,
                        },
                        'ToDevice': {
                            'SetPoint': 0x02,
                            'TrvMode': 0x04}
                        },

    'TS0601-eTRV3': {   'FromDevice': {         # Confirmed with @d2e2n2o et @pipiche
                            0x08: receive_windowdetection_status,
                            0x82: receive_dumy,                     # Water Scale Prof ???
                            0x12: receive_windowdetection,
                            0x1b: receive_calibration,
                            0x28: receive_childlock,
                            0x65: receive_onoff,
                            0x66: receive_temperature,
                            0x67: receive_setpoint,
                            0x69: receive_dumy,                     # ????
                            0x6a: receive_dumy,                     # LH
                            0x6c: receive_preset,
                            0x6d: receive_valveposition,
                            0x6e: receive_lowbattery,
                            },
                        'ToDevice': {
                            'Switch': 0x65,
                            'SetPoint': 0x67,
                            'ChildLock': 0x28,
                            'ValveDetection': 0x14,
                            'WindowDetection': 0x08,
                            'Calibration': 0x1b,
                            'TrvMode': 0x6c,
                            }
                        },

    'TS0601-eTRV': {
        'FromDevice': {
            0x02: receive_setpoint,
            0x03: receive_temperature, 
            0x04: receive_preset,  
            0x08: receive_windowdetection_status,
            0x15: receive_battery,         

            0x12: receive_windowdetection,
            0x1b: receive_calibration,
            0x28: receive_childlock,
            0x65: receive_onoff,
            0x66: receive_temperature,
            0x67: receive_setpoint,
            0x69: receive_dumy,                     # ????
            0x6a: receive_dumy,                     # LH
            0x6c: receive_preset,
            0x6d: receive_valveposition,
            0x6e: receive_lowbattery,
            0x82: receive_dumy,                     # Water Scale Prof ???
        },
        'ToDevice': {
            'SetPoint': 0x02,
            'TrvMode': 0x04}            
    }   
}

def tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging( "Tuya", 'Debug2', "tuya_eTRV_response - Nwkid: %s dp: %02x datatype: %s data: %s" %(NwkId, dp, datatype, data))

    model_target = 'TS0601-eTRV1'
    if _ModelName in eTRV_MODELS:
        model_target = eTRV_MODELS[ _ModelName ]

    manuf_name = get_manuf_name( self, NwkId )

    if datatype == '00':
        receive_dumy( self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data )
        return

    if model_target in eTRV_MATRIX:
        if dp in eTRV_MATRIX[ model_target ]['FromDevice']:
            eTRV_MATRIX[ model_target ]['FromDevice'][ dp](self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
        else:
           self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x datatype: %s data: %s UNKNOW dp for Manuf: %s, Model: %s" %(NwkId, dp, datatype, data, manuf_name, _ModelName))
    else:
        self.log.logging( "Tuya", 'Debug', "tuya_eTRV_response - Nwkid: %s dp: %02x datatype: %s data: %s UNKNOW Manuf %s, Model: %s" %(NwkId, dp, datatype, data, manuf_name, _ModelName))

def tuya_trv_valve_detection( self, nwkid, onoff):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_valve_detection - %s ValveDetection: %s" %(nwkid, onoff))
    if onoff not in ( 0x00, 0x01 ):
        return
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'ValveDetection')
    self.log.logging( "Tuya", 'Debug', "tuya_trv_valve_detection - %s dp for SetPoint: %s" %(nwkid, dp))
    if dp:
        action = '%02x01' %dp
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        data = '%02x' %onoff
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_trv_window_detection( self, nwkid, onoff):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_window_detection - %s WindowDetection: %s" %(nwkid, onoff))
    if onoff not in ( 0x00, 0x01 ):
        return
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'WindowDetection')
    self.log.logging( "Tuya", 'Debug', "tuya_trv_window_detection - %s dp for WindowDetection: %s" %(nwkid, dp))
    if dp:
        action = '%02x01' %dp
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        data = '%02x' %onoff
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_trv_child_lock( self, nwkid, onoff):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_child_lock - %s ChildLock: %s" %(nwkid, onoff))
    if onoff not in ( 0x00, 0x01 ):
        return
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'ChildLock')
    self.log.logging( "Tuya", 'Debug', "tuya_trv_child_lock - %s dp for ChildLock: %s" %(nwkid, dp))
    if dp:
        action = '%02x01' %dp
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        data = '%02x' %onoff
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_trv_calibration( self, nwkid, onoff):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_calibration - %s Calibration: %s" %(nwkid, onoff))
    if onoff not in ( 0x00, 0x01 ):
        return
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'Calibration')
    self.log.logging( "Tuya", 'Debug', "tuya_trv_calibration - %s dp for Calibration: %s" %(nwkid, dp))
    if dp:
        action = '%02x02' %dp
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        data = '%02x' %onoff
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_trv_onoff( self, nwkid, onoff):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_preset - %s Switch: %s" %(nwkid, onoff))
    if onoff not in ( 0x00, 0x01 ):
        return
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'Switch')
    self.log.logging( "Tuya", 'Debug', "tuya_trv_preset - %s dp for Switch: %s" %(nwkid, dp))
    if dp:
        action = '%02x01' %dp
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        data = '%02x' %onoff
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_check_valve_detection( self, NwkId ):
    if 'ValveDetection' not in self.ListOfDevices[ NwkId ]['Param']:
        return
    current_valve_detection = get_tuya_attribute( self, NwkId, 'ValveDetection')
    if current_valve_detection != self.ListOfDevices[ NwkId ]['Param']['ValveDetection']:
        tuya_trv_valve_detection( self, NwkId, self.ListOfDevices[ NwkId ]['Param']['ValveDetection'])

def tuya_check_window_detection( self, NwkId ):
    if 'WindowDetection' not in self.ListOfDevices[ NwkId ]['Param']:
        return
    current_valve_detection = get_tuya_attribute( self, NwkId, 'WindowDetection')
    if current_valve_detection != self.ListOfDevices[ NwkId ]['Param']['WindowDetection']:
        tuya_trv_window_detection( self, NwkId, self.ListOfDevices[ NwkId ]['Param']['WindowDetection'])

def tuya_check_childlock( self, NwkId ):
    if 'ChildLock' not in self.ListOfDevices[ NwkId ]['Param']:
        return
    current_valve_detection = get_tuya_attribute( self, NwkId, 'ChildLock')
    if current_valve_detection != self.ListOfDevices[ NwkId ]['Param']['ChildLock']:
        tuya_trv_window_detection( self, NwkId, self.ListOfDevices[ NwkId ]['Param']['ChildLock'])

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
        if get_model_name( self, nwkid ) == 'TS0601-thermostat':
            # Setpoiint is defined in ° and not centidegree
            setpoint_value = setpoint_value // 10
        data = '%08x' %setpoint_value
        # determine which Endpoint
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_mode( self, nwkid, mode):
    self.log.logging( "Tuya", 'Debug', "tuya_trv_mode - %s tuya_trv_mode: %s" %(nwkid, mode))
    sqn = get_and_inc_SQN( self, nwkid )
    dp = get_datapoint_command( self, nwkid, 'TrvMode')
    self.log.logging( "Tuya", 'Debug', "tuya_trv_mode - %s dp for TrvMode: %s" %(nwkid, dp))
    if dp:
        EPout = '01'
        cluster_frame = '11'
        cmd = '00' # Command
        if get_model_name( self, nwkid ) == 'TS0601-eTRV3':
            action = '%02x01' %dp # Mode
        else:
            action = '%02x04' %dp # Mode
        data = '%02x' %( mode // 10 )
        tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)   

        if get_model_name( self, nwkid ) == 'TS0601-eTRV3':
            if mode // 10 == 0x00: # Off
                tuya_trv_onoff( self, nwkid, 0x00)
            else:
                tuya_trv_onoff( self, nwkid, 0x01)


def get_manuf_name( self, nwkid ):
    if 'Manufacturer Name' not in self.ListOfDevices[ nwkid ]:
        return None
    return self.ListOfDevices[ nwkid ]['Manufacturer Name']

def get_model_name( self, nwkid ):
    if 'Model' not in self.ListOfDevices[ nwkid ]:
        return None
    _ModelName = self.ListOfDevices[ nwkid ]['Model']
    model_target = 'TS0601-eTRV1'
    if _ModelName in eTRV_MODELS:
        model_target = eTRV_MODELS[ _ModelName ]
    return model_target

def get_datapoint_command( self, nwkid, cmd):
    _model_name = get_model_name( self, nwkid )
    if _model_name not in eTRV_MATRIX:
        self.log.logging( "Tuya", 'Debug', "get_datapoint_command - %s %s not found in eTRV_MATRIX" %(nwkid, _model_name))
        return None
    if cmd not in eTRV_MATRIX[ _model_name ]['ToDevice']:
        self.log.logging( "Tuya", 'Debug', "get_datapoint_command - %s %s not found in eTRV_MATRIX[ %s ]['ToDevice']" %(nwkid, cmd, _model_name))
        return None
    return eTRV_MATRIX[ _model_name ]['ToDevice'][ cmd ]
