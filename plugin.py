#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="2.4.0" wikilink="http://www.domoticz.com/wiki/Zigate" externallink="https://www.zigate.fr/">
	<params>
		<param field="Mode1" label="Model" width="75px">
			<options>
				<option label="USB" value="USB" default="true" />
				<option label="Wifi" value="Wifi"/>
			</options>
		</param>
		<param field="Address" label="IP" width="150px" required="true" default="0.0.0.0"/>
		<param field="Port" label="Port" width="150px" required="true" default="9999"/>
		<param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0"/>
		<param field="Mode5" label="Channel " width="50px" required="true" default="11" />
		<param field="Mode2" label="Permit join time on start (0 disable join; 1-254 up to 254 sec ; 255 enable join all the time) " width="75px" required="true" default="254" />
		<param field="Mode3" label="Erase Persistent Data ( !!! full devices setup need !!! ) " width="75px">
			<options>
				<option label="True" value="True"/>
				<option label="False" value="False" default="true" />
			</options>
		</param>
		<param field="Mode6" label="Debug" width="150px">
			<options>
				<option label="None" value="0"  default="true" />
				<option label="Python Only" value="2"/>
				<option label="Basic Debugging" value="62"/>
				<option label="Basic+Messages" value="126"/>
				<option label="Connections Only" value="16"/>
				<option label="Connections+Python" value="18"/>
				<option label="Connections+Queue" value="144"/>
				<option label="All" value="-1"/>
			</options>
		</param>
	</params>
</plugin>
"""

import Domoticz
import binascii
import time
import struct
import json

import z_var          # Global variables
import z_tools
import z_output
import z_input
import z_heartbeat
import z_database
import z_domoticz
import z_command


class BasePlugin:
	enabled = False

	def __init__(self):
		self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
		self.HBcount=0
		return

	def onStart(self):
		Domoticz.Log("onStart called")

		if Parameters["Mode6"] != "0":
			Domoticz.Debugging(int(Parameters["Mode6"]))
			DumpConfigToLog()
		if Parameters["Mode1"] == "USB":
			z_var.transport = "USB"
			z_var.ZigateConn = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=Parameters["SerialPort"], Baud=115200)
			z_var.ZigateConn.Connect()
		if Parameters["Mode1"] == "Wifi":
			z_var.transport = "Wifi"
			z_var.ZigateConn = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=Parameters["Address"], Port=Parameters["Port"])
			z_var.ZigateConn.Connect()
		
		# CLD CLD
		# Import PluginConf.txt
		tmpPluginConf=""
		with open(Parameters["HomeFolder"]+"PluginConf.txt", 'r') as myPluginConfFile:
			tmpPluginConf+=myPluginConfFile.read().replace('\n', '')
		myPluginConfFile.close()
		Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))
		self.PluginConf=eval(tmpPluginConf)
		z_var.CrcCheck = 1
		if  self.PluginConf['CrcCheck'] == "False" or self.PluginConf['CrcCheck'] == "Off" :
			z_var.CrcCheck = 0
		
		z_var.ReqRcv=bytearray()

		for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
			ID = Devices[x].DeviceID
			try:
				self.ListOfDevices[ID]=eval(Devices[x].Options['Zigate'])
			except: 
				Domoticz.Error("Error loading Device " +str(Devices[x]) + " not loaded int Zigate Plugin!" )
			else :
				self.ListOfDevices[ID]={}
				Domoticz.Log("Device : [" + str(x) + "] ID = " + ID + " Options['Zigate'] = " + Devices[x].Options['Zigate'] + " loaded into self.ListOfDevices")

		#Import DeviceConf.txt
		tmpread=""
		with open(Parameters["HomeFolder"]+"DeviceConf.txt", 'r') as myfile:
			tmpread+=myfile.read().replace('\n', '')
		myfile.close()
		Domoticz.Debug("DeviceConf.txt = " + str(tmpread))
		self.DeviceConf=eval(tmpread)
		#Import DeviceList.txt
		with open(Parameters["HomeFolder"]+"DeviceList.txt", 'r') as myfile2:
			Domoticz.Debug("DeviceList.txt open ")
			for line in myfile2:
				(key, val) = line.split(":",1)
				key = key.replace(" ","")
				key = key.replace("'","")
				z_tools.CheckDeviceList(self, key, val)
		return


	def onStop(self):
		z_var.ZigateConn.Disconnect()
		z_database.WriteDeviceList(self, Parameters["HomeFolder"], 0)
		Domoticz.Log("onStop called")

	def onConnect(self, Connection, Status, Description):
		Domoticz.Log("onConnect called")
		global isConnected

		if (Status == 0):
			isConnected = True
			Domoticz.Log("Connected successfully")
			if Parameters["Mode3"] == "True":
			################### ZiGate - ErasePD ##################
				z_output.sendZigateCmd("0012", "")
			z_output.ZigateConf(Parameters["Mode5"], Parameters["Mode2"])
		else:
			Domoticz.Error("Failed to connect ("+str(Status)+")")
			Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
		return True

	def onMessage(self, Connection, Data):
		Domoticz.Debug("onMessage called on Connection " +str(Connection) + " Data = '" +str(Data) + "'")
		### CLD

		FrameIsKo = 0					

		# Version 3 - Binary reading to avoid mixing end of Frame - Thanks to CLDFR
		z_var.ReqRcv += Data				# Add the incoming data
		Domoticz.Debug("onMessage incoming data : '" + str(binascii.hexlify(z_var.ReqRcv).decode('utf-8'))+ "'" )

		# Zigate Frames start with 0x01 and finished with 0x03	
		# It happens that we get some 
		while 1 :					# Loop until we have 0x03
			Zero1=-1
			Zero3=-1
			idx = 0
			for val in z_var.ReqRcv[0:len(z_var.ReqRcv)] :
				if Zero1 == - 1 and Zero3  == -1 and val == 1 :	# Do we get a 0x01
					Zero1 = idx		# we have identify the Frame start

				if Zero1 != -1 and val == 3 :	# If we have already started a Frame and do we get a 0x03
					Zero3 = idx + 1
					break			# If we got 0x03, let process the Frame
				idx += 1

			if Zero3 == -1 :			# No 0x03 in the Buffer, let's breat and wait to get more data
				return

			Domoticz.Debug("onMessage Frame : Zero1=" + str(Zero1) + " Zero3=" + str(Zero3) )

			# CLD CLD
			if Zero1 != 0 :
				Domoticz.Log("onMessage : we have probably lost some datas, zero1 = " + str(Zero1) )

			# uncode the frame
			BinMsg=bytearray()
			iterReqRcv = iter (z_var.ReqRcv[Zero1:Zero3])

			for iByte in iterReqRcv :			# for each received byte
				if iByte == 2 :				# Coded flag ?
					iByte = next(iterReqRcv) ^ 16	# then uncode the next value
				BinMsg.append(iByte)			# copy

			z_var.ReqRcv = z_var.ReqRcv[Zero3:]                 # What is after 0x03 has to be reworked.

                        # Check length
			Zero1, MsgType, Length, ReceivedChecksum = struct.unpack ('>BHHB', BinMsg[0:6])
			### Domoticz.Debug("onMessage Frame CLD : " + str(Zero1) + " " + str(MsgType) + " " + str(Length) )
			ComputedLength = Length + 7
			ReceveidLength = len(BinMsg)
			Domoticz.Debug("onMessage Frame length : " + str(ComputedLength) + " " + str(ReceveidLength) ) # For testing purpose
			if ComputedLength != ReceveidLength :
				FrameIsKo = 1
				Domoticz.Log("onMessage : Frame size is bad, computed = " + str(ComputedLength) + " received = " + str(ReceveidLength) )

			# Compute checksum
			ComputedChecksum = 0
			for idx, val in enumerate(BinMsg[1:-1]) :
				if idx != 4 :				# Jump the checksum itself
					ComputedChecksum ^= val
			Domoticz.Debug("onMessage Frame : ComputedChekcum=" + str(ComputedChecksum) + " ReceivedChecksum=" + str(ReceivedChecksum) ) # For testing purpose
			if ComputedChecksum != ReceivedChecksum and z_var.CrcCheck == 1 :
				FrameIsKo = 1
				Domoticz.Log("onMessage : Frame CRC is bad, computed = " + str(ComputedChecksum) + " received = " + str(ReceivedChecksum) )

			AsciiMsg=binascii.hexlify(BinMsg).decode('utf-8')
			# ZigateDecode(self, AsciiMsg) 		# decode this Frame
			if FrameIsKo == 0 :
				z_input.ZigateRead(self, Devices, AsciiMsg)		# process this frame

		Domoticz.Debug("onMessage Remaining Frame : " + str(binascii.hexlify(z_var.ReqRcv).decode('utf-8') ))

		return

	def onCommand(self, Unit, Command, Level, Color):
		z_command.mgtCommand( self, Devices, Unit, Command, Level, Color )


	def onDisconnect(self, Connection):
		Domoticz.Log("onDisconnect called")

	def onHeartbeat(self):

		#Domoticz.Log("onHeartbeat called" )
		Domoticz.Debug("ListOfDevices : " + str(self.ListOfDevices))

		## Check the Network status every 15' / Only possible if z_var.FirmwareVersion > 3.0d
		if str(z_var.FirmwareVersion) == "030d" :
			if z_var.HeartbeatCount >= 90 :
				Domoticz.Debug("request Network Status")
				z_output.sendZigateCmd("0009","")
				z_var.HeartbeatCount = 0
			else :
				z_var.HeartbeatCount = z_var.HeartbeatCount + 1

		z_heartbeat.processListOfDevices( self , Devices )

		z_domoticz.ResetDevice( self, Devices, "Motion",5)
		z_database.WriteDeviceList(self, Parameters["HomeFolder"], 200)

		if (z_var.ZigateConn.Connected() != True):
			z_var.ZigateConn.Connect()

		return True


global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

def onStop():
	global _plugin
	_plugin.onStop()

def onConnect(Connection, Status, Description):
	global _plugin
	_plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
	global _plugin
	_plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
	global _plugin
	_plugin.onDisconnect(Connection)

def onHeartbeat():
	global _plugin
	_plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
	for x in Parameters:
		if Parameters[x] != "":
			Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
	Domoticz.Debug("Device count: " + str(len(Devices)))
	for x in Devices:
		Domoticz.Debug("Device:		   " + str(x) + " - " + str(Devices[x]))
		Domoticz.Debug("Device ID:	   '" + str(Devices[x].ID) + "'")
		Domoticz.Debug("Device Name:	 '" + Devices[x].Name + "'")
		Domoticz.Debug("Device nValue:	" + str(Devices[x].nValue))
		Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
		Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
		Domoticz.Debug("Device Options: " + str(Devices[x].Options))
	return

