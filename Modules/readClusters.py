#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_readClusters.py

    Description: manage all incoming Clusters messages

"""

import Domoticz
import binascii
import time
import struct
import json
import queue
import string

from Modules.domoticz import MajDomoDevice
from Modules.tools import DeviceExist, getEPforClusterType
from Modules.output import ReadAttributeRequest_Ack

def retreive4Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+4)]

def retreive8Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+8)]

def decodeAttribute(AttType, Attribute, handleErrors=False):

    if len(Attribute) == 0:
        return
    Domoticz.Debug("decodeAttribute( %s, %s) " %(AttType, Attribute) )

    if int(AttType,16) == 0x10:    # Boolean
        return Attribute
    elif int(AttType,16) == 0x16:  # 8Bit bitmap
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x20:  # Uint8 / unsigned char
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x21:   # 16BitUint
        return str(struct.unpack('H',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x22:   # ZigBee_24BitUint
            return str(struct.unpack('I',struct.pack('I',int("0"+Attribute,16)))[0])
    elif int(AttType,16) == 0x23:   # 32BitUint
            Domoticz.Debug("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x25:   # ZigBee_48BitUint
            return str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])
    elif int(AttType,16)  == 0x28: # int8
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x29:   # 16Bitint   -> tested on Measurement clusters
        return str(struct.unpack('h',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x2a:   # ZigBee_24BitInt
        Domoticz.Debug("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])))
        return str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])
    elif int(AttType,16) == 0x2b:   # 32Bitint
            Domoticz.Debug("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x2d:   # ZigBee_48Bitint
            Domoticz.Debug("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])))
            return str(struct.unpack('q',struct.pack('Q',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x30:  # 8BitEnum
        return int(Attribute,16 )
    elif int(AttType,16)  == 0x31: # 16BitEnum 
        return str(struct.unpack('h',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x39:  # Xiaomi Float
        return str(struct.unpack('f',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x42:  # CharacterString
        try:
            decode = binascii.unhexlify(Attribute).decode('utf-8')
        except:
            if handleErrors: # If there is an error we force the result to '' This is used for 0x0000/0x0005
                Domoticz.Log("decodeAttribute - seems errors, so returning empty")
                decode = ''
            else:
                decode = binascii.unhexlify(Attribute).decode('utf-8', errors = 'ignore')
                Domoticz.Debug("decodeAttribute - seems errors, returning with errors ignore")
        return decode
    else:
        Domoticz.Debug("decodeAttribut(%s, %s) unknown, returning %s unchanged" %(AttType, Attribute, Attribute) )
        return Attribute

def ReadCluster(self, Devices, MsgData):

    MsgLen=len(MsgData)
    Domoticz.Debug("ReadCluster - MsgData lenght is: " + str(MsgLen) + " out of 24+")

    if MsgLen < 24:
        Domoticz.Error("ReadCluster - MsgData lenght is too short: " + str(MsgLen) + " out of 24+")
        Domoticz.Error("ReadCluster - MsgData: '" +str(MsgData) + "'")
        return


    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    MsgAttrID=MsgData[12:16]
    MsgAttrStatus=MsgData[16:18]
    MsgAttType=MsgData[18:20]
    MsgAttSize=MsgData[20:24]
    MsgClusterData=MsgData[24:len(MsgData)]
    tmpEp=""
    tmpClusterid=""

    self.statistics._clusterOK += 1

    if 'ReadAttributes' in self.ListOfDevices[MsgSrcAddr]:
        if MsgSrcEp in self.ListOfDevices[MsgSrcAddr]['ReadAttributes']['Ep']:
            if MsgClusterId in self.ListOfDevices[MsgSrcAddr]['ReadAttributes']['Ep'][MsgSrcEp]:
                self.ListOfDevices[MsgSrcAddr]['ReadAttributes']['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgAttrStatus

    if MsgAttrStatus != "00" and MsgClusterId != '0500':
        Domoticz.Debug("ReadCluster - Status %s for addr: %s/%s on cluster/attribute %s/%s" %(MsgAttrStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID) )
        self.statistics._clusterKO += 1
        return

    if DeviceExist(self, Devices, MsgSrcAddr) == False:
        #Pas sur de moi, mais je vois pas pkoi continuer, pas sur que de mettre a jour un device bancale soit utile
        Domoticz.Error("ReadCluster - KeyError: MsgData = " + MsgData)
        return
    else:
        # Can we receive a Custer while the Device is not yet in the ListOfDevices ??????
        # This looks not possible to me !!!!!!!
        # This could be in the case of Xiaomi sending Cluster 0x0000 before anything is done on the plugin.
        # I would consider this doesn't make sense, and we should simply return a warning, that we receive a message from an unknown device !
        try: 
            tmpEp=self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]
            try:
                tmpClusterid=self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]
            except: 
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}
        except:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]={}
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}

    if self.pluginconf.debugReadCluster == 1:
        Domoticz.Debug("ReadCluster - %s NwkId: %s Ep: %s AttrId: %s AttyType: %s Attsize: %s Status: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgAttrStatus, MsgClusterData))

        
    if   MsgClusterId=="0000": Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0001": Cluster0001( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0005": Cluster0005( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0006": Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0008": Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0012": Cluster0012( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="000c": Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0101": Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0201": Cluster0201( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0300": Cluster0300( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0400": Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0402": Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0403": Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0405": Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0406": Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0500": Cluster0500( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0702":  Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0b04": Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="fc00": Clusterfc00( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    else:
        Domoticz.Error("ReadCluster - Error/unknow Cluster Message: " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
        Domoticz.Error("                                 MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
        Domoticz.Error("                                 MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )

def Cluster0001( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    oldValue = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]).split(";")
    if len(oldValue) != 4:
        oldValue = '0;0;0;0'.split(';')

    value = decodeAttribute( MsgAttType, MsgClusterData)
    if MsgAttrID == "0000": # Voltage
        value = round(int(value)/10, 1)
        mainVolt = value
        newValue = '%s;%s;%s;%s' %(mainVolt, oldValue[1], oldValue[2], oldValue[3])
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
        Domoticz.Debug("readCluster 0001 - %s Voltage: %s V " %(MsgSrcAddr, value) )

    elif MsgAttrID == "0010": # Voltage
        battVolt = value
        newValue = '%s;%s;%s;%s' %(oldValue[0], battVolt, oldValue[2], oldValue[3])
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        Domoticz.Debug("readCluster 0001 - %s Battery Voltage: %s " %(MsgSrcAddr, value) )

    elif MsgAttrID == "0020": # Battery Voltage
        battRemainVolt = value
        newValue = '%s;%s;%s;%s' %(oldValue[0], oldValue[1], battRemainVolt, oldValue[3])
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        Domoticz.Debug("readCluster 0001 - %s Battery: %s V" %(MsgSrcAddr, value) )

    elif MsgAttrID == "0021": # Battery %
        battRemainPer = value
        newValue = '%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], battRemainPer)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        self.ListOfDevices[MsgSrcAddr]['Battery'] = value
        Domoticz.Debug("readCluster 0001 - %s Battery: %s " %(MsgSrcAddr, value) )

    elif MsgAttrID == "0031": # Battery Size
        # 0x03 stand for AA
        Domoticz.Log("readCluster 0001 - %s Battery size: %s " %(MsgSrcAddr, value) )

    elif MsgAttrID == "0033": # Battery Quantity
        Domoticz.Log("readCluster 0001 - %s Battery Quantity: %s " %(MsgSrcAddr, value) )

    else:
        Domoticz.Log("readCluster 0001 - unexepected Attribute: %s %s %s %s" %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

def Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Smart Energy Metering
    if int(MsgAttSize,16) == 0:
        Domoticz.Debug("Cluster0702 - empty message ")
        return


    value = int(decodeAttribute( MsgAttType, MsgClusterData ))
    Domoticz.Debug("Cluster0702 - MsgAttrID: %s MsgAttType: %s DataLen: %s Data: %s decodedValue: %s" %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value))

    if MsgAttrID == "0000": 
        Domoticz.Debug("Cluster0702 - 0x0000 CURRENT_SUMMATION_DELIVERED %s " %(value))
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        #MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

    elif MsgAttrID == "0301":   # Multiplier
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        Domoticz.Debug("Cluster0702 - Multiplier: %s" %(value))

    elif MsgAttrID == "0302":   # Divisor
        Domoticz.Debug("Cluster0702 - Divisor: %s" %(value))

    elif MsgAttrID == "0200": 
        Domoticz.Debug("Cluster0702 - Status: %s" %(value))


    elif MsgAttrID == "0400": 
        Domoticz.Debug("Cluster0702 - 0x0400 Instant demand %s" %(value))
        value = round(value/10, 3)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = str(value)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

    else:
        Domoticz.Log("ReadCluster - 0x0702 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )
    return


def Cluster0300( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    # Color Temperature
    if 'ColorInfos' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['ColorInfos'] ={}

    value = decodeAttribute( MsgAttType, MsgClusterData)
    if MsgAttrID == "0000":     # CurrentHue
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Hue'] = value
        Domoticz.Debug("ReadCluster0300 - CurrentHue: %s" %value)
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Hue']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001":   # CurrentSaturation
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Saturation'] = value
        Domoticz.Debug("ReadCluster0300 - CurrentSaturation: %s" %value)
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Saturation']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0003":     # CurrentX
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['X'] = value
        Domoticz.Debug("ReadCluster0300 - CurrentX: %s" %value)
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-X']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004":   # CurrentY
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Y'] = value
        Domoticz.Debug("ReadCluster0300 - CurrentY: %s" %value)
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Y']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0007":   # ColorTemperatureMireds
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorTemperatureMireds'] = value
        Domoticz.Debug("ReadCluster0300 - ColorTemperatureMireds: %s" %value)
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorTemperatureMireds']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0008":   # Color Mode 
                                # 0x00: CurrentHue and CurrentSaturation
                                # 0x01: CurrentX and CurrentY
                                # 0x02: ColorTemperatureMireds
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = value
        Domoticz.Debug("ReadCluster0300 - Color Mode: %s" %value)
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorMode']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "f000":
        # 070000df
        # 00800900
        #self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = value
        Domoticz.Log("ReadCluster0300 - Color Mode: %s" %value)
        #if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
        #    self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorMode']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    else:
        Domoticz.Log("ReadCluster - ClusterID=0300 - NOT IMPLEMENTED YET - MsgAttrID = " +\
                str(MsgAttrID) + " value = " + str(MsgClusterData) )

def Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Electrical Measurement Cluster
    Domoticz.Log("ReadCluster - ClusterID=0b04 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )


def Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Magic Cube Xiaomi rotation and Power Meter

    Domoticz.Debug("ReadCluster - ClusterID=000C - MsgSrcEp: %s MsgAttrID: %s MsgClusterData: %s " %(MsgSrcEp, MsgAttrID, MsgClusterData))
    if MsgAttrID=="0055":
        # Are we receiving Power
        EPforPower = getEPforClusterType( self, MsgSrcAddr, "Power" ) 
        EPforMeter = getEPforClusterType( self, MsgSrcAddr, "Meter" ) 
        EPforPowerMeter = getEPforClusterType( self, MsgSrcAddr, "PowerMeter" ) 
        Domoticz.Debug("EPforPower: %s, EPforMeter: %s, EPforPowerMeter: %s" %(EPforPower, EPforMeter, EPforPowerMeter))
       
        if len(EPforPower) == len(EPforMeter) == len(EPforPowerMeter) == 0:
            rotation_angle = struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0]

            Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube angle: %s" %rotation_angle)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(int(rotation_angle)), Attribute_ = '0055' )

            if rotation_angle < 0:
                #anti-clokc
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="90"
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"90")
            if rotation_angle >= 0:
                # Clock
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

        elif len(EPforMeter) > 0 or len(EPforPowerMeter) > 0 : # We have several EPs in Power/Meter
            value = round(float(decodeAttribute( MsgAttType, MsgClusterData )),3)
            Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " +str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(value))
            Domoticz.Debug("ReadCluster - ClusterId=000c - List of Power/Meter EPs" +str( EPforPower ) + str(EPforMeter) +str(EPforPowerMeter) )
            for ep in EPforPower + EPforMeter:
                if ep == MsgSrcEp:
                    Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(value) )
                    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0702',str(value))   # For to Power Cluster
                    break      # We just need to send once
        else:
            Domoticz.Log("ReadCluster 000c - received unknown value - MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
                    %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    elif MsgAttrID=="ff05": # Rotation - horinzontal
        Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) )
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
        #MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

    else:
        Domoticz.Debug("ReadCluster - ClusterID=000c - unknown message - SAddr = " + str(MsgSrcAddr) + " EP = " +\
                str( MsgSrcEp) + " MsgAttrID = " + str(MsgAttrID) + " Value = "+ str(MsgClusterData) )


def Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # LevelControl cluster

    Domoticz.Debug("ReadCluster - ClusterID: %s Addr: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s"
            %(MsgClusterId, MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))
    if MsgAttrID == '0000':
        Domoticz.Debug("ReadCluster - ClusterId=0008 - Level Control: " + str(MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = MsgClusterData
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
    elif MsgAttrID == 'f000':
        Domoticz.Debug("ReadCluster - ClusterId=0008 - Attribute f000: " + str(MsgClusterData) )

    return

def Cluster0005( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    Domoticz.Log("ReadCluster - %s - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

def Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Cluster On/Off

    if MsgSrcEp == '06': # Most likely Livolo
        Domoticz.Log("ReadCluster - ClusterId=0006 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
                %(MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    if MsgAttrID=="0000" or MsgAttrID=="8000":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
        Domoticz.Debug("ReadCluster - ClusterId=0006 - reception General: On/Off: " + str(MsgClusterData) )

    elif MsgAttrID == "f000" and MsgAttType == "0023" and MsgAttSize == "0004":
        value = int(decodeAttribute( MsgAttType, MsgClusterData ))
        Domoticz.Debug("ReadCluster - Feedback from device " + str(MsgSrcAddr) + "/" + MsgSrcEp + " MsgClusterData: " + MsgClusterData + \
                " decoded: " + str(value) )
    else:
        Domoticz.Debug("ReadCluster - ClusterId=0006 - reception heartbeat - Message attribut inconnu: " + MsgAttrID + " / " + MsgClusterData)
    return

def Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Door Lock Cluster

    def decode_vibr(value):         #Decoding XIAOMI Vibration sensor 
        if value == '' or value is None:
            return value
        if   value == "0001": return '20' # Take/Vibrate
        elif value == "0002": return '10' # we will most-likely receive 0x0503/0x0054 after
        elif value == "0003": return '30' #Drop
        return '00'

    Domoticz.Log("ReadCluster 0101 - Dev: %s, EP:%s AttrID: %s, AttrType: %s, Attribute: %s" \
            %( MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgClusterData))

    if MsgAttrID == "0000":          # Lockstate
        Domoticz.Log("ReadCluster 0101 - Dev: Lock state " +str(MsgClusterData) )

    elif MsgAttrID == "0001":         # Locktype
        Domoticz.Log("ReadCluster 0101 - Dev: Lock type "  + str(MsgClusterData))

    elif MsgAttrID == "0002":         # Enabled
        Domoticz.Log("ReadCluster 0101 - Dev: Enabled "  + str(MsgClusterData))

    elif MsgAttrID ==  "0055":   # Aqara Vibration
        Domoticz.Log("ReadCluster 0101 - Aqara Vibration - Attribute: %s" %(MsgClusterData) )
        # "LevelNames": "Off|Tilt|Vibrate|Free Fall"
        state = decode_vibr( MsgClusterData )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    elif MsgAttrID == "0503":   # Aqara Vibration
        if MsgClusterData == "0054": # Following Tilt
            state = "10"
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    elif MsgAttrID == "0505":   # Aqara Vibration
        if MsgClusterData == "00CA0000":
            pass

    elif MsgAttrID == "0508":   # Aqara Vibration / Liberation Mode 
        state = "00"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    else:
        Domoticz.Debug("ReadCluster 0101 - unknown AtttrID: %s Attribute: %s" %(MsgAttrID, MsgClusterData) )
        


def Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Measurement Umidity Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( MsgAttType, MsgClusterData))/100,1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = value

    Domoticz.Debug("ReadCluster - ClusterId=0405 - reception hum: " + str(int(MsgClusterData,16)/100) )


def Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Temperature Measurement Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( MsgAttType, MsgClusterData))/100,1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
    else:
        Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")

def Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: Pression atmospherique)

    if MsgAttType == "0028":
        # seems to be a boolean . May be a beacon ...
        return

    value = int(decodeAttribute( MsgAttType, MsgClusterData ))
    Domoticz.Debug("Cluster0403 - decoded value: from:%s to %s" %( MsgClusterData, value) )

    if MsgAttrID == "0000": # Atmo in mb
        #value = round((value/100),1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        Domoticz.Debug("ReadCluster - ClusterId=0403 - 0000 reception atm: " + str(value ) )

    if MsgAttrID == "0010": # Atmo in 10xmb
        value = round((value/10),1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        Domoticz.Debug("ReadCluster - ClusterId=0403 - 0010 reception atm: " + str(value ) )


def Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: Occupancy Sensing)

    Domoticz.Debug("ReadCluster - ClusterId=0406 - reception Occupancy Sensor: " + str(MsgClusterData) )
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData

def Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: LUX)

    Domoticz.Debug("ReadCluster - ClusterId=0400 - reception LUX Sensor: " + str(int(MsgClusterData,16)) )
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(int(MsgClusterData,16) ))
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=int(MsgClusterData,16)

def Cluster0500( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    ''' 
    Cluster: Security & Safety IAZ Zone
    https://www.nxp.com/docs/en/user-guide/JN-UG-3077.pdf ( section 26.2 )
    '''


    ZONE_TYPE = { 0x0000: 'standard',
        0x000D: 'motion',
        0x0015: 'contact',
        0x0028: 'fire',
        0x002A: 'water',
        0x002B: 'gas',
        0x002C: 'personal',
        0x002D: 'vibration',
        0x010F: 'remote_control',
        0x0115: 'key_fob',
        0x021D: 'key_pad',
        0x0225: 'standar_warning',
        0xFFFF: 'invalid' }

    Domoticz.Debug("ReadCluster0500 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" \
            %( MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Log("ReadCluster0500 - receiving a message from unknown device: %s" %MsgSrcAddr)
        return

    if 'IAS' not in  self.ListOfDevices[MsgSrcAddr]:
         self.ListOfDevices[MsgSrcAddr]['IAS'] = {}
         self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = {}
         self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneType'] = {}
         self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = {}

    if MsgAttrID == "0000": # ZoneState ( 0x00 Not Enrolled / 0x01 Enrolled )
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 5, MsgClusterData)
        if int(MsgClusterData,16) == 0x00:
            Domoticz.Debug("ReadCluster0500 - Device: %s NOT ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)))
            self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = int(MsgClusterData,16)
        elif  int(MsgClusterData,16) == 0x01:
            Domoticz.Debug("ReadCluster0500 - Device: %s ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)))
            self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = int(MsgClusterData,16)

    elif MsgAttrID == "0001": # ZoneType
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 5, MsgClusterData)
        if int(MsgClusterData,16) in ZONE_TYPE:
            Domoticz.Log("ReadCluster0500 - Device: %s - ZoneType: %s" %(MsgSrcAddr, ZONE_TYPE[int(MsgClusterData,16)]))
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneType'] = int(MsgClusterData,16)
        else: 
            Domoticz.Log("ReadCluster0500 - Device: %s - Unknown ZoneType: %s" %(MsgSrcAddr, MsgClusterData))


    elif MsgAttrID == "0002": # Zone Status
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 5, MsgClusterData)
        if MsgClusterData !='' and len(MsgClusterData) == 16:
            alarm1 = int(MsgClusterData,16) & 0x0000000000000001
            alarm2 = int(MsgClusterData,16) & 0x0000000000000010
            tamper = int(MsgClusterData,16) & 0x0000000000000100
            batter = int(MsgClusterData,16) & 0x0000000000001000
            srepor = int(MsgClusterData,16) & 0x0000000000010000
            rrepor = int(MsgClusterData,16) & 0x0000000000100000
            troubl = int(MsgClusterData,16) & 0x0000000001000000
            acmain = int(MsgClusterData,16) & 0x0000000010000000
            test   = int(MsgClusterData,16) & 0x0000000100000000
            batdef = int(MsgClusterData,16) & 0x0000001000000000
            Domoticz.Log("ReadCluster0500 - Device:%s status alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s" \
                    %( MsgSrcAddr, alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef))

            #self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = int(MsgClusterData,16)
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" %( alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef)

        else:
            Domoticz.Log("ReadCluster0500 - Device: %s empty data: %s" %(MsgSrcAddr, MsgClusterData))

    elif MsgAttrID == "0010":
        Domoticz.Log("ReadCluster0500 - receiving attribute 0x0010: %s" %MsgClusterData)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 7, MsgClusterData)

    Domoticz.Debug("ReadCluster0500 - Device: %s Data: %s" %(MsgSrcAddr, MsgClusterData))

    return



def Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # General Basic Cluster
    # It might be good to make sure that we are on a Xiaomi device - A priori: 0x115f


    if MsgAttrID == "0000": # ZCL Version
        Domoticz.Debug("ReadCluster - 0x0000 - ZCL Version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ZCL_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001": # Application Version
        Domoticz.Debug("ReadCluster - Application version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['App_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['App Version'] = str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0002": # Stack Version
        Domoticz.Debug("ReadCluster - Stack version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        self.ListOfDevices[MsgSrcAddr]['Stack Version'] = str(decodeAttribute( MsgAttType, MsgClusterData) )
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Stack_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0003": # Hardware version
        Domoticz.Debug("ReadCluster - 0x0000 - Hardware version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        self.ListOfDevices[MsgSrcAddr]['HW Version'] = str(decodeAttribute( MsgAttType, MsgClusterData) )
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['HW_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004": # Manufacturer
        Domoticz.Debug("ReadCluster - 0x0000 - Manufacturer: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Manufacturer']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID=="0005":  # Model info
        if MsgClusterData != '':
            modelName = decodeAttribute( MsgAttType, MsgClusterData, handleErrors=True)  # In case there is an error while decoding then return ''
            Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device: " + modelName)
            if modelName != '':
                # It has been decoded !
                Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device: " + modelName)

                if self.ListOfDevices[MsgSrcAddr]['Model'] == '' or self.ListOfDevices[MsgSrcAddr]['Model'] == {}:
                    self.ListOfDevices[MsgSrcAddr]['Model'] = modelName
                else:
                    if self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:  
                        modelName = self.ListOfDevices[MsgSrcAddr]['Model']
                    elif modelName in self.DeviceConf:
                        self.ListOfDevices[MsgSrcAddr]['Model'] = modelName

                # Let's see if this model is known in DeviceConf. If so then we will retreive already the Eps
                if self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:                 # If the model exist in DeviceConf.txt
                    modelName = self.ListOfDevices[MsgSrcAddr]['Model']
                    Domoticz.Debug("Extract all info from Model : %s" %self.DeviceConf[modelName])
                    self.ListOfDevices[MsgSrcAddr]['ConfigSource'] ='DeviceConf'
                    if 'Type' in self.DeviceConf[modelName]:                                   # If type exist at top level : copy it
                        self.ListOfDevices[MsgSrcAddr]['Type']=self.DeviceConf[modelName]['Type']
                    for Ep in self.DeviceConf[modelName]['Ep']:                                # For each Ep in DeviceConf.txt
                        if Ep not in self.ListOfDevices[MsgSrcAddr]['Ep']:                     # If this EP doesn't exist in database
                            self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]={}                        # create it.
                        for cluster in self.DeviceConf[modelName]['Ep'][Ep]:                   # For each cluster discribe in DeviceConf.txt
                            if cluster not in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]:        # If this cluster doesn't exist in database
                                self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}           # create it.
                        if 'Type' in self.DeviceConf[modelName]['Ep'][Ep]:                     # If type exist at EP level : copy it
                            self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]['Type']=self.DeviceConf[modelName]['Ep'][Ep]['Type']
                        if 'ColorMode' in self.DeviceConf[modelName]['Ep'][Ep]:
                            if 'ColorInfos' not in self.ListOfDevices[MsgSrcAddr]:
                                self.ListOfDevices[MsgSrcAddr]['ColorInfos'] ={}
                            if 'ColorMode' in  self.DeviceConf[modelName]['Ep'][Ep]:
                                self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = int(self.DeviceConf[modelName]['Ep'][Ep]['ColorMode'])

                if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
                    self.DiscoveryDevices[MsgSrcAddr]['Model'] = modelName

    elif MsgAttrID == "0007": # Power Source
        Domoticz.Debug("ReadCluster - Power Source: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        # 0x03 stand for Battery
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['PowerSource'] = str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0016": # Battery
        Domoticz.Debug("ReadCluster - 0x0000 - Battery: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        if self.pluginconf.allowStoreDiscoveryFrames and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Battery'] = str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID=="ff01" and self.ListOfDevices[MsgSrcAddr]['Status']=="inDB":  # xiaomi battery lvl

        ReadAttributeRequest_Ack(self, MsgSrcAddr)         # Ping Xiaomi devices

        Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " ClusterData : " + str(MsgClusterData) )
        # Taging: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/42#issuecomment-370152404
        # 0x0624 might be the LQI indicator and 0x0521 the RSSI dB

        sBatteryLvl = retreive4Tag( "0121", MsgClusterData )
        sTemp2 = retreive4Tag( "0328", MsgClusterData )   # Device Temperature
        sTemp = retreive4Tag( "6429", MsgClusterData )
        sOnOff = retreive4Tag( "6410", MsgClusterData )[0:2]
        sHumid = retreive4Tag( "6521", MsgClusterData )
        sHumid2 = retreive4Tag( "6529", MsgClusterData )
        sPress = retreive8Tag( "662b", MsgClusterData )

        sOnOff2 = retreive4Tag( "6420", MsgClusterData )[0:2]    # OnOff for Aqara Bulb
        sLevel = retreive4Tag( "6520", MsgClusterData )[0:2]     # Dim level for Aqara Bulb
        stag10 = retreive4Tag( "6621", MsgClusterData )

        #MAX_VOLTS = 3.0
        #MIN_VOLTS = 2.5

        if sBatteryLvl != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '8e':    # Battery Level makes sense for non main powered devices
            BatteryLvl = '%s%s' % (str(sBatteryLvl[2:4]),str(sBatteryLvl[0:2])) 

            ValueBattery=round(int(BatteryLvl,16)/10/3.3)

            #battery_percent = ( (ValueBattery - MIN_VOLTS) / (MAX_VOLTS - MIN_VOLTS)) * 100
            #Domoticz.Log("ReadCluster 0000/ff01 Saddr: %s - Volts: %s Battery %s" %(MsgSrcAddr, ValueBattery, battery_percent))
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Battery : " + str(ValueBattery) )
            self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery

        if sTemp != '':
            Temp = struct.unpack('h',struct.pack('>H',int(sTemp,16)))[0]
            ValueTemp=round(Temp/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402']=ValueTemp
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)

        if sHumid != '':
            ValueHumid = struct.unpack('H',struct.pack('>H',int(sHumid,16)))[0]
            ValueHumid = round(ValueHumid/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0405']=ValueHumid
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity : " + str(ValueHumid) )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0405",ValueHumid)

        if sHumid2 != '':
            Humid2 = struct.unpack('h',struct.pack('>H',int(sHumid2,16)))[0]
            ValueHumid2=round(Humid2/100,1)
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity2 : " + str(ValueHumid2) )

        if sPress != '':
            Press = '%s%s%s%s' % (str(sPress[6:8]),str(sPress[4:6]),str(sPress[2:4]),str(sPress[0:2])) 
            ValuePress=round((struct.unpack('i',struct.pack('i',int(Press,16)))[0])/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]["0403"]=ValuePress
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Atmospheric Pressure : " + str(ValuePress) )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0403",ValuePress)

        if sOnOff != '':
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: %s sOnOff: %s" %(MsgSrcAddr, sOnOff))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff

        if sOnOff2 != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] == '8e': # Aqara Bulb
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: %s sOnOff2: %s" %(MsgSrcAddr, sOnOff2))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff2
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006',sOnOff2)

        if sLevel != '':
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: %s sLevel: %s" %(MsgSrcAddr, sLevel))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0008',sLevel)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0008'] = sLevel

        if stag10 != '':
            # f400 --
            # 4602 --
            Domoticz.Log("ReadCluster - 0000/ff01 Saddr: %s Tag10: %s" %(MsgSrcAddr, stag10))

    elif MsgAttrID=="ff02" and self.ListOfDevices[MsgSrcAddr]['Status']=="inDB":  # 
        Domoticz.Log("ReadCluster - %s/%s MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
                %( MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    else:
        Domoticz.Debug("ReadCluster 0x0000 - Message attribut inconnu: " + str(decodeAttribute( MsgAttType, MsgClusterData) ))
    

def Cluster0012( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    def cube_decode(value):
        'https://github.com/sasu-drooz/Domoticz-Zigate/wiki/Aqara-Cube-decoding'
        value=int(value,16)
        if value == '' or value is None:
            return value

        if value == 0x0000:         
            Domoticz.Debug("cube action: " + 'Shake' )
            value='10'
        elif value == 0x0002:            
            Domoticz.Debug("cube action: " + 'Wakeup' )
            value = '20'
        elif value == 0x0003:
            Domoticz.Debug("cube action: " + 'Drop' )
            value = '30'
        elif value & 0x0040 != 0:    
            face = value ^ 0x0040
            face1 = face >> 3
            face2 = face ^ (face1 << 3)
            Domoticz.Debug("cube action: " + 'Flip90_{}{}'.format(face1, face2))
            value = '40'
        elif value & 0x0080 != 0:  
            face = value ^ 0x0080
            Domoticz.Debug("cube action: " + 'Flip180_{}'.format(face) )
            value = '50'
        elif value & 0x0100 != 0:  
            face = value ^ 0x0100
            Domoticz.Debug("cube action: " + 'Push/Move_{}'.format(face) )
            value = '60'
        elif value & 0x0200 != 0:  # double_tap
            face = value ^ 0x0200
            Domoticz.Debug("cube action: " + 'Double_tap_{}'.format(face) )
            value = '70'
        else:  
            Domoticz.Debug("cube action: Not expected value %s" %value )
        return value

    if self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.remote.b1acn01', 'lumi.remote.b186acn01', 'lumi.remote.b286acn01'):
        value = decodeAttribute( MsgAttType, MsgClusterData )
        Domoticz.Debug("ReadCluster - ClusterId=0012 - Switch Aqara: EP: %s Value: %s " %(MsgSrcEp,value))
        value = int(value)
        if value == 0: value = 3
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",str(value))    # Force ClusterType Switch in order to behave as 
        return                                                                              # a switch in order to behave as a switch

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.sensor_cube.aqgl01', 'lumi.sensor_cube'):
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
        Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(MsgClusterData) )
        Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(cube_decode(MsgClusterData)) )
        return

    else:
        Domoticz.Log("Cluster0012 - unknown Model: %s for this Attribute: %s value: %s " %(self.ListOfDevices[MsgSrcAddr]['Model'], MsgAttrID, MsgClusterData))



def Cluster0201( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    # Thermostat cluster
    oldValue = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]).split(";")
    if len(oldValue) != 6:
        oldValue = '0;0;0;0;0;0'.split(';')

    Domoticz.Log("ReadCluster 0201 - Addr: %s Ep: %s AttrId: %s AttrType: %s AttSize: %s Data: %s"
            %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    value = decodeAttribute( MsgAttType, MsgClusterData)

    if MsgAttrID =='0000':  # Local Temperature (Zint16)
        ValueTemp=round(int(value)/100,1)
        localTemp = ValueTemp
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0402',ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402'] = str(ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(localTemp, oldValue[1], oldValue[2], oldValue[3], oldValue[4],oldValue[5])
        Domoticz.Log("ReadCluster 0201 - Local Temp: %s" %ValueTemp)

    elif MsgAttrID == '0008':   #  Pi Heating Demand  (valve position %)
        Domoticz.Log("ReadCluster 0201 - Heating demand: %s" %value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], value, oldValue[2], oldValue[3], oldValue[4],oldValue[5])

    elif MsgAttrID == '0010':   # Calibration / Adjustement
        value = value / 10 
        Domoticz.Log("ReadCluster 0201 - Calibration: %s" %value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], value, oldValue[2], oldValue[3], oldValue[4],oldValue[5])

    elif MsgAttrID == '0011':   # Cooling Setpoint (Zinte16)
        ValueTemp=round(int(value)/100,1)
        Domoticz.Log("ReadCluster 0201 - Cooling Setpoint: %s" %ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], ValueTemp, oldValue[3], oldValue[4],oldValue[5])

    elif MsgAttrID == '0012':   # Heat Setpoint (Zinte16)
        ValueTemp=round(int(value)/100,1)
        Domoticz.Log("ReadCluster 0201 - Heating Setpoint: %s" %ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], ValueTemp, oldValue[4],oldValue[5])
        if str(self.ListOfDevices[MsgSrcAddr]['Model']).find('SPZB') == -1:
            # In case it is not a Eurotronic, let's Update heatPoint
            Domoticz.Log("ReadCluster 0201 - Request update on Domoticz")
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], ValueTemp, oldValue[4],oldValue[5])

    elif MsgAttrID == '0014':   # Unoccupied Heating
        Domoticz.Log("ReadCluster 0201 - Unoccupied Heating:  %s" %value)

    elif MsgAttrID == '0015':   # MIN_HEAT_SETPOINT_LIMIT
        ValueTemp=round(int(value)/100,1)
        Domoticz.Log("ReadCluster 0201 - Min SetPoint: %s" %ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], oldValue[3], ValueTemp, oldValue[5])

    elif MsgAttrID == '0016':   # MAX_HEAT_SETPOINT_LIMIT
        ValueTemp=round(int(value)/100,1)
        Domoticz.Log("ReadCluster 0201 - Max SetPoint: %s" %ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], oldValue[3], oldValue[4], ValueTemp)

    elif MsgAttrID == '001b':
        Domoticz.Log("ReadCluster 0201 - Attribute 1B: %s" %value)

    elif MsgAttrID == '001c':
        SYSTEM_MODE = { 0x00: 'Off' ,
                0x01: 'Auto' ,
                0x02: 'Reserved' ,
                0x03: 'Cool',
                0x04: 'Heat' ,
                0x05: 'Emergency Heating',
                0x06: 'Pre-cooling',
                0x07: 'Fan only'  }

        if int(value) in SYSTEM_MODE:
            Domoticz.Log("ReadCluster 0201 - System Mode: %s / %s" %(value, SYSTEM_MODE[value]))
        else:
            Domoticz.Log("ReadCluster 0201 - Attribute 1C: %s" %value)


    elif MsgAttrID == '0403':
        Domoticz.Log("ReadCluster 0201 - Attribute 403: %s" %value)

    elif MsgAttrID == '0408':
        value = int(decodeAttribute( MsgAttType, MsgClusterData))
        Domoticz.Log("ReadCluster 0201 - Attribute 408: %s" %value)

    elif MsgAttrID == '0409':
        value = int(decodeAttribute( MsgAttType, MsgClusterData))
        Domoticz.Log("ReadCluster 0201 - Attribute 409: %s" %value)

    elif MsgAttrID == '4000': # TRV Mode
        Domoticz.Log("ReadCluster 0201 - TRV Mode: %s" %value)

    elif MsgAttrID == '4001': # Valve position
        Domoticz.Log("ReadCluster 0201 - Valve position: %s" %value)

    elif MsgAttrID == '4002': # Erreors
        Domoticz.Log("ReadCluster 0201 - Status: %s" %value)

    elif MsgAttrID == '4003': # Current Temperature Set point
        ValueTemp = round(int(value)/100,1)
        Domoticz.Log("ReadCluster 0201 - Current Temp Set point: %s versus %s " %(ValueTemp, oldValue[3]))
        if ValueTemp != float(oldValue[3]):
            # Seems that there is a local setpoint
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0201',ValueTemp, Attribute_=MsgAttrID)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], ValueTemp, oldValue[4],oldValue[5])

    elif MsgAttrID == '4008': # Host Flags
        HOST_FLAGS = {
                0x000002:'Display Flipped',
                0x000004:'Boost mode',
                0x000010:'disable off mode',
                0x000020:'enable off mode',
                0x000080:'child lock'
                }
        Domoticz.Log("ReadCluster 0201 - Host Flags: %s" %value)

        
    else:
        Domoticz.Log("ReadCluster 0201 - Unexpected Attribute: %s Type: %s lenght: %s Value:%s  " %(MsgAttrID,MsgAttType,MsgAttSize,MsgClusterData))


def Clusterfc00( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    DIMMER_STEP = (255//100)

    Domoticz.Debug("ReadCluster - %s - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    if MsgAttrID not in ( '0001', '0002', '0003', '0004'):
        Domoticz.Log("ReadCluster - %s - %s/%s unknown MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))
        return

    prev_Value = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]).split(";")
    if len(prev_Value) != 3:
        prev_Value = '0;10'.split(';')
    move = None
    onoffValue = int(prev_Value[0])
    lvlValue = int(prev_Value[1],16)

    Domoticz.Log("ReadCluster - %s - %s/%s - past OnOff: %s, Lvl: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, onoffValue, lvlValue))
    if MsgAttrID == '0001': #On button
        Domoticz.Log("ReadCluster - %s - %s/%s - ON Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp))
        onoffValue = 1

    elif MsgAttrID == '0004': # Off  Button
        Domoticz.Log("ReadCluster - %s - %s/%s - OFF Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp))
        onoffValue = 0

    elif MsgAttrID in  ( '0002', '0003' ): # Dim+ / 0002 is +, 0003 is -
        Domoticz.Log("ReadCluster - %s - %s/%s - DIM Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp))
        action = MsgClusterData[2:4]
        duration = MsgClusterData[6:8]

        duration = int(duration,16)
        Domoticz.Log("ReadCluster - %s - %s/%s - DIM Action: %s, Duration: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, action, duration))
        if action == '00': #Short press
            onoffValue = 1
            # Short press/Release - Make one step   , we just report the press
            if MsgAttrID == '0002': lvlValue += DIMMER_STEP
            elif MsgAttrID == '0003': lvlValue -= DIMMER_STEP

        elif action == '01': # Long press
            onoffValue = 1
            if MsgAttrID == '0002':   lvlValue += DIMMER_STEP
            elif MsgAttrID == '0003': lvlValue -= DIMMER_STEP

        if lvlValue > 255: lvlValue = 255
        if lvlValue <= 0: lvlValue = 0
        Domoticz.Log("ReadCluster - %s - %s/%s - Level: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, lvlValue))

    #Update Domo
    sValue = '%02x' %onoffValue
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s:%s' %(onoffValue, lvlValue)
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', sValue)
    Domoticz.Log("ReadCluster %s - %s/%s - updateing self.ListOfDevices[%s]['Ep'][%s][%s] = %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId , self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]))

    sValue = '%02x' %lvlValue
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s:%s' %(onoffValue, lvlValue)
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, sValue)
    Domoticz.Log("ReadCluster %s - %s/%s - updateing self.ListOfDevices[%s]['Ep'][%s][%s] = %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId , self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]))
