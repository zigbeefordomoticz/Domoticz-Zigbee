#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_input.py

    Description: manage inputs from Zigate

"""

import Domoticz
import binascii
import time
import struct
import queue
import time
import json

from Modules.domoticz import MajDomoDevice, lastSeenUpdate, timedOutDevice
from Modules.tools import timeStamped, updSQN, DeviceExist, getSaddrfromIEEE, IEEEExist, initDeviceInList
from Modules.output import sendZigateCmd, leaveMgtReJoin, rebind_Clusters, ReadAttributeRequest_0000
from Modules.status import DisplayStatusCode
from Modules.readClusters import ReadCluster
from Modules.database import saveZigateNetworkData
from Modules.consts import ADDRESS_MODE, ZCL_CLUSTERS_LIST

#from Modules.adminWidget import updateNotificationWidget, updateStatusWidget

from Classes.IAS import IAS_Zone_Management
from Classes.AdminWidgets import  AdminWidgets
from Classes.GroupMgt import GroupsManagement
from Classes.OTA import OTAManagement
from Classes.NetworkMap import NetworkMap

def ZigateRead(self, Devices, Data):

    DECODERS = {
        '004d': Decode004D,
        '8000': Decode8000_v2, '8001': Decode8001, '8002': Decode8002, '8003': Decode8003, '8004': Decode8004,
        '8005': Decode8005, '8006': Decode8006,
        '8009': Decode8009, '8010': Decode8010,
        '8014': Decode8014, '8015': Decode8015,
        '8024': Decode8024,
        '8028': Decode8028,
        '802b': Decode802B, '802c': Decode802C,
        '8030': Decode8030, '8031': Decode8031,
        '8034': Decode8034,
        '8040': Decode8040, '8041': Decode8041, '8042': Decode8042, '8043': Decode8043, '8044': Decode8044,
        '8045': Decode8045, '8046': Decode8046, '8047': Decode8047, '8048': Decode8048,
        '804a': Decode804A, '804b': Decode804B,
        '804e': Decode804E,
        '8060': Decode8060, '8061': Decode8061, '8062': Decode8062, '8063': Decode8063,
        '8085': Decode8085,
        '8095': Decode8095,
        '80a7': Decode80A7,
        '8100': Decode8100, '8101': Decode8101, '8102': Decode8102,
        '8110': Decode8110,
        '8120': Decode8120,
        '8140': Decode8140,
        '8401': Decode8401,
        '8501': Decode8501,
        '8503': Decode8503,
        '8701': Decode8701, '8702': Decode8702
    }
    
    NOT_IMPLEMENTED = ( '00d1', '8029', '80a0', '80a1', '80a2', '80a3', '80a4', '80a6', 8007 )

    Domoticz.Debug("ZigateRead - decoded data : " + Data + " lenght : " + str(len(Data)) )

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

    Domoticz.Debug("ZigateRead - MsgType: %s, MsgLength: %s, MsgCRC: %s, Data: %s; RSSI: %s" \
            %( MsgType, MsgLength, MsgCRC, MsgData, MsgRSSI) )

    if MsgType in DECODERS:
        _decoding = DECODERS[ MsgType]
        Domoticz.Debug("ZigateRead - Calling Decoder: %s for Message type: %s" %(_decoding, MsgType))
        _decoding( self, Devices, MsgData, MsgRSSI)
        return

    Domoticz.Error("ZigateRead - Decoder not found for %s" %(MsgType))

    return

#IAS Zone
def Decode8401(self, Devices, MsgData, MsgRSSI) : # Reception Zone status change notification

    Domoticz.Log("Decode8401 - Reception Zone status change notification : " + MsgData)
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
        Domoticz.Error("Decode8401 - unknown IAS device %s from plugin" %sMsgSrcAddr)
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
        Domoticz.Log("Decode8401 - receive a message for an unknown device %s : %s" %( MsgSrcAddr, MsgData))
        return

    Domoticz.Log("Decode8401 - MsgSQN: %s MsgSrcAddr: %s MsgEp:%s MsgClusterId: %s MsgZoneStatus: %s MsgExtStatus: %s MsgZoneID: %s MsgDelay: %s" \
            %( MsgSQN, MsgSrcAddr, MsgEp, MsgClusterId, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay))

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
            Domoticz.Debug("Decode8401 - PST03A-v2.2.5 door/windows status : " + value)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0500", value)
            # Nota : tamper alarm on EP 2 are discarded
        elif  MsgEp == "01" :
            iData = (int(MsgZoneStatus,16) & 1)    # For EP 1, bit 0 = "movement"
            # bit 0 = 1 ==> movement
            if iData == 1 :    
                value = "%02d" % iData
                Domoticz.Debug("Decode8401 - PST03A-v2.2.5 mouvements alarm")
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0406", value)
            # bit 2 = 1 ==> tamper (device disassembly)
            iData = (int(MsgZoneStatus,16) & 4) >> 2
            if iData == 1 :     
                value = "%02d" % iData
                Domoticz.Debug("Decode8401 - PST03A-V2.2.5  tamper alarm")
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", value)
        else :
            Domoticz.Debug("Decode8401 - PST03A-v2.2.5, unknow EndPoint : " + MsgDataSrcEp)
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

        Domoticz.Status("IAS Zone change for device:%s  - alarm1: %s, alaram2: %s, tamper: %s, battery: %s, Support Reporting: %s, restore Reporting: %s, trouble: %s, acmain: %s, test: %s, battdef: %s" \
                %( MsgSrcAddr, alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef))

        Domoticz.Log("Decode8401 MsgZoneStatus: %s " %MsgZoneStatus[2:4])
        value = MsgZoneStatus[2:4]
        if value == '21':
            value = '01'
        elif value == '20':
            value = '00'
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", value )

        if battdef or battery:
            self.ListOfDevices[MsgSrcAddr]['Battery'] = '1'

        if 'IAS' in self.ListOfDevices[MsgSrcAddr]:
            if 'ZoneStatus' in self.ListOfDevices[MsgSrcAddr]['IAS']:
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


    return


#Responses
def Decode8000_v2(self, Devices, MsgData, MsgRSSI) : # Status
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8000_v2 - MsgData lenght is : " + str(MsgLen) + " out of 8")

    if MsgLen < 8 :
        Domoticz.Log("Decode8000 - uncomplete message : %s" %MsgData)
        return

    if MsgLen > 8 :
        Domoticz.Log("Decode8000 - More information . New Firmware ???")

    Status=MsgData[0:2]
    SEQ=MsgData[2:4]
    PacketType=MsgData[4:8]

    if   Status=="00" : 
        Status="Success"
    elif Status=="01" : Status="Incorrect Parameters"
    elif Status=="02" : Status="Unhandled Command"
    elif Status=="03" : Status="Command Failed"
    elif Status=="04" : Status="Busy"
    elif Status=="05" : Status="Stack Already Started"
    elif int(Status,16) >= 128 and int(Status,16) <= 244 : Status="ZigBee Error Code "+ DisplayStatusCode(Status)

    Domoticz.Debug("Decode8000_v2 - status: " + Status + " SEQ: " + SEQ + " Packet Type: " + PacketType )

    if   PacketType=="0012" : Domoticz.Log("Erase Persistent Data cmd status : " +  Status )
    elif PacketType=="0024" : Domoticz.Log("Start Network status : " +  Status )
    elif PacketType=="0026" : Domoticz.Log("Remove Device cmd status : " +  Status )
    elif PacketType=="0044" : Domoticz.Log("request Power Descriptor status : " +  Status )

    # Group Management
    if PacketType in ('0060', '0061', '0062', '0063', '0064', '0065'):
        self.groupmgt.statusGroupRequest( MsgData )

    if str(MsgData[0:2]) != "00" :
        Domoticz.Debug("Decode8000 - PacketType: %s Status: [%s] - %s" \
                %(PacketType, MsgData[0:2], Status))

    return

def Decode8001(self, Decode, MsgData, MsgRSSI) : # Reception log Level
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8001 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgLogLvl=MsgData[0:2]
    MsgDataMessage=MsgData[2:len(MsgData)]
    
    Domoticz.Status("Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)
    return

def Decode8002(self, Devices, MsgData, MsgRSSI) : # Data indication
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8002 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgLogLvl=MsgData[0:2]
    MsgProfilID=MsgData[2:6]
    MsgClusterID=MsgData[6:10]
    MsgSourcePoint=MsgData[10:12]
    MsgEndPoint=MsgData[12:14]
    MsgSourceAddressMode=MsgData[16:18]
    if int(MsgSourceAddressMode)==0 :
        MsgSourceAddress=MsgData[18:24]  # uint16_t
        MsgDestinationAddressMode=MsgData[24:26]
        if int(MsgDestinationAddressMode)==0 : # uint16_t
            MsgDestinationAddress=MsgData[26:32]
            MsgPayloadSize=MsgData[32:34]
            MsgPayload=MsgData[34:len(MsgData)]
        else : # uint32_t
            MsgDestinationAddress=MsgData[26:42]
            MsgPayloadSize=MsgData[42:44]
            MsgPayload=MsgData[44:len(MsgData)]
    else : # uint32_t
        MsgSourceAddress=MsgData[18:34]
        MsgDestinationAddressMode=MsgData[34:36]
        if int(MsgDestinationAddressMode)==0 : # uint16_t
            MsgDestinationAddress=MsgData[36:40]
            MsgPayloadSize=MsgData[40:42]
            MsgPayload=MsgData[42:len(MsgData)]
        else : # uint32_t
            MsgDestinationAddress=MsgData[36:52]
            MsgPayloadSize=MsgData[52:54]
            MsgPayload=MsgData[54:len(MsgData)]
    
    Domoticz.Status("Reception Data indication, Source Address : " + MsgSourceAddress + " Destination Address : " + MsgDestinationAddress + " ProfilID : " + MsgProfilID + " ClusterID : " + MsgClusterID + " Payload size : " + MsgPayloadSize + " Message Payload : " + MsgPayload)
    return

def Decode8003(self, Devices, MsgData, MsgRSSI) : # Device cluster list
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8003 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSourceEP=MsgData[0:2]
    MsgProfileID=MsgData[2:6]
    MsgClusterID=MsgData[6:len(MsgData)]

    idx = 0
    clusterLst = []
    while idx < len(MsgClusterID):
        clusterLst.append(MsgClusterID[idx:idx+4] )
        idx += 4
    
    self.zigatedata['Cluster List'] = clusterLst
    Domoticz.Status("Device Cluster list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " Cluster List : " + str(clusterLst) )
    return

def Decode8004(self, Devices, MsgData, MsgRSSI) : # Device attribut list
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8004 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

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
    Domoticz.Status("Device Attribut list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Attribut List : " + str(attributeLst) )
    return

def Decode8005(self, Devices, MsgData, MsgRSSI) : # Command list
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8005 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

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
    Domoticz.Status("Command list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Command List : " + str( commandLst ))
    return

def Decode8006(self, Devices, MsgData, MsgRSSI): # Non “Factory new” Restart

    Domoticz.Debug("Decode8006 - MsgData: %s" %(MsgData))

    Status = MsgData[0:2]
    if MsgData[0:2] == "00":
        Status = "STARTUP"
    elif MsgData[0:2] == "01":
        Status = "RUNNING"
    elif MsgData[0:2] == "02":
        Status = "NFN_START"
    elif MsgData[0:2] == "06":
        Status = "RUNNING"
    Domoticz.Status("Non 'Factory new' Restart status: %s" %(Status) )

def Decode8009(self,Devices, MsgData, MsgRSSI) : # Network State response (Firm v3.0d)
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8009 - MsgData lenght is : " + str(MsgLen) + " out of 42")
    addr=MsgData[0:4]
    extaddr=MsgData[4:20]
    PanID=MsgData[20:24]
    extPanID=MsgData[24:40]
    Channel=MsgData[40:42]
    Domoticz.Debug("Decode8009: Network state - Address :" + addr + " extaddr :" + extaddr + " PanID : " + PanID + " Channel : " + str(int(Channel,16)) )

    
    if self.ZigateIEEE != extaddr:
        self.adminWidgets.updateNotificationWidget( Devices, 'Zigate IEEE: %s' %extaddr)

    self.ZigateIEEE = extaddr
    self.ZigateNWKID = addr

    self.IEEE2NWK[extaddr] = addr
    self.ListOfDevices[addr] = {}
    self.ListOfDevices[addr]['version'] = '3'
    self.ListOfDevices[addr]['IEEE'] = extaddr
    self.ListOfDevices[addr]['Ep'] = {}
    self.ListOfDevices[addr]['Ep']['01'] = {}
    self.ListOfDevices[addr]['Ep']['01']['0004'] = {}
    self.ListOfDevices[addr]['Ep']['01']['0006'] = {}
    self.ListOfDevices[addr]['Ep']['01']['0008'] = {}
    self.ListOfDevices[addr]['PowerSource'] = 'Main'

    if self.currentChannel != int(Channel,16):
        self.adminWidgets.updateNotificationWidget( Devices, 'Zigate Channel: %s' %str(int(Channel,16)))
    self.currentChannel = int(Channel,16)

    self.iaszonemgt.setZigateIEEE( extaddr )

    Domoticz.Status("Zigate addresses ieee: %s , short addr: %s" %( self.ZigateIEEE,  self.ZigateNWKID) )

    # from https://github.com/fairecasoimeme/ZiGate/issues/15 , if PanID == 0 -> Network is done
    if str(PanID) == "0" : 
        Domoticz.Status("Network state DOWN ! " )
        self.adminWidgets.updateNotificationWidget( Devices, 'Network down PanID = 0' )
        self.adminWidgets.updateStatusWidget( Devices, 'No Connection')
    else :
        Domoticz.Status("Network state UP, PANID: %s extPANID: 0x%s Channel: %s" \
                %( PanID, extPanID, int(Channel,16) ))

    self.zigatedata['IEEE'] = extaddr
    self.zigatedata['Short Address'] = addr
    self.zigatedata['Channel'] = Channel
    self.zigatedata['PANID'] = PanID
    self.zigatedata['Extended PANID'] = extPanID
    saveZigateNetworkData( self , self.zigatedata )

    return

def Decode8010(self, Devices, MsgData, MsgRSSI): # Reception Version list
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8010 - MsgData lenght is : " + str(MsgLen) + " out of 8")

    MajorVersNum=MsgData[0:4]
    InstaVersNum=MsgData[4:8]
    try :
        Domoticz.Debug("Decode8010 - Reception Version list : " + MsgData)
        Domoticz.Status("Major Version Num: " + MajorVersNum )
        Domoticz.Status("Installer Version Number: " + InstaVersNum )
    except :
        Domoticz.Error("Decode8010 - Reception Version list : " + MsgData)
    else:
        self.FirmwareVersion = str(InstaVersNum)
        self.FirmwareMajorVersion = str(MajorVersNum)
        self.zigatedata['Firmware Version'] =  str(MajorVersNum) + ' - ' +str(InstaVersNum)

    return

def Decode8014(self, Devices, MsgData, MsgRSSI): # "Permit Join" status response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8014 - MsgData lenght is : " +MsgData + "len: "+ str(MsgLen) + " out of 2")

    Status=MsgData[0:2]
    timestamp = int(time.time())

    Domoticz.Log("Permit Join status: %s" %Status)
    Domoticz.Log("---> self.permitTojoin['Starttime']: %s" %self.permitTojoin['Starttime'])
    Domoticz.Log("---> Current time                  : %s" %timestamp)
    Domoticz.Log("---> self.Ping['Permit']  (prev)   : %s" %self.Ping['Permit'])

    if Status == "00": 
        if ( self.Ping['Permit'] is None) or (self.permitTojoin['Starttime'] >= timestamp - 240):
            Domoticz.Status("Accepting new Hardware: Disable")
        self.Ping['Permit'] = 'Off'
    elif Status == "01" : 
        if (self.Ping['Permit'] is None) or ( self.permitTojoin['Starttime'] >= timestamp - 240):
            Domoticz.Status("Accepting new Hardware: On")
        self.Ping['Permit'] = 'On'
    else: 
        Domoticz.Error("Decode8014 - Unexpected value "+str(MsgData))

    Domoticz.Log("---> self.Ping['Permit']  (new )   : %s" %self.Ping['Permit'])
    self.Ping['TimeStamp'] = int(time.time())
    self.Ping['Status'] = 'Receive'
    Domoticz.Debug("Ping - received")

    return

def Decode8015(self, Devices, MsgData, MsgRSSI) : # Get device list ( following request device list 0x0015 )
    # id: 2bytes
    # addr: 4bytes
    # ieee: 8bytes
    # power_type: 2bytes - 0 Battery, 1 AC Power
    # rssi : 2 bytes - Signal Strength between 1 - 255
    numberofdev=len(MsgData)    
    Domoticz.Status("Number of devices recently active in Zigate = " + str(round(numberofdev/26)) )
    idx=0
    while idx < (len(MsgData)):
        DevID=MsgData[idx:idx+2]
        saddr=MsgData[idx+2:idx+6]
        ieee=MsgData[idx+6:idx+22]
        power=MsgData[idx+22:idx+24]
        rssi=MsgData[idx+24:idx+26]

        if DeviceExist(self, Devices, saddr, ieee):
            Domoticz.Debug("[{:02n}".format((round(idx/26))) + "] DevID = " + DevID + " Network addr = " + saddr + " IEEE = " + ieee + " LQI = {:03n}".format((int(rssi,16))) + " Power = " + power + " HB = {:02n}".format(int(self.ListOfDevices[saddr]['Heartbeat'])) + " found in ListOfDevices")

            if rssi !="00" :
                self.ListOfDevices[saddr]['RSSI']= int(rssi,16)
            else  :
                self.ListOfDevices[saddr]['RSSI']= 12
            Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[saddr]['RSSI']) + "/" + str(rssi) + " for " + str(saddr) )
        else: 
            Domoticz.Status("[{:02n}".format((round(idx/26))) + "] DevID = " + DevID + " Network addr = " + saddr + " IEEE = " + ieee + " LQI = {:03n}".format(int(rssi,16)) + " Power = " + power + " not found in ListOfDevices")
        idx=idx+26

    Domoticz.Debug("Decode8015 - IEEE2NWK      : " +str(self.IEEE2NWK) )
    return

def Decode8024(self, Devices, MsgData, MsgRSSI) : # Network joined / formed
    MsgLen=len(MsgData)
    MsgDataStatus=MsgData[0:2]

    if MsgDataStatus != '00':
        if MsgDataStatus == "00": 
            Domoticz.Status("Joined existing network")
        elif MsgDataStatus == "01": 
            Domoticz.Status("Formed new network")
        elif MsgDataStatus == "04":
            Domoticz.Status("Busy Node")
        else: 
            Status = DisplayStatusCode( MsgDataStatus )
            Domoticz.Log("Network joined / formed Status: %s: %s" %(MsgDataStatus, Status) )
        return
    
    if MsgLen != 24:
        Domoticz.Debug("Decode8024 - uncomplete frame, MsgData: %s, Len: %s out of 24, data received: >%s<" %(MsgData, MsgLen, Data) )
        return

    MsgShortAddress=MsgData[2:6]
    MsgExtendedAddress=MsgData[6:22]
    MsgChannel=MsgData[22:24]

    if MsgExtendedAddress != '' and MsgShortAddress != '':
        self.currentChannel = int(MsgChannel,16)
        self.ZigateIEEE = MsgExtendedAddress
        self.ZigateNWKID = MsgShortAddress
        self.iaszonemgt.setZigateIEEE( MsgExtendedAddress )

    Domoticz.Status("Zigate details IEEE: %s, NetworkID: %s, Channel: %s, Status: %s: %s" \
            %(MsgExtendedAddress, MsgShortAddress, MsgChannel, MsgDataStatus, Status) )

def Decode8028(self, Devices, MsgData, MsgRSSI) : # Authenticate response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8028 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgGatewayIEEE=MsgData[0:16]
    MsgEncryptKey=MsgData[16:32]
    MsgMic=MsgData[32:40]
    MsgNodeIEEE=MsgData[40:56]
    MsgActiveKeySequenceNumber=MsgData[56:58]
    MsgChannel=MsgData[58:60]
    MsgShortPANid=MsgData[60:64]
    MsgExtPANid=MsgData[64:80]
    
    Domoticz.Log("ZigateRead - MsgType 8028 - Authenticate response, Gateway IEEE : " + MsgGatewayIEEE + " Encrypt Key : " + MsgEncryptKey + " Mic : " + MsgMic + " Node IEEE : " + MsgNodeIEEE + " Active Key Sequence number : " + MsgActiveKeySequenceNumber + " Channel : " + MsgChannel + " Short PAN id : " + MsgShortPANid + "Extended PAN id : " + MsgExtPANid )
    return

def Decode802B(self, Devices, MsgData, MsgRSSI) : # User Descriptor Notify
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode802B - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    
    Domoticz.Log("ZigateRead - MsgType 802B - User Descriptor Notify, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest)
    return

def Decode802C(self, Devices, MsgData, MsgRSSI) : # User Descriptor Response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode802C - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    MsgLenght=MsgData[8:10]
    MsgMData=MsgData[10:len(MsgData)]
    
    Domoticz.Log("ZigateRead - MsgType 802C - User Descriptor Notify, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest + " Lenght : " + MsgLenght + " Data : " + MsgMData)
    return

def Decode8030(self, Devices, MsgData, MsgRSSI) : # Bind response
    MsgLen=len(MsgData)
    Domoticz.Log("Decode8030 - MsgData lenght is : " + str(MsgLen) + " out of 4 ")
    Domoticz.Log("Decode8030 - Msgdata: %s" %(MsgData))

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]

    if MsgLen > 4:
        # Firmware 3.1a
        MsgSrcEp = MsgData[4:6]
        MsgSrcAddrMode = MsgData[6:8]
        if int(MsgSrcAddrMode,16) == ADDRESS_MODE['short']:
            MsgSrcAddr=MsgData[8:12]
            Domoticz.Log("Decode8030 - Bind reponse for %s/%s" %(MsgSrcAddr, MsgSrcEp))
        elif int(MsgSrcAddrMode,16) == ADDRESS_MODE['ieee']:
            MsgSrcAddr=MsgData[8:24]
            Domoticz.Log("Decode8030 - Bind reponse for %s/%s" %(MsgSrcAddr, MsgSrcEp))
        else:
            Domoticz.Error("Decode8030 - Unknown addr mode %s in %s" %(MsgSrcAddrMode, MsgData))

    if MsgDataStatus != '00':
        Domoticz.Log("Decode8030 - Bind response SQN: %s status [%s] - %s" %(MsgSequenceNumber ,MsgDataStatus, DisplayStatusCode(MsgDataStatus)) )

    Domoticz.Log("Decode8030 - Bind response, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ))
    return

def Decode8031(self, Devices, MsgData, MsgRSSI) : # Unbind response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8031 - MsgData lenght is : " + str(MsgLen) + " out of 2" )
    Domoticz.Log("Decode8031 - Msgdata: %s" %(MsgData))

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]

    if MsgLen > 4:
        # Firmware 3.1a
        MsgSrcEp = MsgData[4:6]
        MsgSrcAddrMode = MsgData[6:8]
        if int(MsgSrcAddrMode,16) == ADDRESS_MODE['short']:
            MsgSrcAddr=MsgData[8:12]
            MsgDataSQN=MsgData[12:14]
            Domoticz.Log("Decode8031 - Unbind reponse for %s/%s" %(MsgSrcAddr, MsgSrcEp))
        elif int(MsgSrcAddrMode,16) == ADDRESS_MODE['ieee']:
            MsgSrcAddr=MsgData[8:24]
            MsgDataSQN=MsgData[24:26]
            Domoticz.Log("Decode8031 - Unbind reponse for %s/%s" %(MsgSrcAddr, MsgSrcEp))
        else:
            Domoticz.Error("Decode8031 - Unknown addr mode %s in %s" %(MsgSrcAddr, MsgData))

    if MsgDataStatus != '00':
        Domoticz.Debug("Decode8031 - Unbind response SQN: %s status [%s] - %s" %(MsgSequenceNumber ,MsgDataStatus, DisplayStatusCode(MsgDataStatus)) )
    
    Domoticz.Debug("ZigateRead - MsgType 8031 - Unbind response, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ))
    return

def Decode8034(self, Devices, MsgData, MsgRSSI) : # Complex Descriptor response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8034 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    MsgLenght=MsgData[8:10]
    MsgXMLTag=MsgData[10:12]
    MsgCountField=MsgData[12:14]
    MsgFieldValues=MsgData[14:len(MsgData)]
    
    Domoticz.Log("Decode8034 - Complex Descriptor for: %s xmlTag: %s fieldCount: %s fieldValue: %s, Status: %s" \
            %( MsgNetworkAddressInterest, MsgXMLTag, MsgCountField, MsgFieldValues, MsgDataStatus))

    return

def Decode8040(self, Devices, MsgData, MsgRSSI) : # Network Address response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8040 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgIEEE=MsgData[4:20]
    MsgShortAddress=MsgData[20:24]
    MsgNumAssocDevices=MsgData[24:26]
    MsgStartIndex=MsgData[26:28]
    MsgDeviceList=MsgData[28:len(MsgData)]
    
    Domoticz.Status("Network Address response, Sequence number : " + MsgSequenceNumber + " Status : " 
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

    Domoticz.Log("Decode8041 - IEEE Address response, Sequence number : " + MsgSequenceNumber + " Status : " 
                    + DisplayStatusCode( MsgDataStatus ) + " IEEE : " + MsgIEEE + " Short Address : " + MsgShortAddress 
                    + " number of associated devices : " + MsgNumAssocDevices + " Start Index : " + MsgStartIndex + " Device List : " + MsgDeviceList)


    if ( self.pluginconf.pluginConf['logFORMAT'] == 1 ) :
        Domoticz.Log("Zigate activity for | 8041 " +str(MsgShortAddress) + " | " + str(MsgIEEE) + " | " + str(int(MsgRSSI,16)) + " | " +str(MsgSequenceNumber) +" | ")

    if self.ListOfDevices[MsgShortAddress]['Status'] == "8041" :        # We have requested a IEEE address for a Short Address, 
                                                                        # hoping that we can reconnect to an existing Device
        if DeviceExist(self, Devices, MsgShortAddress, MsgIEEE ) == True :
            Domoticz.Log("Decode 8041 - Device details : " +str(self.ListOfDevices[MsgShortAddress]) )
        else :
            Domoticz.Error("Decode 8041 - Unknown device : " +str(MsgShortAddress) + " IEEE : " +str(MsgIEEE) )
    
    return

def Decode8042(self, Devices, MsgData, MsgRSSI) : # Node Descriptor response

    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8042 - MsgData lenght is : " + str(MsgLen) + " out of 34")

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

    Domoticz.Debug("Decode8042 - Reception Node Descriptor for : " +addr + " SEQ : " + sequence + " Status : " + status +" manufacturer :" + manufacturer + " mac_capability : "+str(mac_capability) + " bit_field : " +str(bit_field) )

    if addr not in self.ListOfDevices:
        Domoticz.Log("Decode8042 receives a message from a non existing device %s" %addr)
        return

    mac_capability = int(mac_capability,16)
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

    Domoticz.Debug("Decode8042 - Alternate PAN Coordinator = " +str(AltPAN ))    # 1 if node is capable of becoming a PAN coordinator
    Domoticz.Debug("Decode8042 - Receiver on Idle = " +str(ReceiveonIdle))     # 1 if the device does not disable its receiver to 
                                                                            # conserve power during idle periods.
    Domoticz.Debug("Decode8042 - Power Source = " +str(PowerSource))            # 1 if the current power source is mains power. 
    Domoticz.Debug("Decode8042 - Device type  = " +str(DeviceType))            # 1 if this node is a full function device (FFD). 

    bit_fieldL   = int(bit_field[2:4],16)
    bit_fieldH   = int(bit_field[0:2],16)
    LogicalType =   bit_fieldL & 0x00F
    if   LogicalType == 0 : LogicalType = "Coordinator"
    elif LogicalType == 1 : LogicalType = "Router"
    elif LogicalType == 2 : LogicalType = "End Device"
    Domoticz.Debug("Decode8042 - bit_field = " +str(bit_fieldL) +" : "+str(bit_fieldH) )
    Domoticz.Debug("Decode8042 - Logical Type = " +str(LogicalType) )

    if self.ListOfDevices[addr]['Status'] != "inDB" :
        if self.pluginconf.pluginConf['allowStoreDiscoveryFrames'] and addr in self.DiscoveryDevices :
            self.DiscoveryDevices[addr]['Manufacturer'] = manufacturer
            self.DiscoveryDevices[addr]['8042'] = MsgData
            self.DiscoveryDevices[addr]['DeviceType'] = str(DeviceType)
            self.DiscoveryDevices[addr]['LogicalType'] = str(LogicalType)
            self.DiscoveryDevices[addr]['PowerSource'] = str(PowerSource)
            self.DiscoveryDevices[addr]['ReceiveOnIdle'] = str(ReceiveonIdle)

    self.ListOfDevices[addr]['Manufacturer']=manufacturer
    self.ListOfDevices[addr]['DeviceType']=str(DeviceType)
    self.ListOfDevices[addr]['LogicalType']=str(LogicalType)
    self.ListOfDevices[addr]['PowerSource']=str(PowerSource)
    self.ListOfDevices[addr]['ReceiveOnIdle']=str(ReceiveonIdle)

    return

def Decode8043(self, Devices, MsgData, MsgRSSI) : # Reception Simple descriptor response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8043 - MsgData lenght is : " + str(MsgLen) )

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataLenght=MsgData[8:10]
    Domoticz.Debug("Decode8043 - Reception Simple descriptor response : SQN : " + MsgDataSQN + \
            ", Status : " + DisplayStatusCode( MsgDataStatus ) + ", short Addr : " + MsgDataShAddr + ", Lenght : " + MsgDataLenght)

    updSQN( self, MsgDataShAddr, MsgDataSQN)


    if int(MsgDataLenght,16) == 0 : return

    MsgDataEp=MsgData[10:12]
    MsgDataProfile=MsgData[12:16]
    MsgDataDeviceId=MsgData[16:20]
    MsgDataBField=MsgData[20:22]
    MsgDataInClusterCount=MsgData[22:24]

    if MsgDataShAddr not in self.ListOfDevices:
        Domoticz.Log("Decode8043 - receive message for non existing device")
        return

    if int(MsgDataProfile,16) == 0xC05E and int(MsgDataDeviceId,16) == 0xE15E:
        # ZLL Commissioning EndPoint / Jaiwel
        Domoticz.Log("Decode8043 - Received ProfileID: %s, ZDeviceID: %s - skip" %(MsgDataProfile, MsgDataDeviceId))
        if MsgDataEp in self.ListOfDevices[MsgDataShAddr]['Ep']:
            del self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp]
        if 'NbEp' in  self.ListOfDevices[MsgDataShAddr]:
            if self.ListOfDevices[MsgDataShAddr]['NbEp'] > '1':
                self.ListOfDevices[MsgDataShAddr]['NbEp'] = int( self.ListOfDevices[MsgDataShAddr]['NbEp']) - 1
        return

    Domoticz.Status("[%s] NEW OBJECT: %s Simple Descriptor EP %s" %('-', MsgDataShAddr, MsgDataEp))

    if 'ProfileID' in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]['ProfileID'] != MsgDataProfile:
            Domoticz.Log("Decode8043 - Overwrite ProfileID %s with %s from Ep: %s " \
                    %( self.ListOfDevices[MsgDataShAddr]['ProfileID'] , MsgDataProfile, MsgDataEp))
    self.ListOfDevices[MsgDataShAddr]['ProfileID'] = MsgDataProfile
    Domoticz.Status("[%s] NEW OBJECT: %s ProfileID %s" %('-', MsgDataShAddr, MsgDataProfile))

    if 'ZDeviceID' in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] != MsgDataDeviceId:
            Domoticz.Log("Decode8043 - Overwrite ZDeviceID %s with %s from Ep: %s " \
                    %( self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] , MsgDataProfile, MsgDataEp))
    self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] = MsgDataDeviceId
    Domoticz.Status("[%s] NEW OBJECT: %s ZDeviceID %s" %('-', MsgDataShAddr, MsgDataDeviceId))

    # Decoding Cluster IN
    Domoticz.Status("[%s] NEW OBJECT: %s Cluster IN Count: %s" %('-', MsgDataShAddr, MsgDataInClusterCount))
    idx = 24
    i=1
    if int(MsgDataInClusterCount,16)>0 :
        while i <= int(MsgDataInClusterCount,16) :
            MsgDataCluster=MsgData[idx+((i-1)*4):idx+(i*4)]
            if 'ConfigSource' in self.ListOfDevices[MsgDataShAddr]:
                if self.ListOfDevices[MsgDataShAddr]['ConfigSource'] != 'DeviceConf':
                    if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                        self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
                else:
                    Domoticz.Debug("[%s] NEW OBJECT: %s we keep DeviceConf info" %('-',MsgDataShAddr))
            else: # Not 'ConfigSource'
                self.ListOfDevices[MsgDataShAddr]['ConfigSource'] = '8043'
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}

            if MsgDataCluster in ZCL_CLUSTERS_LIST:
                Domoticz.Status("[%s] NEW OBJECT: %s Cluster In %s: %s (%s)" %('-', MsgDataShAddr, i, MsgDataCluster, ZCL_CLUSTERS_LIST[MsgDataCluster]))
            else:
                Domoticz.Status("[%s] NEW OBJECT: %s Cluster In %s: %s" %('-', MsgDataShAddr, i, MsgDataCluster))
            MsgDataCluster=""
            i=i+1

    # Decoding Cluster Out
    idx = 24 + int(MsgDataInClusterCount,16) *4
    MsgDataOutClusterCount=MsgData[idx:idx+2]

    Domoticz.Status("[%s] NEW OBJECT: %s Cluster OUT Count: %s" %('-', MsgDataShAddr, MsgDataOutClusterCount))
    idx += 2
    i=1
    if int(MsgDataOutClusterCount,16)>0 :
        while i <= int(MsgDataOutClusterCount,16) :
            MsgDataCluster=MsgData[idx+((i-1)*4):idx+(i*4)]
            if 'ConfigSource' in self.ListOfDevices[MsgDataShAddr]:
                if self.ListOfDevices[MsgDataShAddr]['ConfigSource'] != 'DeviceConf':
                    if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                        self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
                else:
                    Domoticz.Debug("[%s] NEW OBJECT: %s we keep DeviceConf info" %('-',MsgDataShAddr))
            else: # Not 'ConfigSource'
                self.ListOfDevices[MsgDataShAddr]['ConfigSource'] = '8043'
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}

            if MsgDataCluster in ZCL_CLUSTERS_LIST:
                Domoticz.Status("[%s] NEW OBJECT: %s Cluster Out %s: %s (%s)" %('-', MsgDataShAddr, i, MsgDataCluster, ZCL_CLUSTERS_LIST[MsgDataCluster]))
            else:
                Domoticz.Status("[%s] NEW OBJECT: %s Cluster Out %s: %s" %('-', MsgDataShAddr, i, MsgDataCluster))
            MsgDataCluster=""
            i=i+1

    if self.pluginconf.pluginConf['allowStoreDiscoveryFrames'] and MsgDataShAddr in self.DiscoveryDevices :
        self.DiscoveryDevices[MsgDataShAddr]['ProfileID'][MsgDataProfile] = MsgDataEp
        self.DiscoveryDevices[MsgDataShAddr]['ZDeviceID'][MsgDataDeviceId] = MsgDataEp
        if self.DiscoveryDevices[MsgDataShAddr].get('8043') :
            self.DiscoveryDevices[MsgDataShAddr]['8043'][MsgDataEp] = str(MsgData)
            self.DiscoveryDevices[MsgDataShAddr]['Ep'] = dict( self.ListOfDevices[MsgDataShAddr]['Ep'] )
        else :
            self.DiscoveryDevices[MsgDataShAddr]['8043'] = {}
            self.DiscoveryDevices[MsgDataShAddr]['8043'][MsgDataEp] = str(MsgData)
            self.DiscoveryDevices[MsgDataShAddr]['Ep'] = dict( self.ListOfDevices[MsgDataShAddr]['Ep'] )
        
        if 'IEEE' in self.ListOfDevices[MsgDataShAddr]:
            _jsonFilename = self.pluginconf.pluginConf['pluginZData'] + "/DiscoveryDevice-" + str(self.ListOfDevices[MsgDataShAddr]['IEEE']) + ".json"
        else:
            _jsonFilename = self.pluginconf.pluginConf['pluginZData'] + "/DiscoveryDevice-" + str(MsgDataShAddr) + ".json"

        with open ( _jsonFilename, 'at') as json_file:
            json.dump(self.DiscoveryDevices[MsgDataShAddr],json_file, indent=4, sort_keys=True)

    if self.ListOfDevices[MsgDataShAddr]['Status'] != "inDB" :
        self.ListOfDevices[MsgDataShAddr]['Status'] = "8043"
        self.ListOfDevices[MsgDataShAddr]['Heartbeat'] = "0"
    else :
        updSQN( self, MsgDataShAddr, MsgDataSQN)

    Domoticz.Debug("Decode8043 - Processed " + MsgDataShAddr + " end results is : " + str(self.ListOfDevices[MsgDataShAddr]) )
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

    Domoticz.Debug("Decode8044 - SQNum = " +SQNum +" Status = " + Status + " Power mode = " + power_mode + " power_source = " + power_source + " current_power_source = " + current_power_source + " current_power_level = " + current_power_level )
    return

def Decode8045(self, Devices, MsgData, MsgRSSI) : # Reception Active endpoint response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8045 - MsgData lenght is : " + str(MsgLen) )

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataEpCount=MsgData[8:10]

    MsgDataEPlist=MsgData[10:len(MsgData)]

    Domoticz.Debug("Decode8045 - Reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + DisplayStatusCode( MsgDataStatus ) + ", short Addr " + MsgDataShAddr + ", List " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)

    OutEPlist=""
    
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
            i = i + 2
        self.ListOfDevices[MsgDataShAddr]['NbEp'] =  str(int(MsgDataEpCount,16))     # Store the number of EPs

        for iterEp in self.ListOfDevices[MsgDataShAddr]['Ep']:
            Domoticz.Status("[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" %( '-', MsgDataShAddr, iterEp))
            sendZigateCmd(self,"0043", str(MsgDataShAddr)+str(iterEp))
        if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
            self.ListOfDevices[MsgDataShAddr]['Heartbeat'] = "0"
            self.ListOfDevices[MsgDataShAddr]['Status'] = "0043"

        Domoticz.Debug("Decode8045 - Device : " + str(MsgDataShAddr) + " updated ListofDevices with " + str(self.ListOfDevices[MsgDataShAddr]['Ep']) )

        if self.pluginconf.pluginConf['allowStoreDiscoveryFrames'] and MsgDataShAddr in self.DiscoveryDevices :
            self.DiscoveryDevices[MsgDataShAddr]['8045'] = str(MsgData)
            self.DiscoveryDevices[MsgDataShAddr]['NbEP'] = str(int(MsgDataEpCount,16))

    return

def Decode8046(self, Devices, MsgData, MsgRSSI) : # Match Descriptor response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8046 - MsgData lenght is : " + str(MsgLen) )

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataLenList=MsgData[8:10]
    MsgDataMatchList=MsgData[10:len(MsgData)]

    updSQN( self, MsgDataShAddr, MsgDataSQN)
    Domoticz.Log("Decode8046 - Match Descriptor response : SQN : " + MsgDataSQN + ", Status " + DisplayStatusCode( MsgDataStatus ) + ", short Addr " + MsgDataShAddr + ", Lenght list  " + MsgDataLenList + ", Match list " + MsgDataMatchList)
    return

def Decode8047(self, Devices, MsgData, MsgRSSI) : # Management Leave response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8047 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]

    Domoticz.Status("Decode8047 - Leave response, SQN: %s Status: %s - %s" \
            %( MsgSequenceNumber, MsgDataStatus, DisplayStatusCode( MsgDataStatus )))

    return

def Decode8048(self, Devices, MsgData, MsgRSSI) : # Leave indication
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8048 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgExtAddress=MsgData[0:16]
    MsgDataStatus=MsgData[16:18]
    
    Domoticz.Status("Leave indication from IEEE: %s , Status: %s " %(MsgExtAddress, MsgDataStatus))
    devName = ''
    for x in Devices:
        if Devices[x].DeviceID == MsgExtAddress:
            devName = Devices[x].Name
            break
    self.adminWidgets.updateNotificationWidget( Devices, 'Leave indication from %s for %s ' %(MsgExtAddress, devName) )

    if ( self.pluginconf.pluginConf['logFORMAT'] == 1 ) :
        Domoticz.Log("Zigate activity for | 8048 |  | " + str(MsgExtAddress) + " | " + str(int(MsgRSSI,16)) + " |  | ")

    if MsgExtAddress not in self.IEEE2NWK: # Most likely this object has been removed and we are receiving the confirmation.
        return
    sAddr = getSaddrfromIEEE( self, MsgExtAddress )

    if sAddr == '' :
        Domoticz.Log("Decode8048 - device not found with IEEE = " +str(MsgExtAddress) )
    else :
        timeStamped(self, sAddr, 0x8048)
        Domoticz.Status("device " +str(sAddr) + " annouced to leave" )
        if self.ListOfDevices[sAddr]['Status'] == 'inDB':
            self.ListOfDevices[sAddr]['Status'] = 'Left'
            self.ListOfDevices[sAddr]['Heartbeat'] = 0
            Domoticz.Status("Calling leaveMgt to request a rejoin of %s/%s " %( sAddr, MsgExtAddress))
            leaveMgtReJoin( self, sAddr, MsgExtAddress )

    return

def Decode804A(self, Devices, MsgData, MsgRSSI) : # Management Network Update response

    self.networkenergy.NwkScanResponse( MsgData)
    return

def Decode804B(self, Devices, MsgData, MsgRSSI) : # System Server Discovery response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode804B - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgServerMask=MsgData[4:8]
    
    Domoticz.Log("ZigateRead - MsgType 804B - System Server Discovery response, Sequence number : " + MsgSequenceNumber + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Server Mask : " + MsgServerMask)
    return

def Decode804E( self, Devices, MsgData, MsgRSSI):

    Domoticz.Debug("Decode804E - Receive message")
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
    Domoticz.Debug("Decode80A0 - MsgData lenght is : " + str(MsgLen) + " out of 24" )

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
    
    Domoticz.Log("ZigateRead - MsgType 80A0 - View Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
    return

def Decode80A1(self, Devices, MsgData, MsgRSSI) : # Add Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A1 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    Domoticz.Log("ZigateRead - MsgType 80A1 - Add Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

def Decode80A2(self, Devices, MsgData, MsgRSSI) : # Remove Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A2 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    Domoticz.Log("ZigateRead - MsgType 80A2 - Remove Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

def Decode80A3(self, Devices, MsgData, MsgRSSI) : # Remove All Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A3 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    
    Domoticz.Log("ZigateRead - MsgType 80A3 - Remove All Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
    return

def Decode80A4(self, Devices, MsgData, MsgRSSI) : # Store Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A4 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    Domoticz.Log("ZigateRead - MsgType 80A4 - Store Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return
    
def Decode80A6(self, Devices, MsgData, MsgRSSI) : # Scene Membership response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A6 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgCapacity=MsgData[10:12]
    MsgGroupID=MsgData[12:16]
    MsgSceneCount=MsgData[16:18]
    MsgSceneList=MsgData[18:len(MsgData)]
    
    Domoticz.Log("ZigateRead - MsgType 80A6 - Scene Membership response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

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

    Domoticz.Debug("Decode8100 - Report Individual Attribute : [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" \
            %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData ))

    timeStamped( self, MsgSrcAddr , 0x8100)
    if ( self.pluginconf.pluginConf['logFORMAT'] == 1 ) :
        Domoticz.Log("Zigate activity for | 8100 | " +str(MsgSrcAddr) +" |  | " + str(int(MsgRSSI,16)) + " | " +str(MsgSQN) + "  | ")
    try :
        self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
    except : 
        self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Health' in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
    updSQN( self, MsgSrcAddr, MsgSQN)
    ReadCluster(self, Devices, MsgData) 

    return

def Decode8101(self, Devices, MsgData, MsgRSSI) :  # Default Response
    MsgDataSQN=MsgData[0:2]
    MsgDataEp=MsgData[2:4]
    MsgClusterId=MsgData[4:8]
    MsgDataCommand=MsgData[8:10]
    MsgDataStatus=MsgData[10:12]
    Domoticz.Debug("Decode8101 - Default response - SQN: %s, EP: %s, ClusterID: %s , DataCommand: %s, - Status: [%s] %s" \
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

    Domoticz.Debug("Decode8102 - Individual Attribute response : [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" \
            %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData ))

    if ( self.pluginconf.pluginConf['logFORMAT'] == 1 ) :
        if 'IEEE' in self.ListOfDevices[MsgSrcAddr]:
            Domoticz.Log("Zigate activity for | 8102 | " +str(MsgSrcAddr) +" | " +str(self.ListOfDevices[MsgSrcAddr]['IEEE']) +" | " + str(int(MsgRSSI,16)) + " | " +str(MsgSQN) + "  | ")
        else:
            Domoticz.Log("Zigate activity for | 8102 | " +str(MsgSrcAddr) +" | - | " + str(int(MsgRSSI,16)) + " | " +str(MsgSQN) + "  | ")

    if DeviceExist(self, Devices, MsgSrcAddr) == True :
        try:
            self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
        except:
            self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

        Domoticz.Debug("Decode8102 : Attribute Report from " + str(MsgSrcAddr) + " SQN = " + str(MsgSQN) + " ClusterID = " 
                        + str(MsgClusterId) + " AttrID = " +str(MsgAttrID) + " Attribute Data = " + str(MsgClusterData) )

        lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
        if 'Health' in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
        timeStamped( self, MsgSrcAddr , 0x8102)
        updSQN( self, MsgSrcAddr, str(MsgSQN) )
        ReadCluster(self, Devices, MsgData) 
    else :
        # This device is unknown, and we don't have the IEEE to check if there is a device coming with a new sAddr
        # Will request in the next hearbeat to for a IEEE request
        Domoticz.Error("Decode8102 - Receiving a message from unknown device : " + str(MsgSrcAddr) + " with Data : " +str(MsgData) )
        #Domoticz.Status("Decode8102 - Will try to reconnect device : " + str(MsgSrcAddr) )
        #Domoticz.Status("Decode8102 - but will most likely fail if it is battery powered device.")
        #initDeviceInList(self, MsgSrcAddr)
        #self.ListOfDevices[MsgSrcAddr]['Status']="0041"
        #self.ListOfDevices[MsgSrcAddr]['MacCapa']= "0"
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

    Domoticz.Debug("Decode8110 - WriteAttributeResponse - MsgSQN: %s, MsgSrcAddr: %s, MsgSrcEp: %s, MsgClusterId: %s, MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
            %( MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    timeStamped( self, MsgSrcAddr , 0x8110)
    updSQN( self, MsgSrcAddr, MsgSQN)

    if MsgClusterId == "0500":
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 3, MsgClusterData)

    return

def Decode8120(self, Devices, MsgData, MsgRSSI) :  # Configure Reporting response

    Domoticz.Debug("Decode8120 - Configure reporting response : %s" %MsgData)
    if len(MsgData) < 14:
        Domoticz.Error("Decode8120 - uncomplet message %s " %MsgData)
        return

    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    RemainData = MsgData[12:len(MsgData)]

    Domoticz.Debug("Decode8120 - SQN: %s, SrcAddr: %s, SrcEP: %s, ClusterID: %s, RemainData: %s" %(MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, RemainData))


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
        Domoticz.Debug("nbAttribute: %s, idx: %s" %(nbattribute, idx))
        MsgDataStatus = MsgData[(12+(nbattribute*4)):(12+(nbattribute*4)+2)]
        Domoticz.Debug("Decode8120 - Attributes : %s status: %s " %(str(MsgAttribute), MsgDataStatus))

    Domoticz.Debug("Decode8120 - Configure Reporting response - ClusterID: %s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s - %s" \
       %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgDataStatus, DisplayStatusCode( MsgDataStatus) ))

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
        Domoticz.Debug("Decode8120 - Configure Reporting response - ClusterID: %s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s - %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgDataStatus, DisplayStatusCode( MsgDataStatus) ))
    return

def Decode8140(self, Devices, MsgData, MsgRSSI) :  # Attribute Discovery response
    MsgComplete=MsgData[0:2]
    MsgAttType=MsgData[2:4]
    MsgAttID=MsgData[4:8]
    
    if len(MsgData) > 8:
        MsgSrcAddr = MsgData[8:12]
        MsgSrcEp = MsgData[12:14]
        MsgClusterID = MsgData[14:18]

        Domoticz.Log("Decode8140 - Attribute Discovery Response - %s/%s - Cluster: %s - Attribute: %s - Attribute Type: %s"
            %( MsgSrcAddr, MsgSrcEp, MsgClusterID, MsgAttID, MsgAttType))
        
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

        if self.pluginconf.pluginConf['allowStoreDiscoveryFrames'] and MsgSrcAddr in self.DiscoveryDevices :
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

            if 'IEEE' in self.ListOfDevices[MsgSrcAddr]:
                _jsonFilename = self.pluginconf.pluginConf['pluginZData'] + "/DiscoveryDevice-" + str(self.ListOfDevices[MsgSrcAddr]['IEEE']) + ".json"
            else:
                _jsonFilename = self.pluginconf.pluginConf['pluginZData'] + "/DiscoveryDevice-" + str(MsgSrcAddr) + ".json"
            with open ( _jsonFilename, 'at') as json_file:
                json.dump(self.DiscoveryDevices[MsgSrcAddr],json_file, indent=4, sort_keys=True)

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
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8701 - MsgLen = " + str(MsgLen))

    if MsgLen==0 :
        return
    else:
        # This is the reverse of what is documented. Suspecting that we got a BigEndian uint16 instead of 2 uint8
        Status=MsgData[2:4]
        NwkStatus=MsgData[0:2]
    
    Domoticz.Debug("Decode8701 - Route discovery has been performed, status: %s Nwk Status: %s " \
            %( Status, NwkStatus))

    if NwkStatus != "00" :
        Domoticz.Debug("Decode8701 - Route discovery has been performed, status: %s - %s Nwk Status: %s - %s " \
                %( Status, DisplayStatusCode( Status ), NwkStatus, DisplayStatusCode(NwkStatus)))

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

    if self.FirmwareVersion.lower() <= '030f':
        MsgDataDestAddr=MsgData[8:24]
        MsgDataSQN=MsgData[24:26]
        if int(MsgDataDestAddr,16) == ( int(MsgDataDestAddr,16) & 0xffff000000000000):
            MsgDataDestAddr = MsgDataDestAddr[0:4]
    else:    # Fixed by https://github.com/fairecasoimeme/ZiGate/issues/161
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
        Domoticz.Log("Decode8702 - Unknown Address %s : (%s,%s)" %( MsgDataDestAddr, NWKID, IEEE ))
        return
    
    if self.APS:
        self.APS.processAPSFailure(NWKID, IEEE, MsgDataStatus)

    timeStamped( self, NWKID , 0x8702)
    updSQN( self, NWKID, MsgDataSQN)

    return

#Device Announce
def Decode004D(self, Devices, MsgData, MsgRSSI) : # Reception Device announce
    MsgSrcAddr=MsgData[0:4]
    MsgIEEE=MsgData[4:20]
    MsgMacCapa=MsgData[20:22]

    if MsgSrcAddr in self.ListOfDevices:
        if self.ListOfDevices[MsgSrcAddr]['Status'] in ( '004d', '0045', '0043', '8045', '8043'):
            # Let's skip it has this is a duplicate message from the device
            return

    Domoticz.Status("Device Annoucement ShortAddr: %s, IEEE: %s " %( MsgSrcAddr, MsgIEEE))

    if ( self.pluginconf.pluginConf['logFORMAT'] == 1 ) :
        Domoticz.Log("Zigate activity for | 004d | " +str(MsgSrcAddr) +" | " + str(MsgIEEE) + " | " + str(int(MsgRSSI,16)) + " |  | ")

    # Test if Device Exist, if Left then we can reconnect, otherwise initialize the ListOfDevice for this entry
    if not DeviceExist(self, Devices, MsgSrcAddr, MsgIEEE):
        if MsgIEEE in self.IEEE2NWK :
            if self.IEEE2NWK[MsgIEEE] :
                Domoticz.Log("Decode004d - self.IEEE2NWK[MsgIEEE] = " +str(self.IEEE2NWK[MsgIEEE]) )
        self.IEEE2NWK[MsgIEEE] = MsgSrcAddr
        if not IEEEExist( self, MsgIEEE ):
            initDeviceInList(self, MsgSrcAddr)
            Domoticz.Debug("Decode004d - Looks like it is a new device sent by Zigate")
            self.CommiSSionning = True
            self.ListOfDevices[MsgSrcAddr]['MacCapa'] = MsgMacCapa
            self.ListOfDevices[MsgSrcAddr]['IEEE'] = MsgIEEE
        else:
            # we are getting a Dupplicate. Most-likely the Device is existing and we have to reconnect.
            if not DeviceExist(self, Devices, MsgSrcAddr,MsgIEEE):
                Domoticz.Log("Decode004d - Paranoia .... NwkID: %s, IEEE: % -> %s " %(MsgSrcAddr, MsgIEEE, str(self.ListOfDevices[MsgSrcAddr])))
        # We will request immediatly the List of EndPoints
        self.ListOfDevices[MsgSrcAddr]['Heartbeat'] = "0"
        self.ListOfDevices[MsgSrcAddr]['Status'] = "0045"
        sendZigateCmd(self,"0045", str(MsgSrcAddr))             # Request list of EPs

        Domoticz.Debug("Decode004d - " + str(MsgSrcAddr) + " Info: " +str(self.ListOfDevices[MsgSrcAddr]) )

    else:
        # Device exist
        # We will also reset ReadAttributes
        if self.pluginconf.pluginConf['allowReBindingClusters']:
            Domoticz.Log("Decode004d - rebind clusters for %s" %MsgSrcAddr)
            rebind_Clusters( self, MsgSrcAddr)

            if 'ReadAttributes' in self.ListOfDevices[MsgSrcAddr]:
                del self.ListOfDevices[MsgSrcAddr]['ReadAttributes']
    
            if 'ConfigureReporting' in self.ListOfDevices[MsgSrcAddr]:
                del self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']
                self.ListOfDevices[MsgSrcAddr]['Heartbeat'] = 0

            # Let's take the opportunity to trigger some request/adjustement
            ReadAttributeRequest_0000( self,  MsgSrcAddr)
            sendZigateCmd(self,"0042", str(MsgSrcAddr) )

    timeStamped( self, MsgSrcAddr , 0x004d)

    if self.pluginconf.pluginConf['allowStoreDiscoveryFrames']:
        self.DiscoveryDevices[MsgSrcAddr] = {}
        self.DiscoveryDevices[MsgSrcAddr]['004d']={}
        self.DiscoveryDevices[MsgSrcAddr]['8043']={}
        self.DiscoveryDevices[MsgSrcAddr]['8045']={}
        self.DiscoveryDevices[MsgSrcAddr]['Ep']={}
        self.DiscoveryDevices[MsgSrcAddr]['MacCapa']={}
        self.DiscoveryDevices[MsgSrcAddr]['IEEE']={}
        self.DiscoveryDevices[MsgSrcAddr]['ProfileID']={}
        self.DiscoveryDevices[MsgSrcAddr]['ZDeviceID']={}
        self.DiscoveryDevices[MsgSrcAddr]['004d'] = str(MsgData)
        self.DiscoveryDevices[MsgSrcAddr]['IEEE'] = str(MsgIEEE)
        self.DiscoveryDevices[MsgSrcAddr]['MacCapa'] = str(MsgMacCapa)
    
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

    Domoticz.Debug("Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
            %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))

    if MsgSrcAddr not in self.ListOfDevices:
        return
    timeStamped( self, MsgSrcAddr , 0x8085)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return

    if self.ListOfDevices[MsgSrcAddr]['Model'] in ( 'TRADFRI remote control', 'RC 110'):

        if MsgClusterId == '0008':
            if MsgCmd in TYPE_ACTIONS:
                selector = TYPE_ACTIONS[MsgCmd]
                Domoticz.Debug("Decode8085 - Selector: %s" %selector)
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector )
            else:
                Domoticz.Log("Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" \
                        %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
        else:
            Domoticz.Log("Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" \
                    %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
    else:
       Domoticz.Log("Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
               %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))


def Decode8095(self, Devices, MsgData, MsgRSSI) :
    'Remote button pressed ON/OFF'

    MsgSQN = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]

    Domoticz.Debug("Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " \
            %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))

    if MsgSrcAddr not in self.ListOfDevices:
        return
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
        else:
            Domoticz.Log("Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))

    elif self.ListOfDevices[MsgSrcAddr]['Model'] == 'TRADFRI motion sensor':
        """
        Ikea Motion Sensor
        """
        if MsgClusterId == '0006' and MsgCmd == '42':   # Motion Sensor On
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, "0406", '01')
        else:
            Domoticz.Log("Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
    else:
        MajDomoDevice( self, Devices, MsgSrcAddr, MsgEP, "0006", MsgCmd)
        Domoticz.Debug("Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))


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

    Domoticz.Debug("Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
    if MsgSrcAddr not in self.ListOfDevices:
        return
    timeStamped( self, MsgSrcAddr , 0x80A7)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return

    if MsgClusterId == '0005':
        if MsgDirection not in TYPE_DIRECTIONS:
            # Might be in the case of Release Left or Right
            Domoticz.Log("Decode80A7 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                    %(MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))

        elif MsgCmd in TYPE_ACTIONS and MsgDirection in TYPE_DIRECTIONS:
            selector = TYPE_DIRECTIONS[MsgDirection] + '_' + TYPE_ACTIONS[MsgCmd]
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector )
            Domoticz.Debug("Decode80A7 - selector: %s" %selector)

            if self.groupmgt:
                if TYPE_DIRECTIONS[MsgDirection] in ( 'right', 'left'):
                    self.groupmgt.manageIkeaTradfriRemoteLeftRight( MsgSrcAddr, TYPE_DIRECTIONS[MsgDirection])
        else:
            Domoticz.Log("Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                    %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
    else:
        Domoticz.Log("Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" \
                %(MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))




