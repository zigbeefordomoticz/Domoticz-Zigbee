#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: lumi.py
 
    Description: Lumi specifics handling

"""
import time
import struct

import Domoticz


from math import atan, sqrt, pi

from Modules.domoMaj import MajDomoDevice
from Modules.basicOutputs import ZigatePermitToJoin, leaveRequest, write_attribute
from Modules.zigateConsts import ZIGATE_EP
from Modules.logging import loggingLumi, loggingCluster
from Modules.tools import voltage2batteryP, checkAttribute, checkAndStoreAttributeValue

def xiaomi_leave( self, NWKID):
    
    if self.permitTojoin['Duration'] != 255:
        loggingLumi( self, 'Log', "------> switch zigate in pairing mode")
        ZigatePermitToJoin(self, ( 1 * 60 ))

    # sending a Leave Request to device, so the device will send a leave
    loggingLumi( self, 'Log', "------> Sending a leave to Xiaomi battery devive: %s" %(NWKID))
    leaveRequest( self, IEEE= self.ListOfDevices[NWKID]['IEEE'], Rejoin=True )

def setXiaomiVibrationSensitivity( self, key, sensitivity = 'medium'):
    
    VIBRATION_SENSIBILITY = { 'high':0x01, 'medium':0x0B, 'low':0x15}

    if sensitivity not in VIBRATION_SENSIBILITY:
        sensitivity = 'medium'

    manuf_id = "115F"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0000
    attribute = "%04x" %0xFF0D
    data_type = "20" # Int8
    data = "%02x" %VIBRATION_SENSIBILITY[sensitivity]
    write_attribute( self, key, "01", "01", cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

def enableOppleSwitch( self, nwkid ):

    if nwkid not in self.ListOfDevices:
        return

    if 'Model' not in self.ListOfDevices[nwkid]:
        return

    if ( self.ListOfDevices[nwkid]['Model'] in ('lumi.remote.b686opcn01-bulb','lumi.remote.b486opcn01-bulb','lumi.remote.b286opcn01-bulb' )
                                                and 'Lumi' not in self.ListOfDevices[nwkid] ):
        self.ListOfDevices[nwkid]['Lumi'] = {}
        self.ListOfDevices[nwkid]['Lumi']['AqaraOppleBulbMode'] = True
        return

    manuf_id = '115F'
    manuf_spec = "01"
    cluster_id = 'FCC0'
    Hattribute = '0009'
    data_type = '20'
    Hdata = '01'

    loggingLumi( self, 'Debug', "Write Attributes LUMI Magic Word Nwkid: %s" %nwkid, nwkid)
    write_attribute( self, nwkid, ZIGATE_EP, '01', cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def lumiReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    if srcNWKID not in self.ListOfDevices:
        return

    loggingLumi( self, 'Debug', "lumiReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), srcNWKID)

    if 'Model' not in self.ListOfDevices[srcNWKID]:
        return
    
    _ModelName = self.ListOfDevices[srcNWKID]['Model']

    if _ModelName in ( 'lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01'):
        # Recompute Data in order to match with a similar content with 0x8085/0x8095

        fcf = MsgPayload[0:2] # uint8
        sqn = MsgPayload[2:4] # uint8
        cmd = MsgPayload[4:6] # uint8
        data = MsgPayload[6:] # all the rest

        if ClusterID in ( '0006', '0008', '0300'):
            Data = '00000000000000'
            Data += data
            AqaraOppleDecoding( self, Devices, srcNWKID , srcEp, ClusterID, _ModelName, Data)

        elif ClusterID == '0001':
            # 18780a2000201e
            # fcf: 18
            # sqn: 78
            # cmd: 0a
            # DataType: 20
            # Attribute: 0020
            # Value: 1e

            loggingLumi( self, 'Log', "lumiReadRawAPS - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
                %(srcNWKID,srcEp , ClusterID, cmd, data ))

def AqaraOppleDecoding( self, Devices, nwkid, Ep, ClusterId, ModelName, payload):

    def actionFromCluster0008(StepMode ):
    
        action =''
        # Action
        if StepMode == '02': # 1 Click
            action = 'click_'
        elif StepMode == '01': # Long Click
            action = 'long_'
        elif StepMode == '03': # Release
            action = 'release'

        return action

    def buttonFromCluster0008( StepSize ):
    
        # Button
        if StepSize == '00': # Right
            action += 'right'            
        elif StepSize == '01': # Left
            action += 'left'

        return action

    def actionFromCluster0300(StepMode , EnhancedStepSize ):

        action =''
        if EnhancedStepSize == '4500': 
            if StepMode == '01':
                action = 'click_left'
            elif StepMode == '03':
                action = 'click_right'

        elif EnhancedStepSize == '0f00': 
            if StepMode == '01':
                action = 'long_left'
            elif StepMode == '03':
                action = 'long_right'
            elif StepMode == '00':
                action = 'release'

        return action

    if 'Model' not in self.ListOfDevices[nwkid]:
        return

    _ModelName = self.ListOfDevices[nwkid]['Model']

    if ClusterId == '0006': # Top row
        Command =  payload[14:16]    
        loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s,  ON/OFF, Cmd: %s" \
            %(nwkid, Ep, Command), nwkid)
        MajDomoDevice( self, Devices, nwkid, '01', "0006", Command)

    elif ClusterId == '0008': # Middle row
        StepMode = payload[14:16]
        StepSize = payload[16:18]
        TransitionTime = payload[18:22]
        unknown = payload[22:26]

        OPPLE_MAPPING_4_6_BUTTONS = {
            'click_left': '00',
            'click_right': '01',
            'long_left': '02',
            'long_right': '03',
            'release': '04'
        }

        action = actionFromCluster0008(StepMode ) + buttonFromCluster0008( StepSize )

        loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s, LvlControl, StepMode: %s, StepSize: %s, TransitionTime: %s, unknown: %s action: %s" \
            %(nwkid, Ep,StepMode,StepSize,TransitionTime,unknown, action), nwkid)
        if action in OPPLE_MAPPING_4_6_BUTTONS:
            MajDomoDevice( self, Devices, nwkid, '02', "0006", OPPLE_MAPPING_4_6_BUTTONS[ action ])

    elif ClusterId == '0300': # Botton row (need firmware)
        StepMode = payload[14:16]
        EnhancedStepSize = payload[16:20]
        TransitionTime = payload[20:24]
        ColorTempMinimumMired = payload[24:28]
        ColorTempMaximumMired = payload[28:32]
        unknown = payload[32:36]

        if _ModelName == 'lumi.remote.b686opcn01': # Ok
            OPPLE_MAPPING_4_6_BUTTONS = {
                'click_left': '00','click_right': '01',
                'long_left': '02','long_right': '03',
                'release': '04'
            }
        elif _ModelName in ( 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01') : # Not seen, just assumption
            OPPLE_MAPPING_4_6_BUTTONS = {
                'click_left': '02','click_right': '03',
            }   

        loggingLumi( self, 'Debug', "AqaraOppleDecoding - Nwkid: %s, Ep: %s, ColorControl, StepMode: %s, EnhancedStepSize: %s, TransitionTime: %s, ColorTempMinimumMired: %s, ColorTempMaximumMired: %s action: %s" \
            %(nwkid, Ep,StepMode,EnhancedStepSize,TransitionTime,ColorTempMinimumMired, ColorTempMaximumMired, action), nwkid)
        
        action = actionFromCluster0300(StepMode , EnhancedStepSize )       
        if action in OPPLE_MAPPING_4_6_BUTTONS:
            MajDomoDevice( self, Devices, nwkid, '03', "0006", OPPLE_MAPPING_4_6_BUTTONS[ action ])

    return
 
def AqaraOppleDecoding0012(self, Devices, nwkid, Ep, ClusterId, AttributeId, Value):

    # Ep : 01 (left)
    # Value: 0x0001 - click
    #        0x0002 - Double click
    #        0x0003 - Tripple click
    #        0x0000 - Long Click
    #        0x00ff - Release

    OPPLE_MAPPING = {
        '0001': '01',
        '0002': '02',
        '0003': '03',
        '0000': '04',
        '00ff': '05'
    }
    if Value in OPPLE_MAPPING:
        MajDomoDevice( self, Devices, nwkid, Ep, "0006", OPPLE_MAPPING[ Value ])  

    return

def retreive4Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: 
        return ''
    return chain[c:(c+4)]

def retreive8Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: 
        return ''
    return chain[c:(c+8)]

def readXiaomiCluster( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    def decodeFloat( data ):
        return (int(data[2:4]+data[0:2],16))

    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    
    # Taging: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/42#issuecomment-370152404
    # 0x0624 might be the LQI indicator and 0x0521 the RSSI dB

    sBatteryLvl =  retreive4Tag( "0121", MsgClusterData )
    sTemp2 =       retreive4Tag( "0328", MsgClusterData )         # Device Temperature
    stag04 =       retreive4Tag( '0424', MsgClusterData )
    sRSSI =        retreive4Tag( '0521', MsgClusterData )[0:2]    # RSSI
    sLQI =         retreive8Tag( '0620', MsgClusterData ) # LQI
    sLighLevel =   retreive4Tag( '0b21', MsgClusterData)

    sOnOff =       retreive4Tag( "6410", MsgClusterData )[0:2]
    sOnOff2 =      retreive4Tag( "6420", MsgClusterData )[0:2]    # OnOff for Aqara Bulb / Current position lift for lumi.curtain
    sTemp =        retreive4Tag( "6429", MsgClusterData )
    sOnOff3 =      retreive4Tag( "6510", MsgClusterData )         # On/off lumi.ctrl_ln2 EP 02
    sHumid =       retreive4Tag( "6521", MsgClusterData )
    sHumid2 =      retreive4Tag( "6529", MsgClusterData )
    sLevel =       retreive4Tag( "6520", MsgClusterData )[0:2]    # Dim level for Aqara Bulb
    sPress =       retreive8Tag( "662b", MsgClusterData )

    sConsumption = retreive8Tag( '9539', MsgClusterData )         # Cummulative Consumption
    sVoltage =     retreive8Tag( '9639', MsgClusterData )         # Voltage
    sCurrent =     retreive8Tag( '9739', MsgClusterData )         # Ampere
    sPower =       retreive8Tag( '9839', MsgClusterData )         # Power Watt

    if sConsumption != '':
        #Domoticz.Log("ReadCluster - %s/%s Saddr: %s/%s Consumption %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, sConsumption ))
        Domoticz.Log("ReadCluster - %s/%s Saddr: %s Consumption %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, float(decodeFloat( sConsumption )) ))
        if 'Consumption' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['Consumption'] = 0
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['Consumption'] = self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['Consumption'] + float(decodeFloat( sConsumption ))
        #checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0702', '0000' , float(decodeFloat( sConsumption )))

    if sVoltage != '':
        #Domoticz.Log("ReadCluster - %s/%s Saddr: %s/%s Voltage %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, sVoltage ))
        Domoticz.Log("ReadCluster - %s/%s Saddr: %s Voltage %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, float(decodeFloat( sVoltage )) ))
        checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0001', '0000' , float(decodeFloat( sVoltage )) )
        # Update Voltage ( cluster 0001 )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0001", float(decodeFloat( sVoltage )))

    if sCurrent != '':
        #Domoticz.Log("ReadCluster - %s/%s Saddr: %s/%s Courant %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, sCurrent ))
        Domoticz.Log("ReadCluster - %s/%s Saddr: %s Courant %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, float(decodeFloat( sCurrent ))))

    if sPower != '':
        #Domoticz.Log("ReadCluster - %s/%s Saddr: %s/%s Power %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, sPower ))
        Domoticz.Log("ReadCluster - %s/%s Saddr: %s Power %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, float(decodeFloat( sPower ))))
        #checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0702', '0400' , float(decodeFloat( sPower )) )
        # Update Power Widget
        #MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0702", float(decodeFloat( sPower ))) 

    if sLighLevel != '':
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s Saddr: %s Light Level: %s" 
            %(MsgClusterId, MsgAttrID, MsgSrcAddr,  int(sLighLevel,16)), MsgSrcAddr)

    if sRSSI != '':
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s Saddr: %s RSSI: %s" 
            %(MsgClusterId, MsgAttrID, MsgSrcAddr,  int(sRSSI,16)), MsgSrcAddr)

    if sLQI != '':
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s Saddr: %s LQI: %s" 
            %(MsgClusterId, MsgAttrID, MsgSrcAddr,  int(sLQI,16)), MsgSrcAddr)

    if sBatteryLvl != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '8e' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '84' and self.ListOfDevices[MsgSrcAddr]['PowerSource'] != 'Main':
        voltage = '%s%s' % (str(sBatteryLvl[2:4]),str(sBatteryLvl[0:2]))
        voltage = int(voltage, 16 )
        ValueBattery = voltage2batteryP( voltage, 3150, 2750)
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s Saddr: %s Battery: %s Voltage: %s MacCapa: %s PowerSource: %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, ValueBattery, voltage,  self.ListOfDevices[MsgSrcAddr]['MacCapa'], self.ListOfDevices[MsgSrcAddr]['PowerSource']), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Battery'] = ValueBattery
        self.ListOfDevices[MsgSrcAddr]['BatteryUpdateTime'] = int(time.time())
        checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0001', '0000' , voltage)

    if sTemp != '':
        Temp = struct.unpack('h',struct.pack('>H',int(sTemp,16)))[0]
        ValueTemp=round(Temp/100,1)
        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)
        checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0402', '0000' , ValueTemp)

    if sHumid != '':
        ValueHumid = struct.unpack('H',struct.pack('>H',int(sHumid,16)))[0]
        ValueHumid = round(ValueHumid/100,1)
        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity : " + str(ValueHumid) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0405",ValueHumid)
        checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0405', '0000' , ValueHumid)

    if sHumid2 != '':
        Humid2 = struct.unpack('h',struct.pack('>H',int(sHumid2,16)))[0]
        ValueHumid2=round(Humid2/100,1)
        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity2 : " + str(ValueHumid2) , MsgSrcAddr)

    if sPress != '':
        Press = '%s%s%s%s' % (str(sPress[6:8]),str(sPress[4:6]),str(sPress[2:4]),str(sPress[0:2])) 
        ValuePress=round((struct.unpack('i',struct.pack('i',int(Press,16)))[0])/100,1)
        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Atmospheric Pressure : " + str(ValuePress) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0403",ValuePress)
        checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0403', '0000' , sPress)

    if sOnOff != '':
        if self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.sensor_wleak.aq1':
            loggingCluster( self, 'Debug', " --- Do not process this sOnOff: %s  because it is a leak sensor : %s" %(sOnOff, MsgSrcAddr), MsgSrcAddr)
            # Wleak send status via 0x8401 and Zone change. Looks like we get some false positive here.
            return

        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s sOnOff: %s" %(MsgSrcAddr, sOnOff), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
        checkAndStoreAttributeValue( self,  MsgSrcAddr , MsgSrcEp, '0006', '0000' , sOnOff)


    if sOnOff2 != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] == '8e': # Aqara Bulb / Lumi Curtain - Position
        if self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.sensor_wleak.aq1':
            loggingCluster( self, 'Debug', " --- Do not process this sOnOff: %s  because it is a leak sensor : %s" %(sOnOff, MsgSrcAddr), MsgSrcAddr)
            # Wleak send status via 0x8401 and Zone change. Looks like we get some false positive here.
            return
        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s sOnOff2: %s" %(MsgSrcAddr, sOnOff2), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006',sOnOff2)
        checkAndStoreAttributeValue( self,  MsgSrcAddr , MsgSrcEp, '0006', '0000' , sOnOff)

    if sLevel != '':
        loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s sLevel: %s" %(MsgSrcAddr, sLevel), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0008',sLevel)
        checkAndStoreAttributeValue( self, MsgSrcAddr , MsgSrcEp, '0008', '0000' , sLevel)

def cube_decode(self, value, MsgSrcAddr):
    'https://github.com/sasu-drooz/Domoticz-Zigate/wiki/Aqara-Cube-decoding'
    value=int(value,16)
    if value == '' or value is None:
        return value

    if value == 0x0000:         
        loggingCluster( self, 'Debug', "cube action: " + 'Shake' , MsgSrcAddr)
        value='10'
    elif value == 0x0002:            
        loggingCluster( self, 'Debug', "cube action: " + 'Wakeup' , MsgSrcAddr)
        value = '20'
    elif value == 0x0003:
        loggingCluster( self, 'Debug', "cube action: " + 'Drop' , MsgSrcAddr)
        value = '30'
    elif value & 0x0040 != 0:    
        face = value ^ 0x0040
        face1 = face >> 3
        face2 = face ^ (face1 << 3)
        loggingCluster( self, 'Debug', "cube action: " + 'Flip90_{}{}'.format(face1, face2), MsgSrcAddr)
        value = '40'
    elif value & 0x0080 != 0:  
        face = value ^ 0x0080
        loggingCluster( self, 'Debug', "cube action: " + 'Flip180_{}'.format(face) , MsgSrcAddr)
        value = '50'
    elif value & 0x0100 != 0:  
        face = value ^ 0x0100
        loggingCluster( self, 'Debug', "cube action: " + 'Push/Move_{}'.format(face) , MsgSrcAddr)
        value = '60'
    elif value & 0x0200 != 0:  # double_tap
        face = value ^ 0x0200
        loggingCluster( self, 'Debug', "cube action: " + 'Double_tap_{}'.format(face) , MsgSrcAddr)
        value = '70'
    else:  
        loggingCluster( self, 'Debug', "cube action: Not expected value %s" %value , MsgSrcAddr)
    return value

def decode_vibr(value):         #Decoding XIAOMI Vibration sensor 
    if value == '' or value is None:
        return value
    if  value == "0001": 
        return '20' # Take/Vibrate/Shake
    if value == "0002": 
        return '10' # Tilt / we will most-likely receive 0x0503/0x0054 after
    if value == "0003": 
        return '30' #Drop
    return '00'

def decode_vibrAngle( rawData):

    value = int(rawData,16)
    x =  value & 0xffff
    y = (value >> 16) & 0xffff
    z = (value >> 32) & 0xfff

    x2 = x*x
    y2 = y*y
    z2 = z*z

    angleX= angleY = angleZ = 0
    if z2 + y2 != 0: 
        angleX = round( atan( x / sqrt(z2+y2)) * 180 / pi)
    if x2 + z2 != 0: 
        angleY = round( atan( y / sqrt(x2+z2)) * 180 / pi)
    if x2 + y2 != 0: 
        angleZ = round( atan( z / sqrt(x2+y2)) * 180 / pi)
    return (angleX, angleY, angleZ)
