#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: NetworkMap.py

    Description: Network Mapping based on LQI

"""
"""
    Table Neighbours
        self.Neighbours[ nwkdi ]
                                ['Status'] ( 'Completed' /* table is completd (all entries collected */
                                             'WaitResponse' /* Waiting for response */
                                             'ScanRequired' /* A scan is required to get more entries */
                                ['TableMaxSize'] Number of Expected entries
                                ['TableCurSize'] Number of actual entries
                                ['Neighbours'][ nwkid ]
                                                       [attributes]
"""


import datetime
import time
import os.path
import json

import Domoticz
from Modules.output import sendZigateCmd
from Classes.AdminWidgets import AdminWidgets

class NetworkMap():

    def __init__( self, PluginConf, ZigateComm, ListOfDevices, Devices, HardwareID):

        self.pluginconf = PluginConf
        self.ZigateComm = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.HardwareID = HardwareID

        self._NetworkMapPhase = 0
        self.LQIreqInProgress = []
        self.LQIticks = 0
        self.Neighbours = {}                   # Table of Neighbours


    def NetworkMapPhase( self ):

        return self._NetworkMapPhase

    def _initNeighbours( self):

        # Will popoulate the Neghours dict with all Main Powered Devices
        Domoticz.Debug("_initNeighbours")

        for nwkid in self.ListOfDevices:
            router = False
            if nwkid == '0000':
                router = True
            elif 'LogicalType' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['LogicalType'] in ( 'Router' ):
                    router = True
                if 'DeviceType' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['DeviceType'] in ( 'FFD' ):
                        router = True
                if 'MacCapa' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['MacCapa'] in ( '8e' ):
                        router = True

            if not router:
                continue
            self._initNeighboursTableEntry( nwkid )

        return


    def _initNeighboursTableEntry( self, nwkid):

        Domoticz.Debug("_initNeighboursTableEntry - %s" %nwkid)
        self.Neighbours[ nwkid ] = {}
        self.Neighbours[ nwkid ]['Status'] = 'ScanRequired'
        self.Neighbours[ nwkid ]['TableMaxSize'] = 0
        self.Neighbours[ nwkid ]['TableCurSize'] = 0
        self.Neighbours[ nwkid ]['Neighbours'] = {}

    def prettyPrintNeighbours( self ):

        for nwkid in self.Neighbours:
            Domoticz.Log("Neighbours table: %s, %s out of %s - Status: %s" \
                    %(nwkid,self.Neighbours[ nwkid ]['TableCurSize'], self.Neighbours[ nwkid ]['TableMaxSize'], self.Neighbours[ nwkid ]['Status']))
            for entry in self.Neighbours[ nwkid ]['Neighbours']:
                Domoticz.Log("---> Neighbour %s ( %s )" %( entry, self.Neighbours[ nwkid ]['Neighbours'][entry]['_relationshp']))
        Domoticz.Debug("")


    def LQIreq(self, nwkid='0000'):
        """
        Send a Management LQI request 
        This function requests a remote node to provide a list of neighbouring nodes, from its Neighbour table, 
        including LQI (link quality) values for radio transmissions from each of these nodes. 
        The destination node of this request must be a Router or the Co- ordinator.
         <Target Address: uint16_t>
         <Start Index: uint8_t>
        """

        Domoticz.Debug("LQIreq - nwkid: %s" %nwkid)

        if nwkid not in self.Neighbours:
            self._initNeighboursTableEntry( nwkid)
        
        router = False
        if nwkid != '0000' and nwkid not in self.ListOfDevices:
            return
        if nwkid == '0000':
            router = True
        elif 'LogicalType' in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]['LogicalType'] in ( 'Router' ):
                router = True
            if 'DeviceType' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['DeviceType'] in ( 'FFD' ):
                    router = True
            if 'MacCapa' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['MacCapa'] in ( '8e' ):
                    router = True
            if 'PowerSource' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['PowerSource'] in ( 'Main'):
                    router = True

        if not router:
            Domoticz.Debug("Skiping %s as it's not a Router nor Coordinator" %nwkid)
            return

        index = self.Neighbours[ nwkid ]['TableCurSize']

        self.LQIreq
        self.LQIreqInProgress.append ( nwkid )
        datas = "%s%02X" %(nwkid, index)

        Domoticz.Debug("LQIreq - from: %s start at index: %s" %( nwkid, index ))
        self.Neighbours[ nwkid ]['Status'] = 'WaitResponse'
        sendZigateCmd(self, "004E",datas)    

        return


    def start_scan(self):

        if len(self.Neighbours) != 0:
            Domoticz.Debug("start_scan - initialize data")
            del self.Neighbours
            self.Neighbours = {}

        self._initNeighbours( )
        # Start on Zigate Controler
        self.prettyPrintNeighbours()
        self._NetworkMapPhase = 2
        self.LQIreq( )

    def continue_scan(self):

        Domoticz.Debug("continue_scan - %s" %( len(self.LQIreqInProgress) ))
        self.prettyPrintNeighbours()
        if len(self.LQIreqInProgress) > 0 and self.LQIticks < 2:
            Domoticz.Debug("Command pending")
            self.LQIticks += 1
            return
        elif len(self.LQIreqInProgress) > 0 and self.LQIticks >= 2:
            entry = self.LQIreqInProgress.pop()
            Domoticz.Debug("Commdand pending Timeout: %s" % entry)
            self.Neighbours[entry]['Status'] = 'TimedOut'
            self.LQIticks = 0
            Domoticz.Debug("continue_scan - %s" %( len(self.LQIreqInProgress) ))

        waitResponse = False
        for entry in self.Neighbours:
            if self.Neighbours[entry]['Status'] == 'Completed':
                continue

            elif self.Neighbours[entry]['Status'] == 'TimedOut':
                continue

            elif self.Neighbours[entry]['Status'] == 'WaitResponse':
                waitResponse = True
                continue

            elif self.Neighbours[entry]['Status'] == 'ScanRequired':
                    self.LQIreq( entry )
                    return

        else:
            # We have been through all list of devices and not action triggered
            if not waitResponse:
                Domoticz.Debug("continue_scan - scan completed, all Neighbour tables received.")
                self._NetworkMapPhase = 0
                self.finish_scan()
        return

    def finish_scan( self ):

        # Write the report onto file
        Domoticz.Log("Network Topology report")
        Domoticz.Log("------------------------------------------------------------------------------------------")
        Domoticz.Log("")
        Domoticz.Log("%6s %6s %9s %11s %6s %4s %7s" %("Node", "Node", "Relation", "Type", "Deepth", "LQI", "Rx-Idle"))

        for nwkid in self.Neighbours:
            for child in self.Neighbours[nwkid]['Neighbours']:
                Domoticz.Log("%6s %6s %9s %11s %6d %4d %7s" \
                    %( nwkid, child , self.Neighbours[nwkid]['Neighbours'][child]['_relationshp'],
                            self.Neighbours[nwkid]['Neighbours'][child]['_devicetype'],
                            int(self.Neighbours[nwkid]['Neighbours'][child]['_depth'],16),
                            int(self.Neighbours[nwkid]['Neighbours'][child]['_lnkqty'],16),
                            self.Neighbours[nwkid]['Neighbours'][child]['_rxonwhenidl']))
        Domoticz.Log("--")

        self.prettyPrintNeighbours()
        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkTopology-' + '%02d' %self.HardwareID + '.json'

        storeLQI = {}
        storeLQI[int(time.time())] = dict(self.Neighbours)

        if os.path.isdir( self.pluginconf.pluginConf['pluginReports'] ):
            with open( _filename, 'at') as json_file:
                json_file.write('\n')
                json.dump( storeLQI, json_file)
            #self.adminWidgets.updateNotificationWidget( Devices, 'A new LQI report is available')
        else:
            Domoticz.Error("Unable to get access to directory %s, please check PluginConf.txt" %(self.pluginconf.pluginConf['pluginReports']))


    def LQIresp(self, MsgData):

        Domoticz.Debug("LQIresp - MsgData = " +str(MsgData))

        SQN = MsgData[0:2]
        Status = MsgData[2:4]
        NeighbourTableEntries = int(MsgData[4:6], 16)
        NeighbourTableListCount = int(MsgData[6:8], 16)
        StartIndex = int(MsgData[8:10], 16)
        ListOfEntries = MsgData[10:len(MsgData)]

        if Status != '00':
            Domoticz.Error("LQIresp - Status: %s for %s" %(Status, MsgData))
            return
        if len(self.LQIreqInProgress) == 0:
            Domoticz.Error("LQIresp - Receive unexpected message %s"  %(MsgData))
            return

        if len(ListOfEntries)//42 != NeighbourTableListCount:
            Domoticz.Log("LQIresp - missmatch. Expecting %s entries and found %s" \
                    %(NeighbourTableListCount, len(ListOfEntries)//42))

        NwkIdSource = self.LQIreqInProgress.pop()
        Domoticz.Debug("self.LQIreqInProgress = %s" %len(self.LQIreqInProgress))
        Domoticz.Log("LQIresp - %s Status: %s, NeighbourTableEntries: %s, StartIndex: %s, NeighbourTableListCount: %s" \
                %(NwkIdSource, Status, NeighbourTableEntries, StartIndex, NeighbourTableListCount))

        if not self.Neighbours[ NwkIdSource ]['TableMaxSize']  and NeighbourTableEntries:
            self.Neighbours[ NwkIdSource ]['TableMaxSize'] = NeighbourTableEntries

        if not NeighbourTableListCount and not NeighbourTableEntries:
            # No element in that list
            Domoticz.Debug("LQIresp -  No element in that list ")
            self.Neighbours[NwkIdSource]['Status'] = 'Completed'
            return

        if (StartIndex + NeighbourTableListCount) == NeighbourTableEntries:
            Domoticz.Debug("mgtLQIresp - We have received %3s entries out of %3s" %( NeighbourTableListCount, NeighbourTableEntries))
            self.Neighbours[NwkIdSource]['TableCurSize'] = StartIndex + NeighbourTableListCount
            self.Neighbours[NwkIdSource]['Status'] = 'Completed'
        else:
            Domoticz.Debug("mgtLQIresp - We have received %3s entries out of %3s" %( NeighbourTableListCount, NeighbourTableEntries))
            self.Neighbours[NwkIdSource]['Status'] = 'ScanRequired'
            self.Neighbours[NwkIdSource]['TableCurSize'] = StartIndex + NeighbourTableListCount

        # Decoding the Table
        Domoticz.Log("mgtLQIresp - ListOfEntries: %s" %len(ListOfEntries))
        n = 0
        while n < ((NeighbourTableListCount * 42)):
            _nwkid    = ListOfEntries[n:n+4]        # uint16
            _extPANID = ListOfEntries[n+4:n+20]     # uint64
            _ieee     = ListOfEntries[n+20:n+36]    # uint64

            _depth = _lnkqty = _bitmap = 0
            if ListOfEntries[n+36:n+38] != '':
                _depth    = ListOfEntries[n+36:n+38] # uint8
            if ListOfEntries[n+38:n+40] != '':
                _lnkqty   = ListOfEntries[n+38:n+40] #uint8
            if ListOfEntries[n+40:n+42] != '':
                _bitmap   = int(ListOfEntries[n+40:n+42], 16) # uint8

            _devicetype   =  _bitmap & 0b00000011
            _permitjnt    = (_bitmap & 0b00001100) >> 2
            _relationshp  = (_bitmap & 0b00110000) >> 4
            _rxonwhenidl  = (_bitmap & 0b11000000) >> 6
            Domoticz.Log("bitmap         : {0:{fill}8b}".format(_bitmap, fill='0') + " - %0X for ( %s, %s)" %(_bitmap, NwkIdSource, _nwkid))
            Domoticz.Log("--> _devicetype: | | |- %s" %_devicetype)
            Domoticz.Log("--> _permitjnt:  | | -%s" %_permitjnt)
            Domoticz.Log("--> _relationshp:| -%s" %_relationshp)
            Domoticz.Log("--> _rxonwhenidl:-%s" %_rxonwhenidl)

            # s a 2-bit value representing the ZigBee device type of the neighbouring node
            if  _devicetype   == 0x00: _devicetype = 'Coordinator'
            elif  _devicetype == 0x01: _devicetype = 'Router'
            elif  _devicetype == 0x02: _devicetype = 'End Device'
            elif  _devicetype == 0x03: _devicetype = '??'


            #is a 3-bit value representing the neighbouring node’s relationship to the local node
            if _relationshp   == 0x00: _relationshp = 'Parent'
            elif _relationshp == 0x01: _relationshp = 'Child'
            elif _relationshp == 0x02: _relationshp = 'Sibling'
            #else: _relationshp = 'Child'
            elif _relationshp == 0x03: _relationshp = 'None'
            elif _relationshp == 0x04: _relationshp = 'Former Child'

            if _permitjnt   == 0x00: _permitjnt = 'Off'
            elif _permitjnt == 0x01 : _permitjnt = 'On'
            elif _permitjnt == 0x02 : _permitjnt = '--'

            if _rxonwhenidl   == 0x00: _rxonwhenidl = 'Rx-Off'
            elif _rxonwhenidl == 0x01: _rxonwhenidl = 'Rx-On'
            elif _rxonwhenidl == 0x02: _rxonwhenidl = '--'
            n = n + 42
            Domoticz.Debug("mgtLQIresp - capture a new neighbour %s from %s" %(_nwkid, NwkIdSource))
            Domoticz.Debug("---> _nwkid: %s" %(_nwkid))
            Domoticz.Debug("---> _extPANID: %s" %_extPANID)
            Domoticz.Debug("---> _ieee: %s" %_ieee)
            Domoticz.Debug("---> _depth: %s" %_depth)
            Domoticz.Debug("---> _lnkqty: %s" %_lnkqty)
            Domoticz.Debug("---> _devicetype: %s" %_devicetype)
            Domoticz.Debug("---> _permitjnt: %s" %_permitjnt)
            Domoticz.Debug("---> _relationshp: %s" %_relationshp)
            Domoticz.Debug("---> _rxonwhenidl: %s" %_rxonwhenidl)
        
            if _nwkid in self.Neighbours[ NwkIdSource ]['Neighbours']:
                Domoticz.Log("LQIresp - %s already in Neighbours Table for %s" %(_nwkid, NwkIdSource))
                return

            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid] = {}
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_extPANID'] = _extPANID
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_ieee'] = _ieee
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_depth'] = _depth
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_lnkqty'] = _lnkqty
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_devicetype'] = _devicetype
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_permitjnt'] = _permitjnt
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_relationshp'] = _relationshp
            self.Neighbours[NwkIdSource]['Neighbours'][_nwkid]['_rxonwhenidl'] = _rxonwhenidl

        return
