#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_domoticz.py

	Description: All interactions with Domoticz 

"""

import Domoticz
import binascii
import time
import struct
import json

def CreateDomoDevice(self, Devices, NWKID) :
	def getCreatedID( self, Devices, DeviceID, Name ) :
		for x in Devices :
			Domoticz.Log( Devices[x].DeviceID + " / " + DeviceID + " ----- " + Devices[x].Name + " / " +self.Key+" - "+Name )
			if Devices[x].DeviceID == DeviceID and Devices[x].Name.find(Name) >= 0 :
				Domoticz.Log("getCreatedID - found " +str(Devices[x].ID) )
				return Devices[x].ID

	def FreeUnit(self, Devices) :
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

	
	if NWKID == '' :
		Domoticz.Error("CreateDomoDevice - Cannot create a Device without an IEEE ." )
		return

	if NWKID not in self.ListOfDevices :
		Domoticz.Error("CreateDomoDevice - Cannot find a IEEE for this NWKID " +str(NWKID) )
		return

	DeviceID_IEEE = self.ListOfDevices[NWKID]['IEEE']

	# When Type is at Global level, then we create all Type against the 1st EP
	# If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
	GlobalEP = False
	for Ep in self.ListOfDevices[NWKID]['Ep'] :
		# Use 'type' at level EndPoint if existe
		Domoticz.Log("CreatDomoDevice - Process EP : " +str(Ep) )
		if not GlobalEP :								# First time, or we dont't GlobalType
			if 'Type' in  self.ListOfDevices[NWKID]['Ep'][Ep] :
				if self.ListOfDevices[NWKID]['Ep'][Ep]['Type'] != "" :
					dType = self.ListOfDevices[NWKID]['Ep'][Ep]['Type']
					aType = str(dType)
					Type = aType.split("/")
					Domoticz.Log("CreateDomoDevice -  Type via ListOfDevice: " + str(Type) + " Ep : " + str(Ep) )
			else :
				if self.ListOfDevices[NWKID]['Type']== {} :
					Type=GetType(self, NWKID, Ep).split("/")
					Domoticz.Log("CreateDomoDevice -  Type via GetType: " + str(Type) + " Ep : " + str(Ep) )
				else :
					GlobalEP = True
					Type=self.ListOfDevices[NWKID]['Type'].split("/")
					Domoticz.Log("CreateDomoDevice - Type : '" + str(Type) + "'")
		else :
			break									# We have created already the Devices (as GlobalEP is set)
	
		if not self.ListOfDevices[NWKID]['Ep'][Ep].get('ClusterType') :
			self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'] = {}

		if Type !="" :
			if "Humi" in Type and "Temp" in Type and "Baro" in Type:
				t="Temp+Hum+Baro" # Detecteur temp + Hum + Baro

				unit = FreeUnit(self, Devices)
				Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName=t ).Create()
				ID = Devices[unit].ID
				self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

			if "Humi" in Type and "Temp" in Type :
				t="Temp+Hum"
				unit = FreeUnit(self, Devices)
				Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName=t ).Create()
				ID = Devices[unit].ID
				self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

			#For color Bulb
			if ("Switch" in Type) and ("LvlControl" in Type) and ("ColorControl" in Type):
				Type = ['ColorControl']
			elif ("Switch" in Type) and ("LvlControl" in Type):
				Type = ['LvlControl']

			for t in Type :
				Domoticz.Log("CreateDomoDevice - Device ID : " + str(DeviceID_IEEE) + " Device EP : " + str(Ep) + " Type : " + str(t) )
				if t=="Temp" : # Detecteur temp
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName="Temperature" ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Humi" : # Detecteur hum
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName="Humidity" ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Baro" : # Detecteur Baro
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName="Barometer" ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Door": # capteur ouverture/fermeture xiaomi
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=2 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Motion" :  # detecteur de presence
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=8 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="MSwitch"  :  # interrupteur multi lvl 86sw2 xiaomi
					self.ListOfDevices[NWKID]['Status']="inDB"
					Options = {"LevelActions": "||||", "LevelNames": "Push|1 Click|2 Click|3 Click|4 Click", "LevelOffHidden": "false", "SelectorStyle": "0"}
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="DSwitch"  :  # interrupteur double sur EP different
					self.ListOfDevices[NWKID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0"}
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="DButton"  :  # interrupteur double sur EP different
					self.ListOfDevices[NWKID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0"}
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Smoke" :  # detecteur de fumee
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=5).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Lux" :  # Lux sensors
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=246, Subtype=1 , Switchtype=0 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Switch":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=0 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Button":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=9).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Aqara" or t=="XCube" :  # Xiaomi Magic Cube
					self.ListOfDevices[NWKID]['Status']="inDB"
					Options = {"LevelActions": "|||||||||", "LevelNames": "Off|Shake|Wakeup|Drop|90°|180°|Push|Tap|Rotation", "LevelOffHidden": "true", "SelectorStyle": "0"}
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Water" :  # detecteur d'eau 
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=0 , Image=11 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Plug" :  # prise pilote
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73 , Switchtype=0 , Image=1 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="LvlControl" and self.ListOfDevices[NWKID]['Model']=="shutter.Profalux" :  # Volet Roulant / Shutter / Blinds, let's created blindspercentageinverted devic
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73, Switchtype=16 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="LvlControl" and self.ListOfDevices[NWKID]['Model']!="shutter.Profalux" :  # variateur de luminosite + On/off
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=244, Subtype=73, Switchtype=7 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="ColorControl" :  # variateur de couleur/luminosite/on-off
					self.ListOfDevices[NWKID]['Status']="inDB"
					# Type 0xF1	pTypeColorSwitch

					#SubType sTypeColor_RGB_W				0x01 // RGB + white, either RGB or white can be lit
					#SubType sTypeColor_RGB				  0x02 // RGB
					#SubType sTypeColor_White				0x03 // Monochrome white
					#SubType sTypeColor_RGB_CW_WW			0x04 // RGB + cold white + warm white, either RGB or white can be lit
					#SubType sTypeColor_LivCol			   0x05
					#SubType sTypeColor_RGB_W_Z			  0x06 // Like RGBW, but allows combining RGB and white
					#SubType sTypeColor_RGB_CW_WW_Z		  0x07 // Like RGBWW, but allows combining RGB and white
					#SubType sTypeColor_CW_WW				0x08 // Cold white + Warm white

					# Switchtype 7 STYPE_Dimmer

					if self.ListOfDevices[NWKID]['Model'] == "Ampoule.LED1624G9.Tradfri":
						Subtype_ = 2
					elif self.ListOfDevices[NWKID]['Model'] == "Ampoule.LED1545G12.Tradfri":
						Subtype_ = 8
					else:
						Subtype_ = 7

					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, Type=241, Subtype=Subtype_ , Switchtype=7 ).Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				#Ajout meter
				if t=="Power" : # Will display Watt real time
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName="Usage").Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t

				if t=="Meter" : # Will display kWh
					self.ListOfDevices[NWKID]['Status']="inDB"
					unit = FreeUnit(self, Devices)
					Domoticz.Device(DeviceID=str(DeviceID_IEEE),Name=str(t) + "-" + str(DeviceID_IEEE) + "-" + str(Ep), Unit=unit, TypeName="kWh").Create()
					ID = Devices[unit].ID
					self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID )] = t


def MajDomoDevice(self, Devices, NWKID, Ep, clusterID, value, Color_='') :

	# Starting V3
	# DeviceID => NWK@
	# We must talk to Domoticz with IEEE

	DeviceID_IEEE= self.ListOfDevices[NWKID]['IEEE']

	Domoticz.Debug("MajDomoDevice - Device ID : " + str(DeviceID_IEEE) + " - Device EP : " + str(Ep) + " - Type : " + str(clusterID)  + " - Value : " + str(value) + " - Hue : " + str(Color_))

	Type=TypeFromCluster(clusterID)
	Domoticz.Debug("MajDomoDevice - Type = " + str(Type) )

	x=0
	for x in Devices:
		if Devices[x].DeviceID == DeviceID_IEEE :
			Domoticz.Debug("MajDomoDevice - NWKID = " +str(NWKID) + " IEEE = " +str(DeviceID_IEEE) + " Unit = " +str(Devices[x].ID) )
	
			ID = Devices[x].ID
			Dtypename = ""
			Domoticz.Debug("MajDomoDevice - " +str(self.ListOfDevices[NWKID]['Ep'][Ep]) )
		
			if self.ListOfDevices[NWKID].get('ClusterType') :		# We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
				Domoticz.Debug("MajDomoDevice - search ClusterType in : " +str(self.ListOfDevices[NWKID]['ClusterType']) + " for : " +str(ID) )
				Dtypename=self.ListOfDevices[NWKID]['ClusterType'][str(ID)]
			else :
				# Are we in a situation with one Devices whatever Eps are ?
				# To do that, check there is only 1 ClusterType even if several EPs
				nbClusterType = 0
				for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
					if self.ListOfDevices[NWKID]['Ep'][tmpEp].get('ClusterType') :
						nbClusterType = nbClusterType + 1
						ptEP = tmpEp

				Domoticz.Debug("MajDomoDevice - We have " +str(nbClusterType) + " EPs with ClusterType" )
				
				if nbClusterType == 1 :		# All Updates are redirected to the same EP
					# We must redirect all to the EP where there is a ClusterType
					# ptEP is be the Only  EP where we have found ClusterType
					for key  in self.ListOfDevices[NWKID]['Ep'][ptEP]['ClusterType'] :
						if str(ID) == str(key) :
							Dtypename=str(self.ListOfDevices[NWKID]['Ep'][ptEP]['ClusterType'][key])
				
				else :
					Domoticz.Debug("MajDomoDevice - search ClusterType in : " +str(self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType']) + " for : " +str(ID) )
					for key  in self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'] :
						if str(ID) == str(key) :
							Dtypename=str(self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][key])

			if Dtypename == "" :	# No match with ClusterType
				continue

			Domoticz.Debug("MajDomoDevice - Dtypename    = " + str(Dtypename) )

			if self.ListOfDevices[NWKID]['RSSI'] != 0 :
				SignalLevel = self.ListOfDevices[NWKID]['RSSI']
			else : SignalLevel = 15
			if self.ListOfDevices[NWKID]['Battery'] != '' :
				BatteryLevel =  self.ListOfDevices[NWKID]['Battery']
			else :
				BatteryLevel = 255

			# Instant Watts. 
			# PowerMeter is for Compatibility , as it was created as a PowerMeter device.
			if ( Dtypename=="Power" or Dtypename=="PowerMeter") and clusterID == "000c": 
				nValue=float(value)
				sValue=value
				Domoticz.Debug("MajDomoDevice Power : " + sValue)
				UpdateDevice_v2(Devices, x,nValue,str(sValue),BatteryLevel, SignalLevel)								

			if Dtypename=="Meter" and clusterID == "000c": # kWh
				nValue=float(value)
				sValue=str(float(value))
				Domoticz.Debug("MajDomoDevice Power : " + sValue)
				UpdateDevice_v2(Devices, x,0, str(nValue)+";"+sValue, BatteryLevel, SignalLevel)								

			if Dtypename=="Temp+Hum+Baro" : #temp+hum+Baro xiaomi
				Bar_forecast = '0' # Set barometer forecast to 0 (No info)
				if Type=="Temp" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2] , SplitData[3], Bar_forecast)
					Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),BatteryLevel, SignalLevel)								
				if Type=="Humi" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], str(value) ,  SplitData[2] , SplitData[3], Bar_forecast)
					Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),BatteryLevel, SignalLevel)								
				if Type=="Baro" :  # barometer
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					valueBaro='%s;%s;%s;%s;%s' % (SplitData[0], SplitData[1], str(value) , SplitData[3], Bar_forecast)
					UpdateDevice_v2(Devices, x,0,str(valueBaro),BatteryLevel, SignalLevel)								
			if Dtypename=="Temp+Hum" : #temp+hum xiaomi
				if Type=="Temp" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
					Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),BatteryLevel, SignalLevel)								
				if Type=="Humi" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
					Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),BatteryLevel, SignalLevel)								
			if Type==Dtypename=="Temp" :  # temperature
				UpdateDevice_v2(Devices, x,0,str(value),BatteryLevel, SignalLevel)								
			if Type==Dtypename=="Humi" :   # humidite
				UpdateDevice_v2(Devices, x,int(value),"0",BatteryLevel, SignalLevel)								
			if Type==Dtypename=="Baro" :  # barometre
				CurrentnValue=Devices[x].nValue
				CurrentsValue=Devices[x].sValue
				Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
				SplitData=CurrentsValue.split(";")
				valueBaro='%s;%s' % (value,SplitData[0])
				UpdateDevice_v2(Devices, x,0,str(valueBaro),BatteryLevel, SignalLevel)
			if Type=="Door" and Dtypename=="Door" :  # Door / Window
				if value == "01" :
					state="Open"
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
				elif value == "00" :
					state="Closed"
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
			if Dtypename=="Plug" and Type=="Switch" :
				if value == "01" :
					UpdateDevice_v2(Devices, x,1,"On",BatteryLevel, SignalLevel)
				elif value == "00" :
					state="Off"
					UpdateDevice_v2(Devices, x,0,"Off",BatteryLevel, SignalLevel)

			if Type=="Switch" and Dtypename=="Door" :  # porte / fenetre
				if value == "01" :
					state="Open"
					#Correction Thiklop : value n'est pas toujours un entier. Exécution de l'updatedevice dans le test
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
				elif value == "00" :
					state="Closed"
					#Correction Thiklop : idem
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
					#Fin de la correction
			if Type==Dtypename=="Switch" : # switch simple
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
			if Type=="Switch" and Dtypename=="Button": # boutton simple
				if value == "01" :
					state="On"
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
				else:
					return
			if Type=="Switch" and Dtypename=="Water" : # detecteur d eau
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
			if Type=="Switch" and Dtypename=="Smoke" : # detecteur de fume
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
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
				UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
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
				UpdateDevice_v2(Devices, x,int(data),str(state),BatteryLevel, SignalLevel)
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
				UpdateDevice_v2(Devices, x,int(data),str(state),BatteryLevel, SignalLevel)

			if Type=="XCube" and Dtypename=="Aqara" and Ep == "02": #Magic Cube Acara 
					Domoticz.Debug("MajDomoDevice - XCube update device with data = " + str(value) )
					UpdateDevice_v2( Devices, x, int(value), str(value), BatteryLevel, SignalLevel )

			if Type=="XCube" and Dtypename=="Aqara" and Ep == "03": #Magic Cube Acara Rotation
					Domoticz.Debug("MajDomoDevice - XCube update device with data = " + str(value) )
					UpdateDevice_v2( Devices, x, int(value), str(value), BatteryLevel, SignalLevel )

			if Type==Dtypename=="XCube" and Ep == "02":  # cube xiaomi
				if value == "0000" : #shake
					state="10"
					data="01"
					UpdateDevice_v2( Devices, x, int(data), str(state), BatteryLevel, SignalLevel )
				elif value == "0204" or value == "0200" or value == "0203" or value == "0201" or value == "0202" or value == "0205": #tap
					state="50"
					data="05"
					UpdateDevice_v2( Devices, x, int(data), str(state), BatteryLevel, SignalLevel )
				elif value == "0103" or value == "0100" or value == "0104" or value == "0101" or value == "0102" or value == "0105": #Slide
					state="20"
					data="02"
					UpdateDevice_v2( Devices, x, int(data), str(state), BatteryLevel, SignalLevel )
				elif value == "0003" : #Free Fall
					state="70"
					data="07"
					UpdateDevice_v2( Devices, x, int(data), str(state), BatteryLevel, SignalLevel )
				elif value >= "0004" and value <= "0059": #90°
					state="30"
					data="03"
					UpdateDevice_v2( Devices, x, int(data), str(state), BatteryLevel, SignalLevel )
				elif value >= "0060" : #180°
					state="90"
					data="09"
					UpdateDevice_v2( Devices, x, int(data), str(state), BatteryLevel, SignalLevel )

			if Type==Dtypename=="Lux" :
				UpdateDevice_v2(Devices, x,int(value),str(value),BatteryLevel, SignalLevel)
			if Type==Dtypename=="Motion" :
				#Correction Thiklop : value pas toujours un entier :
				#'onMessage' failed 'ValueError':'invalid literal for int() with base 10: '00031bd000''.
				# UpdateDevice dans le if
				if value == "01" :
					state="On"
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
				elif value == "00" :
					state="Off"
					UpdateDevice_v2(Devices, x,int(value),str(state),BatteryLevel, SignalLevel)
				#Fin de correction

			if Type==Dtypename=="LvlControl" :
				try:
					sValue =  round((int(value,16)/255)*100)
				except:
					Domoticz.Error("MajDomoDevice - value is not an int = " + str(value) )
				else:
					Domoticz.Debug("MajDomoDevice LvlControl - DvID : " + str(DeviceID_IEEE) + " - Device EP : " + str(Ep) + " - Value : " + str(sValue) + " sValue : " + str(Devices[x].sValue) )

					nValue = 2
					
					if str(nValue) != str(Devices[x].nValue) or str(sValue) != str(Devices[x].sValue) :
						Domoticz.Debug("MajDomoDevice update DevID : " + str(DeviceID_IEEE) + " from " + str(Devices[x].nValue) + " to " + str(nValue) )
						UpdateDevice_v2(Devices, x, str(nValue), str(sValue) ,BatteryLevel, SignalLevel)

			if Type==Dtypename=="ColorControl" :
				try:
					sValue =  round((int(value,16)/255)*100)
				except:
					Domoticz.Error("MajDomoDevice - value is not an int = " + str(value) )
				else:
					Domoticz.Debug("MajDomoDevice ColorControl - DvID : " + str(DeviceID_IEEE) + " - Device EP : " + str(Ep) + " - Value : " + str(sValue) + " sValue : " + str(Devices[x].sValue) )
			
				nValue = 2
			
				if str(nValue) != str(Devices[x].nValue) or str(sValue) != str(Devices[x].sValue) or str(Color_) != str(Devices[x].Color):
					Domoticz.Debug("MajDomoDevice update DevID : " + str(DeviceID_IEEE) + " from " + str(Devices[x].nValue) + " to " + str(nValue))
					UpdateDevice_v2(Devices, x, str(nValue), str(sValue) ,BatteryLevel, SignalLevel, Color_)

			#Modif Meter PP 09/09/2018 Je pense que c'est inutile car on a le test sur Dtypename==PowerMeter qui est plus pertinant
			#if clusterID=="000c" and Type != "XCube":
			#	Domoticz.Debug("Update Value Meter : "+str(round(struct.unpack('f',struct.pack('i',int(value,16)))[0])))
			#	UpdateDevice_v2(Devices, x, 0, str(round(struct.unpack('f',struct.pack('i',int(value,16)))[0])) ,BatteryLevel, SignalLevel)

def ResetDevice(self, Devices, Type, HbCount) :
	'''
		Reset all Devices from the ClusterType Motion after 30s
	'''

	Domoticz.Debug("ResetDevice : " +str(HbCount) )
	x=0
	for x in Devices:
		LUpdate=Devices[x].LastUpdate
		_tmpDeviceID_IEEE = Devices[x].DeviceID
		LUpdate=time.mktime(time.strptime(LUpdate,"%Y-%m-%d %H:%M:%S"))
		current = time.time()
		# Look for the corresponding ClusterType
		if _tmpDeviceID_IEEE in  self.IEEE2NWK :
			NWKID = self.IEEE2NWK[_tmpDeviceID_IEEE]
			if NWKID not in self.ListOfDevices :
				Domoticz.Error("ResetDevice " +str(NWKID) + " not found in " +str(self.ListOfDevices) )
				continue

			ID = Devices[x].ID
			Domoticz.Debug("ResetDevice - Processing ID = " +str(ID) ) 

			Dtypename=''
			for tmpEp in  self.ListOfDevices[NWKID]['Ep'] :
				if  self.ListOfDevices[NWKID]['Ep'][tmpEp].get('ClusterType') :
					if  str(ID) in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'] :
						Dtypename=self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][str(ID)]
						Domoticz.Debug("ResetDevice - Found ClusterType in EP["+str(tmpEp)+"] : " +str(Dtypename) + " for Device :" + str(ID) )
			if Dtypename == '' :
				if self.ListOfDevices[NWKID].get('ClusterType') : 
					if str(ID) in self.ListOfDevices[NWKID]['ClusterType'] :
						Dtypename=self.ListOfDevices[NWKID]['ClusterType'][str(ID)]
						Domoticz.Debug("ResetDevice - Found ClusterType : " +str(Dtypename) + " for Device : " + str(ID) )
			else :
				Domoticz.Debug("ResetDevice - No ClusterType found for this device : " +str(ID) + " in " +str(self.ListOfDevices[NWKID]) )


			Domoticz.Debug("ResetDevice - ID = " +str(ID) + " ClusterType : " +str(Dtypename) ) 
			# Takes the opportunity to update RSSI and Battery
			if self.ListOfDevices[NWKID].get('RSSI') : 
				SignalLevel = self.ListOfDevices[NWKID]['RSSI']
			if self.ListOfDevices[NWKID].get('Battery') : 
				BatteryLevel = self.ListOfDevices[NWKID]['Battery']

			Domoticz.Debug("ResetDevice - Time delat since Last update : "+str( current - LUpdate) )
		
			if (current - LUpdate)> 30 and Dtypename=="Motion":
				Domoticz.Debug("Last update of the devices " + str(x) + " was : " + str(LUpdate)  + " current is : " + str(current) + " this was : " + str(current-LUpdate) + " secondes ago")
				UpdateDevice_v2(Devices, x, 0, "Off" ,BatteryLevel, SignalLevel, SuppTrigger=True)
	return
			
def UpdateDevice_v2(Devices, Unit, nValue, sValue, BatteryLvl, SignalLvl, Color_ = '', SuppTrigger=False ):

	Domoticz.Debug("UpdateDevice_v2 for : " + str(Unit) + " Battery Level = " + str(BatteryLvl) + " Signal Level = " + str(SignalLvl) )
	if isinstance(SignalLvl,int) :
		rssi= round( (SignalLvl * 12 ) / 255)
		Domoticz.Debug("UpdateDevice_v2 for : " + str(Unit) + " RSSI = " + str(rssi) )
	else :
		rssi=12

	if not isinstance(BatteryLvl,int) or BatteryLvl == '' :
		BatteryLvl = 255

	# Make sure that the Domoticz device still exists (they can be deleted) before updating it
	if (Unit in Devices):
		if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].Color != Color_):
			if Color_: Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Color = Color_, SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl) )
			else:      
				if SuppTrigger :
					Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue) , SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), SuppressTrigger=True )
				else :
					Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue) , SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl) )
			Domoticz.Log("Update v2 Values "+str(nValue)+":'"+str(sValue)+":"+ str(Color_)+"' ("+Devices[Unit].Name+")")

		elif ( Devices[Unit].BatteryLevel != BatteryLvl and BatteryLvl != 255) or ( Devices[Unit].SignalLevel != rssi ) :    # In that case we do update, but do not trigger any notification.
			Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), SuppressTriggers=True)
			Domoticz.Log("Update v2 SignalLevel: "+str(rssi)+":' BatteryLevel: "+str(BatteryLvl)+"' ("+Devices[Unit].Name+")")

	return


def GetType(self, Addr, Ep) :
	Type =""
	Domoticz.Log("GetType - Model " +str(self.ListOfDevices[Addr]['Model']) )

	if self.ListOfDevices[Addr]['Model']!={} and self.ListOfDevices[Addr]['Model'] in self.DeviceConf :  # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
		if 'Type' in  self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep] :
			if self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type'] != "" :
				Domoticz.Log("GetType - Found Type  " +str(self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type']) )
				Type = self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type']
				Type = str(Type)
		else :
			Type = self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Type']

		Domoticz.Debug("GetType - Type was set to : " + str(Type) )
	else :
		Domoticz.Debug("GetType - Model not found in DeviceConf : " + str(self.ListOfDevices[Addr]['Model']) )
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
