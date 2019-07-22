
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

from Modules.domoticz import MajDomoDevice, lastSeenUpdate
from Modules.tools import DeviceExist, getEPforClusterType, is_hex, loggingCluster
from Modules.output import ReadAttributeRequest_Ack

def retreive4Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+4)]

def retreive8Tag(tag,chain):
    c = str.find(chain,tag) + 4
    if c == 3: return ''
    return chain[c:(c+8)]

def decodeAttribute(self, AttType, Attribute, handleErrors=False):

    if len(Attribute) == 0:
        return
    loggingCluster( self, 'Debug', "decodeAttribute( %s, %s) " %(AttType, Attribute) )

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
            loggingCluster( self, 'Debug', "decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('I',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x25:   # ZigBee_48BitUint
            return str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])
    elif int(AttType,16)  == 0x28: # int8
        return int(Attribute, 16 )
    elif int(AttType,16) == 0x29:   # 16Bitint   -> tested on Measurement clusters
        return str(struct.unpack('h',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x2a:   # ZigBee_24BitInt
        loggingCluster( self, 'Debug', "decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])))
        return str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])
    elif int(AttType,16) == 0x2b:   # 32Bitint
            loggingCluster( self, 'Debug', "decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])))
            return str(struct.unpack('i',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x2d:   # ZigBee_48Bitint
            loggingCluster( self, 'Debug', "decodeAttribut(%s, %s) untested, returning %s " %(AttType, Attribute, \
                                    str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])))
            return str(struct.unpack('q',struct.pack('Q',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x30:  # 8BitEnum
        return int(Attribute,16 )
    elif int(AttType,16)  == 0x31: # 16BitEnum 
        return str(struct.unpack('h',struct.pack('H',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x39:  # Xiaomi Float
        return str(struct.unpack('f',struct.pack('I',int(Attribute,16)))[0])
    elif int(AttType,16) == 0x42:  # CharacterString
        decode = ''
        try:
            decode = binascii.unhexlify(Attribute).decode('utf-8')
        except:
            if handleErrors: # If there is an error we force the result to '' This is used for 0x0000/0x0005
                Domoticz.Log("decodeAttribute - seems errors decoding %s, so returning empty" %str(Attribute))
                decode = ''
            else:
                decode = binascii.unhexlify(Attribute).decode('utf-8', errors = 'ignore')
                loggingCluster( self, 'Debug', "decodeAttribute - seems errors, returning with errors ignore")

        # Cleaning
        decode = decode.strip('\x00')
        decode = decode.strip()
        return decode
    else:
        loggingCluster( self, 'Debug', "decodeAttribut(%s, %s) unknown, returning %s unchanged" %(AttType, Attribute, Attribute) )
        return Attribute

def ReadCluster(self, Devices, MsgData):

    MsgLen=len(MsgData)

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

    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("ReadCluster - unknown device: %s" %(MsgSrcAddr))
        return

    if 'ReadAttributes' in self.ListOfDevices[MsgSrcAddr]:
        if 'Ep' in self.ListOfDevices[MsgSrcAddr]['ReadAttributes']:
            if MsgSrcEp in self.ListOfDevices[MsgSrcAddr]['ReadAttributes']['Ep']:
                if MsgClusterId in self.ListOfDevices[MsgSrcAddr]['ReadAttributes']['Ep'][MsgSrcEp]:
                    self.ListOfDevices[MsgSrcAddr]['ReadAttributes']['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgAttrStatus

    if MsgAttrStatus != "00" and MsgClusterId != '0500':
        loggingCluster( self, 'Debug', "ReadCluster - Status %s for addr: %s/%s on cluster/attribute %s/%s" %(MsgAttrStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID) , nwkid=MsgSrcAddr)
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

    loggingCluster( self, 'Debug', "ReadCluster - %s NwkId: %s Ep: %s AttrId: %s AttyType: %s Attsize: %s Status: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgAttrStatus, MsgClusterData),MsgSrcAddr)

    DECODE_CLUSTER = {
            "0000": Cluster0000,
            "0001": Cluster0001,
            "0005": Cluster0005,
            "0006": Cluster0006,
            "0008": Cluster0008,
            "0012": Cluster0012,
            "000c": Cluster000c,
            "0101": Cluster0101,
            "0102": Cluster0102,
            "0201": Cluster0201,
            "0204": Cluster0204,
            "0300": Cluster0300,
            "0400": Cluster0400,
            "0402": Cluster0402,
            "0403": Cluster0403,
            "0405": Cluster0405,
            "0406": Cluster0406,
            "0500": Cluster0500,
            "0502": Cluster0502,
            "0702": Cluster0702,
            "0b04": Cluster0b04,
            "fc00": Clusterfc00
            }

    if MsgClusterId in DECODE_CLUSTER:
        _func = DECODE_CLUSTER[ MsgClusterId ]
        _func(  self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData )
    else:
        Domoticz.Error("ReadCluster - Error/unknow Cluster Message: " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
        Domoticz.Error("                                 MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
        Domoticz.Error("                                 MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )

def Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # General Basic Cluster
    # It might be good to make sure that we are on a Xiaomi device - A priori: 0x115f

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Log("ReadCluster0000 - receiving a message from unknown device: %s" %MsgSrcAddr)
        return

    if MsgAttrID == "0000": # ZCL Version
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - ZCL Version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['ZCL Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ZCL_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001": # Application Version
        loggingCluster( self, 'Debug', "ReadCluster - Application version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['App_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['App Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0002": # Stack Version
        loggingCluster( self, 'Debug', "ReadCluster - Stack version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Stack Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Stack_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0003": # Hardware version
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - Hardware version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['HW Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['HW_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004": # Manufacturer
        _manufcode = str(decodeAttribute( self, MsgAttType, MsgClusterData))
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - Manufacturer: " + _manufcode, MsgSrcAddr)
        if is_hex(_manufcode):
            self.ListOfDevices[MsgSrcAddr]['Manufacturer'] = _manufcode
        else:
            self.ListOfDevices[MsgSrcAddr]['Manufacturer Name'] = _manufcode

        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Manufacturer']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID=="0005":  # Model info
        if MsgClusterData != '':
            modelName = decodeAttribute( self, MsgAttType, MsgClusterData, handleErrors=True)  # In case there is an error while decoding then return ''
            loggingCluster( self, 'Debug', "ReadCluster - %s / %s - Recepion Model: >%s<" %(MsgClusterId, MsgAttrID, modelName), MsgSrcAddr)
            if modelName != '':

                if 'Ep' in self.ListOfDevices[MsgSrcAddr]:
                    for iterEp in self.ListOfDevices[MsgSrcAddr]['Ep']:
                        if 'ClusterType' in self.ListOfDevices[MsgSrcAddr]['Ep'][iterEp]:
                            loggingCluster( self, 'Debug', "ReadCluster - %s / %s - %s %s is already provisioned in Domoticz" \
                                    %(MsgClusterId, MsgAttrID, MsgSrcAddr, modelName), MsgSrcAddr)
                            return

                if 'Model' in self.ListOfDevices[MsgSrcAddr]:
                    if self.ListOfDevices[MsgSrcAddr]['Model'] == modelName and self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:
                        loggingCluster( self, 'Debug', "ReadCluster - %s / %s - no action" %(MsgClusterId, MsgAttrID), MsgSrcAddr)
                        return
                else:
                    self.ListOfDevices[MsgSrcAddr]['Model'] = {}

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
                    loggingCluster( self, 'Debug', "Extract all info from Model : %s" %self.DeviceConf[modelName], MsgSrcAddr)
                    if 'Type' in self.DeviceConf[modelName]:                                   # If type exist at top level : copy it
                        self.ListOfDevices[MsgSrcAddr]['ConfigSource'] ='DeviceConf'
                        self.ListOfDevices[MsgSrcAddr]['Type']=self.DeviceConf[modelName]['Type']
                        if 'Ep' in self.ListOfDevices[MsgSrcAddr]:
                            loggingCluster( self, 'Debug', "Removing existing received Ep", MsgSrcAddr)
                            del self.ListOfDevices[MsgSrcAddr]['Ep']                           # It has been prepopulated by some 0x8043 message, let's remove them.
                            self.ListOfDevices[MsgSrcAddr]['Ep'] = {}                          # It has been prepopulated by some 0x8043 message, let's remove them.

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
                    loggingCluster( self, 'Debug', "Result based on DeviceConf is: %s" %str(self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

                if self.pluginconf.pluginConf['capturePairingInfos']:
                    if MsgSrcAddr not in self.DiscoveryDevices:
                        self.DiscoveryDevices[MsgSrcAddr] = {}
                    self.DiscoveryDevices[MsgSrcAddr]['Model'] = modelName

    elif MsgAttrID == '0006': # CLD_BAS_ATTR_DATE_CODE
        # 20151006091b090
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_1'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0007": # Power Source
        loggingCluster( self, 'Debug', "ReadCluster - Power Source: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        # 0x03 stand for Battery
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['PowerSource'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0008': # 
        loggingCluster( self, 'Debug', "ReadCluster - Attribute 0008: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)

    elif MsgAttrID == '0009': # 
        loggingCluster( self, 'Debug', "ReadCluster - Attribute 0009: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)

    elif MsgAttrID == '000a': # Product Code
        loggingCluster( self, 'Debug', "ReadCluster - Product Code: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)


    elif MsgAttrID == '0010': # LOCATION_DESCRIPTION
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - Attribut 0010: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Location'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0015': # SW_BUILD_ID
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - Attribut 0015: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_2'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0016": # Battery
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - Attribut 0016 : " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Battery'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Battery0016'] = decodeAttribute( self, MsgAttType, MsgClusterData)
        self.ListOfDevices[MsgSrcAddr]['BatteryUpdateTime'] = int(time.time())

    elif MsgAttrID == "4000": # SW Build
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - Attribut 4000: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_3'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID in ( 'ff0d', 'ff22', 'ff23'): # Xiaomi Code
        loggingCluster( self, 'Debug', "ReadCluster - 0x0000 - %s/%s Attribut %s %s %s %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttrSize, MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID in ( 'ff01', 'ff02'):
        
        if self.ListOfDevices[MsgSrcAddr]['Status'] != "inDB":  # xiaomi battery lvl
            return

        ReadAttributeRequest_Ack(self, MsgSrcAddr)         # Ping Xiaomi devices

        loggingCluster( self, 'Debug', "ReadCluster - %s %s Saddr: %s ClusterData: %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgClusterData), MsgSrcAddr)
        # Taging: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/42#issuecomment-370152404
        # 0x0624 might be the LQI indicator and 0x0521 the RSSI dB

        sBatteryLvl = retreive4Tag( "0121", MsgClusterData )
        stag04 = retreive4Tag( '0424', MsgClusterData )
        stag05 = retreive4Tag( '0521', MsgClusterData )
        stag06 = retreive4Tag( '0620', MsgClusterData )
        sTemp2 =  retreive4Tag( "0328", MsgClusterData )   # Device Temperature
        sOnOff =  retreive4Tag( "6410", MsgClusterData )[0:2]
        sOnOff2 = retreive4Tag( "6420", MsgClusterData )[0:2]    # OnOff for Aqara Bulb
        sTemp =   retreive4Tag( "6429", MsgClusterData )
        sHumid =  retreive4Tag( "6521", MsgClusterData )
        sHumid2 = retreive4Tag( "6529", MsgClusterData )
        sLevel =  retreive4Tag( "6520", MsgClusterData )[0:2]     # Dim level for Aqara Bulb
        stag10 =  retreive4Tag( "6621", MsgClusterData )
        sPress =  retreive8Tag( "662b", MsgClusterData )

        if sBatteryLvl != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '8e':    # Battery Level makes sense for non main powered devices
            voltage = '%s%s' % (str(sBatteryLvl[2:4]),str(sBatteryLvl[0:2]))
            voltage = int(voltage, 16 )
            ValueBattery_old=round(voltage/10/3.3)
            volt_min = 2750; volt_max = 3150

            if voltage > volt_max: ValueBattery = 100
            elif voltage < volt_min: ValueBattery = 0
            else: ValueBattery = 100 - round( ((volt_max - (voltage))/(volt_max - volt_min)) * 100 )

            loggingCluster( self, 'Debug', "ReadCluster - %s/%s Saddr: %s Battery: %s OldValue: %s Voltage: %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, ValueBattery, ValueBattery_old, voltage), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Battery'] = ValueBattery
            self.ListOfDevices[MsgSrcAddr]['BatteryUpdateTime'] = int(time.time())

            # Store Voltage in 0x0001
            if '0001' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001'] = {}
            oldValue = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']).split(";")
            if len(oldValue) != 4:
                oldValue = '0;0;0;0'.split(';')
   
            newValue = '%s;%s;%s;%s' %(voltage, oldValue[0], oldValue[1], oldValue[2])
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001'] = newValue


        if sTemp != '':
            Temp = struct.unpack('h',struct.pack('>H',int(sTemp,16)))[0]
            ValueTemp=round(Temp/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402']=ValueTemp
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) , MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)

        if sHumid != '':
            ValueHumid = struct.unpack('H',struct.pack('>H',int(sHumid,16)))[0]
            ValueHumid = round(ValueHumid/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0405']=ValueHumid
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity : " + str(ValueHumid) , MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0405",ValueHumid)

        if sHumid2 != '':
            Humid2 = struct.unpack('h',struct.pack('>H',int(sHumid2,16)))[0]
            ValueHumid2=round(Humid2/100,1)
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Humidity2 : " + str(ValueHumid2) , MsgSrcAddr)

        if sPress != '':
            Press = '%s%s%s%s' % (str(sPress[6:8]),str(sPress[4:6]),str(sPress[2:4]),str(sPress[0:2])) 
            ValuePress=round((struct.unpack('i',struct.pack('i',int(Press,16)))[0])/100,1)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]["0403"]=ValuePress
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: " + str(MsgSrcAddr) + " Atmospheric Pressure : " + str(ValuePress) , MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0403",ValuePress)

        if sOnOff != '':
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s sOnOff: %s" %(MsgSrcAddr, sOnOff), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff

        if sOnOff2 != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] == '8e': # Aqara Bulb
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s sOnOff2: %s" %(MsgSrcAddr, sOnOff2), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff2
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006',sOnOff2)

        if sLevel != '':
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s sLevel: %s" %(MsgSrcAddr, sLevel), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0008',sLevel)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0008'] = sLevel

        if stag10 != '':
            # f400 --
            # 4602 --
            loggingCluster( self, 'Debug', "ReadCluster - 0000/ff01 Saddr: %s Tag10: %s" %(MsgSrcAddr, stag10), MsgSrcAddr)

    elif MsgAttrID == "fffd": #
        Domoticz.Log("ReadCluster - 0000 %s/%s attribute fffd: %s" %(MsgSrcAddr, MsgSrcEp, str(decodeAttribute( self, MsgAttType, MsgClusterData))))

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 



def Cluster0001( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    oldValue = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]).split(";")
    if len(oldValue) != 4:
        # 1- mainVolt
        # 2- battVolt
        # 3- battRemainVolt
        # 4- battRemainPer
        oldValue = '0;0;0;0'.split(';')

    value = decodeAttribute( self, MsgAttType, MsgClusterData)

    if MsgAttrID == "0000": # Voltage
        value = round(int(value)/10, 1)
        mainVolt = value
        newValue = '%s;%s;%s;%s' %(mainVolt, oldValue[1], oldValue[2], oldValue[3])
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Voltage: %s V " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0001": # MAINS FREQUENCY
                              # 0x00 indicates a DC supply, or Freq too low
                              # 0xFE indicates AC Freq is too high
                              # 0xFF indicates AC Freq cannot be measured
        if int(value) == 0x00:
            Domoticz.Log("readCluster 0001 %s Freq is DC or too  low" %MsgSrcAddr)
        elif int(value) == 0xFE:
            Domoticz.Log("readCluster 0001 %s Freq is too high" %MsgSrcAddr)
        elif int(value) == 0xFF:
            Domoticz.Log("readCluster 0001 %s Freq cannot be measured" %MsgSrcAddr)
        else:
            value = round(int(value)/2)  # 
            Domoticz.Log("readCluster 0001 %s Freq %s Hz" %(MsgSrcAddr, value))

    elif MsgAttrID == "0002": # MAINS ALARM MASK
        _undervoltage = (int(value)) & 1
        _overvoltage = (int(value) >> 1 ) & 1
        _mainpowerlost = (int(value) >> 2 ) & 1
        Domoticz.Log("readCluster 0001 %s Alarm Mask: UnderVoltage: %s OverVoltage: %s MainPowerLost: %s" \
                %(MsgSrcAddr, _undervoltage, _overvoltage, _mainpowerlost))

    elif MsgAttrID == "0010": # Voltage
        battVolt = value
        newValue = '%s;%s;%s;%s' %(oldValue[0], battVolt, oldValue[2], oldValue[3])
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Battery Voltage: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0020": # Battery Voltage
        battRemainVolt = value
        newValue = '%s;%s;%s;%s' %(oldValue[0], oldValue[1], battRemainVolt, oldValue[3])
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Battery: %s V" %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0021": # Battery %
        battRemainPer = value
        newValue = '%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], battRemainPer)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = newValue
        self.ListOfDevices[MsgSrcAddr]['Battery'] = value
        self.ListOfDevices[MsgSrcAddr]['BatteryUpdateTime'] = int(time.time())
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Battery: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0031": # Battery Size
        # 0x03 stand for AA
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Battery size: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0033": # Battery Quantity
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Battery Quantity: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == 'fffd': # Cluster Version
        loggingCluster( self, 'Debug', "readCluster 0001 - %s Cluster Version: %s " %(MsgSrcAddr, value) , MsgSrcAddr)
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0300( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    if MsgAttrID == '0000':
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Current hue: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == '0001':
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Current saturation: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == '0002':
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Remaining time: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == '0003':
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Current X: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == '0004':
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Current Y: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == '0007':
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Color Temp: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == '0008':
        COLOR_MODE = { '00': 'Current hue and current saturation',
                '01': 'Current x and current y',
                '02': 'Color temperature' }
        loggingCluster( self, 'Debug', "readCluster - %s - %s/%s Color Mode: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 


def Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Smart Energy Metering
    if int(MsgAttSize,16) == 0:
        loggingCluster( self, 'Debug', "Cluster0702 - empty message ", MsgSrcAddr)
        return


    value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
    loggingCluster( self, 'Debug', "Cluster0702 - MsgAttrID: %s MsgAttType: %s DataLen: %s Data: %s decodedValue: %s" %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    if MsgAttrID == "0000": 
        loggingCluster( self, 'Debug', "Cluster0702 - 0x0000 CURRENT_SUMMATION_DELIVERED %s " %(value), MsgSrcAddr)
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        #MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
    elif MsgAttrID == "0001":
        loggingCluster( self, 'Debug', "ReadCluster0702 - %s/%s Attribute %s: %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID,value), MsgSrcAddr)

    elif MsgAttrID == "000a":
        loggingCluster( self, 'Debug', "ReadCluster0702 - %s/%s Attribute %s: %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID,value), MsgSrcAddr)

    elif MsgAttrID == "000b":
        loggingCluster( self, 'Debug', "ReadCluster0702 - %s/%s Attribute %s: %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID,value), MsgSrcAddr)

    elif MsgAttrID == "0301":   # Multiplier
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(value)
        loggingCluster( self, 'Debug', "Cluster0702 - Multiplier: %s" %(value), MsgSrcAddr)

    elif MsgAttrID == "0302":   # Divisor
        loggingCluster( self, 'Debug', "Cluster0702 - Divisor: %s" %(value), MsgSrcAddr)

    elif MsgAttrID == "0200": 
        loggingCluster( self, 'Debug', "Cluster0702 - Status: %s" %(value), MsgSrcAddr)


    elif MsgAttrID == "0400": 
        loggingCluster( self, 'Debug', "Cluster0702 - 0x0400 Instant demand %s" %(value), MsgSrcAddr)
        value = round(value/10, 3)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = str(value)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 


def Cluster0300( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    # Color Temperature
    if 'ColorInfos' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['ColorInfos'] ={}

    value = decodeAttribute( self, MsgAttType, MsgClusterData)
    if MsgAttrID == "0000":     # CurrentHue
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Hue'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - CurrentHue: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Hue']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001":   # CurrentSaturation
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Saturation'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - CurrentSaturation: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Saturation']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0002":   
        loggingCluster( self, 'Debug', "ReadCluster0300 - %s/%s RemainingTime: %s" %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)

    elif MsgAttrID == "0003":     # CurrentX
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['X'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - CurrentX: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-X']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004":   # CurrentY
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Y'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - CurrentY: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Y']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0007":   # ColorTemperatureMireds
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorTemperatureMireds'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - ColorTemperatureMireds: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorTemperatureMireds']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0008":   # Color Mode 
                                # 0x00: CurrentHue and CurrentSaturation
                                # 0x01: CurrentX and CurrentY
                                # 0x02: ColorTemperatureMireds
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - Color Mode: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorMode']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '000f':
        loggingCluster( self, 'Debug', "ReadCluster0300 - %s/%s Attribute %s: %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID,value), MsgSrcAddr)

    elif MsgAttrID == '400b':
        loggingCluster( self, 'Debug', "ReadCluster0300 - %s/%s Attribute %s: %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID,value), MsgSrcAddr)

    elif MsgAttrID == '400c':
        loggingCluster( self, 'Debug', "ReadCluster0300 - %s/%s Attribute %s: %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID,value), MsgSrcAddr)


    elif MsgAttrID == "f000":
        # 070000df
        # 00800900
        #self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = value
        loggingCluster( self, 'Debug', "ReadCluster0300 - Color Mode: %s" %value, MsgSrcAddr)
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Electrical Measurement Cluster
    Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 


def Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Magic Cube Xiaomi rotation and Power Meter

    loggingCluster( self, 'Debug', "ReadCluster - ClusterID=000C - MsgSrcEp: %s MsgAttrID: %s MsgClusterData: %s " %(MsgSrcEp, MsgAttrID, MsgClusterData), MsgSrcAddr)
    if MsgAttrID == '0051': #
        loggingCluster( self, 'Debug', "%s/%s Out of service: %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID=="0055":
        # Are we receiving Power
        EPforPower = getEPforClusterType( self, MsgSrcAddr, "Power" ) 
        EPforMeter = getEPforClusterType( self, MsgSrcAddr, "Meter" ) 
        EPforPowerMeter = getEPforClusterType( self, MsgSrcAddr, "PowerMeter" ) 
        loggingCluster( self, 'Debug', "EPforPower: %s, EPforMeter: %s, EPforPowerMeter: %s" %(EPforPower, EPforMeter, EPforPowerMeter), MsgSrcAddr)
       
        if len(EPforPower) == len(EPforMeter) == len(EPforPowerMeter) == 0:
            rotation_angle = struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0]

            loggingCluster( self, 'Debug', "ReadCluster - ClusterId=000c - Magic Cube angle: %s" %rotation_angle, MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(int(rotation_angle)), Attribute_ = '0055' )

            if rotation_angle < 0:
                #anti-clokc
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="90"
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"90")
            if rotation_angle >= 0:
                # Clock
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

        elif len(EPforPower) > 0 or len(EPforMeter) > 0 or len(EPforPowerMeter) > 0 : # We have several EPs in Power/Meter
            value = round(float(decodeAttribute( self, MsgAttType, MsgClusterData )),3)
            loggingCluster( self, 'Debug', "ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " +str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(value), MsgSrcAddr)
            loggingCluster( self, 'Debug', "ReadCluster - ClusterId=000c - List of Power/Meter EPs" +str( EPforPower ) + str(EPforMeter) +str(EPforPowerMeter) , MsgSrcAddr)
            for ep in EPforPower + EPforMeter:
                if ep == MsgSrcEp:
                    loggingCluster( self, 'Debug', "ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(value) , MsgSrcAddr)
                    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = str(value)
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0702',str(value))   # For to Power Cluster
                    break      # We just need to send once
        else:
            Domoticz.Log("ReadCluster 000c - received unknown value - MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
                    %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))
            Domoticz.Log("----------------> EPforPower: %s" %EPforPower)
            Domoticz.Log("----------------> EPforMeter: %s" %EPforMeter)
            Domoticz.Log("----------------> EPforPowerMeter: %s" %EPforPowerMeter)


    elif MsgAttrID=="006f": # Status flag
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s ClusterId=000c - Status flag: %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID=="ff05": # Rotation - horinzontal
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) , MsgSrcAddr)
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
        #MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0005( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Cluster On/Off

    if MsgAttrID in ( "0000" , "8000"):
        if 'Model' in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.ctrl_neutral1':
                # endpoint 02 is for controlling the L1 outpu
                # Blacklist all EPs other than '02'
                if MsgSrcEp != '02':
                    loggingCluster( self, 'Debug', "ReadCluster - ClusterId=%s - Unexpected EP, %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" \
                         %(MsgClusterId, MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
                    return
            if self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.ctrl_neutral2':
                # EP 02 ON/OFF LEFT    -- OK
                # EP 03 ON/ON RIGHT    -- OK
                # EP 04 EVENT LEFT
                # EP 05 EVENT RIGHT
                if MsgSrcEp in ( '05' , '04' ):
                    loggingCluster( self, 'Debug', "ReadCluster - ClusterId=%s - not processed EP, %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" \
                       %(MsgClusterId, MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
                    return

            if self.ListOfDevices[MsgSrcAddr]['Model'] == 'TI0001':
                # Livolo / Might get something else than On/Off
                Domoticz.Log("ReadCluster - ClusterId=0006 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
                         %(MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData

        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0006 - reception General: On/Off: " + str(MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '4000': # Global Scene Control
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0006 - Global Scene Control Attr: %s Value: %s" %(MsgAttrID, MsgClusterData))

    elif MsgAttrID == '4001': # On Time
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0006 - On Time Attr: %s Value: %s" %(MsgAttrID, MsgClusterData))

    elif MsgAttrID == '4002': # Off Wait Time
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0006 - Off Wait Time Attr: %s Value: %s" %(MsgAttrID, MsgClusterData))

    elif MsgAttrID == '4003': # Power On On Off
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" %(MsgAttrID, MsgClusterData))

    elif MsgAttrID == "f000" and MsgAttType == "23" and MsgAttSize == "0004":
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        loggingCluster( self, 'Debug', "ReadCluster - Feedback from device " + str(MsgSrcAddr) + "/" + MsgSrcEp + " MsgClusterData: " + MsgClusterData + \
                " decoded: " + str(value) , MsgSrcAddr)
    elif MsgAttrID == 'fffd':
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0006 - unknown Attr: %s Value: %s" %(MsgAttrID, MsgClusterData))

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # LevelControl cluster

    loggingCluster( self, 'Debug', "ReadCluster - ClusterID: %s Addr: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s"
            %(MsgClusterId, MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgSrcEp == '06': # Most likely Livolo
        Domoticz.Log("ReadCluster - ClusterId=0008 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
                %(MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))
        if self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006'] == '07': # Left
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', MsgClusterData)
        else:    # Assuming RIght
            if value == '01':
                value = '03'
            else:
                value = '0'
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', MsgClusterData)
            return

    if MsgAttrID == '0000': # Current Level
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0008 - Level Control: " + str(MsgClusterData) , MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = MsgClusterData
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

    elif MsgAttrID == 'f000':
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0008 - Attribute f000: " + str(MsgClusterData) , MsgSrcAddr)
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Door Lock Cluster

    def decode_vibr(value):         #Decoding XIAOMI Vibration sensor 
        if value == '' or value is None:
            return value
        if   value == "0001": return '20' # Take/Vibrate/Shake
        elif value == "0002": return '10' # Tilt / we will most-likely receive 0x0503/0x0054 after
        elif value == "0003": return '30' #Drop
        return '00'

    loggingCluster( self, 'Debug', "ReadCluster 0101 - Dev: %s, EP:%s AttrID: %s, AttrType: %s, AttrSize: %s Attribute: %s" \
            %( MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgAttrID == "0000":          # Lockstate
        loggingCluster( self, 'Debug', "ReadCluster 0101 - Dev: Lock state " +str(MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == "0001":         # Locktype
        loggingCluster( self, 'Debug', "ReadCluster 0101 - Dev: Lock type "  + str(MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0002":         # Enabled
        loggingCluster( self, 'Debug', "ReadCluster 0101 - Dev: Enabled "  + str(MsgClusterData), MsgSrcAddr)

    elif MsgAttrID ==  "0055":   # Aqara Vibration
        loggingCluster( self, 'Debug', "ReadCluster %s/%s - Aqara Vibration - Event: %s" %(MsgClusterId, MsgAttrID, MsgClusterData) , MsgSrcAddr)
        # "LevelNames": "Off|Tilt|Vibrate|Free Fall"
        state = decode_vibr( MsgClusterData )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    elif MsgAttrID == "0503":   # Bed activties
        loggingCluster( self, 'Debug', "ReadCluster %s/%s -  Vibration Angle - Attribute: %s" %(MsgClusterId, MsgAttrID, MsgClusterData) , MsgSrcAddr)

        if MsgClusterData == "0054": # Following Tilt
            state = "10"
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    elif MsgAttrID == "0505":   # Vibration Strenght
        loggingCluster( self, 'Debug', "ReadCluster %s/%s -  Vibration Strenght - Attribute: %s" %(MsgClusterId, MsgAttrID, MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == "0508":   # Aqara Vibration / Liberation Mode / Orientation
        x = int(MsgClusterData, 16) & 0xffff
        y = int(MsgClusterData, 16)  >> 16 & 0xffff
        z = int(MsgClusterData, 16)  >> 32 & 0xffff

        if  z+y != 0 and x+z != 0 and x+y != 0:
            from math import atan, sqrt, pi
            x2 = x*x; y2 = y*y; z2 = z*z
            angleX = round( atan(x/sqrt(z2+y2)) * 180 / pi)
            angleY = round( atan(y/sqrt(x2+z2)) * 180 / pi)
            angleZ = round( atan(z/sqrt(x2+y2)) * 180 / pi)

            loggingCluster( self, 'Debug', "ReadCluster %s/%s -  Vibration Orientation - 0x%16x - x=%d, y=%d, z=%d" \
                    %(MsgClusterId, MsgAttrID, int(MsgClusterData,16), x, y, z) , MsgSrcAddr)

        state = "00"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = state

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 
        
def Cluster0102( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Windows Covering / Shutter
    value = decodeAttribute(self, MsgAttType, MsgClusterData)
    loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Attribute: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)


    if MsgAttrID == "0000":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Window Covering Type: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)
        WINDOW_COVERING = { '00': 'Rollershade',
                            '01': 'Rollershade - 2 Motor',
                            '02': 'Rollershade – Exterior',
                            '03': 'Rollershade - Exterior - 2 Motor',
                            '04': 'Drapery',
                            '05': 'Awning',
                            '06': 'Shutter',
                            '07': 'Tilt Blind - Tilt Only',
                            '08': 'Tilt Blind - Lift and Tilt',
                            '09': 'Projector Screen'
                            }

    elif  MsgAttrID == "0001":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Physical close limit lift cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif  MsgAttrID == "0002":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Physical close limit Tilt cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0003":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Curent position Lift in cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0004":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Curent position Tilt in cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0005":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Number of Actuations – Lift: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0006":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Number of Actuations – Tilt: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0007":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Config Status: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0008":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Curent position lift in %: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = value

    elif MsgAttrID == "0009":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Curent position Tilte in %: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0010":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Open limit lift cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0011":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Closed limit lift cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0014":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Velocity lift: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)
        loggingCluster( self, 'Debug', "Velocity", MsgSrcAddr)

    elif MsgAttrID == "0017":
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Windows Covering mode: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 



def Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: LUX)
    # Input on Lux calculation is coming from PhilipsHue / Domoticz integration.

    value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
    if 'Model' in self.ListOfDevices[MsgSrcAddr]:
        if str(self.ListOfDevices[MsgSrcAddr]['Model']).find('lumi.sensor') != -1:
            # In case of Xiaomi, we got direct value
            lux = value
        else:
            lux = int(pow( 10, ((value -1) / 10000.00)))
    loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - LUX Sensor: %s/%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData, lux), MsgSrcAddr)
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(lux))
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(lux)


def Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Temperature Measurement Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( self, MsgAttType, MsgClusterData))/100,1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
    else:
        Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")

def Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: Pression atmospherique)

    if MsgAttType == "0028":
        # seems to be a boolean . May be a beacon ...
        return

    value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
    loggingCluster( self, 'Debug', "Cluster0403 - decoded value: from:%s to %s" %( MsgClusterData, value) , MsgSrcAddr)

    if MsgAttrID == "0000": # Atmo in mb
        #value = round((value/100),1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0403 - 0000 reception atm: " + str(value ) , MsgSrcAddr)

    elif MsgAttrID == "0010": # Atmo in 10xmb
        value = round((value/10),1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=value
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s ClusterId=%s - Scaled value %s: %s " %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0014": # Scale
        loggingCluster( self, 'Debug', "ReadCluster - %s/%s ClusterId=%s - Scale %s: %s " %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData), MsgSrcAddr)

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # Measurement Umidity Cluster

    if MsgClusterData != '':
        value = round(int(decodeAttribute( self, MsgAttType, MsgClusterData))/100,1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = value

    loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0405 - reception hum: " + str(int(MsgClusterData,16)/100) , MsgSrcAddr)

def Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):
    # (Measurement: Occupancy Sensing)

    loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0406 - reception Occupancy Sensor: " + str(MsgClusterData) , MsgSrcAddr)
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData

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
        0x0225: 'standard_warning',
        0xFFFF: 'invalid' }

    loggingCluster( self, 'Debug', "ReadCluster0500 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" \
            %( MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Log("ReadCluster0500 - receiving a message from unknown device: %s" %MsgSrcAddr)
        return

    if 'IAS' not in  self.ListOfDevices[MsgSrcAddr]:
         self.ListOfDevices[MsgSrcAddr]['IAS'] = {}
         self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = {}
         self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneType'] = {}
         self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = {}

    if not isinstance(self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'], dict):
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = {}

    if MsgAttrID == "0000": # ZoneState ( 0x00 Not Enrolled / 0x01 Enrolled )
        if int(MsgClusterData,16) == 0x00:
            loggingCluster( self, 'Debug', "ReadCluster0500 - Device: %s NOT ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = int(MsgClusterData,16)
        elif  int(MsgClusterData,16) == 0x01:
            loggingCluster( self, 'Debug', "ReadCluster0500 - Device: %s ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['IAS']['EnrolledStatus'] = int(MsgClusterData,16)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 5, MsgClusterData)

    elif MsgAttrID == "0001": # ZoneType
        if int(MsgClusterData,16) in ZONE_TYPE:
            loggingCluster( self, 'Debug', "ReadCluster0500 - Device: %s - ZoneType: %s" %(MsgSrcAddr, ZONE_TYPE[int(MsgClusterData,16)]), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneType'] = int(MsgClusterData,16)
        else: 
            loggingCluster( self, 'Debug', "ReadCluster0500 - Device: %s - Unknown ZoneType: %s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 5, MsgClusterData)

    elif MsgAttrID == "0002": # Zone Status
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 5, MsgClusterData)
        if MsgClusterData != '' and MsgAttType == '19':
            alarm1 = int(MsgClusterData,16) & 0b0000000000000001
            alarm2 = (int(MsgClusterData,16) & 0b0000000000000010 ) >> 1
            tamper = (int(MsgClusterData,16) & 0b0000000000000100 ) >> 2
            batter = (int(MsgClusterData,16) & 0b0000000000001000 ) >> 3
            srepor = (int(MsgClusterData,16) & 0b0000000000010000 ) >> 4
            rrepor = (int(MsgClusterData,16) & 0b0000000000100000 ) >> 5
            troubl = (int(MsgClusterData,16) & 0b0000000001000000 ) >> 6
            acmain = (int(MsgClusterData,16) & 0b0000000010000000 ) >> 7
            test   = (int(MsgClusterData,16) & 0b0000000100000000 ) >> 8
            batdef = (int(MsgClusterData,16) & 0b0000001000000000 ) >> 9

            loggingCluster( self, 'Debug', "ReadCluster 0500/0002 - IAS Zone - Device:%s status alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s" \
                    %( MsgSrcAddr, alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef), MsgSrcAddr)

            if 'IAS' in self.ListOfDevices[MsgSrcAddr]:
                if 'ZoneStatus' in self.ListOfDevices[MsgSrcAddr]['IAS']:
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['alarm1'] = alarm1
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['alarm2'] = alarm2
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['tamper'] = tamper
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['battery'] = batter
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['Support Reporting'] = srepor
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['Restore Reporting'] = rrepor
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['trouble'] = troubl
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['acmain'] = acmain
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['test'] = test
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['battdef'] = batdef

            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['GlobalInfos'] = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" \
                    %( alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef)
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['TimeStamp'] = int(time.time())
        else:
            loggingCluster( self, 'Debug', "ReadCluster0500 - Device: %s empty data: %s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0010": # IAS CIE Address
        loggingCluster( self, 'Debug', "ReadCluster0500 - IAS CIE Address: %s" %MsgClusterData, MsgSrcAddr)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 7, MsgClusterData)

    elif MsgAttrID == "0011": # Zone ID
        loggingCluster( self, 'Debug', "ReadCluster0500 - ZoneID : %s" %MsgClusterData, MsgSrcAddr)

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

    loggingCluster( self, 'Debug', "ReadCluster0500 - Device: %s Data: %s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)

    return

def Cluster0502( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    loggingCluster( self, 'Debug', "ReadCluster0502 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" \
            %( MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Log("ReadCluster0502 - receiving a message from unknown device: %s" %MsgSrcAddr)
        return

    if MsgAttrID == "0000": # Max Duration
        loggingCluster( self, 'Debug', "ReadCluster - 0502 - %s/%s Max Duration: %s" \
                %( MsgSrcAddr, MsgSrcEp, str(decodeAttribute( self, MsgAttType, MsgClusterData) )), MsgSrcAddr)
        if 'IAS WD' not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['IAS WD'] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS WD']['MaxDuration'] = decodeAttribute( self, MsgAttType, MsgClusterData)
    elif MsgAttrID == "fffd":
        loggingCluster( self, 'Debug', "ReadCluster - 0502 - %s/%s unknown attribute: %s %s %s %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 
    return

    

def Cluster0012( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    def cube_decode(value):
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

    if self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.remote.b1acn01', \
                                                    'lumi.remote.b186acn01', 'lumi.remote.b286acn01'):
        # 0 -> Hold
        # 1 -> Short Release
        # 2 -> Double press
        # 255 -> Long Release
        value = decodeAttribute( self, MsgAttType, MsgClusterData )
        Domoticz.Log("ReadCluster - ClusterId=0012 - Switch Aqara: EP: %s Value: %s " %(MsgSrcEp,value))
        value = int(value)
        if value == 0: value = 3
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",str(value))    # Force ClusterType Switch in order to behave as 

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.sensor_switch.aq3'):
        value = decodeAttribute( self, MsgAttType, MsgClusterData )
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0012 - Switch Aqara (AQ2): EP: %s Value: %s " %(MsgSrcEp,value), MsgSrcAddr)
        value = int(value)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",str(value))    # Force ClusterType Switch in order to behave as 

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.ctrl_ln2.aq1'):
        value = decodeAttribute( self, MsgAttType, MsgClusterData )
        value = int(value)
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0012 - Switch Aqara lumi.ctrl_ln2.aq1: EP: %s Attr: %s Value: %s " %(MsgSrcEp,MsgAttrID, value), MsgSrcAddr)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.sensor_cube.aqgl01', 'lumi.sensor_cube'):
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(MsgClusterData) , MsgSrcAddr)
        loggingCluster( self, 'Debug', "ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(cube_decode(MsgClusterData)) , MsgSrcAddr)

    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 


def Cluster0201( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    # Thermostat cluster
    oldValue = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]).split(";")
    if len(oldValue) != 6:
        oldValue = '0;0;0;0;0;0'.split(';')

    loggingCluster( self, 'Debug', "ReadCluster 0201 - Addr: %s Ep: %s AttrId: %s AttrType: %s AttSize: %s Data: %s"
            %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    value = decodeAttribute( self, MsgAttType, MsgClusterData)

    if MsgAttrID =='0000':  # Local Temperature (Zint16)
        ValueTemp=round(int(value)/100,1)
        localTemp = ValueTemp
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0402',ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402'] = str(ValueTemp)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(localTemp, oldValue[1], oldValue[2], oldValue[3], oldValue[4],oldValue[5])
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Local Temp: %s" %ValueTemp, MsgSrcAddr)

    elif MsgAttrID == '0001': # Outdoor Temperature
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Outdoor Temp: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0002': # Occupancy
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Occupancy: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0003': # Min Heat Setpoint Limit
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Min Heat Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0004': # Max Heat Setpoint Limit
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Max Heat Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0005': # Min Cool Setpoint Limit
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Min Cool Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0006': # Max Cool Setpoint Limit
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Max Cool Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0007':   #  Pi Cooling Demand  (valve position %)
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Pi Cooling Demand: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0008':   #  Pi Heating Demand  (valve position %)
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Pi Heating Demand: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], value, oldValue[2], oldValue[3], oldValue[4],oldValue[5])

    elif MsgAttrID == '0009':   #  HVAC System Type Config
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s HVAC System Type Config: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0010':   # Calibration / Adjustement
        value = value / 10 
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Calibration: %s" %value, MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], value, oldValue[2], oldValue[3], oldValue[4],oldValue[5])

    elif MsgAttrID == '0011':   # Cooling Setpoint (Zinte16)
        ValueTemp=round(int(value)/100,1)
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Cooling Setpoint: %s" %ValueTemp, MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], ValueTemp, oldValue[3], oldValue[4],oldValue[5])

    elif MsgAttrID == '0012':   # Heat Setpoint (Zinte16)
        ValueTemp=round(int(value)/100,1)
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Heating Setpoint: %s" %ValueTemp, MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], ValueTemp, oldValue[4],oldValue[5])
        if str(self.ListOfDevices[MsgSrcAddr]['Model']).find('SPZB') == -1:
            # In case it is not a Eurotronic, let's Update heatPoint
            loggingCluster( self, 'Debug', "ReadCluster 0201 - Request update on Domoticz", MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], ValueTemp, oldValue[4],oldValue[5])

    elif MsgAttrID == '0014':   # Unoccupied Heating
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Unoccupied Heating:  %s" %value, MsgSrcAddr)

    elif MsgAttrID == '0015':   # MIN_HEAT_SETPOINT_LIMIT
        ValueTemp=round(int(value)/100,1)
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Min SetPoint: %s" %ValueTemp, MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], oldValue[3], ValueTemp, oldValue[5])

    elif MsgAttrID == '0016':   # MAX_HEAT_SETPOINT_LIMIT
        ValueTemp=round(int(value)/100,1)
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Max SetPoint: %s" %ValueTemp, MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], oldValue[3], oldValue[4], ValueTemp)

    elif MsgAttrID == '001b': # Control Sequence Operation
        SEQ_OPERATION = { '00': 'Cooling',
                '01': 'Cooling with reheat',
                '02': 'Heating',
                '03': 'Heating with reheat',
                '04': 'Cooling and heating',
                '05': 'Cooling and heating with reheat'
                }
        loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s Control Sequence Operation: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

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
            loggingCluster( self, 'Debug', "ReadCluster 0201 - System Mode: %s / %s" %(value, SYSTEM_MODE[value]), MsgSrcAddr)
        else:
            loggingCluster( self, 'Debug', "ReadCluster 0201 - Attribute 1C: %s" %value, MsgSrcAddr)


    elif MsgAttrID == '0403':
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Attribute 403: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '0408':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Attribute 408: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '0409':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Attribute 409: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '4000': # TRV Mode for EUROTRONICS
        loggingCluster( self, 'Debug', "ReadCluster 0201 - TRV Mode: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '4001': # Valve position for EUROTRONICS
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Valve position: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '4002': # Erreors for EUROTRONICS
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Status: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '4003': # Current Temperature Set point for EUROTRONICS
        ValueTemp = round(int(value)/100,1)
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Current Temp Set point: %s versus %s " %(ValueTemp, oldValue[3]), MsgSrcAddr)
        if ValueTemp != float(oldValue[3]):
            # Seems that there is a local setpoint
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0201',ValueTemp, Attribute_=MsgAttrID)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s;%s;%s;%s' %(oldValue[0], oldValue[1], oldValue[2], ValueTemp, oldValue[4],oldValue[5])

    elif MsgAttrID == '4008': # Host Flags for EUROTRONICS
        HOST_FLAGS = {
                0x000002:'Display Flipped',
                0x000004:'Boost mode',
                0x000010:'disable off mode',
                0x000020:'enable off mode',
                0x000080:'child lock'
                }
        loggingCluster( self, 'Debug', "ReadCluster 0201 - Host Flags: %s" %value, MsgSrcAddr)

        
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

def Cluster0204( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    loggingCluster( self, 'Debug', "ReadCluster 0204 - Addr: %s Ep: %s AttrId: %s AttrType: %s AttSize: %s Data: %s"
            %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)


    if MsgAttrID == '0001':
        # Lock Mode
        value = decodeAttribute( self, MsgAttType, MsgClusterData)
        Domoticz.Log("ReadCluster 0204 - Lokc Mode: %s" %value)
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 


def Clusterfc00( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ):

    DIMMER_STEP = 1

    loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgAttrID not in ( '0001', '0002', '0003', '0004'):
        Domoticz.Log("ReadCluster - %s - %s/%s unknown MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))
        return

    loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s - reading self.ListOfDevices[%s]['Ep'][%s][%s] = %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId , self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]), MsgSrcAddr)
    prev_Value = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]).split(";")
    if len(prev_Value) != 3:
        prev_Value = '0;80;0'.split(';')
    move = None
    prev_onoffvalue = onoffValue = int(prev_Value[0],16)
    prev_lvlValue = lvlValue = int(prev_Value[1],16)
    prev_duration = duration = int(prev_Value[2],16)

    loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - past OnOff: %s, Lvl: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, onoffValue, lvlValue), MsgSrcAddr)
    if MsgAttrID == '0001': #On button
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - ON Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        onoffValue = 1

    elif MsgAttrID == '0004': # Off  Button
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - OFF Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        onoffValue = 0

    elif MsgAttrID in  ( '0002', '0003' ): # Dim+ / 0002 is +, 0003 is -
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - DIM Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        action = MsgClusterData[2:4]
        duration = MsgClusterData[6:10]
        duration = struct.unpack('H',struct.pack('>H',int(duration,16)))[0]


        if action in ('00'): #Short press
            loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - DIM Action: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, action), MsgSrcAddr)
            onoffValue = 1
            # Short press/Release - Make one step   , we just report the press
            if MsgAttrID == '0002': 
                lvlValue += DIMMER_STEP
            elif MsgAttrID == '0003': 
                lvlValue -= DIMMER_STEP

        elif action in ('01') : # Long press
            delta = duration - prev_duration  # Time press since last message
            onoffValue = 1
            if MsgAttrID == '0002':
                lvlValue += round( delta * DIMMER_STEP)
            elif MsgAttrID == '0003': 
                lvlValue -= round( delta * DIMMER_STEP)

        elif action in ('03') : # Release after Long Press
            loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - DIM Release after %s seconds" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, round(duration/10)), MsgSrcAddr)

        else:
            loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - DIM Action: %s not processed" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, action), MsgSrcAddr)
            return   # No need to update

        # Check if we reach the limits Min and Max
        if lvlValue > 255: lvlValue = 255
        if lvlValue <= 0: lvlValue = 0
        loggingCluster( self, 'Debug', "ReadCluster - %s - %s/%s - Level: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, lvlValue), MsgSrcAddr)
    else:
        Domoticz.Log("readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)) 

    #Update Domo
    sonoffValue = '%02x' %onoffValue
    slvlValue = '%02x' %lvlValue
    sduration = '%02x' %duration
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = '%s;%s;%s' %(sonoffValue, slvlValue, sduration)
    loggingCluster( self, 'Debug', "ReadCluster %s - %s/%s - updating self.ListOfDevices[%s]['Ep'][%s][%s] = %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId , self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]), MsgSrcAddr)

    if prev_onoffvalue != onoffValue:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', sonoffValue)
    if prev_lvlValue != lvlValue:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, slvlValue)
