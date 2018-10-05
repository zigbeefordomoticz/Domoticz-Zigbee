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
				Domoticz.Log("DeviceExist - old device still active  " + str(existingDevice) )
				#del i
				return True
	return False


def initDeviceInList(self, Addr) :
	if Addr != '' :
		self.ListOfDevices[Addr]={}
		self.ListOfDevices[Addr]['Version']="2"
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
		if 'Version' in DeviceListVal :
			self.ListOfDevices[key]['Version']=DeviceListVal['Version']


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



def getTypebyCluster( self, Cluster ) :
	clustersType = { '0405' : 'Humi',
       			 '0406' : 'Motion',
       			 '0400' : 'Lux',
       			 '0403' : 'Baro',
       			 '0402' : 'Temp',
       			 '0006' : 'Switch',
       			 '0500' : 'Door',
       			 '0012' : 'XCube',
       			 '000c' : 'XCube',
       			 '0008' : 'LvlControl',
       			 '0300' : 'ColorControl'
			}

	if Cluster == '' or Cluster is None :
		return ''
	if Cluster in clustersType :
		return clustersType[Cluster]
	else :
		return ''

def getListofClusterbyModel( self, Model , InOut ) :
	"""
	Provide the list of clusters attached to Ep In
	"""
	listofCluster = list()
	if InOut == '' or InOut is None :
		return listofCluster
	if InOut != 'Epin' and InOut != 'Epout' :
		Domoticz.Error( "getListofClusterbyModel - Argument error : " +Model + " " +InOut )
		return ''

	if Model in self.DeviceConf :
		if self.DeviceConf[Model].get(InOut):
			for ep in self.DeviceConf[Model][InOut] :
				seen = ''
				for cluster in sorted(self.DeviceConf[Model][InOut][ep]) :
					if cluster == 'Type' or  cluster == seen :
						continue
					listofCluster.append( cluster )
					seen = cluster
	return listofCluster


def getListofInClusterbyModel( self, Model ) :
	return getListofClusterbyModel( self, Model, 'Epin' )

def getListofOutClusterbyModel( self, Model ) :
	return getListofClusterbyModel( self, Model, 'Epout' )

	
def getListofTypebyModel( self, Model ) :
	"""
	Provide a list of Tuple ( Ep, Type ) for a given Model name if found. Else return an empty list
		Type is provided as a list of Type already.
	"""
	EpType = list()
	if Model in self.DeviceConf :
		for ep in self.DeviceConf[Model]['Epin'] :
			if self.DeviceConf[Model]['Epin'][ep].get('Type') :
				EpinType = ( ep, getListofType( self.DeviceConf[Model]['Epin'][ep]['Type']) )
				EpType.append(EpinType)
	return EpType
	
def getModelbyZDeviceIDProfileID( self, ZDeviceID, ProfileID):
	"""
	Provide a Model for a given ZdeviceID, ProfileID
	"""
	for model in self.DeviceConf :
		if self.DeviceConf[model]['ProfileID'] == ProfileID and self.DeviceConf[model]['ZDeviceID'] == ZDeviceID :
			return model
	return ''




def getListofType( self, Type ) :
	"""
	For a given DeviceConf Type "Plug/Power/Meters" return a list of Type [ 'Plug', 'Power', 'Meters' ]
	"""

	if Type == '' or Type is None :
		return ''
	retList = list()
	retList= Type.split("/")
	return retList



