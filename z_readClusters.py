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

def decodeAttribute( AttrID, AttType, AttSize, Attribute ):
	'''
		decode Attribute based on their Type and Size
	'''
	'''
	https://www.dresden-elektronik.de/fileadmin/Downloads/Dokumente/Produkte/6_Software/deconz-cpp-doc/da/d4d/namespacedeCONZ.html
	ZclNoData = 0x00, Zcl8BitData = 0x08, Zcl16BitData = 0x09, Zcl24BitData = 0x0a,
  	Zcl32BitData = 0x0b, Zcl40BitData = 0x0c, Zcl48BitData = 0x0d, Zcl56BitData = 0x0e,
  	Zcl64BitData = 0x0f, ZclBoolean = 0x10, Zcl8BitBitMap = 0x18, Zcl16BitBitMap = 0x19,
  	Zcl24BitBitMap = 0x1a, Zcl32BitBitMap = 0x1b, Zcl40BitBitMap = 0x1c, Zcl48BitBitMap = 0x1d,
  	Zcl56BitBitMap = 0x1e, Zcl64BitBitMap = 0x1f, Zcl8BitUint = 0x20, Zcl16BitUint = 0x21,
  	Zcl24BitUint = 0x22, Zcl32BitUint = 0x23, Zcl40BitUint = 0x24, Zcl48BitUint = 0x25,
  	Zcl56BitUint = 0x26, Zcl64BitUint = 0x27, Zcl8BitInt = 0x28, Zcl16BitInt = 0x29,
  	Zcl24BitInt = 0x2a, Zcl32BitInt = 0x2b, Zcl40BitInt = 0x2c, Zcl48BitInt = 0x2d,
  	Zcl56BitInt = 0x2e, Zcl64BitInt = 0x2f, Zcl8BitEnum = 0x30, Zcl16BitEnum = 0x31,
  	ZclOctedString = 0x41, ZclCharacterString = 0x42, ZclLongOctedString = 0x43, ZclLongCharacterString = 0x44,
  	ZclTimeOfDay = 0xe0, ZclDate = 0xe1, ZclUtcTime = 0xe2, ZclClusterId = 0xe8,
  	ZclAttributeId = 0xe9, ZclBACNetOId = 0xea, ZclIeeeAddress = 0xf0, Zcl128BitSecurityKey = 0xf1 

	'''
	if AttType == "0010" : 		# Boolean
		return Attribute
	elif AttType == "0020" : 	# Uint8
		return Attribute
#	elif AttType == "0023" :	# 32BitUint
	elif AttType == "0039" : 	# Xiaomi Float
		return str(struct.unpack('f',struct.pack('i',int(Attribute,16)))[0])
	elif AttType == "0042" : 	# CharacterString
		return Attribute

	Domoticz.Log("ReadCluster - decodeAttribute Type = " + AttType + " not yet decoded" )


def ReadCluster(self, Devices, MsgData):


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

	Domoticz.Log("ReadCluster - " +MsgClusterId +"  Saddr : " + str(MsgSrcAddr) + " SrcEp : " + MsgSrcEp + " AttrID : " + MsgAttrID + " AttType : " + MsgAttType + " AttSize : " +MsgAttSize +" Attribute : " + str(MsgClusterData) )

		
	if   MsgClusterId=="0000" : Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0006" : Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0008" : Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0012" : Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="000c" : Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0101" : Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0400" : Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0402" : Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0403" : Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0405" : Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0406" : Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0702":  Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	elif MsgClusterId=="0b04" : Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData )
	else :
		Domoticz.Error("ReadCluster - Error/unknow Cluster Message : " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
		Domoticz.Error("                                 MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
		Domoticz.Error("                                 MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )


def Cluster0702( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Smart Energy Metering
	if MsgAttrID == "0000" : # Summation
		bytelen = len(MsgClusterData)
		Domoticz.Log("ReadCluster 0702 - Attribute 0x0000 -MsgClusterData = " + str(MsgClusterData) + " MsgClusterData len = " +str(bytelen) )

	elif MsgAttrID == "1024" : # Instant Measurement 0x0400
		bytelen = len(MsgClusterData)
		Domoticz.Log("ReadCluster 0702 - Attribute 0x0400 - MsgClusterData = " + str(MsgClusterData) + " MsgClusterData len = " +str(bytelen) )
	else :
		Domoticz.Log("ReadCluster - 0x0702 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )
		Domoticz.Log("ReadCluster - 0x0702 - NOT IMPLEMENTED YET - MsgAttType = " +str(MsgAttType) )
		Domoticz.Log("ReadCluster - 0x0702 - NOT IMPLEMENTED YET - MsgAttSize = " +str(MsgAttSize) )


def Cluster0b04( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Electrical Measurement Cluster

	Domoticz.Log("ReadCluster - ClusterID=0b04 - NOT IMPLEMENTED YET - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )


def Cluster000c( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Magic Cube Xiaomi rotation and Power Meter

	Domoticz.Debug("ReadCluster - ClusterID=000C - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) + " len = " +str(len(MsgClusterData)))
	if MsgAttrID=="0055" :
		# Are we receiving Power
		EPforPower = z_tools.getEPforClusterType( self, MsgSrcAddr, "Power" ) 
		EPforMeter = z_tools.getEPforClusterType( self, MsgSrcAddr, "Meter" ) 
		if len(EPforPower) == len(EPforMeter) == 0 :
			Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube angle: " + str(struct.unpack('f',struct.pack('I',int(MsgClusterData,16)))[0])  )
			# will need to investigate to see if this should trigger an update or not.
			# Probably the right think would be to detect clock and anti-clock rotation. 
			# Add a Selector anti-clock on the Switch seector

		else : # We have several EPs in Power/Meter
			Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " +str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0]))
			Domoticz.Debug("ReadCluster - ClusterId=000c - List of Power/Meter EPs" +str( EPforPower ) + str(EPforMeter) )
			for ep in EPforPower + EPforMeter:
				if ep == MsgSrcEp :
					Domoticz.Debug("ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0]))
					self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=str(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0])
					z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(round(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0],1)))
					break      # We just need to send once

	elif MsgAttrID=="ff05" : # Rotation - horinzontal
		Domoticz.Debug("ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) )
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")

	else :
		Domoticz.Log("ReadCluster - ClusterID=000c - unknown message - SAddr = " + str(MsgSrcAddr) + " EP = " + str( MsgSrcEp) + " MsgAttrID = " + str(MsgAttrID) + " Value = "+ str(MsgClusterData) )


def Cluster0008( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# LevelControl cluster

	Domoticz.Debug("ReadCluster - ClusterId=0008 - Level Control : " + str(MsgClusterData) )
	z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
	return

def Cluster0006( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Cluster On/Off

	if MsgAttrID=="0000" or MsgAttrID=="8000":
		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster - ClusterId=0006 - reception General: On/Off : " + str(MsgClusterData) )

	elif MsgAttrID == "f000" and MsgAttType == "0023" and MsgAttSize == "0004" :
		Domoticz.Debug("ReadCluster - Feedback from device " + str(MsgSrcAddr) + "/" + MsgSrcEp + " MsgClusterData: " + MsgClusterData )
	else :
		Domoticz.Error("ReadCluster - ClusterId=0006 - reception heartbeat - Message attribut inconnu : " + MsgAttrID + " / " + MsgData)
	return

def Cluster0101( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Door Lock Cluster

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


def Cluster0405( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Measurement Umidity Cluster

	z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
	self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
	Domoticz.Debug("ReadCluster - ClusterId=0405 - reception hum : " + str(int(MsgClusterData,16)/100) )


def Cluster0402( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Measurement Cluster

	if MsgClusterData != "":
		if MsgClusterData[0] == "f" :  # cas temperature negative
			MsgClusterData=-(int(MsgClusterData,16)^int("FFFF",16))
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
			Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )
		else:
			MsgClusterData=int(MsgClusterData,16)
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
			Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )
	else : 
		Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")


def Cluster0403( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# (Measurement: Pression atmospherique)

	if MsgAttType=="0028":
		#z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgClusterData,8))
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : NOT DOMOTICZ UPDATE !!!!" + str(MsgClusterData) )
			
	if MsgAttType=="0029" and MsgAttrID=="0000":
		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
		Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16),1)))
			
	if MsgAttType=="0029" and MsgAttrID=="0010":
		z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/10,1))
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/10,1)
		Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16)/10,1)))


def Cluster0406( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# (Measurement: Occupancy Sensing)

	Domoticz.Debug("ReadCluster - ClusterId=0406 - reception Occupancy Sensor : " + str(MsgClusterData) )
	z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
	self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData

def Cluster0400( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# (Measurement: LUX)

	Domoticz.Debug("ReadCluster - ClusterId=0400 - reception LUX Sensor : " + str(int(MsgClusterData,16)) )
	z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(int(MsgClusterData,16) ))
	self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=int(MsgClusterData,16)




def Cluster0012( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# Magic Cube Xiaomi
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

	self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
	z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
	Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(MsgClusterData) )
	Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(cube_decode(MsgClusterData)) )



def Cluster0000( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData ) :
	# General Basic Cluster

	# It might be good to make sure that we are on a Xiaomi device - A priori : 0x115f
	if MsgAttrID=="ff01" and self.ListOfDevices[MsgSrcAddr]['Status']=="inDB" :  # xiaomi battery lvl
		Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " ClusterData : " + str(MsgClusterData) )
		# Taging: https://github.com/dresden-elektronik/deconz-rest-plugin/issues/42#issuecomment-370152404
		# 0x0624 might be the LQI indicator and 0x0521 the RSSI dB

		sBatteryLvl = retreive4Tag( "0121", MsgClusterData )
		sTemp2	    = retreive4Tag( "0328", MsgClusterData )   # Device Temperature
		sTemp	    = retreive4Tag( "6429", MsgClusterData )
		sOnOff	    = retreive4Tag( "6410", MsgClusterData )
		sHumid	    = retreive4Tag( "6521", MsgClusterData )
		sHumid2	    = retreive4Tag( "6529", MsgClusterData )
		sPress	    = retreive8Tag( "662b", MsgClusterData )

		if sBatteryLvl != '' and self.ListOfDevices[MsgSrcAddr]['MacCapa'] != '8e' :	# Battery Level makes sense for non main powered devices
			BatteryLvl = '%s%s' % (str(sBatteryLvl[2:4]),str(sBatteryLvl[0:2])) 
			ValueBattery=round(int(BatteryLvl,16)/10/3.3)
			Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Battery : " + str(ValueBattery) )
			self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
		if sTemp != '' :
			Temp = '%s%s' % (str(sTemp[2:4]),str(sTemp[0:2])) 
			ValueTemp=round(int(Temp,16)/100,1)
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0402']=ValueTemp
			Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Temperature : " + str(ValueTemp) )
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)
#		if sTemp2 != '' :
#			Temp2 = '%s%s' % (str(sTemp2[2:4]),str(sTemp2[0:2])) 
#			ValueTemp2=round(int(Temp2,16)/100,1)
#			Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " Device Temperature : " + str(ValueTemp2) )
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
			Domoticz.Debug("ReadCluster - 0000/ff01 Saddr : " + str(MsgSrcAddr) + " On/Off : " + str(sOnOff) )
			z_domoticz.MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006",sOnOff)
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]['0006']=sOnOff


	elif MsgAttrID=="0005" :  # Model info
		try : 
			MType=binascii.unhexlify(MsgClusterData).decode('utf-8')					# Convert the model name to ASCII
			Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device : " + MType)
			self.ListOfDevices[MsgSrcAddr]['Model']=MType							   # Set the model name in database
			if z_var.storeDiscoveryFrames == 1 and MsgSrcAddr in self.DiscoveryDevices :
				self.DiscoveryDevices[MsgSrcAddr]['Model']=MType

			if MType in self.DeviceConf :												# If the model exist in DeviceConf.txt
				for Ep in self.DeviceConf[MType]['Ep'] :								# For each Ep in DeviceConf.txt
					if Ep not in self.ListOfDevices[MsgSrcAddr]['Ep'] :					# If this EP doesn't exist in database
						self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]={}						# create it.
					for cluster in self.DeviceConf[MType]['Ep'][Ep] :					# For each cluster discribe in DeviceConf.txt
						if cluster not in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep] :	# If this cluster doesn't exist in database
							self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}		# create it.
					if 'Type' in self.DeviceConf[MType]['Ep'][Ep] :						# If type exist at EP level : copy it
						self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]['Type']=self.DeviceConf[MType]['Ep'][Ep]['Type']
				if 'Type' in self.DeviceConf[MType] :									# If type exist at top level : copy it
					self.ListOfDevices[MsgSrcAddr]['Type']=self.DeviceConf[MType]['Type']
		except:
			Domoticz.Error("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - Model info Xiaomi : " +  MsgSrcAddr)
			return
	elif MsgAttrID == "0000" : # ZCL Version
		Domoticz.Debug("ReadCluster - 0x0000 - ZCL Version : " +str(MsgClusterData) )
	elif MsgAttrID == "0003" : # Hardware version
		Domoticz.Debug("ReadCluster - 0x0000 - Hardware version : " +str(MsgClusterData) )
	elif MsgAttrID == "0004" : # Manufacturer
		Domoticz.Debug("ReadCluster - 0x0000 - Manufacturer : " +str(MsgClusterData) )
	elif MsgAttrID == "0007" : # Power Source
		Domoticz.Debug("ReadCluster - 0x0000 - Power Source : " +str(MsgClusterData) )
	elif MsgAttrID == "0016" : # Battery
		Domoticz.Debug("ReadCluster - 0x0000 - Battery : " +str(MsgClusterData) )
	else :
		Domoticz.Debug("ReadCluster 0x0000 - Message attribut inconnu : " + MsgData)
	
