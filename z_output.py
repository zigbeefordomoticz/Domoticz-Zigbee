#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_output.py

	Description: All communications towards Zigate


"""

import Domoticz
import binascii
import time
import struct
import json
import queue

import z_var
import z_tools

def ZigateConf_light( channel, discover ):
	################### ZiGate - get Firmware version #############
	# answer is expected on message 8010
	sendZigateCmd("0010","")

	################### ZiGate - Request Device List #############
	# answer is expected on message 8015. Only available since firmware 03.0b
	Domoticz.Log("ZigateConf -  Request : Get List of Device " + str(z_var.FirmwareVersion) )
	sendZigateCmd("0015","")

	################### ZiGate - discover mode 255 sec Max ##################
	#### Set discover mode only if requested - so != 0				  #####
	if str(discover) != "0":
		if str(discover)=="255": 
			Domoticz.Status("Zigate enter in discover mode for ever")
		else : 
			Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
		sendZigateCmd("0049","FFFC" + hex(int(discover))[2:4] + "00")

def ZigateConf( channel, discover ):

	################### ZiGate - get Firmware version #############
	# answer is expected on message 8010
	sendZigateCmd("0010","",2)

	################### ZiGate - Request Device List #############
	# answer is expected on message 8015. Only available since firmware 03.0b
	Domoticz.Log("ZigateConf -  Request : Get List of Device " + str(z_var.FirmwareVersion) )
	sendZigateCmd("0015","",2)

	################### ZiGate - discover mode 255 sec Max ##################
	#### Set discover mode only if requested - so != 0				  #####
	if str(discover) != "0":
		if str(discover)=="255": 
			Domoticz.Status("Zigate enter in discover mode for ever")
		else : 
			Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
		sendZigateCmd("0049","FFFC" + hex(int(discover))[2:4] + "00", 2)

	################### ZiGate - set channel ##################
	sendZigateCmd("0021", "0000" + z_tools.returnlen(2,hex(int(channel))[2:4]) + "00", 2)

	################### ZiGate - Set Type COORDINATOR #################
	sendZigateCmd("0023","00", 2)
	
	################### ZiGate - start network ##################
	sendZigateCmd("0024","", 2)
		
def sendZigateCmd(cmd,datas, _weight=1 ) :
	def ZigateEncode(Data):  # ajoute le transcodage
		Domoticz.Debug("ZigateEncode - Encodind data : " + Data)
		Out=""
		Outtmp=""
		Transcode = False
		for c in Data :
			Outtmp+=c
			if len(Outtmp)==2 :
				if Outtmp[0] == "1" and Outtmp != "10":
					if Outtmp[1] == "0" :
						Outtmp="0200"
						Out+=Outtmp
					else :
						Out+=Outtmp
				elif Outtmp[0] == "0" :
					Out+="021" + Outtmp[1]
				else :
					Out+=Outtmp
				Outtmp=""
		Domoticz.Debug("Transcode in : " + str(Data) + "  / out :" + str(Out) )
		return Out

	def getChecksum(msgtype,length,datas) :
		temp = 0 ^ int(msgtype[0:2],16)
		temp ^= int(msgtype[2:4],16)
		temp ^= int(length[0:2],16)
		temp ^= int(length[2:4],16)
		for i in range(0,len(datas),2) :
			temp ^= int(datas[i:i+2],16)
			chk=hex(temp)
		Domoticz.Debug("getChecksum - Checksum : " + str(chk))
		return chk[2:4]


	command = {}
	command['cmd'] = cmd
	command['datas'] = datas

	if datas == "" :
		length="0000"
	else :
		length=z_tools.returnlen(4,(str(hex(int(round(len(datas)/2)))).split('x')[-1]))  # by Cortexlegeni 
		Domoticz.Debug("sendZigateCmd - length is : " + str(length) )
	if datas =="" :
		checksumCmd=getChecksum(cmd,length,"0")
		if len(checksumCmd)==1 :
			strchecksum="0" + str(checksumCmd)
		else :
			strchecksum=checksumCmd
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + "03" 
	else :
		checksumCmd=getChecksum(cmd,length,datas)
		if len(checksumCmd)==1 :
			strchecksum="0" + str(checksumCmd)
		else :
			strchecksum=checksumCmd
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"   
	Domoticz.Debug("sendZigateCmd - Command send : " + str(lineinput))

	# Compute the Delay based on the weight of the command and the current queue
	# For instance if queue is empty , you can engage the command immediatly
	# _weight

	if z_var.cmdInProgress.qsize() == 0 : 	# reset Delay to 0 as we don't have any more request in the pipe
		delay = 0			# Allow immediate execution, and reset to default the liveSendDelay
		z_var.liveSendDelay = z_var.sendDelay 
	else :					# Compute delay with _weight 
		delay = ( z_var.sendDelay * _weight) * ( z_var.cmdInProgress.qsize() )
		if delay < z_var.liveSendDelay:	# If the computed Delay is lower than previous, we must stay on the last one until queue is empty
			delay =  z_var.liveSendDelay
		else :
			z_var.liveSendDelay = delay

	z_var.cmdInProgress.put( command )
	Domoticz.Debug("sendZigateCmd - Command in queue : " + str( z_var.cmdInProgress.qsize() ) )
	if z_var.cmdInProgress.qsize() > 15 :
		Domoticz.Log("sendZigateCmd - Command in queue : > 15 - queue is : " + str( z_var.cmdInProgress.qsize() ) )
		Domoticz.Log("sendZigateCmd() - Computed delay is : " + str(delay) + " liveSendDelay : " + str( z_var.liveSendDelay) + " based on _weight = " +str(_weight) + " sendDelay = " + str(z_var.sendDelay) + " Qsize = " + str(z_var.cmdInProgress.qsize()) )

	Domoticz.Debug("sendZigateCmd() - Computed delay is : " + str(delay) + " liveSendDelay : " + str( z_var.liveSendDelay) + " based on _weight = " +str(_weight) + " sendDelay = " + str(z_var.sendDelay) + " Qsize = " + str(z_var.cmdInProgress.qsize()) )

	if str(z_var.transport) == "USB" or str(z_var.transport) == "Wifi":
		z_var.ZigateConn.Send(bytes.fromhex(str(lineinput)), delay )


def ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes ) :

	# frame to be send is :
	# DeviceID 16bits / EPin 8bits / EPout 8bits / Cluster 16bits / Direction 8bits / Manufacturer_spec 8bits / Manufacturer_id 16 bits / Nb attributes 8 bits / List of attributes ( 16bits )

	Domoticz.Debug("ReadAttributeReq - addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " +str(ListOfAttributes) ) 
	if not isinstance(ListOfAttributes, list):
		# We received only 1 attribute
		Attr = "{:04n}".format(ListOfAttributes) 
		lenAttr = 1
		weight = 1
	else :
		lenAttr = len(ListOfAttributes)
		weight = int ((lenAttr ) / 2) + 1
		Attr =''
		Domoticz.Debug("attributes : " +str(ListOfAttributes) +" len =" +str(lenAttr) )
		for x in ListOfAttributes :
			Attr += "{:04n}".format(x)

	datas = "{:02n}".format(2) + addr + EpIn + EpOut + Cluster + "00" + "00" + "0000" + "{:02n}".format(lenAttr) + Attr
	sendZigateCmd("0100", datas , weight )

def ReadAttributeRequest_0000(self, key) :
	# Basic Cluster
	EPin = "01"
	EPout= "01"

	Domoticz.Log("Request for cluster 0x0000 via Read Attribute request : " + key + " EPout = " + EPout )
	
	# General
	listAttributes = []
	listAttributes.append(0x0000) 		# ZCL Version
	listAttributes.append(0x0003)		# Hardware version
	listAttributes.append(0x0004)		# Manufacturer
	listAttributes.append(0x0005)		# Model Identifier
	listAttributes.append(0x0007)		# Power Source
	listAttributes.append(0x0010)		# Battery
	for tmpEp in self.ListOfDevices[key]['Ep'] :
			if "0000" in self.ListOfDevices[key]['Ep'][tmpEp] : #switch cluster
					EPout=tmpEp
	ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )

def ReadAttributeRequest_0001(self, key) :
	# Power Config
	EPin = "01"
	EPout= "01"
	Domoticz.Log("Request for cluster 0x0001 via Read Attribute request : " + key + " EPout = " + EPout )
	listAttributes = []
	listAttributes.append(0x0000)		# Voltage
	listAttributes.append(0x0010)		# Battery Voltage
	listAttributes.append(0x0020)		# Battery %

	for tmpEp in self.ListOfDevices[key]['Ep'] :
			if "0001" in self.ListOfDevices[key]['Ep'][tmpEp] : #switch cluster
					EPout=tmpEp
	ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0006(self, key) :
	# Cluster 0x0006 with attribute 0x0000
	EPin = "01"
	EPout= "01"
	for tmpEp in self.ListOfDevices[key]['Ep'] :
			if "0006" in self.ListOfDevices[key]['Ep'][tmpEp] : #switch cluster
					EPout=tmpEp

	Domoticz.Debug("Request OnOff status via Read Attribute request : " + key + " EPout = " + EPout )
	ReadAttributeReq( self, key, "01", EPout, "0006", 0)


def ReadAttributeRequest_0008(self, key) :
	# Cluster 0x0008 with attribute 0x0000
	EPin = "01"
	EPout= "01"
	for tmpEp in self.ListOfDevices[key]['Ep'] :
			if "0008" in self.ListOfDevices[key]['Ep'][tmpEp] : #switch cluster
					EPout=tmpEp

	Domoticz.Debug("Request Control level of shutter via Read Attribute request : " + key + " EPout = " + EPout )
	ReadAttributeReq( self, key, "01", EPout, "0008", 0)

def ReadAttributeRequest_000C(self, key) :
	# Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering
	EPin = "01"
	EPout= "02"

	Domoticz.Log("Request OnOff status for Xiaomi plug via Read Attribute request : " + key + " EPout = " + EPout )
	ReadAttributeReq( self, key, "01", EPout, "000C", 55 )
	ReadAttributeReq( self, key, "01", "01", "0000", 0xff01 )

def ReadAttributeRequest_0702(self, key) :
	# Cluster 0x0702 Metering

	listAttributes = []
	listAttributes.append(0x0000) # Current Summation Delivered
	listAttributes.append(0x01)
	listAttributes.append(0x0100)
	listAttributes.append(0x0200)
	listAttributes.append(0x0300)
	listAttributes.append(0x0400) # Instantaneous Demand

	listAttributes.append(0xE000) # http://www.netvox.com.tw/usermanual/Z803_UserManual_ENG_WEB.pdf
	listAttributes.append(0xE001)
	listAttributes.append(0xE002)
	listAttributes.append(0xE003)

	EPin = "01"
	EPout= "09"
	for tmpEp in self.ListOfDevices[key]['Ep'] :
			if "0702" in self.ListOfDevices[key]['Ep'][tmpEp] : #switch cluster
					EPout=tmpEp
	Domoticz.Log("Request Metering infor for Salus plug via Read Attribute request : " + key + " EPout = " + EPout )
	ReadAttributeReq( self, key, EPin, EPout, "0702", listAttributes)



def removeZigateDevice( self, key ) :
	# remove a device in Zigate
	# Key is the short address of the device
	# extended address is ieee address

	if key in  self.ListOfDevices:
		ieee =  self.ListOfDevices[key]['IEEE']
		Domoticz.Log("Remove from Zigate Device = " + str(key) + " IEEE = " +str(ieee) )
		sendZigateCmd("0026", str(ieee) + str(ieee) )
	else :
		Domoticz.Log("Unknow device to be removed - Device  = " + str(key))

	return


def enableReporting( self, nwkid, cluster, AttrId  ) :

	AttributeType = { 
			'0006' : { '0000': '0010' },
			'0008' : { '0000': '0020' },
			'000c' : { '0055': '0039' },
			'0702' : { '0000': '0025', '0400' : '86FF' }
			} 

	if cluster == '' or cluster is None :
		Domoticz.Log("enableReporting - No cluster found : " +str(cluster) )
		return 

	AttrType = ''
	if cluster in AttributeType :
		if AttrId in AttributeType[cluster] :
			AttrType = AttributeType[cluster][AttrId]

	if AttrType == '' or AttrType is None :
		Domoticz.Log("enableReporting - AttrType no found : " +str(cluster) )
		return

	if not isinstance(AttrId, list):
		# We received only 1 attribute
		Attr = AttrId
		lenAttr = 1
		weight = 1
	else :
		lenAttr = len(AttrId)
		weight = int ((lenAttr ) / 2) + 1
		Attr =''
		Domoticz.Debug("attributes : " +str(ListOfAttributes) +" len =" +str(lenAttr) )
		for x in AttrId :
       			Attr += x

	MinInter = "0005"	# 5 Seconds
	MaxInter = "0300"	# 5 minutes
	TimeOut =  "0000"
	ChgFlag =  "01"		# Minimum change 1	

	EPout = "01"
	for tmpEp in self.ListOfDevices[nwkid]['Ep'] :
		if cluster in self.ListOfDevices[nwkid]['Ep'][tmpEp] : #switch cluster
			EPout=tmpEp
			
	'''
	Address Mode    : u8
	Network Address : u16
	Source EP       : u8
	Dest   EP       : u8
    ClusterId       : u16
    Direction       : u8
	Manufacturer spe: u8
	Manufacturer Id : u16
	Nb attributes   : u8
	Attribute list  : u16 each
	Attribute direc : u8
	Attribute Type  : u8
	Min Interval    : u16
	Max Interval    : u16
	TimeOut         : u16
	Change			: u8
	'''
	
	datas = "{:02n}".format(2) + nwkid + "01" + EPout + cluster + "00" + "00" + "0000" + "{:02n}".format(lenAttr) + Attr + "00" + AttrType + MinInter + MaxInter + TimeOut + ChgFlag
	Domoticz.Log("enableReporting - " +str(datas) )
	sendZigateCmd("0120", datas , weight )


def attribute_discovery_request(self, addr, endpoint, cluster):

	EPout = "01"
	for tmpEp in self.ListOfDevices[nwkid]['Ep'] :
		if cluster in self.ListOfDevices[nwkid]['Ep'][tmpEp] : #switch cluster
			EPout=tmpEp
	datas = "{:02n}".format(2) + nwkid + "01" + EpOut + cluster + "00" + "00" + "0000" + "FF"
	sendZigateCmd("0120", datas , weight )
