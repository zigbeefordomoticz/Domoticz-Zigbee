#
# Author: zaraki673
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673" version="2.3.5 developement" wikilink="http://www.domoticz.com/wiki/Zigate" externallink="https://www.zigate.fr/">
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

FirmwareVersion = ''
HeartbeatCount = 88     # request a network status 10s after start

class BasePlugin:
	enabled = False

	def __init__(self):
		self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
		self.HBcount=0
		return

	def onStart(self):
		Domoticz.Log("onStart called")
		Domoticz.Log("Development branch")
		global ReqRcv
		global ZigateConn
		if Parameters["Mode6"] != "0":
			Domoticz.Debugging(int(Parameters["Mode6"]))
			DumpConfigToLog()
		if Parameters["Mode1"] == "USB":
			ZigateConn = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=Parameters["SerialPort"], Baud=115200)
			ZigateConn.Connect()
		if Parameters["Mode1"] == "Wifi":
			ZigateConn = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=Parameters["Address"], Port=Parameters["Port"])
			ZigateConn.Connect()
		ReqRcv=bytearray()

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
				CheckDeviceList(self, key, val)
		return


	def onStop(self):
		ZigateConn.Disconnect()
		WriteDeviceList(self, 0)
		Domoticz.Log("onStop called")

	def onConnect(self, Connection, Status, Description):
		Domoticz.Log("onConnect called")
		global isConnected

		if (Status == 0):
			isConnected = True
			Domoticz.Log("Connected successfully")
			if Parameters["Mode3"] == "True":
			################### ZiGate - ErasePD ##################
				sendZigateCmd("0012", "")
			ZigateConf()
		else:
			Domoticz.Error("Failed to connect ("+str(Status)+")")
			Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
		return True

	def onMessage(self, Connection, Data):
		Domoticz.Debug("onMessage called on Connection " +str(Connection) + " Data = '" +str(Data) + "'")
		global ReqRcv

		# Version 3 - Binary reading to avoid mixing end of Frame - Thanks to CLDFR
		ReqRcv += Data				# Add the incoming data
		Domoticz.Debug("onMessage incoming data : '" + str(binascii.hexlify(ReqRcv).decode('utf-8'))+ "'" )

		# Zigate Frames start with 0x01 and finished with 0x03	
		# It happens that we get some 
		while 1 :					# Loop until we have 0x03
			Zero1=-1
			Zero3=-1
			idx = 0
			for val in ReqRcv[0:len(ReqRcv)] :
				if Zero1 == - 1 and Zero3  == -1 and val == 1 :	# Do we get a 0x01
					Zero1 = idx		# we have identify the Frame start

				if Zero1 != -1 and val == 3 :	# If we have already started a Frame and do we get a 0x03
					Zero3 = idx + 1
					break			# If we got 0x03, let process the Frame
				idx += 1

			if Zero3 == -1 :			# No 0x03 in the Buffer, let's breat and wait to get more data
				return

			Domoticz.Debug("onMessage Frame : Zero1=" + str(Zero1) + " Zero3=" + str(Zero3) )

			BinMsg = ReqRcv[Zero1:Zero3]		# What is before 0x03 is in the Frame to be process
			ReqRcv = ReqRcv[Zero3:]			# What is after 0x03 has to be reworked.

			# Process the incoming Frame
			AsciiMsg=binascii.hexlify(BinMsg).decode('utf-8')
			Domoticz.Debug("onMessage Frame : " + str(AsciiMsg) )
			ZigateDecode(self, AsciiMsg) 		# decode this Frame

		Domoticz.Debug("onMessage Remaining Frame : " + str(binascii.hexlify(ReqRcv).decode('utf-8') ))

		return

	def onCommand(self, Unit, Command, Level, Hue):
		Domoticz.Log("#########################")
		Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level) + " Hue: " + str(Hue) )

		DSwitchtype= str(Devices[Unit].SwitchType)
		Domoticz.Debug("DSwitchtype : " + DSwitchtype)

		DSubType= str(Devices[Unit].SubType)
		Domoticz.Debug("DSubType : " + DSubType)

		DType= str(Devices[Unit].Type)
		DOptions = Devices[Unit].Options

		Dtypename=DOptions['TypeName']
		Domoticz.Debug("Dtypename : " + Dtypename)
		Dzigate=eval(DOptions['Zigate'])
		SignalLevel = self.ListOfDevices[Devices[Unit].DeviceID]['RSSI']

		EPin="01"
		EPout="01"  # If we don't have a cluster search, or if we don't find an EPout for a cluster search, then lets use EPout=01
		ClusterSearch = ""
		if Dtypename=="Switch" or Dtypename=="Plug" or Dtypename=="MSwitch" or Dtypename=="Smoke" or Dtypename=="DSwitch" or Dtypename=="Button" or Dtypename=="DButton":
			ClusterSearch="0006"
		if Dtypename=="LvlControl" :
			ClusterSearch="0008"
		if Dtypename=="ColorControl" :
			ClusterSearch="0300"
		
		for tmpEp in self.ListOfDevices[Devices[Unit].DeviceID]['Ep'] :
			if ClusterSearch in self.ListOfDevices[Devices[Unit].DeviceID]['Ep'][tmpEp] : #switch cluster
				EPout=tmpEp

			if Command == "On" :
				self.ListOfDevices[Devices[Unit].DeviceID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
				sendZigateCmd("0092","02" + Devices[Unit].DeviceID + EPin + EPout + "01")
				if DSwitchtype == "16" :
					UpdateDevice_v2(Unit, 1, "100",DOptions, SignalLevel)
				else:
					UpdateDevice_v2(Unit, 1, "On",DOptions, SignalLevel)

			if Command == "Off" :
				if (False):#Pas trouve un moyen sans problemes
					if (Dtypename=="LvlControl") or (Dtypename == 'ColorControl') :
						#Disabled for level control and color control
						Command == "Set Level"
						Level = 1
				else:
					self.ListOfDevices[Devices[Unit].DeviceID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
					sendZigateCmd("0092","02" + Devices[Unit].DeviceID + EPin + EPout + "00")
					if DSwitchtype == "16" :
						UpdateDevice_v2(Unit, 0, "0",DOptions, SignalLevel)
					else :
						UpdateDevice_v2(Unit, 0, "Off",DOptions, SignalLevel)

			if Command == "Set Level" :
				self.ListOfDevices[Devices[Unit].DeviceID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
				OnOff = '01' # 00 = off, 01 = on
				value=Hex_Format(2,round(1+Level*253/100)) #To prevent off state with dimmer, only available with switch
				sendZigateCmd("0081","02" + Devices[Unit].DeviceID + EPin + EPout + OnOff + value + "0010")
				if DSwitchtype == "16" :
					UpdateDevice_v2(Unit, 2, str(Level) ,DOptions, SignalLevel) #Need to use 1 as nvalue else, it will set it to off
				else:
					UpdateDevice_v2(Unit, 1, str(Level) ,DOptions, SignalLevel) #Need to use 1 as nvalue else, it will set it to off

			if Command == "Set Color" :
				Domoticz.Debug("onCommand - Set Color - Level = " + str(Level) + " Hue = " + str(Hue) )
				Hue_List = json.loads(Hue)

				def hex_to_rgb(h):
					''' convert hex color to rgb tuple '''
					h = h.strip('#')
					return tuple(int(h[i:i+2], 16)/255 for i in (0, 2 ,4))

				def rgb_to_xy(rgb):
					''' convert rgb tuple to xy tuple '''
					red, green, blue = rgb
					r = ((red + 0.055) / (1.0 + 0.055))**2.4 if (red > 0.04045) else (red / 12.92)
					g = ((green + 0.055) / (1.0 + 0.055))**2.4 if (green > 0.04045) else (green / 12.92)
					b = ((blue + 0.055) / (1.0 + 0.055))**2.4 if (blue > 0.04045) else (blue / 12.92)
					X = r * 0.664511 + g * 0.154324 + b * 0.162028
					Y = r * 0.283881 + g * 0.668433 + b * 0.047685
					Z = r * 0.000088 + g * 0.072310 + b * 0.986039
					cx = 0
					cy = 0
					if (X + Y + Z) != 0:
						cx = X / (X + Y + Z)
						cy = Y / (X + Y + Z)
					return (cx, cy)

				self.ListOfDevices[Devices[Unit].DeviceID]['Heartbeat'] = 0  # As we update the Device, let's restart and do the next pool in 5'

				#First manage level
				OnOff = '01' # 00 = off, 01 = on
				value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state
				sendZigateCmd("0081","02" + Devices[Unit].DeviceID + EPin + EPout + OnOff + value + "0000")

				#Now color
				#CT mode
				if Hue_List['m'] == 2:
					#Value is in mireds (not kelvin)
					#Correct values are from 153 (6500K) up to 588 (1700K)
					# t is 0 > 255
					TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700);
					TempMired = 1000000 // TempKelvin
					sendZigateCmd("00C0","02" + Devices[Unit].DeviceID + EPin + EPout + Hex_Format(4,TempMired) + "0000")
				#CW WW mode, don't exist ???
				elif Hue_List['m'] == 9999:
					ww = int(Hue_List['ww'])
					cw = int(Hue_List['cw'])
					cwww = Hex_Format(2,cw) + Hex_Format(2,ww)
					#Use it as it ?
					strTemp = str(cwww)
					sendZigateCmd("00C0","02" + Devices[Unit].DeviceID + EPin + EPout + strTemp + "0000")
				#RGB mode
				elif Hue_List['m'] == 3:
					x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))	   
					#Convert 0>1 to 0>FFFF
					x = int(x*65536)
					y = int(y*65536)																   
					strxy = Hex_Format(4,x) + Hex_Format(4,y)
					sendZigateCmd("00B7","02" + Devices[Unit].DeviceID + EPin + EPout + strxy + "0000")
				#With saturation and hue, not seen in domoticz but present on zigate
				elif Hue_List['m'] == 9998:
					saturation = 0 #0 > 100
					hue2 = 0		#0 > 360
					hue2 = int(hue2*254//360)
					saturation = int(saturation*254//100)
					sendZigateCmd("0C0","02" + Devices[Unit].DeviceID + EPin + EPout + Hex_Format(2,hue2) + Hex_Format(2,saturation) + "0000")

				#Update Device
				UpdateDevice_v2(Unit, 1, str(value) ,DOptions, SignalLevel, str(Hue))



	def onDisconnect(self, Connection):
		Domoticz.Log("onDisconnect called")

	def onHeartbeat(self):
		global FirmwareVersion
		global HeartbeatCount

		#Domoticz.Log("onHeartbeat called" )
		Domoticz.Debug("ListOfDevices : " + str(self.ListOfDevices))

		## Check the Network status every 15' / Only possible if FirmwareVersion > 3.0d
		if str(FirmwareVersion) == "030d" :
			if HeartbeatCount >= 90 :
				Domoticz.Debug("request Network Status")
				sendZigateCmd("0009","")
				HeartbeatCount = 0
			else :
				HeartbeatCount = HeartbeatCount + 1

		for key in self.ListOfDevices :
			status=self.ListOfDevices[key]['Status']
			RIA=int(self.ListOfDevices[key]['RIA'])
			self.ListOfDevices[key]['Heartbeat']=str(int(self.ListOfDevices[key]['Heartbeat'])+1)

			########## Known Devices 
			if status == "inDB" : 
				# device id type shutter, let check the shutter status every 5' ( 30 * onHearbeat period ( 10s ) )
				if self.ListOfDevices[key]['Model'] == "shutter.Profalux" and self.ListOfDevices[key]['Heartbeat']>="30" :
					Domoticz.Debug("Request a Read attribute for the shutter " + str(key) )
					self.ListOfDevices[key]['Heartbeat']="0"
	#				ReadAttributeRequest_0008(self, key)

			########## UnKnown Devices  - Creation process
			if status != "inDB" :
				# Request EP list
				if status=="004d" and self.ListOfDevices[key]['Heartbeat']=="1":
					Domoticz.Log("Creation process for " + str(key) + " Info: " + str(self.ListOfDevices[key]) )
					# We should check if the device has not been already created via IEEE
					if IEEEExist( self, self.ListOfDevices[key]['IEEE'] ) == False :
						Domoticz.Debug("onHeartbeat - new device discovered request EP list with 0x0045 and lets wait for 0x8045: " + key)
						sendZigateCmd("0045", str(key))
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
						sendZigateCmd("0043", str(key)+str(cle))
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
							# plug osram
							if self.ListOfDevices[key]['ZDeviceID']=="0010" :  
								self.ListOfDevices[key]['Model']="plug.Osram"
								if self.ListOfDevices[key]['Ep']=={} :
									self.ListOfDevices[key]['Ep']={'03': {'0006'}}

						if self.ListOfDevices[key]['ProfileID']=="0104" :  # profile home automation
							# plug salus
							if self.ListOfDevices[key]['ZDeviceID']=="0051" :  # device id type plug on/off
								self.ListOfDevices[key]['Model']="plug.Salus"
								if self.ListOfDevices[key]['Ep']=={} :
									self.ListOfDevices[key]['Ep']={'09': {'0006'}}
							# ampoule Tradfi
							if self.ListOfDevices[key]['ZDeviceID']=="0100" :  # device id type light on/off
								self.ListOfDevices[key]['Model']="Ampoule.LED1622G12.Tradfri"
								if self.ListOfDevices[key]['Ep']=={} :
									self.ListOfDevices[key]['Ep']={'01': {'0006', '0008'}}
							# shutter profalux
							if self.ListOfDevices[key]['ZDeviceID']=="0200" :  # device id type shutter
								self.ListOfDevices[key]['Model']="shutter.Profalux"
								if self.ListOfDevices[key]['Ep']=={} :
									self.ListOfDevices[key]['Ep']={'01':{'0006','0008'}}
						# phillips hue
						if self.ListOfDevices[key]['ProfileID']=="a1e0" :  
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
							#DOptions = Devices[x].Options
							#Dzigate=eval(DOptions['Zigate'])
							#Domoticz.Debug("HearBeat - Devices[x].Options['Zigate']['IEEE']=" + str(Dzigate['IEEE']))
							#Domoticz.Debug("HearBeat - self.ListOfDevices[key]['IEEE']=" + str(self.ListOfDevices[key]['IEEE']))
							#if Dzigate['IEEE']!='' and self.ListOfDevices[key]['IEEE']!='' :
							#	if Dzigate['IEEE']==self.ListOfDevices[key]['IEEE'] :
							#		IEEEexist = True
							#		Domoticz.Debug("HearBeat - Devices IEEE already exist. Unit=" + str(x))
						if IsCreated == False : #and IEEEexist == False:
							Domoticz.Debug("onHeartbeat - creating device id : " + str(key) + " with : " + str(self.ListOfDevices[key]) )
							CreateDomoDevice(self, key)
						#if IsCreated == False and IEEEexist == True :
						#	Domoticz.Debug("HearBeat - updating device id : " + str(key))
						#	UpdateDomoDevice(self, key)

					#end (RIA>=10 or self.ListOfDevices[key]['Model']!= {})
				#end status != "UNKNOW"	
			#end status != inDB
		#end for key in ListOfDevices

		ResetDevice("Motion",5)
		WriteDeviceList(self, 200)

		if (ZigateConn.Connected() != True):
			ZigateConn.Connect()

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

def ZigateConf():
	global FirmwareVersion

	################### ZiGate - get Firmware version #############
	# answer is expected on message 8010
	sendZigateCmd("0010","")

	################### ZiGate - set channel ##################
	sendZigateCmd("0021", "0000" + returnlen(2,hex(int(Parameters["Mode5"]))[2:4]) + "00")

	################### ZiGate - Set Type COORDINATOR #################
	sendZigateCmd("0023","00")
	
	################### ZiGate - start network ##################
	sendZigateCmd("0024","")

	################### ZiGate - Request Device List #############
	# answer is expected on message 8015. Only available since firmware 03.0b
	if str(FirmwareVersion) == "030d" or str(FirmwareVersion) == "030c" or str(FirmwareVersion == "030b") :
		Domoticz.Log("ZigateConf -  Request : Get List of Device " + str(FirmwareVersion) )
		sendZigateCmd("0015","")
	else :
		Domoticz.Error("Cannot request Get List of Device due to low firmware level" + str(FirmwareVersion) )

	################### ZiGate - discover mode 255 sec Max ##################
	#### Set discover mode only if requested - so != 0                  #####
	if Parameters["Mode2"] != "0":
		if str(Parameters["Mode2"])=="255": 
			Domoticz.Status("Zigate enter in discover mode for ever")
		else : 
			Domoticz.Status("Zigate enter in discover mode for " + str(Parameters["Mode2"]) + " Secs" )
		sendZigateCmd("0049","FFFC" + hex(int(Parameters["Mode2"]))[2:4] + "00")

def ZigateDecode(self, Data):  # supprime le transcodage
	Domoticz.Debug("ZigateDecode - decodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			if Outtmp == "02" :
				Transcode=True
			else :
				if Transcode == True:
					Transcode = False
					if Outtmp[0]=="1" :
						Out+="0"
					else :
						Out+="1"
					Out+=Outtmp[1]
				else :
					Out+=Outtmp
			Outtmp=""
	ZigateRead(self, Out)

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

def sendZigateCmd(cmd,datas) :
	if datas == "" :
		length="0000"
	else :
		length=returnlen(4,(str(hex(int(round(len(datas)/2)))).split('x')[-1]))  # by Cortexlegeni 
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
	Domoticz.Debug("sendZigateCmd - Comand send : " + str(lineinput))
	if Parameters["Mode1"] == "USB":
		ZigateConn.Send(bytes.fromhex(str(lineinput)))	
	if Parameters["Mode1"] == "Wifi":
		ZigateConn.Send(bytes.fromhex(str(lineinput))+bytes("\r\n",'utf-8'),1)

def ZigateRead(self, Data):
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
		calculatedchecksum=getChecksum( MsgType , MsgLength , MsgData + MsgRSSI)
	else :
		MsgData=""
		MsgRSSI=""
		calculatedchecksum=getChecksum( MsgType , MsgLength , "0")

	if ( int(calculatedchecksum,16) != int(MsgCRC,16) ) :
		Domoticz.Error("ZigateRead -  Checksum error: " + calculatedchecksum + " / " + MsgCRC + " MsgType = " + MsgType + " MsgLength : " + MsgLength + " RawData '" + Data  + "'" )
		return

	Domoticz.Debug("ZigateRead - Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC)

	
	if str(MsgType)=="004d":  # Device announce
		Domoticz.Debug("ZigateRead - MsgType 004d - Reception Device announce : " + Data)
		Decode004d(self, MsgData)
		return
		
	elif str(MsgType)=="00d1":  #
		Domoticz.Debug("ZigateRead - MsgType 00d1 - Reception Touchlink status : " + Data)
		return
		
	elif str(MsgType)=="8000":  # Status
		Domoticz.Debug("ZigateRead - MsgType 8000 - reception status : " + Data)
		#Decode8000(self, MsgData)
		Decode8000_v2(self, MsgData)
		return

	elif str(MsgType)=="8001":  # Log
		Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level : " + Data)
		Decode8001(self, MsgData)
		return

	elif str(MsgType)=="8002":  #
		Domoticz.Debug("ZigateRead - MsgType 8002 - Reception Data indication : " + Data)
		return

	elif str(MsgType)=="8003":  #
		Domoticz.Debug("ZigateRead - MsgType 8003 - Reception Liste des cluster de l'objet : " + Data)
		return

	elif str(MsgType)=="8004":  #
		Domoticz.Debug("ZigateRead - MsgType 8004 - Reception Liste des attributs de l'objet : " + Data)
		return
		
	elif str(MsgType)=="8005":  #
		Domoticz.Debug("ZigateRead - MsgType 8005 - Reception Liste des commandes de l'objet : " + Data)
		return

	elif str(MsgType)=="8006":  #
		Domoticz.Debug("ZigateRead - MsgType 8006 - Reception Non factory new restart : " + Data)
		return

	elif str(MsgType)=="8007":  #
		Domoticz.Debug("ZigateRead - MsgType 8007 - Reception Factory new restart : " + Data)
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
		return

	elif str(MsgType)=="8028":  #
		Domoticz.Debug("ZigateRead - MsgType 8028 - Reception Authenticate response : " + Data)
		return

	elif str(MsgType)=="8029":  #
		Domoticz.Debug("ZigateRead - MsgType 8029 - Reception Out of band commissioning data response : " + Data)
		return

	elif str(MsgType)=="802b":  #
		Domoticz.Debug("ZigateRead - MsgType 802b - Reception User descriptor notify : " + Data)
		return

	elif str(MsgType)=="802c":  #
		Domoticz.Debug("ZigateRead - MsgType 802c - Reception User descriptor response : " + Data)
		return

	elif str(MsgType)=="8030":  #
		Domoticz.Debug("ZigateRead - MsgType 8030 - Reception Bind response : " + Data)
		return

	elif str(MsgType)=="8031":  #
		Domoticz.Debug("ZigateRead - MsgType 8031 - Reception Unbind response : " + Data)
		return

	elif str(MsgType)=="8034":  #
		Domoticz.Debug("ZigateRead - MsgType 8034 - Reception Coplex Descriptor response : " + Data)
		return

	elif str(MsgType)=="8040":  #
		Domoticz.Debug("ZigateRead - MsgType 8040 - Reception Network address response : " + Data)
		return

	elif str(MsgType)=="8041":  #
		Domoticz.Debug("ZigateRead - MsgType 8041 - Reception IEEE address response : " + Data)
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
		Domoticz.Debug("ZigateRead - MsgType 8046 - Reception Match descriptor response : " + Data)
		return

	elif str(MsgType)=="8047":  #
		Domoticz.Debug("ZigateRead - MsgType 8047 - Reception Management leave response : " + Data)
		return

	elif str(MsgType)=="8048":  #
		Domoticz.Debug("ZigateRead - MsgType 8048 - Reception Leave indication : " + Data)
		return

	elif str(MsgType)=="804a":  #
		Domoticz.Debug("ZigateRead - MsgType 804a - Reception Management Network Update response : " + Data)
		return

	elif str(MsgType)=="804b":  #
		Domoticz.Debug("ZigateRead - MsgType 804b - Reception System server discovery response : " + Data)
		return

	elif str(MsgType)=="804e":  #
		Domoticz.Debug("ZigateRead - MsgType 804e - Reception Management LQI response : " + Data)
		return

	elif str(MsgType)=="8060":  #
		Domoticz.Debug("ZigateRead - MsgType 8060 - Reception Add group response : " + Data)
		return

	elif str(MsgType)=="8061":  #
		Domoticz.Debug("ZigateRead - MsgType 8061 - Reception Viex group response : " + Data)
		return

	elif str(MsgType)=="8062":  #
		Domoticz.Debug("ZigateRead - MsgType 8062 - Reception Get group Membership response : " + Data)
		return

	elif str(MsgType)=="8063":  #
		Domoticz.Debug("ZigateRead - MsgType 8063 - Reception Remove group response : " + Data)
		return

	elif str(MsgType)=="80a0":  #
		Domoticz.Debug("ZigateRead - MsgType 80a0 - Reception View scene response : " + Data)
		return

	elif str(MsgType)=="80a1":  #
		Domoticz.Debug("ZigateRead - MsgType 80a1 - Reception Add scene response : " + Data)
		return

	elif str(MsgType)=="80a2":  #
		Domoticz.Debug("ZigateRead - MsgType 80a2 - Reception Remove scene response : " + Data)
		return

	elif str(MsgType)=="80a3":  #
		Domoticz.Debug("ZigateRead - MsgType 80a3 - Reception Remove all scene response : " + Data)
		return

	elif str(MsgType)=="80a4":  #
		Domoticz.Debug("ZigateRead - MsgType 80a4 - Reception Store scene response : " + Data)
		return

	elif str(MsgType)=="80a6":  #
		Domoticz.Debug("ZigateRead - MsgType 80a6 - Reception Scene membership response : " + Data)
		return

	elif str(MsgType)=="8100":  #
		Domoticz.Debug("ZigateRead - MsgType 8100 - Reception Real individual attribute response : " + Data)
		Decode8100(self, MsgData, MsgRSSI)
		return

	elif str(MsgType)=="8101":  # Default Response
		Domoticz.Debug("ZigateRead - MsgType 8101 - Default Response: " + Data)
		Decode8101(self, MsgData)
		return

	elif str(MsgType)=="8102":  # Report Individual Attribute response
		Domoticz.Debug("ZigateRead - MsgType 8102 - Report Individual Attribute response : " + Data)	
		Decode8102(self, MsgData, MsgRSSI)
		return
		
	elif str(MsgType)=="8110":  #
		Domoticz.Debug("ZigateRead - MsgType 8110 - Reception Write attribute response : " + Data)
		return

	elif str(MsgType)=="8120":  #
		Domoticz.Debug("ZigateRead - MsgType 8120 - Reception Configure reporting response : " + Data)
		return

	elif str(MsgType)=="8140":  #
		Domoticz.Debug("ZigateRead - MsgType 8140 - Reception Attribute discovery response : " + Data)
		return

	elif str(MsgType)=="8401":  # Reception Zone status change notification
		Domoticz.Debug("ZigateRead - MsgType 8401 - Reception Zone status change notification : " + Data)
		Decode8401(self, MsgData)
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
		Domoticz.Debug("ZigateRead - Unknow Message Type for : " + Data)
		return
	
	return

def Decode004d(self, MsgData) : # Reception Device announce
	MsgSrcAddr=MsgData[0:4]
	MsgIEEE=MsgData[4:20]
	MsgMacCapa=MsgData[20:22]
	Domoticz.Debug("Decode004d - Reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa)
	# tester si le device existe deja dans la base domoticz
	if DeviceExist(self, MsgSrcAddr)==False :
		Domoticz.Debug("Decode004d - Looks like it is a new device sent by Zigate")
		self.ListOfDevices[MsgSrcAddr]['MacCapa']=MsgMacCapa
		self.ListOfDevices[MsgSrcAddr]['IEEE']=MsgIEEE
		# Should we not force status to "004d" and reset Hearbeat , in order to start the processing from begining in onHeartbeat() ?
	else :
		Domoticz.Debug("Decode004d - Existing device")
		# Should we not force status to "004d" and reset Hearbeat , in order to start the processing from begining in onHeartbeat() ?
		
	return

def Decode8000_v2(self, MsgData) : # Status
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8000_v2 - MsgData lenght is : " + str(MsgLen) + " out of 8")

	if MsgLen != 8 :
		return

	Status=MsgData[0:2]
	SEQ=MsgData[2:4]
	PacketType=MsgData[4:8]

	if Status=="00" : Status="Success"
	elif Status=="01" : Status="Incorrect Parameters"
	elif Status=="02" : Status="Unhandled Command"
	elif Status=="03" : Status="Command Failed"
	elif Status=="04" : Status="Busy"
	elif Status=="05" : Status="Stack Already Started"
	elif int(Status,16) >= 128 and int(Status,16) <= 244 : Status="ZigBee Error Code "+ DisplayStatusCode(Status)

	Domoticz.Debug("Decode8000_v2 - status: " + Status + " SEQ: " + SEQ + " Packet Type: " + PacketType )

	if   PacketType=="0012" : Domoticz.Log("Erase Persistent Data cmd status : " +  Status )
	elif PacketType=="0014" : Domoticz.Log("Permit Join status : " +  Status )
	elif PacketType=="0024" : Domoticz.Log("Start Network status : " +  Status )
	elif PacketType=="0026" : Domoticz.Log("Remove Device cmd status : " +  Status )
	elif PacketType=="0044" : Domoticz.Log("request Power Descriptor status : " +  Status )

	if str(MsgData[0:2]) != "00" : Domoticz.Log("Decode8000_v2 - status: " + Status + " SEQ: " + SEQ + " Packet Type: " + PacketType )

	return
	
def Decode8000(self, MsgData) : # Reception status
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8000 - MsgData lenght is : " + str(MsgLen) + " out of 8")

	MsgDataLenght=MsgData[0:4]
	MsgDataStatus=MsgData[4:6]
	if MsgDataStatus=="00" :
		MsgDataStatus="Success"
	elif MsgDataStatus=="01" :
		MsgDataStatus="Incorrect Parameters"
	elif MsgDataStatus=="02" :
		MsgDataStatus="Unhandled Command"
	elif MsgDataStatus=="03" :
		MsgDataStatus="Command Failed"
	elif MsgDataStatus=="04" :
		MsgDataStatus="Busy"
	elif MsgDataStatus=="05" :
		MsgDataStatus="Stack Already Started"
	else :
		MsgDataStatus="ZigBee Error Code "+ MsgDataStatus
	MsgDataSQN=MsgData[6:8]
	#Correction Thiklop : MsgDataLenght n'est pas toujours un entier
	#Encapsulation des 4 lignes dans un try except pour sortir proprement en testant le type de MsgDataLenght
	try :
		int(MsgDataLenght,16)
	except :
		Domoticz.Error("Decode8000 - Fonction Decode 8000 problème de MsgDataLenght, pas un int")
		MsgDataMessage=""
	else :
		if int(MsgDataLenght,16) > 2 :
			MsgDataMessage=MsgData[8:len(MsgData)]
		else :
			MsgDataMessage=""
	#Fin de la correction
	Domoticz.Debug("Decode8000 - Reception status : " + MsgDataStatus + ", SQN : " + MsgDataSQN + ", Message : " + MsgDataMessage)
	return

def Decode8001(self, MsgData) : # Reception log Level
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8001 - MsgData lenght is : " + str(MsgLen) + " out of 2" )

	MsgLogLvl=MsgData[0:2]
	MsgDataMessage=MsgData[2:len(MsgData)]
	Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)
	return

def Decode8009(self,MsgData) : # Network State response (Firm v3.0d)
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8009 - MsgData lenght is : " + str(MsgLen) + " out of 42")

	addr=MsgData[0:4]
	extaddr=MsgData[4:20]
	PanID=MsgData[20:24]
	extPanID=MsgData[24:40]
	Channel=MsgData[40:42]
	Domoticz.Debug("Decode8009: Network state - Address :" + addr + " extaddr :" + extaddr + " PanID : " + PanID + " Channel : " + Channel )
	# from https://github.com/fairecasoimeme/ZiGate/issues/15 , if PanID == 0 -> Network is done
	if str(PanID) == "0" : 
		Domoticz.Error("Decode8009: Network state DOWN ! " )
	else :
		Domoticz.Status("Decode8009: Network state UP - PAN Id = " + str(PanID) + " on Channel = " + Channel )

	return

def Decode8010(self,MsgData) : # Reception Version list
	global FirmwareVersion
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
		FirmwareVersion = InstaVersNum

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
		if saddr in  self.ListOfDevices:
			Domoticz.Log("Decode8015 : [ " + str(round(idx/26)) + "] DevID = " + DevID + " Addr = " + saddr + " IEEE = " + ieee + " RSSI = " + str(int(rssi,16)) + " Power = " + power + " found in ListOfDevice")
			if rssi !="00" :
				self.ListOfDevices[saddr]['RSSI']= int(rssi,16)
			else  :
				self.ListOfDevices[saddr]['RSSI']= 12
			Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[saddr]['RSSI']) + "/" + str(rssi) + " for " + str(saddr) )
		else: 
			Domoticz.Log("Decode8015 : [ " + str(round(idx/26)) + "] DevID = " + DevID + " Addr = " + saddr + " IEEE = " + ieee + " not found in ListOfDevice")
		idx=idx+26

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
	Domoticz.Debug("Decode8043 - Reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status : " + MsgDataStatus + ", short Addr : " + MsgDataShAddr + ", Lenght : " + MsgDataLenght)
	if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
		self.ListOfDevices[MsgDataShAddr]['Status']="8043"
	if int(MsgDataLenght,16)>0 :
		MsgDataEp=MsgData[10:12]
		MsgDataProfile=MsgData[12:16]
		self.ListOfDevices[MsgDataShAddr]['ProfileID']=MsgDataProfile
		MsgDataDeviceId=MsgData[16:20]
		self.ListOfDevices[MsgDataShAddr]['ZDeviceID']=MsgDataDeviceId
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
	Domoticz.Debug("Decode8045 - Reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", EP count " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)
	OutEPlist=""
	DeviceExist(self, MsgDataShAddr)
	#Correction Thiklop : MsgDataShAddr provoque un Keyerror (?)
	#Sortie propre par try except
	try :
		temp_sert_a_rien = self.ListOfDevices[MsgDataShAddr]['Status']!="inDB"
	except :
		Domoticz.Error("Decode8045 - KeyError : MsgDataShAddr = " + MsgDataShAddr)
	else :
		if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
			self.ListOfDevices[MsgDataShAddr]['Status']="8045"
		# PP: Does that mean that if we Device is already in the Database, we might overwrite 'EP' ?
		for i in MsgDataEPlist :
			OutEPlist+=i
			if len(OutEPlist)==2 :
				if OutEPlist not in self.ListOfDevices[MsgDataShAddr]['Ep'] :
					self.ListOfDevices[MsgDataShAddr]['Ep'][OutEPlist]={}
					OutEPlist=""
	#Fin de correction
	Domoticz.Debug("Decode8045 - Device : " + str(MsgDataShAddr) + " updated ListofDevices with " + str(self.ListOfDevices[MsgDataShAddr]['Ep']) )
	return

def Decode8100(self, MsgData, MsgRSSI) :  # Report Individual Attribute response
	try:
		MsgSQN=MsgData[0:2]
		MsgSrcAddr=MsgData[2:6]
		MsgSrcEp=MsgData[6:8]
		MsgClusterId=MsgData[8:12]
		MsgAttrID=MsgData[12:16]
		MsgAttType=MsgData[16:20]
		MsgAttSize=MsgData[20:24]
		MsgClusterData=MsgData[24:len(MsgData)]
	except:
		Domoticz.Error("Decode8100 - MsgData = " + MsgData)

	else:
		Domoticz.Debug("Decode8100 - reception data : " + MsgClusterData + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp + " RSSI: " + MsgRSSI)
		try :
			self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
		except : 
			self.ListOfDevices[MsgSrcAddr]['RSSI']= 0
		Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[MsgSrcAddr]['RSSI']) + "/" + str(MsgRSSI) + " for " + str(MsgSrcAddr) )
		ReadCluster(self, MsgData) 
	return


def Decode8101(self, MsgData) :  # Default Response
	MsgDataSQN=MsgData[0:2]
	MsgDataEp=MsgData[2:4]
	MsgClusterId=MsgData[4:8]
	MsgDataCommand=MsgData[8:10]
	MsgDataStatus=MsgData[10:12]
	Domoticz.Debug("Decode8101 - reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " + MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + MsgDataStatus)
	return

def Decode8102(self, MsgData, MsgRSSI) :  # Report Individual Attribute response
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]
	Domoticz.Debug("Decode8102 - reception data : " + MsgClusterData + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp + " RSSI = " + MsgRSSI )
	if MsgSrcAddr  in self.ListOfDevices:
		try:
			self.ListOfDevices[MsgSrcAddr]['RSSI']= int(MsgRSSI,16)
		except:
			self.ListOfDevices[MsgSrcAddr]['RSSI']= 0
		Domoticz.Debug("Decode8015 : RSSI set to " + str( self.ListOfDevices[MsgSrcAddr]['RSSI']) + "/" + str(MsgRSSI) + " for " + str(MsgSrcAddr) )
		ReadCluster(self, MsgData) 
	else :
		Domoticz.Error("Decode8102 - Receiving a message from unknown device : " + str(MsgSrcAddr) + " with Data : " +str(MsgData) )
	return

def Decode8701(self, MsgData) : # Reception Router Disovery Confirm Status
	MsgLen=len(MsgData)
	Domoticz.Debug("Decode8701 - MsgLen = " + str(MsgLen))

	if MsgLen==0 :
		return
	else:
		MsgStatus=MsgData[0:2]
		NwkStatus=MsgData[2:4]
		Domoticz.Debug("Decode8701 - Reception Router Discovery Confirm Status:" + MsgStatus + ", Nwk Status : "+ NwkStatus )
	
		if NwkStatus != "00" : Domoticz.Error("Decode8701 - Reception Router Discovery Confirm Status:" + DisplayStatusCode( NwkStatus) + ", Nwk Status : "+ NwkStatus )
		return

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
		Domoticz.Debug("Decode 8702 - " +  DisplayStatusCode( MsgDataStatus )  + ", SrcEp : " + MsgDataSrcEp + ", DestEp : " + MsgDataDestEp + ", DestMode : " + MsgDataDestMode + ", DestAddr : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)
		return

def Decode8401(self, MsgData) : # Reception Zone status change notification
	Domoticz.Debug("Decode8401 - Reception Zone status change notification : " + MsgData)
	MsgSrcAddr=MsgData[10:14]
	MsgSrcEp=MsgData[2:4]
	MsgClusterData=MsgData[16:18]
	MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, "0006", MsgClusterData)
	return

def CreateDomoDevice(self, DeviceID) :
	for Ep in self.ListOfDevices[DeviceID]['Ep'] :
		if self.ListOfDevices[DeviceID]['Type']== {} :
			Type=GetType(self, DeviceID, Ep).split("/")
			Domoticz.Log("CreateDomoDevice -  Type via GetType: " + str(Type) + " Ep : " + str(Ep) )
		else :
			Type=self.ListOfDevices[DeviceID]['Type'].split("/")
			Domoticz.Log("CreateDomoDevice - Type : '" + str(Type) + "'")

		if Type !="" :
			if "Humi" in Type and "Temp" in Type and "Baro" in Type:
				t="Temp+Hum+Baro" # Detecteur temp + Hum + Baro
				Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), TypeName=t, Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()
			if "Humi" in Type and "Temp" in Type :
				t="Temp+Hum"
				Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), TypeName=t, Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

			#For color Bulb
			if ("Switch" in Type) and ("LvlControl" in Type) and ("ColorControl" in Type):
				Type = ['ColorControl']
			elif ("Switch" in Type) and ("LvlControl" in Type):
				Type = ['LvlControl']

			for t in Type :
				Domoticz.Log("CreateDomoDevice - Device ID : " + str(DeviceID) + " Device EP : " + str(Ep) + " Type : " + str(t) )
				if t=="Temp" : # Detecteur temp
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), TypeName="Temperature", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Humi" : # Detecteur hum
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), TypeName="Humidity", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Baro" : # Detecteur Baro
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), TypeName="Barometer", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Door": # capteur ouverture/fermeture xiaomi
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=2 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Motion" :  # detecteur de presence
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=8 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="MSwitch"  :  # interrupteur multi lvl 86sw2 xiaomi
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "||||", "LevelNames": "Push|1 Click|2 Click|3 Click|4 Click", "LevelOffHidden": "false", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="DSwitch"  :  # interrupteur double sur EP different
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="DButton"  :  # interrupteur double sur EP different
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="Smoke" :  # detecteur de fumee
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=5 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Lux" :  # Lux sensors
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=246, Subtype=1 , Switchtype=0 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Switch":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=0 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Button":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=9 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Aqara" or t=="XCube" :  # Xiaomi Magic Cube
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||||||||", "LevelNames": "Off|Shake|Wakeup|Drop|90°|180°|Push|Tap|Rotation", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="Water" :  # detecteur d'eau 
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=0 , Image=11 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Plug" :  # prise pilote
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73 , Switchtype=0 , Image=1 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="LvlControl" and self.ListOfDevices[DeviceID]['Model']=="shutter.Profalux" :  # Volet Roulant / Shutter / Blinds, let's created blindspercentageinverted devic
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73, Switchtype=16 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="LvlControl" and self.ListOfDevices[DeviceID]['Model']!="shutter.Profalux" :  # variateur de luminosite + On/off
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=244, Subtype=73, Switchtype=7 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="ColorControl" :  # variateur de couleur/luminosite/on-off
					self.ListOfDevices[DeviceID]['Status']="inDB"
					# Type 0xF1    pTypeColorSwitch
					# SubType 0x07 sTypeColor_RGB_CW_WW_Z
					# SubType 0x02 sTypeColor_RGB
					# SubType 0x08 sTypeColor_CW_WW

					# Switchtype 7 STYPE_Dimmer

					if self.ListOfDevices[DeviceID]['Model'] == "Ampoule.LED1624G9.Tradfri":
						Subtype_ = 2
					if self.ListOfDevices[DeviceID]['Model'] == "Ampoule.LED1545G12.Tradfri":
						Subtype_ = 8
					else:
						Subtype_ = 7

					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=FreeUnit(self), Type=241, Subtype=Subtype_ , Switchtype=7 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				#Ajout meter
				if t=="PowerMeter" :  # Power Prise Xiaomi
					Domoticz.Debug("Ajout Meter")
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, TypeName="Usage" , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

#def UpdateDomoDevice(self, DeviceID) :
#	IEEEexist=False
#	x=0
#	for x in Devices:
#		DOptions = Devices[x].Options
#		Dzigate=eval(DOptions['Zigate'])
#		if Dzigate['IEEE']==self.ListOfDevices[DeviceID]['IEEE'] :
#			Domoticz.Debug("HearBeat - Devices IEEE already exist. Unit=" + str(x))
#			Devices[x].Update(nValue=Devices[x].nValue, sValue=str(Devices[x].sValue), DeviceID=str(DeviceID))
			


def FreeUnit(self) :
	FreeUnit=""
	for x in range(1,256):
		Domoticz.Debug("FreeUnit - is device " + str(x) + " exist ?")
		if x not in Devices :
			Domoticz.Debug("FreeUnit - device " + str(x) + " not exist")
			FreeUnit=x
			return FreeUnit			
	if FreeUnit =="" :
		FreeUnit=len(Devices)+1
	Domoticz.Debug("FreeUnit - Free Device Unit find : " + str(x))
	return FreeUnit

def MajDomoDevice(self,DeviceID,Ep,clusterID,value,Color_='') :
	Domoticz.Log("MajDomoDevice - Device ID : " + str(DeviceID) + " - Device EP : " + str(Ep) + " - Type : " + str(clusterID)  + " - Value : " + str(value) + " - Hue : " + str(Color_))
	x=0
	Type=TypeFromCluster(clusterID)
	Domoticz.Debug("MajDomoDevice - Type = " + str(Type) )
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) :
			DOptions = Devices[x].Options
			Dtypename=DOptions['TypeName']
			DOptions['Zigate']=str(self.ListOfDevices[DeviceID])
			SignalLevel = self.ListOfDevices[DeviceID]['RSSI']

			Domoticz.Debug("MajDomoDevice - Dtypename = " + str(Dtypename) )
	
			if Dtypename=="Temp+Hum+Baro" : #temp+hum+Baro xiaomi
				Bar_forecast = '0' # Set barometer forecast to 0 (No info)
				if Type=="Temp" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2] , SplitData[3], Bar_forecast)
					Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
					#UpdateDevice(x,0,str(NewSvalue),DOptions)								
					UpdateDevice_v2(x,0,str(NewSvalue),DOptions, SignalLevel)								
				if Type=="Humi" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], str(value) ,  SplitData[2] , SplitData[3], Bar_forecast)
					Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
					#UpdateDevice(x,0,str(NewSvalue),DOptions)
					UpdateDevice_v2(x,0,str(NewSvalue),DOptions, SignalLevel)								
				if Type=="Baro" :  # barometer
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					valueBaro='%s;%s;%s;%s;%s' % (SplitData[0], SplitData[1], str(value) , SplitData[3], Bar_forecast)
					#UpdateDevice(x,0,str(valueBaro),DOptions)
					UpdateDevice_v2(x,0,str(valueBaro),DOptions, SignalLevel)								
			if Dtypename=="Temp+Hum" : #temp+hum xiaomi
				if Type=="Temp" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
					Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
					#UpdateDevice(x,0,str(NewSvalue),DOptions)								
					UpdateDevice_v2(x,0,str(NewSvalue),DOptions, SignalLevel)								
				if Type=="Humi" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
					Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
					#UpdateDevice(x,0,str(NewSvalue),DOptions)
					UpdateDevice_v2(x,0,str(NewSvalue),DOptions, SignalLevel)								
			if Type==Dtypename=="Temp" :  # temperature
				#UpdateDevice(x,0,str(value),DOptions)				
				UpdateDevice_v2(x,0,str(value),DOptions, SignalLevel)								
			if Type==Dtypename=="Humi" :   # humidite
				#UpdateDevice(x,int(value),"0",DOptions)				
				UpdateDevice_v2(x,int(value),"0",DOptions, SignalLevel)								
			if Type==Dtypename=="Baro" :  # barometre
				CurrentnValue=Devices[x].nValue
				CurrentsValue=Devices[x].sValue
				Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
				SplitData=CurrentsValue.split(";")
				valueBaro='%s;%s' % (value,SplitData[0])
				#UpdateDevice(x,0,str(valueBaro),DOptions)
				UpdateDevice_v2(x,0,str(valueBaro),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="Door" :  # porte / fenetre
				if value == "01" :
					state="Open"
					#Correction Thiklop : value n'est pas toujours un entier. Exécution de l'updatedevice dans le test
					#UpdateDevice(x,int(value),str(state),DOptions)
					UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
				elif value == "00" :
					state="Closed"
					#Correction Thiklop : idem
					#UpdateDevice(x,int(value),str(state),DOptions)
					UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
					#Fin de la correction
			if Type==Dtypename=="Switch" : # switch simple
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				#UpdateDevice(x,int(value),str(state),DOptions)
				UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
				if value == "01" :
					state="Open"
				elif value == "00" :
					state="Closed"
				UpdateDevice(x,int(value),str(state),DOptions)
				#UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="Button": # boutton simple
				if value == "01" :
					state="On"
					#UpdateDevice(x,int(value),str(state),DOptions)
					UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
				else:
					return
			if Type=="Switch" and Dtypename=="Water" : # detecteur d eau
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				#UpdateDevice(x,int(value),str(state),DOptions)
				UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="Smoke" : # detecteur de fume
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				#UpdateDevice(x,int(value),str(state),DOptions)
				UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="MSwitch" : # multi lvl switch
				if value == "00" :
					state="00"
				elif value == "01" :
					state="10"
				elif value == "02" :
					state="20"
				elif value == "03" :
					state="30"
				elif value == "04" :
					state="40"
				else :
					state="0"
				#UpdateDevice(x,int(value),str(state),DOptions)
				UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="DSwitch" : # double switch avec EP different   ====> a voir pour passer en deux switch simple ... a corriger/modifier
				if Ep == "01" :
					if value == "01" or value =="00" :
						state="10"
						data="01"
				elif Ep == "02" :
					if value == "01" or value =="00":
						state="20"
						data="02"
				elif Ep == "03" :
					if value == "01" or value =="00" :
						state="30"
						data="03"
				#UpdateDevice(x,int(data),str(state),DOptions)
				UpdateDevice_v2(x,int(data),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="DButton" : # double bouttons avec EP different   ====> a voir pour passer en deux bouttons simple ...  idem DSwitch ???
				if Ep == "01" :
					if value == "01" or value =="00" :
						state="10"
						data="01"
				elif Ep == "02" :
					if value == "01" or value =="00":
						state="20"
						data="02"
				elif Ep == "03" :
					if value == "01" or value =="00" :
						state="30"
						data="03"
				#UpdateDevice(x,int(data),str(state),DOptions)
				UpdateDevice_v2(x,int(data),str(state),DOptions, SignalLevel)

			if Type=="XCube" and Dtypename=="Aqara" and Ep == "02": #Magic Cube Acara 
					Domoticz.Debug("MajDomoDevice - XCube update device with data = " + str(value) )
					UpdateDevice_v2( x, int(value), str(value), DOptions, SignalLevel )

			if Type=="XCube" and Dtypename=="Aqara" and Ep == "03": #Magic Cube Acara Rotation
					Domoticz.Debug("MajDomoDevice - XCube update device with data = " + str(value) )
					UpdateDevice_v2( x, int(value), str(value), DOptions, SignalLevel )

			if Type==Dtypename=="XCube" and Ep == "02":  # cube xiaomi
				if value == "0000" : #shake
					state="10"
					data="01"
					UpdateDevice(x,int(data),str(state),DOptions)
				elif value == "0204" or value == "0200" or value == "0203" or value == "0201" or value == "0202" or value == "0205": #tap
					state="50"
					data="05"
					UpdateDevice(x,int(data),str(state),DOptions)
				elif value == "0103" or value == "0100" or value == "0104" or value == "0101" or value == "0102" or value == "0105": #Slide
					state="20"
					data="02"
					UpdateDevice(x,int(data),str(state),DOptions)
				elif value == "0003" : #Free Fall
					state="70"
					data="07"
					UpdateDevice(x,int(data),str(state),DOptions)
				elif value >= "0004" and value <= "0059": #90°
					state="30"
					data="03"
					UpdateDevice(x,int(data),str(state),DOptions)
				elif value >= "0060" : #180°
					state="90"
					data="09"
					UpdateDevice(x,int(data),str(state),DOptions)

			if Type==Dtypename=="Lux" :
				#UpdateDevice(x,0,str(value),DOptions)
				UpdateDevice_v2(x,0,str(value),DOptions, SignalLevel)
			if Type==Dtypename=="Motion" :
				#Correction Thiklop : value pas toujours un entier :
				#'onMessage' failed 'ValueError':'invalid literal for int() with base 10: '00031bd000''.
				# UpdateDevice dans le if
				if value == "01" :
					state="On"
					UpdateDevice(x,int(value),str(state),DOptions)
					#UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
				elif value == "00" :
					state="Off"
					UpdateDevice(x,int(value),str(state),DOptions)
					#UpdateDevice_v2(x,int(value),str(state),DOptions, SignalLevel)
				#Fin de correction

			if Type==Dtypename=="LvlControl" :
				try:
					sValue =  round((int(value,16)/255)*100)
				except:
					Domoticz.Error("MajDomoDevice - value is not an int = " + str(value) )
				else:
					Domoticz.Debug("MajDomoDevice LvlControl - DvID : " + str(DeviceID) + " - Device EP : " + str(Ep) + " - Value : " + str(sValue) + " sValue : " + str(Devices[x].sValue) )

					nValue = 2
					
					if str(nValue) != str(Devices[x].nValue) or str(sValue) != str(Devices[x].sValue) :
						Domoticz.Debug("MajDomoDevice update DevID : " + str(DeviceID) + " from " + str(Devices[x].nValue) + " to " + str(nValue) )
						#UpdateDevice(x, str(nValue), str(sValue) ,DOptions)
						UpdateDevice_v2(x, str(nValue), str(sValue) ,DOptions, SignalLevel)


			if Type==Dtypename=="ColorControl" :
				try:
					sValue =  round((int(value,16)/255)*100)
				except:
					Domoticz.Error("MajDomoDevice - value is not an int = " + str(value) )
				else:
					Domoticz.Debug("MajDomoDevice ColorControl - DvID : " + str(DeviceID) + " - Device EP : " + str(Ep) + " - Value : " + str(sValue) + " sValue : " + str(Devices[x].sValue) )
			
				nValue = 2
			
				if str(nValue) != str(Devices[x].nValue) or str(sValue) != str(Devices[x].sValue) or str(Color_) != str(Devices[x].Color):
					Domoticz.Debug("MajDomoDevice update DevID : " + str(DeviceID) + " from " + str(Devices[x].nValue) + " to " + str(nValue))
					Domoticz.Debug("MajDomoDevice update DevID : " + str(DeviceID) + " from " + str(Devices[x].Color) + " to " + str(Color_))
					#UpdateDevice(x, str(nValue), str(sValue) ,DOptions)
					UpdateDevice_v2(x, str(nValue), str(sValue) ,DOptions, SignalLevel, Color_)
						#Modif Meter
			if clusterID=="000c" and Type != "XCube":
				Domoticz.Debug("Update Value Meter : "+str(round(struct.unpack('f',struct.pack('i',int(value,16)))[0])))
				UpdateDevice(x,0,str(round(struct.unpack('f',struct.pack('i',int(value,16)))[0])),DOptions)

def ResetDevice(Type,HbCount) :
	x=0
	for x in Devices: 
		try :
			LUpdate=Devices[x].LastUpdate
			LUpdate=time.mktime(time.strptime(LUpdate,"%Y-%m-%d %H:%M:%S"))
			current = time.time()
			DOptions = Devices[x].Options
			Dtypename=DOptions['TypeName']
			if (current-LUpdate)> 30 :
				if Dtypename=="Motion":
					value = "00"
					state="Off"
					#Devices[x].Update(nValue = int(value),sValue = str(state))
					UpdateDevice(x,int(value),str(state),DOptions)	
		except :
			return
def IEEEExist(self, IEEE) :
	#check in ListOfDevices for an existing IEEE
	if IEEE : 
		if IEEE in self.ListOfDevices and IEEE != '' :
			return True
		else:
			return False

def DeviceExist(self, Addr) :
	#check in ListOfDevices
	if Addr in self.ListOfDevices and Addr != '' :
		if 'Status' in self.ListOfDevices[Addr] :
			return True
		else :
			initDeviceInList(self, Addr)
			return False
	else :  # devices inconnu ds listofdevices et ds db
		initDeviceInList(self, Addr)
		return False

def initDeviceInList(self, Addr) :
	if Addr != '' :
		self.ListOfDevices[Addr]={}
		self.ListOfDevices[Addr]['Ep']={}
		self.ListOfDevices[Addr]['Status']="004d"
		self.ListOfDevices[Addr]['Heartbeat']="0"
		self.ListOfDevices[Addr]['RIA']="0"
		self.ListOfDevices[Addr]['RSSI']={}
		self.ListOfDevices[Addr]['Battery']={}
		self.ListOfDevices[Addr]['Model']={}
		self.ListOfDevices[Addr]['MacCapa']={}
		self.ListOfDevices[Addr]['IEEE']={}
		self.ListOfDevices[Addr]['Type']={}
		self.ListOfDevices[Addr]['ProfileID']={}
		self.ListOfDevices[Addr]['ZDeviceID']={}

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

def UpdateSignalLevel( DeviceID, SignalLvl) :
	x=0
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID):
			Domoticz.Debug("Update Signal Level for Devices Unit=" + str(x) + " DeviceID = " + str(DeviceID) + " with level = " + str(SignalLvl) )
			CurrentnValue=Devices[x].nValue
			CurrentsValue=Devices[x].sValue
			CurrentsOptions=Devices[x].Options
			rssi= round( (SignalLvl * 12 ) / 200) # Should be 255, but there is no chance to have 255 !
			Domoticz.Debug("Update Signal Level for Devices Unit=" + str(x) + " DeviceID = " + str(DeviceID) + " with level = " + str(SignalLvl) + " RSSI = " + str(rssi) )
			Devices[x].Update(nValue=int(CurrentnValue), sValue=str(CurrentsValue), Options=str(CurrentsOptions), SignalLevel=int(rssi) )
	return

def UpdateBattery(DeviceID,BatteryLvl):
	x=0
	found=False
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID):
			found==True
			Domoticz.Log("Devices exist in DB. Unit=" + str(x))
			CurrentnValue=Devices[x].nValue
			Domoticz.Log("CurrentnValue = " + str(CurrentnValue))
			CurrentsValue=Devices[x].sValue
			Domoticz.Log("CurrentsValue = " + str(CurrentsValue))
			Domoticz.Log("BatteryLvl = " + str(BatteryLvl))
			Devices[x].Update(nValue = int(CurrentnValue),sValue = str(CurrentsValue), BatteryLevel = BatteryLvl )
	if found==False :
		self.ListOfDevices[DeviceID]['Status']="004d"
		self.ListOfDevices[DeviceID]['Battery']=BatteryLvl



def UpdateDevice_v2(Unit, nValue, sValue, Options, SignalLvl, Color_ = ''):
	# V2 update Domoticz with SignaleLevel/RSSI
	Domoticz.Debug("UpdateDevice_v2 - Options = " + str(Options))
	Dzigate=eval(Options['Zigate'])

	Domoticz.Debug("UpdateDevice_v2 for : " + str(Unit) + " Signal Level = " + str(SignalLvl) )
	if isinstance(SignalLvl,int) :
		rssi= round( (SignalLvl * 12 ) / 255)
		Domoticz.Debug("UpdateDevice_v2 for : " + str(Unit) + " RSSI = " + str(rssi) )
	else:
		Domoticz.Debug("UpdateDevice_v2 for : " + str(Unit) + " SignalLvl is not an int" )
		rssi=12

	BatteryLvl=str(Dzigate['Battery'])
	if BatteryLvl == '{}' :
		BatteryLvl=255
		Domoticz.Debug("UpdateDevice_v2 for : " + str(Unit) + " BatteryLvl = " + str(BatteryLvl))

	# Make sure that the Domoticz device still exists (they can be deleted) before updating it
	if (Unit in Devices):
		if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].Color != Color_):

			if Color_:
				Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Options=str(Options), SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl) , Color = Color_)
				Domoticz.Log("Update v2 Color "+ str(Color_) +"' ("+Devices[Unit].Name+")")
			else:
				Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Options=str(Options), SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl))

			Domoticz.Log("Update v2 "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
	return

def UpdateDevice(Unit, nValue, sValue, Options):
	Dzigate=eval(Options['Zigate'])
	BatteryLvl=str(Dzigate['Battery'])
	if BatteryLvl == '{}' :
		BatteryLvl=255
	Domoticz.Debug("BatteryLvl = " + str(BatteryLvl))
	Domoticz.Debug("Options = " + str(Options))
	# Make sure that the Domoticz device still exists (they can be deleted) before updating it 
	if (Unit in Devices):
		if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
			Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Options=str(Options), BatteryLevel=int(BatteryLvl))
			Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
	return	

def ReadCluster(self, MsgData):
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
	if DeviceExist(self, MsgSrcAddr)==False :
		#Correction Thiklop : MsgSrcEp n'est pas toujours dans la ListOfDevices (?)
		#Encapsulation dans un try except pour sortir proprement
		try :
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]={}
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}
		except :
			Domoticz.Error("ReadCluster - KeyError : MsgData = " + MsgData)
			# Si le Device n'existe pas . On recoit un cluster d'un device non identifié. Il faut alors le rejeté , non ?
			return
		#Fin de la correction
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
		if MsgAttrID=="ff01" :  # xiaomi battery lvl
			MsgBattery=MsgClusterData[4:8]
			try :
				ValueBattery='%s%s' % (str(MsgBattery[2:4]),str(MsgBattery[0:2]))
				ValueBattery=round(int(ValueBattery,16)/10/3.3)
				Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=ff01 - reception batteryLVL : " + str(ValueBattery) + " pour le device addr : " +  MsgSrcAddr)
				#if self.ListOfDevices[MsgSrcAddr]['Status']=="inDB":
				#	UpdateBattery(MsgSrcAddr,ValueBattery)
				self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
			except :
				Domoticz.Error("ReadCluster - ClusterId=0000 - MsgAttrID=ff01 - reception batteryLVL : erreur de lecture pour le device addr : " +  MsgSrcAddr)
				return
		elif MsgAttrID=="0005" :  # Model info Xiaomi
			try : 
				MType=binascii.unhexlify(MsgClusterData).decode('utf-8')
				Domoticz.Debug("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device : " + MType)
				self.ListOfDevices[MsgSrcAddr]['Model']=MType
				if self.ListOfDevices[MsgSrcAddr]['Model']!= {} and self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf : # verifie que le model existe ds le fichier de conf des models
					Modeltmp=str(self.ListOfDevices[MsgSrcAddr]['Model'])
					for Ep in self.DeviceConf[Modeltmp]['Ep'] :
						if Ep in self.ListOfDevices[MsgSrcAddr]['Ep'] :
							for cluster in self.DeviceConf[Modeltmp]['Ep'][Ep] :
								if cluster not in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep] :
									self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}
						else :
							self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]={}
							for cluster in self.DeviceConf[Modeltmp]['Ep'][Ep] :
								self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}
					self.ListOfDevices[MsgSrcAddr]['Type']=self.DeviceConf[Modeltmp]['Type']
			except:
				Domoticz.Error("ReadCluster - ClusterId=0000 - MsgAttrID=0005 - Model info Xiaomi : " +  MsgSrcAddr)
				return
		else :
			Domoticz.Debug("ReadCluster - ClusterId=0000 - reception heartbeat - Message attribut inconnu : " + MsgData)
			return
	
	elif MsgClusterId=="0006" :  # (General: On/Off) xiaomi
		if MsgAttrID=="0000" or MsgAttrID=="8000":
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			Domoticz.Debug("ReadCluster - ClusterId=0006 - reception General: On/Off : " + str(MsgClusterData) )
		else :
			Domoticz.Error("ReadCluster - ClusterId=0006 - reception heartbeat - Message attribut inconnu : " + MsgData)
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
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
		return

	elif MsgClusterId=="0402" :  # (Measurement: Temperature) xiaomi
		#MsgValue=Data[len(Data)-8:len(Data)-4]
		#Correction Thiklop : onMessage' failed 'IndexError':'string index out of range'.
		if MsgClusterData != "":
			if MsgClusterData[0] == "f" :  # cas temperature negative
				MsgClusterData=-(int(MsgClusterData,16)^int("FFFF",16))
				MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
				Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )
			#Correction Thiklop 2 : cas des température > 1000°C
			#elif int(MsgClusterData,16) < 100000 : #1000 °C x 100
			else:
				MsgClusterData=int(MsgClusterData,16)
				MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(MsgClusterData/100,1)
				Domoticz.Debug("ReadCluster - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )
			#else :
			#	Domoticz.Log("Température > 1000°C")
			#Fin de correction 2
		else : 
			Domoticz.Error("ReadCluster - ClusterId=0402 - MsgClusterData vide")
		#Fin de la correction

	elif MsgClusterId=="0403" :  # (Measurement: Pression atmospherique) xiaomi   ### a corriger/modifier http://zigate.fr/xiaomi-capteur-temperature-humidite-et-pression-atmospherique-clusters/
		if MsgAttType=="0028":
			#MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgClusterData,8))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(MsgClusterData) )
			
		if MsgAttType=="0029" and MsgAttrID=="0000":
			#MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
			Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16),1)))
			
		if MsgAttType=="0029" and MsgAttrID=="0010":
			#MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/10,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/10,1)
			Domoticz.Debug("ReadCluster - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16)/10,1)))

	elif MsgClusterId=="0405" :  # (Measurement: Humidity) xiaomi
		#MsgValue=Data[len(Data)-8:len(Data)-4]
		#Correction Thiklop : le MsgClusterData n'est pas toujours un entier et est vide ?!
		#Encapsulation dans un try except pour gérer proprement le problème
		try :
			int(MsgClusterData,16)
		except :
			Domoticz.Error("ReadCluster -ClusterID=0405 - decapteur Xiamo humidité. La valeur n'est pas un entier : " + MsgClusterData)
		else :
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
			Domoticz.Debug("ReadCluster - ClusterId=0405 - reception hum : " + str(int(MsgClusterData,16)/100) )
		#Fin de correction

	elif MsgClusterId=="0406" :  # (Measurement: Occupancy Sensing) xiaomi
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
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
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(int(MsgClusterData,16) ))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=int(MsgClusterData,16)
			Domoticz.Debug("ReadCluster - ClusterId=0400 - reception LUX Sensor : " + str(int(MsgClusterData,16)) )
		#Fin de la correction
		
	elif MsgClusterId=="0012" :  # Magic Cube Xiaomi
		# Thanks to : https://github.com/dresden-elektronik/deconz-rest-plugin/issues/138#issuecomment-325101635
		#         +---+
		#         | 2 |
		#     +---+---+---+
		#     | 4 | 0 | 1 |
		#     +---+---+---+
		#         | 5 |
		#         +---+
		#         | 3 |
		#         +---+
		#     Side 5 is with the MI logo; side 3 contains the battery door.
		#
		#     Shake: 0x0000 (side on top doesn't matter)
		#     90º Flip from side x on top to side y on top: 0x0040 + (x << 3) + y
		#     180º Flip to side x on top: 0x0080 + x
		#     Push while side x is on top: 0x0100 + x
		#     Double Tap while side x is on top: 0x0200 + x
		#     Push works in any direction.
		#     For Double Tap you really need to lift the cube and tap it on the table twice.
		def cube_decode(value):
			value=int(value,16)
			if value == '' or value is None:
				return value

			if value == 0x0000 : 		
				Domoticz.Log("cube action : " + 'Shake' )
				value='10'
			elif value == 0x0002 :			
				Domoticz.Log("cube action : " + 'Wakeup' )
				value = '20'
			elif value == 0x0003 :
				Domoticz.Log("cube action : " + 'Drop' )
				value = '30'
			elif value & 0x0040 != 0 :	
				face = value ^ 0x0040
				face1 = face >> 3
				face2 = face ^ (face1 << 3)
				Domoticz.Log("cube action : " + 'Flip90_{}{}'.format(face1, face2))
				value = '40'
			elif value & 0x0080 != 0:  
				face = value ^ 0x0080
				Domoticz.Log("cube action : " + 'Flip180_{}'.format(face) )
				value = '50'
			elif value & 0x0100 != 0:  
				face = value ^ 0x0100
				Domoticz.Log("cube action : " + 'Push/Move_{}'.format(face) )
				value = '60'
			elif value & 0x0200 != 0:  # double_tap
				face = value ^ 0x0200
				Domoticz.Log("cube action : " + 'Double_tap_{}'.format(face) )
				value = '70'
			else:  
				Domoticz.Log("cube action : Not expected value" + value )
			return value

		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,cube_decode(MsgClusterData) )
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(MsgClusterData) )
		Domoticz.Debug("ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(cube_decode(MsgClusterData)) )
		
		
	elif MsgClusterId=="000c" :  # Magic Cube Xiaomi rotation and Power Meter
		Domoticz.Debug("ReadCluster - ClusterID=000C - MsgAttrID = " +str(MsgAttrID) + " value = " + str(MsgClusterData) )
		if  MsgAttrID=="0055" and MsgSrcEp == '02' : # Consomation Electrique
			Domoticz.Log("ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(round(struct.unpack('f',struct.pack('i',int(MsgClusterData,16)))[0])))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)

		elif MsgAttrID=="ff05" and MsgSrcEp == '03' : # Rotation - horinzontal
			Domoticz.Log("ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData) )
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]="80"
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,"80")
		else :
			Domoticz.Log("ReadCluster - ClusterID=000c - unknown 000c message - EP = " + str( MsgSrcEp) + " MsgAttrID = " + str(MsgAttrID) + " Value = "+ str(MsgClusterData) )
		
	else :
		Domoticz.Error("ReadCluster - Error/unknow Cluster Message : " + MsgClusterId + " for Device = " + str(MsgSrcAddr) + " Ep = " + MsgSrcEp )
		Domoticz.Error("                           MsgAttrId = " + MsgAttrID + " MsgAttType = " + MsgAttType )
		Domoticz.Error("                           MsgAttSize = " + MsgAttSize + " MsgClusterData = " + MsgClusterData )
		return

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


def CheckType(self, MsgSrcAddr) :
	Domoticz.Debug("CheckType of device : " + MsgSrcAddr)
	x=0
	found=False
	for x in Devices:
		if Devices[x].DeviceID == str(MsgSrcAddr) :
			found=True
	
	if found==False :
		#check type with domoticz device type then add or del then re add device
		self.ListOfDevices[MsgSrcAddr]['Status']="inDB"

def GetType(self, Addr, Ep) :
	if self.ListOfDevices[Addr]['Model']!={} and self.ListOfDevices[Addr]['Model'] in self.DeviceConf :  # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
		Type = self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Type']
		Domoticz.Debug("GetType - Type was set to : " + str(Type) )
	else :
		Domoticz.Log("GetType - Model not found in DeviceConf : " + str(self.ListOfDevices[Addr]['Model']) )
		Type=""
		for cluster in self.ListOfDevices[Addr]['Ep'][Ep] :
			Domoticz.Debug("GetType - Type will be set to : " + str(Type) )
			Domoticz.Debug("GetType - check Type for Cluster : " + str(cluster) )
			if Type != "" and Type[:1]!="/" :
				Type+="/"
			Type+=TypeFromCluster(cluster)
		#Type+=Type
		Type=Type.replace("/////","/")
		Type=Type.replace("////","/")
		Type=Type.replace("///","/")
		Type=Type.replace("//","/")
		if Type[:-1]=="/" :
			Type = Type[:-1]
		if Type[0:]=="/" :
			Type = Type[1:]
		if Type != "" :
			self.ListOfDevices[Addr]['Type']=Type
			Domoticz.Debug("GetType - Type is now set to : " + str(Type) )
		else :
			Domoticz.Log("GetType - WARNING - Not able to find a Type for Addr : " + str(Addr) + " Ep : " + str(Ep) + " Device Info : " + str(self.ListOfDevices[Addr]) )
	return Type

def TypeFromCluster(cluster):
	if cluster=="0405" :
		TypeFromCluster="Humi"
	elif cluster=="0406" :
		TypeFromCluster="Motion"
	elif cluster=="0400" :
		TypeFromCluster="Lux"
	elif cluster=="0403" :
		TypeFromCluster="Baro"
	elif cluster=="0402" :
		TypeFromCluster="Temp"
	elif cluster=="0006" :
		TypeFromCluster="Switch"
	elif cluster=="0500" :
		TypeFromCluster="Door"
	elif cluster=="0012" :
		TypeFromCluster="XCube"
	elif cluster=="000c" :
		TypeFromCluster="XCube"
	elif cluster=="0008" :
		TypeFromCluster="LvlControl"
	elif cluster=="0300" :
		TypeFromCluster="ColorControl"
	else :
		TypeFromCluster=""
	return TypeFromCluster

def WriteDeviceList(self, count):
	if self.HBcount>=count :
		with open(Parameters["HomeFolder"]+"DeviceList.txt", 'wt') as file:
			for key in self.ListOfDevices :
				file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
		Domoticz.Debug("Write DeviceList.txt = " + str(self.ListOfDevices))
		self.HBcount=0
	else :
		Domoticz.Debug("HB count = " + str(self.HBcount))
		self.HBcount=self.HBcount+1

def returnlen(taille , value) :
	while len(value)<taille:
		value="0"+value
	return str(value)


def Hex_Format(taille, value):
	value = hex(int(value))[2:]
	if len(value) > taille:
		return 'f' * taille
	while len(value)<taille:
		value="0"+value
	return str(value)

def CheckDeviceList(self, key, val) :
	Domoticz.Debug("CheckDeviceList - Address search : " + str(key))
	Domoticz.Debug("CheckDeviceList - with value : " + str(val))
	
	DeviceListVal=eval(val)
	if DeviceExist(self, key)==False :
		Domoticz.Debug("CheckDeviceList - Address will be add : " + str(key))
		self.ListOfDevices[key]['RIA']="10"
		self.ListOfDevices[key]['Ep']=DeviceListVal['Ep']
		if 'Type' in DeviceListVal :
			self.ListOfDevices[key]['Type']=DeviceListVal['Type']
		if 'Model' in DeviceListVal :
			self.ListOfDevices[key]['Model']=DeviceListVal['Model']
		if 'MacCapa' in DeviceListVal :
			self.ListOfDevices[key]['MacCapa']=DeviceListVal['MacCapa']
		if 'IEEE' in DeviceListVal :
			self.ListOfDevices[key]['IEEE']=DeviceListVal['IEEE']
		if 'ProfileID' in DeviceListVal :
			self.ListOfDevices[key]['ProfileID']=DeviceListVal['ProfileID']
		if 'ZDeviceID' in DeviceListVal :
			self.ListOfDevices[key]['ZDeviceID']=DeviceListVal['ZDeviceID']
		if 'Status' in DeviceListVal :
			self.ListOfDevices[key]['Status']=DeviceListVal['Status']
	return

def DisplayStatusCode( StatusCode ) :
	# As described in https://www.nxp.com/docs/en/user-guide/JN-UG-3113.pdf section 10.2

	StatusMsg=""
	if str(StatusCode)=="00" :   StatusMsg="Success"
	elif str(StatusCode)=="c1" : StatusMsg="An invalid or out-of-range parameter has been passed"
	elif str(StatusCode)=="c2" : StatusMsg="Request cannot be processed"
	elif str(StatusCode)=="c3" : StatusMsg="NLME-JOIN.request not permitted"
	elif str(StatusCode)=="c4" : StatusMsg="NLME-NETWORK-FORMATION.request failed"
	elif str(StatusCode)=="c5" : StatusMsg="NLME-DIRECT-JOIN.request failure - device already present"
	elif str(StatusCode)=="c6" : StatusMsg="NLME-SYNC.request has failed"
	elif str(StatusCode)=="c7" : StatusMsg="NLME-DIRECT-JOIN.request failure - no space in Router table"
	elif str(StatusCode)=="c8" : StatusMsg="NLME-LEAVE.request failure - device not in Neighbour table"
	elif str(StatusCode)=="c9" : StatusMsg="NLME-GET/SET.request unknown attribute identified"
	elif str(StatusCode)=="ca" : StatusMsg="NLME-JOIN.request detected no networks"
	elif str(StatusCode)=="cb" : StatusMsg="Reserved"
	elif str(StatusCode)=="cc" : StatusMsg="Security processing has failed on outgoing frame due to maximum frame counter"
	elif str(StatusCode)=="cd" : StatusMsg="Security processing has failed on outgoing frame due to no key"
	elif str(StatusCode)=="ce" : StatusMsg="Security processing has failed on outgoing frame due CCM"
	elif str(StatusCode)=="cf" : StatusMsg="Attempt at route discovery has failed due to lack of table space"
	elif str(StatusCode)=="d0" : StatusMsg="Attempt at route discovery has failed due to any reason except lack of table space"
	elif str(StatusCode)=="d1" : StatusMsg="NLDE-DATA.request has failed due to routing failure on sending device"
	elif str(StatusCode)=="d2" : StatusMsg="Broadcast or broadcast-mode multicast has failed as there is no room in BTT"
	elif str(StatusCode)=="d3" : StatusMsg="Unicast mode multi-cast frame was discarded pending route discovery"
	elif str(StatusCode)=="d4" : StatusMsg="Unicast frame does not have a route available but it is buffered for automatic resend"

	elif str(StatusCode)=="a0": StatusMsg="A transmit request failed since the ASDU is too large and fragmentation is not supported"
	elif str(StatusCode)=="a1": StatusMsg="A received fragmented frame could not be defragmented at the current time"
	elif str(StatusCode)=="a2": StatusMsg="A received fragmented frame could not be defragmented since the device does not support fragmentation"
	elif str(StatusCode)=="a3": StatusMsg="A parameter value was out of range"
	elif str(StatusCode)=="a4": StatusMsg="An APSME-UNBIND.request failed due to the requested binding link not existing in the binding table"
	elif str(StatusCode)=="a5": StatusMsg="An APSME-REMOVE-GROUP.request has been issued with a group identified that does not appear in the group table"
	elif str(StatusCode)=="a6": StatusMsg="A parameter value was invaid or out of range"
	elif str(StatusCode)=="a7": StatusMsg="An APSDE-DATA.request requesting ack transmission failed due to no ack being received"
	elif str(StatusCode)=="a8": StatusMsg="An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to there being no devices bound to this device"
	elif str(StatusCode)=="a9": StatusMsg="An APSDE-DATA.request with a destination addressing mode set to 0x03 failed due to no corresponding short address found in the address map table"
	elif str(StatusCode)=="aa": StatusMsg="An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to a binding table not being supported on the device"
	elif str(StatusCode)=="ab": StatusMsg="An ASDU was received that was secured using a link key"
	elif str(StatusCode)=="ac": StatusMsg="An ASDU was received that was secured using a network key"
	elif str(StatusCode)=="ad": StatusMsg="An APSDE-DATA.request requesting security has resulted in an error during the corresponding security processing"

	else:                       StatusMsg="Unknown code : " + StatusCode


	return StatusMsg


def decodeMacCapa ( MsgMacCapa ) :
	# MAC capability
	#     Bit 0 – Alternate PAN Coordinator
	#     Bit 1 – Device Type
	#     Bit 2 – Power source
	#     Bit 3 – Receiver On when Idle
	#     Bit 4,5 – Reserved
	#     Bit 6 – Security capability
	#     Bit 7 – Allocate Address
	# Implement the decoding of this bit field and return an 8 char array with 1 or 0 based on the MAC capabilities

	return

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
