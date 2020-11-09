#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#   French translation: @martial83
#

import Domoticz

from Classes.LoggingManagement import LoggingManagement
from Modules.basicOutputs import write_attribute, sendZigateCmd, raw_APS_request
from Modules.tools import retreive_cmd_payload_from_8002, is_ack_tobe_disabled, checkAndStoreAttributeValue
from Modules.zigateConsts import ZIGATE_EP

from Modules.domoMaj import MajDomoDevice

import struct
import json
import os

CASAIA_MANUF_CODE = '113c'
CASAIA_MANUF_CODE_BE = '3c11'
CASAIA_AC201_CLUSTER = 'ffad'

CASAIA_CONFIG_FILENAME = "Casa.ia.json"

DEVICE_TYPE = '00'
DEVICE_ID = '01'

# Pairing
# Hub               Device
# Cmd Data          Cmd Data  
# 0x00 00    --->
#            <---   0x00 0001ffff02ffff03ffff04ffff05ffff
# 0x11 00    --->  
#            <---   0x11 000000
# 0x12 000000 --->
#             <---  0x12 0000000000
# 0x06 000000 --->
#             <---  0x06 0000000000


# Sending IR Code
# 0x01 00014d03 -->
#           
AC201_COMMAND = {
    'Off':       '010000',  # Ok 6/11
    'On':        '010100',  # Ok 6/11

    'Cool':      '010300',  # Ok 6/11
    'Heat':      '010400',  # Ok 6/11

    'Fan':       '010700',  # Ok 7/11
    'Dry':       '010800',  # Ok 7/11

    'HeatSetpoint':  '02', # Heat Setpoint Ok 7/11
    'CoolSetpoint':  '03', # Cool Setpoint Ok 7/11

    'FanLow':    '040100', # Ok 6/11
    'FanMedium': '040200', # Ok 6/11
    'FanHigh':   '040300', # Ok 6/11
    'FanAuto':   '040500', # Ok 6/11

}

def pollingCasaia( self, NwkId ):
    # This fonction is call if enabled to perform any Manufacturer specific polling action
    # The frequency is defined in the pollingSchneider parameter (in number of seconds)
    self.log.logging( "CasaIA", "Debug" , "pollingCasaia %s" %(NwkId ))
    read_AC_status_request( self, NwkId)
    return False

def casaia_AC201_pairing( self, NwkId):
    # Call during the Zigbee pairing process
    self.log.logging( "CasaIA", "Debug" , "casaia_AC201_pairing %s" %(NwkId ))

    # Read Existing Pairing Infos: Command 0x00
    read_multi_pairing_code_request( self, NwkId )

    # Add an entry in the PAC Casa file in order to get the IRCode
    add_pac_entry(self, self.ListOfDevices[ NwkId ]['IEEE'])

    # 
    # command_mysterious( self, NwkId, '000000')

    # In case we have already the IRCode 
    casaia_ac201_ir_pairing( self, NwkId)

    # Read Current AC Status
    read_AC_status_request( self, NwkId)

    # Command 0x11 - Payload 00
    # read_learned_data_group_status_request( self, NwkId)

    # Command 0x12 - Payload 000000
    # read_learned_data_group_name_request(self, NwkId)

    # Command 0x06 - Payload 000000 or 0x000100
    # command_mysterious( self, NwkId, '000100')




def callbackDeviceAwake_Casaia(self, NwkId, EndPoint, cluster):
    #This is fonction is call when receiving a message from a Manufacturer battery based device.
    #The function is called after processing the readCluster part

    self.log.logging( "CasaIA", "Debug" , "callbackDeviceAwake_Casaia %s/%s cluster: %s" %(NwkId, EndPoint, cluster ))


def casaia_ac201_ir_pairing( self, NwkId):
    self.log.logging( "CasaIA", "Debug" , "casaia_ac201_ir_pairing %s" %(NwkId ))
    pac_code = get_pac_code(self, self.ListOfDevices[ NwkId ]['IEEE'])
    self.log.logging( "CasaIA", "Debug" , "casaia_ac201_ir_pairing %s IRCode: %s" %(NwkId, pac_code ))
    if pac_code and pac_code != '000':
        write_multi_pairing_code_request( self, NwkId , pac_code )
        read_AC_status_request( self, NwkId)

def casaiaReadRawAPS(self, Devices, NwkId, srcEp, ClusterId, dstNWKID, dstEP, MsgPayload):

    self.log.logging( "CasaIA", "Debug" , "casaiaReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(NwkId, srcEp, ClusterId, dstNWKID, dstEP, MsgPayload))


    if NwkId not in self.ListOfDevices:
        Domoticz.Error("%s not found in Database")
        return

    if 'Model' not in self.ListOfDevices[ NwkId]:
        return
    _Model = self.ListOfDevices[ NwkId]['Model']

    if ClusterId == CASAIA_AC201_CLUSTER:
        # AC201
        ( GlobalCommand, Sqn, ManufacturerCode, Command, Data, ) = retreive_cmd_payload_from_8002(MsgPayload)

        if Command == '00':
            read_multi_pairing_response( self, Devices, NwkId, srcEp, Data)
        elif Command == '02':
            read_AC_status_response( self, Devices, NwkId, srcEp, Data)
        elif Command in ['11', '12']:
            read_learned_data_group_status_request(self, Devices, NwkId, srcEp, Data)
    
def casaia_swing_OnOff( self, NwkId, OnOff):
    
    if OnOff not in ('00', '01'):
        return
    EPout = get_ffad_endpoint(self, NwkId)

    write_attribute (self, NwkId, ZIGATE_EP, EPout, '0201', CASAIA_MANUF_CODE, '01', 'fd00', '10', OnOff, ackIsDisabled = is_ack_tobe_disabled(self, NwkId))
    self.log.logging( "Casaia", 'Debug', "swing_OnOff ++++ %s/%s OnOff: %s" %( NwkId, EPout, OnOff), NwkId)

def casaia_setpoint(self, NwkId, setpoint):
    self.log.logging( "CasaIA", "Debug" , "casaia_setpoint %s SetPoint: %s" %(NwkId, setpoint ))
    if  str(check_hot_cold_setpoint(self, NwkId)) == 'Heat':
        write_AC201_status_request( self, NwkId, 'HeatSetpoint', setpoint)
    elif str(check_hot_cold_setpoint(self, NwkId)) == 'Cool':
        write_AC201_status_request( self, NwkId, 'CoolSetpoint', setpoint)
    else:
      read_AC_status_request( self, NwkId)  

def casaia_system_mode( self, NwkId, Action):
    self.log.logging( "CasaIA", "Debug" , "casaia_system_mode %s Action: %s" %(NwkId, Action ))
    write_AC201_status_request( self, NwkId, Action)


## 0xFFAD Client to Server
def read_multi_pairing_code_request( self, NwkId ):
    # Command  0x00
    # determine which Endpoint
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    cluster_frame = '01'
    device_type = DEVICE_TYPE # Device type
    cmd = '00' 

    payload = cluster_frame + sqn + cmd  + device_type
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_multi_pairing_code_request ++++ %s payload: %s" %( NwkId, payload), NwkId)

def write_multi_pairing_code_request( self, NwkId , pairing_code_value ):
    # Command 0x01
    device_type = DEVICE_TYPE
    device_id = DEVICE_ID

    pairing_code = '%04x' %struct.unpack('H',struct.pack('>H', int(pairing_code_value)))[0]
    cmd = '01'
    payload =  cmd + device_type + device_id + pairing_code
    send_manuf_specific_cmd( self, NwkId, payload)
    self.log.logging( "Casaia", 'Debug', "write_multi_pairing_code_request ++++ %s payload: %s" %( NwkId, payload), NwkId)

def read_AC_status_request( self, NwkId):
    # Command 0x02
    self.log.logging( "Casaia", 'Debug', "read_AC_status_request NwkId: %s" %( NwkId), NwkId) 
    device_type = DEVICE_TYPE
    device_id = DEVICE_ID
    cmd = '02'
    payload =  cmd + device_type + device_id
    send_manuf_specific_cmd( self, NwkId, payload)
    self.log.logging( "Casaia", 'Debug', "read_AC_status_request ++++ %s payload: %s" %( NwkId, payload), NwkId)

def write_AC201_status_request( self, NwkId, Action, setpoint = None):
    # Command 0x03
    # 03 00 01 0001010000
    self.log.logging( "Casaia", 'Debug', "write_AC201_status_request NwkId: %s Action: %s Setpoint: %s" %( NwkId, Action, setpoint), NwkId) 

    # Check if the IRCode is set!
    ir_code = get_casaia_attribute( self, NwkId, 'IRCode', device_id = DEVICE_ID)
    if ir_code is None or ir_code == 'ffff':
        self.log.logging( "Casaia", 'Error', "write_AC201_status_request - %s IRCode %s not in place" %(NwkId, ir_code))
        casaia_ac201_ir_pairing( self, NwkId)
        return

    if Action not in AC201_COMMAND:
        self.log.logging( "Casaia", 'Error', "write_AC201_status_request - %s Unknow action: %s" %(NwkId,Action))
        return
    if Action in ( 'HeatSetpoint', 'CoolSetpoint') and setpoint is None:
        self.log.logging( "Casaia", 'Error', "write_AC201_status_request - %s Setpoint without a setpoint value !" %(NwkId))
        return        

    # Command 0x03
    device_type = '00' # Device type
    device_id = DEVICE_ID
    command = AC201_COMMAND[ Action ]
    if Action in ( 'HeatSetpoint', 'CoolSetpoint'):
        command += '%04x' %struct.unpack('H',struct.pack('>H', setpoint))[0]

    cmd = '03'
    payload =  cmd + device_type + device_id  + command

    send_manuf_specific_cmd( self, NwkId, payload)
    self.log.logging( "Casaia", 'Debug', "write_AC201_status_request ++++ %s payload: %s" %( NwkId, payload), NwkId) 
    read_AC_status_request( self, NwkId)

def read_learned_data_group_status_request( self, NwkId):
    # Command 0x11
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)
    device_type = '00' # Device type
    cluster_frame = '05'
    cmd = '11'
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_learned_data_group_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)

def read_learned_data_group_name_request(self, NwkId):
    # Command 0x12
    device_type = DEVICE_TYPE
    group_bitmap = '0000'

    cmd = '12'
    payload = cmd + device_type + group_bitmap
    send_manuf_specific_cmd( self, NwkId, payload)

    self.log.logging( "Casaia", 'Debug', "read_learned_data_group_status_request ++++ %s payload: %s" %( NwkId, payload), NwkId)

def command_mysterious( self, NwkId, magic):
    # Command 0x06

    cmd = '06'
    payload = cmd + magic
    send_manuf_specific_cmd( self, NwkId, payload)

    self.log.logging( "Casaia", 'Debug', "read_learned_data_group_status_request ++++ %s payload: %s" %( NwkId, payload), NwkId)  

## 0xFFAD Server to Client

def read_multi_pairing_response( self, Devices, NwkId, Ep, payload):
    # Command 0x00
    # 00 01 ffff 02 ffff 03 ffff 04 ffff 05 ffff
    self.log.logging( "CasaIA", "Debug" , "read_multi_pairing_response %s payload: %s" %(NwkId , payload))

    device_type = payload[0:2]
    store_casaia_attribute( self, NwkId, 'DeviceType', device_type )
    idx = 2
    while idx < len(payload):
        device_id = payload[idx:idx+2]
        idx += 2
        pairing_code = payload[idx:idx+4]
        store_casaia_attribute( self, NwkId, 'IRCode', pairing_code , device_id = device_id)
        idx += 4

def read_AC_status_response( self, Devices, NwkId, Ep, payload):
    # Command 0x02

    self.log.logging( "CasaIA", "Debug" , "read_AC_status_response %s payload: %s" %(NwkId , payload))

    status = payload[0:2]
    device_type = payload[2:4]
    device_id = payload[4:6]
    pairing_code = struct.unpack('H',struct.pack('>H', int(payload[6:10],16)))[0]
    current_temp = struct.unpack('H',struct.pack('>H', int(payload[10:14],16)))[0]
    system_mode = payload[14:16]
    heat_setpoint = struct.unpack('H',struct.pack('>H', int(payload[16:20],16)))[0]
    cool_stepoint = struct.unpack('H',struct.pack('>H', int(payload[20:24],16)))[0]
    fan_mode = payload[24:26]

    self.log.logging( "CasaIA", "Debug" , "read_AC_status_response Status: %s device_type: %s device_id: %s pairing_code: %s current_temp: %s system_mode: %s heat_setpoint: %s cool_setpoint: %s fan_mode: %s"
        %( status, device_type, device_id, pairing_code, current_temp, system_mode, heat_setpoint, cool_stepoint, fan_mode))

    store_casaia_attribute( self, NwkId, 'DeviceType', device_type )
    store_casaia_attribute( self, NwkId, 'IRCode', str(pairing_code) , device_id = device_id)
    store_casaia_attribute( self, NwkId, 'DeviceStatus', status , device_id = device_id)
    store_casaia_attribute( self, NwkId, 'CurrentTemp', current_temp , device_id = device_id)
    store_casaia_attribute( self, NwkId, 'SystemMode', system_mode , device_id = device_id)
    store_casaia_attribute( self, NwkId, 'HeatSetpoint', heat_setpoint , device_id = device_id)
    store_casaia_attribute( self, NwkId, 'CoolSetpoint', cool_stepoint , device_id = device_id)
    store_casaia_attribute( self, NwkId, 'FanMode', fan_mode , device_id = device_id)


    # Update Current Temperature Widget
    temp = round( current_temp / 100 , 1)
    self.log.logging( "CasaIA", "Debug" , "read_AC_status_response Status: %s request Update Temp: %s" %( NwkId, temp))
    MajDomoDevice(self, Devices, NwkId, Ep, '0402', temp)

    # Update Fan Mode
    self.log.logging( "CasaIA", "Debug" , "read_AC_status_response Status: %s request Update Fan Mode: %s" %( NwkId, fan_mode))
    if system_mode == '00':
        MajDomoDevice(self, Devices, NwkId, Ep, '0202', '00')
    else:
        MajDomoDevice(self, Devices, NwkId, Ep, '0202', fan_mode)

    # Update SetPoint
    if str(check_hot_cold_setpoint(self, NwkId)) == 'Heat':
        setpoint = str(round( heat_setpoint / 100, 1))
        self.log.logging( "CasaIA", "Debug" , "read_AC_status_response Status: %s request Update Setpoint: %s" %( NwkId, setpoint))
        MajDomoDevice(self, Devices, NwkId, Ep, '0201', setpoint, Attribute_ ='0012')

    elif str(check_hot_cold_setpoint(self, NwkId)) == 'Cool':
        setpoint = str(round( cool_stepoint / 100, 1))
        self.log.logging( "CasaIA", "Debug" , "read_AC_status_response Status: %s request Update Setpoint: %s" %( NwkId, setpoint))
        MajDomoDevice(self, Devices, NwkId, Ep, '0201', setpoint, Attribute_ ='0012')

    # Update System Mode
    self.log.logging( "CasaIA", "Debug" , "read_AC_status_response Status: %s request Update System Mode: %s" %( NwkId, system_mode))
    MajDomoDevice(self, Devices, NwkId, Ep, '0201', system_mode)
    
    



def read_learned_data_group_status_request_response(self, Devices, NwkId, srcEp, payload):
    # Command 0x11
    device_type = payload[0:2]
    status = payload[2:6]

def read_learned_data_group_name_request_response(self, Devices, NwkId, srcEp, payload):
    # Cmmand 0x12
    device_type= payload[0:2]
    group_bitmap = payload[2:6]
    status = payload[6:8]
    group_num = payload[8:10]
    group_name = payload[10:34]
    store_casaia_attribute( self, NwkId, 'GroupBitmap', group_bitmap )
    store_casaia_attribute( self, NwkId, 'GroupNum', group_num )
    store_casaia_attribute( self, NwkId, 'GroupName', group_name )


## Internal

def check_hot_cold_setpoint(self, NwkId):
    system_mode = get_casaia_attribute( self, NwkId, 'SystemMode', device_id = DEVICE_ID )
    if system_mode == '04':
        return 'Heat'
    if system_mode == '03':
        return 'Cool'
    return None


def send_manuf_specific_cmd( self, NwkId, payload):

    cluster_frame = '05'
    sqn = get_sqn(self, NwkId)    
    EPout = get_ffad_endpoint(self, NwkId)

    data = cluster_frame + CASAIA_MANUF_CODE_BE + sqn
    data += payload
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', data, zigate_ep=ZIGATE_EP)

def get_ffad_endpoint( self, NwkId):
    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "ffad" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp
    return EPout

def get_sqn(self, NwkId):
    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['SQN'] != {} and self.ListOfDevices[NwkId]['SQN'] != '' ):
        sqn = '%02x' % (int(self.ListOfDevices[NwkId]['SQN'],16) + 1)
    return sqn

def store_casaia_attribute( self, NwkId, Attribute, Value , device_id = None):
    
    if 'CASA.IA' not in self.ListOfDevices[ NwkId ]:
        self.ListOfDevices[ NwkId ]['CASA.IA'] = {}
    if device_id:
        if device_id not in self.ListOfDevices[ NwkId ]['CASA.IA']:
            self.ListOfDevices[ NwkId ]['CASA.IA'][ device_id ] = {}

        self.ListOfDevices[ NwkId ]['CASA.IA'][ device_id ][ Attribute ] = Value
        
    else:
        self.ListOfDevices[ NwkId ]['CASA.IA'][ Attribute ] = Value

def get_casaia_attribute( self, NwkId, Attribute, device_id = None):

    if 'CASA.IA' not in self.ListOfDevices[ NwkId ]:
        self.log.logging( "CasaIA", "Debug" , "get_casaia_attribute - %s CASA.IA not found in %s" %(NwkId,self.ListOfDevices[ NwkId ]))
        return None
    if device_id:
        if Attribute not in self.ListOfDevices[ NwkId ]['CASA.IA'][ device_id ]:
            self.log.logging( "CasaIA", "Debug" , "get_casaia_attribute (1) - %s Attribute: %s not found in %s" %(NwkId,self.ListOfDevices[ NwkId ]['CASA.IA'][device_id]))
            return None
        return self.ListOfDevices[ NwkId ]['CASA.IA'][ device_id ][ Attribute ]
    if Attribute not in self.ListOfDevices[ NwkId ]['CASA.IA']:
        self.log.logging( "CasaIA", "Debug" , "get_casaia_attribute (2) - %s Attribute: %s not found in %s" %(NwkId,self.ListOfDevices[ NwkId ]['CASA.IA']))
        return None
    return self.ListOfDevices[ NwkId ]['CASA.IA'][ Attribute ]

def open_casa_config( self ): # OK 6/11/2020

    casaiafilename =  self.pluginconf.pluginConf['pluginConfig'] + "/" + CASAIA_CONFIG_FILENAME
    self.CasaiaPAC = {}
    if os.path.isfile( casaiafilename ):
        with open( casaiafilename , 'rt') as handle:
            try:
                self.CasaiaPAC = json.load( handle, encoding=dict)
            except json.decoder.JSONDecodeError as e:
                res = "Failed"
                Domoticz.Error("loadJsonDatabase poorly-formed %s, not JSON: %s" %(self.pluginConf['filename'],e))

def add_pac_entry(self, ieee): # OK 6/11/2020

    if self.CasaiaPAC is None:
        open_casa_config( self )

    if ieee not in self.CasaiaPAC:
        self.CasaiaPAC[ieee] = {'IRCode': '000'}
    
    casaiafilename =  self.pluginconf.pluginConf['pluginConfig'] + "/" + CASAIA_CONFIG_FILENAME
    with open( casaiafilename , 'wt') as handle:
        json.dump( self.CasaiaPAC, handle, sort_keys=True, indent=2)

def get_pac_code(self, ieee):

    open_casa_config( self )
    if ieee in self.CasaiaPAC and self.CasaiaPAC[ ieee ] and 'IRCode' in self.CasaiaPAC[ ieee ] and  self.CasaiaPAC[ ieee ]['IRCode'] != '000':
        return self.CasaiaPAC[ ieee ]['IRCode']
    else:
        return None