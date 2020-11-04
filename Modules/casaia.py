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

import struct
import json
import os

CASAIA_MANUF_CODE = '113c'
CASAIA_MANUF_CODE_BE = '3c11'
CASAIA_AC201_CLUSTER = 'ffad'

CASAIA_CONFIG_FILENAME = "Casa.ia.json"

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

def pollingOwon( self, key ):
    
    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """
    return False

def callbackDeviceAwake_Owon(self, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    Domoticz.Log("callbackDeviceAwake_Orvibo - Nwkid: %s, EndPoint: %s cluster: %s" \
            %(NwkId, EndPoint, cluster))

def casaiaReadRawAPS(self, Devices, NwkId, srcEp, ClusterId, dstNWKID, dstEP, MsgPayload):

    Domoticz.Log("OrviboReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
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
            read_multi_pairing_response( self, NwkId, Data)
        elif Command == '02':
            read_AC_status_response( self, NwkId, Data)
        elif Command in ['11', '12']:
            read_learned_data_group_status_request(self, NwkId, Data)


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

def casaia_swing_OnOff( self, NwkId, OnOff):
    
    if OnOff not in ('00', '01'):
        return
    EPout = get_ffad_endpoint(self, NwkId)

    write_attribute (self, NwkId, ZIGATE_EP, EPout, '0201', CASAIA_MANUF_CODE, '01', 'fd00', '10', OnOff, ackIsDisabled = is_ack_tobe_disabled(self, NwkId))
    self.log.logging( "Casaia", 'Debug', "swing_OnOff ++++ %s/%s OnOff: %s" %( NwkId, EPout, OnOff), NwkId)

def casaia_setpoint(self, NwkId, setpoint):
    pass

def casaia_system_mode( self, NwkId, system_mode):
    pass




## 0xFFAD Client to Server
def read_multi_pairing_code_request( self, NwkId ):
    # Command  0x00
    # determine which Endpoint
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type = '00' # Device type

    cluster_frame = '01'
    cmd = '00' # Ask the Tilt Blind to stop moving

    payload = cluster_frame + sqn + cmd  + device_type
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_multi_pairing_code_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)

def write_multi_pairing_code_request( self, NwkId ):
    # Command 0x01
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type = '00' # Device type
    device_id = '01'

    pairing_code_value = 845
    pairing_code = '%04x' %struct.unpack('H',struct.pack('>H', pairing_code_value))[0]

    cluster_frame = '05'
    cmd = '01'

    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type + device_id + pairing_code
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "write_multi_pairing_code_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)

def read_AC_status_request( self, NwkId):
    # Command 0x02
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type = '00' # Device type
    device_id = '01'

    cluster_frame = '05'
    cmd = '02'

    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type + device_id
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_AC_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)

def write_AC_status_request( self, NwkId):
    # Command 0x03

    # Switch On: Payload:  00 01 01 01 00
    # Switch Off: Payload: 00 01 01 00 00 
    # Cool :               00 01 01 03 00
    # Heat :               00 01 01 04 00
    # Fan To High:         00 01 04 03 00
    # Fan to Low:          00 01 04 01 00
    # Fan to Auto:         00 01 04 05 00
    # Setpoint 3O (3000)   00 01 02 b8 0b
    # Setpoint 12 (1200)   00 01 02 b0 04

    # Command 0x03
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type = '00' # Device type
    device_id = '01'

    # 0x01 para type system mode
    # 0x02para type heat temperature
    # 0x03 para type cool temperature
    # 0x04 para type fan mode

    para_type = '01'

    if para_type in ( '01', '04'):
        parameter_dt ='20' # 16bituint
        parameter = '%02x' %0x00
    else:
        parameter_dt ='21' # 16bituint
        parameter = '%04x' %0x0000

    cluster_frame = '01'
    cmd = '03'
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type + device_id  + parameter
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "write_AC_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)    

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

def read_learned_data_group_status_request(self, NwkId):
    # Command 0x12
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)
    device_type = '00' # Device type
    group_bitmap = '0000'
    cluster_frame = '05'
    cmd = '12'
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type + group_bitmap
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_learned_data_group_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)



## 0xFFAD Server to Client

def read_multi_pairing_response( self, nwkid, payload):
    # Command 0x00
    # 00 01 ffff 02 ffff 03 ffff 04 ffff 05 ffff

    device_type = payload[0:2]
    idx = 2
    while idx < len(payload):
        device_id = payload[idx:idx+2]
        idx += 2
        pairing_code = payload[idx:idx+4]
        idx += 4

def read_AC_status_response( self, nwkid, payload):
    # Command 0x02
    #00 00 01 4d03 c007 01 d007 280a 01

    status = payload[0:2]
    device_type = payload[2:4]
    device_id = payload[4:6]
    pairing_code = payload[6:10]
    current_temp = payload[10:14]
    system_mode = payload[14:16]
    heat_setpoint = payload[16:20]
    cool_stepoint = payload[20:24]
    fan_mode = payload[24:26]

def read_learned_data_group_status_request(self, nwkid, payload):
    # Command 0x11
    device_type = payload[0:2]
    status = payload[2:6]

def read_learned_data_group_status_request(self, nwkid, payload):
    # Cmmand 0x12
    device_type= payload[0:2]
    group_bitmap = payload[2:6]
    status = payload[6:8]
    group_num = payload[8:10]
    group_name = payload[10:34]


## Internal

def store_casaia_attribute( self, NwkId, Attribute, Value ):
    if 'CASA.IA' not in self.ListOfDevices[ NwkId ]:
        self.ListOfDevices[ NwkId ]['CASA.IA'] = {}
    self.ListOfDevices[ NwkId ]['CASA.IA'][ Attribute ] = Value

def open_casa_config( self ):

    casaiafilename =  self.pluginconf.pluginConf['pluginConf'] + "/" + CASAIA_CONFIG_FILENAME
    if os.path.isfile( casaiafilename ):
        with open( casaiafilename , 'rt') as handle:
            self.CasaiaPAC = {}
            try:
                self.CasaiaPAC = json.load( handle, encoding=dict)
            except json.decoder.JSONDecodeError as e:
                res = "Failed"
                Domoticz.Error("loadJsonDatabase poorly-formed %s, not JSON: %s" %(self.pluginConf['filename'],e))

def add_pac_entry(self, ieee):

    if self.CasaiaPAC is None:
        open_casa_config( self )

    self.CasaiaPAC[ieee] = {'IRCode': '000'}
    
    casaiafilename =  self.pluginconf.pluginConf['pluginConf'] + "/" + CASAIA_CONFIG_FILENAME
    with open( casaiafilename , 'wt') as handle:
        json.dump( self.CasaiaPAC, handle, sort_keys=True, indent=2)

def get_pac_code(self, ieee):

    if self.CasaiaPAC is None:
        open_casa_config( self )
    if ieee in self.CasaiaPAC and self.CasaiaPAC[ ieee ] and 'IRCode' in self.CasaiaPAC[ ieee ] and  self.CasaiaPAC[ ieee ]['IRCode'] != '000':
        return self.CasaiaPAC[ ieee ]['IRCode']
    else:
        return None