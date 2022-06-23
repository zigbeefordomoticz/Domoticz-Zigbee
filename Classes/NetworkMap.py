#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
#
#    Module: NetworkMap.py
#
#    Description: Network Mapping based on LQI
#
#
#
#    Table Neighbours
#        self.Neighbours[ nwkdi ]
#                                ['Status'] ( 'Completed' /* table is completd (all entries collected */
#                                             'WaitResponse' /* Waiting for response */
#                                             'WaitResponse2' /* Waiting for response */
#                                             'ScanRequired' /* A scan is required to get more entries */
#                                             'ScanRequired2' /* A scan is required to get more entries */
#                                ['TableMaxSize'] Number of Expected entries
#                                ['TableCurSize'] Number of actual entries
#                                ['Neighbours'][ nwkid ]
#                                                       [attributes]
#


import json
import os.path
import time
from datetime import datetime

from Modules.zb_tables_management import (mgmt_rtg, start_new_table_scan,
                                          update_merge_new_device_to_last_entry)
from Zigbee.zdpCommands import zdp_NWK_address_request, zdp_nwk_lqi_request


class NetworkMap:
    def __init__(self, zigbee_communitation, PluginConf, ZigateComm, ListOfDevices, Devices, HardwareID, log):
        self.zigbee_communication = zigbee_communitation
        self.pluginconf = PluginConf
        self.ControllerLink = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.HardwareID = HardwareID
        self.log = log
        self.FirmwareVersion = None

        self._NetworkMapPhase = 0
        self.LQIreqInProgress = []
        self.LQIticks = 0
        self.Neighbours = {}  # Table of Neighbours

    def update_firmware(self, firmwareversion):
        self.FirmwareVersion = firmwareversion

    def logging(self, logType, message):
        self.log.logging("NetworkMap", logType, message)

    def NetworkMapPhase(self):
        return self._NetworkMapPhase

    def LQIresp(self, MsgData):
        LQIresp_decoding(self, MsgData)

    def start_scan(self):
        if len(self.Neighbours) != 0:
            self.logging("Debug", "start_scan - initialize data")
            del self.Neighbours
            self.Neighbours = {}
            
        self.ListOfDevices["0000"]["TopologyStartTime"] = int(time.time())
        
        _initNeighbours(self)
        # Start on Zigate Controler

        prettyPrintNeighbours(self)
        self._NetworkMapPhase = 2
        LQIreq(self)

    def continue_scan(self):

        self.logging("Debug", "len(self.LQIreqInProgress) - %s" % (len(self.LQIreqInProgress)))

        prettyPrintNeighbours(self)
        if len(self.LQIreqInProgress) > 0 and self.LQIticks < 2:
            self.logging("Debug", "continue_scan - Command pending")
            self.LQIticks += 1
            return

        if len(self.LQIreqInProgress) > 0 and self.LQIticks >= 2:
            entry = self.LQIreqInProgress.pop()
            self.logging("Debug", "Commdand pending Timeout: %s" % entry)
            if self.Neighbours[entry]["Status"] == "WaitResponse":
                self.Neighbours[entry]["Status"] = "ScanRequired2"
                self.logging("Debug", "LQI:continue_scan - Try one more for %s" % entry)
            elif self.Neighbours[entry]["Status"] == "WaitResponse2":
                self.Neighbours[entry]["Status"] = "TimedOut"
                self.logging("Debug", "LQI:continue_scan - TimedOut for %s" % entry)

            self.LQIticks = 0
            self.logging("Debug", "continue_scan - %s" % (len(self.LQIreqInProgress)))

        # We reach here because:
        # self.LQIreqInProgress == 0
        # self.LQIreqInProgress  0 and LQItick >= 2

        waitResponse = False
        progress = current_process = max_process = avg_size = 0
        for entry in list(self.Neighbours):
            if self.Neighbours[entry]["TableMaxSize"] > 0:
                avg_size = (avg_size + self.Neighbours[entry]["TableMaxSize"]) / 2
                current_process += self.Neighbours[entry]["TableCurSize"]
                max_process += self.Neighbours[entry]["TableMaxSize"]
            else:
                # If Max size is 0 (not yet started), then we take the Average size of known table
                max_process += avg_size
            self.logging(
                "Debug",
                "== Entry: %s Current: %s Max: %s"
                % (entry, self.Neighbours[entry]["TableCurSize"], self.Neighbours[entry]["TableMaxSize"]),
            )
        if max_process > 0:
            progress = int((current_process / max_process) * 100)
        self.logging("Status", "Network Topology progress: %s %%" % progress)

        for entry in list(self.Neighbours):
            if entry not in self.ListOfDevices:
                self.logging("Debug", "LQIreq - device %s not found removing from the device to be scaned" % entry)
                # Most likely this device as been removed, or change it Short Id
                del self.Neighbours[entry]
                continue

            if self.Neighbours[entry]["Status"] == "Completed":
                continue

            if self.Neighbours[entry]["Status"] in ("TimedOut", "NotReachable"):
                continue

            if self.Neighbours[entry]["Status"] in ("WaitResponse", "WaitResponse2"):
                if len(self.LQIreqInProgress) > 0:
                    waitResponse = True
                else:
                    self.Neighbours[entry]["Status"] = "TimedOut"
                continue

            elif self.Neighbours[entry]["Status"] in ("ScanRequired", "ScanRequired2"):
                LQIreq(self, entry)
                return

        # We have been through all list of devices and not action triggered
        if not waitResponse:
            self.logging("Debug", "continue_scan - scan completed, all Neighbour tables received.")
            
            finish_scan(self)
            self._NetworkMapPhase = 0


def _initNeighbours(self):
    # Will popoulate the Neghours dict with all Main Powered Devices
    self.logging("Debug", "_initNeighbours")
    _initNeighboursTableEntry(self, "0000")


def _initNeighboursTableEntry(self, nwkid):
    # Start discovering a new Router
    # Makes sure nwkid is known as a Router.
    if nwkid not in self.ListOfDevices or not is_a_router(self, nwkid):
        self.logging("Debug", "Found %s in a Neighbour table tag as a router, but is not" % nwkid)
        return

    start_new_table_scan(self, nwkid, "Neighbours")
    self.logging("Debug", "_initNeighboursTableEntry - %s" % nwkid)
    self.Neighbours[nwkid] = {"Status": "ScanRequired", "TableMaxSize": 0, "TableCurSize": 0, "Neighbours": {}}

    # New router, let's trigger Routing Table and Associated Devices
    if self.pluginconf.pluginConf["TopologyV2"]:
        mgmt_rtg(self, nwkid, "RoutingTable")
        if "IEEE" in self.ListOfDevices[ nwkid ]:
            zdp_NWK_address_request(self, nwkid, self.ListOfDevices[ nwkid ]['IEEE'], u8RequestType="01")


def is_a_router(self, nwkid):
    if nwkid == "0000":
        return True
    if nwkid not in self.ListOfDevices:
        return False

    if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in (
        "TI0001",
        "TS0011",
        "TS0013",
        "TS0601-switch",
        "TS0601-2Gangs-switch",
    ):
        return False

    if "LogicalType" in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]["LogicalType"] == "Router":
            return True
        if "DeviceType" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["DeviceType"] == "FFD":
            return True
        if "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] == "8e":
            return True
    return False


def finish_scan(self):

    # Write the report onto file
    self.logging("Status", "Network Topology report")
    self.logging("Status", "------------------------------------------------------------------------------------------")
    self.logging("Status", "")
    self.logging( "Status", "%6s %6s %9s %11s %6s %4s %7s %7s" % ("Node", "Node", "Relation", "Type", "Deepth", "LQI", "Rx-Idle", "PmtJoin"), )

    for nwkid in self.Neighbours:
        self.logging("Debug", "Network Topology report -- %s" %nwkid)
        # We will keep 3 versions of Neighbours
        if nwkid not in self.ListOfDevices:
            self.logging("Error", "finish_scan - %s not found in list Of Devices." % nwkid)
            self.logging("Debug", "Network Topology report -- %s not found" %nwkid)
            continue

        if self.Neighbours[nwkid]["Status"] == "NotReachable":
            self.logging( "Status", "%6s %6s %9s %11s %6s %4s %7s %7s NotReachable" % (nwkid, "-", "-", "-", "-", "-", "-", "-") )
            self.logging("Debug", "Network Topology report -- %s not reachable" %nwkid)
            continue

        if self.Neighbours[nwkid]["Status"] == "TimedOut":
            self.logging( "Status", "%6s %6s %9s %11s %6s %4s %7s %7s TimedOut" % (nwkid, "-", "-", "-", "-", "-", "-", "-") )
            self.logging("Debug", "Network Topology report -- %s Timeout" %nwkid)
            continue

        element = {}
        for child in self.Neighbours[nwkid]["Neighbours"]:
            element[ child ] = {}
            self.logging(
                "Status",
                "%6s %6s %9s %11s %6d %4d %7s %7s"
                % (
                    nwkid,
                    child,
                    self.Neighbours[nwkid]["Neighbours"][child]["_relationshp"],
                    self.Neighbours[nwkid]["Neighbours"][child]["_devicetype"],
                    int(self.Neighbours[nwkid]["Neighbours"][child]["_depth"], 16),
                    int(self.Neighbours[nwkid]["Neighbours"][child]["_lnkqty"], 16),
                    self.Neighbours[nwkid]["Neighbours"][child]["_rxonwhenidl"],
                    self.Neighbours[nwkid]["Neighbours"][child]["_permitjnt"],
                ),
            )
            element[child]["_relationshp"] = self.Neighbours[nwkid]["Neighbours"][child]["_relationshp"]
            element[child]["_devicetype"] = self.Neighbours[nwkid]["Neighbours"][child]["_devicetype"]
            element[child]["_depth"] = int(self.Neighbours[nwkid]["Neighbours"][child]["_depth"], 16)
            element[child]["_lnkqty"] = int(self.Neighbours[nwkid]["Neighbours"][child]["_lnkqty"], 16)
            element[child]["_rxonwhenidl"] = self.Neighbours[nwkid]["Neighbours"][child]["_rxonwhenidl"]
            element[child]["_IEEE"] = self.Neighbours[nwkid]["Neighbours"][child]["_ieee"]
            element[child]["_permitjnt"] = self.Neighbours[nwkid]["Neighbours"][child]["_permitjnt"]

            storeLQIforEndDevice( self, child, nwkid, int(self.Neighbours[nwkid]["Neighbours"][child]["_lnkqty"], 16) )
        update_merge_new_device_to_last_entry(self, nwkid, "Neighbours", element )

    self.logging("Status", "--")
    prettyPrintNeighbours(self)

    storeLQI = { int(self.ListOfDevices["0000"]["TopologyStartTime"]): dict(self.Neighbours) }

    if not self.pluginconf.pluginConf["TopologyV2"]:
        save_report_to_file(self, storeLQI)
    del self.ListOfDevices["0000"]["TopologyStartTime"]
    
def save_report_to_file(self, storeLQI):
    _filename = self.pluginconf.pluginConf["pluginReports"] + "NetworkTopology-v3-" + "%02d" % self.HardwareID + ".json"
    if os.path.isdir(self.pluginconf.pluginConf["pluginReports"]):

        nbentries = 0
        if os.path.isfile(_filename):
            with open(_filename, "r") as fin:
                data = fin.read().splitlines(True)
                nbentries = len(data)

        with open(_filename, "w") as fout:
            # we need to short the list by todayNumReports - todayNumReports - 1
            maxNumReports = self.pluginconf.pluginConf["numTopologyReports"]
            start = (nbentries - maxNumReports) + 1 if nbentries >= maxNumReports else 0
            self.logging("Debug", "Rpt max: %s , New Start: %s, Len:%s " % (maxNumReports, start, nbentries))

            if nbentries != 0:
                fout.write("\n")
                fout.writelines(data[start:])
            fout.write("\n")
            json.dump(storeLQI, fout)
    else:
        self.logging(
            "Error",
            "LQI:Unable to get access to directory %s, please check PluginConf.txt"
            % (self.pluginconf.pluginConf["pluginReports"]),
        )
    

def prettyPrintNeighbours(self):

    for nwkid in self.Neighbours:
        self.logging(
            "Debug",
            "Neighbours table: %s, %s out of %s - Status: %s"
            % (
                nwkid,
                self.Neighbours[nwkid]["TableCurSize"],
                self.Neighbours[nwkid]["TableMaxSize"],
                self.Neighbours[nwkid]["Status"],
            ),
        )
        for entry in self.Neighbours[nwkid]["Neighbours"]:
            self.logging(
                "Debug",
                "---> Neighbour %s ( %s )" % (entry, self.Neighbours[nwkid]["Neighbours"][entry]["_relationshp"]),
            )
    self.logging("Debug", "")


def storeLQIforEndDevice(self, child, router, lqi):
    if child not in self.ListOfDevices:
        return
    if "MapLQI" not in self.ListOfDevices[child]:
        self.ListOfDevices[child]["MapLQI"] = {}
    self.ListOfDevices[child]["MapLQI"][router] = lqi


def LQIreq(self, nwkid="0000"):
    """
    Send a Management LQI request
    This function requests a remote node to provide a list of neighbouring nodes, from its Neighbour table,
    including LQI (link quality) values for radio transmissions from each of these nodes.
    The destination node of this request must be a Router or the Co- ordinator.
        <Target Address: uint16_t>
        <Start Index: uint8_t>
    """

    self.logging("Debug", "LQIreq - nwkid: %s" % nwkid)

    if nwkid not in self.Neighbours:
        _initNeighboursTableEntry(self, nwkid)
        
    tobescanned = False
    if nwkid != "0000" and nwkid not in self.ListOfDevices:
        return

    if not is_a_router(self, nwkid):
        self.logging("Debug", "Skiping %s as it's not a Router nor Coordinator, removing the entry" % nwkid)
        if nwkid in self.Neighbours:
            del self.Neighbours[nwkid]
        return

    # u8StartIndex is the Neighbour table index of the first entry to be included in the response to this request
    index = self.Neighbours[nwkid]["TableCurSize"]

    self.LQIreqInProgress.append(nwkid)
    datas = "%s%02X" % (nwkid, index)

    self.logging("Debug", "LQIreq - from: %s start at index: %s" % (nwkid, index))
    if self.Neighbours[nwkid]["Status"] == "ScanRequired":
        self.Neighbours[nwkid]["Status"] = "WaitResponse"

    elif self.Neighbours[nwkid]["Status"] == "ScanRequired2":
        self.Neighbours[nwkid]["Status"] = "WaitResponse2"

    if (
        nwkid != "0000"
        and nwkid in self.ListOfDevices
        and "Health" in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]["Health"] == "Not Reachable"
    ):
        self.logging("Debug", "LQIreq - skiping device %s which is Not Reachable" % nwkid)
        self.Neighbours[nwkid]["Status"] = "NotReachable"
        return

    self.logging("Debug", "zdp_nwk_lqi_request %s" % datas)
    zdp_nwk_lqi_request( self, nwkid, "%02x" %index)
    #self.ControllerLink.sendData("004E", datas)


def LQIresp_decoding(self, MsgData):

    self.logging("Debug", "804E - %s" % (MsgData))

    NwkIdSource = None
    if len(self.LQIreqInProgress) > 0:
        NwkIdSource = self.LQIreqInProgress.pop()

    if len(MsgData) < 10:
        self.logging("Error", "LQIresp_decoding - Incomplete message: %s (%s)" %(MsgData, len(MsgData)))
        return

    SQN = MsgData[:2]
    Status = MsgData[2:4]
    NeighbourTableEntries = int(MsgData[4:6], 16)
    NeighbourTableListCount = int(MsgData[6:8], 16)
    StartIndex = int(MsgData[8:10], 16)
    ListOfEntries = MsgData[10 : 10 + 42 * NeighbourTableListCount]

    self.logging("Debug", "--- Entries: %s" % (ListOfEntries))

    if len(MsgData) == (10 + 42 * NeighbourTableListCount + 4):
        # Firmware 3.1a and aboce
        NwkIdSource = MsgData[10 + 42 * NeighbourTableListCount:]
    self.logging("Debug", "LQIresp - MsgSrc: %s" % NwkIdSource)

    if NwkIdSource is None:
        return

    if Status != "00":
        self.logging("Debug", ("LQI:LQIresp - Status: %s for %s Sqn:%s (raw data: %s)" % (Status, MsgData[len(MsgData) - 4 :], SQN, MsgData)))

        return

    if len(ListOfEntries) // 42 != NeighbourTableListCount:
        self.logging(
            "Error",
            "LQI:LQIresp - missmatch. Expecting %s entries and found %s"
            % (NeighbourTableListCount, len(ListOfEntries) // 42),
        )

    self.logging("Debug", "self.LQIreqInProgress = %s" % len(self.LQIreqInProgress))
    self.logging(
        "Debug",
        "LQIresp - %s Status: %s, NeighbourTableEntries: %s, StartIndex: %s, NeighbourTableListCount: %s"
        % (NwkIdSource, Status, NeighbourTableEntries, StartIndex, NeighbourTableListCount),
    )

    if NwkIdSource not in self.Neighbours:
        # Un expected request. May be due to an async request
        return

    if not self.Neighbours[NwkIdSource]["TableMaxSize"] and NeighbourTableEntries:
        self.Neighbours[NwkIdSource]["TableMaxSize"] = NeighbourTableEntries
        self.ListOfDevices[NwkIdSource]["NeighbourTableSize"] = self.Neighbours[NwkIdSource]["TableMaxSize"]

    if not NeighbourTableListCount and not NeighbourTableEntries:
        # No element in that list
        self.logging("Debug", "LQIresp -  No element in that list ")
        self.Neighbours[NwkIdSource]["Status"] = "Completed"
        return

    self.logging(
        "Debug",
        "mgtLQIresp - We have received %3s entries out of %3s" % (NeighbourTableListCount, NeighbourTableEntries),
    )
    if (StartIndex + NeighbourTableListCount) == NeighbourTableEntries:
        self.Neighbours[NwkIdSource]["TableCurSize"] = StartIndex + NeighbourTableListCount
        self.Neighbours[NwkIdSource]["Status"] = "Completed"
    else:
        self.Neighbours[NwkIdSource]["Status"] = "ScanRequired"
        self.Neighbours[NwkIdSource]["TableCurSize"] = StartIndex + NeighbourTableListCount

    # Decoding the Table
    self.logging("Debug", "mgtLQIresp - ListOfEntries: %s" % len(ListOfEntries))
    n = 0
    while n < ((NeighbourTableListCount * 42)) and len(ListOfEntries[n:]) >= 42:
        self.logging("Debug2", "--- -- Entry[%s] %s" % (n // 42, ListOfEntries[n : n + 42]))
        _nwkid = ListOfEntries[n : n + 4]  # uint16
        _extPANID = ListOfEntries[n + 4 : n + 20]  # uint64
        _ieee = ListOfEntries[n + 20 : n + 36]     # uint64
        _depth = ListOfEntries[n + 36 : n + 38]    # uint8
        _lnkqty = ListOfEntries[n + 38 : n + 40]   # uint8
        _bitmap = int(ListOfEntries[n + 40 : n + 42], 16)  # uint8
        _devicetype = _bitmap & 0b00000011
        _permitjnt = (_bitmap & 0b00001100) >> 2
        _relationshp = (_bitmap & 0b00110000) >> 4
        _rxonwhenidl = (_bitmap & 0b11000000) >> 6

        n += 42

        if int(_ieee, 16) in {0x00, 0xFFFFFFFFFFFFFFFF}:
            self.logging(
                "Debug",
                "Network Topology ignoring invalid neighbor: %s (%s)" %( _ieee, ListOfEntries[n : n + 42])
            )
            continue


        self.logging(
            "Debug2",
            "--- --bitmap         : {0:{fill}8b}".format(_bitmap, fill="0")
            + " - %0X for ( %s, %s)" % (_bitmap, NwkIdSource, _nwkid),
        )
        self.logging("Debug2", "--- ----> _devicetype: | | |- %02d" % _devicetype)
        self.logging("Debug2", "--- ----> _permitjnt:  | | -%02d" % _permitjnt)
        self.logging("Debug2", "--- ----> _relationshp:| -%02d" % _relationshp)
        self.logging("Debug2", "--- ----> _rxonwhenidl:-%02d" % _rxonwhenidl)

        # s a 2-bit value representing the ZigBee device type of the neighbouring node
        DEVICE_TYPE = {
            0x00: "Coordinator",
            0x01: "Router",
            0x02: "End Device",
            0x03: "??",
        }
        if _devicetype in DEVICE_TYPE:
            _devicetype = DEVICE_TYPE[ _devicetype ]

        PERMIT_JOIN_MODE = {
            0x00: "Off",
            0x01: "On",
            0x02: "??"
        }
        if _permitjnt in PERMIT_JOIN_MODE:
            _permitjnt = PERMIT_JOIN_MODE[ _permitjnt ]

        # is a 3-bit value representing the neighbouring node’s relationship to the local node
        RELATIONSHIP = {
            0x00: "Parent",
            0x01: "Child",
            0x02: "Sibling",
            0x03: "None",
            0x04: "Former Child",
        }
        if _relationshp in RELATIONSHIP:
            _relationshp = RELATIONSHIP[ _relationshp ]

        RXONIDLE = {
            0x00: "Rx-Off",
            0x01: "Rx-On",
            0x02: "??"
        }
        if _rxonwhenidl in RXONIDLE:
            _rxonwhenidl = RXONIDLE[ _rxonwhenidl ]

        self.logging("Debug2", "--- --mgtLQIresp - capture a new neighbour %s from %s" % (_nwkid, NwkIdSource))
        self.logging("Debug2", "--- -----> _nwkid: %s" % (_nwkid))
        self.logging("Debug2", "--- -----> _extPANID: %s" % _extPANID)
        self.logging("Debug2", "--- -----> _ieee: %s" % _ieee)
        self.logging("Debug2", "--- -----> _depth: %s" % _depth)
        self.logging("Debug2", "--- -----> _lnkqty: %s" % _lnkqty)
        self.logging("Debug2", "--- -----> _devicetype: %s" % _devicetype)
        self.logging("Debug2", "--- -----> _permitjnt: %s" % _permitjnt)
        self.logging("Debug2", "--- -----> _relationshp: %s" % _relationshp)
        self.logging("Debug2", "--- -----> _rxonwhenidl: %s" % _rxonwhenidl)

        if (
            _nwkid not in self.Neighbours
            and _devicetype in ("Router",)
            and _relationshp in ("Parent", "Child", "Sibling")
        ):
            self.logging("Debug", "===========> Adding %s in scanner queue" % _nwkid)
            _initNeighboursTableEntry(self, _nwkid)

        if _nwkid in self.Neighbours[NwkIdSource]["Neighbours"] and _relationshp not in ("Parent", "Child"):
            self.logging("Debug", "LQI:LQIresp - %s already in Neighbours Table for %s" % (_nwkid, NwkIdSource))
            # Let's check the infos
            self.logging(
                "Debug2",
                "      - _extPANID:    %s  versus %s"
                % (_extPANID, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_extPANID"]),
            )
            self.logging(
                "Debug2",
                "      - _ieee:        %s  versus %s"
                % (_ieee, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_ieee"]),
            )
            self.logging(
                "Debug2",
                "      - _depth:       %s  versus %s"
                % (_depth, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_depth"]),
            )
            self.logging(
                "Debug2",
                "      - _lnkqty:      %s  versus %s"
                % (_lnkqty, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_lnkqty"]),
            )
            self.logging(
                "Debug2",
                "      - _relationshp: %s  versus %s"
                % (_relationshp, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_relationshp"]),
            )
            return

        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid] = {}
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_extPANID"] = _extPANID
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_ieee"] = _ieee
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_depth"] = _depth
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_lnkqty"] = _lnkqty
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_devicetype"] = _devicetype
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_permitjnt"] = _permitjnt
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_relationshp"] = _relationshp
        self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_rxonwhenidl"] = _rxonwhenidl