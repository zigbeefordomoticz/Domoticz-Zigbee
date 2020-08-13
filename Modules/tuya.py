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

from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import sendZigateCmd, raw_APS_request

from Modules.logging import loggingTuya
from Modules.domoMaj import MajDomoDevice

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

def tuyaReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    # Zigbee Tuya Command on Cluster 0xef00:
    # 
    #   0x00 Used by the ZC to send commands to the ZEDs.
    #   0x01 Used by the ZED to inform of changes in its state.
    #   0x02 Send by the ZED after receiving a 0x00 command. 
    #        Its data payload uses the same format as the 0x01 commands.
    # cmd, data
    # 0x0404, 0x02 Change mode from Auto -> Manual
    # 0x0202, Setpoint Change target temp after mode chg
    # 0x0203, Temperature Notif temp after mode chg

    # 0x0404, 0x00 Change mode from Manual -> Off
    # 0x0202, Setpoint Change target temp after mode chg 
    # 0x0203, Temperature Notif temp after mode chg

    # 0x0404, 0x01 Change mode from Off -> Auto
    # 0x0202, Setpoint Change target temp after mode chg
    # 0x0203, Temperature Notif temp after mode chg

    # 0x0107, 0x01 Child lock On
    # 0x0107, 0x00 Child lock Off
    # 0x0114, 0x01 Valve check enable
    # 0x0112, 0x01 Window detection enabled
    # 0x0411, 0x00 Valve problem ??
    # 0x0413, 0x00 Valve problem ??
    # 0x0303, Temp Room temperature
    # 0x0215, Battery status
    
    if srcNWKID not in self.ListOfDevices:
        return

    if ClusterID != 'ef00':
        return

    loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), srcNWKID)


    if 'Model' not in self.ListOfDevices[srcNWKID]:
        return
    
    _ModelName = self.ListOfDevices[srcNWKID]['Model']

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8
    status = MsgPayload[6:8] #uint8
    transid = MsgPayload[8:10] # uint8
    dp = MsgPayload[10:14] # uint16
    decode_dp = struct.unpack('>H',struct.pack('H',int(dp,16)))[0]
    fn = MsgPayload[14:16]
    len_data = MsgPayload[16:18]
    data = MsgPayload[18:]

    loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
        %(srcNWKID,srcEp , ClusterID, cmd, data ))

    if cmd == 0x0202:
        # Setpoint Change target temp
        # data is setpoint
        loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Setpoint: %s" %int(data,16))
        MajDomoDevice(self, Devices, srcNWKID, srcEp, '0201', int(data,16))


    elif cmd in (0x0203, 0x0303):
        # Temperature notification
        # data is the temp
        loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Temperature: %s" %int(data,16))
        MajDomoDevice(self, Devices, srcNWKID, srcEp, '0402', int(data,16))


    elif cmd == 0x0215:
        # Battery status
        loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Battery status %s" %int(data,16))


    elif cmd == 0x0404:
        # Change mode
        if data == '00':
            # Offline
            loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Offline")

        elif data == '01':
            # Auto
            loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Auto")

        elif data == '02':
            # Manual
            loggingTuya( self, 'Log', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Manual")


def tuya_setpoint( self, nwkid, setpoint_value):

    # determine which Endpoint
    EPout = '01'

    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cluster_frame = '11'
    cmd = '00' # Setpoint
    action = '0202'
    data = '%08x' %setpoint_value
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data ):

    if nwkid not in self.ListOfDevices:
        return
        
    if 'Tuya' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices['nwkid']['Tuya'] = {}

    if 'TuyaTransactionId' not in self.ListOfDevices['nwkid']:
        self.ListOfDevices['nwkid']['TuyaTransactionId'] = 0x00
    self.ListOfDevices['nwkid']['TuyaTransactionId'] += 1

    if self.ListOfDevices['nwkid']['TuyaTransactionId'] > 0xff:
        self.ListOfDevices['nwkid']['TuyaTransactionId'] = 0x00
    
    transid = '%02x' %self.ListOfDevices['nwkid']['TuyaTransactionId']
    payload = cluster_frame + sqn + cmd + '00' + transid + action + '00' + '%02x' %len(data) + data
    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingTuya( self, 'Debug', "tuya_cmd - %s/%s cmd: %s payload: %s" %(nwkid, EPout , cmd, payload))