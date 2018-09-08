#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_database.py

	Description: Function to access Zigate Plugin Database & Dictionary

"""

import Domoticz

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
