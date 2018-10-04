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

