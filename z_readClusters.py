#!/usr/bin/env python3
# coding: utf-8 -*-
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

import z_domoticz
import z_var
import z_tools
import z_status

def retreive4Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+4)]

def retreive8Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+8)]

def decodeAttribute(AttType, Attribute):
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
    Domoticz.Log("decodeAttribute( %s, %s) " %(AttType, Attribute) )

    # tested
    if int(AttType,16) == 0x10:    # Boolean
        return Attribute
    elif int(AttType,16) == 0x20:  # Uint8
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x30:  # 8BitEnum
        return int(Attribute,16 )
    elif int(AttType,16)  == 0x28: # int8
        return int(Attribute, 16 )
    elif int(AttType,16)  == 0x31: # 16BitEnum 
        return str(struct.unpack('h',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x29:   # 16Bitint   -> tested on Measurement clusters
        return str(struct.unpack('h',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x21:   # 16BitUint
        return str(struct.unpack('H',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x39:  # Xiaomi Float
        return str(struct.unpack('f',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x42:  # CharacterString
        try:
            decoded = binascii.unhexlify(str(Attribute)).decode('utf-8')
        except: 
            decoded = str(Attribute)
        return decoded

    # Not tested yet

    elif int(AttType,16) == 0x23:   # 32BitUint
            Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])

    elif int(AttType,16) == 0x25:   # ZigBee_48BitUint
            Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])))
            return str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])

    elif int(AttType,16) == 0x2b:   # 32Bitint
            Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])

    elif int(AttType,16) == 0x2d:   # ZigBee_48Bitint
            Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])))
            return str(struct.unpack('q',struct.pack('Q',int(Attribute,16)))[0])

    elif int(AttType,16) == 0x22:   # ZigBee_24BitUint
            Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('I',struct.pack('I',int("0"+Attribute,16)))[0])

    elif int(AttType,16) == 0x2a:   # ZigBee_24BitInt
            Domoticz.Log("decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])


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

    self.stats['clusters'] += 1

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
    if z_tools.DeviceExist(self, MsgSrcAddr) == False:
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

    Domoticz.Log("ReadCluster - " +MsgClusterId +"  Saddr: " + str(MsgSrcAddr) + " SrcEp : " + MsgSrcEp +\
            " AttrID: " + MsgAttrID + " AttType : " + MsgAttType + " AttSize : " +MsgAttSize +" Attribute : " + str(MsgClusterData) + " Status: " + MsgAttrStatus )

        
    if   MsgClusterId=="0000": Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
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
    elif MsgClusterId=="0702":  Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    elif MsgClusterId=="0b04": Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    else:
        Domoticz.Error("ReadCluster - Error/unknow Cluster Message: " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
        Domoticz.Error("                                 MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
        Domoticz.Error("                                 MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )


def Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Smart Energy Metering
    if int(MsgAttSize,16) == 0:
        Domoticz.Debug("Cluster0702 - empty message ")
        return

    value = int(decodeAttribute( MsgAttType, MsgClusterData ))
    Domoticz.Log("Cluster0702 - MsgAttrID: %s MsgAttType: %s decodedValue: %s" %(MsgAttrID, MsgAttType, value))

    if MsgAttrID == "0000": Domoticz.Debug("Cluster0702 - 0x0000 CURRENT_SUMMATION_DELIVERED")
    elif MsgAttrID == "0001": Domoticz.Debug("Cluster0702 - 0x0001 CURRENT_SUMMATION_RECEIVED ")
    elif MsgAttrID == "0028": Domoticz.Debug("Cluster0702 - 0x001C PREVIOUS_BLOCK_PERIOD_CONSUMPTION_DELIVERED ")
    elif MsgAttrID == "0256": Domoticz.Debug("Cluster0702 - 0x0100 CURRENT_TIER_1_SUMMATION_DELIVERED")
    elif MsgAttrID == "0512": Domoticz.Debug("Cluster0702 - 0x0200 STATUS")
    elif MsgAttrID == "0768": Domoticz.Debug("Cluster0702 - 0x0300 UNIT_OF_MEASURE")
    elif MsgAttrID == "0769": Domoticz.Debug("Cluster0702 - 0x0301 MULTIPLIER")
    elif MsgAttrID == "0770": Domoticz.Debug("Cluster0702 - 0x0302 SUMMATION_FORMATING")
    elif MsgAttrID == "0774": Domoticz.Debug("Cluster0702 - 0x0306 METERING_DEVICE_TYPE")
    elif MsgAttrID == "1024": Domoticz.Debug("Cluster0702 - 0x0400 INSTANTANEOUS_DEMAND")
    else:
        Domoticz.Debug("ReadCluster - 0x0702 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )
    return


def Cluster0300( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Color Temperature
    Domoticz.Log("ReadCluster - ClusterID=0300 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )

def Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Electrical Measurement Cluster
    Domoticz.Log("ReadCluster - ClusterID=0b04 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )


def Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Magic Cube Xiaomi rotation and Power Meter

    Domoticz.Debug("ReadCluster - ClusterID=000C - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) + " len = " +str(len(MsgClusterData)))
    if MsgAttrID=="0055":
        # Are we receiving Power
        EPforPower = z_tools.getEPforClusterType( self, MsgSrcAddr, "Power" ) 
        EPforMeter = z_tools.getEPforClusterType( self, MsgSrcAddr, "Meter" ) 
        EPforPowerMeter = z_tools.getEPforClusterType( self, MsgSrcAddr, "PowerMeter" ) 
        if len(EPforPower) == len(EPforMeter) == len(EPforPowerMeter) == 0:
            Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube angle: " + str(struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0])  )

        else: # We have several EPs in Power/Meter
            value = round(float(decodeAttribute( MsgAttType, MsgClusterData )),3)
            Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " +str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(value))
            Domoticz.Debug("ReadCluster - ClusterId=000c - List of Power/Meter EPs" +str( EPforPower ) + str(EPforMeter) +str(EPforPowerMeter) )
            for ep in EPforPower + EPforMeter:
                if ep == MsgSrcEp:
                    Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(value) )
                    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
                    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
                    break      # We just need to send once

    elif MsgAttrID=="ff05": # Rotation - horinzontal
        Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

    else:
        Domoticz.Log("ReadCluster - ClusterID=000c - unknown message - SAddr = " + str(MsgSrcAddr) + " EP = " +\
                str( MsgSrcEp) + " MsgAttrID = " + str(MsgAttrID) + " Value = "+ str(MsgClusterData) )


def Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # LevelControl cluster

    Domoticz.Debug("ReadCluster - ClusterId=0008 - Level Control: " + str(MsgClusterData) )
    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
    return

def Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Cluster On/Off

    if MsgAttrID=="0000" or MsgAttrID=="8000":
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
        Domoticz.Debug("ReadCluster - ClusterId=0006 - reception General: On/Off: " + str(MsgClusterData) )

    elif MsgAttrID == "f000" and MsgAttType == "0023" and MsgAttSize == "0004":
        # Nov 01 10:59:43 pi3 domoticz[865]: 2018-11-01 10:59:43.881  (Zigate) ReadCluster - 0006  Saddr: d54c SrcEp : 01 AttrID : f000 AttType : 0023 AttSize : 0004 Attribute : 070000c0
        # Nov 01 10:59:43 pi3 domoticz[865]: 2018-11-01 10:59:43.881  (Zigate) ReadCluster - Feedback from device d54c/01 MsgClusterData: 070000c0 decoded: 117440704

        value = int(decodeAttribute( MsgAttType, MsgClusterData ))
        Domoticz.Log("ReadCluster - Feedback from device " + str(MsgSrcAddr) + "/" + MsgSrcEp + " MsgClusterData: " + MsgClusterData + \
                " decoded: " + str(value) )
    else:
        Domoticz.Error("ReadCluster - ClusterId=0006 - reception heartbeat - Message attribut inconnu: " + MsgAttrID + " / " + MsgData)
    return

def Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Door Lock Cluster

    def decode_vibr(value):         #Decoding XIAOMI Vibration sensor 
        if value == '' or value is None:
            return value
        if   value == "0001": return 'Take'
        elif value == "0002": return 'Tilt'
        elif value == "0003": return 'Drop'
        return ''

    Domoticz.Error("ReadCluster 0101 not fully implemented, please contact us on https://github.com/sasu-drooz/Domoticz-Zigate" )
    Domoticz.Log("ReadCluster 0101 - Dev: " +MsgSrcAddr + " Ep : " + MsgSrcEp + " Attribute : " + MsgAttrID )

    if MsgAttrID == "0000":          # Lockstate
        Domoticz.Log("ReadCluster 0101 - Dev: Lock state " +str(MsgClusterData) )
    elif MsgAttrID == "0001":         # Locktype
        Domoticz.Log("ReadCluster 0101 - Dev: Lock type "  + str(MsgClusterData))
    elif MsgAttrID == "0002":         # Enabled
        Domoticz.Log("ReadCluster 0101 - Dev: Enabled "  + str(MsgClusterData))
    elif MsgAttrID == "0055":         # Movement
        Domoticz.Log("ReadCluster 0101 - Dev: Movement " + decode_vibr( MsgClusterData ) )
    elif MsgAttrID == "0503":         # Rotation
        Domoticz.Log("ReadCluster 0101 - Dev: Rotation "  + str(MsgClusterData))
    elif MsgAttrID == "0505":         # Unknown
        Domoticz.Log("ReadCluster 0101 - Dev: Unknown "  + str(MsgClusterData))


def Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Measurement Umidity Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( MsgAttType, MsgClusterData))/100,1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = value

    #z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
    #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
    Domoticz.Debug("ReadCluster - ClusterId=0405 - reception hum: " + str(int(MsgClusterData,16)/100) )


def Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Temperature Measurement Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( MsgAttType, MsgClusterData))/100,1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
    else:
        Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")


#    if MsgClusterData != "":
#        if MsgClusterData[0] == "f":  # cas temperature negative
#            MsgClusterData=-(int(MsgClusterData,16)^int("FFFF",16))
#            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
#            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
#            Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp: " + str(MsgClusterData/100) )
#        else:
#            MsgClusterData=int(MsgClusterData,16)
#            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
#            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
#            Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp: " + str(MsgClusterData/100) )
#    else: 
#        Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")
#

def Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: Pression atmospherique)

    if MsgAttType == "0028":
        # seems to be a boolean . May be a beacon ...
        return

    value = int(decodeAttribute( MsgAttType, MsgClusterData ))
    Domoticz.Log("Cluster0403 - decoded value: from:%s to %s" %( MsgClusterData, value) )

    if MsgAttrID == "0000": # Atmo in mb
        #value = round((value/100),1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        Domoticz.Log("ReadCluster - ClusterId=0403 - 0000 reception atm: " + str(value ) )

    if MsgAttrID == "0010": # Atmo in 10xmb
        value = round((value/10),1)
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        Domoticz.Log("ReadCluster - ClusterId=0403 - 0010 reception atm: " + str(value ) )
        #
# OLD CODE
#    if MsgAttType=="0028":
#        #z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgClusterData,8))
#        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
#        Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm: NOT DOMOTICZ UPDATE !!!!" + str(MsgClusterData) )
#            
#    if MsgAttType=="0029" and MsgAttrID=="0000":
#        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
#        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
#        Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm: " + str(round(int(MsgClusterData,16),1)))
#            
#    if MsgAttType=="0029" and MsgAttrID=="0010":
#        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/10,1))
#        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/10,1)
#        Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm: " + str(round(int(MsgClusterData,16)/10,1)))


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


def Cluster0012( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Magic Cube Xiaomi
    # Thanks to: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/138#issuecomment-325101635
    #         +---+
    #         | 2 |
    #     +---+---+---+
    #     | 4 | 0 | 1 |
    #     +---+---+---+
    #         | 5 |
    #         +---+
    #         | 3 |
    #         +---+
    #     Side 5 is with the MI logo; side 3 contains the battery door.
    #
    #     Shake: 0x0000 (side on top doesn't matter)
    #     90º Flip from side x on top to side y on top: 0x0040 + (x << 3) + y
    #     180º Flip to side x on top: 0x0080 + x
    #     Push while side x is on top: 0x0100 + x
    #     Double Tap while side x is on top: 0x0200 + x
    #     Push works in any direction.
    #     For Double Tap you really need to lift the cube and tap it on the table twice.
    def cube_decode(value):
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
            Domoticz.Debug("cube action: Not expected value" + value )
        return value

    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
    z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
    Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(MsgClusterData) )
    Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(cube_decode(MsgClusterData)) )



def Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # General Basic Cluster
    # It might be good to make sure that we are on a Xiaomi device - A priori: 0x115f
    if MsgAttrID=="ff01" and self.ListOfDevices[MsgSrcAddr]['Status']=="inDB":  # xiaomi battery lvl
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
            Temp = '%s%s' % (str(sTemp[2:4]),str(sTemp[0:2])) 
            ValueTemp=round(int(Temp,16)/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402']=ValueTemp
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)
#        if sTemp2 != '':
#            Temp2 = '%s%s' % (str(sTemp2[2:4]),str(sTemp2[0:2])) 
#            ValueTemp2=round(int(Temp2,16)/100,1)
#            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Device Temperature : " + str(ValueTemp2) )
        if sHumid != '':
            Humid = '%s%s' % (str(sHumid[2:4]),str(sHumid[0:2])) 
            ValueHumid=round(int(Humid,16)/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0405']=ValueHumid
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity : " + str(ValueHumid) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0405",ValueHumid)
        if sHumid2 != '':
            Humid2 = '%s%s' % (str(sHumid2[2:4]),str(sHumid2[0:2])) 
            ValueHumid2=round(int(Humid2,16)/100,1)
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity2 : " + str(ValueHumid2) )
        if sPress != '':
            Press = '%s%s%s%s' % (str(sPress[6:8]),str(sPress[4:6]),str(sPress[2:4]),str(sPress[0:2])) 
            ValuePress=round((struct.unpack('i',struct.pack('i',int(Press,16)))[0])/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]["0403"]=ValuePress
            Domoticz.Log("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Atmospheric Pressure : " + str(ValuePress) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0403",ValuePress)
        if sOnOff != '':
            sOnOff = sOnOff[0:2]  
            Domoticz.Debug("ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " On/Off : " + str(sOnOff) )
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff


    elif MsgAttrID=="0005":  # Model info
        if MsgClusterData != '':
            modelName = decodeAttribute( MsgAttType, MsgClusterData)
            Domoticz.Log("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device: " + modelName)
            if modelName != '':
                # It has been decoded !
                Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device: " + modelName)
                if z_var.storeDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices:
                    self.DiscoveryDevices[MsgSrcAddr]['Model']=modelName
                if self.ListOfDevices[MsgSrcAddr]['Model'] == '' or self.ListOfDevices[MsgSrcAddr]['Model'] == {}:
                    self.ListOfDevices[MsgSrcAddr]['Model'] = modelName

    elif MsgAttrID == "0000": # ZCL Version
        Domoticz.Debug("ReadCluster - 0x0000 - ZCL Version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
    elif MsgAttrID == "0003": # Hardware version
        Domoticz.Debug("ReadCluster - 0x0000 - Hardware version: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
    elif MsgAttrID == "0004": # Manufacturer
        Domoticz.Debug("ReadCluster - 0x0000 - Manufacturer: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
    elif MsgAttrID == "0007": # Power Source
        Domoticz.Debug("ReadCluster - 0x0000 - Power Source: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
    elif MsgAttrID == "0016": # Battery
        Domoticz.Debug("ReadCluster - 0x0000 - Battery: " +str(decodeAttribute( MsgAttType, MsgClusterData) ))
    else:
        Domoticz.Debug("ReadCluster 0x0000 - Message attribut inconnu: " + str(decodeAttribute( MsgAttType, MsgClusterData) ))
    
