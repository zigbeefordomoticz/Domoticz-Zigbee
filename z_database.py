#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_database.py

	Description: Function to access Zigate Plugin Database & Dictionary

"""

import Domoticz
import z_var
import z_tools


def LoadDeviceList(self ):
	# Load DeviceList.txt into ListOfDevices
	#
	Domoticz.Log("DeviceList filename : " +self.DeviceListName )
	status = 'Success'
	with open( DeviceListName , 'r') as myfile2:
		Domoticz.Log( DeviceListName + " open ")
		for line in myfile2:
			(key, val) = line.split(":",1)
			key = key.replace(" ","")
			key = key.replace("'","")

			if self.ListOfDevices[key]['Version'] != '3' :
				Domoticz.Error("LoadDeviceList - entry " +key +" not loaded - not Version 3 - " +str(dlVal) )
				status = 'Failed'
			else :
				# CheckDevceList will create an entry in ListOfDevices. 
				z_tools.CheckDeviceList(self, key, val)
				self.ListOfDevices[key]['Heartbeat'] = 0			# Reset heartbeat counter to 0
	myfile2.close()
	return status


def WriteDeviceList(self, Folder, count):
	if self.HBcount>=count :
		Domoticz.Log("Write " + self.DeviceListName + " = " + str(self.ListOfDevices))
		with open( self.DeviceListName , 'wt') as file:
			for key in self.ListOfDevices :
				file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
		self.HBcount=0
		file.close()
	else :
		Domoticz.Debug("HB count = " + str(self.HBcount))
		self.HBcount=self.HBcount+1


def importDeviceConf( self ) :
	#Import DeviceConf.txt
	tmpread=""
	with open( z_var.homedirectory + "DeviceConf.txt", 'r') as myfile:
		tmpread+=myfile.read().replace('\n', '')
	self.DeviceConf=eval(tmpread)
	myfile.close()


def importPluginConf( self ) :
	# Import PluginConf.txt
	tmpPluginConf=""
	with open(Parameters["HomeFolder"]+"PluginConf.txt", 'r') as myPluginConfFile:
		tmpPluginConf+=myPluginConfFile.read().replace('\n', '')
	myPluginConfFile.close()
	Domoticz.Debug("PluginConf.txt = " + str(tmpPluginConf))
	self.PluginConf=eval(tmpPluginConf)

def checkListOfDevice2Devices( self, Devices ) :

	# As of V3 we will be loading only the IEEE information as that is the only one existing in Domoticz area.
	# It is also expected that the ListOfDevices is already loaded.

	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		ID = Devices[x].DeviceID
		found = False
		for key in self.ListOfDevices :
			if self.ListOfDevices[key]['IEEE'] ==  ID :
				Domoticz.Debug("loadListOfDevices - we found a matching entry for ID " +str(x) + " as DeviceID = " +str(ID) +" NWK_ID = " + str(key) )
				found = True

		if not found :
			Domoticz.Error(""loadListOfDevices - didn't find a match n DeviceList for Domoticz device : " +str(x) +" and IEEE = " +str(ID) )

