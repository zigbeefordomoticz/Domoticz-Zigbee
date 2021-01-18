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
from Classes.LoggingManagement import LoggingManagement
from Modules.tools import updSQN, get_and_inc_SQN
from Modules.domoMaj import MajDomoDevice
from Modules.tuyaTools import tuya_cmd
from Modules.tuyaSiren import tuya_siren_response
from Modules.tuyaTRV import tuya_eTRV_response

# Tuya TRV Commands
# https://medium.com/@dzegarra/zigbee2mqtt-how-to-add-support-for-a-new-tuya-based-device-part-2-5492707e882d

# Cluster 0xef00
# Commands 
#   Direction: Coordinator -> Device 0x00 SetPoint 
#   Direction: Device -> Coordinator 0x01 
#   Direction: Device -> Coordinator 0x02 Setpoint command response

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
    if len(MsgPayload) < 6:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - MsgPayload %s too short" %(MsgPayload),NwkId )
        return

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8
    updSQN( self, NwkId, sqn)

    if cmd not in ('00', '01', '02', '03'):
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Unknown command %s MsgPayload %s/ Data: %s" %(cmd, MsgPayload, MsgPayload[6:]),NwkId )
        return

    status = MsgPayload[6:8]   #uint8
    transid = MsgPayload[8:10] # uint8
    dp = int(MsgPayload[10:12],16)
    datatype = MsgPayload[12:14]
    fn = MsgPayload[14:16]
    len_data = MsgPayload[16:18]
    data = MsgPayload[18:]

    _ModelName = self.ListOfDevices[NwkId]['Model']

    # [ZiGateForwarder_17] tuyaReadRawAPS - Nwkid: fc08/01 fcf: 09 sqn: 06 cmd: 02 status: 00 transid: 02 dp: 69 datatype: 02 fn: 00 data: 000000e3
    self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s fcf: %s sqn: %s cmd: %s status: %s transid: %s dp: %02x datatype: %s fn: %s data: %s"
        %(NwkId, srcEp, fcf, sqn, cmd, status, transid, dp, datatype, fn, data),NwkId )
    if _ModelName == 'TS0601-switch' and dp in ( 0x01, 0x02, 0x03):
        tuya_switch_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data)

    if _ModelName == 'TS0601-eTRV' and dp in (0x02, 0x03, 0x04, 0x07, 0x12, 0x14, 0x15, 0x6d, 0x6a):
        tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data)

    if _ModelName == 'TS0601-sirene' and dp in ( 0x65, 0x66 , 0x67, 0x68, 0x69,  0x6a , 0x6c, 0x6d,0x6e ,0x70, 0x71, 0x72, 0x73, 0x74):
        tuya_siren_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data)

    if _ModelName == 'TS0601-dimmer' and dp in ( 0x01, 0x02 ):
        tuya_dimmer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data)


def tuya_switch_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
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
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Unknown attribut Nwkid: %s/%s decodeDP: %04x data: %s"
            %(NwkId, srcEp, dp, data), NwkId)


#### Tuya Smart Dimmer Switch
def tuya_dimmer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, data):
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
        level = int((int(data,16)*255//1000))
        self.log.logging( "Tuya", 'Debug', "tuya_dimmer_response - Nwkid: %s/%s Dim up/dow %s %s" %(NwkId, srcEp, int(data,16), level),NwkId )
        MajDomoDevice(self, Devices, NwkId, srcEp, '0008', '%02x' %level)

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