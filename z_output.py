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

def ZigateConf( channel, discover ):

	################### ZiGate - get Firmware version #############
	# answer is expected on message 8010
	sendZigateCmd("0010","")

	################### ZiGate - set channel ##################
	sendZigateCmd("0021", "0000" + z_tools.returnlen(2,hex(int(channel))[2:4]) + "00")

	################### ZiGate - Set Type COORDINATOR #################
	sendZigateCmd("0023","00")
	
	################### ZiGate - start network ##################
	sendZigateCmd("0024","")

	################### ZiGate - Request Device List #############
	# answer is expected on message 8015. Only available since firmware 03.0b
#	if str(z_var.FirmwareVersion) == "030d" or str(z_var.FirmwareVersion) == "030c" or str(z_var.FirmwareVersion) == "030b" :
	Domoticz.Log("ZigateConf -  Request : Get List of Device " + str(z_var.FirmwareVersion) )
	sendZigateCmd("0015","")
#	else :
#		Domoticz.Error("Cannot request Get List of Device due to low firmware level" + str(z_var.FirmwareVersion) )

	################### ZiGate - discover mode 255 sec Max ##################
	#### Set discover mode only if requested - so != 0                  #####
	if str(discover) != "0":
		if str(discover)=="255": 
			Domoticz.Status("Zigate enter in discover mode for ever")
		else : 
			Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
		sendZigateCmd("0049","FFFC" + hex(int(discover))[2:4] + "00")
		
def sendZigateCmd(cmd,datas) :
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
	z_var.cmdInProgress.put( command )
	Domoticz.Debug("sendZigateCmd - Command in queue : " + str( z_var.cmdInProgress.qsize() ) )

	if str(z_var.transport) == "USB":
		if z_var.sendDelay == 0 : 
			z_var.ZigateConn.Send(bytes.fromhex(str(lineinput)))	
		else : 
			z_var.ZigateConn.Send(bytes.fromhex(str(lineinput)), z_var.sendDelay )
	if str(z_var.transport) == "Wifi":
		z_var.ZigateConn.Send(bytes.fromhex(str(lineinput))+bytes("\r\n",'utf-8'),1)


def ReadAttributeRequest_0008(self, key) :
	# Cluster 0x0008 with attribute 0x0000
	# frame to be send is :
	# DeviceID 16bits / EPin 8bits / EPout 8bits / Cluster 16bits / Direction 8bits / Manufacturer_spec 8bits / Manufacturer_id 16 bits / Nb attributes 8 bits / List of attributes ( 16bits )
	EPin = "01"
	EPout= "01"
	for tmpEp in self.ListOfDevices[key]['Ep'] :
	        if "0008" in self.ListOfDevices[key]['Ep'][tmpEp] : #switch cluster
	                EPout=tmpEp

	Domoticz.Debug("Request Control level of shutter via Read Attribute request : " + key + " EPout = " + EPout )
	sendZigateCmd("0100", "02" + str(key) + EPin + EPout + "0008" + "00" + "00" + "0000" + "01" + "0000" )

def ReadAttributeRequest_000C(self, key) :
	# Cluster 0x000C with attribute 0x0055
	# frame to be send is :
	# DeviceID 16bits / EPin 8bits / EPout 8bits / Cluster 16bits / Direction 8bits / Manufacturer_spec 8bits / Manufacturer_id 16 bits / Nb attributes 8 bits / List of attributes ( 16bits )
	EPin = "01"
	EPout= "02"

	Domoticz.Debug("Request Control level of shutter via Read Attribute request : " + key + " EPout = " + EPout )
	sendZigateCmd("0100", "02" + str(key) + EPin + EPout + "000C" + "00" + "00" + "0000" + "01" + "0055" )


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
