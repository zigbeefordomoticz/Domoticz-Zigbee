#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#   French translation: @martial83
#

import Domoticz

from Classes.LoggingManagement import LoggingManagement
from Modules.basicOutputs import write_attribute, sendZigateCmd, raw_APS_request
from Modules.tools import retreive_cmd_payload_from_8002, is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP

import struct
import json
import os

CASAIA_MANUF_CODE = '113c'
CASAIA_MANUF_CODE_BE = '3c11'
CASAIA_AC201_CLUSTER = 'ffad'

CASAIA_CONFIG_FILENAME = "Casa.ia.json"



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


def swing_OnOff( self, NwkId, OnOff):

    if OnOff not in ('00', '01'):
        return
    EPout = get_ffad_endpoint(self, NwkId)

    write_attribute (self, NwkId, ZIGATE_EP, EPout, '0201', CASAIA_MANUF_CODE, '01', 'fd00', '10', OnOff, ackIsDisabled = is_ack_tobe_disabled(self, NwkId))
    self.log.logging( "Casaia", 'Debug', "swing_OnOff ++++ %s/%s OnOff: %s" %( NwkId, EPout, OnOff), NwkId)


def casaiaReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    Domoticz.Log("OrviboReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload))

 
    if srcNWKID not in self.ListOfDevices:
        Domoticz.Error("%s not found in Database")
        return

    if 'Model' not in self.ListOfDevices[ srcNWKID]:
        return

    _Model = self.ListOfDevices[ srcNWKID]['Model']

    if ClusterID == CASAIA_AC201_CLUSTER:
        # AC201
        ( GlobalCommand, Sqn, ManufacturerCode, Command, Data, ) = retreive_cmd_payload_from_8002(MsgPayload)


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

def read_multi_pairing_code_request( self, NwkId ):
    # Command  0x00
    # determine which Endpoint
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type_dt = '20' # 8buint
    device_type = '00' # Device type

    cluster_frame = '01'
    cmd = '00' # Ask the Tilt Blind to stop moving

    payload = cluster_frame + sqn + cmd + device_type_dt + device_type
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_multi_pairing_code_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)

def write_multi_pairing_code_request( self, NwkId ):
    # Command 0x01
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type_dt = '20' # 8buint
    device_type = '00' # Device type
    devce_id_dt ='20'  #8bituint
    device_id = '01'
    pairing_code_dt ='21' # 16bituint

    pairing_code_value = 845
    pairing_code = '%04x' %struct.unpack('H',struct.pack('>H', pairing_code_value))[0]

    cluster_frame = '05'
    cmd = '01'

    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type_dt + device_type + devce_id_dt + device_id + pairing_code_dt + pairing_code
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "write_multi_pairing_code_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)


def read_AC_status_request( self, NwkId):
    # Command 0x02
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)

    device_type_dt = '20' # 8buint
    device_type = '00' # Device type
    devce_id_dt ='20'  #8bituint
    device_id = '01'

    cluster_frame = '01'
    cmd = '02'

    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type_dt + device_type + devce_id_dt + device_id
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "read_AC_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)


def write_AC_status_request( self, NwkId):
    # Command 0x03
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)


    device_type_dt = '20' # 8buint
    device_type = '00' # Device type
    devce_id_dt ='20'  #8bituint
    device_id = '01'

    # 0x01 para type system mode
    # 0x02para type heat temperature
    # 0x03 para type cool temperature
    # 0x04 para type fan mode
    para_type_dt = '20'
    para_type = '01'

    if para_type in ( '01', '04'):
        parameter_dt ='20' # 16bituint
        parameter = '%02x' %0x00
    else:
        parameter_dt ='21' # 16bituint
        parameter = '%04x' %0x0000

    cluster_frame = '01'
    cmd = '03'
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type_dt + device_type + devce_id_dt + device_id + parameter_dt + parameter
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "write_AC_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)    


def enter_IR_learn_mode(self, NwkId):
    # Command 0x10

    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)


    device_type_dt = '20' # 8buint
    device_type = '00' # Device type

    group_num_dt = '20'
    group_num = '01'

    button_num_dt = '20'
    button_num = '01'

    cluster_frame = '01'
    cmd = '10'
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type_dt + device_type + group_num_dt + group_num + button_num_dt + button_num
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "write_AC_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)    


def read_learned_data_button_status_request( self, NwkId):
    # Commande 0x14

    pass

def read_learned_data_button_name_status_request( self, NwkId):
    # Command 0x15
    
    pass

def brand_searching_request( self, NwkId):
    # Command 0x50

    cmd = '50'
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_sqn(self, NwkId)


    device_type_dt = '28' # 8buint
    device_type = '00' # Device type

    device_id_dt = '28'
    device_id = '01'

    brand_id_dt ='29'
    brand_id = '%04x' %struct.unpack('H',struct.pack('>H', 845))[0]

    group_id_dt = '28'
    group_id = '01'

    auto_search_dt ='28'
    auto_search = '00'

    pairing_code = '%04x' %struct.unpack('H',struct.pack('>H', 845))[0]

    cluster_frame = '01'
    
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd 
    payload += device_type_dt + device_type + brand_id_dt + brand_id + group_id_dt + group_id + auto_search_dt + auto_search + pairing_code
    raw_APS_request( self, NwkId, EPout, 'ffad', '0104', payload, zigate_ep=ZIGATE_EP)
    self.log.logging( "Casaia", 'Debug', "write_AC_status_request ++++ %s/%s payload: %s" %( NwkId, EPout, payload), NwkId)


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