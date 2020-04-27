#
"""
    Module: z_input.py

    Description: manage inputs from Zigate

"""

import Domoticz
import binascii
import time
from datetime import datetime
import struct
import queue
from time import time
import json

from Modules.domoticz import MajDomoDevice, lastSeenUpdate, timedOutDevice
from Modules.tools import timeStamped, updSQN, DeviceExist, getSaddrfromIEEE, IEEEExist, initDeviceInList, mainPoweredDevice, loggingMessages, lookupForIEEE
from Modules.logging import loggingPairing, loggingInput
from Modules.output import sendZigateCmd, leaveMgtReJoin, ReadAttributeRequest_0000, ReadAttributeRequest_0001, setTimeServer, ZigatePermitToJoin
from Modules.bindings import rebind_Clusters
from Modules.livolo import livolo_bind
from Modules.configureReporting import processConfigureReporting
from Modules.schneider_wiser import schneider_wiser_registration, schneiderReadRawAPS
from Modules.errorCodes import DisplayStatusCode
from Modules.readClusters import ReadCluster
from Modules.database import saveZigateNetworkData
from Modules.zigateConsts import ADDRESS_MODE, ZCL_CLUSTERS_LIST, LEGRAND_REMOTES, LEGRAND_REMOTE_SWITCHS, ZIGATE_EP
from Modules.pluzzy import pluzzyDecode8102
from Modules.zigate import  initLODZigate, receiveZigateEpList, receiveZigateEpDescriptor

from Modules.callback import callbackDeviceAwake
from Modules.inRawAps import inRawAps
from Modules.pdmHost import pdmHostAvailableRequest, PDMSaveRequest, PDMLoadRequest, \
            PDMGetBitmapRequest, PDMIncBitmapRequest, PDMExistanceRequest, pdmLoadConfirmed, \
            PDMDeleteRecord, PDMDeleteAllRecord, PDMCreateBitmap, PDMDeleteBitmapRequest


#from Modules.adminWidget import updateNotificationWidget, updateStatusWidget

from Classes.IAS import IAS_Zone_Management
from Classes.AdminWidgets import  AdminWidgets
from Classes.GroupMgt import GroupsManagement
from Classes.OTA import OTAManagement
from Classes.NetworkMap import NetworkMap

def ZigateRead(self, Devices, Data):

    DECODERS = {
        '0100': Decode0100,
        '004d': Decode004D,
        '8000': Decode8000_v2, '8001': Decode8001, '8002': Decode8002, '8003': Decode8003, '8004': Decode8004,
        '8005': Decode8005, '8006': Decode8006, '8007': Decode8007,
        '8009': Decode8009, '8010': Decode8010, '8011': Decode8011, '8012': Decode8012,
        '8014': Decode8014, '8015': Decode8015,
        '8017': Decode8017,
        '8024': Decode8024,
        '8028': Decode8028,
        '802b': Decode802B, '802c': Decode802C,
        '8030': Decode8030, '8031': Decode8031, '8035': Decode8035,
        '8034': Decode8034,
        '8040': Decode8040, '8041': Decode8041, '8042': Decode8042, '8043': Decode8043, '8044': Decode8044,
        '8045': Decode8045, '8046': Decode8046, '8047': Decode8047, '8048': Decode8048, '8049': Decode8049,
        '804a': Decode804A, '804b': Decode804B,
        '804e': Decode804E,
        '8060': Decode8060, '8061': Decode8061, '8062': Decode8062, '8063': Decode8063,
        '8085': Decode8085,
        '8095': Decode8095,
        '80a6': Decode80A6,
        '80a7': Decode80A7,
        '8100': Decode8100, '8101': Decode8101, '8102': Decode8102,
        '8110': Decode8110,
        '8120': Decode8120,
        '8140': Decode8140,
        '8401': Decode8401,
        '8501': Decode8501,
        '8503': Decode8503,
        '8701': Decode8701, '8702': Decode8702,
        '8806': Decode8806, '8807': Decode8807,
        '0300': Decode0300, '0301': Decode0301, '0302': Decode0302,
        '0200': Decode0200, '0201': Decode0201, '0202': Decode0202, '0203': Decode0203, '0204':Decode0204, 
        '0205': Decode0205, '0206': Decode0206, '0207': Decode0207, '0208': Decode0208
    }
    
    NOT_IMPLEMENTED = ( '00d1', '8029', '80a0', '80a1', '80a2', '80a3', '80a4' )

    #loggingInput( self, 'Debug', "ZigateRead - decoded data : " + Data + " lenght : " + str(len(Data)) )

    FrameStart=Data[0:2]
    FrameStop=Data[len(Data)-2:len(Data)]
    if ( FrameStart != "01" and FrameStop != "03" ): 
        Domoticz.Error("ZigateRead received a non-zigate frame Data : " + Data + " FS/FS = " + FrameStart + "/" + FrameStop )
        return

    MsgType=Data[2:6]
    MsgType = MsgType.lower()
    MsgLength=Data[6:10]
    MsgCRC=Data[10:12]

    if len(Data) > 12 :
        # We have Payload : data + rssi
        MsgData=Data[12:len(Data)-4]
        MsgRSSI=Data[len(Data)-4:len(Data)-2]
    else :
        MsgData=""
        MsgRSSI=""

    loggingInput( self, 'Debug', "ZigateRead - MsgType: %s, MsgLength: %s, MsgCRC: %s, Data: %s; RSSI: %s" \
            %( MsgType, MsgLength, MsgCRC, MsgData, MsgRSSI) )

    if MsgType in DECODERS:
        _decoding = DECODERS[ MsgType]
        _decoding( self, Devices, MsgData, MsgRSSI)
        return

    Domoticz.Error("ZigateRead - Decoder not found for %s" %(MsgType))

    return

#IAS Zone
def Decode8401(self, Devices, MsgData, MsgRSSI) : # Reception Zone status change notification

    loggingInput( self, 'Debug', "Decode8401 - Reception Zone status change notification : " + MsgData)
    MsgSQN=MsgData[0:2]           # sequence number: uint8_t
    MsgEp=MsgData[2:4]            # endpoint : uint8_t
    MsgClusterId=MsgData[4:8]     # cluster id: uint16_t
    MsgSrcAddrMode=MsgData[8:10]  # src address mode: uint8_t
    if MsgSrcAddrMode == "02":
        MsgSrcAddr=MsgData[10:14]     # src address: uint64_t or uint16_t based on address mode
        MsgZoneStatus=MsgData[14:18]  # zone status: uint16_t
        MsgExtStatus=MsgData[18:20]   # extended status: uint8_t
        MsgZoneID=MsgData[20:22]      # zone id : uint8_t
        MsgDelay=MsgData[22:26]       # delay: data each element uint16_t
    elif MsgSrcAddrMode == "03":
        MsgSrcAddr=MsgData[10:26]     # src address: uint64_t or uint16_t based on address mode
        MsgZoneStatus=MsgData[26:30]  # zone status: uint16_t
        MsgExtStatus=MsgData[30:32]   # extended status: uint8_t
        MsgZoneID=MsgData[32:34]      # zone id : uint8_t
        MsgDelay=MsgData[34:38]       # delay: data each element uint16_t

    # 0  0  0    0  1    1    1  2  2
    # 0  2  4    8  0    4    8  0  2
    # 5a 02 0500 02 0ffd 0010 00 ff 0001
    # 5d 02 0500 02 0ffd 0011 00 ff 0001

    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("Decode8401 - unknown IAS device %s from plugin" %MsgSrcAddr)
        return
    if 'Health' in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'

    timeStamped( self, MsgSrcAddr , 0x8401)
    updSQN( self, MsgSrcAddr, MsgSQN)

    Model = ''
    if MsgSrcAddr in self.ListOfDevices:
        if 'Model' in self.ListOfDevices[MsgSrcAddr]:
            Model =  self.ListOfDevices[MsgSrcAddr]['Model']
    else:
        loggingInput( self, 'Log',"Decode8401 - receive a message for an unknown device %s : %s" %( MsgSrcAddr, MsgData))
        return


    loggingInput( self, 'Debug', "Decode8401 - MsgSQN: %s MsgSrcAddr: %s MsgEp:%s MsgClusterId: %s MsgZoneStatus: %s MsgExtStatus: %s MsgZoneID: %s MsgDelay: %s" \
            %( MsgSQN, MsgSrcAddr, MsgEp, MsgClusterId, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay), MsgSrcAddr)

    if Model == "PST03A-v2.2.5" :
        ## CLD CLD
        # bit 3, battery status (0=Ok 1=to replace)
        iData = int(MsgZoneStatus,16) & 8 >> 3                 # Set batery level
        if iData == 0 :
            self.ListOfDevices[MsgSrcAddr]['Battery']="100"        # set to 100%
        else :
            self.ListOfDevices[MsgSrcAddr]['Battery']="0"
        if MsgEp == "02" :                    
            iData = int(MsgZoneStatus,16) & 1      #  For EP 2, bit 0 = "door/window status"
            # bit 0 = 1 (door is opened) ou bit 0 = 0 (door is closed)
            value = "%02d" % iData
            loggingInput( self, 'Debug', "Decode8401 - PST03A-v2.2.5 door/windows status : " + value, MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0500", value)
            # Nota : tamper alarm on EP 2 are discarded
        elif  MsgEp == "01" :
            iData = (int(MsgZoneStatus,16) & 1)    # For EP 1, bit 0 = "movement"
            # bit 0 = 1 ==> movement
            if iData == 1 :    
                value = "%02d" % iData
                loggingInput( self, 'Debug', "Decode8401 - PST03A-v2.2.5 mouvements alarm", MsgSrcAddr)
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0406", value)
            # bit 2 = 1 ==> tamper (device disassembly)
            iData = (int(MsgZoneStatus,16) & 4) >> 2
            if iData == 1 :     
                value = "%02d" % iData
                loggingInput( self, 'Debug', "Decode8401 - PST03A-V2.2.5  tamper alarm", MsgSrcAddr)
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", value)
        else :
            loggingInput( self, 'Debug', "Decode8401 - PST03A-v2.2.5, unknow EndPoint : " + MsgEp, MsgSrcAddr)
    else :      ## default 
        alarm1 =  int(MsgZoneStatus,16) & 1 
        alarm2 =  ( int(MsgZoneStatus,16)  >> 1 ) & 1
        tamper =  ( int(MsgZoneStatus,16)  >> 2 ) & 1
        battery  = ( int(MsgZoneStatus,16) >> 3 ) & 1
        suprrprt = ( int(MsgZoneStatus,16) >> 4 ) & 1
        restrprt = ( int(MsgZoneStatus,16) >> 5 ) & 1
        trouble  = ( int(MsgZoneStatus,16) >> 6 ) & 1
        acmain   = ( int(MsgZoneStatus,16) >> 7 ) & 1
        test     = ( int(MsgZoneStatus,16) >> 8 ) & 1
        battdef  = ( int(MsgZoneStatus,16) >> 9 ) & 1

        if '0500' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500'] = {}
        if not isinstance( self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500'] , dict):
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp][MsgClusterId]['0500'] = {}
        if '0002' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002'] = {}

        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002'] = \
                'alarm1: %s, alaram2: %s, tamper: %s, battery: %s, Support Reporting: %s, restore Reporting: %s, trouble: %s, acmain: %s, test: %s, battdef: %s' \
                %(alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef)

        loggingInput( self, 'Debug', "IAS Zone for device:%s  - alarm1: %s, alaram2: %s, tamper: %s, battery: %s, Support Reporting: %s, restore Reporting: %s, trouble: %s, acmain: %s, test: %s, battdef: %s" \
                %( MsgSrcAddr, alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef), MsgSrcAddr)

        loggingInput( self, 'Debug',"Decode8401 MsgZoneStatus: %s " %MsgZoneStatus[2:4], MsgSrcAddr)
        value = MsgZoneStatus[2:4]

        if self.ListOfDevices[MsgSrcAddr]['Model'] in ( '3AFE14010402000D', '3AFE28010402000D'): #Konke Motion Sensor
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0406", '%02d' %alarm1 )
        elif self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'lumi.sensor_magnet', 'lumi.sensor_magnet.aq2' ): # Xiaomi Door sensor
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", '%02d' %alarm1 )
        else:
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, MsgClusterId, '%02d' %( alarm1 or alarm2) )

        if battdef or battery:
            self.ListOfDevices[MsgSrcAddr]['Battery'] = '1'

        if 'IAS' in self.ListOfDevices[MsgSrcAddr]:
            if 'ZoneStatus' in self.ListOfDevices[MsgSrcAddr]['IAS']:
                if not isinstance(self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'], dict):
                    self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = {}

                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['alarm1'] = alarm1
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['alarm2'] = alarm2
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['tamper'] = tamper
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['battery'] = battery
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['Support Reporting'] = suprrprt
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['Restore Reporting'] = restrprt
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['trouble'] = trouble
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['acmain'] = acmain
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['test'] = test
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['battdef'] = battdef
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['GlobalInfos'] = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" %( alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef)
                self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['TimeStamp'] = int(time())
    return


#Responses
def Decode8000_v2(self, Devices, MsgData, MsgRSSI) : # Status
    MsgLen=len(MsgData)

    if MsgLen < 8 :
        loggingInput( self, 'Log',"Decode8000 - uncomplete message : %s" %MsgData)
        return

    if MsgLen > 8 :
        loggingInput( self, 'Log',"Decode8000 - More information . New Firmware ???")
        loggingInput( self, 'Log',"Decode8000 - %s" %MsgData)

    Status=MsgData[0:2]
    SEQ=MsgData[2:4]
    PacketType=MsgData[4:8]

    if self.pluginconf.pluginConf['debugzigateCmd']:
        loggingInput( self, 'Log', "Decode8000    - %s      Status: %s" %( PacketType, Status))

    if   Status=="00" : Status="Success"
    elif Status=="01" : Status="Incorrect Parameters"
    elif Status=="02" : Status="Unhandled Command"
    elif Status=="03" : Status="Command Failed"
    elif Status=="04" : Status="Busy"
    elif Status=="05" : Status="Stack Already Started"
    elif int(Status,16) >= 128 and int(Status,16) <= 244 : Status="ZigBee Error Code "+ DisplayStatusCode(Status)


    if   PacketType=="0012" : loggingInput( self, 'Log',"Erase Persistent Data cmd status : " +  Status )
    elif PacketType=="0024" : loggingInput( self, 'Log',"Start Network status : " +  Status )
    elif PacketType=="0026" : loggingInput( self, 'Log',"Remove Device cmd status : " +  Status )
    elif PacketType=="0044" : loggingInput( self, 'Log',"request Power Descriptor status : " +  Status )

    if PacketType=="0012":
        # Let's trigget a zigate_Start
        #self.startZigateNeeded = self.HeartbeatCount
        #if self.HeartbeatCount == 0:
        #    self.startZigateNeeded = 1
        pass

    # Group Management
    if PacketType in ('0060', '0061', '0062', '0063', '0064', '0065'):
        if self.groupmgt:
            self.groupmgt.statusGroupRequest( MsgData )

    if str(MsgData[0:2]) != "00" :
        loggingInput( self, 'Debug', "Decode8000 - PacketType: %s Status: [%s] - %s" \
                %(PacketType, MsgData[0:2], Status))

    return

def Decode8001(self, Decode, MsgData, MsgRSSI) : # Reception log Level
    MsgLen=len(MsgData)

    MsgLogLvl=MsgData[0:2]
    MsgDataMessage=MsgData[2:len(MsgData)]
    
    loggingInput( self, 'Status', "Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)
    return

def Decode8002(self, Devices, MsgData, MsgRSSI) : # Data indication

    MsgLogLvl=MsgData[0:2]
    MsgProfilID=MsgData[2:6]
    MsgClusterID=MsgData[6:10]
    MsgSourcePoint=MsgData[10:12]
    MsgDestPoint=MsgData[12:14]
    MsgSourceAddressMode=MsgData[14:16]

    #Domoticz.Log("Decode8002 - MsgLogLvl: %s , MsgProfilID: %s, MsgClusterID: %s MsgSourcePoint: %s, MsgDestPoint: %s, MsgSourceAddressMode: %s" \
    #        %(MsgLogLvl, MsgProfilID, MsgClusterID, MsgSourcePoint, MsgDestPoint, MsgSourceAddressMode))

    if MsgProfilID != '0104':
        Domoticz.Log("Decode8002 - Not an HA Profile, let's drop the packet %s" %MsgData)
        return

    if int(MsgSourceAddressMode,16) == ADDRESS_MODE['short'] or \
            int(MsgSourceAddressMode,16) == ADDRESS_MODE['group']:
        MsgSourceAddress=MsgData[16:20]  # uint16_t
        MsgDestinationAddressMode=MsgData[20:22]

        if int(MsgDestinationAddressMode,16)==ADDRESS_MODE['short'] or \
                int(MsgDestinationAddressMode,16)==ADDRESS_MODE['group']:
            # Short Address
            MsgDestinationAddress=MsgData[22:26] # uint16_t
            MsgPayload=MsgData[26:len(MsgData)]

        elif int(MsgDestinationAddressMode,16)==ADDRESS_MODE['ieee']: # uint32_t
            # IEEE
            MsgDestinationAddress=MsgData[22:38] # uint32_t
            MsgPayload=MsgData[38:len(MsgData)]

        else:
            Domoticz.Log("Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s" \
                    %(MsgDestinationAddressMode, MsgData))
            return

    elif int(MsgSourceAddressMode,16) == ADDRESS_MODE['ieee']:
        MsgSourceAddress=MsgData[16:32] #uint32_t
        MsgDestinationAddressMode=MsgData[32:34]

        if int(MsgDestinationAddressMode,16)== ADDRESS_MODE['short'] or \
                int(MsgDestinationAddressMode,16)==ADDRESS_MODE['group']:
            MsgDestinationAddress=MsgData[34:38] # uint16_t
            MsgPayload=MsgData[38:len(MsgData)]

        elif int(MsgDestinationAddressMode,16)== ADDRESS_MODE['ieee']:
            # IEEE
            MsgDestinationAddress=MsgData[34:40] #uint32_t
            MsgPayload=MsgData[40:len(MsgData)]
        else:
            Domoticz.Log("Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s" \
                    %(MsgDestinationAddressMode, MsgData))
            return
    else:
        Domoticz.Log("Decode8002 - Unexpected Source ADDR_MOD: %s, drop packet %s" \
                %(MsgSourceAddressMode, MsgData))
        return

    loggingInput( self, 'Debug', "Reception Data indication, Source Address : " + MsgSourceAddress + " Destination Address : " + MsgDestinationAddress + " ProfilID : " + MsgProfilID + " ClusterID : " + MsgClusterID + " Message Payload : " + MsgPayload)

    # Let's check if this is an Schneider related APS. In that case let's process
    srcnwkid = dstnwkid = None
    if len(MsgSourceAddress) == 4:
        # Short address
        if MsgSourceAddress not in self.ListOfDevices:
            return
        srcnwkid = MsgSourceAddress
    else:
        # IEEE 
        if MsgSourceAddress not in self.IEEE2NWK:
            return
        srcnwkid = self.IEEE2NWK[ MsgSourceAddress ]

    if len(MsgDestinationAddress) == 4:
        # Short address
        if MsgDestinationAddress not in self.ListOfDevices:
            return
        dstnwkid = MsgDestinationAddress
    else:
        # IEEE 
        if MsgDestinationAddress not in self.IEEE2NWK:
            return
        dstnwkid = self.IEEE2NWK[ MsgDestinationAddress ]

    if 'Manufacturer' not in self.ListOfDevices[srcnwkid]:
        return

    inRawAps( self, Devices, srcnwkid, MsgSourcePoint,  MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload)

    callbackDeviceAwake( self, srcnwkid, MsgSourcePoint, MsgClusterID)

    return

def Decode8003(self, Devices, MsgData, MsgRSSI) : # Device cluster list
    MsgLen=len(MsgData)

    MsgSourceEP=MsgData[0:2]
    MsgProfileID=MsgData[2:6]
    MsgClusterID=MsgData[6:len(MsgData)]

    idx = 0
    clusterLst = []
    while idx < len(MsgClusterID):
        clusterLst.append(MsgClusterID[idx:idx+4] )
        idx += 4
    
    self.zigatedata['Cluster List'] = clusterLst
    loggingInput( self, 'Status', "Device Cluster list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " Cluster List : " + str(clusterLst) )
    return

def Decode8004(self, Devices, MsgData, MsgRSSI) : # Device attribut list
    MsgLen=len(MsgData)

    MsgSourceEP=MsgData[0:2]
    MsgProfileID=MsgData[2:6]
    MsgClusterID=MsgData[6:10]
    MsgAttributList=MsgData[10:len(MsgData)]
    
    idx = 0
    attributeLst = []
    while idx < len(MsgAttributList):
        attributeLst.append(MsgAttributList[idx:idx+4] )
        idx += 4

    self.zigatedata['Device Attributs List'] = attributeLst
    loggingInput( self, 'Status', "Device Attribut list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Attribut List : " + str(attributeLst) )
    return

def Decode8005(self, Devices, MsgData, MsgRSSI) : # Command list
    MsgLen=len(MsgData)

    MsgSourceEP=MsgData[0:2]
    MsgProfileID=MsgData[2:6]
    MsgClusterID=MsgData[6:10]
    MsgCommandList=MsgData[10:len(MsgData)]
    
    idx = 0
    commandLst = []
    while idx < len(MsgCommandList):
        commandLst.append(MsgCommandList[idx:idx+4] )
        idx += 4

    self.zigatedata['Device Attributs List'] = commandLst
    loggingInput( self, 'Status', "Command list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Command List : " + str( commandLst ))
    return

def Decode8006(self, Devices, MsgData, MsgRSSI): # Non “Factory new” Restart

    loggingInput( self, 'Log', "Decode8006 - MsgData: %s" %(MsgData))

    Status = MsgData[0:2]
    if MsgData[0:2] == "00":
        Status = "STARTUP"
    elif MsgData[0:2] == "01":
        Status = "RUNNING"
    elif MsgData[0:2] == "02":
        Status = "NFN_START"
    elif MsgData[0:2] == "06":
        Status = "RUNNING"

    #self.startZigateNeeded = self.HeartbeatCount
    #if self.HeartbeatCount == 0:
    #    self.startZigateNeeded = 1
    loggingInput( self, 'Status', "Non 'Factory new' Restart status: %s" %(Status) )

def Decode8007(self, Devices, MsgData, MsgRSSI): # “Factory new” Restart

    loggingInput( self, 'Debug', "Decode8007 - MsgData: %s" %(MsgData))

    Status = MsgData[0:2]
    if MsgData[0:2] == "00":
        Status = "STARTUP"
    elif MsgData[0:2] == "01":
        Status = "RUNNING"
    elif MsgData[0:2] == "02":
        Status = "NFN_START"
    elif MsgData[0:2] == "06":
        Status = "RUNNING"

    #self.startZigateNeeded = self.HeartbeatCount
    #if self.HeartbeatCount == 0:
    #    self.startZigateNeeded = 1
    loggingInput( self, 'Status', "'Factory new' Restart status: %s" %(Status) )

def Decode8009(self,Devices, MsgData, MsgRSSI) : # Network State response (Firm v3.0d)
    MsgLen=len(MsgData)
    addr=MsgData[0:4]
    extaddr=MsgData[4:20]
    PanID=MsgData[20:24]
    extPanID=MsgData[24:40]
    Channel=MsgData[40:42]
    loggingInput( self, 'Debug', "Decode8009: Network state - Address :" + addr + " extaddr :" + extaddr + " PanID : " + PanID + " Channel : " + str(int(Channel,16)) )

    if self.ZigateIEEE != extaddr:
        # In order to update the first time
        self.adminWidgets.updateNotificationWidget( Devices, 'Zigate IEEE: %s' %extaddr)

    self.ZigateIEEE = extaddr
    self.ZigateNWKID = addr

    if self.ZigateNWKID != '0000':
        Domoticz.Error("Zigate not correctly initialized")
        return

    # At that stage IEEE is set to 0x0000 which is correct for the Coordinator
    if extaddr not in self.IEEE2NWK:
        if self.IEEE2NWK != addr:
            initLODZigate( self, addr, extaddr )

    if self.currentChannel != int(Channel,16):
        self.adminWidgets.updateNotificationWidget( Devices, 'Zigate Channel: %s' %str(int(Channel,16)))

    # Let's check if this is a first initialisation, and then we need to update the Channel setting
    if 'startZigateNeeded' not in self.zigatedata and not self.startZigateNeeded:    
        if str(int(Channel,16)) != self.pluginconf.pluginConf['channel']:
            Domoticz.Status("Updating Channel in Plugin Configuration from: %s to: %s" \
                %( self.pluginconf.pluginConf['channel'], int(Channel,16)))
            self.pluginconf.pluginConf['channel'] = str(int(Channel,16))
            self.pluginconf.write_Settings()

    self.currentChannel = int(Channel,16)

    if self.iaszonemgt:
        self.iaszonemgt.setZigateIEEE( extaddr )


    loggingInput( self, 'Status', "Zigate addresses ieee: %s , short addr: %s" %( self.ZigateIEEE,  self.ZigateNWKID) )

    # from https://github.com/fairecasoimeme/ZiGate/issues/15 , if PanID == 0 -> Network is done
    if str(PanID) == "0" : 
        loggingInput( self, 'Status', "Network state DOWN ! " )
        self.adminWidgets.updateNotificationWidget( Devices, 'Network down PanID = 0' )
        self.adminWidgets.updateStatusWidget( Devices, 'No Connection')
    else :
        loggingInput( self, 'Status', "Network state UP, PANID: %s extPANID: 0x%s Channel: %s" \
                %( PanID, extPanID, int(Channel,16) ))

    self.zigatedata['IEEE'] = extaddr
    self.zigatedata['Short Address'] = addr
    self.zigatedata['Channel'] = int(Channel,16)
    self.zigatedata['PANID'] = PanID
    self.zigatedata['Extended PANID'] = extPanID
    saveZigateNetworkData( self , self.zigatedata )

    return

def Decode8010(self, Devices, MsgData, MsgRSSI): # Reception Version list
    MsgLen=len(MsgData)

    MajorVersNum=MsgData[0:4]
    InstaVersNum=MsgData[4:8]
    try :
        loggingInput( self, 'Debug', "Decode8010 - Reception Version list : " + MsgData)
        loggingInput( self, 'Status', "Major Version Num: " + MajorVersNum )
        loggingInput( self, 'Status', "Installer Version Number: " + InstaVersNum )
    except :
        Domoticz.Error("Decode8010 - Reception Version list : " + MsgData)
    else:
        self.FirmwareVersion = str(InstaVersNum)
        self.FirmwareMajorVersion = str(MajorVersNum)
        self.zigatedata['Firmware Version'] =  str(MajorVersNum) + ' - ' +str(InstaVersNum)

    self.PDMready = True
    return

def Decode8011( self, Devices, MsgData, MsgRSSI ):

    # APP APS ACK
    loggingInput( self, 'Debug', "Decode8011 - APS ACK: %s" %MsgData)
    MsgStatus = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]


    if MsgSrcAddr not in self.ListOfDevices:
        return

    _powered = mainPoweredDevice( self, MsgSrcAddr)
    loggingInput( self, 'Debug', "Decode8011 - Src: %s, SrcEp: %s, Cluster: %s, Status: %s MainPowered: %s" \
            %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgStatus, _powered), MsgSrcAddr)

    timeStamped( self, MsgSrcAddr , 0x8011)
    if MsgStatus == '00':
        lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
        if 'Health' in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]['Health'] != 'Live':
                loggingInput( self, 'Log', "Receive an APS Ack from %s, let's put the device back to Live" %MsgSrcAddr, MsgSrcAddr)
                self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
    else:
        if _powered and self.pluginconf.pluginConf['enableACKNACK']: # NACK for a Non powered device doesn't make sense
            timedOutDevice( self, Devices, NwkId = MsgSrcAddr)
            if 'Health' in self.ListOfDevices[MsgSrcAddr]:
                if self.ListOfDevices[MsgSrcAddr]['Health'] != 'Not Reachable':
                    self.ListOfDevices[MsgSrcAddr]['Health'] = 'Not Reachable'
                if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                    if self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != {} and self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != '':
                        loggingInput( self, 'Log', "Receive NACK from %s (%s) clusterId: %s" %(self.ListOfDevices[MsgSrcAddr]['ZDeviceName'], MsgSrcAddr, MsgClusterId), MsgSrcAddr)
                    else:
                        loggingInput( self, 'Log', "Receive NACK from %s clusterId: %s" %(MsgSrcAddr, MsgClusterId), MsgSrcAddr)
        else:
            if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                if self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != {} and self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != '':
                    loggingInput( self, 'Debug', "Receive NACK from %s (%s) clusterId: %s" %(self.ListOfDevices[MsgSrcAddr]['ZDeviceName'], MsgSrcAddr, MsgClusterId), MsgSrcAddr)
                else:
                    loggingInput( self, 'Debug', "Receive NACK from %s clusterId: %s" %(MsgSrcAddr, MsgClusterId), MsgSrcAddr)

def Decode8012( self, Devices, MsgData, MsgRSSI ):
    """
    confirms that a data packet sent by the local node has been successfully 
    passed down the stack to the MAC layer and has made its first hop towards
    its destination (an acknowledgment has been received from the next hop node).
    """

    MsgStatus = MsgData[0:2]
    MsgSrcEp = MsgData[2:4]
    MsgDstEp = MsgData[4:6]
    MsgAddrMode = MsgData[6:8]

    if int(MsgAddrMode,16) == 0x03: # IEEE
        MsgSrcIEEE = MsgData[8:24]
        MsgSQN = MsgData[24:26]
        if MsgSrcIEEE in self.IEEE2NWK:
            MsgSrcNwkId = self.IEEE2NWK[MsgSrcIEEE ]
    else:
        MsgSrcNwkid = MsgData[8:12]
        MsgSQN = MsgData[12:14]
 
    loggingInput( self, 'Log', "Decode8012 - Src: %s, SrcEp: %s,Status: %s" \
            %(MsgSrcNwkid, MsgSrcEp, MsgStatus))


def Decode8014(self, Devices, MsgData, MsgRSSI): # "Permit Join" status response

    MsgLen=len(MsgData)
    Status=MsgData[0:2]
    timestamp = int(time())

    loggingInput( self, 'Debug',"Decode8014 - Permit Join status: %s" %( Status == '01' ) , 'ffff')

    prev = self.Ping['Permit']

    if Status == "00": 
        if self.permitTojoin['Starttime'] == 0:
            # First Status after plugin start
            # Let's force a Permit Join of Duration 0
            ZigatePermitToJoin( self, 0 )
            self.permitTojoin['Starttime'] = timestamp

        elif ( self.Ping['Permit'] is None) or (self.permitTojoin['Starttime'] >= timestamp - 240):
            loggingInput( self, 'Status', "Accepting new Hardware: Disable")
        self.permitTojoin['Duration'] = 0
        self.Ping['Permit'] = 'Off'

    elif Status == "01" : 
        if (self.Ping['Permit'] is None) or ( self.permitTojoin['Starttime'] >= timestamp - 240):
            loggingInput( self, 'Status', "Accepting new Hardware: On")
        self.Ping['Permit'] = 'On'

        if self.permitTojoin['Duration'] == 0:
            # In case 'Duration' is unknown or set to 0 and then, we have a Permit to Join, we are most-likely in the case of
            # a restart of the plugin.
            # We will make the assumption that Duration will be 255. In case that is not the case, during the next Ping, 
            # we will receive a permit Off
            self.permitTojoin['Duration'] = 254
            self.permitTojoin['Starttime'] = timestamp
    else: 
        Domoticz.Error("Decode8014 - Unexpected value "+str(MsgData))

    loggingInput( self, 'Debug',"---> self.permitTojoin['Starttime']: %s" %self.permitTojoin['Starttime'], 'ffff')
    loggingInput( self, 'Debug',"---> self.permitTojoin['Duration'] : %s" %self.permitTojoin['Duration'], 'ffff')
    loggingInput( self, 'Debug',"---> Current time                  : %s" %timestamp, 'ffff')
    loggingInput( self, 'Debug',"---> self.Ping['Permit']  (prev)   : %s" %prev, 'ffff')
    loggingInput( self, 'Debug',"---> self.Ping['Permit']  (new )   : %s" %self.Ping['Permit'], 'ffff')

    self.Ping['TimeStamp'] = int(time())
    self.Ping['Status'] = 'Receive'

    loggingInput( self, 'Debug', "Ping - received", 'ffff')
    return

def Decode8017(self, Devices, MsgData, MsgRSSI) : # 

    ZigateTime = MsgData[0:8]

    EPOCTime = datetime(2000,1,1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    ZigateTime =  struct.unpack('I',struct.pack('I',int(ZigateTime,16)))[0]
    loggingInput(self, 'Debug', "UTC time is: %s, Zigate Time is: %s with deviation of :%s " %(UTCTime, ZigateTime, UTCTime - ZigateTime))
    if  abs( UTCTime - ZigateTime ) > 5:# If Deviation is more than 5 sec then reset Time
        setTimeServer( self )

def Decode8015(self, Devices, MsgData, MsgRSSI) : # Get device list ( following request device list 0x0015 )
    # id: 2bytes
    # addr: 4bytes
    # ieee: 8bytes
    # power_type: 2bytes - 0 Battery, 1 AC Power
    # rssi : 2 bytes - Signal Strength between 1 - 255
    numberofdev=len(MsgData)    
    loggingInput( self, 'Status', "Number of devices recently active in Zigate = " + str(round(numberofdev/26)) )
    idx=0
    while idx < (len(MsgData)):
        DevID=MsgData[idx:idx+2]
        saddr=MsgData[idx+2:idx+6]
        ieee=MsgData[idx+6:idx+22]
        power=MsgData[idx+22:idx+24]
        rssi=MsgData[idx+24:idx+26]

        if int(ieee,16) != 0x0:
            if DeviceExist(self, Devices, saddr, ieee):
                loggingInput( self, 'Debug', "[{:02n}".format((round(idx/26))) + "] DevID = " + DevID + \
                        " Network addr = " + saddr + " IEEE = " + ieee + \
                        " LQI = {:03n}".format((int(rssi,16))) + " Power = " + power + \
                        " HB = {:02n}".format(int(self.ListOfDevices[saddr]['Heartbeat'])) + " found in ListOfDevices")
                if rssi !="00" :
                    self.ListOfDevices[saddr]['RSSI']= int(rssi,16)
                else  :
                    self.ListOfDevices[saddr]['RSSI']= 12
                loggingInput( self, 'Debug', "Decode8015 : RSSI set to " + str( self.ListOfDevices[saddr]['RSSI']) + "/" + str(rssi) + " for " + str(saddr) )
            else: 
                loggingInput( self, 'Status', "[{:02n}".format((round(idx/26))) + "] DevID = " + DevID + \
                        " Network addr = " + saddr + " IEEE = " + ieee + \
                        " LQI = {:03n}".format(int(rssi,16)) + " Power = " + power + " not found in ListOfDevices")
        idx=idx+26

    loggingInput( self, 'Debug', "Decode8015 - IEEE2NWK      : " +str(self.IEEE2NWK) )
    return

def Decode8024(self, Devices, MsgData, MsgRSSI) : # Network joined / formed

    MsgLen=len(MsgData)
    MsgDataStatus=MsgData[0:2]

    Domoticz.Log("Decode8024: Status: %s" %MsgDataStatus)

    if MsgDataStatus == '00':
         loggingInput( self, 'Status', "Start Network - Success")
         Status = 'Success'
    elif MsgDataStatus == '01':
         loggingInput( self, 'Status', "Start Network - Formed new network")
         Status = 'Success'
    elif MsgDataStatus == '02':
        loggingInput( self, 'Status', "Start Network: Error invalid parameter.")
        Status = 'Start Network: Error invalid parameter.'
    elif MsgDataStatus == '04':
        loggingInput( self, 'Status', "Start Network: Node is on network. ZiGate is already in network so network is already formed")
        Status = 'Start Network: Node is on network. ZiGate is already in network so network is already formed'
    elif MsgDataStatus == '06':
        loggingInput( self, 'Status', "Start Network: Commissioning in progress. If network forming is already in progress")
        Status = 'Start Network: Commissioning in progress. If network forming is already in progress'
    else: 
        Status = DisplayStatusCode( MsgDataStatus )
        loggingInput( self, 'Log',"Start Network: Network joined / formed Status: %s" %(MsgDataStatus))
    
    if MsgLen != 24:
        loggingInput( self, 'Debug', "Decode8024 - uncomplete frame, MsgData: %s, Len: %s out of 24, data received: >%s<" %(MsgData, MsgLen, MsgData) )
        return

    MsgShortAddress=MsgData[2:6]
    MsgExtendedAddress=MsgData[6:22]
    MsgChannel=MsgData[22:24]

    if MsgExtendedAddress != '' and MsgShortAddress != '' and MsgShortAddress == '0000':
        # Let's check if this is a first initialisation, and then we need to update the Channel setting
        if 'startZigateNeeded' not in self.zigatedata and not self.startZigateNeeded:
            if str(int(MsgChannel,16)) != self.pluginconf.pluginConf['channel']:
                Domoticz.Status("Updating Channel in Plugin Configuration from: %s to: %s" \
                    %( self.pluginconf.pluginConf['channel'], int(MsgChannel,16)))
                self.pluginconf.pluginConf['channel'] = str(int(MsgChannel,16))
                self.pluginconf.write_Settings()

        self.currentChannel = int(MsgChannel,16)
        self.ZigateIEEE = MsgExtendedAddress
        self.ZigateNWKID = MsgShortAddress
        if self.iaszonemgt:
            self.iaszonemgt.setZigateIEEE( MsgExtendedAddress )
        self.zigatedata['IEEE'] = MsgExtendedAddress
        self.zigatedata['Short Address'] = MsgShortAddress
        self.zigatedata['Channel'] = int(MsgChannel,16)

        loggingInput( self, 'Status', "Zigate details IEEE: %s, NetworkID: %s, Channel: %s, Status: %s: %s" \
            %(MsgExtendedAddress, MsgShortAddress, int(MsgChannel,16), MsgDataStatus, Status) )
    else:
        Domoticz.Error("Zigate initialisation failed IEEE: %s, Nwkid: %s, Channel: %s" %(MsgExtendedAddress,MsgShortAddress, MsgChannel ))

def Decode8028(self, Devices, MsgData, MsgRSSI) : # Authenticate response
    MsgLen=len(MsgData)

    MsgGatewayIEEE=MsgData[0:16]
    MsgEncryptKey=MsgData[16:32]
    MsgMic=MsgData[32:40]
    MsgNodeIEEE=MsgData[40:56]
    MsgActiveKeySequenceNumber=MsgData[56:58]
    MsgChannel=MsgData[58:60]
    MsgShortPANid=MsgData[60:64]
    MsgExtPANid=MsgData[64:80]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 8028 - Authenticate response, Gateway IEEE : " + MsgGatewayIEEE + " Encrypt Key : " + MsgEncryptKey + " Mic : " + MsgMic + " Node IEEE : " + MsgNodeIEEE + " Active Key Sequence number : " + MsgActiveKeySequenceNumber + " Channel : " + MsgChannel + " Short PAN id : " + MsgShortPANid + "Extended PAN id : " + MsgExtPANid )
    return

def Decode802B(self, Devices, MsgData, MsgRSSI) : # User Descriptor Notify
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 802B - User Descriptor Notify, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest)
    return

def Decode802C(self, Devices, MsgData, MsgRSSI) : # User Descriptor Response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    MsgLenght=MsgData[8:10]
    MsgMData=MsgData[10:len(MsgData)]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 802C - User Descriptor Notify, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest + " Lenght : " + MsgLenght + " Data : " + MsgMData)
    return

def Decode8030(self, Devices, MsgData, MsgRSSI) : # Bind response

    MsgLen=len(MsgData)
    loggingInput( self, 'Debug', "Decode8030 - Msgdata: %s, MsgLen: %s" %(MsgData, MsgLen))

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]

    if MsgLen < 10:
        return

    MsgSrcAddrMode = MsgData[4:6]

    if int(MsgSrcAddrMode,16) == ADDRESS_MODE['short']:
        MsgSrcAddr=MsgData[6:10]
        nwkid = MsgSrcAddr
        loggingInput( self, 'Debug', "Decode8030 - Bind reponse for %s" %(MsgSrcAddr) , MsgSrcAddr)

    elif int(MsgSrcAddrMode,16) == ADDRESS_MODE['ieee']:
        loggingInput( self, 'Debug', "Decode8030 - Bind reponse for %s" %(MsgSrcAddr))
        MsgSrcAddr = MsgData[6:14]
        if MsgSrcAddr not in self.IEEE2NWK:
            Domoticz.Error("Decode8030 - Do no find %s in IEEE2NWK" %MsgSrcAddr)
            return
        nwkid = self.IEEE2NWK[MsgSrcAddr]

    elif int(MsgSrcAddrMode,16) == 0:
        # Most likely Firmware 3.1a
        MsgSrcAddr = MsgData[8:12]
        nwkid = MsgSrcAddr

    else:
        Domoticz.Error("Decode8030 - Unknown addr mode %s in %s" %(MsgSrcAddrMode, MsgData))
        return

    loggingInput( self, 'Debug', "Decode8030 - Bind response, Device: %s Status: %s" %(MsgSrcAddr, MsgDataStatus), MsgSrcAddr)

    if nwkid in self.ListOfDevices:
        if 'Bind' in self.ListOfDevices[nwkid]:
            for Ep in list(self.ListOfDevices[nwkid]['Bind']):
                if Ep not in self.ListOfDevices[nwkid]['Ep']:
                    # Bad hack - Root cause not identify. Suspition of back and fourth move between stable and beta branch
                    Domoticz.Error("Decode8030 --> %s Found an inconstitent Ep : %s in %s" %(nwkid, Ep, str(self.ListOfDevices[nwkid]['Bind'])))
                    del self.ListOfDevices[nwkid]['Bind'][ Ep ]
                    continue

                for cluster in list(self.ListOfDevices[nwkid]['Bind'][ Ep ]):
                    if self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Phase'] == 'requested':
                        self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Stamp'] = int(time())
                        self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Phase'] = 'binded'
                        self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Status'] = MsgDataStatus
                        return
        if 'WebBind' in self.ListOfDevices[nwkid]:
            for Ep in list(self.ListOfDevices[nwkid]['WebBind']):
                if Ep not in self.ListOfDevices[nwkid]['Ep']:
                    # Bad hack - Root cause not identify. Suspition of back and fourth move between stable and beta branch
                    Domoticz.Error("Decode8030 --> %s Found an inconstitent Ep : %s in %s" %(nwkid, Ep, str(self.ListOfDevices[nwkid]['WebBind'])))
                    del self.ListOfDevices[nwkid]['WebBind'][ Ep ]
                    continue

                for cluster in list(self.ListOfDevices[nwkid]['WebBind'][ Ep ]):
                    if self.ListOfDevices[nwkid]['WebBind'][Ep][cluster]['Phase'] == 'requested':
                        self.ListOfDevices[nwkid]['WebBind'][Ep][cluster]['Stamp'] = int(time())
                        self.ListOfDevices[nwkid]['WebBind'][Ep][cluster]['Phase'] = 'binded'
                        self.ListOfDevices[nwkid]['WebBind'][Ep][cluster]['Status'] = MsgDataStatus
                        return

    return

def Decode8031(self, Devices, MsgData, MsgRSSI) : # Unbind response
    MsgLen=len(MsgData)
    loggingInput( self, 'Debug', "Decode8031 - Msgdata: %s" %(MsgData))

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]

    if MsgLen < 10:
        return

    MsgSrcAddrMode = MsgData[4:6]
    if int(MsgSrcAddrMode,16) == ADDRESS_MODE['short']:
        MsgSrcAddr=MsgData[6:10]
        nwkid = MsgSrcAddr
        loggingInput( self, 'Debug', "Decode8031 - UnBind reponse for %s" %(MsgSrcAddr) , MsgSrcAddr)
    elif int(MsgSrcAddrMode,16) == ADDRESS_MODE['ieee']:
        MsgSrcAddr=MsgData[6:14]
        loggingInput( self, 'Debug', "Decode8031 - UnBind reponse for %s" %(MsgSrcAddr))
        if MsgSrcAddr in self.IEEE2NWK:
            nwkid = self.IEEE2NWK[MsgSrcAddr]
            Domoticz.Error("Decode8031 - Do no find %s in IEEE2NWK" %MsgSrcAddr)
    else:
        Domoticz.Error("Decode8031 - Unknown addr mode %s in %s" %(MsgSrcAddrMode, MsgData))

    loggingInput( self, 'Debug', "Decode8031 - UnBind response, Device: %s SQN: %s Status: %s" %(MsgSrcAddr, MsgSequenceNumber, MsgDataStatus), MsgSrcAddr)

    if MsgDataStatus != '00':
        loggingInput( self, 'Debug', "Decode8031 - Unbind response SQN: %s status [%s] - %s" %(MsgSequenceNumber ,MsgDataStatus, DisplayStatusCode(MsgDataStatus)), MsgSrcAddr )
    
    return

def Decode8034(self, Devices, MsgData, MsgRSSI) : # Complex Descriptor response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    MsgLenght=MsgData[8:10]
    MsgXMLTag=MsgData[10:12]
    MsgCountField=MsgData[12:14]
    MsgFieldValues=MsgData[14:len(MsgData)]
    
    loggingInput( self, 'Log',"Decode8034 - Complex Descriptor for: %s xmlTag: %s fieldCount: %s fieldValue: %s, Status: %s" \
            %( MsgNetworkAddressInterest, MsgXMLTag, MsgCountField, MsgFieldValues, MsgDataStatus))

    return

def Decode8040(self, Devices, MsgData, MsgRSSI) : # Network Address response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgIEEE=MsgData[4:20]
    MsgShortAddress=MsgData[20:24]
    MsgNumAssocDevices=MsgData[24:26]
    MsgStartIndex=MsgData[26:28]
    MsgDeviceList=MsgData[28:len(MsgData)]
    
    loggingInput( self, 'Status', "Network Address response, Sequence number : " + MsgSequenceNumber + " Status : " 
                        + DisplayStatusCode( MsgDataStatus ) + " IEEE : " + MsgIEEE + " Short Address : " + MsgShortAddress 
                        + " number of associated devices : " + MsgNumAssocDevices + " Start Index : " + MsgStartIndex + " Device List : " + MsgDeviceList)
    return

def Decode8041(self, Devices, MsgData, MsgRSSI) : # IEEE Address response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgIEEE=MsgData[4:20]
    MsgShortAddress=MsgData[20:24]
    MsgNumAssocDevices=MsgData[24:26]
    MsgStartIndex=MsgData[26:28]
    MsgDeviceList=MsgData[28:len(MsgData)]

    loggingInput( self, 'Log',"Decode8041 - IEEE Address response, Sequence number : " + MsgSequenceNumber + " Status : " 
                    + DisplayStatusCode( MsgDataStatus ) + " IEEE : " + MsgIEEE + " Short Address : " + MsgShortAddress 
                    + " number of associated devices : " + MsgNumAssocDevices + " Start Index : " + MsgStartIndex + " Device List : " + MsgDeviceList)


    timeStamped( self, MsgShortAddress , 0x8041)
    loggingMessages( self, '8041', MsgShortAddress, MsgIEEE, MsgRSSI, MsgSequenceNumber)
    lastSeenUpdate( self, Devices, NwkId=MsgShortAddress)

    if self.ListOfDevices[MsgShortAddress]['Status'] == "8041" :        # We have requested a IEEE address for a Short Address, 
                                                                        # hoping that we can reconnect to an existing Device
        if DeviceExist(self, Devices, MsgShortAddress, MsgIEEE ) == True :
            loggingInput( self, 'Log',"Decode 8041 - Device details : " +str(self.ListOfDevices[MsgShortAddress]) )
        else :
            Domoticz.Error("Decode 8041 - Unknown device : " +str(MsgShortAddress) + " IEEE : " +str(MsgIEEE) )
    
    return

def Decode8042(self, Devices, MsgData, MsgRSSI) : # Node Descriptor response

    MsgLen=len(MsgData)

    sequence=MsgData[0:2]
    status=MsgData[2:4]
    addr=MsgData[4:8]
    manufacturer=MsgData[8:12]
    max_rx=MsgData[12:16]
    max_tx=MsgData[16:20]
    server_mask=MsgData[20:24]
    descriptor_capability=MsgData[24:26]
    mac_capability=MsgData[26:28]
    max_buffer=MsgData[28:30]
    bit_field=MsgData[30:34]

    loggingInput( self, 'Debug', "Decode8042 - Reception Node Descriptor for : " +addr + " SEQ : " + sequence + " Status : " + status +" manufacturer :" + manufacturer + " mac_capability : "+str(mac_capability) + " bit_field : " +str(bit_field) , addr)

    if addr not in self.ListOfDevices:
        loggingInput( self, 'Log',"Decode8042 receives a message from a non existing device %s" %addr)
        return

    self.ListOfDevices[addr]['Max Buffer Size'] = max_buffer
    self.ListOfDevices[addr]['Max Rx'] = max_rx
    self.ListOfDevices[addr]['Max Tx'] = max_tx

    mac_capability = int(mac_capability,16)

    if mac_capability == 0x0000:
        return

    AltPAN      =   ( mac_capability & 0x00000001 )
    DeviceType  =   ( mac_capability >> 1 ) & 1
    PowerSource =   ( mac_capability >> 2 ) & 1
    ReceiveonIdle = ( mac_capability >> 3 ) & 1

    
    if DeviceType == 1 : 
        DeviceType = "FFD"
    else : 
        DeviceType = "RFD"
    if ReceiveonIdle == 1 : 
        ReceiveonIdle = "On"
    else : 
        ReceiveonIdle = "Off"
    if PowerSource == 1 :
        PowerSource = "Main"
    else :
        PowerSource = "Battery"

    loggingInput( self, 'Debug', "Decode8042 - Alternate PAN Coordinator = " +str(AltPAN ), addr)    # 1 if node is capable of becoming a PAN coordinator
    loggingInput( self, 'Debug', "Decode8042 - Receiver on Idle = " +str(ReceiveonIdle), addr)     # 1 if the device does not disable its receiver to 
                                                                            # conserve power during idle periods.
    loggingInput( self, 'Debug', "Decode8042 - Power Source = " +str(PowerSource), addr)            # 1 if the current power source is mains power. 
    loggingInput( self, 'Debug', "Decode8042 - Device type  = " +str(DeviceType), addr)            # 1 if this node is a full function device (FFD). 

    bit_fieldL   = int(bit_field[2:4],16)
    bit_fieldH   = int(bit_field[0:2],16)
    LogicalType =   bit_fieldL & 0x00F
    if   LogicalType == 0 : LogicalType = "Coordinator"
    elif LogicalType == 1 : LogicalType = "Router"
    elif LogicalType == 2 : LogicalType = "End Device"
    loggingInput( self, 'Debug', "Decode8042 - bit_field = " +str(bit_fieldL) +" : "+str(bit_fieldH) , addr)
    loggingInput( self, 'Debug', "Decode8042 - Logical Type = " +str(LogicalType) , addr)

    if self.ListOfDevices[addr]['Status'] != "inDB" :
        if self.pluginconf.pluginConf['capturePairingInfos'] and addr in self.DiscoveryDevices :
            self.DiscoveryDevices[addr]['Manufacturer'] = manufacturer # Manufacturer Code
            self.DiscoveryDevices[addr]['8042'] = MsgData
            self.DiscoveryDevices[addr]['DeviceType'] = str(DeviceType)
            self.DiscoveryDevices[addr]['LogicalType'] = str(LogicalType)
            self.DiscoveryDevices[addr]['PowerSource'] = str(PowerSource)
            self.DiscoveryDevices[addr]['ReceiveOnIdle'] = str(ReceiveonIdle)

    #if 'Model' in self.ListOfDevices[addr]:
    #    if self.ListOfDevices[addr]['Model'] != {}:
    #        if self.ListOfDevices[addr]['Model'] == 'TI0001':
    #            return

    self.ListOfDevices[addr]['Manufacturer']=manufacturer
    self.ListOfDevices[addr]['DeviceType']=str(DeviceType)
    self.ListOfDevices[addr]['LogicalType']=str(LogicalType)
    self.ListOfDevices[addr]['PowerSource']=str(PowerSource)
    self.ListOfDevices[addr]['ReceiveOnIdle']=str(ReceiveonIdle)


    return

def Decode8043(self, Devices, MsgData, MsgRSSI) : # Reception Simple descriptor response
    MsgLen=len(MsgData)

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataLenght=MsgData[8:10]

    updSQN( self, MsgDataShAddr, MsgDataSQN)

    if int(MsgDataLenght,16) == 0 : return

    MsgDataEp=MsgData[10:12]
    MsgDataProfile=MsgData[12:16]
    MsgDataDeviceId=MsgData[16:20]
    MsgDataBField=MsgData[20:22]
    MsgDataInClusterCount=MsgData[22:24]

    if MsgDataShAddr == '0000': # Ep list for Zigate
        receiveZigateEpDescriptor( self, MsgData)
        return
    elif MsgDataShAddr not in self.ListOfDevices:
        Domoticz.Error("Decode8043 - receive message for non existing device")
        return

    if self.pluginconf.pluginConf['capturePairingInfos']:
        if MsgDataShAddr not in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgDataShAddr] = {}
        if 'Ep' not in self.DiscoveryDevices[MsgDataShAddr]:
            self.DiscoveryDevices[MsgDataShAddr]['Ep'] = {}
        if MsgDataEp not in self.DiscoveryDevices[MsgDataShAddr]['Ep']:
            self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ProfileID'] = ''
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ZDeviceID'] = ''
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ClusterIN'] = []
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ClusterOUT'] = []
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['8043'] = MsgData  

    if int(MsgDataProfile,16) == 0xC05E and int(MsgDataDeviceId,16) == 0xE15E:
        # ZLL Commissioning EndPoint / Jaiwel
        loggingInput( self, 'Log',"Decode8043 - Received ProfileID: %s, ZDeviceID: %s - skip" %(MsgDataProfile, MsgDataDeviceId))
        if MsgDataEp in self.ListOfDevices[MsgDataShAddr]['Ep']:
            del self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp]
        if 'NbEp' in  self.ListOfDevices[MsgDataShAddr]:
            if self.ListOfDevices[MsgDataShAddr]['NbEp'] > '1':
                self.ListOfDevices[MsgDataShAddr]['NbEp'] = int( self.ListOfDevices[MsgDataShAddr]['NbEp']) - 1
        return

    loggingInput( self, 'Status', "[%s] NEW OBJECT: %s Simple Descriptor Response EP: 0x%s RSSI: %s" %('-', MsgDataShAddr, MsgDataEp, int(MsgRSSI,16)))

    if 'ProfileID' in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]['ProfileID'] != MsgDataProfile:
            #loggingInput( self, 'Log',"Decode8043 - Overwrite ProfileID %s with %s from Ep: %s " \
            #        %( self.ListOfDevices[MsgDataShAddr]['ProfileID'] , MsgDataProfile, MsgDataEp))
            pass
    self.ListOfDevices[MsgDataShAddr]['ProfileID'] = MsgDataProfile
    loggingInput( self, 'Status', "[%s]    NEW OBJECT: %s ProfileID %s" %('-', MsgDataShAddr, MsgDataProfile))

    if self.pluginconf.pluginConf['capturePairingInfos']:
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ProfileID'] = MsgDataProfile

    if 'ZDeviceID' in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] != MsgDataDeviceId:
            #loggingInput( self, 'Log',"Decode8043 - Overwrite ZDeviceID %s with %s from Ep: %s " \
            #        %( self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] , MsgDataDeviceId, MsgDataEp))
            pass
    self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] = MsgDataDeviceId
    loggingInput( self, 'Status', "[%s]    NEW OBJECT: %s ZDeviceID %s" %('-', MsgDataShAddr, MsgDataDeviceId))

    # Decode Bit Field
    # Device version: 4 bits (bits 0-4)
    # eserved: 4 bits (bits4-7)
    DeviceVersion = int(MsgDataBField ,16) & 0x00001111
    self.ListOfDevices[MsgDataShAddr]['ZDeviceVersion'] = '%04x' %DeviceVersion
    loggingInput( self, 'Status', "[%s]    NEW OBJECT: %s Application Version %s" %('-', MsgDataShAddr,  self.ListOfDevices[MsgDataShAddr]['ZDeviceVersion']))

    if self.pluginconf.pluginConf['capturePairingInfos']:
        self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ZDeviceID'] = MsgDataDeviceId

    # Decoding Cluster IN
    loggingInput( self, 'Status', "[%s]    NEW OBJECT: %s Cluster IN Count: %s" %('-', MsgDataShAddr, MsgDataInClusterCount))
    idx = 24
    i=1
    if int(MsgDataInClusterCount,16)>0 :
        while i <= int(MsgDataInClusterCount,16) :
            MsgDataCluster=MsgData[idx+((i-1)*4):idx+(i*4)]
            if 'ConfigSource' in self.ListOfDevices[MsgDataShAddr]:
                if self.ListOfDevices[MsgDataShAddr]['ConfigSource'] != 'DeviceConf':
                    if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Ep']:
                        self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
                    if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                        self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster] = {}
                else:
                    loggingPairing( self, 'Debug', "[%s]    NEW OBJECT: %s we keep DeviceConf info" %('-',MsgDataShAddr))
            else: # Not 'ConfigSource'
                self.ListOfDevices[MsgDataShAddr]['ConfigSource'] = '8043'
                if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Ep']:
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}

            if MsgDataCluster in ZCL_CLUSTERS_LIST:
                loggingInput( self, 'Status', "[%s]       NEW OBJECT: %s Cluster In %s: %s (%s)" %('-', MsgDataShAddr, i, MsgDataCluster, ZCL_CLUSTERS_LIST[MsgDataCluster]))
            else:
                loggingInput( self, 'Status', "[%s]       NEW OBJECT: %s Cluster In %s: %s" %('-', MsgDataShAddr, i, MsgDataCluster))

            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ClusterIN'].append( MsgDataCluster )
            MsgDataCluster=""
            i=i+1


    # Decoding Cluster Out
    idx = 24 + int(MsgDataInClusterCount,16) *4
    MsgDataOutClusterCount=MsgData[idx:idx+2]

    loggingInput( self, 'Status', "[%s]    NEW OBJECT: %s Cluster OUT Count: %s" %('-', MsgDataShAddr, MsgDataOutClusterCount))
    idx += 2
    i=1
    if int(MsgDataOutClusterCount,16)>0 :
        while i <= int(MsgDataOutClusterCount,16) :
            MsgDataCluster = MsgData[idx+((i-1)*4):idx+(i*4)]
            if 'ConfigSource' in self.ListOfDevices[MsgDataShAddr]:
                if self.ListOfDevices[MsgDataShAddr]['ConfigSource'] != 'DeviceConf':
                    if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Ep']:
                        self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
                    if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                        self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
                else:
                    loggingInput( self, 'Debug', "[%s]    NEW OBJECT: %s we keep DeviceConf info" %('-',MsgDataShAddr), MsgDataShAddr)
            else: # Not 'ConfigSource'
                self.ListOfDevices[MsgDataShAddr]['ConfigSource'] = '8043'
                if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Ep']:
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}

            if MsgDataCluster in ZCL_CLUSTERS_LIST:
                loggingInput( self, 'Status', "[%s]       NEW OBJECT: %s Cluster Out %s: %s (%s)" %('-', MsgDataShAddr, i, MsgDataCluster, ZCL_CLUSTERS_LIST[MsgDataCluster]))
            else:
                loggingInput( self, 'Status', "[%s]       NEW OBJECT: %s Cluster Out %s: %s" %('-', MsgDataShAddr, i, MsgDataCluster))

            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[MsgDataShAddr]['Ep'][MsgDataEp]['ClusterOUT'].append( MsgDataCluster )

            MsgDataCluster=""
            i=i+1

    if self.ListOfDevices[MsgDataShAddr]['Status'] != "inDB" :
        self.ListOfDevices[MsgDataShAddr]['Status'] = "8043"
        self.ListOfDevices[MsgDataShAddr]['Heartbeat'] = "0"
    else :
        updSQN( self, MsgDataShAddr, MsgDataSQN)

    loggingPairing( self, 'Debug', "Decode8043 - Processed " + MsgDataShAddr + " end results is : " + str(self.ListOfDevices[MsgDataShAddr]) )
    return

def Decode8044(self, Devices, MsgData, MsgRSSI): # Power Descriptior response
    MsgLen=len(MsgData)
    SQNum=MsgData[0:2]
    Status=MsgData[2:4]
    bit_fields=MsgData[4:8]

    # Not Short address, nor IEEE. Hard to relate to a device !

    power_mode = bit_fields[0]
    power_source = bit_fields[1]
    current_power_source = bit_fields[2]
    current_power_level = bit_fields[3]

    loggingInput( self, 'Debug', "Decode8044 - SQNum = " +SQNum +" Status = " + Status + " Power mode = " + power_mode + " power_source = " + power_source + " current_power_source = " + current_power_source + " current_power_level = " + current_power_level )
    return

def Decode8045(self, Devices, MsgData, MsgRSSI) : # Reception Active endpoint response
    MsgLen=len(MsgData)

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataEpCount=MsgData[8:10]

    MsgDataEPlist=MsgData[10:len(MsgData)]

    loggingPairing( self, 'Debug', "Decode8045 - Reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + DisplayStatusCode( MsgDataStatus ) + ", short Addr " + MsgDataShAddr + ", List " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)

    if self.pluginconf.pluginConf['capturePairingInfos']:
        if MsgDataShAddr not in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgDataShAddr] = {}
        self.DiscoveryDevices[MsgDataShAddr]['8045'] = MsgData

    OutEPlist=""
    
    # Special Case, where we build the Zigate list of clusters
    if MsgDataShAddr == '0000':
        receiveZigateEpList( self, MsgDataEpCount, MsgDataEPlist)
        return

    if DeviceExist(self, Devices, MsgDataShAddr) == False:
        #Pas sur de moi, mais si le device n'existe pas, je vois pas pkoi on continuerait
        Domoticz.Error("Decode8045 - KeyError : MsgDataShAddr = " + MsgDataShAddr)
        return
    else :
        if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
            self.ListOfDevices[MsgDataShAddr]['Status']="8045"
        else :
            updSQN( self, MsgDataShAddr, MsgDataSQN)
            
        i=0
        while i < 2 * int(MsgDataEpCount,16) :
            tmpEp = MsgDataEPlist[i:i+2]
            if not self.ListOfDevices[MsgDataShAddr]['Ep'].get(tmpEp) :
                self.ListOfDevices[MsgDataShAddr]['Ep'][tmpEp] = {}
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[MsgDataShAddr]['Ep'][tmpEp] = {}
            loggingInput( self, 'Status', "[%s] NEW OBJECT: %s Active Endpoint Response Ep: %s RSSI: %s" %( '-', MsgDataShAddr, tmpEp, int(MsgRSSI,16)))
            i += 2

        self.ListOfDevices[MsgDataShAddr]['NbEp'] =  str(int(MsgDataEpCount,16))     # Store the number of EPs
        if self.pluginconf.pluginConf['capturePairingInfos']:
            self.DiscoveryDevices[MsgDataShAddr]['NbEp'] = MsgDataEpCount

        for iterEp in self.ListOfDevices[MsgDataShAddr]['Ep']:
            loggingInput( self, 'Status', "[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" %( '-', MsgDataShAddr, iterEp))
            sendZigateCmd(self,"0043", str(MsgDataShAddr)+str(iterEp))
        if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
            self.ListOfDevices[MsgDataShAddr]['Heartbeat'] = "0"
            self.ListOfDevices[MsgDataShAddr]['Status'] = "0043"

        loggingPairing( self, 'Debug', "Decode8045 - Device : " + str(MsgDataShAddr) + " updated ListofDevices with " + str(self.ListOfDevices[MsgDataShAddr]['Ep']) )

    return

def Decode8046(self, Devices, MsgData, MsgRSSI) : # Match Descriptor response
    MsgLen=len(MsgData)

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataLenList=MsgData[8:10]
    MsgDataMatchList=MsgData[10:len(MsgData)]

    updSQN( self, MsgDataShAddr, MsgDataSQN)
    loggingInput( self, 'Log',"Decode8046 - Match Descriptor response : SQN : " + MsgDataSQN + ", Status " + DisplayStatusCode( MsgDataStatus ) + ", short Addr " + MsgDataShAddr + ", Lenght list  " + MsgDataLenList + ", Match list " + MsgDataMatchList)
    return

def Decode8047(self, Devices, MsgData, MsgRSSI) : # Management Leave response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]

    loggingInput( self, 'Status', "Decode8047 - Leave response, RSSI: %s Status: %s - %s" \
            %( MsgRSSI, MsgDataStatus, DisplayStatusCode( MsgDataStatus )))

    return

def Decode8048(self, Devices, MsgData, MsgRSSI) : # Leave indication
    MsgLen=len(MsgData)

    MsgExtAddress=MsgData[0:16]
    MsgDataStatus=MsgData[16:18]
    
    devName = ''
    for x in Devices:
        if Devices[x].DeviceID == MsgExtAddress:
            devName = Devices[x].Name
            break
    self.adminWidgets.updateNotificationWidget( Devices, 'Leave indication from %s for %s ' %(MsgExtAddress, devName) )

    loggingMessages( self, '8048', None, MsgExtAddress, MsgRSSI, None)

    if MsgExtAddress not in self.IEEE2NWK: # Most likely this object has been removed and we are receiving the confirmation.
        return
    sAddr = getSaddrfromIEEE( self, MsgExtAddress )

    loggingInput( self, 'Debug', "Leave indication from IEEE: %s , Status: %s " %(MsgExtAddress, MsgDataStatus), sAddr)
    if sAddr == '' :
        loggingInput( self, 'Log',"Decode8048 - device not found with IEEE = " +str(MsgExtAddress) )
    else :
        timeStamped(self, sAddr, 0x8048)
        zdevname = ''
        if 'ZDeviceName' in self.ListOfDevices[sAddr]:
            zdevname = self.ListOfDevices[sAddr]['ZDeviceName']
        loggingInput( self, 'Status', "%s (%s/%s) send a Leave indication and will be outside of the network. RSSI: %s" %(zdevname, sAddr, MsgExtAddress, MsgRSSI))
        if self.ListOfDevices[sAddr]['Status'] == 'inDB':
            self.ListOfDevices[sAddr]['Status'] = 'Left'
            self.ListOfDevices[sAddr]['Heartbeat'] = 0
            #Domoticz.Status("Calling leaveMgt to request a rejoin of %s/%s " %( sAddr, MsgExtAddress))
            #leaveMgtReJoin( self, sAddr, MsgExtAddress )
        elif self.ListOfDevices[sAddr]['Status'] == 'Left':
            Domoticz.Error("Receiving a leave from %s/%s while device is %s status" %( sAddr, MsgExtAddress, self.ListOfDevices[sAddr]['Status']))

            # This is bugy, as I should then remove the device in Domoticz
            #loggingInput( self, 'Log',"--> Removing: %s" %str(self.ListOfDevices[sAddr]))
            #del self.ListOfDevices[sAddr]
            #del self.IEEE2NWK[MsgExtAddress]

            # Will set to Leave in order to protect Domoticz Widget, Just need to make sure that we can reconnect at a point of time
            self.ListOfDevices[sAddr]['Status'] = 'Leave'
            self.ListOfDevices[sAddr]['Heartbeat'] = 0

    return

def Decode8049(self, Devices, MsgData, MsgRSSI) : # E_SL_MSG_PERMIT_JOINING_RESPONSE

    loggingInput( self, 'Log',"Decode8049 - MsgData: %s" %MsgData)

def Decode804A(self, Devices, MsgData, MsgRSSI) : # Management Network Update response

    if self.networkenergy:
        self.networkenergy.NwkScanResponse( MsgData)
    return

def Decode804B(self, Devices, MsgData, MsgRSSI) : # System Server Discovery response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgServerMask=MsgData[4:8]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 804B - System Server Discovery response, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Server Mask : " + MsgServerMask)
    return

def Decode804E( self, Devices, MsgData, MsgRSSI):

    loggingInput( self, 'Debug', "Decode804E - Receive message")
    if self.networkmap:
        self.networkmap.LQIresp( MsgData )

#Group response
# Implemented in z_GrpMgt.py
def Decode8060( self, Devices, MsgData, MsgRSSI):

    self.groupmgt.addGroupResponse( MsgData )

def Decode8061( self, Devices, MsgData, MsgRSSI):

    self.groupmgt.viewGroupResponse( MsgData )

def Decode8062( self, Devices, MsgData, MsgRSSI):

    self.groupmgt.getGroupMembershipResponse(MsgData)

def Decode8063( self, Devices, MsgData, MsgRSSI):

    self.groupmgt.removeGroupResponse( MsgData )


#Reponses SCENE
def Decode80A0(self, Devices, MsgData, MsgRSSI) : # View Scene response

    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    MsgSceneTransitonTime=MsgData[16:20]
    MSgSceneNameLength=MsgData[20:22]
    MSgSceneNameLengthMax=MsgData[22:24]
    #<scene name data: data each element is uint8_t>
    #<extensions length: uint16_t>
    #<extensions max length: uint16_t>
    #<extensions data: data each element is uint8_t>
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 80A0 - View Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
    return

def Decode80A1(self, Devices, MsgData, MsgRSSI) : # Add Scene response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 80A1 - Add Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

def Decode80A2(self, Devices, MsgData, MsgRSSI) : # Remove Scene response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 80A2 - Remove Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

def Decode80A3(self, Devices, MsgData, MsgRSSI) : # Remove All Scene response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 80A3 - Remove All Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
    return

def Decode80A4(self, Devices, MsgData, MsgRSSI) : # Store Scene response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    loggingInput( self, 'Log',"ZigateRead - MsgType 80A4 - Store Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return
    
def Decode80A6(self, Devices, MsgData, MsgRSSI) : # Scene Membership response

    MsgSrcAddr = MsgData[len(MsgData)-4: len(MsgData)]

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgCapacity=int(MsgData[10:12],16)
    MsgGroupID=MsgData[12:16]
    MsgSceneCount=int(MsgData[16:18],16)

    loggingInput( self, 'Log',"Decode80A6 - Scene Membership response - MsgSrcAddr: %s MsgEP: %s MsgGroupID: %s MsgClusterID: %s MsgDataStatus: %s MsgCapacity: %s MsgSceneCount: %s"
        %(MsgSrcAddr, MsgEP, MsgGroupID,MsgClusterID, MsgDataStatus, MsgCapacity, MsgSceneCount))
    if MsgDataStatus != '00':
        loggingInput( self, 'Log',"Decode80A6 - Scene Membership response - MsgSrcAddr: %s MsgEP: %s MsgClusterID: %s MsgDataStatus: %s" %(MsgSrcAddr, MsgEP, MsgClusterID, MsgDataStatus))
        return

    if MsgSceneCount > MsgCapacity:
        loggingInput( self, 'Log',"Decode80A6 - Scene Membership response MsgSceneCount %s > MsgCapacity %s" %(MsgSceneCount, MsgCapacity))
        return

    MsgSceneList=MsgData[18: 18+MsgSceneCount*2]
    if len(MsgData) > 18+MsgSceneCount*2:
        MsgSrcAddr = MsgData[18+MsgSceneCount*2 : (18+MsgSceneCount*2) + 4]
    idx = 0
    MsgScene = []
    while idx < MsgSceneCount:
        scene = MsgSceneList[ idx: idx*2]
        if scene not in MsgScene:
            MsgScene.append( scene )
    loggingInput( self, 'Log',"           - Scene List: %s" %(str(MsgScene)))

def Decode0100(self, Devices, MsgData, MsgRSSI) :  # Read Attribute request
    # Seems to come with Livolo and Firmware 3.1b

    MsgMode = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgDstEp = MsgData[8:10]
    MsgUnknown = MsgData[10:30]
    MsgStatus = MsgData[30:32]

    # What is expected on the Widget is:
    # Left Off: 00
    # Left On: 01
    # Right Off: 02
    # Right On: 03
    loggingInput( self, 'Debug', "Decode0100 - Livolo %s/%s Data: %s" %(MsgSrcAddr, MsgSrcEp, MsgStatus), MsgSrcAddr)

    brand = ''
    if MsgSrcAddr not in self.ListOfDevices:
        return
    if 'Manufacturer Name' in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]['Manufacturer Name'] == 'LIVOLO':
            brand = 'Livolo'
    if 'Model' in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]['Model'] == 'TI0001':
            brand = 'Livolo'

    if brand == 'Livolo':
        if 'Ep' not in self.ListOfDevices[MsgSrcAddr]:
            return
        if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]['Ep']:
            return
        if '0006' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
            return
    
        if MsgStatus == '00': # Left / Single - Off
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', '00')
        elif MsgStatus == '01': # Left / Single - On
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', '01')
        if MsgStatus == '02': # Right - Off
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', '00')
        elif MsgStatus == '03': # Right - On
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, '0006', '01')
    
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']['0000'] = MsgStatus
    else:
        Domoticz.Log("Decode0100 - Request from %s/%s Data: %s Status: %s" %(MsgSrcAddr, MsgSrcEp, MsgUnknown, MsgStatus))

#Reponses Attributs
def Decode8100(self, Devices, MsgData, MsgRSSI) :  # Report Individual Attribute response
    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    MsgAttrID = MsgData[12:16]
    MsgAttrStatus = MsgData[16:18]
    MsgAttType=MsgData[18:20]
    MsgAttSize=MsgData[20:24]
    MsgClusterData=MsgData[24:len(MsgData)]

    loggingInput( self, 'Debug', "Decode8100 - Report Attributes Response : [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" \
            %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)

    timeStamped( self, MsgSrcAddr , 0x8100)
    loggingMessages( self, '8100', MsgSrcAddr, None, MsgRSSI, MsgSQN)
    try :
        self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
    except : 
        self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

        if self.pluginconf.pluginConf['debugRSSI']:
            if self.ListOfDevices[MsgSrcAddr]['RSSI'] <= self.pluginconf.pluginConf['debugRSSI']:
                if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                    if self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != '' and self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != {}:
                        loggingInput( self, 'Log',"Decode8100 - RSSI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)%s" \
                                %(self.ListOfDevices[MsgSrcAddr]['RSSI'], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp, self.ListOfDevices[MsgSrcAddr]['ZDeviceName']))
                    else:
                        loggingInput( self, 'Log',"Decode8100 - RSSI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)" \
                                %(self.ListOfDevices[MsgSrcAddr]['RSSI'], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp))
                else:
                    loggingInput( self, 'Log',"Decode8100 - RSSI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)" \
                            %(self.ListOfDevices[MsgSrcAddr]['RSSI'], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp))

    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Health' in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
    updSQN( self, MsgSrcAddr, MsgSQN)
    ReadCluster(self, Devices, MsgData) 
    callbackDeviceAwake( self, MsgSrcAddr, MsgSrcEp, MsgClusterId)

    return

def Decode8101(self, Devices, MsgData, MsgRSSI) :  # Default Response
    MsgDataSQN=MsgData[0:2]
    MsgDataEp=MsgData[2:4]
    MsgClusterId=MsgData[4:8]
    MsgDataCommand=MsgData[8:10]
    MsgDataStatus=MsgData[10:12]
    loggingInput( self, 'Debug', "Decode8101 - Default response - SQN: %s, EP: %s, ClusterID: %s , DataCommand: %s, - Status: [%s] %s" \
            %(MsgDataSQN, MsgDataEp, MsgClusterId, MsgDataCommand, MsgDataStatus,  DisplayStatusCode( MsgDataStatus ) ))
    return

def Decode8102(self, Devices, MsgData, MsgRSSI) :  # Report Individual Attribute response
    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    MsgAttrID=MsgData[12:16]
    MsgAttStatus=MsgData[16:18]
    MsgAttType=MsgData[18:20]
    MsgAttSize=MsgData[20:24]
    MsgClusterData=MsgData[24:len(MsgData)]

    loggingInput( self, 'Debug', "Decode8102 - Read Attributes Response : [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" \
            %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)

    if self.PluzzyFirmware:
        loggingInput( self, 'Log', "Patching payload:", MsgSrcAddr)
        _type = MsgAttStatus
        _status = MsgAttType
        _size = MsgAttSize
        _data = MsgClusterData

        _newsize = '00' + _size[0:2]
        _newdata = MsgAttSize[2:4] + MsgClusterData

        loggingInput( self, 'Log', " MsgAttStatus: %s -> %s" %(MsgAttStatus, _status), MsgSrcAddr)
        loggingInput( self, 'Log', " MsgAttType: %s -> %s" %(MsgAttType, _type), MsgSrcAddr)
        loggingInput( self, 'Log', " MsgAttSize: %s -> %s" %(MsgAttSize, _newsize), MsgSrcAddr)
        loggingInput( self, 'Log', " MsgClusterData: %s -> %s" %(MsgClusterData, _newdata), MsgSrcAddr)

        MsgAttStatus = _status
        MsgAttType = _type
        MsgAttSize = _newsize
        MsgClusterData = _newdata
        MsgData = MsgSQN + MsgSrcAddr + MsgSrcEp + MsgClusterId + MsgAttrID + MsgAttStatus + MsgAttType + MsgAttSize + MsgClusterData
        pluzzyDecode8102( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, MsgRSSI)

    loggingMessages( self, '8102', MsgSrcAddr, None, MsgRSSI, MsgSQN)

    if DeviceExist(self, Devices, MsgSrcAddr) == True :
        try:
            self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
        except:
            self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

        if self.pluginconf.pluginConf['debugRSSI']:
            if self.ListOfDevices[MsgSrcAddr]['RSSI'] <= self.pluginconf.pluginConf['debugRSSI']:
                if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
                    if self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != '' and self.ListOfDevices[MsgSrcAddr]['ZDeviceName'] != {}:
                        loggingInput( self, 'Log',"Decode8102 - RSSI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)%s" \
                                %(self.ListOfDevices[MsgSrcAddr]['RSSI'], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp, self.ListOfDevices[MsgSrcAddr]['ZDeviceName']))
                    else:
                        loggingInput( self, 'Log',"Decode8102 - RSSI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)" \
                                %(self.ListOfDevices[MsgSrcAddr]['RSSI'], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp))
                else:
                    loggingInput( self, 'Log',"Decode8102 - RSSI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)" \
                            %(self.ListOfDevices[MsgSrcAddr]['RSSI'], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp))



        loggingInput( self, 'Debug2', "Decode8102 : Attribute Report from " + str(MsgSrcAddr) + " SQN = " + str(MsgSQN) + " ClusterID = " 
                        + str(MsgClusterId) + " AttrID = " +str(MsgAttrID) + " Attribute Data = " + str(MsgClusterData) , MsgSrcAddr)

        lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
        if 'Health' in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
        timeStamped( self, MsgSrcAddr , 0x8102)
        updSQN( self, MsgSrcAddr, str(MsgSQN) )
        ReadCluster(self, Devices, MsgData) 
        callbackDeviceAwake( self, MsgSrcAddr, MsgSrcEp, MsgClusterId)
    else :
        # This device is unknown, and we don't have the IEEE to check if there is a device coming with a new sAddr
        # Will request in the next hearbeat to for a IEEE request
        ieee = lookupForIEEE( self, MsgSrcAddr , True)
        if ieee:
            loggingInput( self, 'Log',"Found IEEE for short address: %s is %s" %(MsgSrcAddr, ieee))
        else:
            # If we didn't find it, let's trigger a NetworkMap scan if not one in progress
            if self.networkmap:
                if not self.networkmap.NetworkMapPhase():
                    loggingInput( self, 'Status',"Trigger a Network Scan in order to update Neighbours Tables", MsgSrcAddr)
                    self.networkmap.start_scan()

            loggingInput( self, 'Log',"Decode8102 - Receiving a message from unknown device : " + str(MsgSrcAddr) + " with Data : " +str(MsgData) )
            loggingInput( self, 'Log',"           - [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" \
                %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData ), MsgSrcAddr)
    
            # This should work only for FFD devices ( Receive on idle )
            loggingInput( self, 'Log',"Request for IEEE for short address: %s" %(MsgSrcAddr))
            u8RequestType = '00'
            u8StartIndex = '00'
            sendZigateCmd(self ,'0041', '02' + MsgSrcAddr + u8RequestType + u8StartIndex )
    return

def Decode8110(self, Devices, MsgData, MsgRSSI) :  # Write Attribute response
    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    MsgAttrID=MsgData[12:16]
    MsgAttType=MsgData[16:18]
    MsgAttSize=MsgData[18:22]
    MsgClusterData=MsgData[22:len(MsgData)]

    loggingInput( self, 'Debug', "Decode8110 - WriteAttributeResponse - MsgSQN: %s, MsgSrcAddr: %s, MsgSrcEp: %s, MsgClusterId: %s, MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
            %( MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)

    timeStamped( self, MsgSrcAddr , 0x8110)
    updSQN( self, MsgSrcAddr, MsgSQN)

    if MsgClusterId == "0500":
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 3, MsgClusterData)

    return

def Decode8120(self, Devices, MsgData, MsgRSSI) :  # Configure Reporting response

    loggingInput( self, 'Debug', "Decode8120 - Configure reporting response : %s" %MsgData)
    if len(MsgData) < 14:
        Domoticz.Error("Decode8120 - uncomplet message %s " %MsgData)
        return

    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    RemainData = MsgData[12:len(MsgData)]

    loggingInput( self, 'Debug', "--> SQN: %s, SrcAddr: %s, SrcEP: %s, ClusterID: %s, RemainData: %s" %(MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, RemainData), MsgSrcAddr)


    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("Decode8120 - receiving Configure reporting response from unknow  %s" %MsgSrcAddr)
        return


    elif len(MsgData) == 14: # Firmware < 3.0f
        MsgDataStatus=MsgData[12:14]
    else:
        MsgAttribute = []
        nbattribute = int(( len(MsgData) - 14 ) // 4)
        idx = 0
        while idx < nbattribute :
            MsgAttribute.append( MsgData[(12+(idx*4)):(12+(idx*4))+4] )
            idx += 1
        loggingInput( self, 'Debug', "--> nbAttribute: %s, idx: %s" %(nbattribute, idx), MsgSrcAddr)
        MsgDataStatus = MsgData[(12+(nbattribute*4)):(12+(nbattribute*4)+2)]
        loggingInput( self, 'Debug', "--> Attributes : %s status: %s " %(str(MsgAttribute), MsgDataStatus), MsgSrcAddr)

    loggingInput( self, 'Debug', "Decode8120 - Configure Reporting response - ClusterID: %s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s - %s" \
       %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgDataStatus, DisplayStatusCode( MsgDataStatus) ), MsgSrcAddr)

    timeStamped( self, MsgSrcAddr , 0x8120)
    updSQN( self, MsgSrcAddr, MsgSQN)

    if 'ConfigureReporting' in self.ListOfDevices[MsgSrcAddr]:
        if 'Ep' in self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']:
            if MsgSrcEp in self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep']:
                if str(MsgClusterId) not in self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp]:
                    self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}
            else:
                self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp] = {}
                self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}
        else:
            self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'] = {}
            self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp] = {}
            self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}
    else:
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting'] = {}
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'] = {}
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp] = {}
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}

    self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][MsgClusterId] = MsgDataStatus

    if MsgDataStatus != '00':
        # Looks like that this Device doesn't handle Configure Reporting, so let's flag it as such, so we won't do it anymore
        loggingInput( self, 'Debug', "Decode8120 - Configure Reporting response - ClusterID: %s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s - %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgDataStatus, DisplayStatusCode( MsgDataStatus) ), MsgSrcAddr)
    return

def Decode8140(self, Devices, MsgData, MsgRSSI) :  # Attribute Discovery response
    MsgComplete=MsgData[0:2]
    MsgAttType=MsgData[2:4]
    MsgAttID=MsgData[4:8]
    
    if len(MsgData) > 8:
        MsgSrcAddr = MsgData[8:12]
        MsgSrcEp = MsgData[12:14]
        MsgClusterID = MsgData[14:18]

        loggingInput( self, 'Debug', "Decode8140 - Attribute Discovery Response - %s/%s - Cluster: %s - Attribute: %s - Attribute Type: %s Complete: %s"
            %( MsgSrcAddr, MsgSrcEp, MsgClusterID, MsgAttID, MsgAttType, MsgComplete), MsgSrcAddr)
        
        if MsgSrcAddr not in self.ListOfDevices:
            return

        if 'Attributes List' not in  self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['Attributes List'] = {}
            self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'] = {}
        if 'Ep' not in self.ListOfDevices[MsgSrcAddr]['Attributes List']:
            self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'] = {}
        if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep']:
            self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp] = {}
        if MsgClusterID not in  self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp]:
            self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID] = {}
        if MsgAttID not in self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID]:
            self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID] = MsgAttType

        if self.pluginconf.pluginConf['capturePairingInfos'] and MsgSrcAddr in self.DiscoveryDevices :
            if 'Attribute Discovery' not in  self.DiscoveryDevices[MsgSrcAddr]:
                self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery'] = {}
                self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'] = {}
            if MsgSrcEp not in  self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep']:
                self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'][MsgSrcEp] = {}
            if MsgClusterID not in self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'][MsgSrcEp]:
                self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'][MsgSrcEp][MsgClusterID] = {}
            if MsgAttID not in self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'][MsgSrcEp][MsgClusterID]:
                self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'][MsgSrcEp][MsgClusterID] = {}
                self.DiscoveryDevices[MsgSrcAddr]['Attribute Discovery']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID] = MsgAttType
    return

# OTA and Remote decoding kindly authorized by https://github.com/ISO-B
def Decode8501(self, Devices, MsgData, MsgRSSI) : # OTA image block request
    'BLOCK_REQUEST  0x8501  ZiGate will receive this command when device asks OTA firmware'

    if self.OTA:
        self.OTA.ota_request_firmware( MsgData )
    return

def Decode8503(self, Devices, MsgData, MsgRSSI) : # OTA image block request
    #'UPGRADE_END_REQUEST    0x8503  Device will send this when it has received last part of firmware'

    if self.OTA:
        self.OTA.ota_request_firmware_completed( MsgData ),
    return

#Router Discover
def Decode8701(self, Devices, MsgData, MsgRSSI) : # Reception Router Disovery Confirm Status

    MsgLen = len(MsgData)
    loggingInput( self, 'Debug', "Decode8701 - MsgData: %s MsgLen: %s" %(MsgData, MsgLen))

    if MsgLen >= 4:
        # This is the reverse of what is documented. Suspecting that we got a BigEndian uint16 instead of 2 uint8
        NwkStatus = MsgData[0:2]
        Status = MsgData[2:4]
        MsgSrcAddr = ''
        MsgSrcIEEE = ''
    if MsgLen >= 8:
        MsgSrcAddr = MsgData[4:8]
        if MsgSrcAddr in self.ListOfDevices:
            MsgSrcIEEE = self.ListOfDevices[ MsgSrcAddr ][ 'IEEE' ]

    if Status != "00" :
        loggingInput( self, 'Log', "Decode8701 - Route discovery has been performed for %s, status: %s - %s Nwk Status: %s - %s " \
                %( MsgSrcAddr, Status, DisplayStatusCode( Status ), NwkStatus, DisplayStatusCode(NwkStatus)))

    loggingInput( self, 'Debug', "Decode8701 - Route discovery has been performed for %s %s, status: %s Nwk Status: %s " \
            %( MsgSrcAddr, MsgSrcIEEE, Status, NwkStatus))

    return

#Réponses APS
def Decode8702(self, Devices, MsgData, MsgRSSI) : # Reception APS Data confirm fail

    """
    Status: d4 - Unicast frame does not have a route available but it is buffered for automatic resend
    Status: e9 - No acknowledgement received when expected
    Status: f0 - Pending transaction has expired and data discarded
    Status: cf - Attempt at route discovery has failed due to lack of table spac
    """

    MsgLen=len(MsgData)
    if MsgLen==0: 
        return

    MsgDataStatus=MsgData[0:2]
    MsgDataSrcEp=MsgData[2:4]
    MsgDataDestEp=MsgData[4:6]
    MsgDataDestMode=MsgData[6:8]

    if not self.FirmwareVersion:
        MsgDataDestAddr=MsgData[8:24]
        MsgDataSQN=MsgData[24:26]
        if int(MsgDataDestAddr,16) == ( int(MsgDataDestAddr,16) & 0xffff000000000000):
            MsgDataDestAddr = MsgDataDestAddr[0:4]
    elif self.FirmwareVersion.lower() <= '030f':
        MsgDataDestAddr=MsgData[8:24]
        MsgDataSQN=MsgData[24:26]
        if int(MsgDataDestAddr,16) == ( int(MsgDataDestAddr,16) & 0xffff000000000000):
            MsgDataDestAddr = MsgDataDestAddr[0:4]
    else:    # Fixed by https://github.com/fairecasoimeme/ZiGate/issues/161
        loggingInput( self, 'Debug', "Decode8702 - with Firmware > 3.0f")
        if int(MsgDataDestMode,16) == ADDRESS_MODE['short']:
            MsgDataDestAddr=MsgData[8:12]
            MsgDataSQN=MsgData[12:14]
        elif int(MsgDataDestMode,16) == ADDRESS_MODE['group']:
            MsgDataDestAddr=MsgData[8:12]
            MsgDataSQN=MsgData[12:14]
        elif int(MsgDataDestMode,16) == ADDRESS_MODE['ieee']:
            MsgDataDestAddr=MsgData[8:24]
            MsgDataSQN=MsgData[24:26]
        else:
            Domoticz.Error("Decode8702 - Unexpected addmode %s for data %s" %(MsgDataDestMode, MsgData))
            return

    NWKID = None
    IEEE = None
    if int(MsgDataDestMode,16) == ADDRESS_MODE['ieee']:
        if MsgDataDestAddr in self.IEEE2NWK:
            NWKID = self.IEEE2NWK[MsgDataDestAddr]
            IEEE = MsgDataDestAddr
    else:
        if MsgDataDestAddr in self.ListOfDevices:
            NWKID = MsgDataDestAddr
            IEEE = self.ListOfDevices[MsgDataDestAddr]['IEEE']
    if NWKID == None or IEEE == None:
        loggingInput( self, 'Log',"Decode8702 - Unknown Address %s : (%s,%s)" %( MsgDataDestAddr, NWKID, IEEE ))
        return
    
    loggingInput( self, 'Debug', "Decode8702 - IEEE: %s Nwkid: %s Status: %s" %(IEEE, NWKID, MsgDataStatus), NWKID)
    if self.APS:
        self.APS.processAPSFailure(NWKID, IEEE, MsgDataStatus)

    timeStamped( self, NWKID , 0x8702)
    updSQN( self, NWKID, MsgDataSQN)

    return

#Device Announce
def Decode004D(self, Devices, MsgData, MsgRSSI) : # Reception Device announce

    """
    Il y a un Device Announce interne qui ne peut pas avoir un LQI ni de rejoin
    et un autre Device announce qui a le LQI et le rejoin. 
    J'avais supprimé le premier mais tu en as besoin. 
    Du coup, pour une même commande on se retrouve avec 2 structures.

    if len(MsgData) == 22 ==> No Join Flag
    if len(MsgData) == 24 ==> Join Flag 

    """

    MsgSrcAddr=MsgData[0:4]
    MsgIEEE=MsgData[4:20]
    MsgMacCapa=MsgData[20:22]
    MsgRejoinFlag = 'XX'

    if len(MsgData) > 22: # Firmware 3.1b 
        MsgRejoinFlag = MsgData[22:24]

    def decodeMacCapa( maccap ):

        maccap = int(maccap,16)
        alternatePANCOORDInator = (maccap & 0b00000001)
        deviceType              = (maccap & 0b00000010) >> 1
        deviceType              = (maccap & 0b00000010) >> 1
        powerSource             = (maccap & 0b00000100) >> 2
        receiveOnIddle          = (maccap & 0b00001000) >> 3
        securityCap             = (maccap & 0b01000000) >> 6
        allocateAddress         = (maccap & 0b10000000) >> 7

        MacCapa = []
        if alternatePANCOORDInator:
            MacCapa.append('Able to act Coordinator')
        if deviceType:
            MacCapa.append('Full-Function Device')
        else:
            MacCapa.append('Reduced-Function Device')
        if powerSource:
            MacCapa.append('Main Powered')
        if receiveOnIddle:
            MacCapa.append('Receiver during Idle')
        if securityCap:
            MacCapa.append('High security')
        else:
            MacCapa.append('Standard security')
        if allocateAddress:
            MacCapa.append('NwkAddr should be allocated')
        else:
            MacCapa.append('NwkAddr need to be allocated')
        return MacCapa

    REJOIN_NETWORK = {
            '00': '0x00 - join a network through association',
            '01': '0x01 - joining directly or rejoining the network using the orphaning procedure',
            '02': '0x02 - joining the network using the NWK rejoining procedure.',
            '03': '0x03 - change the operational network channel to that identified in the ScanChannels parameter.',
            '99': '0x99 - Unknown value received.'
            }

    if MsgSrcAddr in self.ListOfDevices:
        if self.ListOfDevices[MsgSrcAddr]['Status'] in ( '004d', '0045', '0043', '8045', '8043'):
            # Let's skip it has this is a duplicate message from the device
            loggingInput( self, 'Debug', "Decode004D - Already known device %s with status: %s" %( MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Status']), MsgSrcAddr)
            return

    deviceMacCapa = list(decodeMacCapa( MsgMacCapa ))

    now = time()

    if MsgRejoinFlag not in REJOIN_NETWORK:
        MsgRejoinFlag = '99'

    if MsgSrcAddr in self.ListOfDevices:
        if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
            loggingPairing( self, 'Status', "Device Announcement: %s(%s, %s) Join Flag: %s RSSI: %s" \
                    %( self.ListOfDevices[MsgSrcAddr]['ZDeviceName'], MsgSrcAddr, MsgIEEE, REJOIN_NETWORK[ MsgRejoinFlag ], int(MsgRSSI,16)))
        else:
            loggingPairing( self, 'Status', "Device Announcement Addr: %s, IEEE: %s Join Flag: %s RSSI: %s" \
                    %( MsgSrcAddr, MsgIEEE, REJOIN_NETWORK[ MsgRejoinFlag ], int(MsgRSSI,16)))
    else:
        loggingPairing( self, 'Status', "Device Announcement Addr: %s, IEEE: %s Join Flag: %s RSSI: %s" \
                %( MsgSrcAddr, MsgIEEE, REJOIN_NETWORK[ MsgRejoinFlag ], int(MsgRSSI,16)))

    loggingMessages( self, '004D', MsgSrcAddr, MsgIEEE, MsgRSSI, None)

    # Test if Device Exist, if Left then we can reconnect, otherwise initialize the ListOfDevice for this entry
    if DeviceExist(self, Devices, MsgSrcAddr, MsgIEEE):
        # ############
        # Device exist, Reconnection has been done by DeviceExist()
        #
        loggingInput( self, 'Debug', "Decode004D - Already known device %s infos: %s" %( MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

        # If we got a recent Annoucement in the last 15 secondes, then we drop the new one
        if 'Announced' in  self.ListOfDevices[MsgSrcAddr]:
            if  now < self.ListOfDevices[MsgSrcAddr]['Announced'] + 15:
                # Looks like we have a duplicate Device Announced in less than 15s
                loggingInput( self, 'Log', "Decode004D - Duplicate Device Annoucement for %s -> Drop" %( MsgSrcAddr), MsgSrcAddr)
                return

        self.ListOfDevices[MsgSrcAddr]['Announced'] = now

        if self.pluginconf.pluginConf['ExpDeviceAnnoucement1'] and MsgRejoinFlag == '99':
            if 'Health' in self.ListOfDevices[MsgSrcAddr]:
                if self.ListOfDevices[MsgSrcAddr]['Health'] == 'Live':
                    loggingInput( self, 'Log', "   -> ExpDeviceAnnoucement 1: droping packet for %s due to MsgRejoinFlag: 99. Health: %s, MacCapa: %s, RSSI: %s" \
                        %( MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Health'], str(deviceMacCapa), MsgRSSI), MsgSrcAddr)
                    timeStamped( self, MsgSrcAddr , 0x004d)
                    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
                    return
   
        if self.pluginconf.pluginConf['ExpDeviceAnnoucement2'] and 'Main Powered' in deviceMacCapa:
            if 'Health' in self.ListOfDevices[MsgSrcAddr]:
                if self.ListOfDevices[MsgSrcAddr]['Health'] == 'Live':
                    loggingInput( self, 'Log', "   -> ExpDeviceAnnoucement 2: droping packet for %s due to Main Powered and Live RSSI: %s" \
                            %(MsgSrcAddr, MsgRSSI), MsgSrcAddr)
                    timeStamped( self, MsgSrcAddr , 0x004d)
                    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
                    return

        if self.pluginconf.pluginConf['ExpDeviceAnnoucement3'] and MsgRejoinFlag in ( '01', '02' ):
            loggingInput( self, 'Log', "   -> ExpDeviceAnnoucement 3: drop packet for %s due to  Rejoining network as %s, RSSI: %s" \
                    %(MsgSrcAddr, MsgRejoinFlag, MsgRSSI), MsgSrcAddr)
            timeStamped( self, MsgSrcAddr , 0x004d)
            lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
            return

        timeStamped( self, MsgSrcAddr , 0x004d)
        lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)

        # Reset the device Hearbeat, This should allow to trigger Read Request
        self.ListOfDevices[MsgSrcAddr]['Heartbeat'] = 0

        # If this is a rejoin after a leave, let's update the Status
        if self.ListOfDevices[MsgSrcAddr]['Status'] == 'Left':
            loggingInput( self, 'Debug', "Decode004D -  %s Status from Left to inDB" %( MsgSrcAddr), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Status'] = 'inDB'

        # Redo the binding if allow
        if 'Model' in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]['Model'] != {}:
                if self.ListOfDevices[MsgSrcAddr]['Model'] in LEGRAND_REMOTES:
                    # If Remote Legrand skip, but do req Battery infos
                    loggingInput( self, 'Debug', "Decode004D - Legrand remote, no rebind, just exit" , MsgSrcAddr)
                    ReadAttributeRequest_0001( self,  MsgSrcAddr)   # Refresh battery
                    return

        for tmpep in self.ListOfDevices[MsgSrcAddr]['Ep']:
            if '0500' in self.ListOfDevices[MsgSrcAddr]['Ep'][tmpep]:
                # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
                loggingInput( self, 'Debug', "Decode004D - IAS Zone controler setting %s" \
                        %( MsgSrcAddr), MsgSrcAddr)
                self.iaszonemgt.IASZone_triggerenrollement( MsgSrcAddr, tmpep)
                if '0502'  in self.ListOfDevices[MsgSrcAddr]['Ep'][tmpep]:
                    loggingInput( self, 'Debug', "Decode004D - IAS WD enrolment %s" \
                        %( MsgSrcAddr), MsgSrcAddr)
                    self.iaszonemgt.IASWD_enroll( MsgSrcAddr, tmpep)
                break

        if self.pluginconf.pluginConf['allowReBindingClusters']:
            loggingInput( self, 'Debug', "Decode004D - Request rebind clusters for %s" %( MsgSrcAddr), MsgSrcAddr)
            rebind_Clusters( self, MsgSrcAddr)
    
        # As we are redo bind, we need to redo the Configure Reporting
        if 'ConfigureReporting' in self.ListOfDevices[MsgSrcAddr]:
            del self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']
        processConfigureReporting( self, NWKID=MsgSrcAddr )

        # Let's take the opportunity to trigger some request/adjustement / NOT SURE IF THIS IS GOOD/IMPORTANT/NEEDED
        loggingInput( self, 'Debug', "Decode004D - Request attribute 0x0000 %s" %( MsgSrcAddr), MsgSrcAddr)
        ReadAttributeRequest_0000( self,  MsgSrcAddr)
        ReadAttributeRequest_0001( self,  MsgSrcAddr)
        sendZigateCmd(self,"0042", str(MsgSrcAddr) )

        # Let's check if this is a Schneider Wiser
        if 'Manufacturer' in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]['Manufacturer'] == '105e':
                schneider_wiser_registration( self, Devices, MsgSrcAddr )
    else:
        # New Device coming for provisioning

        # There is a dilem here as Livolo and Schneider Wiser share the same IEEE prefix.
        if not self.pluginconf.pluginConf['enableSchneiderWiser']:
            PREFIX_MACADDR_LIVOLO = '00124b00'
            if MsgIEEE[0:len(PREFIX_MACADDR_LIVOLO)] == PREFIX_MACADDR_LIVOLO:
                livolo_bind( self, MsgSrcAddr, '06')

        # New device comming. The IEEE is not known
        loggingInput( self, 'Debug', "Decode004D - New Device %s %s" %(MsgSrcAddr, MsgIEEE), MsgSrcAddr)

        if MsgIEEE in self.IEEE2NWK :
            Domoticz.Error("Decode004d - New Device %s %s already exist in IEEE2NWK" %(MsgSrcAddr, MsgIEEE))
            loggingPairing( self, 'Debug', "Decode004d - self.IEEE2NWK[MsgIEEE] = %s with Status: %s" 
                    %(self.IEEE2NWK[MsgIEEE], self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]['Status']) )
            if self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]['Status'] != 'inDB':
                loggingInput( self, 'Debug', "Decode004d - receiving a new Device Announced for a device in processing, drop it",MsgSrcAddr)
            return

        self.IEEE2NWK[MsgIEEE] = MsgSrcAddr
        if IEEEExist( self, MsgIEEE ):
            # we are getting a dupplicate. Most-likely the Device is existing and we have to reconnect.
            if not DeviceExist(self, Devices, MsgSrcAddr,MsgIEEE):
                loggingPairing( self, 'Error', "Decode004d - Paranoia .... NwkID: %s, IEEE: % -> %s " 
                        %(MsgSrcAddr, MsgIEEE, str(self.ListOfDevices[MsgSrcAddr])))
                return

        # 1- Create the Data Structutre
        initDeviceInList(self, MsgSrcAddr)
        loggingPairing( self, 'Debug',"Decode004d - Looks like it is a new device sent by Zigate")
        self.CommiSSionning = True
        self.ListOfDevices[MsgSrcAddr]['MacCapa'] = MsgMacCapa
        self.ListOfDevices[MsgSrcAddr]['Capability'] = deviceMacCapa
        self.ListOfDevices[MsgSrcAddr]['IEEE'] = MsgIEEE
        self.ListOfDevices[MsgSrcAddr]['Announced'] = now

        if 'Main Powered' in self.ListOfDevices[MsgSrcAddr]['Capability']:
            self.ListOfDevices[MsgSrcAddr]['PowerSource'] = 'Main'
        if 'Full-Function Device' in self.ListOfDevices[MsgSrcAddr]['Capability']:
             self.ListOfDevices[MsgSrcAddr]['LogicalType'] = 'Router'
             self.ListOfDevices[MsgSrcAddr]['DeviceType'] = 'FFD'
        if 'Reduced-Function Device' in self.ListOfDevices[MsgSrcAddr]['Capability']:
             self.ListOfDevices[MsgSrcAddr]['LogicalType'] = 'End Device'
             self.ListOfDevices[MsgSrcAddr]['DeviceType'] = 'RFD'

        loggingPairing( self, 'Log', "--> Adding device %s in self.DevicesInPairingMode" %MsgSrcAddr)
        if MsgSrcAddr not in self.DevicesInPairingMode:
            self.DevicesInPairingMode.append( MsgSrcAddr )
        loggingPairing( self, 'Log',"--> %s" %str(self.DevicesInPairingMode))

        # 2- Store the Pairing info if needed
        if self.pluginconf.pluginConf['capturePairingInfos']:
            if MsgSrcAddr not in self.DiscoveryDevices:
                self.DiscoveryDevices[MsgSrcAddr] = {}
                self.DiscoveryDevices[MsgSrcAddr]['Ep']={}
            self.DiscoveryDevices[MsgSrcAddr]['004D'] = MsgData
            self.DiscoveryDevices[MsgSrcAddr]['NWKID'] = MsgSrcAddr
            self.DiscoveryDevices[MsgSrcAddr]['IEEE'] = MsgIEEE
            self.DiscoveryDevices[MsgSrcAddr]['MacCapa'] = MsgMacCapa
            self.DiscoveryDevices[MsgSrcAddr]['Decode-MacCapa'] = deviceMacCapa

        # 3- We will request immediatly the List of EndPoints
        PREFIX_IEEE_XIAOMI = '00158d000'
        if MsgIEEE[0:len(PREFIX_IEEE_XIAOMI)] == PREFIX_IEEE_XIAOMI:
            ReadAttributeRequest_0000(self, MsgSrcAddr, fullScope=False ) # In order to request Model Name

        loggingPairing( self, 'Debug', "Decode004d - Request End Point List ( 0x0045 )")
        self.ListOfDevices[MsgSrcAddr]['Heartbeat'] = "0"
        self.ListOfDevices[MsgSrcAddr]['Status'] = "0045"
        if MsgIEEE == 'f0d1b80000125e49':
            ReadAttributeRequest_0000(self, MsgSrcAddr , fullScope=False)    # Request Model Name

        sendZigateCmd(self,"0045", str(MsgSrcAddr))             # Request list of EPs
        loggingInput( self, 'Debug', "Decode004D - %s Infos: %s" %( MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

        timeStamped( self, MsgSrcAddr , 0x004d)
        lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)

    return

def Decode8085(self, Devices, MsgData, MsgRSSI) :
    'Remote button pressed'

    MsgSQN = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]

    TYPE_ACTIONS = {
            '01':'hold_down',
            '02':'click_down',
            '03':'release_down',
            '05':'hold_up',
            '06':'click_up',
            '07':'release_up'
            }

    #loggingInput( self, 'Debug', "Decode8085 - MsgData: %s "  %MsgData, MsgSrcAddr)
    loggingInput( self, 'Debug', "Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
            %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        return
    if self.ListOfDevices[MsgSrcAddr]['Status'] != 'inDB':
        return

    if 'Ep' in self.ListOfDevices[MsgSrcAddr]:
        if MsgEP in self.ListOfDevices[MsgSrcAddr]['Ep']:
            if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP]:
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
            if not isinstance( self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] , dict):
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
            if '0000' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]:
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = {}

    timeStamped( self, MsgSrcAddr , 0x8085)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return

    if self.ListOfDevices[MsgSrcAddr]['Model'] == 'TRADFRI remote control':
        if MsgClusterId == '0008':
            if MsgCmd in TYPE_ACTIONS:
                selector = TYPE_ACTIONS[MsgCmd]
                loggingInput( self, 'Debug', "Decode8085 - Selector: %s" %selector, MsgSrcAddr)
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector )
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = selector
            else:
                loggingInput( self, 'Log',"Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" \
                        %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
        else:
            loggingInput( self, 'Log',"Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" \
                    %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)

    elif  self.ListOfDevices[MsgSrcAddr]['Model'] == 'TRADFRI on/off switch':
        """
        Ikea Switch On/Off
        """
        if  MsgClusterId == '0008' and MsgCmd == '05': #Push Up
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '02' )
        elif MsgClusterId == '0008' and MsgCmd == '01': # Push Down
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '03' )
        elif MsgClusterId == '0008' and MsgCmd == '07': # Release Up & Down
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '04' )

        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = MsgCmd

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'RC 110':
        if MsgClusterId != '0008':
            loggingInput( self, 'Log',"Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" \
                    %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
            return

        step_mod = MsgData[14:16]
        up_down = step_size = transition = None
        if len(MsgData) >= 18:
            up_down = MsgData[16:18]
        if len(MsgData) >= 20:
            step_size = MsgData[18:20]
        if len(MsgData) >= 22:
            transition = MsgData[20:22]

        loggingInput( self, 'Log', "Decode8085 - INNR RC 110 step_mod: %s direction: %s, size: %s, transition: %s" \
                %(step_mod, up_down, step_size, transition), MsgSrcAddr)

        TYPE_ACTIONS = { None: '', '01': 'move', '02': 'click', '03': 'stop', '04': 'move_to', }
        DIRECTION = { None: '', '00': 'up', '01': 'down'}
        SCENES = { None: '', '02': 'scene1', '34': 'scene2', '66': 'scene3',
                '99': 'scene4', 'c2': 'scene5', 'fe': 'scene6' }

        if TYPE_ACTIONS[step_mod] in ( 'click', 'move'):
            selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down] 
        elif TYPE_ACTIONS[step_mod] in 'move_to':
            selector = SCENES[up_down]
        elif TYPE_ACTIONS[step_mod] in 'stop':
            selector = TYPE_ACTIONS[step_mod]

        loggingInput( self, 'Debug', "Decode8085 - INNR RC 110 selector: %s" %selector, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector )
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = selector

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in 'TRADFRI wireless dimmer':

        TYPE_ACTIONS = { None: '', 
                '01': 'moveleft', 
                '02': 'click', 
                '03': 'stop',
                '04': 'OnOff',
                '05': 'moveright',
                '06': 'Step 06',
                '07': 'stop',
                }
        DIRECTION = { None: '', 
                '00': 'left', 
                'ff': 'right'
                }

        step_mod = MsgData[14:16]
        up_down = step_size = transition = None
        if len(MsgData) >= 18:
            up_down = MsgData[16:18]
        if len(MsgData) >= 20:
            step_size = MsgData[18:20]
        if len(MsgData) >= 22:
            transition = MsgData[20:22]

        selector = None

        if step_mod == '01':
            # Move left
            loggingInput( self, 'Debug', "Decode8085 - =====> turning left step_size: %s transition: %s" %( step_size, transition), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'moveup'
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, 'moveup' )

        elif step_mod == '04' and up_down == '00' and step_size == '00' and transition == '01':
            # Off
            loggingInput( self, 'Debug', "Decode8085 - =====> turning left step_size: %s transition: %s" %(step_size, transition), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'off'
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, 'off' )

        elif step_mod == '04' and up_down == 'ff' and step_size == '00' and transition == '01':
            # On
            loggingInput( self, 'Debug', "Decode8085 - =====> turning right step_size: %s transition: %s" %( step_size, transition), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'on'
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, 'on' )

        elif step_mod == '05': 
            # Move Right
            loggingInput( self, 'Debug', "Decode8085 - =====> turning Right step_size: %s transition: %s" %(step_size, transition), MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'movedown'
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, 'movedown' )

        elif step_mod == '07':
            # Stop Moving
            loggingInput( self, 'Debug', "Decode8085 - =====> Stop moving step_size: %s transition: %s" %( step_size, transition), MsgSrcAddr)
            pass
        else:
            loggingInput( self, 'Log', "Decode8085 - =====> Unknown step_mod: %s up_down: %s step_size: %s transition: %s" \
                    %(step_mod, up_down, step_size, transition), MsgSrcAddr)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in LEGRAND_REMOTE_SWITCHS:
        loggingInput( self, 'Debug', "Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
            %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)

        TYPE_ACTIONS = { None: '', '01': 'move', '02': 'click', '03': 'stop', }
        DIRECTION = { None: '', '00': 'up', '01': 'down'}

        step_mod = MsgData[14:16]
        up_down = step_size = transition = None
        if len(MsgData) >= 18:
            up_down = MsgData[16:18]
        if len(MsgData) >= 20:
            step_size = MsgData[18:20]
        if len(MsgData) >= 22:
            transition = MsgData[20:22]

        if TYPE_ACTIONS[step_mod] in ( 'click', 'move'):
            selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down] 
        elif TYPE_ACTIONS[step_mod] == 'stop':
            selector = TYPE_ACTIONS[step_mod]
        else:
            Domoticz.Error("Decode8085 - Unknown state for %s step_mod: %s up_down: %s" %(MsgSrcAddr, step_mod, up_down))

        loggingInput( self, 'Debug', "Decode8085 - Legrand selector: %s" %selector, MsgSrcAddr)
        if selector:
            if self.pluginconf.pluginConf['EnableReleaseButton']:
                #loggingInput( self, 'Log',"Receive: %s/%s %s" %(MsgSrcAddr,MsgEP,selector))
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector )
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = selector
            else:
                # Do update only if not Stop action
                if TYPE_ACTIONS[step_mod] != 'stop':
                    #loggingInput( self, 'Log',"Receive: %s/%s %s REQUEST UPDATE" %(MsgSrcAddr,MsgEP,selector))
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector )
                    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = selector

    
    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'Lightify Switch Mini':
        """
        OSRAM Lightify Switch Mini
        Force Ep 03 to update Domoticz Widget
        """

        step_mod = MsgData[14:16]
        up_down = step_size = transition = None
        if len(MsgData) >= 18:
            up_down = MsgData[16:18]
        if len(MsgData) >= 20:
            step_size = MsgData[18:20]
        if len(MsgData) >= 22:
            transition = MsgData[20:22]

        loggingInput( self, 'Log', "Decode8085 - OSRAM Lightify Switch Mini %s/%s: Mod %s, UpDown %s Size %s Transition %s" \
                %(MsgSrcAddr, MsgEP, step_mod, up_down, step_size, transition))

        if MsgCmd == '04': # Appui court boutton central
            loggingInput( self, 'Log', "Decode8085 - OSRAM Lightify Switch Mini %s/%s Central button" %(MsgSrcAddr, MsgEP))
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, '02' )

        elif MsgCmd == '05': # Appui Long Top button
            loggingInput( self, 'Log', "Decode8085 - OSRAM Lightify Switch Mini %s/%s Long press Up button" %(MsgSrcAddr, MsgEP))
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, '03' )

        elif MsgCmd == '01': # Appui Long Botton button
            loggingInput( self, 'Log', "Decode8085 - OSRAM Lightify Switch Mini %s/%s Long press Down button" %(MsgSrcAddr, MsgEP))
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, '04' )

        elif MsgCmd == '03': # Release
            loggingInput( self, 'Log', "Decode8085 - OSRAM Lightify Switch Mini %s/%s release" %(MsgSrcAddr, MsgEP))

        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)

    elif 'Manufacturer' in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]['Manufacturer'] == '1110':
            # Profalux
            loggingInput( self, 'Log',"MsgData: %s" %MsgData)

            TYPE_ACTIONS = { None: '', '03': 'stop', '05': 'move' }
            DIRECTION = { None: '', '00': 'up', '01': 'down'}

            step_mod = MsgData[14:16]
            loggingInput( self, 'Log',"step_mod: %s" %step_mod)

            if step_mod in TYPE_ACTIONS:
                Domoticz.Error("Decode8085 - Profalux Remote, unknown Action: %s" %step_mod)

            selector = up_down = step_size = transition = None
            if len(MsgData) >= 18: up_down = MsgData[16:18]
            if len(MsgData) >= 20: step_size = MsgData[18:20]
            if len(MsgData) >= 22: transition = MsgData[20:22]

            if TYPE_ACTIONS[step_mod] in ( 'move'):
                selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
            elif TYPE_ACTIONS[step_mod] in ( 'stop' ):
                selector = TYPE_ACTIONS[step_mod]
            else:
                Domoticz.Error("Decode8085 - Profalux remote Unknown state for %s step_mod: %s up_down: %s" %(MsgSrcAddr, step_mod, up_down))

            loggingInput( self, 'Debug', "Decode8085 - Profalux remote selector: %s" %selector, MsgSrcAddr)
            if selector:
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector )

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.remote.b686opcn01':

        step_mod = MsgData[14:16]
        up_down = step_size = transition = None
        if len(MsgData) >= 18:
            up_down = MsgData[16:18]
        if len(MsgData) >= 20:
            step_size = MsgData[18:20]
        if len(MsgData) >= 22:
            transition = MsgData[20:22]

        loggingInput( self, 'Log',"Decode8085 - lumi.remote.b686opcn01 %s/%s Cluster: %s Cmd: %s, Unk: %s, step_mod: %s, up_down: %s, step_size: %s, transition: %s"
               %( MsgSrcAddr, MsgEP, MsgCmd, unknown_, step_mod, up_down, step_size, transition), MsgSrcAddr)

    else:
       loggingInput( self, 'Log',"Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
               %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
       self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)


def Decode8095(self, Devices, MsgData, MsgRSSI) :
    'Remote button pressed ON/OFF'

    MsgSQN = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]

    loggingInput( self, 'Debug', "Decode8095 - MsgData: %s "  %MsgData, MsgSrcAddr)
    loggingInput( self, 'Debug', "Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
            %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        return

    if self.ListOfDevices[MsgSrcAddr]['Status'] != 'inDB':
        return

    if 'Ep' in self.ListOfDevices[MsgSrcAddr]:
        if MsgEP in self.ListOfDevices[MsgSrcAddr]['Ep']:
            if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP]:
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
            if not isinstance( self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] , dict):
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
            if '0000' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]:
                self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = {}

    timeStamped( self, MsgSrcAddr , 0x8095)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return

    if self.ListOfDevices[MsgSrcAddr]['Model'] == 'TRADFRI remote control':
        """
        Ikea Remote 5 buttons round.
        ( cmd, directioni, cluster )
        ( 0x02, 0x0006) - click middle button - Action Toggle On/Off Off/on
        """
        if MsgClusterId == '0006' and MsgCmd == '02': 
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", 'toggle' )
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
        else:
            loggingInput( self, 'Log',"Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'TRADFRI motion sensor':
        """
        Ikea Motion Sensor
        """
        if MsgClusterId == '0006' and MsgCmd == '42':   # Motion Sensor On
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, "0406", '01')
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
        else:
            loggingInput( self, 'Log',"Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)

    elif  self.ListOfDevices[MsgSrcAddr]['Model'] == 'TRADFRI on/off switch':
        """
        Ikea Switch On/Off
        """
        MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, "0006", MsgCmd)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'RC 110':
        """
        INNR RC 110 Remote command
        """
        
        ONOFF_TYPE = { 
                '40': 'onoff_with_effect',
                '00': 'off',
                '01': 'on' }
        delayed_all_off = effect_variant = None
        if len(MsgData) >= 16:
            delayed_all_off = MsgData[16:18]
        if len(MsgData) >= 18:
            effect_variant = MsgData[18:20]
       
        if ONOFF_TYPE[MsgCmd] in ( 'on', 'off' ):
            loggingInput( self, 'Log', "Decode8095 - RC 110 ON/Off Command from: %s/%s Cmd: %s Delayed: %s Effect: %s" %(MsgSrcAddr, MsgEP, MsgCmd, delayed_all_off, effect_variant), MsgSrcAddr)
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
        else:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
            loggingInput( self, 'Log', "Decode8095 - RC 110 Unknown Command: %s for %s/%s, Cmd: %s, Unknown: %s " %(MsgCmd, MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] in LEGRAND_REMOTE_SWITCHS:
        """
        Legrand remote switch
        """
        if MsgCmd == '01': # On
            loggingInput( self, 'Debug', "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " %( MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)

        elif MsgCmd == '00': # Off
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
            loggingInput( self, 'Debug', "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " %( MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'Lightify Switch Mini':
        """
        OSRAM Lightify Switch Mini
        """
            # All messages are redirected to 1 Ep in order to process them easyly
        if MsgCmd in ('00', '01'): # On
            loggingInput( self, 'Log', "Decode8095 - OSRAM Lightify Switch Mini: %s/%s, Cmd: %s, Unknown: %s " %( MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)
            MajDomoDevice( self, Devices, MsgSrcAddr, '03', MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
        else:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
            loggingInput( self, 'Log', "Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'lumi.remote.b686opcn01':

        delayed_all_off = effect_variant = None
        if len(MsgData) >= 16:
            delayed_all_off = MsgData[16:18]
        if len(MsgData) >= 18:
            effect_variant = MsgData[18:20]

        loggingInput( self, 'Log', "Decode8095 - lumi.remote.b686opcn01 %s/%s, Cluster: %s, Cmd: %s, Unknown: %s, delayed_all_off:%s , effect_variant: %s " \
                %( MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, delayed_all_off, effect_variant), MsgSrcAddr)

    else:
        MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, "0006", MsgCmd)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' %(MsgCmd, unknown_)
        loggingInput( self, 'Log', "Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)


def Decode80A7(self, Devices, MsgData, MsgRSSI) :
    'Remote button pressed (LEFT/RIGHT)'

    MsgSQN = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgCmd = MsgData[8:10]
    MsgDirection = MsgData[10:12]
    unkown_ = MsgData[12:18]
    MsgSrcAddr = MsgData[18:22]

    # Ikea Remote 5 buttons round.
    #  ( cmd, directioni, cluster )
    #  ( 0x07, 0x00, 0005 )  Click right button
    #  ( 0x07, 0x01, 0005 )  Click left button

    TYPE_DIRECTIONS = {
            '00':'right',
            '01':'left',
            '02':'middle'
            }
    TYPE_ACTIONS = {
            '07':'click',
            '08':'hold',
            '09':'release'
            }

    loggingInput( self, 'Debug', "Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_), MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices:
        return
    if self.ListOfDevices[MsgSrcAddr]['Status'] != 'inDB':
        return

    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP]:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
    if not isinstance( self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] , dict):
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId] = {}
    if '0000' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = {}

    timeStamped( self, MsgSrcAddr , 0x80A7)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return

    if MsgClusterId == '0005':
        if MsgDirection not in TYPE_DIRECTIONS:
            # Might be in the case of Release Left or Right
            loggingInput( self, 'Log',"Decode80A7 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                    %(MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, Direction: %s, %s' %(MsgCmd, MsgDirection, unkown_)

        elif MsgCmd in TYPE_ACTIONS and MsgDirection in TYPE_DIRECTIONS:
            selector = TYPE_DIRECTIONS[MsgDirection] + '_' + TYPE_ACTIONS[MsgCmd]
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector )
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = selector
            loggingInput( self, 'Debug', "Decode80A7 - selector: %s" %selector, MsgSrcAddr)

            if self.groupmgt:
                if TYPE_DIRECTIONS[MsgDirection] in ( 'right', 'left'):
                    self.groupmgt.manageIkeaTradfriRemoteLeftRight( MsgSrcAddr, TYPE_DIRECTIONS[MsgDirection])
        else:
            loggingInput( self, 'Log',"Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                    %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, Direction: %s, %s' %(MsgCmd, MsgDirection, unkown_)
    else:
        loggingInput( self, 'Log',"Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, Direction: %s, %s' %(MsgCmd, MsgDirection, unkown_)


def Decode8806(self, Devices, MsgData, MsgRSSI) :

    ATTENUATION_dBm = {'JN516x': { 0:0, 52:-9, 40:-20, 32:-32 },
            'JN516x M05': { 0:9.5, 52:-3, 40:-15, 31:-26}}

    loggingInput( self, 'Debug', "Decode8806 - MsgData: %s" %MsgData)

    TxPower = MsgData[0:2]
    self.zigatedata['Tx-Power'] = TxPower

    if int(TxPower,16) in ATTENUATION_dBm['JN516x']:
        self.zigatedata['Tx-Attenuation'] =  ATTENUATION_dBm['JN516x'][int(TxPower,16)]
        loggingInput( self, 'Status', "TxPower Attenuation : %s dBm" % ATTENUATION_dBm['JN516x'][int(TxPower,16)])
    else:
        loggingInput( self, 'Status', "Confirming Set TxPower: %s" %int(TxPower,16))

def Decode8807(self, Devices, MsgData, MsgRSSI):

    ATTENUATION_dBm = {'JN516x': { 0:0, 52:-9, 40:-20, 32:-32 },
            'JN516x M05': { 0:9.5, 52:-3, 40:-15, 31:-26}}

    Domoticz.Debug("Decode8807 - MsgData: %s" %MsgData)

    TxPower = MsgData[0:2]
    self.zigatedata['Tx-Power'] = TxPower
    if int(TxPower,16) in ATTENUATION_dBm['JN516x']:
        self.zigatedata['Tx-Attenuation'] =  ATTENUATION_dBm['JN516x'][int(TxPower,16)]
        loggingInput( self, 'Status', "Get TxPower Attenuation : %s dBm" % ATTENUATION_dBm['JN516x'][int(TxPower,16)])
    else:
        loggingInput( self, 'Status', "Get TxPower : %s" %int(TxPower,16))


def Decode8035(self, Devices, MsgData, MsgRSSI):

    # Payload: 030000f104

    PDU_EVENT = {  '00': 'E_PDM_SYSTEM_EVENT_WEAR_COUNT_TRIGGER_VALUE_REACHED',
            '01': 'E_PDM_SYSTEM_EVENT_DESCRIPTOR_SAVE_FAILED',
            '02': 'E_PDM_SYSTEM_EVENT_PDM_NOT_ENOUGH_SPACE',
            '03': 'E_PDM_SYSTEM_EVENT_LARGEST_RECORD_FULL_SAVE_NO_LONGER_POSSIBLE',
            '04': 'E_PDM_SYSTEM_EVENT_SEGMENT_DATA_CHECKSUM_FAIL',
            '05': 'E_PDM_SYSTEM_EVENT_SEGMENT_SAVE_OK',
            '06': 'E_PDM_SYSTEM_EVENT_EEPROM_SEGMENT_HEADER_REPAIRED',
            '07': 'E_PDM_SYSTEM_EVENT_SYSTEM_INTERNAL_BUFFER_WEAR_COUNT_SWAP',
            '08': 'E_PDM_SYSTEM_EVENT_SYSTEM_DUPLICATE_FILE_SEGMENT_DETECTED',
            '09': 'E_PDM_SYSTEM_EVENT_SYSTEM_ERROR',
            '10': 'E_PDM_SYSTEM_EVENT_SEGMENT_PREWRITE',
            '11': 'E_PDM_SYSTEM_EVENT_SEGMENT_POSTWRITE',
            '12': 'E_PDM_SYSTEM_EVENT_SEQUENCE_DUPLICATE_DETECTED',
            '13': 'E_PDM_SYSTEM_EVENT_SEQUENCE_VERIFY_FAIL',
            '14': 'E_PDM_SYSTEM_EVENT_PDM_SMART_SAVE',
            '15': 'E_PDM_SYSTEM_EVENT_PDM_FULL_SAVE'
            }

    eventStatus = MsgData[0:2]
    recordID = MsgData[2:10] 

    if eventStatus in PDU_EVENT:
        loggingInput( self, 'Debug2', "Decode8035 - PDM event : recordID: %s - eventStatus: %s (%s)"  %(recordID, eventStatus, PDU_EVENT[ eventStatus ]), 'ffff')


## PDM HOST
def Decode0300( self, Devices, MsgData, MsgRSSI):

    loggingInput( self, 'Log',  "Decode0300 - PDMHostAvailableRequest: %20.20s" %(MsgData))
    pdmHostAvailableRequest(self, MsgData )
    return

def Decode0301( self, Devices, MsgData, MsgRSSI):

    loggingInput( self, 'Log',  "Decode0301 - E_SL_MSG_ASC_LOG_MSG: %20.20s" %(MsgData))
    return

def Decode0302( self, Devices, MsgData, MsgRSSI):

    loggingInput( self, 'Log',  "Decode0302 - PDMloadConfirmed: %20.20s" %(MsgData))
    pdmLoadConfirmed(self, MsgData )
    return

def Decode0200( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0200 - PDMSaveRequest: %20.20s" %(MsgData))
    PDMSaveRequest( self, MsgData)
    return

def Decode0201( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0201 - PDMLoadRequest: %20.20s" %(MsgData))
    PDMLoadRequest(self, MsgData)
    return

def Decode0202( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0202 - PDMDeleteAllRecord: %20.20s" %(MsgData))
    PDMDeleteAllRecord( self, MsgData)

def Decode0203( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0203 - PDMDeleteRecord: %20.20s" %(MsgData))
    PDMDeleteRecord( self, MsgData)

def Decode0204( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0204 - E_SL_MSG_CREATE_BITMAP_RECORD_REQUEST: %20.20s" %(MsgData))
    PDMCreateBitmap(self, MsgData)

def Decode0205( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0205 - E_SL_MSG_DELETE_BITMAP_RECORD_REQUEST: %20.20s" %(MsgData))
    PDMDeleteBitmapRequest( self, MsgData)


def Decode0206( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0206 - PDMGetBitmapRequest: %20.20s" %(MsgData))
    PDMGetBitmapRequest(self, MsgData )
    return

def Decode0207( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0207 - PDMIncBitmapRequest: %20.20s" %(MsgData))
    PDMIncBitmapRequest( self, MsgData)
    return

def Decode0208( self, Devices, MsgData, MsgRSSI):

    #loggingInput( self, 'Debug',  "Decode0208 - PDMExistanceRequest: %20.20s" %(MsgData))
    PDMExistanceRequest(self, MsgData )
    return




