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

def CreateDomoDevice(self, Devices, DeviceID) :
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

	for Ep in self.ListOfDevices[DeviceID]['Ep'] :
		# Use 'type' at level EndPoint if existe
		if 'Type' in  self.ListOfDevices[DeviceID]['Ep'][Ep] :
			if self.ListOfDevices[DeviceID]['Ep'][Ep]['Type'] != "" :
				dType = self.ListOfDevices[DeviceID]['Ep'][Ep]['Type']
				aType = str(dType)
				Type = aType.split("/")
				Domoticz.Log("CreateDomoDevice -  Type via ListOfDevice: " + str(Type) + " Ep : " + str(Ep) )
		else :

			if self.ListOfDevices[DeviceID]['Type']== {} :
				Type=GetType(self, DeviceID, Ep).split("/")
				Domoticz.Log("CreateDomoDevice -  Type via GetType: " + str(Type) + " Ep : " + str(Ep) )
			else :
				Type=self.ListOfDevices[DeviceID]['Type'].split("/")
				Domoticz.Log("CreateDomoDevice - Type : '" + str(Type) + "'")

		if Type !="" :
			if "Humi" in Type and "Temp" in Type and "Baro" in Type:
				t="Temp+Hum+Baro" # Detecteur temp + Hum + Baro
				Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName=t, Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()
			if "Humi" in Type and "Temp" in Type :
				t="Temp+Hum"
				Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName=t, Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

			#For color Bulb
			if ("Switch" in Type) and ("LvlControl" in Type) and ("ColorControl" in Type):
				Type = ['ColorControl']
			elif ("Switch" in Type) and ("LvlControl" in Type):
				Type = ['LvlControl']

			for t in Type :
				Domoticz.Log("CreateDomoDevice - Device ID : " + str(DeviceID) + " Device EP : " + str(Ep) + " Type : " + str(t) )
				if t=="Temp" : # Detecteur temp
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName="Temperature", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Humi" : # Detecteur hum
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName="Humidity", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Baro" : # Detecteur Baro
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName="Barometer", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Door": # capteur ouverture/fermeture xiaomi
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=2 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Motion" :  # detecteur de presence
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=8 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="MSwitch"  :  # interrupteur multi lvl 86sw2 xiaomi
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "||||", "LevelNames": "Push|1 Click|2 Click|3 Click|4 Click", "LevelOffHidden": "false", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="DSwitch"  :  # interrupteur double sur EP different
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="DButton"  :  # interrupteur double sur EP different
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="Smoke" :  # detecteur de fumee
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=5 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Lux" :  # Lux sensors
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=246, Subtype=1 , Switchtype=0 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Switch":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=0 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Button":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=9 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Aqara" or t=="XCube" :  # Xiaomi Magic Cube
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||||||||", "LevelNames": "Off|Shake|Wakeup|Drop|90°|180°|Push|Tap|Rotation", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="Water" :  # detecteur d'eau 
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=0 , Image=11 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="Plug" :  # prise pilote
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73 , Switchtype=0 , Image=1 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="LvlControl" and self.ListOfDevices[DeviceID]['Model']=="shutter.Profalux" :  # Volet Roulant / Shutter / Blinds, let's created blindspercentageinverted devic
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73, Switchtype=16 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="LvlControl" and self.ListOfDevices[DeviceID]['Model']!="shutter.Profalux" :  # variateur de luminosite + On/off
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=244, Subtype=73, Switchtype=7 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				if t=="ColorControl" :  # variateur de couleur/luminosite/on-off
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
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

					if self.ListOfDevices[DeviceID]['Model'] == "Ampoule.LED1624G9.Tradfri":
						Subtype_ = 2
					elif self.ListOfDevices[DeviceID]['Model'] == "Ampoule.LED1545G12.Tradfri":
						Subtype_ = 8
					else:
						Subtype_ = 7

					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), Type=241, Subtype=Subtype_ , Switchtype=7 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()

				#Ajout meter
				if t=="Power" : # Will display Watt real time
					Domoticz.Log("Create Watts Usage")
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName="Usage" , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()
				if t=="Meter" : # Will display kWh
					self.ListOfDevices[DeviceID]['DomoID']=str(DeviceID)
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Log("Create kW/h Meter")
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + "-" + str(DeviceID) + "-" + str(Ep), Unit=FreeUnit(self, Devices), TypeName="kWh", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "ClusterType":t}).Create()


def MajDomoDevice(self, Devices, DeviceID,Ep,clusterID,value,Color_='') :
	Domoticz.Debug("MajDomoDevice - Device ID : " + str(DeviceID) + " - Device EP : " + str(Ep) + " - Type : " + str(clusterID)  + " - Value : " + str(value) + " - Hue : " + str(Color_))
	x=0
	Type=TypeFromCluster(clusterID)
	Domoticz.Debug("MajDomoDevice - Type = " + str(Type) )
	# As the DeviceID (Short Address) could be a new one (in comparaison to the one use at creation of the Domoticz device ), let's find the initial one.
	# Let's overwrite DeviceID
	
	if self.ListOfDevices[DeviceID].get('DomoID') :
		Domoticz.Debug("Overwrite DeviceID with the one used a CreateDomoDevice : " + str(self.ListOfDevices[DeviceID]['DomoID'] ) )
		DeviceID = self.ListOfDevices[DeviceID]['DomoID']
	
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) :
			DOptions = dict(Devices[x].Options)
			DOptions['Zigate']=dict(self.ListOfDevices[DeviceID])
			SignalLevel = self.ListOfDevices[DeviceID]['RSSI']
			Dtypename=DOptions['ClusterType']

			Domoticz.Debug("MajDomoDevices - DOptions = " + str(DOptions) )
			Domoticz.Debug("MajDomoDevices - ListOfDevices["+str(DeviceID)+"] = "+str(self.ListOfDevices[DeviceID]) )

			Domoticz.Debug("MajDomoDevice - Dtypename = " + str(Dtypename) )
	
			# Instant Watts. 
			# PowerMeter is for Compatibility , as it was created as a PowerMeter device.
			if ( Dtypename=="Power" or Dtypename=="PowerMeter") and clusterID == "000c": 
				nValue=float(value)
				sValue=value
				Domoticz.Debug("MajDomoDevice Power : " + sValue)
				UpdateDevice_v2(Devices, x,nValue,str(sValue),DOptions, SignalLevel)								

			if Dtypename=="Meter" and clusterID == "000c": # kWh
				nValue=float(value)
				sValue=str(float(value))
				Domoticz.Debug("MajDomoDevice Power : " + sValue)
				UpdateDevice_v2(Devices, x,0, str(nValue)+";"+sValue, DOptions, SignalLevel)								

			if Dtypename=="Temp+Hum+Baro" : #temp+hum+Baro xiaomi
				Bar_forecast = '0' # Set barometer forecast to 0 (No info)
				if Type=="Temp" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2] , SplitData[3], Bar_forecast)
					Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),DOptions, SignalLevel)								
				if Type=="Humi" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], str(value) ,  SplitData[2] , SplitData[3], Bar_forecast)
					Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),DOptions, SignalLevel)								
				if Type=="Baro" :  # barometer
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					valueBaro='%s;%s;%s;%s;%s' % (SplitData[0], SplitData[1], str(value) , SplitData[3], Bar_forecast)
					UpdateDevice_v2(Devices, x,0,str(valueBaro),DOptions, SignalLevel)								
			if Dtypename=="Temp+Hum" : #temp+hum xiaomi
				if Type=="Temp" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
					Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),DOptions, SignalLevel)								
				if Type=="Humi" :
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
					Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
					UpdateDevice_v2(Devices, x,0,str(NewSvalue),DOptions, SignalLevel)								
			if Type==Dtypename=="Temp" :  # temperature
				UpdateDevice_v2(Devices, x,0,str(value),DOptions, SignalLevel)								
			if Type==Dtypename=="Humi" :   # humidite
				UpdateDevice_v2(Devices, x,int(value),"0",DOptions, SignalLevel)								
			if Type==Dtypename=="Baro" :  # barometre
				CurrentnValue=Devices[x].nValue
				CurrentsValue=Devices[x].sValue
				Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
				SplitData=CurrentsValue.split(";")
				valueBaro='%s;%s' % (value,SplitData[0])
				UpdateDevice_v2(Devices, x,0,str(valueBaro),DOptions, SignalLevel)
			if Type=="Door" and Dtypename=="Door" :  # Door / Window
				if value == "01" :
					state="Open"
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
				elif value == "00" :
					state="Closed"
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
			if Dtypename=="Plug" and Type=="Switch" :
				if value == "01" :
					UpdateDevice_v2(Devices, x,1,"On",DOptions, SignalLevel)
				elif value == "00" :
					state="Off"
					UpdateDevice_v2(Devices, x,0,"Off",DOptions, SignalLevel)

			if Type=="Switch" and Dtypename=="Door" :  # porte / fenetre
				if value == "01" :
					state="Open"
					#Correction Thiklop : value n'est pas toujours un entier. Exécution de l'updatedevice dans le test
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
				elif value == "00" :
					state="Closed"
					#Correction Thiklop : idem
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
					#Fin de la correction
			if Type==Dtypename=="Switch" : # switch simple
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="Button": # boutton simple
				if value == "01" :
					state="On"
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
				else:
					return
			if Type=="Switch" and Dtypename=="Water" : # detecteur d eau
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
			if Type=="Switch" and Dtypename=="Smoke" : # detecteur de fume
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
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
				UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
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
				UpdateDevice_v2(Devices, x,int(data),str(state),DOptions, SignalLevel)
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
				UpdateDevice_v2(Devices, x,int(data),str(state),DOptions, SignalLevel)

			if Type=="XCube" and Dtypename=="Aqara" and Ep == "02": #Magic Cube Acara 
					Domoticz.Debug("MajDomoDevice - XCube update device with data = " + str(value) )
					UpdateDevice_v2( Devices, x, int(value), str(value), DOptions, SignalLevel )

			if Type=="XCube" and Dtypename=="Aqara" and Ep == "03": #Magic Cube Acara Rotation
					Domoticz.Debug("MajDomoDevice - XCube update device with data = " + str(value) )
					UpdateDevice_v2( Devices, x, int(value), str(value), DOptions, SignalLevel )

			if Type==Dtypename=="XCube" and Ep == "02":  # cube xiaomi
				if value == "0000" : #shake
					state="10"
					data="01"
					UpdateDevice_v2( Devices, x, int(data), str(state), DOptions, SignalLevel )
				elif value == "0204" or value == "0200" or value == "0203" or value == "0201" or value == "0202" or value == "0205": #tap
					state="50"
					data="05"
					UpdateDevice_v2( Devices, x, int(data), str(state), DOptions, SignalLevel )
				elif value == "0103" or value == "0100" or value == "0104" or value == "0101" or value == "0102" or value == "0105": #Slide
					state="20"
					data="02"
					UpdateDevice_v2( Devices, x, int(data), str(state), DOptions, SignalLevel )
				elif value == "0003" : #Free Fall
					state="70"
					data="07"
					UpdateDevice_v2( Devices, x, int(data), str(state), DOptions, SignalLevel )
				elif value >= "0004" and value <= "0059": #90°
					state="30"
					data="03"
					UpdateDevice_v2( Devices, x, int(data), str(state), DOptions, SignalLevel )
				elif value >= "0060" : #180°
					state="90"
					data="09"
					UpdateDevice_v2( Devices, x, int(data), str(state), DOptions, SignalLevel )

			if Type==Dtypename=="Lux" :
				UpdateDevice_v2(Devices, x,int(value),str(value),DOptions, SignalLevel)
			if Type==Dtypename=="Motion" :
				#Correction Thiklop : value pas toujours un entier :
				#'onMessage' failed 'ValueError':'invalid literal for int() with base 10: '00031bd000''.
				# UpdateDevice dans le if
				if value == "01" :
					state="On"
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
				elif value == "00" :
					state="Off"
					UpdateDevice_v2(Devices, x,int(value),str(state),DOptions, SignalLevel)
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
						UpdateDevice_v2(Devices, x, str(nValue), str(sValue) ,DOptions, SignalLevel)

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
					UpdateDevice_v2(Devices, x, str(nValue), str(sValue) ,DOptions, SignalLevel, Color_)

			#Modif Meter PP 09/09/2018 Je pense que c'est inutile car on a le test sur Dtypename==PowerMeter qui est plus pertinant
			#if clusterID=="000c" and Type != "XCube":
			#	Domoticz.Debug("Update Value Meter : "+str(round(struct.unpack('f',struct.pack('i',int(value,16)))[0])))
			#	UpdateDevice_v2(Devices, x, 0, str(round(struct.unpack('f',struct.pack('i',int(value,16)))[0])) ,DOptions, SignalLevel)

def ResetDevice(self, Devices, Type,HbCount) :
	x=0
	for x in Devices:
		LUpdate=Devices[x].LastUpdate
		_tmpDeviceID = Devices[x].DeviceID
		LUpdate=time.mktime(time.strptime(LUpdate,"%Y-%m-%d %H:%M:%S"))
		current = time.time()
		DOptions = dict(Devices[x].Options)
		Dtypename=DOptions['ClusterType']
		try :
			SignalLevel = self.ListOfDevices[_tmpDeviceID]['RSSI']
		except:
			SignalLevel = 15

		if (current-LUpdate)> 30 and Dtypename=="Motion":
			Domoticz.Debug("Last update of the devices " + str(x) + " was : " + str(LUpdate)  + " current is : " + str(current) + " this was : " + str(current-LUpdate) + " secondes ago")
			UpdateDevice_v2(Devices, x, 0, "Off" ,DOptions, SignalLevel)
	return
			
def UpdateDevice_v2(Devices, Unit, nValue, sValue, Options, SignalLvl, Color_ = ''):
	# V2 update Domoticz with SignaleLevel/RSSI
	Zigate=Options['Zigate']
	t=Options['ClusterType']

	Domoticz.Debug("UpdateDevice_v2 - ClusterType = " + str(t))
	Domoticz.Debug("UpdateDevice_v2 - Zigate = " + str(Zigate))
	Dzigate=eval(str(Options['Zigate']))

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
		if ( Devices[Unit].BatteryLevel != BatteryLvl ) or ( Devices[Unit].SignalLevel != rssi ) :    # In that case we do update, but do not trigger any notification.
			tmpZigate={}
			tmpZigate=Options['Zigate']
			tmpClusterType=Options['ClusterType']
			Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Options={"Zigate":str(tmpZigate),"ClusterType":tmpClusterType}, SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), SuppressTriggers=True)
			Domoticz.Log("Update v2 SignalLevel: "+str(rssi)+":' BatteryLevel: "+str(BatteryLvl)+"' ("+Devices[Unit].Name+")")
		elif (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].Color != Color_):
			tmpZigate={}
			tmpZigate=Options['Zigate']
			tmpClusterType=Options['ClusterType']
			if Color_:
				Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Options={"Zigate":str(tmpZigate),"ClusterType":tmpClusterType}, SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl) , Color = Color_)
				Domoticz.Log("Update v2 Color "+ str(Color_) +"' ("+Devices[Unit].Name+")")
			else:
				Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Options={"Zigate":str(tmpZigate),"ClusterType":tmpClusterType}, SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl))
				Domoticz.Log("Update v2 "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")


	return


def GetType(self, Addr, Ep) :
	Type =""
	if self.ListOfDevices[Addr]['Model']!={} and self.ListOfDevices[Addr]['Model'] in self.DeviceConf :  # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
		if 'Type' in  self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep] :
			if self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Ep'][Ep]['Type'] != "" :
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
