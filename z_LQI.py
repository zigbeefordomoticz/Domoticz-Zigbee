#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_LQI.py

	Description: Manage LQI

"""


import Domoticz
import z_output
import z_var

def LQIdiscovery( self ):
	"""
	This is call at Startupup for now ... But final version would be based on a PluginConf parameter which will tell when it should start.
	At start , we will initiate the first LQIRequest on the 0x0000 network address. Then when receiving/decoding an 0x804E message, after populating
	the information in the LQI dictionary, will will trigger one new request on an non-scanned Network address
	"""

	self.LQI = {}
	mgtLQIreq( self )	# We start and by default, it will be on 0x0000 , Index 0

def LQIcontinueScan( self ) :

	if z_var.LQISource == "ffff" : return

	Domoticz.Log("LQIcontinueScan - Size = " +str(len(self.LQI) ) )

	LQIfound = False
	LODfound = False
	for src in self.LQI :
		for key in self.LQI[src] :
			# The destination node of this request must be a Router or the Co- ordinator.
			if str(key) == "0000" : continue	# We started with that one
			Domoticz.Log("LQIcontinueScan - Eligible ? " +str(src) + " / " +str(key) + " Scanned ? " +str(self.LQI[src][key]['Scanned']) )
			if ( not self.LQI[src][key]['Scanned']) and (self.LQI[src][key]['_devicetype'] == 'Router' or self.LQI[src][key]['_devicetype'] == 'Coordinator') :
				LQIfound = True
				self.LQI[src][key]['Scanned'] = True
				self.LQI[str(key)] = {}
				mgtLQIreq( self, key )
				break									# We do only one !
		if LQIfound :
			break

	if not LQIfound :									# We do not have any more node to discover, let's take one from the pool
		Domoticz.Debug("LQIcontinueScan - nothing found in LQI")
		for key in self.ListOfDevices :
			Domoticz.Debug("LQIcontinueScan - checking eligibility of " +str(key) )
			for src in self.LQI :
				if str(key) in self.LQI[src] and str(key) != z_var.LQISource : 
					Domoticz.Debug("LQIcontinueScan - not eligeable already in LQI " +str( self.LQI[src] ) )
				else :
					Domoticz.Debug("LQIcontinueScan - eligeable " +str( key ) )
					LODfound = True
					self.LQI[str(key)] = {}
					mgtLQIreq( self, key )
					break										# We do only one !
			if LODfound :
				break

	if not LQIfound and not LODfound :					# We didn't find any more Network address. Game is over
		Domoticz.Log("LQI Scan is over ....")
		Domoticz.Log("LQI Results :")
		Domoticz.Log(str(self.LQI) )
		z_var.LQISource = "ffff"

def mgtLQIreq( self, nwkid='0000', index=0 ):
	"""
	Send a Management LQI request 
	This function requests a remote node to provide a list of neighbouring nodes, from its Neighbour table, 
	including LQI (link quality) values for radio transmissions from each of these nodes. 
	The destination node of this request must be a Router or the Co- ordinator.
	 <Target Address : uint16_t>
	 <Start Index : uint8_t>
	"""

	z_var.LQISource= str(nwkid)		# We process only one Node at a time and we store NwkId in order to now whom the response is coming from
	datas = str(nwkid) + "{:02n}".format(index)
	Domoticz.Debug("mgtLQIreq : from Nwkid : " +str(nwkid) + " index : "+str(index) )
	z_output.sendZigateCmd("004E",datas, 2)	

	return


def mgtLQIresp ( self , MsgData) :
	"""
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
	"""

	Domoticz.Debug("mgtLQIresp - MsgData = " +str(MsgData) )

	SQN=MsgData[0:2]
	Status=MsgData[2:4]
	NeighbourTableEntries=int(MsgData[4:6],16)
	NeighbourTableListCount=int(MsgData[6:8],16)
	StartIndex=int(MsgData[8:10],16)
	ListOfEntries=MsgData[10:len(MsgData)]


	Domoticz.Debug("mgtLQIresp - SQN = " +str(SQN) )
	Domoticz.Debug("mgtLQIresp - status = " +str(Status) )
	Domoticz.Debug("mgtLQIresp - NeighbourTableEntries = " +str(NeighbourTableEntries) )
	Domoticz.Debug("mgtLQIresp - NeighbourTableListCount = " +str(NeighbourTableListCount) )
	Domoticz.Debug("mgtLQIresp - StartIndex = " +str(StartIndex) )

	if NeighbourTableListCount == 0 :
		# No element in that list
		Domoticz.Log("mgtLQIresp -  No element in that list ")
		return

	NwkIdSource = z_var.LQISource
	self.LQI[NwkIdSource] = {}

	n = 0
	while n < ((NeighbourTableListCount * 42)):
		_nwkid    = ListOfEntries[n:n+4]
		_extPANID = ListOfEntries[n+4:n+20]
		_ieee     = ListOfEntries[n+20:n+36]
		_depth    = ListOfEntries[n+36:n+38]
		_lnkqty   = ListOfEntries[n+38:n+40]
		_bitmap   = int(ListOfEntries[n+40:n+42],16)
		Domoticz.Debug("mgtLQIresp - _bitmap {0:b}".format(_bitmap) )

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
		Domoticz.Debug("mgtLQIresp - Table["+str(NeighbourTableEntries) + "] - " + " _nwkid = " +str(_nwkid) + " _extPANID = " +str(_extPANID) + " _ieee = " +str(_ieee) + " _depth = " +str(_depth) + " _lnkqty = " +str(_lnkqty) + " _devicetype = " +str(_devicetype) + " _permitjnt = " +str(_permitjnt) + " _relationshp = " +str(_relationshp) + " _rxonwhenidl = " +str(_rxonwhenidl) )
	
		self.LQI[NwkIdSource][str(_nwkid)] = {}
		self.LQI[NwkIdSource][str(_nwkid)]['_extPANID'] = _extPANID
		self.LQI[NwkIdSource][str(_nwkid)]['_ieee'] = _ieee
		self.LQI[NwkIdSource][str(_nwkid)]['_depth'] = _depth
		self.LQI[NwkIdSource][str(_nwkid)]['_lnkqty'] = _lnkqty
		self.LQI[NwkIdSource][str(_nwkid)]['_devicetype'] = _devicetype
		self.LQI[NwkIdSource][str(_nwkid)]['_permitjnt'] = _permitjnt
		self.LQI[NwkIdSource][str(_nwkid)]['_relationshp'] = _relationshp
		self.LQI[NwkIdSource][str(_nwkid)]['_rxonwhenidl'] = _rxonwhenidl
		self.LQI[NwkIdSource][str(_nwkid)]['Scanned'] = False

		Domoticz.Log("mgtLQIresp - from " +str(NwkIdSource) + " a new node captured : " +str(_nwkid) ) 
	return
