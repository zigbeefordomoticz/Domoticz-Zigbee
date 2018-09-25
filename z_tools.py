#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module : z_tools.py

	Description: Zigate toolbox
"""
import binascii
import time
import struct
import json

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

def IEEEExist(self, IEEE) :
	#check in ListOfDevices for an existing IEEE
	if IEEE :
		if IEEE in self.ListOfDevices and IEEE != '' :
			return True
		else:
			return False

def DeviceExist(self, Addr , IEE = ''):
	import Domoticz

	#Validity check
	if Addr == '':
		return False
	#check in ListOfDevices
	if Addr in self.ListOfDevices:
		if 'Status' in self.ListOfDevices[Addr] :
			return True

	#If given, let's check if the IEEE is already existing. In such we have a device communicating with a new Saddr
	if IEE:
		for existingKey in self.ListOfDevices:
			existingDevice = self.ListOfDevices[existingKey]
			if existingDevice.get('DomoID') and existingDevice.get('IEEE','wrong iee') == IEE:
				Domoticz.Log("DeviceExist - given Addr/IEEE = " + Addr + "/" + IEE + " found as " + str(existingDevice) )
				Domoticz.Log("DeviceExist - update self.ListOfDevices[" + Addr + "] with " )
				Domoticz.Log("DeviceExist - " + str(existingDevice) )

				# Updating process by :
				# - mapping the information to the new Addr
				#update adress
				self.ListOfDevices[Addr] = existingDevice

				Domoticz.Log("DeviceExist - new device pointing still to old one " + str(Addr) + " -> " + str(self.ListOfDevices[Addr]['DomoID']) )
				Domoticz.Log("DeviceExist - old device still active  " + str(existingDevice) + " -> " + str(self.ListOfDevices[existingDevice]['DomoID']) )
				#del i
				return True
	return False


def initDeviceInList(self, Addr) :
	if Addr != '' :
		self.ListOfDevices[Addr]={}
		self.ListOfDevices[Addr]['Status']="004d"
		self.ListOfDevices[Addr]['SQN']={}
		self.ListOfDevices[Addr]['DomoID']={}
		self.ListOfDevices[Addr]['Ep']={}
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


def CheckDeviceList(self, key, val) :
	import Domoticz

	Domoticz.Debug("CheckDeviceList - Address search : " + str(key))
	Domoticz.Debug("CheckDeviceList - with value : " + str(val))

	DeviceListVal=eval(val)
	if DeviceExist(self, key, DeviceListVal.get('IEEE','')) == False :
		Domoticz.Log("CheckDeviceList - Address will be add : " + str(key))
		initDeviceInList(self, key)
		self.ListOfDevices[key]['RIA']="10"
		if 'Ep' in DeviceListVal :
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
		if 'RSSI' in DeviceListVal :
			self.ListOfDevices[key]['RSSI']=DeviceListVal['RSSI']
		if 'SQN' in DeviceListVal :
			self.ListOfDevices[key]['SQN']=DeviceListVal['SQN']
		if 'DomoID' in DeviceListVal :
			self.ListOfDevices[key]['DomoID']=DeviceListVal['DomoID']


def updSQN( self, key, newSQN) :
	import Domoticz

	# For now, we are simply updating the SQN. When ready we will be able to implement a cross-check in SQN sequence
	Domoticz.Debug("Device : " + key + " MacCapa : " + self.ListOfDevices[key]['MacCapa'] + " updating SQN to " + str(newSQN) )

	if self.ListOfDevices[key]['MacCapa'] != '8e' : 		# So far we have a good understanding on how SQN is managed for battery powered devices
		if self.ListOfDevices[key].get('SQN') :
			oldSQN = self.ListOfDevices[key]['SQN']
		else :
			oldSQN='00'

		if int(oldSQN,16) != int(newSQN,16) :
			Domoticz.Log("updSQN - Device : " + key + " updating SQN to " + str(newSQN) )
			self.ListOfDevices[key]['SQN'] = newSQN
			if ( int(oldSQN,16)+1 != int(newSQN,16) ) and newSQN != "00" :
				Domoticz.Log("Out of sequence for Device: " + str(key) + " SQN move from " +str(oldSQN) + " to " + str(newSQN) + " gap of : " + str(int(newSQN,16) - int(oldSQN,16)))
	else :
		Domoticz.Debug("updSQN - Device : " + key + " MacCapa : " + self.ListOfDevices[key]['MacCapa'] + " SQN " + str(newSQN) )
		self.ListOfDevices[key]['SQN'] = {}
