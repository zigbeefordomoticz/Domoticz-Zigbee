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
import json
import queue
import time
import json

import z_domoticz
import z_tools
import z_status
import z_output
import z_readClusters
import z_LQI


from z_IAS import IAS_Zone_Management

def ZigateRead(self, Devices, Data):
    Domoticz.Debug("ZigateRead - decoded data : " + Data + " lenght : " + str(len(Data)) )

    FrameStart=Data[0:2]
    FrameStop=Data[len(Data)-2:len(Data)]
    if ( FrameStart != "01" and FrameStop != "03" ): 
        Domoticz.Error("ZigateRead received a non-zigate frame Data : " + Data + " FS/FS = " + FrameStart + "/" + FrameStop )
        return

    MsgType=Data[2:6]
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

    if str(MsgType)=="004d":  # Device announce
        Domoticz.Debug("ZigateRead - MsgType 004d - Reception Device announce : " + Data)
        Decode004d(self, MsgData, MsgRSSI)
        return
        
    elif str(MsgType)=="00d1":  #
        Domoticz.Log("ZigateRead - MsgType 00d1 - Reception Touchlink status : " + Data)
        return
        
    elif str(MsgType)=="8000":  # Status
        Domoticz.Debug("ZigateRead - MsgType 8000 - reception status : " + Data)
        Decode8000_v2(self, MsgData)
        return

    elif str(MsgType)=="8001":  # Log
        Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level : " + Data)
        Decode8001(self, MsgData)
        return

    elif str(MsgType)=="8002":  #
        Domoticz.Log("ZigateRead - MsgType 8002 - Reception Data indication : " + Data)
        Decode8002(self, MsgData)
        return

    elif str(MsgType)=="8003":  #
        Domoticz.Debug("ZigateRead - MsgType 8003 - Reception Liste des cluster de l'objet : " + Data)
        Decode8003(self, MsgData)
        return

    elif str(MsgType)=="8004":  #
        Domoticz.Debug("ZigateRead - MsgType 8004 - Reception Liste des attributs de l'objet : " + Data)
        Decode8004(self, MsgData)
        return
        
    elif str(MsgType)=="8005":  #
        Domoticz.Debug("ZigateRead - MsgType 8005 - Reception Liste des commandes de l'objet : " + Data)
        Decode8005(self, MsgData)
        return

    elif str(MsgType)=="8006":  #
        Domoticz.Debug("ZigateRead - MsgType 8006 - Reception Non factory new restart : " + Data)
        Decode8006(self, MsgData)
        return

    elif str(MsgType)=="8007":  #
        Domoticz.Log("ZigateRead - MsgType 8007 - Reception Factory new restart : " + Data)
        #Decode8007(self, MsgData)
        return

    elif str(MsgType)=="8009":  #
        Domoticz.Debug("ZigateRead - MsgType 8009 - Network State response : " + Data)
        Decode8009( self, MsgData)
        return


    elif str(MsgType)=="8010":  # Version
        Domoticz.Debug("ZigateRead - MsgType 8010 - Reception Version list : " + Data)
        Decode8010(self, MsgData)
        return

    elif str(MsgType)=="8014":  #
        Domoticz.Debug("ZigateRead - MsgType 8014 - Reception Permit join status response : " + Data)
        Decode8014(self, MsgData)
        return

    elif str(MsgType)=="8015":  #
        Domoticz.Debug("ZigateRead - MsgType 8015 - Get devices list : " + Data)
        Decode8015(self, MsgData)
        return
        
        
    elif str(MsgType)=="8024":  #
        Domoticz.Debug("ZigateRead - MsgType 8024 - Reception Network joined /formed : " + Data)
        Decode8024(self, MsgData)
        return

    elif str(MsgType)=="8028":  #
        Domoticz.Log("ZigateRead - MsgType 8028 - Reception Authenticate response : " + Data)
        Decode8028(self, MsgData)
        return

    elif str(MsgType)=="8029":  #
        Domoticz.Log("ZigateRead - MsgType 8029 - Reception Out of band commissioning data response : " + Data)
        Decode8029(self, MsgData)
        return

    elif str(MsgType)=="802b":  #
        Domoticz.Log("ZigateRead - MsgType 802b - Reception User descriptor notify : " + Data)
        Decode802B(self, MsgData)
        return

    elif str(MsgType)=="802c":  #
        Domoticz.Log("ZigateRead - MsgType 802c - Reception User descriptor response : " + Data)
        Decode802C(self, MsgData)
        return

    elif str(MsgType)=="8030":  #
        Domoticz.Debug("ZigateRead - MsgType 8030 - Reception Bind response : " + Data)
        Decode8030(self, MsgData)
        return

    elif str(MsgType)=="8031":  #
        Domoticz.Log("ZigateRead - MsgType 8031 - Reception Unbind response : " + Data)
        Decode8031(self, MsgData)
        return

    elif str(MsgType)=="8034":  #
        Domoticz.Log("ZigateRead - MsgType 8034 - Reception Coplex Descriptor response : " + Data)
        Decode8034(self, MsgData)
        return

    elif str(MsgType)=="8040":  #
        Domoticz.Log("ZigateRead - MsgType 8040 - Reception Network address response : " + Data)
        Decode8040(self, MsgData)
        return

    elif str(MsgType)=="8041":  #
        Domoticz.Log("ZigateRead - MsgType 8041 - Reception IEEE address response : " + Data)
        Decode8041(self, MsgData, MsgRSSI)
        return

    elif str(MsgType)=="8042":  #
        Domoticz.Debug("ZigateRead - MsgType 8042 - Reception Node descriptor response : " + Data)
        Decode8042(self, MsgData)
        return

    elif str(MsgType)=="8043":  # Simple Descriptor Response
        Domoticz.Debug("ZigateRead - MsgType 8043 - Reception Simple descriptor response " + Data)
        Decode8043(self, MsgData)
        return

    elif str(MsgType)=="8044":  #
        Domoticz.Debug("ZigateRead - MsgType 8044 - Reception Power descriptor response : " + Data)
        Decode8044(self, MsgData)
        return

    elif str(MsgType)=="8045":  # Active Endpoints Response
        Domoticz.Debug("ZigateRead - MsgType 8045 - Reception Active endpoint response : " + Data)
        Decode8045(self, MsgData)
        return

    elif str(MsgType)=="8046":  #
        Domoticz.Log("ZigateRead - MsgType 8046 - Reception Match descriptor response : " + Data)
        Decode8046(self, MsgData)
        return

    elif str(MsgType)=="8047":  #
        Domoticz.Log("ZigateRead - MsgType 8047 - Reception Management leave response : " + Data)
        Decode8047(self, MsgData)
        return

    elif str(MsgType)=="8048":  #
        Domoticz.Log("ZigateRead - MsgType 8048 - Reception Leave indication : " + Data)
        Decode8048(self, MsgData, MsgRSSI)
        return

    elif str(MsgType)=="804a":  #
        Domoticz.Debug("ZigateRead - MsgType 804a - Reception Management Network Update response : " + Data)
        Decode804A(self, MsgData)
        return

    elif str(MsgType)=="804b":  #
        Domoticz.Log("ZigateRead - MsgType 804b - Reception System server discovery response : " + Data)
        Decode804B(self, MsgData)
        return

    elif str(MsgType)=="804e":  #
        Domoticz.Debug("ZigateRead - MsgType 804e - Reception Management LQI response : " + Data)
        z_LQI.mgtLQIresp( self, MsgData)    
        return

    elif str(MsgType)=="8060":  #
        Domoticz.Debug("ZigateRead - MsgType 8060 - Reception Add group response : " + Data)
        self.groupmgt.addGroupResponse( MsgData )
        return

    elif str(MsgType)=="8061":  #
        Domoticz.Debug("ZigateRead - MsgType 8061 - Reception Viex group response : " + Data)
        self.groupmgt.viewGroupResponse( MsgData )
        return

    elif str(MsgType)=="8062":  #
        Domoticz.Debug("ZigateRead - MsgType 8062 - Reception Get group Membership response : " + Data)
        self.groupmgt.getGroupMembershipResponse(MsgData)
        return

    elif str(MsgType)=="8063":  #
        Domoticz.Debug("ZigateRead - MsgType 8063 - Reception Remove group response : " + Data)
        self.groupmgt.removeGroupResponse( MsgData )
        return

    elif str(MsgType)=="80a0":  #
        Domoticz.Log("ZigateRead - MsgType 80a0 - Reception View scene response : " + Data)
        return

    elif str(MsgType)=="80a1":  #
        Domoticz.Log("ZigateRead - MsgType 80a1 - Reception Add scene response : " + Data)
        return

    elif str(MsgType)=="80a2":  #
        Domoticz.Log("ZigateRead - MsgType 80a2 - Reception Remove scene response : " + Data)
        return

    elif str(MsgType)=="80a3":  #
        Domoticz.Log("ZigateRead - MsgType 80a3 - Reception Remove all scene response : " + Data)
        return

    elif str(MsgType)=="80a4":  #
        Domoticz.Log("ZigateRead - MsgType 80a4 - Reception Store scene response : " + Data)
        return

    elif str(MsgType)=="80a6":  #
        Domoticz.Log("ZigateRead - MsgType 80a6 - Reception Scene membership response : " + Data)
        return

    elif str(MsgType)=="8100":  #
        Domoticz.Debug("ZigateRead - MsgType 8100 - Reception Real individual attribute response : " + Data)
        Decode8100(self, Devices, MsgData, MsgRSSI)
        return

    elif str(MsgType)=="8101":  # Default Response
        Domoticz.Debug("ZigateRead - MsgType 8101 - Default Response: " + Data)
        Decode8101(self, MsgData)
        return

    elif str(MsgType)=="8102":  # Report Individual Attribute response
        Domoticz.Debug("ZigateRead - MsgType 8102 - Report Individual Attribute response : " + Data)    
        Decode8102(self, Devices, MsgData, MsgRSSI)
        return
        
    elif str(MsgType)=="8110":  #
        Domoticz.Log("ZigateRead - MsgType 8110 - Reception Write attribute response : " + Data)
        Decode8110( self, Devices, MsgData)
        return

    elif str(MsgType)=="8120":  #
        Domoticz.Debug("ZigateRead - MsgType 8120 - Reception Configure reporting response : " + Data)
        Decode8120( self, MsgData)
        return

    elif str(MsgType)=="8140":  #
        Domoticz.Log("ZigateRead - MsgType 8140 - Reception Attribute discovery response : " + Data)
        Decode8140( self, MsgData)
        return

    elif str(MsgType)=="8401":  # Reception Zone status change notification
        Domoticz.Debug("ZigateRead - MsgType 8401 - Reception Zone status change notification : " + Data)
        Decode8401(self, Devices, MsgData)
        return

    elif str(MsgType)=="8701":  # 
        Domoticz.Debug("ZigateRead - MsgType 8701 - Reception Router discovery confirm : " + Data)
        Decode8701(self, MsgData)
        return

    elif str(MsgType)=="8702":  # APS Data Confirm Fail
        Domoticz.Debug("ZigateRead - MsgType 8702 -  Reception APS Data confirm fail : " + Data)
        Decode8702(self, MsgData)
        return

    else: # unknow or not dev function
        Domoticz.Log("ZigateRead - Unknow Message Type for : " + Data)
        return
    
    return

#IAS Zone
def Decode8401(self, Devices, MsgData) : # Reception Zone status change notification

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

    z_tools.timeStamped( self, MsgSrcAddr , 8401)
    z_tools.updSQN( self, MsgSrcAddr, MsgSQN)

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
            z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0500", value)
            # Nota : tamper alarm on EP 2 are discarded
        elif  MsgEp == "01" :
            iData = (int(MsgZoneStatus,16) & 1)    # For EP 1, bit 0 = "movement"
            # bit 0 = 1 ==> movement
            if iData == 1 :    
                value = "%02d" % iData
                Domoticz.Debug("Decode8401 - PST03A-v2.2.5 mouvements alarm")
                z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0406", value)
            # bit 2 = 1 ==> tamper (device disassembly)
            iData = (int(MsgZoneStatus,16) & 4) >> 2
            if iData == 1 :     
                value = "%02d" % iData
                Domoticz.Debug("Decode8401 - PST03A-V2.2.5  tamper alarm")
                z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", value)
        else :
            Domoticz.Debug("Decode8401 - PST03A-v2.2.5, unknow EndPoint : " + MsgDataSrcEp)
    else :      ## default 
        # Previously MsgZoneStatus length was only 2 char.
        z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", MsgZoneStatus[2:4])

    return


#Responses
def Decode8000_v2(self, MsgData) : # Status
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8000_v2 - MsgData lenght is : " + str(MsgLen) + " out of 8")

    if MsgLen != 8 :
        return

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
    elif int(Status,16) >= 128 and int(Status,16) <= 244 : Status="ZigBee Error Code "+ z_status.DisplayStatusCode(Status)

    Domoticz.Debug("Decode8000_v2 - status: " + Status + " SEQ: " + SEQ + " Packet Type: " + PacketType )

    if   PacketType=="0012" : Domoticz.Log("Erase Persistent Data cmd status : " +  Status )
    elif PacketType=="0014" : Domoticz.Log("Permit Join status : " +  Status )
    elif PacketType=="0024" : Domoticz.Log("Start Network status : " +  Status )
    elif PacketType=="0026" : Domoticz.Log("Remove Device cmd status : " +  Status )
    elif PacketType=="0044" : Domoticz.Log("request Power Descriptor status : " +  Status )

    if str(MsgData[0:2]) != "00" :
        Domoticz.Log("Decode8000 - PacketType: %s Status: [%s] - %s" \
                %(PacketType, MsgData[0:2], Status))

    if PacketType in ('004a'):
        z_output.channelChangeContinue( self)

    if PacketType in ('0060', '0061', '0062', '0063', '0064', '0065'):
        self.groupmgt.statusGroupRequest
    return

def Decode8001(self, MsgData) : # Reception log Level
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8001 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgLogLvl=MsgData[0:2]
    MsgDataMessage=MsgData[2:len(MsgData)]
    
    Domoticz.Status("ZigateRead - MsgType 8001 - Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)
    return

def Decode8002(self, MsgData) : # Data indication
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
    
    Domoticz.Status("ZigateRead - MsgType 8002 - Reception Data indication, Source Address : " + MsgSourceAddress + " Destination Address : " + MsgDestinationAddress + " ProfilID : " + MsgProfilID + " ClusterID : " + MsgClusterID + " Payload size : " + MsgPayloadSize + " Message Payload : " + MsgPayload)
    return

def Decode8003(self, MsgData) : # Device cluster list
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
    
    Domoticz.Status("Decode8003 - Device Cluster list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " Cluster List : " + str(clusterLst) )
    return

def Decode8004(self, MsgData) : # Device attribut list
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

    Domoticz.Status("Decode8004 - Device Attribut list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Attribut List : " + str(attributeLst) )
    return

def Decode8005(self, MsgData) : # Command list
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

    Domoticz.Status("Decode8005 - Command list, EP source : " + MsgSourceEP + \
            " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Command List : " + str( commandLst ))
    return

def Decode8006(self,MsgData) : # Non “Factory new” Restart

    Domoticz.Debug("Decode8006 - MsgData: %s" %(MsgData))

    Status = MsgData[0:2]
    if MsgData[0:2] == "00":
        Status = "STARTUP"
    elif MsgData[0:2] == "02":
        Status = "NFN_START"
    elif MsgData[0:2] == "06":
        Status = "RUNNING"

    Domoticz.Status("Decode8006 - Non 'Factory new' Restart status: %s" %(Status) )

def Decode8009(self,MsgData) : # Network State response (Firm v3.0d)
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8009 - MsgData lenght is : " + str(MsgLen) + " out of 42")
    addr=MsgData[0:4]
    extaddr=MsgData[4:20]
    PanID=MsgData[20:24]
    extPanID=MsgData[24:40]
    Channel=MsgData[40:42]
    Domoticz.Debug("Decode8009: Network state - Address :" + addr + " extaddr :" + extaddr + " PanID : " + PanID + " Channel : " + str(int(Channel,16)) )

    self.currentChannel = int(Channel,16)
    self.ZigateIEEE = extaddr
    self.ZigateNWKID = addr

    self.iaszonemgt.setZigateIEEE( extaddr )

    Domoticz.Status("Decode8009 : Zigate addresses ieee: %s , short addr: %s" %( self.ZigateIEEE,  self.ZigateNWKID) )

    # from https://github.com/fairecasoimeme/ZiGate/issues/15 , if PanID == 0 -> Network is done
    if str(PanID) == "0" : 
        Domoticz.Status("Decode8009 : Network state DOWN ! " )
    else :
        Domoticz.Status("Decode8009 - Network state UP, PANID: %s extPANID: 0x%s Channel: %s" \
                %( PanID, extPanID, int(Channel,16) ))

    return

def Decode8010(self,MsgData) : # Reception Version list
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
    else :
         self.FirmwareVersion = str(InstaVersNum)

    return

def Decode8014(self,MsgData) : # "Permit Join" status response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8014 - MsgData lenght is : " +MsgData + "len: "+ str(MsgLen) + " out of 2")

    Status=MsgData[0:2]
    if ( Status == "00" ) : Domoticz.Status("Permit Join is Off")
    elif ( Status == "01" ) : Domoticz.Status("Permit Join is On")
    else : Domoticz.Error("Decode8014 - Unexpected value "+str(MsgData))
    return

def Decode8015(self,MsgData) : # Get device list ( following request device list 0x0015 )
    # id: 2bytes
    # addr: 4bytes
    # ieee: 8bytes
    # power_type: 2bytes - 0 Battery, 1 AC Power
    # rssi : 2 bytes - Signal Strength between 1 - 255
    numberofdev=len(MsgData)    
    Domoticz.Status("Decode8015 : Number of devices recently active in Zigate = " + str(round(numberofdev/26)) )
    idx=0
    while idx < (len(MsgData)):
        DevID=MsgData[idx:idx+2]
        saddr=MsgData[idx+2:idx+6]
        ieee=MsgData[idx+6:idx+22]
        power=MsgData[idx+22:idx+24]
        rssi=MsgData[idx+24:idx+26]

        if z_tools.DeviceExist(self, saddr, ieee):
            Domoticz.Status("Decode8015 : [{:02n}".format((round(idx/26))) + "] DevID = " + DevID + " Network addr = " + saddr + " IEEE = " + ieee + " RSSI = {:03n}".format((int(rssi,16))) + " Power = " + power + " HB = {:02n}".format(int(self.ListOfDevices[saddr]['Heartbeat'])) + " found in ListOfDevices")

            if rssi !="00" :
                self.ListOfDevices[saddr]['RSSI']= int(rssi,16)
            else  :
                self.ListOfDevices[saddr]['RSSI']= 12
            Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[saddr]['RSSI']) + "/" + str(rssi) + " for " + str(saddr) )
        else: 
            Domoticz.Status("Decode8015 : [{:02n}".format((round(idx/26))) + "] DevID = " + DevID + " Network addr = " + saddr + " IEEE = " + ieee + " RSSI = {:03n}".format(int(rssi,16)) + " Power = " + power + " not found in ListOfDevices")
        idx=idx+26

    Domoticz.Debug("Decode8015 - IEEE2NWK      : " +str(self.IEEE2NWK) )
    return

def Decode8024(self, MsgData) : # Network joined / formed
    MsgLen=len(MsgData)

    if MsgLen != 24:
        Domoticz.Log("Decode8024 - uncomplete frame, MsgData: %s, Len: %s out of 24" %(MsgData, MsgLen) )
        return

    MsgDataStatus=MsgData[0:2]
    MsgShortAddress=MsgData[2:6]
    MsgExtendedAddress=MsgData[6:22]
    MsgChannel=MsgData[22:24]

    if MsgExtendedAddress != '' and MsgShortAddress != '':
        self.currentChannel = int(MsgChannel,16)
        self.ZigateIEEE = MsgExtendedAddress
        self.ZigateNWKID = MsgShortAddress
        self.iaszonemgt.setZigateIEEE( MsgExtendedAddress )

    if MsgDataStatus == "00": 
        Status = "Joined existing network"
    elif MsgDataStatus == "01": 
        Status = "Formed new network"
    else: 
        Status = z_status.DisplayStatusCode( MsgDataStatus )
    
    Domoticz.Status("Decode8024 - Network joined / formed - IEEE: %s, NetworkID: %s, Channel: %s, Status: %s: %s" \
            %(MsgExtendedAddress, MsgShortAddress, MsgChannel, MsgDataStatus, Status) )

    #Domoticz.Status("ZigateRead - MsgType 8024 - Network joined / formed, Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Short Address : " + MsgShortAddress + " IEEE : " + MsgExtendedAddress + " Channel : " + MsgChannel)

def Decode8028(self, MsgData) : # Authenticate response
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
    
    Domoticz.Status("ZigateRead - MsgType 8028 - Authenticate response, Gateway IEEE : " + MsgGatewayIEEE + " Encrypt Key : " + MsgEncryptKey + " Mic : " + MsgMic + " Node IEEE : " + MsgNodeIEEE + " Active Key Sequence number : " + MsgActiveKeySequenceNumber + " Channel : " + MsgChannel + " Short PAN id : " + MsgShortPANid + "Extended PAN id : " + MsgExtPANid )
    return

def Decode802B(self, MsgData) : # User Descriptor Notify
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode802B - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    
    Domoticz.Status("ZigateRead - MsgType 802B - User Descriptor Notify, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest)
    return

def Decode802C(self, MsgData) : # User Descriptor Response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode802C - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    MsgLenght=MsgData[8:10]
    MsgMData=MsgData[10:len(MsgData)]
    
    Domoticz.Status("ZigateRead - MsgType 802C - User Descriptor Notify, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest + " Lenght : " + MsgLenght + " Data : " + MsgMData)
    return

def Decode8030(self, MsgData) : # Bind response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8030 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    
    if MsgDataStatus != '00':
        Domoticz.Log("Decode8030 - Bind response SQN: %s status [%s] - %s" %(MsgSequenceNumber ,MsgDataStatus, z_status.DisplayStatusCode(MsgDataStatus)) )

    Domoticz.Debug("Decode8030 - Bind response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
    return

def Decode8031(self, MsgData) : # Unbind response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8031 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    
    Domoticz.Status("ZigateRead - MsgType 8031 - Unbind response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
    return

def Decode8034(self, MsgData) : # Complex Descriptor response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8034 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgNetworkAddressInterest=MsgData[4:8]
    MsgLenght=MsgData[8:10]
    MsgXMLTag=MsgData[10:12]
    MsgCountField=MsgData[12:14]
    MsgFieldValues=MsgData[14:len(MsgData)]
    
    Domoticz.Status("ZigateRead - MsgType 8034 - Complex Descriptor response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Network address of interest : " + MsgNetworkAddressInterest + " Lenght : " + MsgLenght + " XML Tag : " + MsgXMLTag + " Count Field : " + MsgCountField + " Field Values : " + MsgFieldValues)
    return

def Decode8040(self, MsgData) : # Network Address response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8040 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgIEEE=MsgData[4:20]
    MsgShortAddress=MsgData[20:24]
    MsgNumAssocDevices=MsgData[24:26]
    MsgStartIndex=MsgData[26:28]
    MsgDeviceList=MsgData[28:len(MsgData)]
    
    Domoticz.Status("ZigateRead - MsgType 8040 - Network Address response, Sequence number : " + MsgSequenceNumber + " Status : " 
                        + z_status.DisplayStatusCode( MsgDataStatus ) + " IEEE : " + MsgIEEE + " Short Address : " + MsgShortAddress 
                        + " number of associated devices : " + MsgNumAssocDevices + " Start Index : " + MsgStartIndex + " Device List : " + MsgDeviceList)
    return

def Decode8041(self, MsgData, MsgRSSI) : # IEEE Address response
    MsgLen=len(MsgData)

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgIEEE=MsgData[4:20]
    MsgShortAddress=MsgData[20:24]
    MsgNumAssocDevices=MsgData[24:26]
    MsgStartIndex=MsgData[26:28]
    MsgDeviceList=MsgData[28:len(MsgData)]

    Domoticz.Log("Decode8041 - IEEE Address response, Sequence number : " + MsgSequenceNumber + " Status : " 
                    + z_status.DisplayStatusCode( MsgDataStatus ) + " IEEE : " + MsgIEEE + " Short Address : " + MsgShortAddress 
                    + " number of associated devices : " + MsgNumAssocDevices + " Start Index : " + MsgStartIndex + " Device List : " + MsgDeviceList)


    if ( self.pluginconf.logFORMAT == 1 ) :
        Domoticz.Log("Zigate activity for | 8041 " +str(MsgShortAddress) + " | " + str(MsgIEEE) + " | " + str(int(MsgRSSI,16)) + " | " +str(MsgSequenceNumber) +" | ")

    if self.ListOfDevices[MsgShortAddress]['Status'] == "8041" :        # We have requested a IEEE address for a Short Address, 
                                                                        # hoping that we can reconnect to an existing Device
        if z_tools.DeviceExist(self, MsgShortAddress, MsgIEEE ) == True :
            Domoticz.Log("Decode 8041 - Device details : " +str(self.ListOfDevices[MsgShortAddress]) )
        else :
            Domoticz.Error("Decode 8041 - Unknown device : " +str(MsgShortAddress) + " IEEE : " +str(MsgIEEE) )
    
    return

def Decode8042(self, MsgData) : # Node Descriptor response

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

    if self.ListOfDevices[addr]['Status']!="inDB" :
        if self.pluginconf.allowStoreDiscoveryFrames == 1 and addr in self.DiscoveryDevices :
            self.DiscoveryDevices[addr]['Manufacturer']=manufacturer
            self.DiscoveryDevices[addr]['8042']=MsgData
            self.DiscoveryDevices[addr]['DeviceType']=str(DeviceType)
            self.DiscoveryDevices[addr]['LogicalType']=str(LogicalType)
            self.DiscoveryDevices[addr]['PowerSource']=str(PowerSource)
            self.DiscoveryDevices[addr]['ReceiveOnIdle']=str(ReceiveonIdle)

    self.ListOfDevices[addr]['Manufacturer']=manufacturer
    self.ListOfDevices[addr]['DeviceType']=str(DeviceType)
    self.ListOfDevices[addr]['LogicalType']=str(LogicalType)
    self.ListOfDevices[addr]['PowerSource']=str(PowerSource)
    self.ListOfDevices[addr]['ReceiveOnIdle']=str(ReceiveonIdle)

    return

def Decode8043(self, MsgData) : # Reception Simple descriptor response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8043 - MsgData lenght is : " + str(MsgLen) )

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataLenght=MsgData[8:10]
    Domoticz.Debug("Decode8043 - Reception Simple descriptor response : SQN : " + MsgDataSQN + \
            ", Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + ", short Addr : " + MsgDataShAddr + ", Lenght : " + MsgDataLenght)

    z_tools.updSQN( self, MsgDataShAddr, MsgDataSQN)


    if int(MsgDataLenght,16) == 0 : return

    MsgDataEp=MsgData[10:12]
    MsgDataProfile=MsgData[12:16]
    MsgDataDeviceId=MsgData[16:20]
    MsgDataBField=MsgData[20:22]
    MsgDataInClusterCount=MsgData[22:24]

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
            if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
            Domoticz.Status("[%s] NEW OBJECT: %s Cluster In %s: %s" %('-', MsgDataShAddr, i, MsgDataCluster))
            MsgDataCluster=""
            i=i+1

    # Decoding Cluster Out
    idx = 24 + int(MsgDataInClusterCount,16) *4
    MsgDataOutClusterCount=MsgData[idx:idx+2]
    Domoticz.Status("[%s] NEW OBJECT: %s Cluster OUT Count: %s" %('-', MsgDataShAddr, MsgDataOutClusterCount))

    
    print("Cluster Out: %s" %MsgDataOutClusterCount)
    idx += 2
    i=1
    if int(MsgDataOutClusterCount,16)>0 :
        while i <= int(MsgDataOutClusterCount,16) :
            MsgDataCluster=MsgData[idx+((i-1)*4):idx+(i*4)]
            if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
                self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
            Domoticz.Status("[%s] NEW OBJECT: %s Cluster Out %s: %s" %('-', MsgDataShAddr, i, MsgDataCluster))
            MsgDataCluster=""
            i=i+1

    if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgDataShAddr in self.DiscoveryDevices :
        self.DiscoveryDevices[MsgDataShAddr]['ProfileID']=MsgDataProfile
        self.DiscoveryDevices[MsgDataShAddr]['ZDeviceID']=MsgDataDeviceId
        if self.DiscoveryDevices[MsgDataShAddr].get('8043') :
            self.DiscoveryDevices[MsgDataShAddr]['8043'][MsgDataEp] = str(MsgData)
            self.DiscoveryDevices[MsgDataShAddr]['Ep'] = dict( self.ListOfDevices[MsgDataShAddr]['Ep'] )
        else :
            self.DiscoveryDevices[MsgDataShAddr]['8043'] = {}
            self.DiscoveryDevices[MsgDataShAddr]['8043'][MsgDataEp] = str(MsgData)
            self.DiscoveryDevices[MsgDataShAddr]['Ep'] = dict( self.ListOfDevices[MsgDataShAddr]['Ep'] )
        
        with open( self.homedirectory+"/Zdatas/DiscoveryDevice-"+str(MsgDataShAddr)+".txt", 'w') as file:
            file.write(MsgDataShAddr + " : " + str(self.DiscoveryDevices[MsgDataShAddr]) + "\n")

    if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
        self.ListOfDevices[MsgDataShAddr]['Status']="8043"
        self.ListOfDevices[MsgDataShAddr]['Heartbeat']="0"
    else :
        z_tools.updSQN( self, MsgDataShAddr, MsgDataSQN)

    Domoticz.Debug("Decode8043 - Processed " + MsgDataShAddr + " end results is : " + str(self.ListOfDevices[MsgDataShAddr]) )
    return

def Decode8044(self, MsgData): # Power Descriptior response
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

def Decode8045(self, MsgData) : # Reception Active endpoint response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8045 - MsgData lenght is : " + str(MsgLen) )

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataEpCount=MsgData[8:10]

    MsgDataEPlist=MsgData[10:len(MsgData)]

    Domoticz.Debug("Decode8045 - Reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + z_status.DisplayStatusCode( MsgDataStatus ) + ", short Addr " + MsgDataShAddr + ", List " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)

    OutEPlist=""
    
    if z_tools.DeviceExist(self, MsgDataShAddr) == False:
        #Pas sur de moi, mais si le device n'existe pas, je vois pas pkoi on continuerait
        Domoticz.Error("Decode8045 - KeyError : MsgDataShAddr = " + MsgDataShAddr)
    else :
        if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
            self.ListOfDevices[MsgDataShAddr]['Status']="8045"
        else :
            z_tools.updSQN( self, MsgDataShAddr, MsgDataSQN)
        # PP: Does that mean that if we Device is already in the Database, we might overwrite 'EP' ?

        i=0
        while i < 2 * int(MsgDataEpCount,16) :
            tmpEp = MsgDataEPlist[i:i+2]
            if not self.ListOfDevices[MsgDataShAddr]['Ep'].get(tmpEp) :
                self.ListOfDevices[MsgDataShAddr]['Ep'][tmpEp] = {}
            i = i + 2
        self.ListOfDevices[MsgDataShAddr]['NbEp'] =  str(int(MsgDataEpCount,16))     # Store the number of EPs

        Domoticz.Debug("Decode8045 - Device : " + str(MsgDataShAddr) + " updated ListofDevices with " + str(self.ListOfDevices[MsgDataShAddr]['Ep']) )

        if self.pluginconf.allowStoreDiscoveryFrames == 1 and MsgDataShAddr in self.DiscoveryDevices :
            self.DiscoveryDevices[MsgDataShAddr]['8045'] = str(MsgData)
            self.DiscoveryDevices[MsgDataShAddr]['NbEP'] = str(int(MsgDataEpCount,16))

    return

def Decode8046(self, MsgData) : # Match Descriptor response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8046 - MsgData lenght is : " + str(MsgLen) )

    MsgDataSQN=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgDataShAddr=MsgData[4:8]
    MsgDataLenList=MsgData[8:10]
    MsgDataMatchList=MsgData[10:len(MsgData)]

    z_tools.updSQN( self, MsgDataShAddr, MsgDataSQN)
    Domoticz.Status("Decode8046 - Match Descriptor response : SQN : " + MsgDataSQN + ", Status " + z_status.DisplayStatusCode( MsgDataStatus ) + ", short Addr " + MsgDataShAddr + ", Lenght list  " + MsgDataLenList + ", Match list " + MsgDataMatchList)
    return

def Decode8047(self, MsgData) : # Management Leave response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8047 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    
    Domoticz.Status("ZigateRead - MsgType 8047 - Management Leave response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
    return

def Decode8048(self, MsgData, MsgRSSI) : # Leave indication
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8048 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgExtAddress=MsgData[0:16]
    MsgDataStatus=MsgData[16:18]
    
    Domoticz.Status("Decode8048 - Leave indication, IEEE : " + MsgExtAddress + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))


    if ( self.pluginconf.logFORMAT == 1 ) :
        Domoticz.Log("Zigate activity for | 8048 |  | " + str(MsgExtAddress) + " | " + str(int(MsgRSSI,16)) + " |  | ")

    if MsgExtAddress not in self.IEEE2NWK: # Most likely this object has been removed and we are receiving the confirmation.
        return
    sAddr = z_tools.getSaddrfromIEEE( self, MsgExtAddress )
    if sAddr == '' :
        Domoticz.Log("Decode8048 - device not found with IEEE = " +str(MsgExtAddress) )
    else :
        Domoticz.Debug("Decode8048 - device " +str(sAddr) + " annouced to leave" )
        Domoticz.Debug("Decode8048 - most likely a 0x004d will come" )
        self.ListOfDevices[sAddr]['Status'] = 'Left'
        self.ListOfDevices[sAddr]['Hearbeat'] = 0
        Domoticz.Log("Calling leaveMgt to request a rejoin of %s/%s " %( sAddr, MsgExtAddress))
        z_output.leaveMgtReJoin( self, sAddr, MsgExtAddress )

    return

def Decode804A(self, MsgData) : # Management Network Update response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode804A - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgTotalTransmission=MsgData[4:8]
    MsgTransmissionFailures=MsgData[8:12]
    MsgScannedChannel=MsgData[12:20]
    MsgScannedChannelListCount=MsgData[20:22]
    MsgChannelListInterference=MsgData[22:len(MsgData)]

    #Decode the Channel mask received
    CHANNELS = { 11: 0x00000800,
            12: 0x00001000,
            13: 0x00002000,
            14: 0x00004000,
            15: 0x00008000,
            16: 0x00010000,
            17: 0x00020000,
            18: 0x00040000,
            19: 0x00080000,
            20: 0x00100000,
            21: 0x00200000,
            22: 0x00400000,
            23: 0x00800000,
            24: 0x01000000,
            25: 0x02000000,
            26: 0x04000000 }

    nwkscan = {}
    channelList = []
    for channel in CHANNELS:
        if int(MsgScannedChannel,16) & CHANNELS[channel]:
            channelList.append( channel )

    channelListInterferences = []
    idx = 0
    while idx < len(MsgChannelListInterference):
        channelListInterferences.append( "%X" %(int(MsgChannelListInterference[idx:idx+2],16)))
        idx += 2

    Domoticz.Status("Decode804A - Management Network Update. SQN: %s, Total Transmit: %s , Transmit Failures: %s , Status: %s) " \
            %(MsgSequenceNumber, int(MsgTotalTransmission,16), int(MsgTransmissionFailures,16), z_status.DisplayStatusCode(MsgDataStatus)) )

    timing = int(time.time())
    nwkscan[timing] = {}
    nwkscan[timing]['Total Tx'] = int(MsgTotalTransmission,16)
    nwkscan[timing]['Total failures'] = int(MsgTransmissionFailures,16)
    for chan, inter in zip( channelList, channelListInterferences ):
        nwkscan[timing][chan] = int(inter,16)
        Domoticz.Status("Decode804A -     Channel: %s Interference: : %s " %(chan, int(inter,16)))

    # Write the report onto file
    _filename =  self.pluginconf.logRepo + 'Network_scan-' + '%02d' %self.HardwareID + '.txt'
    Domoticz.Status("Network Scan report save on " +str(_filename))
    with open(_filename , 'at') as file:
        for key in nwkscan:
            file.write(str(key) + ": " + str(nwkscan[key]) + "\n")

    json_filename = _filename + ".json"
    with open( json_filename , 'at') as json_file:
        json_file.write('\n')
        json.dump( nwkscan, json_file)

    return

def Decode804B(self, MsgData) : # System Server Discovery response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode804B - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgDataStatus=MsgData[2:4]
    MsgServerMask=MsgData[4:8]
    
    Domoticz.Status("ZigateRead - MsgType 804B - System Server Discovery response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Server Mask : " + MsgServerMask)
    return

#Group response
# Implemented in z_GrpMgt.py

#Reponses SCENE
def Decode80A0(self, MsgData) : # View Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A0 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

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
    
    Domoticz.Status("ZigateRead - MsgType 80A0 - View Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
    return

def Decode80A1(self, MsgData) : # Add Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A1 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    Domoticz.Status("ZigateRead - MsgType 80A1 - Add Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

def Decode80A2(self, MsgData) : # Remove Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A2 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    Domoticz.Status("ZigateRead - MsgType 80A2 - Remove Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return

def Decode80A3(self, MsgData) : # Remove All Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A3 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    
    Domoticz.Status("ZigateRead - MsgType 80A3 - Remove All Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
    return

def Decode80A4(self, MsgData) : # Store Scene response
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode80A4 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

    MsgSequenceNumber=MsgData[0:2]
    MsgEP=MsgData[2:4]
    MsgClusterID=MsgData[4:8]
    MsgDataStatus=MsgData[8:10]
    MsgGroupID=MsgData[10:14]
    MsgSceneID=MsgData[14:16]
    
    Domoticz.Status("ZigateRead - MsgType 80A4 - Store Scene response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
    return
    
def Decode80A6(self, MsgData) : # Scene Membership response
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
    
    Domoticz.Status("ZigateRead - MsgType 80A6 - Scene Membership response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID + " Scene ID : " + MsgSceneID)
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

    z_tools.timeStamped( self, MsgSrcAddr , 8100)
    if ( self.pluginconf.logFORMAT == 1 ) :
        Domoticz.Log("Zigate activity for | 8100 | " +str(MsgSrcAddr) +" |  | " + str(int(MsgRSSI,16)) + " | " +str(MsgSQN) + "  | ")
    try :
        self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
    except : 
        self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

    z_tools.updSQN( self, MsgSrcAddr, MsgSQN)
    z_readClusters.ReadCluster(self, Devices, MsgData) 

    return

def Decode8101(self, MsgData) :  # Default Response
    MsgDataSQN=MsgData[0:2]
    MsgDataEp=MsgData[2:4]
    MsgClusterId=MsgData[4:8]
    MsgDataCommand=MsgData[8:10]
    MsgDataStatus=MsgData[10:12]
    Domoticz.Debug("Decode8101 - Default response - SQN: %s, EP: %s, ClusterID: %s , DataCommand: %s, - Status: [%s] %s" \
            %(MsgDataSQN, MsgDataEp, MsgClusterId, MsgDataCommand, MsgDataStatus,  z_status.DisplayStatusCode( MsgDataStatus ) ))
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

    if ( self.pluginconf.logFORMAT == 1 ) :
        if 'IEEE' in self.ListOfDevices[MsgSrcAddr]:
            Domoticz.Log("Zigate activity for | 8102 | " +str(MsgSrcAddr) +" | " +str(self.ListOfDevices[MsgSrcAddr]['IEEE']) +" | " + str(int(MsgRSSI,16)) + " | " +str(MsgSQN) + "  | ")
        else:
            Domoticz.Log("Zigate activity for | 8102 | " +str(MsgSrcAddr) +" | - | " + str(int(MsgRSSI,16)) + " | " +str(MsgSQN) + "  | ")

    if z_tools.DeviceExist(self, MsgSrcAddr) == True :
        try:
            self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
        except:
            self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

        Domoticz.Debug("Decode8102 : Attribute Report from " + str(MsgSrcAddr) + " SQN = " + str(MsgSQN) + " ClusterID = " 
                        + str(MsgClusterId) + " AttrID = " +str(MsgAttrID) + " Attribute Data = " + str(MsgClusterData) )

        z_tools.timeStamped( self, MsgSrcAddr , 8102)
        z_tools.updSQN( self, MsgSrcAddr, str(MsgSQN) )
        z_readClusters.ReadCluster(self, Devices, MsgData) 
    else :
        # This device is unknown, and we don't have the IEEE to check if there is a device coming with a new sAddr
        # Will request in the next hearbeat to for a IEEE request
        Domoticz.Error("Decode8102 - Receiving a message from unknown device : " + str(MsgSrcAddr) + " with Data : " +str(MsgData) )
        #Domoticz.Status("Decode8102 - Will try to reconnect device : " + str(MsgSrcAddr) )
        #Domoticz.Status("Decode8102 - but will most likely fail if it is battery powered device.")
        #z_tools.initDeviceInList(self, MsgSrcAddr)
        #self.ListOfDevices[MsgSrcAddr]['Status']="0041"
        #self.ListOfDevices[MsgSrcAddr]['MacCapa']= "0"
    return

def Decode8110(self, Devices, MsgData) :  # Write Attribute response
    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    MsgAttrID=MsgData[12:16]
    MsgAttType=MsgData[16:18]
    MsgAttSize=MsgData[18:22]
    MsgClusterData=MsgData[22:len(MsgData)]

    Domoticz.Log("Decode8110 - WriteAttributeResponse - MsgSQN: %s, MsgSrcAddr: %s, MsgSrcEp: %s, MsgClusterId: %s, MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, MsgClusterData: %s" \
            %( MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData))

    z_tools.updSQN( self, MsgSrcAddr, MsgSQN)

    if MsgClusterId == "0500":
        self.iaszonemgt.receiveIASmessages( MsgSrcAddr, 3, MsgClusterData)

    return

def Decode8120(self, MsgData) :  # Configure Reporting response
    MsgSQN=MsgData[0:2]
    MsgSrcAddr=MsgData[2:6]
    MsgSrcEp=MsgData[6:8]
    MsgClusterId=MsgData[8:12]
    MsgDataStatus=MsgData[12:14]

    Domoticz.Debug("Decode8120 - Configure Reporting response - ClusterID: %s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s - %s" \
       %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgDataStatus, z_status.DisplayStatusCode( MsgDataStatus) ))

    z_tools.updSQN( self, MsgSrcAddr, MsgSQN)


    if 'ConfigureReporting' in self.ListOfDevices[MsgSrcAddr]:
        if MsgSrcEp in self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep']:
            if str(MsgClusterId) in self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp]:
                pass
            else:
                self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}
        else:
            self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp] = {}
            self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}
    else:
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting'] = {}
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp] = {}
        self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][str(MsgClusterId)] = {}

    self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']['Ep'][MsgSrcEp][MsgClusterId] = MsgDataStatus

    if MsgDataStatus != '00':
        # Looks like that this Device doesn't handle Configure Reporting, so let's flag it as such, so we won't do it anymore
        Domoticz.Debug("Decode8120 - Configure Reporting response - ClusterID: %s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s - %s" \
            %(MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgDataStatus, z_status.DisplayStatusCode( MsgDataStatus) ))
    return

def Decode8140(self, MsgData) :  # Attribute Discovery response
    MsgComplete=MsgData[0:2]
    MsgAttType=MsgData[2:4]
    MsgAttID=MsgData[4:8]
    
    # We need to identify to which NetworkId and which ClusterId this is coming from. This is in response to 0x0140
    # When MsgComplete == 01, we have received all Attribute/AttributeType

    Domoticz.Debug("Decode8140 - Attribute Discovery response - complete : " + MsgComplete + " Attribute Type : " + MsgAttType + " Attribut ID : " + MsgAttID)
    return

#Router Discover
def Decode8701(self, MsgData) : # Reception Router Disovery Confirm Status
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8701 - MsgLen = " + str(MsgLen))

    if MsgLen==0 :
        return
    else:
        # This is the reverse of what is documented. Suspecting that we got a BigEndian uint16 instead of 2 uint8
        Status=MsgData[2:4]
        NwkStatus=MsgData[0:2]
    
    Domoticz.Log("Decode8701 - Route discovery has been performed, status: %s Nwk Status: %s " \
            %( Status, NwkStatus))

    if NwkStatus != "00" :
        Domoticz.Log("Decode8701 - Route discovery has been performed, status: %s - %s Nwk Status: %s - %s " \
                %( Status, z_status.DisplayStatusCode( Status ), NwkStatus, z_status.DisplayStatusCode(NwkStatus)))


        return

#Réponses APS
def Decode8702(self, MsgData) : # Reception APS Data confirm fail
    MsgLen=len(MsgData)
    Domoticz.Debug("Decode8702 - MsgLen = " + str(MsgLen))
    if MsgLen==0 : 
        return
    else:
        MsgDataStatus=MsgData[0:2]
        MsgDataSrcEp=MsgData[2:4]
        MsgDataDestEp=MsgData[4:6]
        MsgDataDestMode=MsgData[6:8]
        MsgDataDestAddr=MsgData[8:12]
        MsgDataSQN=MsgData[12:14]

        z_tools.updSQN( self, MsgDataDestAddr, MsgDataSQN)
        Domoticz.Debug("Decode 8702 - " +  z_status.DisplayStatusCode( MsgDataStatus )  + ", SrcEp : " + MsgDataSrcEp + ", DestEp : " + MsgDataDestEp + ", DestMode : " + MsgDataDestMode + ", DestAddr : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)
        return

#Device Announce
def Decode004d(self, MsgData, MsgRSSI) : # Reception Device announce
    MsgSrcAddr=MsgData[0:4]
    MsgIEEE=MsgData[4:20]
    MsgMacCapa=MsgData[20:22]

    Domoticz.Status("[%s] NEW OBJECT: %s Device Annouce" %(0, MsgSrcAddr))

    if ( self.pluginconf.logFORMAT == 1 ) :
        Domoticz.Log("Zigate activity for | 004d | " +str(MsgSrcAddr) +" | " + str(MsgIEEE) + " | " + str(int(MsgRSSI,16)) + " |  | ")

    # tester si le device existe deja dans la base domoticz
    if z_tools.DeviceExist(self, MsgSrcAddr,MsgIEEE) == False :
        Domoticz.Debug("Decode004d - Looks like it is a new device sent by Zigate")
        self.CommiSSionning = True
        z_tools.initDeviceInList(self, MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['MacCapa']=MsgMacCapa
        self.ListOfDevices[MsgSrcAddr]['IEEE']=MsgIEEE
        if MsgIEEE in self.IEEE2NWK :
            if self.IEEE2NWK[MsgIEEE] :
                Domoticz.Log("Decode004d - self.IEEE2NWK[MsgIEEE] = " +str(self.IEEE2NWK[MsgIEEE]) )
        self.IEEE2NWK[MsgIEEE] = MsgSrcAddr
        Domoticz.Debug("Decode004d - " + str(MsgSrcAddr) + " Info: " +str(self.ListOfDevices[MsgSrcAddr]) )
    else :
        Domoticz.Debug("Decode004d - Existing device")
        # Should we not force status to "004d" and reset Hearbeat , in order to start the processing from begining in onHeartbeat() ?

    if self.pluginconf.allowStoreDiscoveryFrames == 1 :
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


