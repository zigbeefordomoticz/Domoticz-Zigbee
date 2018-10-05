#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_database.py

	Description: Function to access Zigate Plugin Database & Dictionary

"""

import Domoticz
import z_var

def WriteDeviceList(self, Folder, count):
	if self.HBcount>=count :
		with open( Folder+"DeviceList.txt", 'wt') as file:
			for key in self.ListOfDevices :
				file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
		Domoticz.Debug("Write DeviceList.txt = " + str(self.ListOfDevices))
		self.HBcount=0
	else :
		Domoticz.Debug("HB count = " + str(self.HBcount))
		self.HBcount=self.HBcount+1


def importDeviceConf( self ) :
	#Import DeviceConf.txt
	tmpread=""
	with open( z_var.homedirectory + "DeviceConf.txt", 'r') as myfile:
		tmpread+=myfile.read().replace('\n', '')
	myfile.close()
	self.DeviceConf=eval(tmpread)

def loadListOfDevices( self, Devices ) :

	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		Domoticz.Debug("Devices["+str(x)+"].Options = "+str(Devices[x].Options) )
		ID = Devices[x].DeviceID
		self.ListOfDevices[ID]={}
		if Devices[x].Options.get('Zigate') :
			self.ListOfDevices[ID]=eval(Devices[x].Options['Zigate'])
			Domoticz.Log("Device : [" + str(x) + "] ID = " + ID + " Options['Zigate'] = " + str(self.ListOfDevices[ID]) + " loaded into self.ListOfDevices")
		else :
			Domoticz.Error("Error loading Device " +str(Devices[x]) + " not loaded in Zigate Plugin!" )


def loadListOfDevices_v3( self, Devices ) :

	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		if Devices[x].Options.get('Zigate') :
			Zigate = Devices[x].Options['Zigate']
			Zaddr = Zigate['Zaddr']

			Domoticz.Log("loadListOfDevices_v3 - IEEE = " + Devices[x].DeviceID + " Zaddr = " +Zaddr )

			self.ListOfDevices[Zaddr]={}
			self.ListOfDevices[Zaddr]=eval(Devices[x].Options['Zigate'])

			Domoticz.Log("Device : [" + str(x) + "] Zaddr = " + Zaddr + " Options['Zigate'] = " + str(self.ListOfDevices[Zaddr]) + " loaded into ListOfDevices")
		else :
			Domoticz.Error("Error loading Device " +str(Devices[x]) + " not loaded in Zigate Plugin!" )
