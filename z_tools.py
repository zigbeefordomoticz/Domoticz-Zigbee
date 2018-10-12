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

import Domoticz

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

def getSaddrfromIEEE(self, IEEE) :
	# Return Short Address if IEEE found.

	if IEEE != '' :
		for sAddr in self.ListOfDevices :
			if self.ListOfDevices[sAddr]['IEEE'] == IEEE :
				return sAddr

	Domoticz.Log("getSaddrfromIEEE no IEEE found " )

	return ''

def DeviceExist(self, newNWKID , IEEE = ''):

	#Validity check
	if newNWKID == '':
		return False

	#check in ListOfDevices
	if newNWKID in self.ListOfDevices:
		if 'Status' in self.ListOfDevices[newNWKID] :
			return True

	#If given, let's check if the IEEE is already existing. In such we have a device communicating with a new Saddr
	if IEEE:
		for existingIEEEkey in self.IEEE2NWK :
			if existingIEEEkey == IEEE :
				# This device is already in Domoticz 
				existingNWKkey = self.IEEE2NWK[IEEE]

				# Make sure this device is valid 
				if self.ListOfDevices[existingNWKkey]['Status'] == 'inDB' :
					continue

				Domoticz.Debug("DeviceExist - given NWKID/IEEE = " + newNWKID + "/" + IEEE + " found as " +str(existingNWKkey) )

				# Updating process by :
				# - mapping the information to the new newNWKID

				Domoticz.Log("DeviceExist - update self.ListOfDevices[" + newNWKID + "] with " + str(existingIEEEkey) )
				self.ListOfDevices[newNWKID] = dict(self.ListOfDevices[existingNWKkey])

				Domoticz.Log("DeviceExist - update self.IEEE2NWK[" + IEEE + "] from " +str(existingIEEEkey) + " to " + str(newNWKID) )
				self.IEEE2NWK[IEEE] = newNWKID

				Domoticz.Debug("DeviceExist - new device " +str(newNWKID) +" : " + str(self.ListOfDevices[newNWKID]) )
				Domoticz.Debug("DeviceExist - device " +str(IEEE) +" mapped to  " + str(newNWKID) )
				Domoticz.Debug("DeviceExist - old device " +str(existingNWKkey) +" : " + str(self.ListOfDevices[existingNWKkey]) )

				# MostLikely exitsingKey is not needed any more
				removeNwkInList( self, existingNWKkey )	

				if self.ListOfDevices[newNWKID]['Status'] == 'Left' :
					Domoticz.Log("DeviceExist - Update Status from Left to inDB " )
					self.ListOfDevices[newNWKID]['Status'] = 'inDB'
					self.ListOfDevices[newNWKID]['Hearbeat'] = 0

				return True
	return False

def removeNwkInList( self, NWKID) :

	Domoticz.Debug("removeNwkInList - remove " +str(NWKID) + " => " +str( self.ListOfDevices[NWKID] ) ) 
	del self.ListOfDevices[NWKID]



def removeDeviceInList( self, IEEE) :
	# Most likely call when a Device is removed from Domoticz

	key = self.IEEE2NWK[IEEE]
	Domoticz.Debug("removeDeviceInList - removing ListOfDevices["+str(key)+"] : "+str(self.ListOfDevices[key]) )
	del self.ListOfDevices[key]

	Domoticz.Debug("removeDeviceInList - removing IEEE2NWK ["+str(IEEE)+"] : "+str(self.IEEE2NWK[IEEE]) )
	del self.IEEE2NWK[ieee]


def initDeviceInList(self, Nwkid) :
	if Nwkid != '' :
		self.ListOfDevices[Nwkid]={}
		self.ListOfDevices[Nwkid]['Version']="2"
		self.ListOfDevices[Nwkid]['Status']="004d"
		self.ListOfDevices[Nwkid]['SQN']={}
		self.ListOfDevices[Nwkid]['Ep']={}
		self.ListOfDevices[Nwkid]['Heartbeat']="0"
		self.ListOfDevices[Nwkid]['RIA']="0"
		self.ListOfDevices[Nwkid]['RSSI']={}
		self.ListOfDevices[Nwkid]['Battery']={}
		self.ListOfDevices[Nwkid]['Model']={}
		self.ListOfDevices[Nwkid]['MacCapa']={}
		self.ListOfDevices[Nwkid]['IEEE']={}
		self.ListOfDevices[Nwkid]['Type']={}
		self.ListOfDevices[Nwkid]['ProfileID']={}
		self.ListOfDevices[Nwkid]['ZDeviceID']={}
		


def CheckDeviceList(self, key, val) :

	Domoticz.Debug("CheckDeviceList - Address search : " + str(key))
	Domoticz.Debug("CheckDeviceList - with value : " + str(val))

	DeviceListVal=eval(val)
	if DeviceExist(self, key, DeviceListVal.get('IEEE','')) == False :
		Domoticz.Debug("CheckDeviceList - Address will be add : " + str(key))
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
			IEEE = DeviceListVal['IEEE']
			self.IEEE2NWK[IEEE] = key
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
		if 'ClusterType' in DeviceListVal :
			self.ListOfDevices[key]['ClusterType']=DeviceListVal['ClusterType']
		if 'Version' in DeviceListVal :
			self.ListOfDevices[key]['Version']=DeviceListVal['Version']
		

def updSQN( self, key, newSQN) :

	try:
		if not self.ListOfDevices[key] :
			# Seems that the structutre is not yet initialized
			return
	except:
		return

	# For now, we are simply updating the SQN. When ready we will be able to implement a cross-check in SQN sequence
	Domoticz.Debug("Device : " + key + " MacCapa : " + self.ListOfDevices[key]['MacCapa'] + " updating SQN to " + str(newSQN) )

	if self.ListOfDevices[key]['MacCapa'] != '8e' : 		# So far we have a good understanding on how SQN is managed for battery powered devices
		if self.ListOfDevices[key].get('SQN') :
			oldSQN = self.ListOfDevices[key]['SQN']
		else :
			oldSQN='00'

		if int(oldSQN,16) != int(newSQN,16) :
			Domoticz.Debug("updSQN - Device : " + key + " updating SQN to " + str(newSQN) )
			self.ListOfDevices[key]['SQN'] = newSQN
			if ( int(oldSQN,16)+1 != int(newSQN,16) ) and newSQN != "00" :
				Domoticz.Log("Out of sequence for Device: " + str(key) + " SQN move from " +str(oldSQN) + " to " 
								+ str(newSQN) + " gap of : " + str(int(newSQN,16) - int(oldSQN,16)))
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



