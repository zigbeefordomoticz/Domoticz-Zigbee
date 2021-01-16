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
from Modules.basicOutputs import sendZigateCmd, raw_APS_request, write_attribute
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

def tuya_sirene_registration(self, nwkid):
    
    self.log.logging( "Tuya", 'Debug', "tuya_sirene_registration - Nwkid: %s" %nwkid)
    
    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = '01'
    write_attribute( self, nwkid, ZIGATE_EP, EPout, '0000', '0000', '00', 'ffde', '20', '13', ackIsDisabled = False)

    # (2) Cmd 0xf0 send on Cluster 0x0000 - no data
    payload = '11' + get_and_inc_SQN( self, nwkid ) + 'f0'
    raw_APS_request( self, nwkid, EPout, '0000', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, nwkid))

    # (3) Cmd 0x03 on Cluster 0xef00  (Cluster Specific)
    payload = '11' + get_and_inc_SQN( self, nwkid ) + '03'
    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, nwkid))

    # Set the Siren to °C
    tuya_siren_temp_unit( self, nwkid, unit='C' )


def tuyaReadRawAPS(self, Devices, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    # Zigbee Tuya Command on Cluster 0xef00:
    # https://medium.com/@dzegarra/zigbee2mqtt-how-to-add-support-for-a-new-tuya-based-device-part-2-5492707e882d
    # 
    # Cluster 0xef00 (Command in Cluster Specific)
    #   0x00 Used by the ZC to send commands to the ZEDs.
    #   0x01 Used by the ZED to inform of changes in its state.
    #   0x02 Send by the ZED after receiving a 0x00 command. 
    #        Its data payload uses the same format as the 0x01 commands.
    # Seen with Siren
    #   0x03 send by the ZC without any data
    #   0x10 send by ZC , with 2 bytes data 0x0018   
    #   0x0b send by ZED , with 3 bytes data 0x000140   
    #   0x24 send by ZED, with 2 bytes data 0x0027    => Response from ZC 0x24 with 10 bytes ( where the 2 first bytes are from the input command)



    if NwkId not in self.ListOfDevices:
        return

    if ClusterID != 'ef00':
        return

    #self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
    #        %(NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), NwkId)

    if 'Model' not in self.ListOfDevices[NwkId]:
        return

    _ModelName = self.ListOfDevices[NwkId]['Model']

    if len(MsgPayload) < 6:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - MsgPayload %s too short" %(MsgPayload))
        return

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8

    if cmd not in ('00', '01', '02', '03'):
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Unknown command %s MsgPayload %s/ Data: %s" %(cmd, MsgPayload, MsgPayload[6:]))
        return

    status = MsgPayload[6:8]   #uint8
    transid = MsgPayload[8:10] # uint8
    dp = MsgPayload[10:14]     # uint16
    decode_dp = struct.unpack('>H',struct.pack('H',int(dp,16)))[0]
    fn = MsgPayload[14:16]
    len_data = MsgPayload[16:18]
    data = MsgPayload[18:]

    #self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
    #    %(NwkId,srcEp , ClusterID, cmd, data ))

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

    ######################### eTRV
    elif decode_dp == 0x0107:
        # Child Lock unlocked/locked
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Child Lock/Unlock: %s" %(NwkId,srcEp ,data))

    elif decode_dp == 0x0114:
        # Valve state
        # Use Dimer to report On/Off
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Valve state: %s" %(NwkId,srcEp ,data))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0006', data , Attribute_ = '0014')

    elif decode_dp == 0x026d and _ModelName == 'TS0601-eTRV':
        # Valve position in %
        # Use Dimer to report %
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Valve position: %s" %(NwkId,srcEp ,int(data,16)))
        MajDomoDevice(self, Devices, NwkId, srcEp, '0008', int(data,16) , Attribute_ = '026d')

    elif decode_dp == 0x046a:
        # Mode
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Mode: %s" %(NwkId,srcEp ,data))

    elif decode_dp == 0x0112:
        # Open Window
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Nwkid: %s/%s Window Open: %s" %(NwkId,srcEp ,data))
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



    ################### TS0601 Siren, Teperature, Humidity, Alarm
    # ZED -> ZC 0x11 0x000740

    elif decode_dp == 0x0168: #Alarm set 
        # Alarm
        if data == '00':
            MajDomoDevice(self, Devices, NwkId, srcEp, '0006', '00', Attribute_= '0168')
        else:
            MajDomoDevice(self, Devices, NwkId, srcEp, '0006', '01', Attribute_= '0168')

    elif decode_dp == 0x0170:
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Temperature Unit: %s " %( int(data,16)), NwkId)

    elif decode_dp == 0x0171: # Alarm by Temperature
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Alarm by Temperature: %s" %( int(data,16)), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, '0006', data, Attribute_= '0171')

    elif decode_dp == 0x0172: # Alarm by humidity
        self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Alarm by Humidity: %s" %( int(data,16)), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, '0006', data, Attribute_= '0172')

    elif decode_dp == 0x0267:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Current Siren Duration %s" %int(data,16), NwkId)

    elif decode_dp == 0x0269: # Temperature
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Temperature %s" %int(data,16), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, '0402', ( int(data,16) / 10))

    elif decode_dp == 0x026a: # Humidity
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Humidity %s" %int(data,16), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, '0405', ( int(data,16) ) )
             
    elif decode_dp == 0x026b: # Min Alarm Temperature
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Current Min Alarm Temp %s" %int(data,16), NwkId)

    elif decode_dp == 0x026c: # Max Alarm Temperature
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Current Max Alarm Temp %s" %int(data,16), NwkId)

    elif decode_dp == 0x026d and _ModelName == 'TS0601-sirene' : # AMin Alarm Humidity
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Current Min Alarm Humi %s" %int(data,16), NwkId)

    elif decode_dp == 0x026e: # Max Alarm Humidity 
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Current Max Alarm Humi %s" %int(data,16), NwkId)

    elif decode_dp == 0x0465: # Power Mode ( 0x00 Battery, 0x04 USB )
        # 00 02 6504 0001 00 -- Battery mode
        # 00 02 6504 0001 04 -- Main power mode
        if data == '04':
           self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Nwkid: %s/%s switch to USB power" %( NwkId, srcEp), NwkId)
        elif data == '00':
            self.log.logging( "Tuya", 'Log', "tuyaReadRawAPS - Nwkid: %s/%s switch to Battery power" %( NwkId, srcEp), NwkId)

    elif decode_dp == 0x466:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Alarm Melody 0x0473 %s" %int(data,16), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, '0006', (int(data,16)))

    elif decode_dp == 0x0473: # ??
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Unknown 0x0473 %s" %int(data,16), NwkId)

    elif decode_dp == 0x0474: # Current Siren Volume
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Current Siren Volume %s" %int(data,16), NwkId)


    else:
        self.log.logging( "Tuya", 'Debug', "tuyaReadRawAPS - Unknown attribut Nwkid: %s/%s fcf: %s sqn: %s cmd: %s status: %s transid: %s dp: %s decodeDP: %04x fn: %s data: %s"
            %(NwkId, srcEp, fcf, sqn, cmd, status, transid, dp, decode_dp, fn, data), NwkId)

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

def tuya_siren_alarm( self, nwkid, onoff, alarm_num=1):

    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm - %s onoff: %s" %(nwkid, onoff))
    duration = 5
    volume = 2
    if onoff == 0x01:
        alarm_attr = get_alarm_attrbutes( self, nwkid, alarm_num)
        duration = alarm_attr['Duration']
        volume =   alarm_attr['Volume'] 
        melody =   alarm_attr['Melody'] 

        tuya_siren_alarm_duration( self, nwkid, duration)
        tuya_siren_alarm_volume( self, nwkid, volume)        
        tuya_siren_alarm_melody( self, nwkid, melody)

    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0168 ))[0]
    data = '%02x' %onoff
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def get_alarm_attrbutes( self, nwkid, alarm_num):

    default_value = {
        "Alarm1": { "Duration": 5, "Volume": 2, "Melody": 1},
        "Alarm2": { "Duration": 5, "Volume": 2, "Melody": 2},
        "Alarm3": { "Duration": 5, "Volume": 2, "Melody": 3},
        "Alarm4": { "Duration": 5, "Volume": 2, "Melody": 4},
        "Alarm5": { "Duration": 5, "Volume": 2, "Melody": 5},
    }

    alarm = 'Alarm%s' %alarm_num
    if alarm not in default_value:
        Domoticz.Error("get_alarm_attrbutes - something wrong %s %s" %(alarm_num,alarm ))
        return None
    
    default_alarm = default_value[ alarm ]
    if 'Param' not in self.ListOfDevices[ nwkid ]:
        self.log.logging( "Tuya", 'Error', "get_alarm_attrbutes - default value to be used - no Param in DeviceList")
        return default_alarm

    if alarm not in self.ListOfDevices[ nwkid ]['Param']:
        self.log.logging( "Tuya", 'Error', "get_alarm_attrbutes - default value to be used - no %s in Param %s" %(
            alarm, self.ListOfDevices[ nwkid ]['Param']))
        return default_alarm

    alarm_attributes = self.ListOfDevices[ nwkid ]['Param'][alarm]
    if "Duration" not in alarm_attributes or "Volume" not in alarm_attributes or "Melody" not in alarm_attributes:
        self.log.logging( "Tuya", 'Error', "get_alarm_attrbutes - default value to be used - Missing Duration, Volume or Melogy for alarm %s in Param %s" %(
            alarm, self.ListOfDevices[ nwkid ]['Param']))
        return default_alarm

    if alarm_attributes[ "Volume" ] > 2:
        self.log.logging( "Tuya", 'Error', "get_alarm_attrbutes - default value to be used - Volume can only be 0, 1 or 2 instead of %s" %(
            alarm, alarm_attributes[ "Volume" ]))
        return default_alarm
    if alarm_attributes[ "Melody" ] not in ( 1,2,3,4,5):
        self.log.logging( "Tuya", 'Error', "get_alarm_attrbutes - default value to be used - Melody can only be 1,2,3,4,5 instead of %s" %(
            alarm, self.ListOfDevices[ nwkid ]['Param']))
        return default_alarm

    return alarm_attributes

def tuya_siren_temp_alarm( self, nwkid, onoff ):
    self.log.logging( "Tuya", 'Debug', "tuya_siren_temp_alarm - %s onoff: %s" %(nwkid, onoff))
    min_temp = 18
    max_temp = 30

    if onoff:
        if ( 'Param' in self.ListOfDevices[ nwkid ] 
                and 'TemperatureMinAlarm' in self.ListOfDevices[ nwkid ]['Param'] 
                and isinstance( self.ListOfDevices[ nwkid ]['Param']['TemperatureMinAlarm'], int) ):
            min_temp = self.ListOfDevices[ nwkid ]['Param']['TemperatureMinAlarm']

        if ( 'Param' in self.ListOfDevices[ nwkid ] 
                and 'TemperatureMaxAlarm' in self.ListOfDevices[ nwkid ]['Param'] 
                and isinstance( self.ListOfDevices[ nwkid ]['Param']['TemperatureMaxAlarm'], int) ):
            max_temp =   self.ListOfDevices[ nwkid ]['Param']['TemperatureMaxAlarm']    
        tuya_siren_alarm_temp( self, nwkid, min_temp, max_temp)

    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0171 ))[0]
    data = '%02x' %onoff
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_humi_alarm( self, nwkid, onoff ):   
    self.log.logging( "Tuya", 'Debug', "tuya_siren_humi_alarm - %s onoff: %s" %(nwkid, onoff))
    min_humi = 25
    max_humi = 75

    if onoff:
        if ( 'Param' in self.ListOfDevices[ nwkid ] 
                and 'HumidityMinAlarm' in self.ListOfDevices[ nwkid ]['Param'] 
                and isinstance( self.ListOfDevices[ nwkid ]['Param']['HumidityMinAlarm'], int) ):
            min_humi = self.ListOfDevices[ nwkid ]['Param']['HumidityMinAlarm']
    
        if ( 'Param' in self.ListOfDevices[ nwkid ] 
                and 'HumidityMaxAlarm' in self.ListOfDevices[ nwkid ]['Param'] 
                and isinstance( self.ListOfDevices[ nwkid ]['Param']['HumidityMaxAlarm'], int) ):
            max_humi =   self.ListOfDevices[ nwkid ]['Param']['HumidityMaxAlarm']    
        tuya_siren_alarm_humidity( self, nwkid, min_humi, max_humi)        

    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0172 ))[0]
    data = '%02x' %onoff
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_duration( self, nwkid, duration):
    # duration in second
    #     0s - 00 43 6702 0004 00000000
    #    10s - 00 44 6702 0004 0000000a
    #   250s - 00 45 6702 0004 000000fa
    #   300s - 00 46 6702 0004 0000012c
     
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_duration - %s duration: %s" %(nwkid, duration))
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0267 ))[0]
    data = '%08x' %duration
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_volume( self, nwkid, volume):
    # 0-Max, 1-Medium, 2-Low
    # 0- 95db  00 3e 7404 0001 00
    # 1- 80db  00 3d 7404 0001 01
    # 2- 70db  00 3f 7404 0001 02
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_volume - %s volume: %s" %(nwkid, volume))
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0474 ))[0]
    data = '%02x' %volume
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_melody( self, nwkid, melody):
    # 18-Melodies 1 -> 18 ==> 0x00 -- 0x11
    # 1- 00 40 6604 0001 00
    # 2- 00 41 6604 0001 01

    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_melody - %s onoff: %s" %(nwkid, melody))
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0466 ))[0]
    data = '%02x' %melody
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_temp_unit( self, nwkid, unit='C' ):
    # From °c to °F: 00 39 7001 0001 00
    #                00 3b 7001 0001 00

    # From °F to °c: 00 3a 7001 0001 01
    #                00 3c 7001 0001 01
    unit = 0x01 if unit != 'F' else 0x00
    self.log.logging( "Tuya", 'Debug', "tuya_siren_temp_unit - %s Unit Temp: %s" %(nwkid, unit))
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action = '%04x' %struct.unpack('H',struct.pack('>H', 0x0170 ))[0]
    data = '%02x' %unit

    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren_alarm_humidity( self, nwkid, min_humi_alarm, max_humi_alarm):
    #                  Max humi            Min humi
    # 00 34 6e02 00 04 00000058 6d02 00 04 0000000c
    # 00 36 7201 00 01 01
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_min_humidity - %s Min Humi: %s Max Humid: %s" %(nwkid, min_humi_alarm, max_humi_alarm))
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action1 = '%04x' %struct.unpack('H',struct.pack('>H', 0x026E ))[0]
    data1 = '%08x' %max_humi_alarm

    action2 = '%04x' %struct.unpack('H',struct.pack('>H', 0x026D ))[0]
    data2 = '%08x' %min_humi_alarm
    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action1, data1, action2, data2)

def tuya_siren_alarm_temp( self, nwkid, min_temp_alarm, max_temp):
    # Enable Temp Alarm 18° <---> 33°c
    #                  Max temp                Min temp
    # 00 23 6c02 00 04 00000021     6b02 00 04 00000012
    # 00 24 7101 00 01 01
    #
    self.log.logging( "Tuya", 'Debug', "tuya_siren_alarm_min_temp - %s Min Temp: %s Max Temp: %s" %(nwkid, min_temp_alarm, max_temp))
    # determine which Endpoint
    EPout = '01'
    sqn = get_and_inc_SQN( self, nwkid )
    cluster_frame = '11'
    cmd = '00' # Command
    action1 = '%04x' %struct.unpack('H',struct.pack('>H', 0x026C ))[0]
    data1 = '%08x' %max_temp

    action2 = '%04x' %struct.unpack('H',struct.pack('>H', 0x026B ))[0]
    data2 = '%08x' %min_temp_alarm

    tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action1, data1, action2, data2)
    
def tuya_cmd( self, nwkid, EPout, cluster_frame, sqn, cmd, action, data , action2=None, data2 = None):

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
    len_data = (len(data)) // 2
    payload = cluster_frame + sqn + cmd + '00' + transid + action + '00' + '%02x' %len_data + data
    if action2 and data2:
        len_data2 = (len(data2)) // 2
        payload += action2 + '00' + '%02x' %len_data2 + data2

    raw_APS_request( self, nwkid, EPout, 'ef00', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, nwkid))
    self.log.logging( "Tuya", 'Debug', "tuya_cmd - %s/%s cmd: %s payload: %s" %(nwkid, EPout , cmd, payload))
