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
from Modules.tools import  checkAndStoreAttributeValue

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

def tuyaReadRawAPS(self, Devices, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

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
    
    if NwkId not in self.ListOfDevices:
        return

    if ClusterID != 'ef00':
        return

    loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), NwkId)

    if 'Model' not in self.ListOfDevices[NwkId]:
        return
    
    _ModelName = self.ListOfDevices[NwkId]['Model']

    if len(MsgPayload) < 6:
        loggingTuya( self, 'Debug', "tuyaReadRawAPS - MsgPayload %s too short" %(MsgPayload))
        return

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8

    if cmd not in ('00', '01', '02'):
        loggingTuya( self, 'Log', "tuyaReadRawAPS - Unknown command %s MsgPayload %s" %(cmd, MsgPayload))
        return

    status = MsgPayload[6:8]   #uint8
    transid = MsgPayload[8:10] # uint8
    dp = MsgPayload[10:14]     # uint16
    decode_dp = struct.unpack('>H',struct.pack('H',int(dp,16)))[0]
    fn = MsgPayload[14:16]
    len_data = MsgPayload[16:18]
    data = MsgPayload[18:]

    loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
        %(NwkId,srcEp , ClusterID, cmd, data ))

    loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s fcf: %s sqn: %s cmd: %s status: %s transid: %s dp: %s decodeDP: %s fn: %s data: %s"
        %(NwkId, srcEp, fcf, sqn, cmd, status, transid, dp, decode_dp, fn, data))

    if decode_dp == 0x0202:
        # Setpoint Change target temp
        # data is setpoint
        loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Setpoint: %s" %(NwkId,srcEp ,int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', ( int(data,16) / 10 ), Attribute_ = '0012' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '0012' , int(data,16) )


    elif decode_dp in (0x0203, 0x0303):
        # Temperature notification
        # data is the temp
        loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Temperature: %s" %(NwkId,srcEp , int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0402', (int(data,16) / 10 ))
        checkAndStoreAttributeValue( self, NwkId , '01', '0402', '0000' , int(data,16)  )


    elif decode_dp == 0x0215:
        # Battery status
        loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Battery status %s" %(NwkId,srcEp ,int(data,16)))
        checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
        self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)


    elif decode_dp == 0x0404:
        # Change mode
        if data == '00':
            # Offline
            loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Offline" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 0, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'OffLine' )

        elif data == '01':
            # Auto
            loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Auto" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 1, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Auto' )

        elif data == '02':
            # Manual
            loggingTuya( self, 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode to Manual" %(NwkId,srcEp ))
            MajDomoDevice(self, Devices, NwkId, srcEp, '0201', 2, Attribute_ = '001c' )
            checkAndStoreAttributeValue( self, NwkId , '01', '0201', '001c' , 'Manual' )


def tuya_setpoint( self, nwkid, setpoint_value):

    loggingTuya( self, 'Debug', "tuya_setpoint - %s setpoint: %s" %(nwkid, setpoint_value))

    # In Domoticz Setpoint is in ° , In Modules/command.py we multiplied by 100 (as this is the Zigbee standard).
    # Looks like in the Tuya 0xef00 cluster it is only expressed in 10th of degree
    setpoint_value = setpoint_value // 10

    # determine which Endpoint
    EPout = '01'

    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cluster_frame = '11'
    cmd = '00' # Command
    action = '0202'
    data = '%08x' %setpoint_value
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    
def tuya_trv_mode( self, nwkid, mode):

    loggingTuya( self, 'Debug', "tuya_setpoint - %s tuya_trv_mode: %s" %(nwkid, mode))

    # In Domoticz Setpoint is in ° , In Modules/command.py we multiplied by 100 (as this is the Zigbee standard).
    # Looks like in the Tuya 0xef00 cluster it is only expressed in 10th of degree
 
    # determine which Endpoint
    EPout = '01'

    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cluster_frame = '11'
    cmd = '00' # Command
    action = '0404' # Mode
    data = '%02x' %( mode // 10 )
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)   

def tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data ):

    if nwkid not in self.ListOfDevices:
        return
        
    if 'Tuya' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Tuya'] = {}

    if 'TuyaTransactionId' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['TuyaTransactionId'] = 0x00
    self.ListOfDevices[nwkid]['TuyaTransactionId'] += 1

    if self.ListOfDevices[nwkid]['TuyaTransactionId'] > 0xff:
        self.ListOfDevices[nwkid]['TuyaTransactionId'] = 0x00
    
    transid = '%02x' %self.ListOfDevices[nwkid]['TuyaTransactionId']
    payload = cluster_frame + sqn + cmd + '00' + transid + action + '00' + '%02x' %len(data) + data
    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingTuya( self, 'Debug', "tuya_cmd - %s/%s cmd: %s payload: %s" %(nwkid, EPout , cmd, payload))