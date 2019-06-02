#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_LQI.py

    Description: Manage LQI

"""


import queue
import datetime
import time
import os.path
import json

import Domoticz
from Modules.output import sendZigateCmd

from Classes.AdminWidgets import AdminWidgets

def LQIdiscovery(self):
    """
    This is call at Startupup for now ... But final version would be based on a PluginConf parameter which will tell when it should start.
    At start , we will initiate the first LQIRequest on the 0x0000 network address. Then when receiving/decoding an 0x804E message, after populating
    the information in the LQI dictionary, will will trigger one new request on an non-scanned Network address
    """

    self.LQISource = queue.Queue()
    self.LQI = {}
    mgtLQIreq(self)    # We start and by default, it will be on 0x0000 , Index 0

def LQIcontinueScan(self, Devices):

    LQIfound = False
    LODfound = False

    scn = 0
    trt = 0
    for src in self.LQI:
        for child in self.LQI[src]:
            trt += 1
            if self.LQI[src][child]['Scanned']: scn += 1
            Domoticz.Debug(" Source: %4s Child: %4s Relation: %7s Type: %11s Deepth: %2s Scanner: %s" \
                    %(src, child, self.LQI[src][child]['_relationshp'], self.LQI[src][child]['_devicetype'], self.LQI[src][child]['_depth'], self.LQI[src][child]['Scanned']))
    if scn > 0:
        Domoticz.Log("LQIcontinueScan - Nodes = {:2n}".format(trt) + " True " +str(scn) + " {:2n}% completed ".format(round((scn/trt)*100)))
    else:
        Domoticz.Log("LQIcontinueScan - Nodes = {:2n}".format(trt) + " True " +str(scn) + " {:2n}% completed ".format(0))
        
    Domoticz.Debug("LQIcontinueScan - Scanning LOD ")
    for key in self.ListOfDevices:
        Domoticz.Debug("LQIcontinueScan - checking eligibility of " +str(key))
        if str(key) not in self.LQI:
            Domoticz.Debug("LQIcontinueScan - eligeable " +str(key))
            LODfound = True
            if not self.LQI.get(str(key)):
                Domoticz.Debug("LQIcontinueScan - LOD set self.LQI["+str(key)+"] to {}")
                self.LQI[str(key)] = {}
            mgtLQIreq(self, key)
            break                                        # We do only one !
        else:
            Domoticz.Debug("LQIcontinueScan - not eligeable already in LQI " +str(self.LQI[key]))
        if LODfound:
            break                                        # We do only one !

    if not LODfound:
        for src in self.LQI:
            for key in self.LQI[src]:
                if str(src) == str(key):
                    self.LQI[src][key]['Scanned'] = True
                    continue                # This doesn't make sense to scan itself
                # The destination node of this request must be a Router or the Co- ordinator.
                Domoticz.Debug("LQIcontinueScan - Eligible ? " +str(src) + " / " +str(key) + " Scanned ? " +str(self.LQI[src][key]['Scanned']))
                if (not self.LQI[src][key]['Scanned']) and \
                    (self.LQI[src][key]['_devicetype'] == 'Router' or self.LQI[src][key]['_devicetype'] == 'Coordinator'):
                    LQIfound = True
                    self.LQI[src][key]['Scanned'] = True
                    if not self.LQI.get(str(key)):
                        Domoticz.Debug("LQIcontinueScan - set self.LQI["+str(key)+"] to {}")
                        self.LQI[str(key)] = {}
                    mgtLQIreq(self, key)
                    break                                    # We do only one !
                else:
                    self.LQI[src][key]['Scanned'] = True                    # Most likely we will set to True End Node 
            if LQIfound:
                break                                    # We do only one !

    if not LQIfound and not LODfound:                    # We didn't find any more Network address. Game is over

        for src in self.LQI:
            for child in self.LQI[src]:
                try:
                    Domoticz.Log(" Node %4s child %4s relation %7s type %11s deepth %2d linkQty %3d Rx-Idl %6s" \
                        %(src, child, self.LQI[src][child]['_relationshp'], self.LQI[src][child]['_devicetype'], int(self.LQI[src][child]['_depth'], 16), int(self.LQI[src][child]['_lnkqty'], 16), self.LQI[src][child]['_rxonwhenidl']))
                except:
                    Domoticz.Log(" linkQty: " +str(self.LQI[src][child]['_lnkqty']))
                    Domoticz.Log(" Node %4s child %4s relation %7s type %11s deepth %2s linkQty     Rx-Idl %6s" \
                            %(src, child, self.LQI[src][child]['_relationshp'], self.LQI[src][child]['_devicetype'], self.LQI[src][child]['_depth'], self.LQI[src][child]['_rxonwhenidl']))

        Domoticz.Status("Publishing LQI Results")
        for src in self.LQI:
            for child in self.LQI[src]:
                try:
                    Domoticz.Log(" Node %4s child %4s relation %7s type %11s deepth %2d linkQty %3d Rx-Idl %6s" \
                        %(src, child, self.LQI[src][child]['_relationshp'], self.LQI[src][child]['_devicetype'], int(self.LQI[src][child]['_depth'], 16), int(self.LQI[src][child]['_lnkqty'], 16), self.LQI[src][child]['_rxonwhenidl']))
                except:
                    Domoticz.Log(" linkQty: " +str(self.LQI[src][child]['_lnkqty']))
                    Domoticz.Log(" Node %4s child %4s relation %7s type %11s deepth %2s linkQty     Rx-Idl %6s" \
                            %(src, child, self.LQI[src][child]['_relationshp'], self.LQI[src][child]['_devicetype'], self.LQI[src][child]['_depth'], self.LQI[src][child]['_rxonwhenidl']))

        # Write the report onto file
        _filename = self.pluginconf.pluginConf['pluginReports'] + 'LQI_reports-' + '%02d' %self.HardwareID + '.json'
        storeLQI = {}
        storeLQI[int(time.time())] = self.LQI

        self.runLQI[0] = 0
        if os.path.isdir( self.pluginconf.pluginConf['pluginReports'] ):
            with open( _filename, 'at') as json_file:
                json_file.write('\n')
                json.dump( storeLQI, json_file)
            self.adminWidgets.updateNotificationWidget( Devices, 'A new LQI report is available')
        else:
            Domoticz.Error("Unable to get access to directory %s, please check PluginConf.txt" %(self.pluginconf.pluginConf['pluginReports']))



def mgtLQIreq(self, nwkid='0000', index=0):
    """
    Send a Management LQI request 
    This function requests a remote node to provide a list of neighbouring nodes, from its Neighbour table, 
    including LQI (link quality) values for radio transmissions from each of these nodes. 
    The destination node of this request must be a Router or the Co- ordinator.
     <Target Address: uint16_t>
     <Start Index: uint8_t>
    """

    doWork = False
    if nwkid not in self.ListOfDevices:
        return
    if nwkid == '0000':
        doWork = True
    elif 'LogicalType' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['LogicalType'] in ( 'Router' ):
            doWork = True
    if 'DeviceType' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['DeviceType'] in ( 'FFD' ):
            doWork = True
    if 'MacCapa' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['MacCapa'] in ( '8e' ):
            doWork = True
    if 'PowerSource' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['PowerSource'] in ( 'Main'):
            doWork = True

    if not doWork:
        Domoticz.Debug("Skiping %s as it's not a Router nor Coordinator" %nwkid)
        return

    self.LQISource.put(str(nwkid))
    datas = str(nwkid) + "{:02n}".format(index)
    Domoticz.Log("mgtLQIreq: from Nwkid: " +str(nwkid) + " index: "+str(index))
    sendZigateCmd(self, "004E",datas)    

    return


def mgtLQIresp(self, MsgData):
    """
    Process Management LQI response
    This response reports a list of neighbouring nodes along with their LQI (link quality) values

    <Sequence number: uint8_t>                     0:2
    <status: uint8_t>                             2:4
    <Neighbour Table Entries: uint8_t>         4:6
    <Neighbour Table List Count: uint8_t>         6:8
    <Start Index: uint8_t>                     8:10
    <List of Entries elements described below:>    
        Note: If Neighbour Table list count is 0, there are no elements in the list.     
        NWK Address: uint16_t                             n:n+4
        Extended PAN ID: uint64_t                         n+4:n+20
        IEEE Address: uint64_t                         n+20:n+36
        Depth: uint_t                                     n+36:n+38
        Link Quality: uint8_t                             n+38:n+40
        Bit map of attributes Described below: uint8_t     n+40:n+42
                bit 0-1 Device Type         (0-Coordinator 1-Router 2-End Device)     
                bit 2-3 Permit Join status     (1- On 0-Off)     
                bit 4-5 Relationship         (0-Parent 1-Child 2-Sibling)     
                bit 6-7 Rx On When Idle status             (1-On 0-Off)
    """

    Domoticz.Debug("mgtLQIresp - MsgData = " +str(MsgData))

    SQN = MsgData[0:2]
    Status = MsgData[2:4]
    NeighbourTableEntries = int(MsgData[4:6], 16)
    NeighbourTableListCount = int(MsgData[6:8], 16)
    StartIndex = int(MsgData[8:10], 16)
    ListOfEntries = MsgData[10:len(MsgData)]

    Domoticz.Log("mgtLQIresp - Status: %s, NeighbourTableEntries: %s, StartIndex: %s, NeighbourTableListCount: %s" \
            %(Status, NeighbourTableEntries, StartIndex, NeighbourTableListCount))

    if NeighbourTableListCount == 0:
        # No element in that list
        Domoticz.Debug("mgtLQIresp -  No element in that list ")
        return

    if NeighbourTableListCount != NeighbourTableEntries:
        Domoticz.Log("mgtLQIresp - We have received %s entries out of %s" %( NeighbourTableListCount, NeighbourTableEntries))

    NwkIdSource = self.LQISource.get()
    # Let's not overwrite
    if NwkIdSource in self.LQI:                 # Source record exists
        Domoticz.Debug("mgtLQIresp - " +str(NwkIdSource) + " found LQI["+str(NwkIdSource)+"] " + str(self.LQI[NwkIdSource]))
    else:
        self.LQI[NwkIdSource] = {}

    n = 0
    while n < ((NeighbourTableListCount * 42)):
        _nwkid    = ListOfEntries[n:n+4]
        _extPANID = ListOfEntries[n+4:n+20]
        _ieee     = ListOfEntries[n+20:n+36]

        _depth = _lnkqty = _bitmap = 0
        if ListOfEntries[n+36:n+38] != '':
            _depth    = ListOfEntries[n+36:n+38]
        if ListOfEntries[n+38:n+40] != '':
            _lnkqty   = ListOfEntries[n+38:n+40]
        if ListOfEntries[n+40:n+42] != '':
            _bitmap   = int(ListOfEntries[n+40:n+42], 16)

        _devicetype   = _bitmap & 0b00000011
        _permitjnt    = (_bitmap & 0b00001100) >> 2
        _relationshp  = (_bitmap & 0b00110000) >> 4
        _rxonwhenidl  = (_bitmap & 0b11000000) >> 6

        # s a 2-bit value representing the ZigBee device type of the neighbouring node
        if  _devicetype   == 0x00: _devicetype = 'Coordinator'
        elif  _devicetype == 0x01: _devicetype = 'Router'
        elif  _devicetype == 0x02: _devicetype = 'End Device'
        elif  _devicetype == 0x03: _devicetype = '??'

        #is a 3-bit value representing the neighbouring node’s relationship to the local node
        if _relationshp   == 0x00: _relationshp = 'Parent'
        elif _relationshp == 0x01: _relationshp = 'Child'
        elif _relationshp == 0x02: _relationshp = 'Sibling'
        elif _relationshp == 0x03: _relationshp = 'None'
        elif _relationshp == 0x04: _relationshp = 'Former Child'

        if _permitjnt   == 0x00: _permitjnt = 'Off'
        elif _permitjnt == 0x01 : _permitjnt = 'On'
        elif _permitjnt == 0x02 : _permitjnt = '??'

        if _rxonwhenidl   == 0x00: _rxonwhenidl = 'Rx-Off'
        elif _rxonwhenidl == 0x01: _rxonwhenidl = 'Rx-On'
        elif _rxonwhenidl == 0x02: _rxonwhenidl = '??'
        n = n + 42
        Domoticz.Log("mgtLQIresp - capture a new neighbour %s from %s" %(_nwkid, NwkIdSource))
        Domoticz.Log("---> _nwkid: %s" %(_nwkid))
        Domoticz.Log("---> _extPANID: %s" %_extPANID)
        Domoticz.Log("---> _ieee: %s" %_ieee)
        Domoticz.Log("---> _depth: %s" %_depth)
        Domoticz.Log("---> _lnkqty: %s" %_lnkqty)
        Domoticz.Log("---> _devicetype: %s" %_devicetype)
        Domoticz.Log("---> _permitjnt: %s" %_permitjnt)
        Domoticz.Log("---> _relationshp: %s" %_relationshp)
        Domoticz.Log("---> _rxonwhenidl: %s" %_rxonwhenidl)
    
        if str(_nwkid) in self.LQI[NwkIdSource]:    # Is the node also existing
            Domoticz.Debug("mgtLQIresp - " +str(NwkIdSource) + "/" +str(_nwkid) + " found in LQI ")
            if self.LQI[NwkIdSource][str(_nwkid)]['Scanned']:
                Domoticz.Debug("mgtLQIresp - already processed")
                return

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


    return
