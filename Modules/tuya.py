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

from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import sendZigateCmd, raw_APS_request
from Modules.tools import  checkAndStoreAttributeValue, is_ack_tobe_disabled, get_and_inc_SQN

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
    # https://medium.com/@dzegarra/zigbee2mqtt-how-to-add-support-for-a-new-tuya-based-device-part-2-5492707e882d
    # 
    #   0x00 Used by the ZC to send commands to the ZEDs.
    #   0x01 Used by the ZED to inform of changes in its state.
    #   0x02 Send by the ZED after receiving a 0x00 command. 
    #        Its data payload uses the same format as the 0x01 commands.
    # cmd, data

    # 0x0107, 0x01 Child lock On
    # 0x0107, 0x00 Child lock Off
    # 0x0114, 0x01 Valve check enable
    # 0x0112, 0x01 Window detection enabled
    # 0x016c, 0x00 Manual 0x01 Auto
    # 0x0165, 0x00 Off, 0x01 Manu
    # 0x0114, Valve state On/off 

    # 0x0202, Setpoint Change target temp after mode chg 
    # 0x0203, Temperature Notif temp after mode chg
    # 0x0215, Battery status 
    # 0x0255, Min Temp
    # 0x0267, Max Temp
    # 0x026d, Valve position
    # 0x022c, Temp Calibration

    # 0x0303, Temp Room temperature

    # 0x0404, 0x01 Change mode from Off -> Auto
    # 0x0404, 0x02 Change mode from Auto -> Manual
    # 0x0404, 0x00 Change mode from Manual -> Off
    # 0x0411, 0x00 Valve problem ??
    # 0x0413, 0x00 Valve problem ??
    # 0x046a, Mode 0x00 Auto, 0x01 Heat, 0x02 Off
    
    if NwkId not in self.ListOfDevices:
        return

    if ClusterID != 'ef00':
        return

    self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), NwkId)

    if 'Model' not in self.ListOfDevices[NwkId]:
        return
    
    _ModelName = self.ListOfDevices[NwkId]['Model']

    if len(MsgPayload) < 6:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - MsgPayload %s too short" %(MsgPayload))
        return

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8

    if cmd not in ('00', '01', '02'):
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Unknown command %s MsgPayload %s" %(cmd, MsgPayload))
        return

    status = MsgPayload[6:8]   #uint8
    transid = MsgPayload[8:10] # uint8
    dp = MsgPayload[10:14]     # uint16
    decode_dp = struct.unpack('>H',struct.pack('H',int(dp,16)))[0]
    fn = MsgPayload[14:16]
    len_data = MsgPayload[16:18]
    data = MsgPayload[18:]

    self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
        %(NwkId,srcEp , ClusterID, cmd, data ))

    self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s fcf: %s sqn: %s cmd: %s status: %s transid: %s dp: %s decodeDP: %04x fn: %s data: %s"
        %(NwkId, srcEp, fcf, sqn, cmd, status, transid, dp, decode_dp, fn, data))


    if decode_dp == 0x0101:
        # Switch 1
        pass

    elif decode_dp == 0x0102:
        # Switch 2
        pass
    elif decode_dp == 0x0103:
        # Switch 3
        pass

    elif decode_dp == 0x0114:
        # Valve state
        pass
    
    elif decode_dp == 0x0026d:
        # Valve position
        pass

    elif decode_dp == 0x046a:
        # Mode
        pass

    elif decode_dp == 0x0112:
        # Open Window
        MajDomoDevice(self, Devices, NwkId, srcEp, '0500', data )

    elif decode_dp == 0x0202:
        # Setpoint Change target temp
        # data is setpoint
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Setpoint: %s" %(NwkId,srcEp ,int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0201', ( int(data,16) / 10 ), Attribute_ = '0012' )
        checkAndStoreAttributeValue( self, NwkId , '01', '0201', '0012' , int(data,16) )


    elif decode_dp in (0x0203, 0x0303):
        # 0x0202 Thermostat setpoint
        # 0x0203 Thermostat temperature
        # Temperature notification
        # data is the temp
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Temperature: %s" %(NwkId,srcEp , int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0402', (int(data,16) / 10 ))
        checkAndStoreAttributeValue( self, NwkId , '01', '0402', '0000' , int(data,16)  )


    elif decode_dp == 0x0215:
        # Battery status
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Battery status %s" %(NwkId,srcEp ,int(data,16)))
        checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
        self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)


    elif decode_dp == 0x0404:
        # Change mode
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

    # TS0601 Siren, Teperature, Humidity, Alarm
    elif decode_dp == 0x0168:
        # Alarm
        if data == '00':
            MajDomoDevice(self, Devices, NwkId, srcEp, '0006', '01')
        else:
            MajDomoDevice(self, Devices, NwkId, srcEp, '0006', '02')

    elif decode_dp == 0x0171:
        # Alarm by Temperature
        if data == '01':
            MajDomoDevice(self, Devices, NwkId, srcEp, '0006', '03')

    elif decode_dp == 0x0172:
        # Alarm by humidity
        if data == '01':
            MajDomoDevice(self, Devices, NwkId, srcEp, '0006', '04')


    elif decode_dp == 0x026b:
        # Min Alarm Temperature
        pass

    elif decode_dp == 0x026c:
        # Max Alarm Temperature
        pass

    elif decode_dp == 0x026d:
        # AMin Alarm Humidity
        pass

    elif decode_dp == 0x026e:
        # Max Alarm Humidity 
        pass

    elif decode_dp == 0x0269:
        # Temperature
        MajDomoDevice(self, Devices, NwkId, srcEp, '0402', ( int(data,16) / 10))

    elif decode_dp == 0x026a:
        # Humidity
        MajDomoDevice(self, Devices, NwkId, srcEp, '0405', ( int(data,16) ) )        

    else:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Unknown attribut Nwkid: %s/%s fcf: %s sqn: %s cmd: %s status: %s transid: %s dp: %s decodeDP: %04x fn: %s data: %s"
            %(NwkId, srcEp, fcf, sqn, cmd, status, transid, dp, decode_dp, fn, data))

def tuya_setpoint( self, nwkid, setpoint_value):

    self.log.logging( "Tuya", 'Debug', "tuya_setpoint - %s setpoint: %s" %(nwkid, setpoint_value))

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


def tuya_siren_alarm( self, nwkid, onoff):
 
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm - %s onoff: %s" %(nwkid, onoff))

    tuya_siren_alarm_duration( self, nwkid, 1)
    tuya_siren_alarm_volume( self, nwkid, 2)
    tuya_siren_alarm_melody( self, nwkid, 5)


    # determine which Endpoint
    EPout = '01'

    sqn = get_and_inc_SQN( self, nwkid )

    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0168 ))[0]
    data = '%02x' %onoff
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_duration( self, nwkid, duration):
     
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_duration - %s duration: %s" %(nwkid, duration))

    # determine which Endpoint
    EPout = '01'

    sqn = get_and_inc_SQN( self, nwkid )

    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0474 ))[0]
    data = '%02x' %duration
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_volume( self, nwkid, volume):
     
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_volume - %s volume: %s" %(nwkid, volume))

    # determine which Endpoint
    EPout = '01'

    sqn = get_and_inc_SQN( self, nwkid )

    cluster_frame = '11'
    cmd = '00' # Command
    action = '0474'
    data = '%02x' %volume
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_melody( self, nwkid, melody):
     
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_melody - %s onoff: %s" %(nwkid, melody))

    # determine which Endpoint
    EPout = '01'

    sqn = get_and_inc_SQN( self, nwkid )

    cluster_frame = '11'
    cmd = '00' # Command
    action = '0466'
    data = '%02x' %melody
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
    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, nwkid))
    self.log.logging( "Tuya", 'Debug', "tuya_cmd - %s/%s cmd: %s payload: %s" %(nwkid, EPout , cmd, payload))