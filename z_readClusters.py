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

import z_domoticz
import z_tools
import z_output
import z_status

def retreive4Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+4)]

def retreive8Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+8)]

def decodeAttribute(AttType, Attribute, handleErrors=False):
    '''
    decodeAttribute( Attribute Type, Attribute Data )
    Will return an int converted in str, which is the decoding of Attribute Data base on Attribute Type
    Here after are the DataType and their DataType code
    ZigBee_NoData = 0x00, ZigBee_8BitData = 0x08, ZigBee_16BitData = 0x09, ZigBee_24BitData = 0x0a,
    ZigBee_32BitData = 0x0b, ZigBee_40BitData = 0x0c, ZigBee_48BitData = 0x0d, ZigBee_56BitData = 0x0e,
    ZigBee_64BitData = 0x0f, ZigBee_Boolean = 0x10, ZigBee_8BitBitMap = 0x18, ZigBee_16BitBitMap = 0x19,
    ZigBee_24BitBitMap = 0x1a, ZigBee_32BitBitMap = 0x1b, ZigBee_40BitBitMap = 0x1c, ZigBee_48BitBitMap = 0x1d,
    ZigBee_56BitBitMap = 0x1e, ZigBee_64BitBitMap = 0x1f, ZigBee_8BitUint = 0x20, ZigBee_16BitUint = 0x21,
    ZigBee_24BitUint = 0x22, ZigBee_32BitUint = 0x23, ZigBee_40BitUint = 0x24, ZigBee_48BitUint = 0x25,
    ZigBee_56BitUint = 0x26, ZigBee_64BitUint = 0x27, ZigBee_8BitInt = 0x28, ZigBee_16BitInt = 0x29,
    ZigBee_24BitInt = 0x2a, ZigBee_32BitInt = 0x2b, ZigBee_40BitInt = 0x2c, ZigBee_48BitInt = 0x2d,
    ZigBee_56BitInt = 0x2e, ZigBee_64BitInt = 0x2f, ZigBee_8BitEnum = 0x30, ZigBee_16BitEnum = 0x31,
    ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42, ZigBee_LongOctedString = 0x43, ZigBee_LongCharacterString = 0x44,
    ZigBee_TimeOfDay = 0xe0, ZigBee_Date = 0xe1, ZigBee_UtcTime = 0xe2, ZigBee_ClusterId = 0xe8,
    ZigBee_AttributeId = 0xe9, ZigBee_BACNetOId = 0xea, ZigBee_IeeeAddress = 0xf0, ZigBee_128BitSecurityKey = 0xf1 
    '''

    if len(Attribute) == 0:
        return
    Domoticz.Debug("decodeAttribute( %s, %s) " %(AttType, Attribute) )

    # tested
    if int(AttType,16) == 0x10:    # Boolean
        return Attribute
    elif int(AttType,16) == 0x16:  # 8Bit bitmap
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x20:  # Uint8 / unsigned char
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x21:   # 16BitUint
        return str(struct.unpack('H',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x22:   # ZigBee_24BitUint
            #Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
            #                        str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])))
            #return str(struct.unpack('I',struct.pack('I',int("0"+Attribute,16)))[0])
            return str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])   # Zigate retourne un Uint32

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
            #Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
            #                        str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])))
            #return str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])
            return str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])   # Zigate retourne un Uint32
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
                Domoticz.Log("decodeAttribute - seems errors, returning with errors ignore")
        return decode
    else:
        Domoticz.Log("decodeAttribut(%s, %s) unknown, returning %s unchanged" %(AttType, Attribute, Attribute) )
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
        Domoticz.Log("ReadCluster - Status %s for addr: %s/%s on cluster/attribute %s/%s" %(MsgAttrStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID) )
        self.statistics._clusterKO += 1
        return

    if z_tools.DeviceExist(self, Devices, MsgSrcAddr) == False:
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
        Domoticz.Log("ReadCluster - %s NwkId: %s Ep: %s AttrId: %s AttyType: %s Attsize: %s Status: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgAttrStatus, MsgClusterData))

        
    if   MsgClusterId=="0000": Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0001": Cluster0001( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
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
    else:
        Domoticz.Error("ReadCluster - Error/unknow Cluster Message: " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
        Domoticz.Error("                                 MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
        Domoticz.Error("                                 MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )

def Cluster0001( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    value = decodeAttribute( MsgAttType, MsgClusterData)
    if MsgAttrID == "0000": # Voltage
        value = round(int(value)/10, 1)
        Domoticz.Debug("readCluster 0001 - Voltage: %s V " %(value) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

    elif MsgAttrID == "0010": # Voltage
        Domoticz.Debug("readCluster 0001 - Battery Voltage: %s " %(value) )

    elif MsgAttrID == "0020": # Battery %
        Domoticz.Debug("readCluster 0001 - Battery: %s " %(value) )


def Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Smart Energy Metering
    if int(MsgAttSize,16) == 0:
        Domoticz.Debug("Cluster0702 - empty message ")
        return

    value = int(decodeAttribute( MsgAttType, MsgClusterData ))
    Domoticz.Debug("Cluster0702 - MsgAttrID: %s MsgAttType: %s decodedValue: %s" %(MsgAttrID, MsgAttType, value))

    if MsgAttrID == "0000": 
        Domoticz.Debug("Cluster0702 - 0x0000 CURRENT_SUMMATION_DELIVERED %s " %(value))
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        #z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

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
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

    else:
        Domoticz.Debug("ReadCluster - 0x0702 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )
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
        EPforPower = z_tools.getEPforClusterType( self, MsgSrcAddr, "Power" ) 
        EPforMeter = z_tools.getEPforClusterType( self, MsgSrcAddr, "Meter" ) 
        EPforPowerMeter = z_tools.getEPforClusterType( self, MsgSrcAddr, "PowerMeter" ) 
        Domoticz.Debug("EPforPower: %s, EPforMeter: %s, EPforPowerMeter: %s" %(EPforPower, EPforMeter, EPforPowerMeter))
       
        if len(EPforPower) == len(EPforMeter) == len(EPforPowerMeter) == 0:
            Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube angle: " + str(struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0])  )
            if struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0] < 0:
                #anti-clokc
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="90"
                z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"90")
            if struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0] >= 0:
                # Clock
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
                z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

        elif len(EPforMeter) > 0 or len(EPforPowerMeter) > 0 : # We have several EPs in Power/Meter
            value = round(float(decodeAttribute( MsgAttType, MsgClusterData )),3)
            Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " +str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(value))
            Domoticz.Debug("ReadCluster - ClusterId=000c - List of Power/Meter EPs" +str( EPforPower ) + str(EPforMeter) +str(EPforPowerMeter) )
            for ep in EPforPower + EPforMeter:
                if ep == MsgSrcEp:
                    Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(value) )
                    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
                    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
                    break      # We just need to send once
        else:
            Domoticz.Log("ReadCluster 000c - received unknown value - MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
                    %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    elif MsgAttrID=="ff05": # Rotation - horinzontal
        Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) )
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
        #z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

    else:
        Domoticz.Debug("ReadCluster - ClusterID=000c - unknown message - SAddr = " + str(MsgSrcAddr) + " EP = " +\
                str( MsgSrcEp) + " MsgAttrID = " + str(MsgAttrID) + " Value = "+ str(MsgClusterData) )


def Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # LevelControl cluster

    Domoticz.Debug("ReadCluster - ClusterId=0008 - Level Control: " + str(MsgClusterData) )
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = MsgClusterData
    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
    return

def Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Cluster On/Off

    if MsgAttrID=="0000" or MsgAttrID=="8000":
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
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
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    elif MsgAttrID == "0503":   # Aqara Vibration
        if MsgClusterData == "0054": # Following Tilt
            state = "10"
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    elif MsgAttrID == "0505":   # Aqara Vibration
        if MsgClusterData == "00CA0000":
            pass

    elif MsgAttrID == "0508":   # Aqara Vibration / Liberation Mode 
        state = "00"
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    else:
        Domoticz.Debug("ReadCluster 0101 - unknown AtttrID: %s Attribute: %s" %(MsgAttrID, MsgClusterData) )
        


def Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Measurement Umidity Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( MsgAttType, MsgClusterData))/100,1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = value

    Domoticz.Debug("ReadCluster - ClusterId=0405 - reception hum: " + str(int(MsgClusterData,16)/100) )


def Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Temperature Measurement Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( MsgAttType, MsgClusterData))/100,1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
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
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        Domoticz.Debug("ReadCluster - ClusterId=0403 - 0000 reception atm: " + str(value ) )

    if MsgAttrID == "0010": # Atmo in 10xmb
        value = round((value/10),1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        Domoticz.Debug("ReadCluster - ClusterId=0403 - 0010 reception atm: " + str(value ) )


def Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: Occupancy Sensing)

    Domoticz.Debug("ReadCluster - ClusterId=0406 - reception Occupancy Sensor: " + str(MsgClusterData) )
    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData

def Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: LUX)

    Domoticz.Debug("ReadCluster - ClusterId=0400 - reception LUX Sensor: " + str(int(MsgClusterData,16)) )
    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(int(MsgClusterData,16) ))
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

    Domoticz.Log("ReadCluster0500 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" \
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
            Domoticz.Log("ReadCluster0500 - Device: %s NOT ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)))
            self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = int(MsgClusterData,16)
        elif  int(MsgClusterData,16) == 0x01:
            Domoticz.Log("ReadCluster0500 - Device: %s ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)))
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
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = int(MsgClusterData,16)
            Domoticz.Log("ReadCluster0500 - Device:%s status alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s" \
                    %( MsgSrcAddr, alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef))
        else:
            Domoticz.Log("ReadCluster0500 - Device: %s empty data: %s" %(MsgSrcAddr, MsgClusterData))

    elif MsgAttrID == "0010":
        Domoticz.Log("ReadCluster0500 - receiving attribute 0x0010: %s" %MsgClusterData)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 7, MsgClusterData)

    Domoticz.Log("ReadCluster0500 - Device: %s Data: %s"
            %(MsgSrcAddr, MsgClusterData))

    return



def Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # General Basic Cluster
    # It might be good to make sure that we are on a Xiaomi device - A priori: 0x115f

    if MsgAttrID=="ff01" and self.ListOfDevices[MsgSrcAddr]['Status']=="inDB":  # xiaomi battery lvl

        z_output.ReadAttributeRequest_Ack(self, MsgSrcAddr)         # Ping Xiaomi devices

        Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " ClusterData : " + str(MsgClusterData) )
        # Taging: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/42#issuecomment-370152404
        # 0x0624 might be the LQI indicator and 0x0521 the RSSI dB

        sBatteryLvl = retreive4Tag( "0121", MsgClusterData )
        sTemp2 = retreive4Tag( "0328", MsgClusterData )   # Device Temperature
        sTemp = retreive4Tag( "6429", MsgClusterData )
        sOnOff = retreive4Tag( "6410", MsgClusterData )
        sHumid = retreive4Tag( "6521", MsgClusterData )
        sHumid2 = retreive4Tag( "6529", MsgClusterData )
        sPress = retreive8Tag( "662b", MsgClusterData )

        if sBatteryLvl != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '8e':    # Battery Level makes sense for non main powered devices
            BatteryLvl = '%s%s' % (str(sBatteryLvl[2:4]),str(sBatteryLvl[0:2])) 
            ValueBattery=round(int(BatteryLvl,16)/10/3.3)
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Battery : " + str(ValueBattery) )
            self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
        if sTemp != '':
            Temp = struct.unpack('h',struct.pack('>H',int(sTemp,16)))[0]
            ValueTemp=round(Temp/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402']=ValueTemp
            Domoticz.Log("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)
#        if sTemp2 != '':
#            Temp2 = '%s%s' % (str(sTemp2[2:4]),str(sTemp2[0:2])) 
#            ValueTemp2=round(int(Temp2,16)/100,1)
#            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Device Temperature : " + str(ValueTemp2) )
        if sHumid != '':
            ValueHumid = struct.unpack('H',struct.pack('>H',int(sHumid,16)))[0]
            ValueHumid = round(ValueHumid/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0405']=ValueHumid
            Domoticz.Log("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity : " + str(ValueHumid) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0405",ValueHumid)

        if sHumid2 != '':
            Humid2 = struct.unpack('h',struct.pack('>H',int(sHumid2,16)))[0]
            ValueHumid2=round(Humid2/100,1)
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity2 : " + str(ValueHumid2) )

        if sPress != '':
            Press = '%s%s%s%s' % (str(sPress[6:8]),str(sPress[4:6]),str(sPress[2:4]),str(sPress[0:2])) 
            ValuePress=round((struct.unpack('i',struct.pack('i',int(Press,16)))[0])/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]["0403"]=ValuePress
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Atmospheric Pressure : " + str(ValuePress) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0403",ValuePress)

        if sOnOff != '':
            sOnOff = sOnOff[0:2]  
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " On/Off : " + str(sOnOff) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff

    elif MsgAttrID == "0000": # ZCL Version
        Domoticz.Debug("ReadCluster - 0x0000 - ZCL Version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ZCL_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001": # Application Version
        Domoticz.Debug("ReadCluster - Application version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['App_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['App Version'] = str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0002": # Stack Version
        Domoticz.Debug("ReadCluster - Stack version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        self.ListOfDevices[MsgSrcAddr]['Stack Version'] = str(decodeAttribute( MsgAttType, MsgClusterData) )
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Stack_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0003": # Hardware version
        Domoticz.Debug("ReadCluster - 0x0000 - Hardware version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
        self.ListOfDevices[MsgSrcAddr]['HW Version'] = str(decodeAttribute( MsgAttType, MsgClusterData) )
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['HW_Version']=str(decodeAttribute( MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004": # Manufacturer
        Domoticz.Debug("ReadCluster - 0x0000 - Manufacturer: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))

    elif MsgAttrID=="0005":  # Model info
        if MsgClusterData != '':
            modelName = decodeAttribute( MsgAttType, MsgClusterData, handleErrors=True)  # In case there is an error while decoding then return ''
            Domoticz.Log("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device: " + modelName)
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

                if not self.pluginconf.allowStoreDiscoveryFrames:
                    # Let's see if this model is known in DeviceConf. If so then we will retreive already the Eps
               	    if self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:                 # If the model exist in DeviceConf.txt
                        modelName = self.ListOfDevices[MsgSrcAddr]['Model']
                        Domoticz.Debug("Extract all info from Model : %s" %self.DeviceConf[modelName])
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

    elif MsgAttrID == "0007": # Power Source
        Domoticz.Debug("ReadCluster - Power Source: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))

    elif MsgAttrID == "0016": # Battery
        Domoticz.Debug("ReadCluster - 0x0000 - Battery: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
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
        Domoticz.Log("ReadCluster - ClusterId=0012 - Switch Aqara: EP: %s Value: %s " %(MsgSrcEp,value))
        value = int(value)
        if value == 0: value = 3
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",str(value))    # Force ClusterType Switch in order to behave as 
        return                                                                              # a switch in order to behave as a switch

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.sensor_cube.aqgl01', 'lumi.sensor_cube'):
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
        Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(MsgClusterData) )
        Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(cube_decode(MsgClusterData)) )
        return

    else:
        Domoticz.Log("Cluster0012 - unknown Model: %s for this Attribute: %s value: %s " %(self.ListOfDevices[MsgSrcAddr]['Model'], MsgAttrID, MsgClusterData))

