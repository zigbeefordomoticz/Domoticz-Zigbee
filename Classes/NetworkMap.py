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
                                             'WaitResponse2' /* Waiting for response */
                                             'ScanRequired' /* A scan is required to get more entries */
                                             'ScanRequired2' /* A scan is required to get more entries */
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


    def logging( self, logType, message):

        self.debugNetworkMap = self.pluginconf.pluginConf['debugNetworkMap']
        if logType == 'Debug' and self.debugNetworkMap:
            Domoticz.Log( message)
        elif logType == 'Log':
            Domoticz.Log( message )
        elif logType == 'Status':
            Domoticz.Status( message)
        return

    def NetworkMapPhase( self ):

        return self._NetworkMapPhase

    def _initNeighbours( self):

        # Will popoulate the Neghours dict with all Main Powered Devices
        self.logging( 'Debug', "_initNeighbours")

        for nwkid in self.ListOfDevices:
            router = False
            if nwkid == '0000':
                router = True
            elif 'LogicalType' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['LogicalType'] == 'Router':
                    router = True
                if 'DeviceType' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['DeviceType'] == 'FFD':
                        router = True
                if 'MacCapa' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['MacCapa'] == '8e':
                        router = True

            if not router:
                continue
            self._initNeighboursTableEntry( nwkid )

        return


    def _initNeighboursTableEntry( self, nwkid):

        self.logging( 'Debug', "_initNeighboursTableEntry - %s" %nwkid)
        self.Neighbours[ nwkid ] = {}
        self.Neighbours[ nwkid ]['Status'] = 'ScanRequired'
        self.Neighbours[ nwkid ]['TableMaxSize'] = 0
        self.Neighbours[ nwkid ]['TableCurSize'] = 0
        self.Neighbours[ nwkid ]['Neighbours'] = {}

    def prettyPrintNeighbours( self ):

        for nwkid in self.Neighbours:
            self.logging( 'Debug', "Neighbours table: %s, %s out of %s - Status: %s" \
                    %(nwkid,self.Neighbours[ nwkid ]['TableCurSize'], self.Neighbours[ nwkid ]['TableMaxSize'], self.Neighbours[ nwkid ]['Status']))
            for entry in self.Neighbours[ nwkid ]['Neighbours']:
                self.logging( 'Debug', "---> Neighbour %s ( %s )" %( entry, self.Neighbours[ nwkid ]['Neighbours'][entry]['_relationshp']))
        self.logging( 'Debug', "")


    def LQIreq(self, nwkid='0000'):
        """
        Send a Management LQI request 
        This function requests a remote node to provide a list of neighbouring nodes, from its Neighbour table, 
        including LQI (link quality) values for radio transmissions from each of these nodes. 
        The destination node of this request must be a Router or the Co- ordinator.
         <Target Address: uint16_t>
         <Start Index: uint8_t>
        """

        self.logging( 'Debug', "LQIreq - nwkid: %s" %nwkid)


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
            self.logging( 'Debug', "Skiping %s as it's not a Router nor Coordinator" %nwkid)
            return

        index = self.Neighbours[ nwkid ]['TableCurSize']

        self.LQIreq
        self.LQIreqInProgress.append ( nwkid )
        datas = "%s%02X" %(nwkid, index)

        self.logging( 'Debug', "LQIreq - from: %s start at index: %s" %( nwkid, index ))
        if self.Neighbours[ nwkid ]['Status'] == 'ScanRequired':
            self.Neighbours[ nwkid ]['Status'] = 'WaitResponse'
        elif self.Neighbours[ nwkid ]['Status'] == 'ScanRequired2':
            self.Neighbours[ nwkid ]['Status'] = 'WaitResponse2'

        if nwkid in self.ListOfDevices:
            if 'Health' in self.ListOfDevices[nwkid]:
                Domoticz.Log("LQIreq %s - >%s<" %(nwkid, self.ListOfDevices[nwkid]['Health']))
                if self.ListOfDevices[nwkid]['Health'] == 'Not Reachable':
                    self.logging( 'Log', "LQIreq - skiping device %s which is Not Reachable" %nwkid)
                    self.Neighbours[ nwkid ]['Status'] = 'NotReachable'
                    return

        sendZigateCmd(self, "004E",datas)    

        return


    def start_scan(self):

        if len(self.Neighbours) != 0:
            self.logging( 'Debug', "start_scan - initialize data")
            del self.Neighbours
            self.Neighbours = {}

        self._initNeighbours( )
        # Start on Zigate Controler
        self.prettyPrintNeighbours()
        self._NetworkMapPhase = 2
        self.LQIreq( )

    def continue_scan(self):

        self.logging( 'Debug', "continue_scan - %s" %( len(self.LQIreqInProgress) ))
        self.prettyPrintNeighbours()
        if len(self.LQIreqInProgress) > 0 and self.LQIticks < 2:
            self.logging( 'Debug', "Command pending")
            self.LQIticks += 1
            return
        elif len(self.LQIreqInProgress) > 0 and self.LQIticks >= 2:
            entry = self.LQIreqInProgress.pop()
            self.logging( 'Debug', "Commdand pending Timeout: %s" % entry)
            if self.Neighbours[entry]['Status'] == 'WaitResponse':
                self.Neighbours[entry]['Status'] = 'ScanRequired2'
                self.logging( 'Debug', "LQI:continue_scan - Try one more for %s" %entry)
            elif self.Neighbours[entry]['Status'] == 'WaitResponse2':
                self.Neighbours[entry]['Status'] = 'TimedOut'
                self.logging( 'Debug', "LQI:continue_scan - TimedOut for %s" %entry)

            self.LQIticks = 0
            self.logging( 'Debug', "continue_scan - %s" %( len(self.LQIreqInProgress) ))

        waitResponse = False
        for entry in self.Neighbours:
            if self.Neighbours[entry]['Status'] == 'Completed':
                continue
            elif self.Neighbours[entry]['Status'] in ( 'TimedOut', 'NotReachable'):
                continue
            elif self.Neighbours[entry]['Status'] in ( 'WaitResponse', 'WaitResponse2'):
                waitResponse = True
                continue
            elif self.Neighbours[entry]['Status'] in ( 'ScanRequired', 'ScanRequired2') :
                    self.LQIreq( entry )
                    return
        else:
            # We have been through all list of devices and not action triggered
            if not waitResponse:
                self.logging( 'Debug', "continue_scan - scan completed, all Neighbour tables received.")
                self._NetworkMapPhase = 0
                self.finish_scan()
        return

    def finish_scan( self ):

        # Write the report onto file
        Domoticz.Status("Network Topology report")
        Domoticz.Status("------------------------------------------------------------------------------------------")
        Domoticz.Status("")
        Domoticz.Status("%6s %6s %9s %11s %6s %4s %7s" %("Node", "Node", "Relation", "Type", "Deepth", "LQI", "Rx-Idle"))

        for nwkid in self.Neighbours:
            if nwkid in self.ListOfDevices:
                if 'Neighbours' in self.ListOfDevices[nwkid]:
                    del self.ListOfDevices[nwkid]['Neighbours']
                self.ListOfDevices[nwkid]['Neighbours'] = []
            else:
                Domoticz.Error("finish_scan - %s not found in list Of Devices." %nwkid)

            if self.Neighbours[nwkid]['Status'] == 'NotReachable':
                Domoticz.Status("%6s %6s %9s %11s %6s %4s %7s NotReachable" \
                    %( nwkid, '-' , '-','-','-','-','-' ))
                if 'Neighbours' in self.ListOfDevices[nwkid]:
                    self.ListOfDevices[nwkid]['Neighbours'].append( 'Not Reachable' )
            elif self.Neighbours[nwkid]['Status'] == 'TimedOut':
                Domoticz.Status("%6s %6s %9s %11s %6s %4s %7s TimedOut" \
                    %( nwkid, '-' , '-','-','-','-','-' ))
                self.ListOfDevices[nwkid]['Neighbours'].append( 'Timed Out' )
            else:
                for child in self.Neighbours[nwkid]['Neighbours']:
                    Domoticz.Status("%6s %6s %9s %11s %6d %4d %7s" \
                        %( nwkid, child , self.Neighbours[nwkid]['Neighbours'][child]['_relationshp'],
                                self.Neighbours[nwkid]['Neighbours'][child]['_devicetype'],
                                int(self.Neighbours[nwkid]['Neighbours'][child]['_depth'],16),
                                int(self.Neighbours[nwkid]['Neighbours'][child]['_lnkqty'],16),
                                self.Neighbours[nwkid]['Neighbours'][child]['_rxonwhenidl']))
                    element = {}
                    element[child] = {}
                    element[child]['_relationshp'] = self.Neighbours[nwkid]['Neighbours'][child]['_relationshp']
                    element[child]['_devicetype'] =  self.Neighbours[nwkid]['Neighbours'][child]['_devicetype']
                    element[child]['_depth'] =   int(self.Neighbours[nwkid]['Neighbours'][child]['_depth'],16)
                    element[child]['_lnkqty'] =  int(self.Neighbours[nwkid]['Neighbours'][child]['_lnkqty'],16)
                    element[child]['_rxonwhenidl'] = self.Neighbours[nwkid]['Neighbours'][child]['_rxonwhenidl'] 
                    self.ListOfDevices[nwkid]['Neighbours'].append( element )

        Domoticz.Status("--")

        self.prettyPrintNeighbours()

        storeLQI = {}
        storeLQI[int(time.time())] = dict(self.Neighbours)

        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkTopology-v3-' + '%02d' %self.HardwareID + '.json'
        if os.path.isdir( self.pluginconf.pluginConf['pluginReports'] ):

            nbentries = 0
            if os.path.isfile( _filename ):
                with open( _filename, 'r') as fin:
                    data = fin.read().splitlines(True)
                    nbentries = len(data)

            with open( _filename, 'w') as fout:
                # we need to short the list by todayNumReports - todayNumReports - 1
                maxNumReports = self.pluginconf.pluginConf['numTopologyReports']
                start = 0
                if nbentries >= maxNumReports:
                    start = (nbentries - maxNumReports)+ 1
                self.logging( 'Debug', "Rpt max: %s , New Start: %s, Len:%s " %(maxNumReports, start, nbentries))

                if nbentries != 0:
                    fout.write('\n')
                    fout.writelines(data[start:])
                fout.write('\n')
                json.dump( storeLQI, fout)
            #self.adminWidgets.updateNotificationWidget( Devices, 'A new LQI report is available')
        else:
            Domoticz.Error("LQI:Unable to get access to directory %s, please check PluginConf.txt" %(self.pluginconf.pluginConf['pluginReports']))


    def LQIresp(self, MsgData):

        self.logging( 'Debug', "LQIresp - MsgData = " +str(MsgData))

        MsgSrc = None
        SQN = MsgData[0:2]
        Status = MsgData[2:4]
        NeighbourTableEntries = int(MsgData[4:6], 16)
        NeighbourTableListCount = int(MsgData[6:8], 16)
        StartIndex = int(MsgData[8:10], 16)
        ListOfEntries = MsgData[ 10 : 10 + 42*NeighbourTableListCount]

        if len(MsgData) == ( 10 + 42*NeighbourTableListCount + 4 ):
            # Firmware 3.1a and aboce
            MsgSrc = MsgData[ 10 + 42*NeighbourTableListCount: len(MsgData)]
            self.logging( 'Debug', "LQIresp - Firmware 3.1a - MsgSrc: %s" %MsgSrc)

        if Status != '00':
            Domoticz.Error("LQI:LQIresp - Status: %s for %s" %(Status, MsgData))
            return
        if len(self.LQIreqInProgress) == 0:
            Domoticz.Error("LQI:LQIresp - Receive unexpected message %s"  %(MsgData))
            return

        if len(ListOfEntries)//42 != NeighbourTableListCount:
            Domoticz.Error("LQI:LQIresp - missmatch. Expecting %s entries and found %s" \
                    %(NeighbourTableListCount, len(ListOfEntries)//42))

        NwkIdSource = self.LQIreqInProgress.pop()
        if MsgSrc:
            if MsgSrc != NwkIdSource:
                Domoticz.Log("LQIresp - Receive %s but expect %s" %(MsgSrc, NwkIdSource))

        self.logging( 'Debug', "self.LQIreqInProgress = %s" %len(self.LQIreqInProgress))
        self.logging( 'Debug', "LQIresp - %s Status: %s, NeighbourTableEntries: %s, StartIndex: %s, NeighbourTableListCount: %s" \
                %(NwkIdSource, Status, NeighbourTableEntries, StartIndex, NeighbourTableListCount))

        if not self.Neighbours[ NwkIdSource ]['TableMaxSize']  and NeighbourTableEntries:
            self.Neighbours[ NwkIdSource ]['TableMaxSize'] = NeighbourTableEntries

        if not NeighbourTableListCount and not NeighbourTableEntries:
            # No element in that list
            self.logging( 'Debug', "LQIresp -  No element in that list ")
            self.Neighbours[NwkIdSource]['Status'] = 'Completed'
            return

        if (StartIndex + NeighbourTableListCount) == NeighbourTableEntries:
            self.logging( 'Debug', "mgtLQIresp - We have received %3s entries out of %3s" %( NeighbourTableListCount, NeighbourTableEntries))
            self.Neighbours[NwkIdSource]['TableCurSize'] = StartIndex + NeighbourTableListCount
            self.Neighbours[NwkIdSource]['Status'] = 'Completed'
        else:
            self.logging( 'Debug', "mgtLQIresp - We have received %3s entries out of %3s" %( NeighbourTableListCount, NeighbourTableEntries))
            self.Neighbours[NwkIdSource]['Status'] = 'ScanRequired'
            self.Neighbours[NwkIdSource]['TableCurSize'] = StartIndex + NeighbourTableListCount

        # Decoding the Table
        self.logging( 'Debug', "mgtLQIresp - ListOfEntries: %s" %len(ListOfEntries))
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
            self.logging( 'Debug', "bitmap         : {0:{fill}8b}".format(_bitmap, fill='0') + " - %0X for ( %s, %s)" %(_bitmap, NwkIdSource, _nwkid))
            self.logging( 'Debug', "--> _devicetype: | | |- %s" %_devicetype)
            self.logging( 'Debug', "--> _permitjnt:  | | -%s" %_permitjnt)
            self.logging( 'Debug', "--> _relationshp:| -%s" %_relationshp)
            self.logging( 'Debug', "--> _rxonwhenidl:-%s" %_rxonwhenidl)

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
            self.logging( 'Debug', "mgtLQIresp - capture a new neighbour %s from %s" %(_nwkid, NwkIdSource))
            self.logging( 'Debug', "---> _nwkid: %s" %(_nwkid))
            self.logging( 'Debug', "---> _extPANID: %s" %_extPANID)
            self.logging( 'Debug', "---> _ieee: %s" %_ieee)
            self.logging( 'Debug', "---> _depth: %s" %_depth)
            self.logging( 'Debug', "---> _lnkqty: %s" %_lnkqty)
            self.logging( 'Debug', "---> _devicetype: %s" %_devicetype)
            self.logging( 'Debug', "---> _permitjnt: %s" %_permitjnt)
            self.logging( 'Debug', "---> _relationshp: %s" %_relationshp)
            self.logging( 'Debug', "---> _rxonwhenidl: %s" %_rxonwhenidl)
        
            if _nwkid in self.Neighbours[ NwkIdSource ]['Neighbours']:
                Domoticz.Log("LQI:LQIresp - %s already in Neighbours Table for %s" %(_nwkid, NwkIdSource))
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
