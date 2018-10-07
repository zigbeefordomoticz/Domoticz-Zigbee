#!/usr/bin/env python3
# coding: utf-8 -*-
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

import z_domoticz
import z_var
import z_tools
import z_status

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

	if str(MsgType)=="004d":  # Device announce
		Domoticz.Debug("ZigateRead - MsgType 004d - Reception Device announce : " + Data)
		Decode004d(self, MsgData)
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
		Domoticz.Log("ZigateRead - MsgType 8003 - Reception Liste des cluster de l'objet : " + Data)
		Decode8003(self, MsgData)
		return

	elif str(MsgType)=="8004":  #
		Domoticz.Log("ZigateRead - MsgType 8004 - Reception Liste des attributs de l'objet : " + Data)
		Decode8004(self, MsgData)
		return
		
	elif str(MsgType)=="8005":  #
		Domoticz.Log("ZigateRead - MsgType 8005 - Reception Liste des commandes de l'objet : " + Data)
		Decode8005(self, MsgData)
		return

	elif str(MsgType)=="8006":  #
		Domoticz.Log("ZigateRead - MsgType 8006 - Reception Non factory new restart : " + Data)
		#Decode8006(self, MsgData)
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
		Domoticz.Log("ZigateRead - MsgType 8024 - Reception Network joined /formed : " + Data)
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
		Domoticz.Log("ZigateRead - MsgType 8030 - Reception Bind response : " + Data)
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
		Decode8041(self, MsgData)
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
		Decode8048(self, MsgData)
		return

	elif str(MsgType)=="804a":  #
		Domoticz.Log("ZigateRead - MsgType 804a - Reception Management Network Update response : " + Data)
		Decode804A(self, MsgData)
		return

	elif str(MsgType)=="804b":  #
		Domoticz.Log("ZigateRead - MsgType 804b - Reception System server discovery response : " + Data)
		Decode804B(self, MsgData)
		return

	elif str(MsgType)=="804e":  #
		Domoticz.Log("ZigateRead - MsgType 804e - Reception Management LQI response : " + Data)
		Decode804E(self, MsgData)
		return

	elif str(MsgType)=="8060":  #
		Domoticz.Log("ZigateRead - MsgType 8060 - Reception Add group response : " + Data)
		Decode8060(self, MsgData)
		return

	elif str(MsgType)=="8061":  #
		Domoticz.Log("ZigateRead - MsgType 8061 - Reception Viex group response : " + Data)
		Decode8061(self, MsgData)
		return

	elif str(MsgType)=="8062":  #
		Domoticz.Log("ZigateRead - MsgType 8062 - Reception Get group Membership response : " + Data)
		Decode8062(self, MsgData)
		return

	elif str(MsgType)=="8063":  #
		Domoticz.Log("ZigateRead - MsgType 8063 - Reception Remove group response : " + Data)
		Decode8063(self, MsgData)
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
		return

	elif str(MsgType)=="8120":  #
		Domoticz.Log("ZigateRead - MsgType 8120 - Reception Configure reporting response : " + Data)
		return

	elif str(MsgType)=="8140":  #
		Domoticz.Log("ZigateRead - MsgType 8140 - Reception Attribute discovery response : " + Data)
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
	Domoticz.Debug("Decode8401 - Reception Zone status change notification : " + MsgData)
	MsgSQN=MsgData[0:2]			# sequence number: uint8_t
	MsgEp=MsgData[2:4]			# endpoint : uint8_t
	MsgClusterId=MsgData[4:8]		# cluster id: uint16_t
	MsgSrcAddrMode=MsgData[8:10]		# src address mode: uint8_t
	MsgSrcAddr=MsgData[10:14]		# src address: uint64_t or uint16_t based on address mode
	MsgZoneStatus=MsgData[14:18]		# zone status: uint16_t
	MsgExtStatus=MsgData[18:20]		# extended status: uint8_t
	MsgZoneID=MsgData[20:22]		# zone id : uint8_t
	MsgDelay=MsgData[22:24]			# delay: data each element uint16_t

	# 0  0  0	0  1	1	1  2  2
	# 0  2  4	8  0	4	8  0  2
	# 5a 02 0500 02 0ffd 0010 00 ff 0001
	# 5d 02 0500 02 0ffd 0011 00 ff 0001

	z_tools.updSQN( self, MsgSrcAddr, MsgSQN)

	## CLD CLD
	Model =  self.ListOfDevices[MsgSrcAddr]['Model']
	if Model == "PST03A-v2.2.5" :
		# bit 3, battery status (0=Ok 1=to replace)
		iData = int(MsgZoneStatus,16) & 8 >> 3	 			# Set batery level
		if iData == 0 :
			self.ListOfDevices[MsgSrcAddr]['Battery']="100"		# set to 100%
		else :
			self.ListOfDevices[MsgSrcAddr]['Battery']="0"
		if MsgEp == "02" :					
			iData = int(MsgZoneStatus,16) & 1	  #  For EP 2, bit 0 = "door/window status"
			# bit 0 = 1 (door is opened) ou bit 0 = 0 (door is closed)
			value = "%02d" % iData
			Domoticz.Debug("Decode8401 - PST03A-v2.2.5 door/windows status : " + value)
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0500", value)
			# Nota : tamper alarm on EP 2 are discarded
		elif  MsgEp == "01" :
			iData = (int(MsgZoneStatus,16) & 1)	# For EP 1, bit 0 = "movement"
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
	else :	  ## default 
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

	Domoticz.Debug("Decode8000 - Command in progress : " + str (z_var.cmdInProgress.qsize() ) )
	if not z_var.cmdInProgress.empty() :	 			# Should not happen
		mycmd = z_var.cmdInProgress.get(block=False, timeout=None)
		Domoticz.Debug("Decode8000 - expected command status for : " + str(mycmd['cmd']) + "/" + str(mycmd['datas']) )
		if int(mycmd['cmd'],16) == int(PacketType,16) :
			if ( len(mycmd['datas']) > 10 ) :			# As we have the datas from the sendZigateCmd() call, we have the Saddr.
				CmdSrcAddr = mycmd['datas'][2:6]
				Domoticz.Debug("Decode8000 - Command for sAddr : " +str( CmdSrcAddr ) )
				z_tools.updSQN( self, CmdSrcAddr, SEQ )

			if   Status=="00" : Status="Success"
			elif Status=="01" : Status="Incorrect Parameters"
			elif Status=="02" : Status="Unhandled Command"
			elif Status=="03" : Status="Command Failed"
			elif Status=="04" : Status="Busy"
			elif Status=="05" : Status="Stack Already Started"
			elif int(Status,16) >= 128 and int(Status,16) <= 244 : Status="ZigBee Error Code "+ z_status.DisplayStatusCode(Status)

			Domoticz.Log("Decode8000_v2 - status: " + Status + " SEQ: " + SEQ + " Packet Type: " + PacketType )

			if   PacketType=="0012" : Domoticz.Log("Erase Persistent Data cmd status : " +  Status )
			elif PacketType=="0014" : Domoticz.Log("Permit Join status : " +  Status )
			elif PacketType=="0024" : Domoticz.Log("Start Network status : " +  Status )
			elif PacketType=="0026" : Domoticz.Log("Remove Device cmd status : " +  Status )
			elif PacketType=="0044" : Domoticz.Log("request Power Descriptor status : " +  Status )

		else :
			Domoticz.Debug("Decode8000 - Out of sequence : Queue: Command " + str(mycmd) + " vs. " + str(PacketType) + " remaining queue items : " + str(z_var.cmdInProgress.qsize()) )
			# As we are out-of-sequence , this is most-likely because we have lost 1 message.
			# If I still have a message in the queue, let's dequeue one.
			if  z_var.cmdInProgress.qsize() >= 1 :
				mycmd = z_var.cmdInProgress.get(block=False, timeout=None)

	if str(MsgData[0:2]) != "00" : Domoticz.Debug("Decode8000_v2 - status: " + Status + " SEQ: " + SEQ + " Packet Type: " + PacketType )

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
	
	Domoticz.Status("ZigateRead - MsgType 8003 - Device Cluster list, EP source : " + MsgSourceEP + " ProfileID : " + MsgProfileID + " Cluster List : " + MsgClusterID)
	return

def Decode8004(self, MsgData) : # Device attribut list
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8004 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSourceEP=MsgData[0:2]
	MsgProfileID=MsgData[2:6]
	MsgClusterID=MsgData[6:10]
	MsgAttributList=MsgData[10:len(MsgData)]
	
	Domoticz.Status("ZigateRead - MsgType 8004 - Device Attribut list, EP source : " + MsgSourceEP + " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Attribut List : " + MsgAttributList)
	return

def Decode8005(self, MsgData) : # Command list
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8005 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSourceEP=MsgData[0:2]
	MsgProfileID=MsgData[2:6]
	MsgClusterID=MsgData[6:10]
	MsgCommandList=MsgData[10:len(MsgData)]
	
	Domoticz.Status("ZigateRead - MsgType 8005 - Command list, EP source : " + MsgSourceEP + " ProfileID : " + MsgProfileID + " ClusterID : " + MsgClusterID + " Command List : " + MsgCommandList)
	return

def Decode8009(self,MsgData) : # Network State response (Firm v3.0d)
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8009 - MsgData lenght is : " + str(MsgLen) + " out of 42")

	addr=MsgData[0:4]
	extaddr=MsgData[4:20]
	PanID=MsgData[20:24]
	extPanID=MsgData[24:40]
	Channel=MsgData[40:42]
	Domoticz.Debug("Decode8009: Network state - Address :" + addr + " extaddr :" + extaddr + " PanID : " + PanID + " Channel : " + str(int(Channel,16)) )
	# from https://github.com/fairecasoimeme/ZiGate/issues/15 , if PanID == 0 -> Network is done
	if str(PanID) == "0" : 
		Domoticz.Status("Decode8009: Network state DOWN ! " )
	else :
		Domoticz.Status("Decode8009: Network state UP - PAN Id = " + str(PanID) + " on Channel = " + str(int(Channel,16)) )

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
		z_var.FirmwareVersion = InstaVersNum

	return

def Decode8014(self,MsgData) : # "Permit Join" status response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8014 - MsgData lenght is : " + str(MsgLen) + " out of 1")

	Status=MsgData[0:1]
	if ( MsgData[0:1]== "0" ) : Domoticz.Status("Permit Join is Off")
	elif ( MsgData[0:1]== "1" ) : Domoticz.Status("Permit Join is On")
	else : Domoticz.Error("Decode8014 - Unexpected value "+str(MsgData))
	return

def Decode8015(self,MsgData) : # Get device list ( following request device list 0x0015 )
	# id: 2bytes
	# addr: 4bytes
	# ieee: 8bytes
	# power_type: 2bytes - 0 Battery, 1 AC Power
	# rssi : 2 bytes - Signal Strength between 1 - 255
	numberofdev=len(MsgData)	
	Domoticz.Log("Decode8015 : Number of devices known in Zigate = " + str(round(numberofdev/26)) )
	idx=0
	while idx < (len(MsgData)):
		DevID=MsgData[idx:idx+2]
		saddr=MsgData[idx+2:idx+6]
		ieee=MsgData[idx+6:idx+22]
		power=MsgData[idx+22:idx+24]
		rssi=MsgData[idx+24:idx+26]
		Domoticz.Debug("Decode8015 : Dev ID = " + DevID + " addr = " + saddr + " ieee = " + ieee + " power = " + power + " RSSI = " + str(int(rssi,16)) )
		if z_tools.DeviceExist(self, saddr, ieee):
			Domoticz.Status("Decode8015 : [ " + str(round(idx/26)) + "] DevID = " + DevID + " Addr = " + saddr + " IEEE = " + ieee + " RSSI = " + str(int(rssi,16)) + " Power = " + power + " found in ListOfDevice")
			if rssi !="00" :
				self.ListOfDevices[saddr]['RSSI']= int(rssi,16)
			else  :
				self.ListOfDevices[saddr]['RSSI']= 12
			Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[saddr]['RSSI']) + "/" + str(rssi) + " for " + str(saddr) )
		else: 
			# Let's check if the IEEE is not known !
			if not z_tools.DeviceExist( self, saddr, ieee  ) :
				Domoticz.Status("Decode8015 : [ " + str(round(idx/26)) + "] DevID = " + DevID + " Addr = " + saddr + " IEEE = " + ieee + " not found in ListOfDevice")
			else:
				Domoticz.Status("Decode8015 : [ " + str(round(idx/26)) + "] DevID = " + DevID + " Addr = " + saddr + " IEEE = " + ieee + " reconnected to ListOfDevice")
		idx=idx+26

	return

def Decode8024(self, MsgData) : # Network joined / formed
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8024 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgDataStatus=MsgData[0:2]
	MsgShortAddress=MsgData[2:6]
	MsgExtendedAddress=MsgData[6:22]
	MsgChannel=MsgData[22:24]
	
	Domoticz.Status("ZigateRead - MsgType 8024 - Network joined / formed, Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Short Address : " + MsgShortAddress + " IEEE : " + MsgExtendedAddress + " Channel : " + MsgChannel)
	return

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
	
	Domoticz.Status("ZigateRead - MsgType 8030 - Bind response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
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

def Decode8041(self, MsgData) : # IEEE Address response
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

	if self.ListOfDevices[MsgShortAddress]['Status'] == "8041" :		# We have requested a IEEE address for a Short Address, 
																		# hoping that we can reconnect to an existing Device
		if z_tools.DeviceExist(self, MsgShortAddress, MsgIEEE ) == True :
			Domoticz.Status("Decode 8041 - Device : " +str(MsgShortAddress) + " reconnected with " 
					+str(self.ListOfDevices[MsgShortAddress]['DomoID'] ) )
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
	Domoticz.Debug("Decode8042 - Reception Node Descriptor : SEQ : " + sequence + " Status : " + status )
	return

def Decode8043(self, MsgData) : # Reception Simple descriptor response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8043 - MsgData lenght is : " + str(MsgLen) )

	MsgDataSQN=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgDataShAddr=MsgData[4:8]
	MsgDataLenght=MsgData[8:10]
	Domoticz.Debug("Decode8043 - Reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + ", short Addr : " + MsgDataShAddr + ", Lenght : " + MsgDataLenght)
	if int(MsgDataLenght,16)>0 :
		MsgDataEp=MsgData[10:12]
		MsgDataProfile=MsgData[12:16]
		self.ListOfDevices[MsgDataShAddr]['ProfileID']=MsgDataProfile
		if z_var.storeDiscoveryFrames == 1 :
			self.DiscoveryDevices[MsgDataShAddr]['ProfileID']=MsgDataProfile

		MsgDataDeviceId=MsgData[16:20]
		self.ListOfDevices[MsgDataShAddr]['ZDeviceID']=MsgDataDeviceId
		if z_var.storeDiscoveryFrames == 1 :
			self.DiscoveryDevices[MsgDataShAddr]['ZDeviceID']=MsgDataDeviceId

		MsgDataBField=MsgData[20:22]
		MsgDataInClusterCount=MsgData[22:24]
		Domoticz.Debug("Decode8043 - Reception Simple descriptor response : EP : " + MsgDataEp + ", Profile : " + MsgDataProfile + ", Device Id : " + MsgDataDeviceId + ", Bit Field : " + MsgDataBField)
		Domoticz.Debug("Decode8043 - Reception Simple descriptor response : In Cluster Count : " + MsgDataInClusterCount)
		i=1
		if int(MsgDataInClusterCount,16)>0 :
			while i <= int(MsgDataInClusterCount,16) :
				MsgDataCluster=MsgData[24+((i-1)*4):24+(i*4)]
				if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
					self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
					Domoticz.Debug("self.ListOfDevices[MsgDataShAddr] = " +str(self.ListOfDevices[MsgDataShAddr]) )

				Domoticz.Debug("Decode8043 - Reception Simple descriptor response : Cluster in: " + MsgDataCluster)
				MsgDataCluster=""
				i=i+1
	
		MsgDataOutClusterCount=MsgData[24+(int(MsgDataInClusterCount,16)*4):26+(int(MsgDataInClusterCount,16)*4)]
		Domoticz.Debug("Decode8043 - Reception Simple descriptor response : Out Cluster Count : " + MsgDataOutClusterCount)
		i=1
		if int(MsgDataOutClusterCount,16)>0 :
			while i <= int(MsgDataOutClusterCount,16) :
				MsgDataCluster=MsgData[24+((i-1)*4):24+(i*4)]
				if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
					self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}

				Domoticz.Debug("Decode8043 - Reception Simple descriptor response : Cluster out: " + MsgDataCluster)
				MsgDataCluster=""
				i=i+1

	if z_var.storeDiscoveryFrames == 1 :
		self.DiscoveryDevices[MsgDataShAddr]['8043'] = str(MsgData)
		self.DiscoveryDevices[MsgDataShAddr]['Ep'] = dict( self.ListOfDevices[MsgDataShAddr]['Ep'] )

		with open( z_var.homedirectory+"/Zdatas/DiscoveryDevice-"+str(MsgDataShAddr)+".txt", 'w') as file:
			file.write(MsgDataShAddr + " : " + str(self.DiscoveryDevices[MsgDataShAddr]) + "\n")

	if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
		self.ListOfDevices[MsgDataShAddr]['Status']="8043"
	else :
		z_tools.updSQN( self, MsgDataShAddr, MsgDataSQN)

	Domoticz.Debug("Decode8043 - Processed " + MsgDataShAddr + " end results is : " + str(self.ListOfDevices[MsgDataShAddr]) )
	return

def Decode8044(self, MsgData): # Power Descriptior response
	MsgLen=len(MsgData)
	SQNum=MsgData[0:2]
	Status=MsgData[2:4]
	PowerCode=MsgData[4:8]
	Domoticz.Debug("Decode8044 - SQNum = " +SQNum +" Status = " + Status + " Power Code = " + PowerCode )
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
		for i in MsgDataEPlist :
			OutEPlist+=i
			if len(OutEPlist)==2 :
				if OutEPlist not in self.ListOfDevices[MsgDataShAddr]['Ep'] :
					self.ListOfDevices[MsgDataShAddr]['Ep'][OutEPlist]={}
					OutEPlist=""
					
	#Fin de correction

	if z_var.storeDiscoveryFrames == 1 :
		self.DiscoveryDevices[MsgDataShAddr]['8045'] = str(MsgData)

	Domoticz.Debug("Decode8045 - Device : " + str(MsgDataShAddr) + " updated ListofDevices with " + str(self.ListOfDevices[MsgDataShAddr]['Ep']) )
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

def Decode8048(self, MsgData) : # Leave indication
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8048 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgExtAddress=MsgData[0:16]
	MsgDataStatus=MsgData[16:18]
	
	Domoticz.Status("ZigateRead - MsgType 8048 - Leave indication, IEEE : " + MsgExtAddress + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
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
	MsgChannelList=MsgData[22:len(MsgData)]
	Domoticz.Status("ZigateRead - MsgType 804A - Management Network Update response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Total Transmission : " + str(int(MsgTotalTransmission,16)) + " Transmission Failures : " + str(int(MsgTransmissionFailures)) + " Scanned Channel : " + MsgScannedChannel + " Scanned Channel List Count : " + MsgScannedChannelListCount + " Channel List : " + MsgChannelList)
	return

def Decode804B(self, MsgData) : # System Server Discovery response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode804B - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSequenceNumber=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgServerMask=MsgData[4:8]
	
	Domoticz.Status("ZigateRead - MsgType 804B - System Server Discovery response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Server Mask : " + MsgServerMask)
	return

def Decode804E(self, MsgData) : # Management LQI response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode804E - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSequenceNumber=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgNeighbourTableEntrie=MsgData[4:6]
	MsgNeighbourTableListCount=MsgData[6:8]
	MsgStartIndex=MsgData[8:10]
	MsgListOfEntries=MsgData[10:len(MsgData)]
	Domoticz.Status("ZigateRead - MsgType 804E - Management LQI response, Sequence number : " + MsgSequenceNumber + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Neighbour Table Entrie : " + MsgNeighbourTableEntrie + " Neighbour Table List Count : " + MsgNeighbourTableListCount + " Start Index : " + MsgStartIndex + " List of Entries : " + MsgListOfEntries)
	return

#Group response
def Decode8060(self, MsgData) : # Add Group response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8060 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSequenceNumber=MsgData[0:2]
	MsgEP=MsgData[2:4]
	MsgClusterID=MsgData[4:8]
	
	Domoticz.Status("ZigateRead - MsgType 8060 - Add Group response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID)
	return

def Decode8061(self, MsgData) : # View Group response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8061 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSequenceNumber=MsgData[0:2]
	MsgEP=MsgData[2:4]
	MsgClusterID=MsgData[4:8]
	MsgDataStatus=MsgData[8:10]
	MsgGroupID=MsgData[10:14]
	
	Domoticz.Status("ZigateRead - MsgType 8061 - View Group response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
	return

def Decode8062(self, MsgData) : # Get Group Membership response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8062 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSequenceNumber=MsgData[0:2]
	MsgEP=MsgData[2:4]
	MsgClusterID=MsgData[4:8]
	MsgSourceAddress=MsgData[8:12]
	MsgCapacity=MsgData[12:14]
	MsgGroupCount=MsgData[14:16]
	MsgListOfGroup=MsgData[16:len(MsgData)]
	
	Domoticz.Status("ZigateRead - MsgType 8062 - Get Group Membership response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Source Address : " + MsgSourceAddress + " Capacity : " + MsgCapacity + " Group Count : " + MsgGroupCount + " List Of Group : " + MsgListOfGroup)
	return

def Decode8063(self, MsgData) : # Remove Group response
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8063 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgSequenceNumber=MsgData[0:2]
	MsgEP=MsgData[2:4]
	MsgClusterID=MsgData[4:8]
	MsgDataStatus=MsgData[8:10]
	MsgGroupID=MsgData[10:14]
	
	Domoticz.Status("ZigateRead - MsgType 8063 - Remove Group response, Sequence number : " + MsgSequenceNumber + " EndPoint : " + MsgEP + " ClusterID : " + MsgClusterID + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ) + " Group ID : " + MsgGroupID)
	return

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
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]

	Domoticz.Debug("Decode8100 - reception data : " + MsgClusterData + " ClusterID : " + MsgClusterId + " Attribut ID : " 
						+ MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp + " RSSI: " + MsgRSSI)
	try :
		self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
	except : 
		self.ListOfDevices[MsgSrcAddr]['RSSI']= 0
	Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[MsgSrcAddr]['RSSI']) + "/" 
						+ str(MsgRSSI) + " for " + str(MsgSrcAddr) )

	z_tools.updSQN( self, MsgSrcAddr, MsgSQN)
	ReadCluster(self, Devices, MsgData) 

	return

def Decode8101(self, MsgData) :  # Default Response
	MsgDataSQN=MsgData[0:2]
	MsgDataEp=MsgData[2:4]
	MsgClusterId=MsgData[4:8]
	MsgDataCommand=MsgData[8:10]
	MsgDataStatus=MsgData[10:12]
	Domoticz.Debug("Decode8101 - reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " 
						+ MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
	return

def Decode8102(self, Devices, MsgData, MsgRSSI) :  # Report Individual Attribute response
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]

	Domoticz.Debug("Decode8102 - Report Individual Attribute response - reception data : " + MsgClusterData + " ClusterID : " 
					+ MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp + " RSSI = " + MsgRSSI )
	if z_tools.DeviceExist(self, MsgSrcAddr) == True :
		try:
			self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
		except:
			self.ListOfDevices[MsgSrcAddr]['RSSI']= 0

		Domoticz.Debug("Decode8012 : RSSI set to " + str( self.ListOfDevices[MsgSrcAddr]['RSSI']) + "/" + str(MsgRSSI) 
						+ " for " + str(MsgSrcAddr) )
		Domoticz.Debug("Decode8102 : Attribute Report from " + str(MsgSrcAddr) + " SQN = " + str(MsgSQN) + " ClusterID = " 
						+ str(MsgClusterId) + " AttrID = " +str(MsgAttrID) + " Attribute Data = " + str(MsgClusterData) )

		z_tools.updSQN( self, MsgSrcAddr, str(MsgSQN) )
		ReadCluster(self, Devices, MsgData) 
	else :
		# This device is unknown, and we don't have the IEEE to check if there is a device coming with a new sAddr
		# Will request in the next hearbeat to for a IEEE request
		Domoticz.Error("Decode8102 - Receiving a message from unknown device , request a 0x0041 : " + str(MsgSrcAddr) + " with Data : " +str(MsgData) )
		Domoticz.Status("Decode8102 - Will try to reconnect device : " + str(MsgSrcAddr) )
		Domoticz.Status("Decode8102 - but will most likely fail if it is battery powered device.")
		z_tools.initDeviceInList(self, MsgSrcAddr)
		self.ListOfDevices[MsgSrcAddr]['Status']="0041"
		self.ListOfDevices[MsgSrcAddr]['MacCapa']= "0"
		Domoticz.Debug("Decode8102 - " + str(MsgSrcAddr) + " Info: " +str(self.ListOfDevices[MsgSrcAddr]) )
	return

def Decode8110(self, MsgData) :  # Write Attribute response
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]

	Domoticz.Debug("Decode8110 - Write Attribute Response - reception data : " + MsgClusterData + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp)
	return

def Decode8120(self, MsgData) :  # Configure Reporting response
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgDataStatus=MsgData[12:14]

	Domoticz.Debug("Decode8120 - Configure Reporting response - ClusterID : " + MsgClusterId + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp + " Status : " + z_status.DisplayStatusCode( MsgDataStatus ))
	return

def Decode8140(self, MsgData) :  # Attribute Discovery response
	MsgComplete=MsgData[0:2]
	MsgAttType=MsgData[2:4]
	MsgAttID=MsgData[4:8]

	Domoticz.Debug("Decode8140 - Attribute Discovery response - complete : " + MsgComplete + " Attribute Type : " + MsgAttType + " Attribut ID : " + MsgAttrID)
	return

#Router Discover
def Decode8701(self, MsgData) : # Reception Router Disovery Confirm Status
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8701 - MsgLen = " + str(MsgLen))

	if MsgLen==0 :
		return
	else:
		MsgDataStatus=MsgData[0:2]
		NwkStatus=MsgData[2:4]
		Domoticz.Debug("Decode8701 - Reception Router Discovery Confirm Status:" + z_status.DisplayStatusCode( MsgDataStatus ) + ", Nwk Status : "+ NwkStatus )
	
		if NwkStatus != "00" : Domoticz.Error("Decode8701 - Reception Router Discovery Confirm Status:" + z_status.DisplayStatusCode( NwkStatus) + ", Nwk Status : "+ NwkStatus )
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
def Decode004d(self, MsgData) : # Reception Device announce
	MsgSrcAddr=MsgData[0:4]
	MsgIEEE=MsgData[4:20]
	MsgMacCapa=MsgData[20:22]
	# tester si le device existe deja dans la base domoticz
	if z_tools.DeviceExist(self, MsgSrcAddr,MsgIEEE) == False :
		Domoticz.Debug("Decode004d - Looks like it is a new device sent by Zigate")
		z_tools.initDeviceInList(self, MsgSrcAddr)
		self.ListOfDevices[MsgSrcAddr]['MacCapa']=MsgMacCapa
		self.ListOfDevices[MsgSrcAddr]['IEEE']=MsgIEEE
		Domoticz.Debug("Decode004d - " + str(MsgSrcAddr) + " Info: " +str(self.ListOfDevices[MsgSrcAddr]) )
	else :
		Domoticz.Debug("Decode004d - Existing device")
		# Should we not force status to "004d" and reset Hearbeat , in order to start the processing from begining in onHeartbeat() ?

	if z_var.storeDiscoveryFrames == 1 :
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
	
	Domoticz.Status("Decode0004d - Reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa)
	return

def ReadCluster(self, Devices, MsgData):
	def retreive4Tag(tag,chain):
		c = str.find(chain,tag) + 4
		if c == 3: return ''
		return chain[c:(c+4)]
	def retreive8Tag(tag,chain):
		c = str.find(chain,tag) + 4
		if c == 3: return ''
		return chain[c:(c+8)]

	MsgLen=len(MsgData)
	Domoticz.Debug("ReadCluster - MsgData lenght is : " + str(MsgLen) + " out of 24+")

	if MsgLen < 24 :
		Domoticz.Error("ReadCluster - MsgData lenght is too short: " + str(MsgLen) + " out of 24+")
		Domoticz.Error("ReadCluster - MsgData : '" +str(MsgData) + "'")
		return

	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]
	tmpEp=""
	tmpClusterid=""
	if z_tools.DeviceExist(self, MsgSrcAddr) == False :
		#Pas sur de moi, mais je vois pas pkoi continuer, pas sur que de mettre a jour un device bancale soit utile
		Domoticz.Error("ReadCluster - KeyError : MsgData = " + MsgData)
		return
	else :
		self.ListOfDevices[MsgSrcAddr]['RIA']=str(int(self.ListOfDevices[MsgSrcAddr]['RIA'])+1)
		try : 
			tmpEp=self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]
			try :
				tmpClusterid=self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]
			except : 
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}
		except :
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]={}
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}

	if MsgClusterId=="0000" :  # (General: Basic)
		# It might be good to make sure that we are on a Xiaomi device - A priori : 0x115f
		if MsgAttrID=="ff01" and self.ListOfDevices[MsgSrcAddr]['Status']=="inDB" :  # xiaomi battery lvl
			Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " ClusterData : " + str(MsgClusterData) )
			# Taging: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/42#issuecomment-370152404
			# 0x0624 might be the LQI indicator and 0x0521 the RSSI dB

			sBatteryLvl = retreive4Tag( "0121", MsgClusterData )
			sTemp2	  = retreive4Tag( "0328", MsgClusterData )   # Device Temperature
			sTemp	   = retreive4Tag( "6429", MsgClusterData )
			sOnOff	  = retreive4Tag( "6410", MsgClusterData )
			sHumid	  = retreive4Tag( "6521", MsgClusterData )
			sHumid2	 = retreive4Tag( "6529", MsgClusterData )
			sPress	  = retreive8Tag( "662b", MsgClusterData )

			if sBatteryLvl != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '8e' :	# Battery Level makes sense for non main powered devices
				BatteryLvl = '%s%s' % (str(sBatteryLvl[2:4]),str(sBatteryLvl[0:2])) 
				ValueBattery=round(int(BatteryLvl,16)/10/3.3)
				self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
				Domoticz.Log("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Battery : " + str(ValueBattery) )
			if sTemp != '' :
				Temp = '%s%s' % (str(sTemp[2:4]),str(sTemp[0:2])) 
				ValueTemp=round(int(Temp,16)/100,1)
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402']=ValueTemp
				Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) )
				z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)
#			if sTemp2 != '' :
#				Temp2 = '%s%s' % (str(sTemp2[2:4]),str(sTemp2[0:2])) 
#				ValueTemp2=round(int(Temp2,16)/100,1)
#				Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Device Temperature : " + str(ValueTemp2) )
			if sHumid != '' :
				Humid = '%s%s' % (str(sHumid[2:4]),str(sHumid[0:2])) 
				ValueHumid=round(int(Humid,16)/100,1)
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0405']=ValueHumid
				Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Humidity : " + str(ValueHumid) )
				z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0405",ValueHumid)
			if sHumid2 != '' :
				Humid2 = '%s%s' % (str(sHumid2[2:4]),str(sHumid2[0:2])) 
				ValueHumid2=round(int(Humid2,16)/100,1)
				Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Humidity2 : " + str(ValueHumid2) )
			if sPress != '' :
				Press = '%s%s%s%s' % (str(sPress[6:8]),str(sPress[4:6]),str(sPress[2:4]),str(sPress[0:2])) 
				ValuePress=round((struct.unpack('i',struct.pack('i',int(Press,16)))[0])/100,1)
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]["0403"]=ValuePress
				Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Atmospheric Pressure : " + str(ValuePress) )
				z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0403",ValuePress)
			if sOnOff != '' :
				sOnOff = sOnOff[0:2]  
				z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff
				Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " On/Off : " + str(sOnOff) )


		elif MsgAttrID=="0005" :  # Model info Xiaomi
			try : 
				MType=binascii.unhexlify(MsgClusterData).decode('utf-8')										# Convert the model name to ASCII
				Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device : " + MType)
				self.ListOfDevices[MsgSrcAddr]['Model']=MType												   # Set the model name in database

				if MType in self.DeviceConf :																   # If the model exist in DeviceConf.txt
					for Ep in self.DeviceConf[MType]['Ep'] :												# For each Ep in DeviceConf.txt
						if Ep not in self.ListOfDevices[MsgSrcAddr]['Ep'] :							 # If this EP doesn't exist in database
							self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]={}							 # create it.
						for cluster in self.DeviceConf[MType]['Ep'][Ep] :							   # For each cluster discribe in DeviceConf.txt
							if cluster not in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep] :			# If this cluster doesn't exist in database
								self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}			# create it.
						if 'Type' in self.DeviceConf[MType]['Ep'][Ep] :								 # If type exist at EP level : copy it
							self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]['Type']=self.DeviceConf[MType]['Ep'][Ep]['Type']
					if 'Type' in self.DeviceConf[MType] :												   # If type exist at top level : copy it
						self.ListOfDevices[MsgSrcAddr]['Type']=self.DeviceConf[MType]['Type']
			except:
				Domoticz.Error("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - Model info Xiaomi : " +  MsgSrcAddr)
				return
		else :
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - reception heartbeat - Message attribut inconnu : " + MsgData)
			return
	
	elif MsgClusterId=="0006" :  # (General: On/Off) 
		if MsgAttrID=="0000" or MsgAttrID=="8000":
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			Domoticz.Debug("ReadCluster - ClusterId=0006 - reception General: On/Off : " + str(MsgClusterData) )

		elif MsgAttrID == "f000" and MsgAttType == "0023" and MsgAttSize == "0004" :
			Domoticz.Debug("ReadCluster - Feedback from device " + str(MsgSrcAddr) + "/" + MsgSrcEp + " MsgClusterData: " + MsgClusterData )
		else :
			Domoticz.Error("ReadCluster - ClusterId=0006 - reception heartbeat - Message attribut inconnu : " + MsgAttrID + " / " + MsgData)
			return

	elif MsgClusterId=="0008" :  # (Cluster Level Control )
		Domoticz.Debug("ReadCluster - ClusterId=0008 - Level Control : " + str(MsgClusterData) )
		Domoticz.Debug("MsgSQN: " + MsgSQN )
		Domoticz.Debug("MsgSrcAddr: " + MsgSrcAddr )
		Domoticz.Debug("MsgSrcEp: " + MsgSrcEp )
		Domoticz.Debug("MsgAttrId: " + MsgAttrID )
		Domoticz.Debug("MsgAttType: " + MsgAttType )
		Domoticz.Debug("MsgAttSize: " + MsgAttSize )
		Domoticz.Debug("MsgClusterData: " + MsgClusterData )
		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
		return

	elif MsgClusterId=="0101" :  # (Door Lock )
		def decode_vibr(value): 		#Decoding XIAOMI Vibration sensor 
			if value == '' or value is None:
				return value
			if   value == "0001" : return 'Take'
			elif value == "0002" : return 'Tilt'
			elif value == "0003" : return 'Drop'
			return ''

		Domoticz.Error("ReadCluster 0101 not fully implemented, please contact us on https://github.com/sasu-drooz/Domoticz-Zigate" )
		Domoticz.Log("ReadCluster 0101 - Dev : " +MsgSrcAddr + " Ep : " + MsgSrcEp + " Attribute : " + MsgAttrID )

		if MsgAttrID == "0000" :  		# Lockstate
			Domoticz.Log("ReadCluster 0101 - Dev : Lock state " +str(MsgClusterData) )
		elif MsgAttrID == "0001" : 		# Locktype
			Domoticz.Log("ReadCluster 0101 - Dev : Lock type "  + str(MsgClusterData))
		elif MsgAttrID == "0002" : 		# Enabled
			Domoticz.Log("ReadCluster 0101 - Dev : Enabled "  + str(MsgClusterData))
		elif MsgAttrID == "0055" : 		# Movement
			Domoticz.Log("ReadCluster 0101 - Dev : Movement " + decode_vibr( MsgClusterData ) )
		elif MsgAttrID == "0503" : 		# Rotation
			Domoticz.Log("ReadCluster 0101 - Dev : Rotation "  + str(MsgClusterData))
		elif MsgAttrID == "0505" : 		# Unknown
			Domoticz.Log("ReadCluster 0101 - Dev : Unknown "  + str(MsgClusterData))


	elif MsgClusterId=="0402" :  # (Measurement )
		#MsgValue=Data[len(Data)-8:len(Data)-4]
		#Correction Thiklop : onMessage' failed 'IndexError':'string index out of range'.
		if MsgClusterData != "":
			if MsgClusterData[0] == "f" :  # cas temperature negative
				MsgClusterData=-(int(MsgClusterData,16)^int("FFFF",16))
				z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
				Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )
			#Correction Thiklop 2 : cas des température > 1000°C
			#elif int(MsgClusterData,16) < 100000 : #1000 °C x 100
			else:
				MsgClusterData=int(MsgClusterData,16)
				z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
				Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )
			#else :
			#	Domoticz.Log("Température > 1000°C")
			#Fin de correction 2
		else : 
			Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")
		#Fin de la correction

	elif MsgClusterId=="0403" :  # (Measurement: Pression atmospherique) ### a corriger/modifier http://zigate.fr/xiaomi-capteur-temperature-humidite-et-pression-atmospherique-clusters/
		if MsgAttType=="0028":
			#z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgClusterData,8))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(MsgClusterData) )
			
		if MsgAttType=="0029" and MsgAttrID=="0000":
			#MsgValue=Data[len(Data)-8:len(Data)-4]
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
			Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16),1)))
			
		if MsgAttType=="0029" and MsgAttrID=="0010":
			#MsgValue=Data[len(Data)-8:len(Data)-4]
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/10,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/10,1)
			Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16)/10,1)))

	elif MsgClusterId=="0405" :  # (Measurement: Humidity) 
		#MsgValue=Data[len(Data)-8:len(Data)-4]
		#Correction Thiklop : le MsgClusterData n'est pas toujours un entier et est vide ?!
		#Encapsulation dans un try except pour gérer proprement le problème
		try :
			int(MsgClusterData,16)
		except :
			Domoticz.Error("ReadCluster -ClusterID=0405 - decapteur Xiamo humidité. La valeur n'est pas un entier : " + MsgClusterData)
		else :
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
			Domoticz.Debug("ReadCluster - ClusterId=0405 - reception hum : " + str(int(MsgClusterData,16)/100) )
		#Fin de correction

	elif MsgClusterId=="0406" :  # (Measurement: Occupancy Sensing) xiaomi
		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster - ClusterId=0406 - reception Occupancy Sensor : " + str(MsgClusterData) )

	elif MsgClusterId=="0400" :  # (Measurement: LUX) xiaomi
		#Correction Thiklop : le MsgClusterData n'est pas un entier hexa (message vide dans certains cas ?)
		#Encapsulation dans un try except pour une sortie propre
		try :
			int(MsgClusterData,16)
		except :
			Domoticz.Error("readCluster - Problème de conversion int du capteur LUX xiaomi. MsgClusterData = " + MsgClusterData)
		else :
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(int(MsgClusterData,16) ))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=int(MsgClusterData,16)
			Domoticz.Debug("ReadCluster - ClusterId=0400 - reception LUX Sensor : " + str(int(MsgClusterData,16)) )
		#Fin de la correction
		
	elif MsgClusterId=="0012" :  # Magic Cube Xiaomi
		# Thanks to : https://github.com/dresden-elektronik/deconz-rest-plugin/issues/138#issuecomment-325101635
		#		 +---+
		#		 | 2 |
		#	 +---+---+---+
		#	 | 4 | 0 | 1 |
		#	 +---+---+---+
		#		 | 5 |
		#		 +---+
		#		 | 3 |
		#		 +---+
		#	 Side 5 is with the MI logo; side 3 contains the battery door.
		#
		#	 Shake: 0x0000 (side on top doesn't matter)
		#	 90º Flip from side x on top to side y on top: 0x0040 + (x << 3) + y
		#	 180º Flip to side x on top: 0x0080 + x
		#	 Push while side x is on top: 0x0100 + x
		#	 Double Tap while side x is on top: 0x0200 + x
		#	 Push works in any direction.
		#	 For Double Tap you really need to lift the cube and tap it on the table twice.
		def cube_decode(value):
			value=int(value,16)
			if value == '' or value is None:
				return value

			if value == 0x0000 : 		
				Domoticz.Debug("cube action : " + 'Shake' )
				value='10'
			elif value == 0x0002 :			
				Domoticz.Debug("cube action : " + 'Wakeup' )
				value = '20'
			elif value == 0x0003 :
				Domoticz.Debug("cube action : " + 'Drop' )
				value = '30'
			elif value & 0x0040 != 0 :	
				face = value ^ 0x0040
				face1 = face >> 3
				face2 = face ^ (face1 << 3)
				Domoticz.Debug("cube action : " + 'Flip90_{}{}'.format(face1, face2))
				value = '40'
			elif value & 0x0080 != 0:  
				face = value ^ 0x0080
				Domoticz.Debug("cube action : " + 'Flip180_{}'.format(face) )
				value = '50'
			elif value & 0x0100 != 0:  
				face = value ^ 0x0100
				Domoticz.Debug("cube action : " + 'Push/Move_{}'.format(face) )
				value = '60'
			elif value & 0x0200 != 0:  # double_tap
				face = value ^ 0x0200
				Domoticz.Debug("cube action : " + 'Double_tap_{}'.format(face) )
				value = '70'
			else:  
				Domoticz.Debug("cube action : Not expected value" + value )
			return value

		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(MsgClusterData) )
		Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(cube_decode(MsgClusterData)) )
		
		
	elif MsgClusterId=="000c" :  # Magic Cube Xiaomi rotation and Power Meter
		Domoticz.Debug("ReadCluster - ClusterID=000C - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) + " len = " +str(len(MsgClusterData)))

		if  MsgSrcEp == '02' and MsgAttrID=="0055" : # Consomation Electrique
			Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0]))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0])
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(round(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0],1)))

		elif MsgSrcEp == '03' and MsgAttrID=="ff05" : # Rotation - horinzontal
			Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) )
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

		elif MsgSrcEp == '03' and MsgAttrID=="0055" : # Angle 
			Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube angle: " + str(struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0])  )
			# will need to investigate to see if this should trigger an update or not.
			# Probably the right think would be to detect clock and anti-clock rotation. 
			# Add a Selector anti-clock on the Switch seector

		else :
			Domoticz.Log("ReadCluster - ClusterID=000c - unknown message - SAddr = " + str(MsgSrcAddr) + " EP = " + str( MsgSrcEp) + " MsgAttrID = " + str(MsgAttrID) + " Value = "+ str(MsgClusterData) )

	elif MsgClusterId=="0b04" or MsgClusterId=="0702":  # 0b04 is Electrical Measurement Cluster
		Domoticz.Log("ReadCluster - ClusterID=0b04 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )
		
	else :
		Domoticz.Error("ReadCluster - Error/unknow Cluster Message : " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
		Domoticz.Error("						   MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
		Domoticz.Error("						   MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )
		return

