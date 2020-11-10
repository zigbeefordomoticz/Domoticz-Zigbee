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
#import time
import struct
import json
import queue
import string

from time import time

from Modules.zigateConsts import LEGRAND_REMOTE_SHUTTER, LEGRAND_REMOTE_SWITCHS, LEGRAND_REMOTES, ZONE_TYPE, THERMOSTAT_MODE_2_LEVEL
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import lastSeenUpdate, timedOutDevice
from Modules.tools import DeviceExist, getEPforClusterType, is_hex, voltage2batteryP, checkAttribute, checkAndStoreAttributeValue, \
                        set_status_datastruct, set_timestamp_datastruct, get_isqn_datastruct
from Modules.sqnMgmt import sqn_get_internal_sqn_from_app_sqn, TYPE_APP_ZCL

from Modules.lumi import AqaraOppleDecoding0012, readXiaomiCluster, xiaomi_leave, cube_decode, decode_vibr, decode_vibrAngle, readLumiLock

from Classes.LoggingManagement import LoggingManagement

def decodeAttribute(self, AttType, Attribute, handleErrors=False):

    if len(Attribute) == 0:
        return
    #self.log.logging( "Cluster", 'Debug', "decodeAttribute( %s, %s) " %(AttType, Attribute) )

    if int(AttType,16) == 0x10:    # Boolean
        return Attribute[0:2]

    if int(AttType,16) == 0x18:  # 8Bit bitmap
        return int(Attribute[0:8], 16 )

    if int(AttType,16) == 0x19:  # 16BitBitMap
        return str(int(Attribute[0:4], 16 ))

    if int(AttType,16) == 0x20:  # Uint8 / unsigned char
        return int(Attribute[0:2], 16 )

    if int(AttType,16) == 0x21:   # 16BitUint
        return str(struct.unpack('H',struct.pack('H',int(Attribute[0:4],16)))[0])

    if int(AttType,16) == 0x22:   # ZigBee_24BitUint
        return str(struct.unpack('I',struct.pack('I',int("0"+Attribute,16)))[0])

    if int(AttType,16) == 0x23:   # 32BitUint
        return str(struct.unpack('I',struct.pack('I',int(Attribute[0:8],16)))[0])

    if int(AttType,16) == 0x25:   # ZigBee_48BitUint
        return str(struct.unpack('Q',struct.pack('Q',int(Attribute,16)))[0])

    if int(AttType,16)  == 0x28: # int8
        return int(Attribute, 16 )

    if int(AttType,16) == 0x29:   # 16Bitint   -> tested on Measurement clusters
        return str(struct.unpack('h',struct.pack('H',int(Attribute[0:4],16)))[0])

    if int(AttType,16) == 0x2a:   # ZigBee_24BitInt
        return str(struct.unpack('i',struct.pack('I',int("0"+Attribute,16)))[0])

    if int(AttType,16) == 0x2b:   # 32Bitint
        return str(struct.unpack('i',struct.pack('I',int(Attribute[0:8],16)))[0])

    if int(AttType,16) == 0x2d:   # ZigBee_48Bitint
        return str(struct.unpack('q',struct.pack('Q',int(Attribute,16)))[0])

    if int(AttType,16) == 0x30:  # 8BitEnum
        return int(Attribute[0:2],16 )

    if int(AttType,16)  == 0x31: # 16BitEnum 
        return str(struct.unpack('h',struct.pack('H',int(Attribute[0:4],16)))[0])

    if int(AttType,16) == 0x39:  # Xiaomi Float
        return str(struct.unpack('f',struct.pack('I',int(Attribute,16)))[0])

    if int(AttType,16) == 0x42:  # CharacterString
        decode = ''
        try:
            decode = binascii.unhexlify(Attribute).decode('utf-8')
        except:
            if handleErrors: # If there is an error we force the result to '' This is used for 0x0000/0x0005
                self.log.logging( "Cluster", 'Log', "decodeAttribute - seems errors decoding %s, so returning empty" %str(Attribute))
                decode = ''
            else:
                decode = binascii.unhexlify(Attribute).decode('utf-8', errors = 'ignore')
                decode = decode.replace('\x00', '')
                decode = decode.strip()
                self.log.logging( "Cluster", 'Debug', "decodeAttribute - seems errors, returning with errors ignore From: %s to >%s<" %( str(Attribute), str(decode)))

        # Cleaning
        decode = decode.strip('\x00')
        decode = decode.strip()
        return decode

    #self.log.logging( "Cluster", 'Debug', "decodeAttribut(%s, %s) unknown, returning %s unchanged" %(AttType, Attribute, Attribute) )
    return Attribute

def storeReadAttributeStatus( self, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus ):

    i_sqnFromMessage = sqn_get_internal_sqn_from_app_sqn (self.ZigateComm, MsgSQN, TYPE_APP_ZCL)
    i_sqn_expected = get_isqn_datastruct(self, 'ReadAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID )

    # if MsgType == '8100' and i_sqn_expected and i_sqnFromMessage and i_sqn_expected != i_sqnFromMessage:
    #     Domoticz.Log("+++ SQN Missmatch in ReadCluster %s/%s %s %s i_sqn: %s e_sqn: %s i_esqn: %s " 
    #         %( MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, i_sqn_expected, MsgSQN, i_sqnFromMessage ))

    set_status_datastruct(self, 'ReadAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus )
    set_timestamp_datastruct(self, 'ReadAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, int(time()) )

def ReadCluster(self, Devices, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus, MsgAttType, MsgAttSize, MsgClusterData, Source=None):

    #=len(MsgData)

    #if MsgLen < 24:
    #    Domoticz.Error("ReadCluster - MsgData lenght is too short: " + str(MsgLen) + " out of 24+")
    #    Domoticz.Error("ReadCluster - MsgData: '" +str(MsgData) + "'")
    #    return

    #MsgSQN=MsgData[0:2]
    #MsgSrcAddr=MsgData[2:6]
    #MsgSrcEp=MsgData[6:8]
    #MsgClusterId=MsgData[8:12]
    #MsgAttrID=MsgData[12:16]
    #MsgAttrStatus=MsgData[16:18]
    #MsgAttType=MsgData[18:20]
    #MsgAttSize=MsgData[20:24]
    #MsgClusterData=MsgData[24:len(MsgData)]

    self.statistics._clusterOK += 1

    if MsgSrcAddr not in self.ListOfDevices:
        _context = {
            'MsgClusterId' : str(MsgClusterId),
            'MsgSrcEp' : str(MsgSrcEp),
            'MsgAttrID' : str(MsgAttrID),
            'MsgAttType' : str(MsgAttType),
            'MsgAttSize' : str(MsgAttSize),
            'MsgClusterData' : str(MsgClusterData)
        }
        self.log.logging(  "Cluster", 'Error',"ReadCluster - unknown device: %s" %(MsgSrcAddr),MsgSrcAddr,_context)
        return

    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if not DeviceExist(self, Devices, MsgSrcAddr):
        #Pas sur de moi, mais je vois pas pkoi continuer, pas sur que de mettre a jour un device bancale soit utile
        #Domoticz.Error("ReadCluster - KeyError: MsgData = " + MsgData)
        return

    # Can we receive a Custer while the Device is not yet in the ListOfDevices ??????
    # This looks not possible to me !!!!!!!
    # This could be in the case of Xiaomi sending Cluster 0x0000 before anything is done on the plugin.
    # I would consider this doesn't make sense, and we should simply return a warning, that we receive a message from an unknown device !
    if 'Ep' not in self.ListOfDevices[MsgSrcAddr]:
        return
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]['Ep']:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp] = {}
    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = {}

    self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s AttrId: %s AttrType: %s Attsize: %s Status: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgAttrStatus, MsgClusterData),MsgSrcAddr)

    storeReadAttributeStatus( self, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus )

    if MsgAttrStatus != "00" and MsgClusterId != '0500':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Status %s for addr: %s/%s on cluster/attribute %s/%s" %(MsgAttrStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID) , nwkid=MsgSrcAddr)
        self.statistics._clusterKO += 1
        return

    DECODE_CLUSTER = {
            "0000": Cluster0000, 
            "0001": Cluster0001, 
            "0003": Cluster0003, 
            "0005": Cluster0005, 
            "0006": Cluster0006,
            "0008": Cluster0008,
            "0009": Cluster0009,
            "0012": Cluster0012, 
            "000c": Cluster000c,
            "0100": Cluster0100,
            "0101": Cluster0101, 
            "0102": Cluster0102,
            "0201": Cluster0201, 
            "0202": Cluster0202, 
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
            "fc00": Clusterfc00,
            "000f": Cluster000f,
            "fc01": Clusterfc01,
            "fc21": Clusterfc21,
            "fcc0": Clusterfcc0,
            "fc40": Clusterfc40
            }

    if MsgClusterId in DECODE_CLUSTER:
        _func = DECODE_CLUSTER[ MsgClusterId ]
        _func(  self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, \
            MsgAttType, MsgAttSize, MsgClusterData, Source )
    else:

        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
        _context = {
            'MsgClusterId' : str(MsgClusterId),
            'MsgSrcEp' : str(MsgSrcEp),
            'MsgAttrID' : str(MsgAttrID),
            'MsgAttType' : str(MsgAttType),
            'MsgAttSize' : str(MsgAttSize),
            'MsgClusterData' : str(MsgClusterData)
        }
        self.log.logging( "Cluster", 'Error',"ReadCluster - Error/unknow Cluster Message: " + MsgClusterId + " for Device = " + str(MsgSrcAddr),MsgSrcAddr,_context)

def Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # General Basic Cluster
    # It might be good to make sure that we are on a Xiaomi device - A priori: 0x115f

    # Store the Data, can be ovewrite later
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )

    if MsgAttrID == "0000": # ZCL Version
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - ZCL Version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['ZCL Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ZCL_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001": # Application Version
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Application version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['App Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['App_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0002": # Stack Version
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Stack version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Stack Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Stack_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0003": # Hardware version
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Hardware version: " +str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['HW Version'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['HW_Version']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004": # Manufacturer
        # Check if we have a Null caracter
        idx = 0
        for byt in MsgClusterData:
            if MsgClusterData[idx:idx+2] == '00':
                break
            idx += 2

        _manufcode = str(decodeAttribute( self, MsgAttType, MsgClusterData[0:idx],  handleErrors=True))
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Manufacturer: " + str(_manufcode), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData, handleErrors=True) )
        if is_hex(_manufcode):
            self.ListOfDevices[MsgSrcAddr]['Manufacturer'] = _manufcode
        else:
            self.ListOfDevices[MsgSrcAddr]['Manufacturer Name'] = _manufcode
            if _manufcode == 'Schneider Electric':
                self.ListOfDevices[MsgSrcAddr]['Manufacturer'] = '105e'

        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Manufacturer']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID=="0005" and MsgClusterData != '':  # We receive a Model Name
        # Remove Null Char
        idx = 0
        for byt in MsgClusterData:
            if MsgClusterData[idx:idx+2] == '00':
                break
            idx += 2

        # decode the Attribute
        AttrModelName = decodeAttribute( self, MsgAttType, MsgClusterData[0:idx], handleErrors=True)  # In case there is an error while decoding then return ''

        # Continue Cleanup and remove '/'
        modelName = AttrModelName.replace('/','')

        if modelName  in ('lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01'):
            # Manage the Aqara Bulb mode or not
            if self.pluginconf.pluginConf['AqaraOppleBulbMode']:
                # Overwrite the Confif file
                modelName += '-bulb'
            elif 'Lumi' in self.ListOfDevices[MsgSrcAddr]:
                if 'AqaraOppleBulbMode' in self.ListOfDevices[MsgSrcAddr]['Lumi']:
                    # Case where the Widgets have been already created with Bulbmode,
                    # but the parameter is not on anymore
                    # Overwrite the Confif file
                    modelName += '-bulb'

        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = AttrModelName # We store the original one
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s / %s - Recepion Model: >%s<" %(MsgClusterId, MsgAttrID, modelName), MsgSrcAddr)
        if modelName == '':
            return

        # Check if we have already provisionned this Device. If yes, then we drop this message
        if 'Ep' in self.ListOfDevices[MsgSrcAddr]:
            for iterEp in self.ListOfDevices[MsgSrcAddr]['Ep']:
                if 'ClusterType' in self.ListOfDevices[MsgSrcAddr]['Ep'][iterEp]:
                    self.log.logging( "Cluster", 'Debug', "ReadCluster - %s / %s - %s %s is already provisioned in Domoticz" \
                            %(MsgClusterId, MsgAttrID, MsgSrcAddr, modelName), MsgSrcAddr)
                    return

        # Here the Device is not yet provisionned
        if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['Model'] = {}

        if self.ListOfDevices[MsgSrcAddr]['Model'] == modelName and self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:
            # This looks like a Duplicate, just drop
            self.log.logging( "Cluster", 'Debug', "ReadCluster - %s / %s - no action" %(MsgClusterId, MsgAttrID), MsgSrcAddr)
            return

        if self.ListOfDevices[MsgSrcAddr]['Model'] == '' or self.ListOfDevices[MsgSrcAddr]['Model'] == {}:
            self.ListOfDevices[MsgSrcAddr]['Model'] = modelName
        else:
            # We have already a Model Name known
            # If known in DeviceConf, then we keep that one, 
            # otherwise we take the new one.
            if self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:  
                modelName = self.ListOfDevices[MsgSrcAddr]['Model']
            elif modelName in self.DeviceConf:
                self.ListOfDevices[MsgSrcAddr]['Model'] = modelName

        # Let's see if this model is known in DeviceConf. If so then we will retreive already the Eps
        if self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf:                 # If the model exist in DeviceConf.txt
            modelName = self.ListOfDevices[MsgSrcAddr]['Model']
            self.log.logging( "Cluster", 'Debug', "Extract all info from Model : %s" %self.DeviceConf[modelName], MsgSrcAddr)

            if 'ConfigSource' in self.ListOfDevices[MsgSrcAddr]:
                if self.ListOfDevices[MsgSrcAddr]['ConfigSource'] == 'DeviceConf':
                    self.log.logging( "Cluster", 'Debug', "Not redoing the DeviceConf enrollement", MsgSrcAddr)
                    return

            _BackupEp = None
            if 'Type' in self.DeviceConf[modelName]:                                   # If type exist at top level : copy it
                if 'ConfigSource' not in self.ListOfDevices[MsgSrcAddr]:
                    self.ListOfDevices[MsgSrcAddr]['ConfigSource'] = 'DeviceConf'

                self.ListOfDevices[MsgSrcAddr]['Type'] = self.DeviceConf[modelName]['Type']
                if 'Ep' in self.ListOfDevices[MsgSrcAddr]:
                    self.log.logging( "Cluster", 'Debug', "Removing existing received Ep", MsgSrcAddr)
                    _BackupEp = dict(self.ListOfDevices[MsgSrcAddr]['Ep'])
                    del self.ListOfDevices[MsgSrcAddr]['Ep']                           # It has been prepopulated by some 0x8043 message, let's remove them.
                    self.ListOfDevices[MsgSrcAddr]['Ep'] = {}                          # It has been prepopulated by some 0x8043 message, let's remove them.
                    self.log.logging( "Cluster", 'Debug',"-- Record removed 'Ep' %s" %(self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

            for Ep in self.DeviceConf[modelName]['Ep']:                                # For each Ep in DeviceConf.txt
                if Ep not in self.ListOfDevices[MsgSrcAddr]['Ep']:                     # If this EP doesn't exist in database
                    self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]={}                        # create it.
                    self.log.logging( "Cluster", 'Debug', "-- Create Endpoint %s in record %s" %(Ep, self.ListOfDevices[MsgSrcAddr]['Ep']), MsgSrcAddr)

                for cluster in self.DeviceConf[modelName]['Ep'][Ep]:                   # For each cluster discribe in DeviceConf.txt
                    if cluster not in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]:        # If this cluster doesn't exist in database
                        self.log.logging( "Cluster", 'Debug', "----> Cluster: %s" %cluster, MsgSrcAddr)
                        self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}           # create it.
                        if _BackupEp and Ep in _BackupEp:                              # In case we had data, let's retreive it
                            if cluster in _BackupEp[Ep]:
                                for attr in _BackupEp[Ep][cluster]:
                                    if attr in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]:
                                        if self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster][attr] == '' or self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster][attr] == {}:
                                            self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster][attr] = _BackupEp[Ep][cluster][attr]
                                    else:
                                        self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster][attr] = _BackupEp[Ep][cluster][attr]

                                    self.log.logging( "Cluster", 'Debug', "------> Cluster %s set with Attribute %s" %(cluster, attr), MsgSrcAddr)

                if 'Type' in self.DeviceConf[modelName]['Ep'][Ep]:                     # If type exist at EP level : copy it
                    self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]['Type']=self.DeviceConf[modelName]['Ep'][Ep]['Type']
                if 'ColorMode' in self.DeviceConf[modelName]['Ep'][Ep]:
                    if 'ColorInfos' not in self.ListOfDevices[MsgSrcAddr]:
                        self.ListOfDevices[MsgSrcAddr]['ColorInfos'] ={}
                    if 'ColorMode' in  self.DeviceConf[modelName]['Ep'][Ep]:
                        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = int(self.DeviceConf[modelName]['Ep'][Ep]['ColorMode'])

            self.log.logging( "Cluster", 'Debug', "Result based on DeviceConf is: %s" %str(self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

        if self.pluginconf.pluginConf['capturePairingInfos']:
            if MsgSrcAddr not in self.DiscoveryDevices:
                self.DiscoveryDevices[MsgSrcAddr] = {}
            self.DiscoveryDevices[MsgSrcAddr]['Model'] = modelName

    elif MsgAttrID == '0006': # CLD_BAS_ATTR_DATE_CODE
        # 20151006091b090
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_1'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0007": # Power Source
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Power Source: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        # 0x03 stand for Battery
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['PowerSource'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0008': # 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Attribute 0008: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0009': # 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Attribute 0009: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '000a': # Product Code
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Product Code: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '000b': # 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - Attribute 0x000b: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0010': # LOCATION_DESCRIPTION
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Location: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Location'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0011': # Physical Environment
        self.log.logging( "Cluster", 'debug', "ReadCluster - 0x0000 - Physical Environment: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['PhysicalEnv'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0012': # 
        self.log.logging( "Cluster", 'debug', "ReadCluster - 0x0000 - Attribute 0012: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0013': # 
        self.log.logging( "Cluster", 'debug', "ReadCluster - 0x0000 - Attribute 0013: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '0015': # SW_BUILD_ID
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut 0015: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_2'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0016": # Battery
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut 0016 : %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['Battery'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['Battery0016'] = decodeAttribute( self, MsgAttType, MsgClusterData)
        self.ListOfDevices[MsgSrcAddr]['BatteryUpdateTime'] = int(time())

    elif MsgAttrID == "4000": # SW Build
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut 4000: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_3'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "8000": 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut 8000: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        self.ListOfDevices[MsgSrcAddr]['SWBUILD_3'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "e000": # Schneider Thermostat
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut e000: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "e001": # Schneider Thermostat
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut e001: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "e002": # Schneider Thermostat
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut e002: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "f000": 
        legrand = False
        if 'Manufacturer' in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]['Manufacturer'] == '1021' :
               legrand = True 
        if legrand:
            op_time = int(str(decodeAttribute( self, MsgAttType, MsgClusterData) ))
            dd = op_time // 62400
            op_time = op_time - ( dd * 62400 )
            hh =  op_time  // 3600
            op_time = op_time - ( hh * 3600 )
            mm = op_time // 60
            op_time = op_time - ( mm * 60)
            ss =  op_time 

            self.ListOfDevices[MsgSrcAddr]['Operating Time'] = '%sd %sh %sm %ss' %(dd,hh,mm,ss)
            self.log.logging( "Cluster", 'Debug', "%s/%s ReadCluster - 0x0000 - Operating Time: %sdays %shours %smin %ssec" %(MsgSrcAddr, MsgSrcEp, dd, hh,mm,ss), MsgSrcAddr)
        else:
            self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - Attribut f000: %s" %str(decodeAttribute( self, MsgAttType, MsgClusterData) ), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID in ( 'ff0d', 'ff22', 'ff23'): # Xiaomi Code
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0x0000 - %s/%s Attribut %s %s %s %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == 'ff30': # Xiaomi Locking status
        # 1107xx -> Wrong Key or bad insert
        # 1207xx -> Unlock everything to neutral state
        # 1211xx -> Key in the lock
        # xx is the key number
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s %s Saddr: %s ClusterData: %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgClusterData), MsgSrcAddr)
        readLumiLock( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )

    elif MsgAttrID in ( 'ff01', 'ff02', 'fff0'):
        if self.ListOfDevices[MsgSrcAddr]['Status'] != "inDB":  # 
            #Domoticz.Error("ReadCluster - %s - %s/%s Attribut %s received while device not inDB" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID))
            return

        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s %s Saddr: %s ClusterData: %s" %(MsgClusterId, MsgAttrID, MsgSrcAddr, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgClusterData
        readXiaomiCluster( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )

    elif MsgAttrID in ( 'ffe0', 'ffe1', 'ffe2'):
        # Tuya, Zemismart
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0000 %s/%s attribute Tuya/Zemismat - %s: 0x%s %s" 
                %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData, decodeAttribute( self, MsgAttType, MsgClusterData)), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )


    elif MsgAttrID == "fffd": #
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0000/fffd Addr: %s Cluster Revision:%s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )
        #self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['Cluster Revision'] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " 
                %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

def Cluster0001( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    checkAttribute( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID )

    if MsgAttrID == "0000" and MsgAttType == '00':
        # Xiaomi !!
        value = int(MsgClusterData[2:4]+MsgClusterData[0:2],16)
    else:
        value = decodeAttribute( self, MsgAttType, MsgClusterData)

    if MsgAttrID == "0000":    # Voltage
        value = round(int(value)/10, 1)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s General Voltage: %s V " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0001": # MAINS FREQUENCY
                              # 0x00 indicates a DC supply, or Freq too low
                              # 0xFE indicates AC Freq is too high
                              # 0xFF indicates AC Freq cannot be measured
        if int(value) == 0x00:
            self.log.logging( "Cluster", 'Debug', "readCluster 0001 %s Freq is DC or too  low" %MsgSrcAddr, MsgSrcAddr)
        elif int(value) == 0xFE:
            self.log.logging( "Cluster", 'Debug', "readCluster 0001 %s Freq is too high" %MsgSrcAddr, MsgSrcAddr)
        elif int(value) == 0xFF:
            self.log.logging( "Cluster", 'Debug', "readCluster 0001 %s Freq cannot be measured" %MsgSrcAddr, MsgSrcAddr)
        else:
            value = round(int(value)/2)  # 
            self.log.logging( "Cluster", 'Debug', "readCluster 0001 %s Freq %s Hz" %(MsgSrcAddr, value), MsgSrcAddr)

        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0002": # MAINS ALARM MASK
        _undervoltage = (int(value)) & 1
        _overvoltage = (int(value) >> 1 ) & 1
        _mainpowerlost = (int(value) >> 2 ) & 1
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 %s Alarm Mask: UnderVoltage: %s OverVoltage: %s MainPowerLost: %s" \
                %(MsgSrcAddr, _undervoltage, _overvoltage, _mainpowerlost), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == '0007': # Power Source
        if MsgClusterData == '01':
            if (
                'Model' in self.ListOfDevices[MsgSrcAddr]
                and self.ListOfDevices[MsgSrcAddr]['Model'] != {}
                and self.ListOfDevices[MsgSrcAddr]['Model'] == 'TI0001'
            ):
                return

            self.ListOfDevices[MsgSrcAddr]['PowerSource'] = 'Main'
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0010": # Voltage
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Battery Voltage: %s " %(MsgSrcAddr, value) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

    elif MsgAttrID == "0020": # Battery Voltage
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Battery: %s V" %(MsgSrcAddr, value) , MsgSrcAddr)
        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'EH-ZB-BMS' ):
            value = round( value/10, 1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(value))

    elif MsgAttrID == "0021": # Battery %
        if 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'RC-EM':
            return
        if value == 0xff:
            # Invalid measure 
            self.log.logging( "Cluster", 'Log', "readCluster 0001 - %s invalid Battery Percentage: %s " %(MsgSrcAddr, value) , MsgSrcAddr)
            value = 0

        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Battery Percentage: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0031": # Battery Size
        # 0x03 stand for AA
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Battery size: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0033": # Battery Quantity
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Battery Quantity: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0035": # Battery Alarm Mask 
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Attribut 0035: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == "0036": # Minimum Threshold
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Minimum Threshold: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    elif MsgAttrID == 'fffd': # Cluster Version
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "readCluster 0001 - %s Cluster Version: %s " %(MsgSrcAddr, value) , MsgSrcAddr)

    else:
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    UpdateBatteryAttribute( self, MsgSrcAddr, MsgSrcEp )
    ### End of Cluster0001
    
def UpdateBatteryAttribute( self, MsgSrcAddr, MsgSrcEp ):

    XIAOMI_BATTERY_DEVICES = ( 'lumi.remote.b286opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b686opcn01', 
                               'lumi.remote.b286opcn01-bulb', 'lumi.remote.b486opcn01-bulb', 'lumi.remote.b686opcn01-bulb',
                               'lumi.sen_ill.mgl01')

    BATTERY_200PERCENT = ( "Danalock V3", "V3-BTZB", "SML001" , "RWL021", "SPZB0001", "WarningDevice" , "SmokeSensor-N", "SmokeSensor-EM", 
                           "SMOK_V16", "RH3001" ,"TS0201", "COSensor-N", "COSensor-EM" , "TS0043")
    BATTERY_3VOLTS = ( "lumi.sen_ill.mgl01", "3AFE130104020015", "3AFE140103020000", "3AFE14010402000D", "3AFE170100510001" ) + LEGRAND_REMOTES

    BATTERY_15_VOLTS = ( )
    BATTERY_30_VOLTS = ( "3AFE130104020015", "3AFE140103020000", "3AFE14010402000D", "3AFE170100510001" , "SmokeSensor-EM", "COSensor-EM" ) + LEGRAND_REMOTES
    BATTERY_45_VOLTS = ( 'EH-ZB-RTS' ,)

    BATTERY_BASED_DEVICES = BATTERY_200PERCENT + BATTERY_3VOLTS + BATTERY_15_VOLTS + BATTERY_30_VOLTS + BATTERY_45_VOLTS + XIAOMI_BATTERY_DEVICES
                            
    if self.ListOfDevices[ MsgSrcAddr ]['PowerSource'] == 'Main' or self.ListOfDevices[ MsgSrcAddr]['MacCapa'] in( '84' , '8e'):
        # There is hack to be done here, as they are some devices which are Battery based and are annouced as 0x84 !
        if 'Model' in self.ListOfDevices[MsgSrcAddr]:
            # This should reflect the main voltage.
             # Cleanup Battery in case.
            if self.ListOfDevices[MsgSrcAddr]['Model'] not in BATTERY_BASED_DEVICES:
                self.ListOfDevices[ MsgSrcAddr]['Battery'] = {}
                return

    # Compute Battery %
    mainVolt = battVolt = battRemainingVolt = battRemainPer = None

    if '0000' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']:
        mainVolt = float(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0000'])

    if '0010' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']:
        battVolt = float(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0010'])

    if '0020' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001'] and self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0020'] != {}:
        battRemainingVolt = float(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0020'])

    if '0021' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001'] and self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0021'] != {}:
        battRemainPer = float(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0021'])


    self.log.logging( "Cluster", 'Debug', "readCluster 0001 - Device: %s Model: %s mainVolt:%s , battVolt:%s, battRemainingVolt: %s, battRemainPer:%s " %(MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Model'], mainVolt, battVolt, battRemainingVolt, battRemainPer) , MsgSrcAddr)

    value = None
    # Based on % ( 0x0021 )
    if battRemainPer:
        value = battRemainPer
        if 'Model' in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]['Model'] in BATTERY_200PERCENT:
                value = round(battRemainPer / 2)
        #Domoticz.Log("Value from battRemainingVolt : %s" %value)

    # Based on Remaining Voltage
    elif battRemainingVolt: 
        max_voltage = 30
        min_voltage = 25
        if '0001' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
            if '0036' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']:
                if self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0036'] != {} and self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0036'] != '':
                    battery_voltage_threshold = round(int(str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0001']['0036']))/10)
                    
        if 'Model' in self.ListOfDevices[MsgSrcAddr]:
            #if self.ListOfDevices[MsgSrcAddr]['Model'] in LEGRAND_REMOTES:
            #    max_voltage = 30 
            #    min_voltage = 25

            if self.ListOfDevices[MsgSrcAddr]['Model'] == 'EH-ZB-RTS':
                max_voltage = 3 * 1.5 * 10 #  3 * 1.5v batteries in RTS - value are stored in volts * 10
                min_voltage = 3 * 1 * 10

            elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'EH-ZB-BMS':
                max_voltage = 60
                min_voltage = 30

            elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'EH-ZB-VACT':
                max_voltage = 2 * 1.5
                min_voltage = 2 * 1

        value = voltage2batteryP( battRemainingVolt, max_voltage, min_voltage)
        #Domoticz.Log("Value from battRemainingVolt : %s with %s %s %s" %(value, battRemainingVolt, max_voltage, min_voltage))

    #else:
    #    Domoticz.Log("battRelainingVolt: %s %s, battReainPer: %s %s" %( battRemainingVolt, type(battRemainingVolt),
    #    battRemainingVolt, type(battRemainingVolt) ))

    if value:
       self.log.logging( "Cluster", 'Debug', "readCluster 0001 - Device: %s Model: %s Updating battery %s to %s" 
            %(MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Model'], self.ListOfDevices[MsgSrcAddr]['Battery'], value) , MsgSrcAddr)
       if value != self.ListOfDevices[MsgSrcAddr]['Battery']:
           self.ListOfDevices[MsgSrcAddr]['Battery'] = value
           self.ListOfDevices[MsgSrcAddr]['BatteryUpdateTime'] = int(time())
           self.log.logging( "Cluster", 'Debug', "readCluster 0001 - Device: %s Model: %s Updating battery to %s" %(MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Model'], value) , MsgSrcAddr)

def Cluster0003( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ) )

    if MsgAttrID == '0000': # IdentifyTime Attribute
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Remaining time to identify itself %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, int(MsgClusterData, 16)))

def Cluster0005( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ) )

    if MsgAttrID == '0000': # SceneCount
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Scene Count: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0001': # CurrentScene
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Scene Cuurent Scene: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0002': # CurrentGroup
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/% Scene Current Group: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0003': # SceneVal id
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Scene Valid : %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0004': # NameSupport
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Scene NameSupport: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0005': # LastConfiguredBy
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Scene Last Configured By : %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # Cluster On/Off
     
    if MsgAttrID in ( "0000" , "8000"):
        if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
            return

        if self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.ctrl_neutral1' and MsgSrcEp != '02':
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )

            # endpoint 02 is for controlling the L1 output
            # Blacklist all EPs other than '02'
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=%s - Unexpected EP, %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" \
                    %(MsgClusterId, MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
            return

        if self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.ctrl_neutral2' and MsgSrcEp != '02' and MsgSrcEp != '03':
            # EP 02 ON/OFF LEFT    -- OK
            # EP 03 ON/ON RIGHT    -- OK
            # EP 04 EVENT LEFT
            # EP 05 EVENT RIGHT
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=%s - not processed EP, %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" \
                %(MsgClusterId, MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
            return

        if self.ListOfDevices[MsgSrcAddr]['Model'] == '3AFE170100510001': 
            # Konke Multi Purpose Switch
            value = None
            if MsgClusterData in ( '01', '80'): # Simple Click
                value = '01'
            elif MsgClusterData in ( '02', '81'): # Multiple Click
                value = '02'
            elif MsgClusterData == '82': # Long Click
                value = '03'
            elif MsgClusterData == 'cd': # short reset , a short click on the reset button
                return
            else:
                #Domoticz.Log("Konke Multi Purpose Switch - Unknown Value: %s" %MsgClusterData)
                return
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - Konke Multi Purpose Switch reception General: On/Off: %s" %value , MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
            return

        if self.ListOfDevices[MsgSrcAddr]['Model'] == 'TI0001':
            # Livolo / Might get something else than On/Off
                self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
                        %(MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )

        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - reception General: On/Off: %s" %str(MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '4000': # Global Scene Control
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - Global Scene Control Attr: %s Value: %s" %(MsgAttrID, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    elif MsgAttrID == '4001': # On Time
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - On Time Attr: %s Value: %s" %(MsgAttrID, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    elif MsgAttrID == '4002': # Off Wait Time
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - Off Wait Time Attr: %s Value: %s" %(MsgAttrID, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    elif MsgAttrID == '4003': # Power On On Off
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" %(MsgAttrID, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    elif MsgAttrID == "8001":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" %(MsgAttrID, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    elif MsgAttrID == "8002":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" %(MsgAttrID, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    elif MsgAttrID == "f000" and MsgAttType == "23" and MsgAttSize == "0004":
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

        self.log.logging( "Cluster", 'Debug', "ReadCluster - Feedback from device %s/%s Attribute 0xf000 value: %s-%s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData, value), MsgSrcAddr)
        _Xiaomi_code = MsgClusterData[0:2]
        _Xiaomi_sAddr = MsgClusterData[2:6]
        _Xiaomi_Value = MsgClusterData[6:8]

        XIAOMI_CODE = { 
                '00': 'Remote Aqara Bulb Off',
                '01': 'Power outage',
                '02': 'Power On',
                '03': 'Physical Action',
                '04': '04 (please report to @pipiche)',
                '05': '05 (please report to @pipiche)',
                '06': '06 (please report to @pipiche)',
                '07': 'Command count',
                '0a': 'Pairing',
                '0c': '0c (please report to @pipiche)',
                }

        if _Xiaomi_code in XIAOMI_CODE:
            if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                self.log.logging( "Cluster", 'Debug', "ReadCluster - Xiaomi 0006/f000 - %s %s/%s %s: %s" %(self.ListOfDevices[MsgSrcAddr]['ZDeviceName'],MsgSrcAddr, MsgSrcEp, XIAOMI_CODE[ _Xiaomi_code ], int(_Xiaomi_Value,16)), MsgSrcAddr)
            else:
                self.log.logging( "Cluster", 'Debug', "ReadCluster - Xiaomi 0006/f000 - %s/%s %s: %s" %(MsgSrcAddr, MsgSrcEp, XIAOMI_CODE[ _Xiaomi_code ], int(_Xiaomi_Value,16)), MsgSrcAddr)

        else:
            self.log.logging( "Cluster", 'Debug', "ReadCluster - Xiaomi 0006/f000 - - %s/%s Unknown Xiaomi Code %s raw data: %s (please report to @pipiche)" %(MsgSrcAddr, MsgSrcEp, _Xiaomi_code, MsgClusterData), MsgSrcAddr)


    elif MsgAttrID == 'fffd':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0006 - unknown Attr: %s Value: %s" %(MsgAttrID, MsgClusterData))
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ))

def Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # LevelControl cluster

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)

    self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterID: %s Addr: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s"
            %(MsgClusterId, MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgAttrID == '0000': # Current Level
        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'TI0001' and MsgSrcEp == '06' ): # Livolo switch
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
                %(MsgSrcAddr, MsgSrcEp,MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
            # Do nothing as the Livolo state is given by 0x0100
            return
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s Level Control: %s" %(MsgSrcAddr,MsgSrcEp,MsgClusterData) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

    elif MsgAttrID == '0001': # Remaining Time
        # The RemainingTime attribute represents the time remaining until the current
        # command is complete - it is specified in 1/10ths of a second.
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s Remaining Time: %s" %(MsgSrcAddr,MsgSrcEp,MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '0010': # OnOffTransitionTime
        # The OnOffTransitionTime attribute represents the time taken to move to or from the target level 
        # when On of Off commands are received by an On/Off cluster on the same endpoint. It is specified in 1/10ths of a second.
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s OnOff Transition Time: %s" %(MsgSrcAddr,MsgSrcEp,MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '0011': # OnLevel 
        # The OnLevel attribute determines the value that the CurrentLevel attribute is 
        # set to when the OnOff attribute of an On/Off cluster on the same endpoint is set to On. 
        # If the OnLevel attribute is not implemented, or is set to 0xff, it has no effect. 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s On Level : %s" %(MsgSrcAddr,MsgSrcEp,MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '4000': # 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s Attr: %s Value: %s" %(MsgSrcAddr,MsgSrcEp,MsgAttrID,MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == 'f000':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0008 - %s/%s Attr: %s Value: %s" %(MsgSrcAddr,MsgSrcEp,MsgAttrID,MsgClusterData) , MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute( self, MsgAttType, MsgClusterData) )

def Cluster0009( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)
    self.log.logging( "Cluster", 'Log', "ReadCluster 0101 - Dev: %s, EP:%s AttrID: %s, AttrType: %s, AttrSize: %s Attribute: %s Len: %s" \
            %( MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, len(MsgClusterData)), MsgSrcAddr)

def Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # Magic Cube Xiaomi rotation and Power Meter

    self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterID=000C - MsgSrcEp: %s MsgAttrID: %s MsgAttType: %s MsgClusterData: %s " %(MsgSrcEp, MsgAttrID, MsgAttType, MsgClusterData), MsgSrcAddr)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ) )

    if MsgAttrID == '0051': #
        self.log.logging( "Cluster", 'Debug', "%s/%s Out of service: %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgClusterData

    elif MsgAttrID=="0055":
        # Are we receiving Power
        EPforPower = getEPforClusterType( self, MsgSrcAddr, "Power" ) 
        EPforMeter = getEPforClusterType( self, MsgSrcAddr, "Meter" ) 
        EPforPowerMeter = getEPforClusterType( self, MsgSrcAddr, "PowerMeter" ) 
        self.log.logging( "Cluster", 'Debug', "EPforPower: %s, EPforMeter: %s, EPforPowerMeter: %s" %(EPforPower, EPforMeter, EPforPowerMeter), MsgSrcAddr)
       
        if len(EPforPower) == len(EPforMeter) == len(EPforPowerMeter) == 0:
            rotation_angle = struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0]
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=000c - Magic Cube angle: %s" %rotation_angle, MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(int(rotation_angle)), Attribute_ = '0055' )
            if rotation_angle < 0:
                #anti-clokc
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = '90'
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"90")
            if rotation_angle >= 0:
                # Clock
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = '80'
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

        elif len(EPforPower) > 0 or len(EPforMeter) > 0 or len(EPforPowerMeter) > 0 : # We have several EPs in Power/Meter
            value = round(float(decodeAttribute( self, MsgAttType, MsgClusterData )),3)
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " +str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(value), MsgSrcAddr)
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=000c - List of Power/Meter EPs" +str( EPforPower ) + str(EPforMeter) +str(EPforPowerMeter) , MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(value)
            for ep in EPforPower + EPforMeter:
                if ep == MsgSrcEp:
                    self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(value) , MsgSrcAddr)
                    if '0702' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
                        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0702'] = {}
                    if not isinstance( self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0702'], dict):
                        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0702'] = {}
                    if '0400' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0702']:
                        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0702']['0400'] = {}
                    
                    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0702']['0400'] = str(value)
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0702',str(value))   # For to Power Cluster
                    break      # We just need to send once
        else:
            self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID=="006f": # Status flag
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s/%s ClusterId=000c - Status flag: %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgClusterData

    elif MsgAttrID=="ff05": # Rotation - horinzontal
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) , MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgClusterData

    else:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = MsgClusterData
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster000f( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # Binary Input ( Basic )
    # Chapter 19 Input and Output Clusters https://www.nxp.com/docs/en/user-guide/JN-UG-3115.pdf

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    if MsgAttrID == '0051':
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Out of Service: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        if MsgClusterData == '00':
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['Out of Service'] = False
        elif MsgClusterData == '01':
            timedOutDevice( self, Devices, NwkId=MsgSrcEp)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['Out of Service'] = True

    elif MsgAttrID == '0055':
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Present Value: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

        if MsgClusterData == '00': 
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['Active State'] = False
        elif MsgClusterData == '01': 
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['Active State'] = True

        if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
            self.log.logging( "Cluster", 'Log', "Legrand unknown Model %s Value: %s" %(self.ListOfDevices[MsgSrcAddr]['Model'], MsgClusterData), MsgSrcAddr)
            return
            
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Model: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, self.ListOfDevices[MsgSrcAddr]['Model']), MsgSrcAddr)
        if self.ListOfDevices[MsgSrcAddr]['Model'] != {}:
            if self.ListOfDevices[MsgSrcAddr]['Model'] in LEGRAND_REMOTE_SWITCHS:
                self.log.logging( "Cluster", 'Debug', "Legrand remote Switch Present Value: %s" %MsgClusterData, MsgSrcAddr)
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', MsgClusterData)

            elif self.ListOfDevices[MsgSrcAddr]['Model'] in LEGRAND_REMOTE_SHUTTER:
                if MsgClusterData == '01':
                    value = '%02x' %100
                else:
                    value = '%02x' %0
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0102', value)

            elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'Shutter switch with neutral' ):
                # The Shutter should have the Led on its right
                # Present Value: 0x01 -> Open
                # Present Value: 0x00 -> Closed
                self.log.logging( "Cluster", 'Debug', "---->Legrand Shutter switch with neutral Present Value: %s" %MsgClusterData, MsgSrcAddr)
                if MsgClusterData == '01':
                    value = '%02x' %100
                else:
                    value = '%02x' %0

                if 'SWBUILD_3' in self.ListOfDevices[MsgSrcAddr]:
                    if int(self.ListOfDevices[MsgSrcAddr]['SWBUILD_3'],16) >= 0x01a:
                        # Do not use Present Value anymore
                        self.log.logging( "Cluster",  'Debug', "ReadCluster - %s - %s/%s - SWBUILD_3: %0X do not report present value %s"
                            %(MsgAttrID, MsgSrcAddr, MsgSrcEp, int(self.ListOfDevices[MsgSrcAddr]['SWBUILD_3'],16), value), MsgSrcAddr)
                        return

                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0102', value)

            elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'Dimmer switch wo neutral' ):
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', MsgClusterData)

            elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'Micromodule switch'):
                # Useless information. It is given the state of the micromodule button. 01 when click, 00 when release
                pass

            else:
                _context = {
                    'MsgClusterId' : str(MsgClusterId),
                    'MsgSrcEp' : str(MsgSrcEp),
                    'MsgAttrID' : str(MsgAttrID),
                    'MsgAttType' : str(MsgAttType),
                    'MsgAttSize' : str(MsgAttSize),
                    'MsgClusterData' : str(MsgClusterData)
                }
                self.log.logging( "Cluster", 'Error', "Legrand unknown device %s Value: %s" %(self.ListOfDevices[MsgSrcAddr]['Model'], MsgClusterData), MsgSrcAddr,_context)

    elif MsgAttrID == '006f':
        STATUS_FLAGS = {
                '00': 'In Alarm',
                '01': 'Fault',
                '02': 'Overridden',
                '03': 'Out Of service'
                }
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Status Flag: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        if MsgClusterData in STATUS_FLAGS:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['Status'] = STATUS_FLAGS[MsgClusterData]
            if MsgClusterData != '00':
                Domoticz.Status("Device %s/%s Status flag: %s %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData, STATUS_FLAGS[MsgClusterData]))
            else:
                self.log.logging( "Cluster", 'Debug', "Device %s/%s Status flag: %s %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData, STATUS_FLAGS[MsgClusterData]))

        else:
            Domoticz.Status("Device %s/%s Status flag: %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterData))

    elif MsgAttrID == 'fffd':
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0012( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    _modelName = self.ListOfDevices[MsgSrcAddr]['Model']

    self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s - MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s Model: %s"
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, _modelName), MsgSrcAddr)

    # Hanlding Message from the Aqara Opple Switch 2,4,6 buttons
    if _modelName in ('lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01'):    
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
        AqaraOppleDecoding0012(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif _modelName in ( 'lumi.remote.b1acn01', 'lumi.remote.b186acn01', 'lumi.remote.b186acn02', 'lumi.remote.b286acn01', 'lumi.remote.b286acn02'):
        # 0 -> Hold
        # 1 -> Short Release
        # 2 -> Double press
        # 255 -> Long Release
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        self.log.logging( "Cluster", 'Debug',"ReadCluster - ClusterId=0012 - Switch Aqara: EP: %s Value: %s " %(MsgSrcEp,value), MsgSrcAddr)
        if value == 0: 
            value = 3

        # Force ClusterType Switch in order to behave as Switch
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",str(value))    
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,'0006', '0000',  value )

    elif _modelName in ( 'lumi.sensor_switch.aq3', 'lumi.sensor_switch.aq3'):
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0012 - Switch Aqara (AQ2): EP: %s Value: %s " %(MsgSrcEp,value), MsgSrcAddr)
 
         # Store the value in Cluster 0x0006 (as well)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",str(value))
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp, '0006', '0000',  value )
 
    elif _modelName in ( 'lumi.ctrl_ln2.aq1', ):
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0012 - Switch Aqara lumi.ctrl_ln2.aq1: EP: %s Attr: %s Value: %s " %(MsgSrcEp,MsgAttrID, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif _modelName in ( 'lumi.sensor_cube.aqgl01', 'lumi.sensor_cube'):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, cube_decode(self, MsgClusterData, MsgSrcAddr) )

        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  cube_decode(self, MsgClusterData, MsgSrcAddr) )
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(cube_decode(self, MsgClusterData, MsgSrcAddr)) , MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s Model: %s" 
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, _modelName), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

        
def Cluster0100( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)
    
    if MsgAttrID == "0000":
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0100 - Shade Config: PhysicalClosedLimit: %s" %MsgClusterData, MsgSrcAddr)
    elif MsgAttrID == "0001":
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0100 - Shade Config: MotorStepSize: %s" %MsgClusterData, MsgSrcAddr)
    elif MsgAttrID == "0002":
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0100 - Shade Config: Status: %s" %MsgClusterData, MsgSrcAddr)
    elif MsgAttrID == "0010":
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0100 - Shade Config: ClosedLimit: %s" %MsgClusterData, MsgSrcAddr)
    elif MsgAttrID == "0011":
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0100 - Shade Config: Mode: %s" %MsgClusterData, MsgSrcAddr)
    else:
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    
    # Door Lock Cluster
    self.log.logging( "Cluster", 'Debug', "ReadCluster 0101 - Dev: %s, EP:%s AttrID: %s, AttrType: %s, AttrSize: %s Attribute: %s Len: %s" \
            %( MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, len(MsgClusterData)), MsgSrcAddr)

    if MsgAttrID == "0000":          # Lockstate
        LOCKSTATE = {
            '00': 'Not fully locked',
            '01': 'Locked',
            '02': 'Unlocked',
            'ff': 'Undefined'
        }

        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)
        if MsgClusterData == '01':
            # Locked
            if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                self.log.logging( "Cluster", 'Status', "%s DoorLock state %s (%s)" %(self.ListOfDevices[ MsgSrcAddr ]['ZDeviceName'], MsgClusterData, LOCKSTATE[ MsgClusterData ]) , MsgSrcAddr)

            # Update the DoorLock widget seems to be inverted 
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, '00' )
            # Update the Door contact widget ( status )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0500', '00' )

        elif MsgClusterData in ( '00', '02', 'ff' ):
            # Not locked
            if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                self.log.logging( "Cluster", 'Status', "%s DoorLock state %s (%s)" %(self.ListOfDevices[ MsgSrcAddr ]['ZDeviceName'], MsgClusterData, LOCKSTATE[ MsgClusterData ]) , MsgSrcAddr)

            # Update the DoorLock widget seems to be inverted 
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, '01' )
            # Update the Door contact widget
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0500', '01' )

        else:
            _context = {
                'MsgClusterId' : str(MsgClusterId),
                'MsgSrcEp' : str(MsgSrcEp),
                'MsgAttrID' : str(MsgAttrID),
                'MsgAttType' : str(MsgAttType),
                'MsgAttSize' : str(MsgAttSize),
                'MsgClusterData' : str(MsgClusterData)
            }
            self.log.logging( "Cluster", 'Error', "ReadCluster 0101 - %s/%s Dev: Lock state %s " %(MsgSrcAddr, MsgSrcEp, MsgClusterData) , MsgSrcAddr,_context)
        

    elif MsgAttrID == "0001":         # Locktype
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0101 - Dev: Lock type "  + str(MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)

    elif MsgAttrID == "0002":         # Enabled
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0101 - Dev: Enabled "  + str(MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)

    # Aqara related
    elif MsgAttrID ==  "0055":   # Aqara Vibration: Vibration, Tilt, Drop
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s/%s - Aqara Vibration - Event: %s" %(MsgClusterId, MsgAttrID, MsgClusterData) , MsgSrcAddr)
        state = decode_vibr( MsgClusterData )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,state)

    elif MsgAttrID == "0503":   # Bed activties: Tilt angle
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s/%s -  Vibration Angle: %s" %(MsgClusterId, MsgAttrID, MsgClusterData) , MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData)

        if MsgClusterData == "0054": # Following Tilt
            state = "10"
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state )
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, state)

    elif MsgAttrID == "0505":   # Vibration Strenght
        # The vibration sensor has a function in the mihome app called "vibration curve" 
        # with which I get a graph where I can see the value of "Strenght" as a function of time
        value = int(MsgClusterData, 16)
        strenght = ( value >> 16 ) & 0xffff
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s/%s -  Vibration Strenght: %s %s %s" %(MsgClusterId, MsgAttrID, MsgClusterData, value, strenght) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, 'Strenght', str(strenght), Attribute_=MsgAttrID)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,strenght)

    elif MsgAttrID == "0508":   # Aqara Vibration / Liberation Mode / Orientation

        if len(MsgClusterData) != 12:
            # https://github.com/fairecasoimeme/ZiGate/issues/229
            Domoticz.Log("Needs Firmware 3.1b to decode this data")

        angleX, angleY, angleZ = decode_vibrAngle( MsgClusterData)

        self.log.logging( "Cluster", 'Debug', " ReadCluster %s/%s - AttrType: %s AttrLenght: %s AttrData: %s Vibration ==> angleX: %s angleY: %s angleZ: %s" \
                %(MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, angleX, angleY, angleZ), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, 'Orientation', 'angleX: %s, angleY: %s, angleZ: %s' %(angleX, angleY, angleZ) , Attribute_=MsgAttrID)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,'angleX: %s, angleY: %s, angleZ: %s' %(angleX, angleY, angleZ) )
        
    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,MsgClusterData)


def Cluster0102( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # Windows Covering / Shutter

    value = decodeAttribute(self, MsgAttType, MsgClusterData)
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value)

    self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Attribute: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    if MsgAttrID == "0000":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Window Covering Type: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)
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
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Physical close limit lift cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif  MsgAttrID == "0002":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Physical close limit Tilt cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0003":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Curent position Lift in cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0004":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Curent position Tilt in cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0005":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Number of Actuations – Lift: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0006":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Number of Actuations – Tilt: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0007":
        # 00000001 - 0-Not Operational, 1-Operational
        # 00000010 - 0-Not Online, 1-Online
        # 00000100 - 0-Commands are normal, 1-Open/Up Commands reserverd
        # 00001000 - 0-Lift control is Open Loop, 1-Lift control is Closed Loop
        # 00010000 - 0-Titl control is Open Loop, 1-Tilt control is Closed Loop
        # 00100000 - 0-Timer Controlled, 1-Encoder Controlled
        # 01000000 - 0-Timer Controlled, 1-Encoder Controlled
        # 10000000 - Reserved
        self.log.logging( "Cluster", self, 'Debug', "ReadCluster - %s - %s/%s - Config Status: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0008":
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0x%s - %s - %s/%s - Current position lift in %%: %s, Type: %s, Size: %s Data: %s-%s" 
            %(Source, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

        if 'SWBUILD_3' in self.ListOfDevices[MsgSrcAddr]:
            self.log.logging( "Cluster",  'Debug', "ReadCluster - %s - %s/%s - SWBUILD_3: %0X" 
                %(MsgAttrID, MsgSrcAddr, MsgSrcEp, int(self.ListOfDevices[MsgSrcAddr]['SWBUILD_3'],16)), MsgSrcAddr)

        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] != {} ):

            self.log.logging( "Cluster",  'Debug', "ReadCluster - %s - %s/%s - Model: %s" 
                %(MsgAttrID, MsgSrcAddr, MsgSrcEp, self.ListOfDevices[MsgSrcAddr]['Model']), MsgSrcAddr)
    
            if self.ListOfDevices[MsgSrcAddr]['Model'] == 'TS0302' and value == 50:
                # Zemismart Blind shutter switch send 50 went the swicth is on wait mode
                # do not update
                return

            if   self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'TS0302', '1GANGSHUTTER1'):
                value = 0 if value > 100 else 100 - value

            elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'Shutter switch with neutral':
                # The Shutter should have the Led on its right
                # Value: 100 -> Closed
                # Value: 0   -> Open
                # Value: 50  -> Stopped
                pass

        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Shutter switch with neutral After correction value: %s" 
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)

        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "%02x" %value )

    elif MsgAttrID == "0009":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Curent position Tilte in %%: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0010":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Open limit lift cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0011":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Closed limit lift cm: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "0014":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Velocity lift: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)
        self.log.logging( "Cluster", 'Debug', "Velocity", MsgSrcAddr)

    elif MsgAttrID == "0017":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Windows Covering mode: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    elif MsgAttrID == "fffd":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - AttributeID: %s, Type: %s, Size: %s Data: %s-%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0201( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    
    # Thermostat cluster
    self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - %s/%s AttrId: %s AttrType: %s AttSize: %s Data: %s"
            %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    value = decodeAttribute( self, MsgAttType, MsgClusterData)

    if MsgAttrID =='0000':  # Local Temperature (Zint16)
        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'VOC_Sensor' ):
            return
        ValueTemp=round(int(value)/100,2)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0402',ValueTemp)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  ValueTemp )
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,'0402', '0000',  ValueTemp )
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Local Temp: %s" %ValueTemp, MsgSrcAddr)

    elif MsgAttrID == '0001': # Outdoor Temperature
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Outdoor Temp: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0002': # Occupancy
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Occupancy: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0003': # Min Heat Setpoint Limit
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Min Heat Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0004': # Max Heat Setpoint Limit
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Max Heat Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0005': # Min Cool Setpoint Limit
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Min Cool Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0006': # Max Cool Setpoint Limit
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Max Cool Setpoint Limit: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0007':   #  Pi Cooling Demand  (valve position %)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Pi Cooling Demand: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0008':   #  Pi Heating Demand  (valve position %)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Pi Heating Demand: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0009':   #  HVAC System Type Config
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s HVAC System Type Config: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '0010':   # Calibration / Adjustement
        value = value / 10 
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Calibration: %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0011':   # Cooling Setpoint (Zinte16)
        ValueTemp=round(int(value)/100,1)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Cooling Setpoint: %s" %ValueTemp, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  ValueTemp )

    elif MsgAttrID == '0012':   # Heat Setpoint (Zinte16)
        ValueTemp = round(int(value)/100,2)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Heating Setpoint: %s ==> %s" %(value, ValueTemp), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  int(value) )

        if 'Model' in self.ListOfDevices[MsgSrcAddr]:

            if self.ListOfDevices[MsgSrcAddr]['Model'] == 'AC201A':
                # We do not report this, as AC201 rely on 0xffad cluster
                pass
            elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'EH-ZB-VACT':
                # In case of Schneider Wiser Valve, we have to 
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - ValueTemp: %s" %int( ((ValueTemp * 100) * 2) / 2 ), MsgSrcAddr)
                if 'Schneider' in self.ListOfDevices[MsgSrcAddr]:
                    if 'Target SetPoint' in self.ListOfDevices[MsgSrcAddr]['Schneider']:
                        if self.ListOfDevices[MsgSrcAddr]['Schneider']['Target SetPoint'] == int( ((ValueTemp * 100) * 2) / 2 ):
                            # Existing Target equal Local Setpoint in Device
                            self.ListOfDevices[MsgSrcAddr]['Schneider']['Target SetPoint'] = None
                            self.ListOfDevices[MsgSrcAddr]['Schneider']['TimeStamp SetPoint'] = None
                            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp,Attribute_=MsgAttrID)

                        elif self.ListOfDevices[MsgSrcAddr]['Schneider']['Target SetPoint'] is None:
                            # Target is None
                            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp,Attribute_=MsgAttrID)
                    else:
                        # No Target Setpoint, so we assumed Setpoint has been updated manualy.
                        self.ListOfDevices[MsgSrcAddr]['Schneider']['Target SetPoint'] = None
                        self.ListOfDevices[MsgSrcAddr]['Schneider']['TimeStamp SetPoint'] = None
                        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp,Attribute_=MsgAttrID)
                else:
                    # No Schneider section, so we assumed Setpoint has been updated manualy.
                    self.ListOfDevices[MsgSrcAddr]['Schneider'] = {}
                    self.ListOfDevices[MsgSrcAddr]['Schneider']['Target SetPoint'] = None
                    self.ListOfDevices[MsgSrcAddr]['Schneider']['TimeStamp SetPoint'] = None
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp,Attribute_=MsgAttrID)

            elif self.ListOfDevices[MsgSrcAddr]['Model'] != 'SPZB0001':
                # In case it is not a Eurotronic, let's Update heatPoint
                # As Eurotronics will rely on 0x4003 attributes
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Request update on Domoticz %s not a Schneider, not a Eurotronics" %MsgSrcAddr, MsgSrcAddr)
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,ValueTemp,Attribute_=MsgAttrID)
                                

    elif MsgAttrID == '0014':   # Unoccupied Heating
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Unoccupied Heating:  %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0015':   # MIN_HEAT_SETPOINT_LIMIT
        ValueTemp=round(int(value)/100,1)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Min SetPoint: %s" %ValueTemp, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  ValueTemp )

    elif MsgAttrID == '0016':   # MAX_HEAT_SETPOINT_LIMIT
        ValueTemp=round(int(value)/100,1)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Max SetPoint: %s" %ValueTemp, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  ValueTemp )

    elif MsgAttrID == '001a': # Remote Sensing
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Remote Sensing: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0025':   # Scheduler state
        # Bit #0 => disable/enable Scheduler
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Scheduler state:  %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0029':   # Heating operation state
        # bit #0 heat On/Off state
        # bit #1 cool on/off state
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Heating operation state:  %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '001b': # Control Sequence Operation
        SEQ_OPERATION = { '00': 'Cooling',
                '01': 'Cooling with reheat',
                '02': 'Heating',
                '03': 'Heating with reheat',
                '04': 'Cooling and heating',
                '05': 'Cooling and heating with reheat'
                }
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Control Sequence Operation: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    elif MsgAttrID == '001c':
        if int(value) in THERMOSTAT_MODE_2_LEVEL:
            self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - System Mode: %s / %s" %(value, THERMOSTAT_MODE_2_LEVEL[value]), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value, Attribute_=MsgAttrID )
        else:
            self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Attribute 1C: %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '001d':

        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Alarm Mask: %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0403':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Attribute 403: %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0405':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Attribute 405 ( thermostat mode ?=regulator mode For Elko) : %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0406':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Attribute 406 : %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0408':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Attribute 408 ( Elko power consumption in last 10 minutes): %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID == '0409':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - Attribute 409: %s" %value, MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID in ( '4000', '4001', '4002', '4003', '4008' ):

        eurotronics = False
        if (
            'Manufacturer' in self.ListOfDevices[MsgSrcAddr]
            and self.ListOfDevices[MsgSrcAddr]['Manufacturer'] == '1037'
        ):
            eurotronics = True
        if (
            'Manufacturer Name' in self.ListOfDevices[MsgSrcAddr]
            and self.ListOfDevices[MsgSrcAddr]['Manufacturer Name']
            == 'Eurotronic'
        ):
            eurotronics = True

        if eurotronics:
            # Eurotronic SPZB Specifics
            if MsgAttrID == '4000': # TRV Mode for EUROTRONICS
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - %s/%s TRV Mode: %s" %(MsgSrcAddr, MsgSrcEp,value), MsgSrcAddr)
                checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

            elif MsgAttrID == '4001': # Valve position for EUROTRONICS
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - %s/%s Valve position: %s" %(MsgSrcAddr, MsgSrcEp,value), MsgSrcAddr)
                checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

            elif MsgAttrID == '4002': # Erreors for EUROTRONICS
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - %s/%s Status: %s" %(MsgSrcAddr, MsgSrcEp,value), MsgSrcAddr)
                checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

            elif MsgAttrID == '4003': # Current Temperature Set point for EUROTRONICS
                setPoint = ValueTemp = round(int(value)/100,2)
                if '0012' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]:
                    setPoint = self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['0012']
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - %s/%s Current Temp Set point: %s versus %s " %(MsgSrcAddr, MsgSrcEp,ValueTemp, setPoint), MsgSrcAddr)
                if ValueTemp != float(setPoint):
                    # Seems that there is a local setpoint
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0201',ValueTemp, Attribute_=MsgAttrID)
                    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  ValueTemp )
                    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, '0012',  ValueTemp )

            elif MsgAttrID == '4008': # Host Flags for EUROTRONICS
                HOST_FLAGS = {
                        0x000002:'Display Flipped',
                        0x000004:'Boost mode',
                        0x000010:'disable off mode',
                        0x000020:'enable off mode',
                        0x000080:'child lock'
                        }
                self.log.logging( "Cluster", 'Debug', "ReadCluster - 0201 - %s/%s Host Flags: %s" %(MsgSrcAddr, MsgSrcEp,value), MsgSrcAddr)
                checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    elif MsgAttrID in ( 'e010', 'e011', 'e012', 'e013', 'e014', 'e030', 'e031', 'e020'):
        if MsgAttrID == 'e010': # Schneider Thermostat Mode
            THERMOSTAT_MODE = { '00': 'Mode Off', '01': 'Manual',
                '02': 'Schedule', '03': 'Energy Saver',
                '04': 'Schedule Ebergy Saver', '05': 'Holiday Off',
                '06': 'Holiday Frost Protection', }

            if MsgClusterData in THERMOSTAT_MODE:
                self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider Thermostat Mode %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, THERMOSTAT_MODE[MsgClusterData]), MsgSrcAddr)
            else:
                self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider Thermostat Mode 0xe010 %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0201',MsgClusterData, Attribute_=MsgAttrID)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

        elif MsgAttrID == 'e011':  # hact mode : fip or conventional and heating mode : fip or setpoint 
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_HACT_CONFIG  %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0201',MsgClusterData, Attribute_=MsgAttrID)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

        elif MsgAttrID == 'e012':  # 57362, ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_STATUS
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_STATUS  %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0500',MsgClusterData )

        elif MsgAttrID == 'e013': # 57363, ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD  %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
        elif MsgAttrID == 'e014': # 57364, ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_INTERVAL
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_INTERVAL  %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

        elif MsgAttrID == 'e020': # fip mode
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider FIP mode  %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0201',MsgClusterData, Attribute_=MsgAttrID)

        elif MsgAttrID == 'e030': 
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider Valve Position  %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
        elif MsgAttrID == 'e031':
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider Valve Calibration Status %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    else:
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

        
def Cluster0202( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source ):
    
    # Thermostat cluster
    self.log.logging( "Cluster", 'Debug', "ReadCluster - 0202 - %s/%s AttrId: %s AttrType: %s AttSize: %s Data: %s"
            %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    value = decodeAttribute( self, MsgAttType, MsgClusterData)
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  value )

    if MsgAttrID =='0000':  # Fan Mode
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgAttrID, value)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0202 - Fan Mode: %s" %value, MsgSrcAddr)

    elif MsgAttrID == '0001': # Fan Mode Sequence
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s Fan Mode Sequenec: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)


def Cluster0204( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    self.log.logging( "Cluster", 'Debug', "ReadCluster 0204 - Addr: %s Ep: %s AttrId: %s AttrType: %s AttSize: %s Data: %s"
            %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    if MsgAttrID == '0000':
        # TemperatureDisplayMode
        if MsgClusterData == '00':
            self.log.logging( "Cluster", 'Debug', "ReadCluster %s/%s 0204 - Temperature Display Mode : %s --> °C" %( MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)
        elif MsgClusterData == '01':
            self.log.logging( "Cluster", 'Debug', "ReadCluster %s/%s 0204 - Temperature Display Mode : %s -->  °F" %( MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == '0001':
        # Keypad Lock Mode
        KEYPAD_LOCK = {
            '00': 'no lockout'
        }
        value = decodeAttribute( self, MsgAttType, MsgClusterData)
        self.log.logging( "Cluster", 'Debug', "ReadCluster 0204 - Lock Mode: %s" %value, MsgSrcAddr)
    else:
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)


def Cluster0300( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData) ) )
  
    # Color Temperature
    if 'ColorInfos' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['ColorInfos'] ={}

    value = decodeAttribute( self, MsgAttType, MsgClusterData)
    if MsgAttrID == "0000":     # CurrentHue
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Hue'] = value
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - CurrentHue: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Hue']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0001":   # CurrentSaturation
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Saturation'] = value
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - CurrentSaturation: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Saturation']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0002":   
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - %s/%s RemainingTime: %s" %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)

    elif MsgAttrID == "0003":     # CurrentX
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['X'] = value
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - CurrentX: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-X']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0004":   # CurrentY
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['Y'] = value
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - CurrentY: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-Y']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0007":   # ColorTemperatureMireds
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorTemperatureMireds'] = value
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - ColorTemperatureMireds: %s" %value, MsgSrcAddr)
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorTemperatureMireds']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == "0008":   # Color Mode 
        COLOR_MODE = { '00': 'Current hue and current saturation',
                '01': 'Current x and current y',
                '02': 'Color temperature' }

        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Color Mode: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
        self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = value
        if self.pluginconf.pluginConf['capturePairingInfos'] == 1 and MsgSrcAddr in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr]['ColorInfos-ColorMode']=str(decodeAttribute( self, MsgAttType, MsgClusterData) )

    elif MsgAttrID == '000f':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    elif MsgAttrID == "f000":
        # 070000df
        # 00800900
        #self.ListOfDevices[MsgSrcAddr]['ColorInfos']['ColorMode'] = value
        self.log.logging( "Cluster", 'Debug', "ReadCluster0300 - Color Mode: %s" %value, MsgSrcAddr)

    # Seems to be Hue related
    elif MsgAttrID == '0010':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '001a':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '0032':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '0033':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '0034':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '0036':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '0037':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '4001':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '400a':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '400b':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '400c':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '400d':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 
    elif MsgAttrID == '4010':
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr) 

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # (Measurement: LUX)
    # Input on Lux calculation is coming from PhilipsHue / Domoticz integration.

    value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
    lux = int(pow( 10, ((value -1) / 10000.00)))
    if 'Model' in self.ListOfDevices[MsgSrcAddr]:
        if str(self.ListOfDevices[MsgSrcAddr]['Model']).find('lumi.sensor') != -1:
            # In case of Xiaomi, we got direct value
            lux = value
        else:
            lux = int(pow( 10, ((value -1) / 10000.00)))
    self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - LUX Sensor: %s/%s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData, lux), MsgSrcAddr)

    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(lux))
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, lux)

def Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # Temperature Measurement Cluster
    # The possible values are used as follows:
    #   0x0000 to 0x7FFF represent positive temperatures from 0°C to 327.67ºC
    #   0x8000 indicates that the temperature measurement is invalid
    #   0x8001 to 0x954C are unused values
    #   0x954D to 0xFFFF represent negative temperatures from -273.15°C to -1°C 

    # For VOC_Sensor from Nexturn, it uses Cluster 0x0402 to provide, Humidity, CO2 and VOC infos.
    #     Temperature: 0x0000
    #     Humidity: 0x0001
    #     Carbon Dioxide: 0x0002
    #     VOC (Volatile Organic Compounds): 0x0003

    if MsgAttrID == '0000' and MsgClusterData != '':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        
        if value > 0x7FFF and  value < 0x954D:
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Invalid Temperature Measurement: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        else:
            value = round(value/100,1)
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Temperature Measurement: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
            
    elif MsgAttrID == '0001':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute 0x0001: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'VOC_Sensor' ):
            # Humidity
            #Domoticz.Log("Update VOC Sensor Humidity: %s" %value)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0405', value // 100 , Attribute_ = MsgAttrID)

    elif MsgAttrID == '0002':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute 0x0002: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'VOC_Sensor' ):
            # ECO2
            #Domoticz.Log("Update VOC Sensor ECO2: %s" %value)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value ,  Attribute_ = MsgAttrID)

    elif MsgAttrID == '0003':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Attribute 0x0003: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        if ( 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'VOC_Sensor' ):
            # VOC
            #Domoticz.Log("Update VOC Sensor VOC: %s" %value)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value,  Attribute_ = MsgAttrID)

    else:
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
        self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # (Measurement: Pression atmospherique)

    if MsgAttType == "0028":
        # seems to be a boolean . May be a beacon ...
        return

    value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
    self.log.logging( "Cluster", 'Debug', "Cluster0403 - decoded value: from:%s to %s" %( MsgClusterData, value) , MsgSrcAddr)

    if MsgAttrID == "0000": # Atmo in mb
        #value = round((value/100),1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0403 - 0000 reception atm: " + str(value ) , MsgSrcAddr)

    elif MsgAttrID == "0010": # Atmo in 10xmb
        value = round((value/10),1)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,value)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s/%s ClusterId=%s - Scaled value %s: %s " %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0014": # Scale
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s/%s ClusterId=%s - Scale %s: %s " %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData), MsgSrcAddr)

    else:
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # Measurement Umidity Cluster
    # u16MeasuredValue is a mandatory attribute representing the measured relatively humidity as a percentage in steps of 0.01%, 
    # as follows:u16MeasuredValue = 100 x relative humidity percentageSo, 
    # for example, 0x197C represents a relative humidity measurement of 65.24%. 
    # The possible values are used as follows:
    #   0x0000 to 0x2710 represent relative humidities from 0% to 100%
    #   0x2711 to 0xFFFE are unused values
    #   0xFFFF indicates an invalid measure

    if MsgAttrID == '0000' and MsgClusterData != '':
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData))
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        if value > 0x2710:
            self.log.logging( "Cluster", 'Log', "ReadCluster - ClusterId=0405 - Invalid hum: %s - %s" %(int(MsgClusterData,16),value) , MsgSrcAddr)
        else:
            value = round(value/100,1)
            self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0405 - reception hum: %s - %s" %(int(MsgClusterData,16),value) , MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = value
    else:
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    # (Measurement: Occupancy Sensing)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )

    if MsgAttrID == '0000':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0406 - reception Occupancy Sensor: " + str(MsgClusterData) , MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)

    elif MsgAttrID == '0001':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - NwkId: %s Ep: %s AttrId: %s AttyType: %s Attsize: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),MsgSrcAddr)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0406 - Sensor Type: " + str(MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '0010':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - NwkId: %s Ep: %s AttrId: %s AttyType: %s Attsize: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),MsgSrcAddr)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0406 - Occupied to UnOccupied delay: " + str(MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '0011':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - NwkId: %s Ep: %s AttrId: %s AttyType: %s Attsize: %s AttrValue: %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),MsgSrcAddr)
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0406 - UnOccupied to Occupied delay: " + str(MsgClusterData) , MsgSrcAddr)

    elif MsgAttrID == '0030':
        self.log.logging( "Cluster", 'Debug', "ReadCluster - ClusterId=0406 - Attribut 0030: " + str(MsgClusterData) , MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " 
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0500( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    ''' 
    Cluster: Security & Safety IAZ Zone
    https://www.nxp.com/docs/en/user-guide/JN-UG-3077.pdf ( section 26.2 )
    '''
    if MsgClusterData == '':
        return

    self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" \
            %( MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, MsgClusterData )

    if 'IAS' not in  self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['IAS'] = {}

    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]['IAS']:
        self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['EnrolledStatus'] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneType'] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneTypeName'] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus'] = {}

    if not isinstance(self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus'], dict):
        self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus'] = {}

    if MsgAttrID == "0000": # ZoneState ( 0x00 Not Enrolled / 0x01 Enrolled )
        if int(MsgClusterData,16) == 0x00:
            self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Device: %s NOT ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['EnrolledStatus'] = int(MsgClusterData,16)
        elif  int(MsgClusterData,16) == 0x01:
            self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Device: %s ENROLLED (0x%02d)" %(MsgSrcAddr,  int(MsgClusterData,16)), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['EnrolledStatus'] = int(MsgClusterData,16)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, MsgSrcEp, 5, MsgClusterData)

    elif MsgAttrID == "0001": # ZoneType
        if int(MsgClusterData,16) in ZONE_TYPE:
            self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Device: %s - ZoneType: %s" %(MsgSrcAddr, ZONE_TYPE[int(MsgClusterData,16)]), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneType'] = int(MsgClusterData,16)
            self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneTypeName'] = ZONE_TYPE[int(MsgClusterData,16)]
        else: 

            self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Device: %s - Unknown ZoneType: %s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, MsgSrcEp, 5, MsgClusterData)

    elif MsgAttrID == "0002": # Zone Status
        #self.iaszonemgt.receiveIASmessages( MsgSrcAddr, MsgSrcEp,  5, MsgClusterData)     #Not needed for enrollment procedure
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

            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = \
                    'alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s' \
                    %(alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef)
            self.log.logging( "Cluster", 'Debug', "ReadCluster 0500/0002 - IAS Zone - Device:%s status alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s" \
                    %( MsgSrcAddr, alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef), MsgSrcAddr)

            if ( 'IAS' in self.ListOfDevices[MsgSrcAddr] and 
                    MsgSrcEp in self.ListOfDevices[MsgSrcAddr]['IAS'] and 
                    'ZoneStatus' in self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp] ):
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['alarm1'] = alarm1
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['alarm2'] = alarm2
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['tamper'] = tamper
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['battery'] = batter
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['Support Reporting'] = srepor
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['Restore Reporting'] = rrepor
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['trouble'] = troubl
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['acmain'] = acmain
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['test'] = test
                self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['battdef'] = batdef

            self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['GlobalInfos'] = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" \
                    %( alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef)
            self.ListOfDevices[MsgSrcAddr]['IAS'][MsgSrcEp]['ZoneStatus']['TimeStamp'] = int(time())
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, '%02d' %( alarm1 or alarm2) )
            
        else:
            self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Device: %s empty data: %s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0010": # IAS CIE Address
        self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - IAS CIE Address: %s" %MsgClusterData, MsgSrcAddr)
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, MsgSrcEp, 7, MsgClusterData)

    elif MsgAttrID == "0011": # Zone ID
        self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - ZoneID : %s" %MsgClusterData, MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    self.log.logging( "Cluster", 'Debug', "ReadCluster0500 - Device: %s Data: %s" %(MsgSrcAddr, MsgClusterData), MsgSrcAddr)

def Cluster0502( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    self.log.logging( "Cluster", 'Debug', "ReadCluster0502 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" \
            %( MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(decodeAttribute( self, MsgAttType, MsgClusterData)) )

    if MsgAttrID == "0000": # Max Duration
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0502 - %s/%s Max Duration: %s" \
                %( MsgSrcAddr, MsgSrcEp, str(decodeAttribute( self, MsgAttType, MsgClusterData) )), MsgSrcAddr)
        if 'IAS WD' not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['IAS WD'] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS WD']['MaxDuration'] = decodeAttribute( self, MsgAttType, MsgClusterData)

    elif MsgAttrID == "fffd":
        self.log.logging( "Cluster", 'Debug', "ReadCluster - 0502 - %s/%s unknown attribute: %s %s %s %s" %(MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

def Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    
    def compute_conso( self, MsgSrcAddr, raw_value ):

        conso = raw_value # Raw value
        if '0302' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]:
            diviser = self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['0302']
            value = round( conso / ( diviser / 1000 ),3)
            self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s Instant demand %s, div: %s --> %s Watts" %( MsgAttrID, conso, diviser, value))
        elif '0301' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]:
            multiplier = self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['0301']
            value = round( conso * multiplier, 3)
            self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s Instant demand %s, multiply: %s --> %s Watts" %( MsgAttrID, conso, multiplier, value))
        else:
            # Old fashion
            value = round(conso/10, 3)
            if 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'EH-ZB-SPD-V2':
                    value = round(conso, 3)
            if 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'TS0121':
                    value = conso*10

        return ( value )


    # Smart Energy Metering
    if int(MsgAttSize,16) == 0:
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - empty message ", MsgSrcAddr)
        return
    
    checkAttribute( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID )
    
    # Convert to int
    value = decodeAttribute( self, MsgAttType, MsgClusterData )
    try:
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))

    except:
        _context = {
            'MsgClusterId' : str(MsgClusterId),
            'MsgSrcEp' : str(MsgSrcEp),
            'MsgAttrID' : str(MsgAttrID),
            'MsgAttType' : str(MsgAttType),
            'MsgAttSize' : str(MsgAttSize),
            'MsgClusterData' : str(MsgClusterData)
            }
        self.log.logging( "Cluster", 'Error',"Cluster0702 - %s/%s unable to decode %s, MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" 
                %(MsgSrcAddr, MsgSrcEp, value, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),MsgSrcAddr,_context)
        value = 0

    self.log.logging( "Cluster", 'Debug', "Cluster0702 - MsgAttrID: %s MsgAttType: %s DataLen: %s Data: %s decodedValue: %s" %(MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr)

    if MsgAttrID == "0000": # CurrentSummationDelivered
        conso = compute_conso( self,  MsgSrcAddr, value)
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - 0x0000 CURRENT_SUMMATION_DELIVERED Value: %s Conso: %s " %(value, conso), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, conso )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(conso), Attribute_='0000' )

    elif MsgAttrID == "0001": #CURRENT_SUMMATION_RECEIVED
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - CURRENT_SUMMATION_RECEIVED %s " %(value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0002": #Current Max Demand Delivered
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Max Demand Delivered %s " %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "000a": #ATTR_DEFAULT_UPDATE_PERIOD
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - ATTR_DEFAULT_UPDATE_PERIOD %s " %(value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "000b": #FAST_POLL_UPDATE_PERIOD
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - FAST_POLL_UPDATE_PERIOD %s " %(value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0200": 
        METERING_STATUS = { 0: 'Ok',
                1: 'Low Battery',
                2: 'Tamper Detect',
                3: 'Power Failure',
                4: 'Power Quality',
                5: 'Lead Detect'
                }

        if value in METERING_STATUS:
            value = METERING_STATUS[value]

        self.log.logging( "Cluster", 'Debug', "Cluster0702 - Status: %s" %(value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0300":   # Unit of Measure
        MEASURE_UNITS = { 0: 'kW',
                1: 'm³',
                2: 'ft³',
                3: 'ccf'
                }

        if value in MEASURE_UNITS:
            value = MEASURE_UNITS[value]

        self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Unit of Measure: %s" %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0301":   # Multiplier
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Multiplier: %s" %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0302":   # Divisor
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Divisor: %s" %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0303":   # "Summation Formatting
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Summation Formatting: %s" %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0306":   # Device Type
        MEASURE_DEVICE_TYPE = { 0: "Electric Metering",
                1: "Gas Metering",
                2: "Water Metering",
                3: "Thermal Metering",
                4: "Pressure Metering",
                5: "Heat Metering",
                6: "Cooling Metering" }

        if value in MEASURE_DEVICE_TYPE:
            value = MEASURE_DEVICE_TYPE[value]

        self.log.logging( "Cluster", 'Debug', "Cluster0702 - Divisor: %s" %(value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID == "0400": 
        # InstantDemand will be transfer to Domoticz in Watts
        conso = compute_conso( self, MsgSrcAddr, value )

        self.log.logging( "Cluster", 'Debug', "Cluster0702 - 0x0400 Instant demand raw_value: %s Conso: %s" %(value, conso), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(conso))
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(conso) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(conso)

    elif MsgAttrID == "0430":
        # ZBEE_ZCL_ATTR_ID_MET_CUR_WEEK_CON_DEL Attribute Reported by INNR SP 120 Plug ( DataType: 0x27)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, str(value) )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = str(value)

    elif MsgAttrID == '0801':
        self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Electricty Alarm Mask: %s " %(MsgSrcAddr, MsgSrcEp, value), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

    elif MsgAttrID in ( '5000', '5001', '5101', '5121', '5500', '5501', '5601', '5622', '5a20', '5a22' ):
        ELECTRICAL_MEASURES = { '5000': 'electricCurrentMultiplier',
                '5001': 'electricCurrentDivisor',
                '5121': 'maxCurrentBeforeAlarm',
                'e200': 'ctStatusRegister',
                'e201': 'ctPowerConfiguration',
                'e202': 'ctCalibrationMultiplier'
                }

        if MsgAttrID in ELECTRICAL_MEASURES:
            self.log.logging( "Cluster", 'Debug', "Cluster0702 - %s/%s Schneider %s : %s " %(MsgSrcAddr, MsgSrcEp, ELECTRICAL_MEASURES[MsgAttrID], value), MsgSrcAddr)
            checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )
        else:
            self.log.logging( "Cluster", 'Debug', "readCluster - %s - %s/%s Schneider Attribute: %s  Raw Data: %s Decoded Data: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData, value), MsgSrcAddr)
    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, value )

def Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):
    
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgAttrID == "050b": # Active Power
        if -32768 <= int(MsgClusterData[0:4],16) <= 32767:
            value = int(decodeAttribute( self, MsgAttType, MsgClusterData[0:4] ))
            self.log.logging( "Cluster",  'Debug', "ReadCluster %s - %s/%s Power %s" \
                %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value))
            if 'Model' in self.ListOfDevices[ MsgSrcAddr ] and self.ListOfDevices[ MsgSrcAddr ]['Model'] == 'outletv4':
                value /= 10
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(value))
        else:
           self.log.logging( "Cluster",  'Error', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s Out of Range!!" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0505": # RMS Voltage
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Voltage %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value))
        if 'Model' in self.ListOfDevices[ MsgSrcAddr ] and self.ListOfDevices[ MsgSrcAddr ]['Model'] == 'outletv4':
            value /= 10
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0001", str(value))

    elif MsgAttrID == "0508": #RMSCurrent
        value = int(decodeAttribute( self, MsgAttType, MsgClusterData ))
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Current %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, value))
        value /= 100
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(value), Attribute_=MsgAttrID)


    else:
        self.log.logging( "Cluster", 'Log', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

# Cluster Manufacturer specifics
def Clusterfc00( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    DIMMER_STEP = 1

    self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgAttrID not in ( '0001', '0002', '0003', '0004'):
        _context = {
            'MsgClusterId' : str(MsgClusterId),
            'MsgSrcEp' : str(MsgSrcEp),
            'MsgAttrID' : str(MsgAttrID),
            'MsgAttType' : str(MsgAttType),
            'MsgAttSize' : str(MsgAttSize),
            'MsgClusterData' : str(MsgClusterData)
        }
        self.log.logging( "Cluster", 'Error', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr,_context)
        return

    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s - reading self.ListOfDevices[%s]['Ep'][%s][%s][%s] = %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId , MsgAttrID,  self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]), MsgSrcAddr)

    if '0000' in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]:
        prev_Value = str(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]['0000']).split(";")
        if len(prev_Value) == 3:
            for val in prev_Value:
                if not is_hex( val ):
                    prev_Value = '0;80;0'.split(';')
                    break

        else:
            prev_Value = '0;80;0'.split(';')
            
    else:
       prev_Value = '0;80;0'.split(';')


    move = None
    prev_onoffvalue = onoffValue = int(prev_Value[0],16)
    prev_lvlValue = lvlValue = int(prev_Value[1],16)
    prev_duration = duration = int(prev_Value[2],16)

    self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - past OnOff: %s, Lvl: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, onoffValue, lvlValue), MsgSrcAddr)
    if MsgAttrID == '0001': #On button
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - ON Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        onoffValue = 1

    elif MsgAttrID == '0004': # Off  Button
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - OFF Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        onoffValue = 0

    elif MsgAttrID in  ( '0002', '0003' ): # Dim+ / 0002 is +, 0003 is -
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - DIM Button detected" %(MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        action = MsgClusterData[2:4]
        duration = MsgClusterData[6:10]
        duration = struct.unpack('H',struct.pack('>H',int(duration,16)))[0]

        if action in ('00'): #Short press
            self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - DIM Action: %s" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, action), MsgSrcAddr)
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
            self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - DIM Release after %s seconds" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, round(duration/10)), MsgSrcAddr)

        else:
            self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - DIM Action: %s not processed" %(MsgClusterId, MsgSrcAddr, MsgSrcEp, action), MsgSrcAddr)
            return   # No need to update

        # Check if we reach the limits Min and Max
        if lvlValue > 255: 
            lvlValue = 255
        if lvlValue <= 0: 
            lvlValue = 0
        self.log.logging( "Cluster", 'Debug', "ReadCluster - %s - %s/%s - Level: %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, lvlValue), MsgSrcAddr)
    else:
        self.log.logging( "Cluster", 'Log', "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    #Update Domo
    sonoffValue = '%02x' %onoffValue
    slvlValue = '%02x' %lvlValue
    sduration = '%02x' %duration

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, '0000',  '%s;%s;%s' %(sonoffValue, slvlValue, sduration) )
    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s - updating self.ListOfDevices[%s]['Ep'][%s][%s] = %s" \
            %( MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId , self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]), MsgSrcAddr)

    if prev_onoffvalue != onoffValue:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', sonoffValue)
    if prev_lvlValue != lvlValue:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, slvlValue)

def Clusterfc01( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
        %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)   
        
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )
    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    model = self.ListOfDevices[MsgSrcAddr]['Model']

    if 'Legrand' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Legrand'] = {}

    if MsgAttrID == '0000':
        if model == 'Dimmer switch wo neutral':
            # Enable Dimmer  ( 16bitData)
            if MsgClusterData == '0101':
                #'0101' # Enable Dimmer
                self.ListOfDevices[MsgSrcAddr]['Legrand'][ 'EnableDimmer' ] = 1
            else:
                #'0100' # Disable Dimmer
                self.ListOfDevices[MsgSrcAddr]['Legrand'][ 'EnableDimmer' ] = 0

        elif model == 'Cable outlet':
            # 0200 FIP
            # 0100 Normal
            # Legrand Fil Pilote ( 16bitData) 1-Enable, 2-Disable
            self.ListOfDevices[MsgSrcAddr]['Legrand'][ 'LegrandFilPilote' ] = int(MsgClusterData,16)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

    elif MsgAttrID == '0001':
        if model == 'Dimmer switch wo neutral':
            # Enable Led in Dark
            self.ListOfDevices[MsgSrcAddr]['Legrand'][ 'EnableLedInDark' ] = int(MsgClusterData,16)

        elif model == 'Shutter switch with neutral':
            # Enable Led Shutter
            self.ListOfDevices[MsgSrcAddr]['Legrand'][ 'EnableLedShutter' ] = int(MsgClusterData,16)

    elif MsgAttrID == '0002':
        if model in [ 'Dimmer switch wo neutral', 'Connected outlet', 'Mobile outlet', ]:
            # Enable Led if On
            self.ListOfDevices[MsgSrcAddr]['Legrand'][ 'EnableLedIfOn' ] = int(MsgClusterData,16)


def Clusterfc40( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source ):
    
    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
        %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)   
        
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID,  MsgClusterData )
    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    model = self.ListOfDevices[MsgSrcAddr]['Model']

    if 'Legrand' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Legrand'] = {}

    if MsgAttrID == '0000':
        # Confort': 0x00,
        # Confort -1' : 0x01,
        # Confort -2' : 0x02,
        # Eco': 0x03,
        # Hors-gel' : 0x04,
        # Off': 0x05
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

def Clusterfc21( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    # FC21 : PFX Cluster Profalux
    # Attribute 0x0001 => Orientation ( value between 0 to 90)

    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    if MsgAttrID == "0001":
        self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Orientation BSO: %s - %s °" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData, int(MsgClusterData,16)), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

def Clusterfcc0(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData , Source):

    self.log.logging( "Cluster", 'Debug', "ReadCluster %s - %s/%s Attribute: %s Type: %s Size: %s Data: %s" 
        %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
    checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID,  MsgClusterData )

    if MsgAttrID == '00f7':
        readXiaomiCluster( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
