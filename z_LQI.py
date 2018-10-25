#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_LQI.py

	Description: Manage LQI

"""


def mgtLQIreq( self, nwkid='0000', index=0 ):
	'''
	Send a Management LQI request 
	 <Target Address : uint16_t>
	 <Start Index : uint8_t>
	We start from 0000 Index 0
	'''

	datas = str(nwkid) + "{02]".format(index)
	Domoticz.Log("mgtLQIreq : from Nwkid : " +str(nwkid) + " index : "+str(index) )
	sendZigateCmd("004E",datas, 2)	

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

	SQN=MsgData[0:2]
	Status=MsgData[2:4]
	NeighbourTableEntrie=int(MsgData[4:6],16)
	NeighbourTableListCount=int(MsgData[6:8],16)
	StartIndex=int(MsgData[8:10],16)
	ListOfEntries=MsgData[10:len(MsgData)]

	if not LQI :
		LQI = {}

	if int(NeighbourTableListCount,16) == 0 :
		# No element in that list
		Domoticz.Log("mgtLQIresp -  No element in that list ")
		return

	n = 10
	while n < ((NeighbourTableListCount * 42) + 10 ):
		_nwkid    = ListOfEntries[n:n+4]
		_extPANID = ListOfEntries[n+4:n+20]
		_ieee     = ListOfEntries[n+20:n+36]
		_depth    = int(ListOfEntries[n+36:n+38], 16 )
		_lnkqty   = int(ListOfEntries[n+38:n+40], 16 )
		_bitmap   = int(ListOfEntries[n+40:n+42],16)
		_devicetype = ( _bitmap & 0x00000011 )
        _permitjnt  = ( _bitmap >> 2 ) & 0x11
        _relationshp= ( _bitmap >> 4 ) & 0x11
        _rxonwhenidl= ( _bitmap >> 6 ) & 0x11
		n = n + 42
		Domoticz.Log("mgtLQIresp - Table["+str(NeighbourTableEntrie) + "] - " + " _nwkid = " +str(_nwkid) + " _extPANID = " +str(_extPANID) + " _ieee = " +str(_ieee) + " _depth = " +str(_depth) + " _lnkqty = " +str(_lnkqty) + " _devicetype = " +str(_devicetype) + " _permitjnt = " +str(_permitjnt) + " _relationshp = " +str(_relationshp) + " _rxonwhenidl = " +str(_rxonwhenidl)


	return
