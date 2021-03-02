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

from datetime import datetime, timedelta



from Classes.LoggingManagement import LoggingManagement
from Modules.tools import updSQN, get_and_inc_SQN, is_ack_tobe_disabled
from Modules.domoMaj import MajDomoDevice
from Modules.tuyaTools import (tuya_cmd, store_tuya_attribute)
from Modules.tuyaSiren import tuya_siren_response
from Modules.tuyaTRV import tuya_eTRV_response, TUYA_eTRV_MODEL
from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import write_attribute,raw_APS_request

# Tuya TRV Commands
# https://medium.com/@dzegarra/zigbee2mqtt-how-to-add-support-for-a-new-tuya-based-device-part-2-5492707e882d

# Cluster 0xef00
# Commands 
#   Direction: Coordinator -> Device 0x00 SetPoint 
#   Direction: Device -> Coordinator 0x01 
#   Direction: Device -> Coordinator 0x02 Setpoint command response


TUYA_SIREN_MANUFACTURER =  ( '_TZE200_d0yu2xgi', '_TYST11_d0yu2xgi' )
TUYA_SIREN_MODEL        =  ( 'TS0601', '0yu2xgi')

TUYA_DIMMER_MANUFACTURER = ( '_TZE200_dfxkcots', )
TUYA_SWITCH_MANUFACTURER = ( '_TZE200_7tdtqgwv', )
TUYA_CURTAIN_MAUFACTURER = ( "_TZE200_cowvfni3", "_TZE200_wmcdj3aq", "_TZE200_fzo2pocs", "_TZE200_nogaemzt", "_TZE200_5zbp6j0u", \
                            "_TZE200_fdtjuw7u", "_TZE200_bqcqqjpb", "_TZE200_zpzndjez", "_TYST11_cowvfni3", "_TYST11_wmcdj3aq", \
                            "_TYST11_fzo2pocs", "_TYST11_nogaemzt", "_TYST11_5zbp6j0u", "_TYST11_fdtjuw7u", "_TYST11_bqcqqjpb", "_TYST11_zpzndjez", \
                            '_TZE200_rddyvrci', '_TZE200_nkoabg8w', '_TZE200_xuzcvlku', '_TZE200_4vobcgd3', '_TZE200_pk0sfzvr', '_TYST11_xu1rkty3', '_TZE200_zah67ekd' )

TUYA_CURTAIN_MODEL =  ( "owvfni3", "mcdj3aq", "zo2pocs", "ogaemzt", "zbp6j0u", "dtjuw7u", "qcqqjpb", "pzndjez", )

TUYA_THERMOSTAT_MANUFACTURER = ( '_TZE200_aoclfnxz', '_TYST11_zuhszj9s', '_TYST11_jeaxp72v', )

TUYA_eTRV1_MANUFACTURER = ( '_TZE200_kfvq6avy', '_TZE200_ckud7u2l', '_TYST11_KGbxAXL2', '_TYST11_ckud7u2l', )

# https://github.com/zigpy/zigpy/discussions/653#discussioncomment-314395
TUYA_eTRV1_MANUFACTURER = ( '_TYST11_zivfvd7h', '_TZE200_zivfvd7h', '_TYST11_kfvq6avy', '_TZE200_kfvq6avy', '_TYST11_jeaxp72v',)
TUYA_eTRV2_MANUFACTURER = ( '_TZE200_ckud7u2l', '_TYST11_ckud7u2l' ,)
TUYA_eTRV3_MANUFACTURER = ( '_TZE200_c88teujp', '_TYST11_KGbxAXL2', '_TYST11_zuhszj9s', )
TUYA_eTRV_MANUFACTURER =  ( '_TYST11_2dpplnsn', '_TZE200_wlosfena', '_TZE200_fhn3negr', '_TZE200_qc4fpmcn', )
TUYA_eTRV_MODEL =         ( 'TS0601', 'TS0601-eTRV', 'TS0601-eTRV1', 'TS0601-eTRV2', 'TS0601-eTRV3', 'TS0601-thermostat', 'uhszj9s', 'GbxAXL2', '88teujp', \
                             'kud7u2l', 'eaxp72v', 'fvq6avy', 'ivfvd7h',)

TUYA_TS0601_MODEL_NAME = TUYA_eTRV_MODEL + TUYA_CURTAIN_MODEL + TUYA_SIREN_MODEL

def pollingTuya( self, key ):
    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    #if  ( self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE):
    #    return True

    return False

def callbackDeviceAwake_Tuya(self, NwkId, EndPoint, cluster):
    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """
    Domoticz.Log("callbackDeviceAwake_Tuya - Nwkid: %s, EndPoint: %s cluster: %s" \
            %(NwkId, EndPoint, cluster))

    return

def tuyaReadRawAPS(self, Devices, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    if NwkId not in self.ListOfDevices:
        return
    if ClusterID != 'ef00':
        return
    if 'Model' not in self.ListOfDevices[NwkId]:
        return
    _ModelName = self.ListOfDevices[NwkId]['Model']

    if len(MsgPayload) < 6:
        self.log.logging( "Tuya", 'Debug2', "tuyaReadRawAPS - MsgPayload %s too short" %(MsgPayload),NwkId )
        return

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    updSQN( self, NwkId, sqn)

    # Send a Default Response ( why might check the FCF eventually )
    send_default_response( self, NwkId, srcEp , sqn)

    cmd = MsgPayload[4:6] # uint8
    
    if cmd == '24': # Time Synchronisation
        send_timesynchronisation( self, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload[6:])

    elif cmd in ('01', '02', ):
        status = MsgPayload[6:8]   #uint8
        transid = MsgPayload[8:10] # uint8
        dp = int(MsgPayload[10:12],16)
        datatype = int(MsgPayload[12:14],16)
        fn = MsgPayload[14:16]
        len_data = MsgPayload[16:18]
        data = MsgPayload[18:]
        self.log.logging( "Tuya", 'Debug2', "tuyaReadRawAPS - command %s MsgPayload %s/ Data: %s" %(cmd, MsgPayload, MsgPayload[6:]),NwkId )
        tuya_response( self,Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data )

    else:
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Model: %s UNMANAGED Nwkid: %s/%s fcf: %s sqn: %s cmd: %s data: %s" %(
            _ModelName, NwkId, srcEp, fcf, sqn, cmd, MsgPayload[6:]),NwkId )

def tuya_response( self,Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data ):

    self.log.logging( "Tuya", 'Debug', "tuya_response - Model: %s Nwkid: %s/%s dp: %02x data: %s"
        %(_ModelName, NwkId, srcEp, dp, data),NwkId )

    if _ModelName == 'TS0601-switch':
        tuya_switch_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == 'TS0601-curtain':
        tuya_curtain_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in ( 'TS0601-thermostat' ):
        tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in ( TUYA_eTRV_MODEL ):
        tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == 'TS0601-sirene':
        tuya_siren_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == 'TS0601-dimmer':
        tuya_dimmer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    else:
        attribute_name = 'UnknowDp_0x%02x_Dt_0x%02x' %(dp,datatype)
        store_tuya_attribute( self, NwkId, attribute_name, data ) 
        self.log.logging( "Tuya", 'Log', "tuya_response - Model: %s UNMANAGED Nwkid: %s/%s dp: %02x data type: %s data: %s" %(
            _ModelName, NwkId, srcEp,  dp, datatype, data),NwkId )

def send_timesynchronisation( self, NwkId, srcEp, ClusterID, dstNWKID, dstEP, serial_number):
    
    #Request: cmd: 0x24  Data: 0x0008
    #0008 60 0d 80 29600d8e39
    if NwkId not in self.ListOfDevices:
        return 
    sqn = get_and_inc_SQN( self, NwkId )

    field1 = '0d'
    field2 = '80'
    field3 = '29'

    EPOCTime = datetime(1970,1,1)
    now = datetime.utcnow()
    UTCTime_in_sec = int((now  - EPOCTime).total_seconds())
    LOCALtime_in_sec = int((utc_to_local( now )  - EPOCTime).total_seconds())

    utctime = "%08x" %UTCTime_in_sec
    localtime = "%08x" %LOCALtime_in_sec
    self.log.logging( "Tuya", 'Debug', "send_timesynchronisation - %s/%s UTC: %s Local: %s" %(
        NwkId, srcEp, UTCTime_in_sec, LOCALtime_in_sec ))

    payload = '11' + sqn + '24' + serial_number + utctime + localtime
    raw_APS_request( self, NwkId, srcEp, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, NwkId))
    self.log.logging( "Tuya", 'Debug', "send_timesynchronisation - %s/%s " %(NwkId, srcEp ))

def utc_to_local(dt):
    # https://stackoverflow.com/questions/4563272/convert-a-python-utc-datetime-to-a-local-datetime-using-only-python-standard-lib
    import time
    if time.localtime().tm_isdst:
        return dt - timedelta(seconds = time.altzone)
    else:
        return dt - timedelta(seconds = time.timezone)


def send_default_response( self, Nwkid, srcEp , sqn):
    if Nwkid not in self.ListOfDevices:
        return 
    payload = '00' + sqn + '0b' + '01' + '00'
    raw_APS_request( self, Nwkid, srcEp, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, Nwkid))
    self.log.logging( "Tuya", 'Debug2', "send_default_response - %s/%s " %(Nwkid, srcEp ))


def tuya_switch_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    if dp == 0x01:
        # Switch 1
        pass

    elif dp == 0x02:
        # Switch 2
        pass
    elif dp == 0x03:
        # Switch 3
        pass
    else:
        attribute_name = 'UnknowDp_0x%02x_Dt_0x%02x' %(dp,datatype)
        store_tuya_attribute( self, NwkId, attribute_name, data ) 
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Unknown attribut Nwkid: %s/%s decodeDP: %04x data: %s"
            %(NwkId, srcEp, dp, data), NwkId)


# Tuya TS0601 - Curtain
def tuya_curtain_response( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # dp 0x01 closing -- Data can be 00 , 01, 02 - Opening, Stopped, Closing
    # dp 0x02 Percent control - Percent control 
    # db 0x03 and data '00000000'  - Percent state when arrived at position (report)
    # dp 0x05 and data - direction state 
    # dp 0x07 and data 00, 01 - Opening, Closing
    # dp 0x69 and data '00000028'

    # 000104ef00010102 94fd 02 00000970020000 0202 0004 00000004

    self.log.logging( "Tuya", 'Debug', "tuya_curtain_response - Nwkid: %s/%s dp: %s data: %s" %(NwkId, srcEp, dp, data),NwkId )

    if dp == 0x01: # Open / Closing / Stopped
        self.log.logging( "Tuya", 'Debug', "tuya_curtain_response - Open/Close/Stopped action Nwkid: %s/%s  %s" %(NwkId, srcEp, data),NwkId )
        store_tuya_attribute( self, NwkId, 'Action', data ) 

    elif dp in ( 0x02 ):
        # Percent Control
        self.log.logging( "Tuya", 'Debug', "tuya_curtain_response - Percentage Control action Nwkid: %s/%s  %s" %(NwkId, srcEp, data),NwkId )
        store_tuya_attribute( self, NwkId, 'PercentControl', data ) 

    elif dp in ( 0x03, 0x07):
        # Curtain Percentage
        # We need to translate percentage into Analog value between 0 - 255
        level = ( ( int( data, 16)) * 255) // 100
        slevel = '%02x' %level
        self.log.logging( "Tuya", 'Debug', "tuya_curtain_response - Curtain Percentage Nwkid: %s/%s Level %s -> %s" %(NwkId, srcEp, data, level),NwkId )
        store_tuya_attribute( self, NwkId, 'PercentState', data ) 
        MajDomoDevice(self, Devices, NwkId, srcEp, '0008', slevel)

    elif dp == 0x05:
        self.log.logging( "Tuya", 'Debug', "tuya_curtain_response - Direction state Nwkid: %s/%s Action %s" %(NwkId, srcEp, data),NwkId )
        store_tuya_attribute( self, NwkId, 'DirectionState', data ) 

    elif dp in (0x67, 0x69):  
        level = ( (int( data, 16)) * 255) // 100
        slevel = '%02x' %level
        self.log.logging( "Tuya", 'Debug', "tuya_curtain_response - ?????? Nwkid: %s/%s data %s --> %s" %(NwkId, srcEp, data, level),NwkId )
        MajDomoDevice(self, Devices, NwkId, srcEp, '0008', slevel)
        store_tuya_attribute( self, NwkId, 'dp_%s' %dp, data ) 

    else:
        attribute_name = 'UnknowDp_0x%02x_Dt_0x%02x' %(dp,datatype)
        store_tuya_attribute( self, NwkId, attribute_name, data ) 

def tuya_curtain_openclose( self, NwkId , openclose):
    self.log.logging( "Tuya", 'Debug', "tuya_curtain_openclose - %s OpenClose: %s" %(NwkId, openclose),NwkId )
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, NwkId )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0101'
    data = openclose
    tuya_cmd( self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_curtain_stop( self, NwkId):
    pass

def tuya_curtain_lvl(self, NwkId, percent):
    self.log.logging( "Tuya", 'Debug', "tuya_curtain_lvl - %s percent: %s" %(NwkId, percent),NwkId )

    level = percent
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, NwkId )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0202'
    data = '%08x' %level
    tuya_cmd( self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


#### Tuya Smart Dimmer Switch
def tuya_dimmer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    #             cmd | status | transId | dp | DataType | fn | len | Data
    #Dim Down:     01     00        01     02      02      00    04   00000334
    #Dim Up:       01     00        01     02      02      00    04   0000005a
    #Switch Off:   01     00        01     01      01      00    01   00
    #Dim Up  :     01     00        01     01      01      00    01   01

    if dp == 0x01: # Switch On/Off
        MajDomoDevice(self, Devices, NwkId, srcEp, '0006', data)
        self.log.logging( "Tuya", 'Debug', "tuya_dimmer_response - Nwkid: %s/%s On/Off %s" %(NwkId, srcEp, data),NwkId )

    elif dp == 0x02: #Dim Down/Up
        # As MajDomoDevice expect a value between 0 and 255, and Tuya dimmer is on a scale from 0 - 1000.
        analogValue = int(data,16) / 10   # This give from 1 to 100
        level = int( (analogValue * 255 ) / 100 )

        self.log.logging( "Tuya", 'Debug', "tuya_dimmer_response - Nwkid: %s/%s Dim up/dow %s %s" %(NwkId, srcEp, int(data,16), level),NwkId )
        MajDomoDevice(self, Devices, NwkId, srcEp, '0008', '%02x' %level)
    else:
        attribute_name = 'UnknowDp_0x%02x_Dt_0x%02x' %(dp,datatype)
        store_tuya_attribute( self, NwkId, attribute_name, data ) 

def tuya_dimmer_onoff( self, NwkId, srcEp, OnOff ):

    self.log.logging( "Tuya", 'Debug', "tuya_dimmer_onoff - %s OnOff: %s" %(NwkId, OnOff),NwkId ) 
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, NwkId )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0101'
    data = OnOff
    tuya_cmd( self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_dimmer_dimmer( self, NwkId, srcEp, percent ):
    self.log.logging( "Tuya", 'Debug', "tuya_dimmer_dimmer - %s percent: %s" %(NwkId, percent),NwkId )

    level = percent * 10
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, NwkId )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '0202'
    data = '%08x' %level
    tuya_cmd( self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)

#### Tuya Blitzwolf Plug TS0121

def tuya_plug_led_indicator_mode( self, nwkid, mode ):
    # 0x0006 / 0x80001
    # Indicator LED off: 0x00
    # Indicator switch On/Off: 0x01
    # Indicate swicth location: 0x02

    write_attribute( self, nwkid, ZIGATE_EP, '01', '0006', '0000', '01', '8001', '30', mode, ackIsDisabled = True)


# Tuya Smart Cover Switch

def tuya_window_cover_calibration( self, nwkid, start_stop):

    # (0x0102) | Write Attributes (0x02) | 0xf001 | 8-Bit (0x30) | 0 (0x00) | Start Calibration
    # (0x0102) | Write Attributes (0x02) | 0xf001 | 8-Bit (0x30) | 1 (0x01) | End Calibration
    write_attribute( self, nwkid, ZIGATE_EP, '01', '0102', '0000', '00', 'f001', '30', start_stop, ackIsDisabled = True)

def tuya_window_cover_motor_reversal( self, nwkid, mode):

    # (0x0102) | Write Attributes (0x02) | 0xf002 | 8-Bit (0x30) | 0 (0x00) | Off
    # (0x0102) | Write Attributes (0x02) | 0xf002 | 8-Bit (0x30) | 1 (0x01) | On
    write_attribute( self, nwkid, ZIGATE_EP, '01', '0102', '0000', '00', 'f002', '30', mode, ackIsDisabled = True)


def tuya_window_cover_command( self, nwkid, mode ):

    # (0x0006) | Write Attributes (0x02) | 0x8001 | 8-Bit (0x30) | 0 (0x00) | Light Mode 1
    # (0x0006) | Write Attributes (0x02) | 0x8001 | 8-Bit (0x30) | 1 (0x01) | Light Mode 2
    # (0x0006) | Write Attributes (0x02) | 0x8001 | 8-Bit (0x30) | 2 (0x02) | Light Mode 3

    write_attribute( self, nwkid, ZIGATE_EP, '01', '0006', '0000', '00', '8001', '30', mode, ackIsDisabled = True)