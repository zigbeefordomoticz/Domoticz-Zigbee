#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_LQI.py

	Description: Manage LQI

"""


import Domoticz
import z_output

def LQIdiscovery( self ):
	if not self.LQI :
		self.LQI = {}

	self.LQI['Index'] = 0

	mgtLQIreq( self )

def LQIcontinueScan( self ) :

	for key in self.LQI :
		if key == 'Index' : continue
		if str(self.LQI[key]['Scanned']) == '0' :
			Domoticz.Log("LQIcontinueScan - scan : " +str(key) )
			self.LQI['Index'] += 1
			self.LQI[key]['Scanned'] = 1
			mgtLQIreq( self, key,  self.LQI['Index'] )

	for key in self.ListOfDevices :
		if key in self.LQI : continue
		mgtLQIreq( self, key, self.LQI['Index'] )

def mgtLQIreq( self, nwkid='0000', index=0 ):
	'''
	Send a Management LQI request 
	 <Target Address : uint16_t>
	 <Start Index : uint8_t>
	We start from 0000 Index 0
	'''

	datas = str(nwkid) + "{:02n}".format(index)
	Domoticz.Log("mgtLQIreq : from Nwkid : " +str(nwkid) + " index : "+str(index) )
	z_output.sendZigateCmd("004E",datas, 2)	

	return




def mgtLQIresp ( self , MsgData) :
	'''
	Process Management LQI response
	<Sequence number: uint8_t> 					0:2
	<status: uint8_t> 							2:4
	<Neighbour Table Entries : uint8_t> 		4:6
	<Neighbour Table List Count : uint8_t> 		6:8
	<Start Index : uint8_t> 					8:10
	<List of Entries elements described below :>	
		Note: If Neighbour Table list count is 0, there are no elements in the list. 	
		NWK Address : uint16_t 							n:n+4
		Extended PAN ID : uint64_t 						n+4:n+20
		IEEE Address : uint64_t 						n+20:n+36
		Depth : uint_t 									n+36:n+38
		Link Quality : uint8_t 							n+38:n+40
		Bit map of attributes Described below: uint8_t 	n+40:n+42
				bit 0-1 Device Type 		(0-Coordinator 1-Router 2-End Device) 	
				bit 2-3 Permit Join status 	(1- On 0-Off) 	
				bit 4-5 Relationship 		(0-Parent 1-Child 2-Sibling) 	
				bit 6-7 Rx On When Idle status 			(1-On 0-Off)
	'''
	Domoticz.Debug("mgtLQIresp - MsgData = " +str(MsgData) )

	SQN=MsgData[0:2]
	Status=MsgData[2:4]
	NeighbourTableEntries=int(MsgData[4:6],16)
	NeighbourTableListCount=int(MsgData[6:8],16)
	StartIndex=int(MsgData[8:10],16)
	ListOfEntries=MsgData[10:len(MsgData)]


	Domoticz.Log("mgtLQIresp - SQN = " +str(SQN) )
	Domoticz.Log("mgtLQIresp - status = " +str(Status) )
	Domoticz.Log("mgtLQIresp - NeighbourTableEntries = " +str(NeighbourTableEntries) )
	Domoticz.Log("mgtLQIresp - NeighbourTableListCount = " +str(NeighbourTableListCount) )
	Domoticz.Log("mgtLQIresp - StartIndex = " +str(StartIndex) )

	if NeighbourTableListCount == 0 :
		# No element in that list
		Domoticz.Log("mgtLQIresp -  No element in that list ")
		return

	n = 0
	while n < ((NeighbourTableListCount * 42)):
		_nwkid    = ListOfEntries[n:n+4]
		_extPANID = ListOfEntries[n+4:n+20]
		_ieee     = ListOfEntries[n+20:n+36]
		_depth    = ListOfEntries[n+36:n+38]
		_lnkqty   = ListOfEntries[n+38:n+40]
		_bitmap   = int(ListOfEntries[n+40:n+42],16)
		Domoticz.Log("mgtLQIresp - _bitmap {0:b}".format(_bitmap) )

		_devicetype   = _bitmap & 0b00000011
		_permitjnt    = (_bitmap & 0b00001100) >> 2
		_relationshp  = (_bitmap & 0b00110000) >> 4
		_rxonwhenidl  = (_bitmap & 0b11000000) >> 6

		if  _devicetype   == 0x00 : _devicetype = 'Coordinator'
		elif  _devicetype == 0x01 : _devicetype = 'Router'
		elif  _devicetype == 0x02 : _devicetype = 'End Device'

		if _relationshp   == 0x01 : _relationshp = 'Parent'
		elif _relationshp == 0x02 : _relationshp = 'Child'
		elif _relationshp == 0x03 : _relationshp = 'Sibling'

		if _permitjnt   == 0x00 : _permitjnt = 'Off'
		elif _permitjnt == 0x01  : _permitjnt = 'On'
		elif _permitjnt == 0x02  : _permitjnt = '??'

		if _rxonwhenidl   == 0x00 : _rxonwhenidl = 'Rx-Off'
		elif _rxonwhenidl == 0x01 : _rxonwhenidl = 'Rx-On'
		n = n + 42
		Domoticz.Log("mgtLQIresp - Table["+str(NeighbourTableEntries) + "] - " + " _nwkid = " +str(_nwkid) + " _extPANID = " +str(_extPANID) + " _ieee = " +str(_ieee) + " _depth = " +str(_depth) + " _lnkqty = " +str(_lnkqty) + " _devicetype = " +str(_devicetype) + " _permitjnt = " +str(_permitjnt) + " _relationshp = " +str(_relationshp) + " _rxonwhenidl = " +str(_rxonwhenidl) )

		self.LQI[_nwkid] = {}
		self.LQI[_nwkid]['_extPANID'] = _extPANID
		self.LQI[_nwkid]['_ieee'] = _ieee
		self.LQI[_nwkid]['_depth'] = _depth
		self.LQI[_nwkid]['_lnkqty'] = _lnkqty
		self.LQI[_nwkid]['_devicetype'] = _devicetype
		self.LQI[_nwkid]['_permitjnt'] = _permitjnt
		self.LQI[_nwkid]['_relationshp'] = _relationshp
		self.LQI[_nwkid]['_rxonwhenidl'] = _rxonwhenidl
		self.LQI[_nwkid]['Scanned'] = '0'

	return
