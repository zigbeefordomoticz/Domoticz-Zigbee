#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_heartbeat.py

	Description: Manage all actions done during the onHeartbeat() call

"""

import Domoticz
import binascii
import time
import struct
import json

import z_var
import z_output
import z_tools
import z_domoticz

def processKnownDevices( self, key ) :
	# device id type shutter, let check the shutter status every 5' ( 30 * onHearbeat period ( 10s ) )
	if ( int( self.ListOfDevices[key]['Heartbeat']) % 30 ) == 0 or ( self.ListOfDevices[key]['Heartbeat'] == "2" ):
		if self.ListOfDevices[key]['Model'] == "shutter.Profalux" :
			Domoticz.Log("Request a Read attribute for the shutter " + str(key) + " heartbeat = " + str( self.ListOfDevices[key]['Heartbeat']) )
			z_output.ReadAttributeRequest(self, key,'0000','0008')
#			self.ListOfDevices[key]['Heartbeat']="0"

	# device id type Xiaomi Plug, let check the shutter status every 15' ( 90 * onHearbeat period ( 10s ) )
	if ( int( self.ListOfDevices[key]['Heartbeat']) % 90 ) == 0 or ( self.ListOfDevices[key]['Heartbeat'] == "2" ) :
		if self.ListOfDevices[key]['Model'] == "lumi.plug" :
			Domoticz.Log("Request a Read attribute for the Power Plug " + str(key) )
			z_output.ReadAttributeRequest(self, key,'000C','0055')
#			self.ListOfDevices[key]['Heartbeat']="0"


def processNotinDBDevices( self, Devices, key , status , RIA ) :
	# Request EP list
	if status=="004d" and self.ListOfDevices[key]['Heartbeat']=="1":
		Domoticz.Log("Creation process for " + str(key) + " Info: " + str(self.ListOfDevices[key]) )
		# We should check if the device has not been already created via IEEE
		if z_tools.IEEEExist( self, self.ListOfDevices[key]['IEEE'] ) == False :
			Domoticz.Debug("onHeartbeat - new device discovered request EP list with 0x0045 and lets wait for 0x8045: " + key)
			z_output.sendZigateCmd("0045", str(key))
			self.ListOfDevices[key]['Status']="0045"
			self.ListOfDevices[key]['Heartbeat']="0"
		else :
			for dup in self.ListOfDevices :
				if self.ListOfDevices[key]['IEEE'] == self.ListOfDevices[dup]['IEEE'] and self.ListOfDevices[dup]['Status'] == "inDB":
					Domoticz.Error("onHearbeat - Device : " + str(key) + "already known under IEEE: " +str(self.ListOfDevices[key]['IEEE'] ) + " Duplicate of " + str(dup) )
					self.ListOfDevices[key]['Status']="DUP"
					self.ListOfDevices[key]['Heartbeat']="0"
					self.ListOfDevices[key]['RIA']="99"
					oktocreate=True
					break

	# Request Simple Descriptor for each EP	
	if status=="8045" and self.ListOfDevices[key]['Heartbeat']=="1":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8045 received " + key)
		for cle in self.ListOfDevices[key]['Ep']:
			Domoticz.Debug("onHeartbeat - new device discovered request Simple Descriptor 0x0043 and wait for 0x8043 for EP " + cle + ", of : " + key)
			z_output.sendZigateCmd("0043", str(key)+str(cle))
			
		self.ListOfDevices[key]['Status']="0043"
		self.ListOfDevices[key]['Heartbeat']="0"

	# Timeout Management
	# We should wonder if we want to go in an infinite loop.
	if status=="004d" and self.ListOfDevices[key]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered but no processing done, let's Timeout: " + key)
		self.ListOfDevices[key]['Heartbeat']="0"
	if status=="0045" and self.ListOfDevices[key]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8045 not received in time: " + key)
		self.ListOfDevices[key]['Heartbeat']="0"
		self.ListOfDevices[key]['Status']="004d"
	if status=="8045" and self.ListOfDevices[key]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8045 not received in time: " + key)
		self.ListOfDevices[key]['Heartbeat']="0"
		self.ListOfDevices[key]['Status']="004d"
	if status=="0043" and self.ListOfDevices[key]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8043 not received in time: " + key)
		self.ListOfDevices[key]['Heartbeat']="0"
		self.ListOfDevices[key]['Status']="8045"

	# What RIA stand for ???????
	if status=="8043" and self.ListOfDevices[key]['Heartbeat']>="9" and self.ListOfDevices[key]['RIA']>="10":
		self.ListOfDevices[key]['Heartbeat']="0"
		self.ListOfDevices[key]['Status']="UNKNOW"

	#ZLL
	#Lightning devices
	# ZDeviceID = 0000 >> On/Off light
	# ZDeviceID = 0010 >> on/off light but plug
	# ZDeviceID = 0100 >> Dimable but no color
	# ZDeviceID = 0110 >> Dimable but no color and plug
	# ZDeviceID = 0200 >> Color light or shutter
	# ZDeviceID = 0220 >> Temperature Color change
	# ZDeviceID = 0210 >> Hue/Extended Color change
	#Controllers devices
	# ZDeviceID = 0800 >> Color controler
	# ZDeviceID = 0810 >> Color scene controler
	# ZDeviceID = 0820 >> Non color controler
	# ZDeviceID = 0830 >> Non color scene controler
	# ZDeviceID = 0840 >> Control bridge
	# ZDeviceID = 0850 >> on/off sensor
	
	#ZHA
	#Device
	# ZDeviceID = 0000 >> On/Off switch
	# ZDeviceID = 0001 >> Level control switch
	# ZDeviceID = 0002 >> on/off output
	# ZDeviceID = 0003 >> Level contro output
	# ZDeviceID = 0004 >> Scene selector
	# ZDeviceID = 0005 >> Configuration tool
	# ZDeviceID = 0006 >> Remote control
	# ZDeviceID = 0007 >> Combined interface
	# ZDeviceID = 0008 >> Range extender
	# ZDeviceID = 0009 >> Mains Power Outlet
	# ZDeviceID = 000A >> Door lock
	# ZDeviceID = 000B >> Door lock controler
	# ZDeviceID = 000C >> HSimple sensor
	# ZDeviceID = 000D >> Consumption awarness Device
	# ZDeviceID = 0050 >> Home gateway
	# ZDeviceID = 0051 >> Smart plug
	# ZDeviceID = 0052 >> White goods
	# ZDeviceID = 0053 >> Meter interface
	# ZDeviceID = 0100 >> On/Off light
	# ZDeviceID = 0101 >> Dimable light
	# ZDeviceID = 0102 >> Color dimable light
	# ZDeviceID = 0103 >> on/off light
	# ZDeviceID = 0104 >> Dimmer switch
	# ZDeviceID = 0105 >> Color Dimmer switch
	# ZDeviceID = 0106 >> Light sensor
	# ZDeviceID = 0107 >> Occupancy sensor
	# ZDeviceID = 010a >> Unknow : plug legrand
	# ZDeviceID = 0200 >> Shade
	# ZDeviceID = 0201 >> Shade controler
	# ZDeviceID = 0202 >> Window covering device
	# ZDeviceID = 0203 >> Window Covering controler
	# ZDeviceID = 0300 >> Heating/cooling Unit
	# ZDeviceID = 0301 >> Thermostat
	# ZDeviceID = 0302 >> Temperature sensor
	# ZDeviceID = 0303 >> Pump
	# ZDeviceID = 0304 >> Pump controler
	# ZDeviceID = 0305 >> Pressure sensor
	# ZDeviceID = 0306 >> flow sensor
	# ZDeviceID = 0307 >> Mini split AC
	# ZDeviceID = 0400 >> IAS Control and indicating equipement 
	# ZDeviceID = 0401 >> IAS Ancillary Control Equipement
	# ZDeviceID = 0402 >> IAS zone
	# ZDeviceID = 0403 >> IAS Warning device
	
	# ProfileID = c05e >> ZLL: ZigBee Light Link
	# ProfileID = 0104 >> ZHA : ZigBee Home Automation
	# ProfileID = a1e0 >> Philips Hue ???
	# ProfileID =      >> SEP: Smart Energy Profile
	# There is too ZBA, ZTS, ZRS, ZHC but I haven't find information for them
	
	#ZigBee HA contains (nearly?) everything in ZigBee Light Link
	if status != "UNKNOW" and status != "DUP":
		if self.ListOfDevices[key]['MacCapa']=="8e" :  # Device sur secteur
			if self.ListOfDevices[key]['ProfileID']=="c05e" : # ZLL: ZigBee Light Link
				# telecommande Tradfi 30338849.Tradfri
				if self.ListOfDevices[key]['ZDeviceID']=="0830" :
					self.ListOfDevices[key]['Model']="Command.30338849.Tradfri"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01':{'0000','0001','0009','0b05','1000'}}
				# ampoule Tradfri LED1624G9
				if self.ListOfDevices[key]['ZDeviceID']=="0200" :
					self.ListOfDevices[key]['Model']="Ampoule.LED1624G9.Tradfri"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01':{'0006','0008','0300'}}
				# ampoule Tradfi LED1545G12.Tradfri
				if self.ListOfDevices[key]['ZDeviceID']=="0220" :
					self.ListOfDevices[key]['Model']="Ampoule.LED1545G12.Tradfri"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01': {'0006', '0008', '0300'}}
				# ampoule Tradfri LED1622G12.Tradfri ou phillips hue white
				if self.ListOfDevices[key]['ZDeviceID']=="0100" :
					self.ListOfDevices[key]['Model']="Ampoule.LED1622G12.Tradfri"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01': {'0006', '0008'}}
				# Not see yet
				if self.ListOfDevices[key]['ZDeviceID']=="0210" :
					pass								
				# plug osram
				if self.ListOfDevices[key]['ZDeviceID']=="0010" :  
					self.ListOfDevices[key]['Model']="plug.Osram"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'03': {'0006'}}

			if self.ListOfDevices[key]['ProfileID']=="0104" :  # profile home automation
				# plug salus
				if self.ListOfDevices[key]['ZDeviceID']=="0051" :
					self.ListOfDevices[key]['Model']="plug.Salus"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'09': {'0006'}}
				if self.ListOfDevices[key]['ZDeviceID']=="0100" :
					# ampoule Tradfi
					if '1000' in self.ListOfDevices[key]['Ep'].get('01',''): #1000 is ZLL: Commissioning, only for bulb
						self.ListOfDevices[key]['Model']="Ampoule.LED1622G12.Tradfri"
						if self.ListOfDevices[key]['Ep']=={} :
							self.ListOfDevices[key]['Ep']={'01': {'0006', '0008'}}
					#Legrand-netamo switch
					else:
						self.ListOfDevices[key]['Model']="switch.legrand.netamo"
						if self.ListOfDevices[key]['Ep']=={} :
							self.ListOfDevices[key]['Ep']={'01': {'0006', '0008'}}									 
				# shutter profalux
				if self.ListOfDevices[key]['ZDeviceID']=="0200" :
					self.ListOfDevices[key]['Model']="shutter.Profalux"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01':{'0006','0008'}}
				# Plug legrand-netamo
				if self.ListOfDevices[key]['ZDeviceID']=="010a" :
					self.ListOfDevices[key]['Model']="plug.legrand.netamo"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01':{'0000','0003','0004','0006','0005','fc01'}}

			if self.ListOfDevices[key]['ProfileID']=="a1e0" :  # profile unknow : phillips hue
				if self.ListOfDevices[key]['ZDeviceID']=="0061" : 
					self.ListOfDevices[key]['Model']="Ampoule.phillips.hue"
					if self.ListOfDevices[key]['Ep']=={} :
						self.ListOfDevices[key]['Ep']={'01': {'0006', '0008'}}
	
		# At that stage , we should have all information to create the Device Status 8043 is set in Decode8043 when receiving

		if (RIA>=10 or self.ListOfDevices[key]['Model']!= {}) :
			#creer le device ds domoticz en se basant sur les clusterID ou le Model si il est connu
			IsCreated=False
			#IEEEexist=False
			x=0
			nbrdevices=0
			for x in Devices:
				if Devices[x].DeviceID == str(key) :
					IsCreated = True
					Domoticz.Debug("onHeartbeat - Devices already exist. Unit=" + str(x) + " versus " + str(self.ListOfDevices[key]) )
					
				#Dzigate=eval(DOptions['Zigate'])
				#Domoticz.Debug("HearBeat - Devices[x].Options['Zigate']['IEEE']=" + str(Dzigate['IEEE']))
				#Domoticz.Debug("HearBeat - self.ListOfDevices[key]['IEEE']=" + str(self.ListOfDevices[key]['IEEE']))
				#if Dzigate['IEEE']!='' and self.ListOfDevices[key]['IEEE']!='' :
				#	if Dzigate['IEEE']==self.ListOfDevices[key]['IEEE'] :
				#		IEEEexist = True
				#		Domoticz.Debug("HearBeat - Devices IEEE already exist. Unit=" + str(x))
			if IsCreated == False : #and IEEEexist == False:
				Domoticz.Debug("onHeartbeat - creating device id : " + str(key) + " with : " + str(self.ListOfDevices[key]) )
				z_domoticz.CreateDomoDevice(self, Devices, key)
				
				#Wana more information ?
				# Better to check if the field is not already present, to avoid a command for nothing
				z_output.ReadAttributeRequest(self,key, '0000' , '0004') #Manufacture
				
			#if IsCreated == False and IEEEexist == True :
			#	Domoticz.Debug("HearBeat - updating device id : " + str(key))
			#	UpdateDomoDevice(self, key)

		#end (RIA>=10 or self.ListOfDevices[key]['Model']!= {})
	#end status != "UNKNOW"	
	

def processListOfDevices( self , Devices ) :

	for key in list(self.ListOfDevices) :
		
		#ok buged device , need to avoid it, just delete it after the making for the moment
		if len(self.ListOfDevices[key]) == 0:
			Domoticz.Debug("Bad devices detected (empty one), remove it, adr :" + str(key))
			del self.ListOfDevices[key]
			continue
			
		status=self.ListOfDevices[key]['Status']
		RIA=int(self.ListOfDevices[key]['RIA'])
		self.ListOfDevices[key]['Heartbeat']=str(int(self.ListOfDevices[key]['Heartbeat'])+1)

		########## Known Devices 
		if status == "inDB" : 
			processKnownDevices( self , key )

		########## UnKnown Devices  - Creation process
		if status != "inDB" :
			processNotinDBDevices( self , Devices, key, status , RIA )

	#end for key in ListOfDevices

	return True
