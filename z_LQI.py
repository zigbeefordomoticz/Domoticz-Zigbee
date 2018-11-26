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

import Domoticz
import z_output
import z_var

def LQIdiscovery(self):
    """
    This is call at Startupup for now ... But final version would be based on a PluginConf parameter which will tell when it should start.
    At start , we will initiate the first LQIRequest on the 0x0000 network address. Then when receiving/decoding an 0x804E message, after populating
    the information in the LQI dictionary, will will trigger one new request on an non-scanned Network address
    """

    z_var.LQISource = queue.Queue()
    self.LQI = {}
    mgtLQIreq(self)    # We start and by default, it will be on 0x0000 , Index 0

def LQIcontinueScan(self):

    LQIfound = False
    LODfound = False

    scn = 0
    trt = 0
    for src in self.LQI:
        for child in self.LQI[src]:
            trt += 1
            if self.LQI[src][child]['Scanned']: scn += 1
            Domoticz.Debug(" Source {:>4}".format(src) + " child {:>4}".format(child) + \
                    " relation {:>7}".format(self.LQI[src][child]['_relationshp']) + \
                    " type {:>11}".format(self.LQI[src][child]['_devicetype']) + \
                    " deepth {:2n}".format((int(self.LQI[src][child]['_depth'], 16))) + " " +str(self.LQI[src][child]['Scanned']))
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
        Domoticz.Log("LQI Scan is over ....")
        Domoticz.Log("LQI Results:")
        for src in self.LQI:
            for child in self.LQI[src]:
                Domoticz.Log(" Node {:>4}".format(src) + " child {:>4}".format(child) +\
                            " relation {:>7}".format(self.LQI[src][child]['_relationshp']) + " type {:>11}".format(self.LQI[src][child]['_devicetype']) + \
                            " deepth {:2n}".format((int(self.LQI[src][child]['_depth'], 16))) + " linkQty {:3n}".format((int(self.LQI[src][child]['_lnkqty'], 16))) +\
                            " Rx-Idl {:>6}".format(self.LQI[src][child]['_rxonwhenidl']) ) 

        # Write the report onto file
        _filename =  self.homedirectory + "LQI_report-" + str(datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S'))
        Domoticz.Status("LQI report save on " +str(_filename))
        with open(_filename , 'wt') as file:
            for key in self.LQI:
                file.write(key + ": " + str(self.LQI[key]) + "\n")
        self.pluginconf.logLQI = 0

def mgtLQIreq(self, nwkid='0000', index=0):
    """
    Send a Management LQI request 
    This function requests a remote node to provide a list of neighbouring nodes, from its Neighbour table, 
    including LQI (link quality) values for radio transmissions from each of these nodes. 
    The destination node of this request must be a Router or the Co- ordinator.
     <Target Address: uint16_t>
     <Start Index: uint8_t>
    """

    z_var.LQISource.put(str(nwkid))
    datas = str(nwkid) + "{:02n}".format(index)
    Domoticz.Debug("mgtLQIreq: from Nwkid: " +str(nwkid) + " index: "+str(index))
    z_output.sendZigateCmd(self, "004E",datas)    

    return


def mgtLQIresp(self, MsgData):
    """
    Process Management LQI response
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


    Domoticz.Debug("mgtLQIresp - SQN = " +str(SQN))
    Domoticz.Debug("mgtLQIresp - status = " +str(Status))
    Domoticz.Debug("mgtLQIresp - NeighbourTableEntries = " +str(NeighbourTableEntries))
    Domoticz.Debug("mgtLQIresp - NeighbourTableListCount = " +str(NeighbourTableListCount))
    Domoticz.Debug("mgtLQIresp - StartIndex = " +str(StartIndex))

    if NeighbourTableListCount == 0:
        # No element in that list
        Domoticz.Debug("mgtLQIresp -  No element in that list ")
        return

    NwkIdSource = z_var.LQISource.get()
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
        _depth    = ListOfEntries[n+36:n+38]
        _lnkqty   = ListOfEntries[n+38:n+40]
        try:
            _bitmap   = int(ListOfEntries[n+40:n+42], 16)
        except:

            Domoticz.Log("mgtLQIresp - wrong bitmap :%s " %ListOfEntries[n+40:n+42])
            _bitmap = 0

        Domoticz.Debug("mgtLQIresp - error on _bitmap {0:b}".format(_bitmap))
        _devicetype   = _bitmap & 0b00000011
        _permitjnt    = (_bitmap & 0b00001100) >> 2
        _relationshp  = (_bitmap & 0b00110000) >> 4
        _rxonwhenidl  = (_bitmap & 0b11000000) >> 6

        if  _devicetype   == 0x00: _devicetype = 'Coordinator'
        elif  _devicetype == 0x01: _devicetype = 'Router'
        elif  _devicetype == 0x02: _devicetype = 'End Device'
        elif  _devicetype == 0x03: _devicetype = '??'

        if _relationshp   == 0x00: _relationshp = 'Parent'
        elif _relationshp == 0x01: _relationshp = 'Child'
        elif _relationshp == 0x02: _relationshp = 'Sibling'
        elif _relationshp == 0x03: _relationshp = 'None'

        if _permitjnt   == 0x00: _permitjnt = 'Off'
        elif _permitjnt == 0x01 : _permitjnt = 'On'
        elif _permitjnt == 0x02 : _permitjnt = '??'

        if _rxonwhenidl   == 0x00: _rxonwhenidl = 'Rx-Off'
        elif _rxonwhenidl == 0x01: _rxonwhenidl = 'Rx-On'
        elif _rxonwhenidl == 0x02: _rxonwhenidl = '??'
        n = n + 42
        Domoticz.Debug("mgtLQIresp - Table["+str(NeighbourTableEntries) + "] - " + " _nwkid = " +str(_nwkid) + " _extPANID = " +str(_extPANID) + \
                    " _ieee = " +str(_ieee) + " _depth = " +str(_depth) + " _lnkqty = " +str(_lnkqty) + " _devicetype = " +str(_devicetype) + \
                    " _permitjnt = " +str(_permitjnt) + " _relationshp = " +str(_relationshp) + " _rxonwhenidl = " +str(_rxonwhenidl))
    

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

        Domoticz.Debug("mgtLQIresp - from " +str(NwkIdSource) + " a new node captured: " +str(_nwkid))

    return
