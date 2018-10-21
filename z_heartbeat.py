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

def processKnownDevices( self, NWKID ) :

	if ( int( self.ListOfDevices[NWKID]['Heartbeat']) == 3 )  :
		if self.ListOfDevices[NWKID]['Model'] == 'plug.Salus' or self.ListOfDevices[NWKID]['Model'] == 'plug.legrand.netamo':
			# A faire de façon plus ellegante en recupérant les Clusters disponibles
			z_output.enableReporting( self, NWKID, "0006", "0000" )
			z_output.enableReporting( self, NWKID, "0702", "0000" )
			z_output.enableReporting( self, NWKID, "0702", "0400" )

	# Check if Node Descriptor was run ( this could not be the case on early version)
	if ( int( self.ListOfDevices[NWKID]['Heartbeat']) == 12 )  :
		if not self.ListOfDevices[NWKID].get('PowerSource') :	# Looks like PowerSource is not available, let's request a Node Descriptor
			z_output.sendZigateCmd("0042", str(NWKID), 2 )	# Request a Node Descriptor


	if  self.ListOfDevices[NWKID].get('PowerSource') :		# Let's check first that the field exist, if not it will be requested at Heartbeat == 12 (see above)
		if self.ListOfDevices[NWKID]['PowerSource'] == 'Main' :	#  Only for device receiving req on idle

			for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
				# Let's request an update of LvlControl for all Devices which are ClusterType LvlControl Every 5' ( 30 * onHearbeat period ( 10s ) )
				if ( int( self.ListOfDevices[NWKID]['Heartbeat']) % 30 ) == 0 or ( self.ListOfDevices[NWKID]['Heartbeat'] == "6" ):
					if self.ListOfDevices[NWKID]['Ep'][tmpEp].get('ClusterType') :
						if 'LvlControl' in (self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']).values():
							Domoticz.Debug("Request a Read attribute for LvlControl " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
							z_output.ReadAttributeRequest_0008(self, NWKID )
							break	# We break as we are sending only once!
					else : 
						if 'LvlControl' in (self.ListOfDevices[NWKID]['ClusterType']).values():
							Domoticz.Debug("Request a Read attribute for LvlControl " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
							z_output.ReadAttributeRequest_0008(self, NWKID )
							break	# We break as we are sending only once!

				# Let's request Power and Meter information for 0x000c Cluster and 0702 for Salus status every 15' ( 90 * onHearbeat period ( 10s ) )
				if ( int( self.ListOfDevices[NWKID]['Heartbeat']) % 90 ) == 0 or ( self.ListOfDevices[NWKID]['Heartbeat'] == "6" ) :
					if self.ListOfDevices[NWKID]['Ep'][tmpEp].get('ClusterType') :
						if 'PowerMeter' in (self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']).values() or  'Meter' in (self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']).values():
							if self.ListOfDevices[NWKID]['Model']  == 'lumi.plug' :
								Domoticz.Debug("Request a Read attribute for Power and Meter " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
								z_output.ReadAttributeRequest_000C(self, NWKID)   # Xiaomi
								break	# We break as we are sending only once!
							elif self.ListOfDevices[NWKID]['Model'] == 'plug.Salus' or self.ListOfDevices[NWKID]['Model'] == 'plug.legrand.netamo' :
								Domoticz.Log("Request a Read attribute for Power and Meter " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
								z_output.ReadAttributeRequest_0702(self, NWKID)   # Salus ; for now , but we should avoid making in all cases.
								break	# We break as we are sending only once!
					else : 
						if 'PowerMeter' in (self.ListOfDevices[NWKID]['ClusterType']).values()  or 'Meter' in (self.ListOfDevices[NWKID]['ClusterType']).values():
							if self.ListOfDevices[NWKID]['Model']  == 'lumi.plug' :
								Domoticz.Debug("Request a Read attribute for Power and Meter " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
								z_output.ReadAttributeRequest_000C(self, NWKID)   # Xiaomi
								break	# We break as we are sending only once!
							elif self.ListOfDevices[NWKID]['Model'] == 'plug.Salus' :
								Domoticz.Log("Request a Read attribute for Power and Meter " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
								z_output.ReadAttributeRequest_0702(self, NWKID)   # Salus ; for now , but we should avoid making in all cases.
								break	# We break as we are sending only once!

				# Request On/Off status
				if ( int( self.ListOfDevices[NWKID]['Heartbeat']) % 30 ) == 0 or ( self.ListOfDevices[NWKID]['Heartbeat'] == "6" ) :
					if self.ListOfDevices[NWKID]['Ep'][tmpEp].get('ClusterType') :
						if 'Plug' in (self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']).values() or  'Switch' in (self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']).values():
							if self.ListOfDevices[NWKID]['Model']  == 'lumi.plug' :
								Domoticz.Debug("Request a Read attribute for OnOff status " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
								z_output.ReadAttributeRequest_0006(self, NWKID)   
								break	# We break as we are sending only once!
							elif self.ListOfDevices[NWKID]['Model'] == 'plug.Salus' :
								Domoticz.Log("Request a Read attribute for OnOff status " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
								z_output.ReadAttributeRequest_0006(self, NWKID)   
								break	# We break as we are sending only once!
					else : 
						if 'Plug' in (self.ListOfDevices[NWKID]['ClusterType']).values() or 'Switch' in (self.ListOfDevices[NWKID]['ClusterType']).values() :
							Domoticz.Log("Request a Read attribute for OnOff status " + str(NWKID) + " heartbeat = " + str( self.ListOfDevices[NWKID]['Heartbeat']) )
							z_output.ReadAttributeRequest_0006(self, NWKID)   



	
def processNotinDBDevices( self, Devices, NWKID , status , RIA ) :
	# Request EP list
	if status=="004d" and self.ListOfDevices[NWKID]['Heartbeat']=="1":
		Domoticz.Log("Creation process for " + str(NWKID) + " Info: " + str(self.ListOfDevices[NWKID]) )
		# We should check if the device has not been already created via IEEE
		if z_tools.IEEEExist( self, self.ListOfDevices[NWKID]['IEEE'] ) == False :
			Domoticz.Log("onHeartbeat - new device discovered request Node Descriptor for : " +str(NWKID) )
			z_output.sendZigateCmd("0042", str(NWKID))	# Request a Node Descriptor
			self.ListOfDevices[NWKID]['Status']="0042"
			self.ListOfDevices[NWKID]['Heartbeat']="0"
			z_output.ReadAttributeRequest_0000(self, NWKID ) # Basic Cluster readAttribute Request
		else :
			for dup in self.ListOfDevices :
				if self.ListOfDevices[NWKID]['IEEE'] == self.ListOfDevices[dup]['IEEE'] and self.ListOfDevices[dup]['Status'] == "inDB":
					Domoticz.Error("onHearbeat - Device : " + str(NWKID) + "already known under IEEE: " +str(self.ListOfDevices[NWKID]['IEEE'] ) 
										+ " Duplicate of " + str(dup) )
					self.ListOfDevices[NWKID]['Status']="DUP"
					self.ListOfDevices[NWKID]['Heartbeat']="0"
					self.ListOfDevices[NWKID]['RIA']="99"
					break

	if status=="8042" and self.ListOfDevices[NWKID]['Heartbeat']=="1":	# Status is set by Decode8042
			Domoticz.Log("onHeartbeat - new device discovered request EP list with 0x0045 and lets wait for 0x8045: " + NWKID)
			z_output.sendZigateCmd("0045", str(NWKID))	# We use NWKID as we are in the discovery process (no reason to use DomoID at that time / Device not yet created
			self.ListOfDevices[NWKID]['Status']="0045"
			self.ListOfDevices[NWKID]['Heartbeat']="0"

	if status=="8045" and self.ListOfDevices[NWKID]['Heartbeat']=="1":	# Status is set by Decode8045
		Domoticz.Log("onHeartbeat - new device discovered 0x8045 received " + NWKID)
		for cle in self.ListOfDevices[NWKID]['Ep']:
			Domoticz.Log("onHeartbeat - new device discovered request Simple Descriptor 0x0043 and wait for 0x8043 for EP " + cle + ", of : " + NWKID)
			z_output.sendZigateCmd("0043", str(NWKID)+str(cle), 2 )	# We use NWKID 
													
		self.ListOfDevices[NWKID]['Status']="0043"
		self.ListOfDevices[NWKID]['Heartbeat']="0"

	if status=="0041" and self.ListOfDevices[NWKID]['Heartbeat']=="1":	# It has been requested tto issue a 0x0041 request 
		Domoticz.Log("processNotinDBDevices - request IEEE for " +str(str(NWKID)) )
		z_output.sendZigateCmd("0041", str(NWKID)+str(NWKID)+"00" )   	
		self.ListOfDevices[NWKID]['Status']="8041"
		self.ListOfDevices[NWKID]['Heartbeat']="0"

	# Timeout Management
	# We should wonder if we want to go in an infinite loop.
	if status=="004d" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered but no processing done, let's Timeout: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"

	if status=="0042" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x0042 not received in time: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="0045"		# Let's continue in 0x0045 , those informations are not a must

	if status=="8042" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8042 not received in time: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="0045"		# Let's continue in 0x0045 , those informations are not a must

	if status=="0045" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8045 not received in time: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="004d"

	if status=="8045" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8045 not received in time: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="004d"

	if status=="0043" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8043 not received in time: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="8045"

	if status=="8041" and self.ListOfDevices[NWKID]['Heartbeat']>="9":
		Domoticz.Debug("onHeartbeat - new device discovered 0x8043 not received in time: " + NWKID)
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="0041"

	# What RIA stand for ??????? (see line 228)
	if ( status=="8043" or status=="8041" ) and self.ListOfDevices[NWKID]['Heartbeat']>="9" and self.ListOfDevices[NWKID]['RIA']>="10":
		self.ListOfDevices[NWKID]['Heartbeat']="0"
		self.ListOfDevices[NWKID]['Status']="UNKNOW"
		Domoticz.Log("processNotinDB - not able to find response from " +str(NWKID) + " stop process at " +str(status) )

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
	# ProfileID =	  >> SEP: Smart Energy Profile
	# There is too ZBA, ZTS, ZRS, ZHC but I haven't find information for them
	
	#ZigBee HA contains (nearly?) everything in ZigBee Light Link

	if ( z_var.storeDiscoveryFrames == 0 and status != "UNKNOW" and status != "DUP")  or (  z_var.storeDiscoveryFrames == 1 and status == "8043" ) :
		if self.ListOfDevices[NWKID]['MacCapa']=="8e" :  # Device sur secteur
			if self.ListOfDevices[NWKID]['ProfileID']=="c05e" : # ZLL: ZigBee Light Link
				# telecommande Tradfi 30338849.Tradfri
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0830" :
					self.ListOfDevices[NWKID]['Model']="Command.30338849.Tradfri"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01':{'0000','0001','0009','0b05','1000'}}
				# ampoule Tradfri LED1624G9
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0200" :
					self.ListOfDevices[NWKID]['Model']="Ampoule.LED1624G9.Tradfri"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01':{'0006','0008','0300'}}
				# ampoule Tradfi LED1545G12.Tradfri
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0220" :
					self.ListOfDevices[NWKID]['Model']="Ampoule.LED1545G12.Tradfri"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01': {'0006', '0008', '0300'}}
				# ampoule Tradfri LED1622G12.Tradfri ou phillips hue white
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0100" :
					self.ListOfDevices[NWKID]['Model']="Ampoule.LED1622G12.Tradfri"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01': {'0006', '0008'}}
				# Not see yet
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0210" :
					pass								
				# plug osram
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0010" :  
					self.ListOfDevices[NWKID]['Model']="plug.Osram"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'03': {'0006'}}

			if self.ListOfDevices[NWKID]['ProfileID']=="0104" :  # profile home automation
				# plug salus
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0051" :
					self.ListOfDevices[NWKID]['Model']="plug.Salus"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'09': {'0006'}}
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0100" :
					# ampoule Tradfi
					if '1000' in self.ListOfDevices[NWKID]['Ep'].get('01',''): #1000 is ZLL: Commissioning, only for bulb
						self.ListOfDevices[NWKID]['Model']="Ampoule.LED1622G12.Tradfri"
						if self.ListOfDevices[NWKID]['Ep']=={} :
							self.ListOfDevices[NWKID]['Ep']={'01': {'0006', '0008'}}
					#Legrand-netamo switch
					else:
						self.ListOfDevices[NWKID]['Model']="switch.legrand.netamo"
						if self.ListOfDevices[NWKID]['Ep']=={} :
							self.ListOfDevices[NWKID]['Ep']={'01': {'0006', '0008'}}									 
				# shutter profalux
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0200" :
					self.ListOfDevices[NWKID]['Model']="shutter.Profalux"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01':{'0006','0008'}}
				# Plug legrand-netamo
				if self.ListOfDevices[NWKID]['ZDeviceID']=="010a" :
					self.ListOfDevices[NWKID]['Model']="plug.legrand.netamo"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01':{'0000','0003','0004','0006','0005','fc01'}}

			if self.ListOfDevices[NWKID]['ProfileID']=="a1e0" :  # profile unknow : phillips hue
				if self.ListOfDevices[NWKID]['ZDeviceID']=="0061" : 
					self.ListOfDevices[NWKID]['Model']="Ampoule.phillips.hue"
					if self.ListOfDevices[NWKID]['Ep']=={} :
						self.ListOfDevices[NWKID]['Ep']={'01': {'0006', '0008'}}
	
		# At that stage , we should have all information to create the Device Status 8043 is set in Decode8043 when receiving

		if (RIA>=10 or self.ListOfDevices[NWKID]['Model']!= {} ) :
			Domoticz.Log("processNotinDBDevices - final step for creation of : " +str(NWKID) + " => " +str(self.ListOfDevices[NWKID]) )
			#creer le device ds domoticz en se basant sur les clusterID (case RIA>=10, see z_input.py in readcluster ) ou le Model si il est connu
			IsCreated=False
			x=0
			nbrdevices=0
			for x in Devices:
				if self.ListOfDevices[NWKID].get('IEEE') :
					if Devices[x].DeviceID == str(self.ListOfDevices[NWKID]['IEEE']) :
						IsCreated = True
						Domoticz.Log("Heartbeat - Devices already exist. Unit=" + str(x) + " versus " + str(self.ListOfDevices[NWKID]) )

			if IsCreated == False:
				Domoticz.Log("onHeartbeat - creating device id : " + str(NWKID) + " with : " + str(self.ListOfDevices[NWKID]) )
				z_domoticz.CreateDomoDevice(self, Devices, NWKID)

		#end (RIA>=10 or self.ListOfDevices[NWKID]['Model']!= {})
	#end status != "UNKNOW"	
	

def processListOfDevices( self , Devices ) :

	for NWKID in list(self.ListOfDevices) :
		#ok buged device , need to avoid it, just delete it after the making for the moment
		if len(self.ListOfDevices[NWKID]) == 0:
			Domoticz.Debug("Bad devices detected (empty one), remove it, adr :" + str(NWKID))
			del self.ListOfDevices[NWKID]
			continue
			
		status=self.ListOfDevices[NWKID]['Status']
		RIA=int(self.ListOfDevices[NWKID]['RIA'])
		self.ListOfDevices[NWKID]['Heartbeat']=str(int(self.ListOfDevices[NWKID]['Heartbeat'])+1)

		########## Known Devices 
		if status == "inDB" : 
			processKnownDevices( self , NWKID )

		if status == "Left" :
			# Device has sent a 0x8048 message annoucing its departure (Leave)
			# Most likely we should receive a 0x004d, where the device come back with a new short address
			Domoticz.Log("processListOfDevices - Device : " +str(NWKID) + " is in Status = 'Left' for " +str(self.ListOfDevices[NWKID]['Heartbeat']) + "HB" )

		elif status != "inDB" :
			# Creation process
			processNotinDBDevices( self , Devices, NWKID, status , RIA )

	#end for key in ListOfDevices

	return True

