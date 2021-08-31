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


from datetime import datetime
import time
import os.path
import json

import Domoticz

from Classes.AdminWidgets import AdminWidgets
from Classes.LoggingManagement import LoggingManagement


class NetworkMap:
    def __init__(self, PluginConf, ZigateComm, ListOfDevices, Devices, HardwareID, log):
        self.pluginconf = PluginConf
        self.ZigateComm = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.HardwareID = HardwareID
        self.log = log

        self._NetworkMapPhase = 0
        self.LQIreqInProgress = []
        self.LQIticks = 0
        self.Neighbours = {}  # Table of Neighbours

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
        self.logging("Log", "Network Topology progress: %s %%" % progress)

        for entry in list(self.Neighbours):
            if entry not in self.ListOfDevices:
                self.logging("Log", "LQIreq - device %s not found removing from the device to be scaned" % entry)
                # Most likely this device as been removed, or change it Short Id
                del self.Neighbours[entry]
                continue

            if self.Neighbours[entry]["Status"] == "Completed":
                continue

            elif self.Neighbours[entry]["Status"] in ("TimedOut", "NotReachable"):
                continue

            elif self.Neighbours[entry]["Status"] in ("WaitResponse", "WaitResponse2"):
                if len(self.LQIreqInProgress) > 0:
                    waitResponse = True
                else:
                    self.Neighbours[entry]["Status"] = "TimedOut"
                continue

            elif self.Neighbours[entry]["Status"] in ("ScanRequired", "ScanRequired2"):
                LQIreq(self, entry)

        else:
            # We have been through all list of devices and not action triggered
            if not waitResponse:
                self.logging("Debug", "continue_scan - scan completed, all Neighbour tables received.")
                finish_scan(self)
                self._NetworkMapPhase = 0


def _initNeighbours(self):
    # Will popoulate the Neghours dict with all Main Powered Devices
    self.logging("Debug", "_initNeighbours")

    # for nwkid in self.ListOfDevices:
    #    tobescanned = False
    #    if nwkid == '0000':
    #        tobescanned = True
    #    elif 'LogicalType' in self.ListOfDevices[nwkid]:
    #        if self.ListOfDevices[nwkid]['LogicalType'] == 'Router':
    #            tobescanned = True
    #        if 'DeviceType' in self.ListOfDevices[nwkid]:
    #            if self.ListOfDevices[nwkid]['DeviceType'] == 'FFD':
    #                tobescanned = True
    #        if 'MacCapa' in self.ListOfDevices[nwkid]:
    #            if self.ListOfDevices[nwkid]['MacCapa'] == '8e':
    #                tobescanned = True

    #    if not tobescanned:
    #        continue
    #    _initNeighboursTableEntry( self, nwkid )
    tobescanned = True
    _initNeighboursTableEntry(self, "0000")


def _initNeighboursTableEntry(self, nwkid):

    # Makes sure nwkid is known as a Router.
    if nwkid in self.ListOfDevices and not is_a_router(self, nwkid):
        self.logging("Error", "Found %s in a Neighbour table tag as a router, but is not" % nwkid)
        return

    self.logging("Debug", "_initNeighboursTableEntry - %s" % nwkid)
    self.Neighbours[nwkid] = {}
    self.Neighbours[nwkid]["Status"] = "ScanRequired"
    self.Neighbours[nwkid]["TableMaxSize"] = 0
    self.Neighbours[nwkid]["TableCurSize"] = 0
    self.Neighbours[nwkid]["Neighbours"] = {}


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
        if "DeviceType" in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]["DeviceType"] == "FFD":
                return True
        if "MacCapa" in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]["MacCapa"] == "8e":
                return True
    return False


def finish_scan(self):

    # Write the report onto file
    self.logging("Status", "Network Topology report")
    self.logging("Status", "------------------------------------------------------------------------------------------")
    self.logging("Status", "")
    self.logging(
        "Status",
        "%6s %6s %9s %11s %6s %4s %7s %7s"
        % ("Node", "Node", "Relation", "Type", "Deepth", "LQI", "Rx-Idle", "PmtJoin"),
    )

    for nwkid in self.Neighbours:
        # We will keep 3 versions of Neighbours
        if nwkid not in self.ListOfDevices:
            self.logging("Error", "finish_scan - %s not found in list Of Devices." % nwkid)
            continue

        if "Neighbours" not in self.ListOfDevices[nwkid]:
            self.ListOfDevices[nwkid]["Neighbours"] = []
        if not isinstance(self.ListOfDevices[nwkid]["Neighbours"], list):
            del self.ListOfDevices[nwkid]["Neighbours"]
            self.ListOfDevices[nwkid]["Neighbours"] = []

        if len(self.ListOfDevices[nwkid]["Neighbours"]) > 3:
            del self.ListOfDevices[nwkid]["Neighbours"][0]

        LOD_Neighbours = {}
        LOD_Neighbours["Time"] = 0
        LOD_Neighbours["Devices"] = []

        # Set Time when the Neighbours have been calaculated
        LOD_Neighbours["Time"] = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")

        if self.Neighbours[nwkid]["Status"] == "NotReachable":
            self.logging(
                "Status", "%6s %6s %9s %11s %6s %4s %7s %7s NotReachable" % (nwkid, "-", "-", "-", "-", "-", "-", "-")
            )
            LOD_Neighbours["Devices"].append("Not Reachable")
        elif self.Neighbours[nwkid]["Status"] == "TimedOut":
            self.logging(
                "Status", "%6s %6s %9s %11s %6s %4s %7s %7s TimedOut" % (nwkid, "-", "-", "-", "-", "-", "-", "-")
            )
            LOD_Neighbours["Devices"].append("Timed Out")
        else:
            for child in self.Neighbours[nwkid]["Neighbours"]:
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
                element = {}
                element[child] = {}
                element[child]["_relationshp"] = self.Neighbours[nwkid]["Neighbours"][child]["_relationshp"]
                element[child]["_devicetype"] = self.Neighbours[nwkid]["Neighbours"][child]["_devicetype"]
                element[child]["_depth"] = int(self.Neighbours[nwkid]["Neighbours"][child]["_depth"], 16)
                element[child]["_lnkqty"] = int(self.Neighbours[nwkid]["Neighbours"][child]["_lnkqty"], 16)
                element[child]["_rxonwhenidl"] = self.Neighbours[nwkid]["Neighbours"][child]["_rxonwhenidl"]
                element[child]["_IEEE"] = self.Neighbours[nwkid]["Neighbours"][child]["_ieee"]
                element[child]["_permitjnt"] = self.Neighbours[nwkid]["Neighbours"][child]["_permitjnt"]

                LOD_Neighbours["Devices"].append(element)

                storeLQIforEndDevice(
                    self, child, nwkid, int(self.Neighbours[nwkid]["Neighbours"][child]["_lnkqty"], 16)
                )

        self.ListOfDevices[nwkid]["Neighbours"].append(LOD_Neighbours)

    self.logging("Status", "--")

    prettyPrintNeighbours(self)

    storeLQI = {}
    storeLQI[int(time.time())] = dict(self.Neighbours)

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
            start = 0
            if nbentries >= maxNumReports:
                start = (nbentries - maxNumReports) + 1
            self.logging("Debug", "Rpt max: %s , New Start: %s, Len:%s " % (maxNumReports, start, nbentries))

            if nbentries != 0:
                fout.write("\n")
                fout.writelines(data[start:])
            fout.write("\n")
            json.dump(storeLQI, fout)
        # self.adminWidgets.updateNotificationWidget( Devices, 'A new LQI report is available')
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
        nwkid in self.ListOfDevices
        and "Health" in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]["Health"] == "Not Reachable"
    ):
        self.logging("Log", "LQIreq - skiping device %s which is Not Reachable" % nwkid)
        self.Neighbours[nwkid]["Status"] = "NotReachable"
        return

    self.logging("Debug", "004E %s" % datas)
    self.ZigateComm.sendData("004E", datas)


def LQIresp_decoding(self, MsgData):

    self.logging("Debug", "804E - %s" % (MsgData))

    NwkIdSource = None
    if len(self.LQIreqInProgress) > 0:
        NwkIdSource = self.LQIreqInProgress.pop()

    SQN = MsgData[0:2]
    Status = MsgData[2:4]
    NeighbourTableEntries = int(MsgData[4:6], 16)
    NeighbourTableListCount = int(MsgData[6:8], 16)
    StartIndex = int(MsgData[8:10], 16)
    ListOfEntries = MsgData[10 : 10 + 42 * NeighbourTableListCount]

    self.logging("Debug", "--- Entries: %s" % (ListOfEntries))

    if len(MsgData) == (10 + 42 * NeighbourTableListCount + 4):
        # Firmware 3.1a and aboce
        NwkIdSource = MsgData[10 + 42 * NeighbourTableListCount : len(MsgData)]
    self.logging("Debug", "LQIresp - MsgSrc: %s" % NwkIdSource)

    if NwkIdSource is None:
        return

    if Status != "00":
        self.logging(
            "Debug",
            "LQI:LQIresp - Status: %s for %s Sqn:%s (raw data: %s)"
            % (Status, MsgData[len(MsgData) - 4 : len(MsgData)], SQN, MsgData),
        )
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

    if (StartIndex + NeighbourTableListCount) == NeighbourTableEntries:
        self.logging(
            "Debug",
            "mgtLQIresp - We have received %3s entries out of %3s" % (NeighbourTableListCount, NeighbourTableEntries),
        )
        self.Neighbours[NwkIdSource]["TableCurSize"] = StartIndex + NeighbourTableListCount
        self.Neighbours[NwkIdSource]["Status"] = "Completed"
    else:
        self.logging(
            "Debug",
            "mgtLQIresp - We have received %3s entries out of %3s" % (NeighbourTableListCount, NeighbourTableEntries),
        )
        self.Neighbours[NwkIdSource]["Status"] = "ScanRequired"
        self.Neighbours[NwkIdSource]["TableCurSize"] = StartIndex + NeighbourTableListCount

    # Decoding the Table
    self.logging("Debug", "mgtLQIresp - ListOfEntries: %s" % len(ListOfEntries))
    n = 0
    while n < ((NeighbourTableListCount * 42)):
        if len(ListOfEntries[n:]) < 42:
            break
        self.logging("Debug", "--- -- Entry[%s] %s" % (n // 42, ListOfEntries[n : n + 42]))
        _nwkid = ListOfEntries[n : n + 4]  # uint16
        _extPANID = ListOfEntries[n + 4 : n + 20]  # uint64
        _ieee = ListOfEntries[n + 20 : n + 36]  # uint64

        _depth = ListOfEntries[n + 36 : n + 38]  # uint8
        _lnkqty = ListOfEntries[n + 38 : n + 40]  # uint8
        _bitmap = int(ListOfEntries[n + 40 : n + 42], 16)  # uint8

        _devicetype = _bitmap & 0b00000011
        _permitjnt = (_bitmap & 0b00001100) >> 2
        _relationshp = (_bitmap & 0b00110000) >> 4
        _rxonwhenidl = (_bitmap & 0b11000000) >> 6

        n = n + 42
        self.logging(
            "Debug",
            "--- --bitmap         : {0:{fill}8b}".format(_bitmap, fill="0")
            + " - %0X for ( %s, %s)" % (_bitmap, NwkIdSource, _nwkid),
        )
        self.logging("Debug", "--- ----> _devicetype: | | |- %02d" % _devicetype)
        self.logging("Debug", "--- ----> _permitjnt:  | | -%02d" % _permitjnt)
        self.logging("Debug", "--- ----> _relationshp:| -%02d" % _relationshp)
        self.logging("Debug", "--- ----> _rxonwhenidl:-%02d" % _rxonwhenidl)

        # s a 2-bit value representing the ZigBee device type of the neighbouring node
        if _devicetype == 0x00:
            _devicetype = "Coordinator"
        elif _devicetype == 0x01:
            _devicetype = "Router"
        elif _devicetype == 0x02:
            _devicetype = "End Device"
        elif _devicetype == 0x03:
            _devicetype = "??"

        if _permitjnt == 0x00:
            _permitjnt = "Off"
        elif _permitjnt == 0x01:
            _permitjnt = "On"
        elif _permitjnt == 0x02:
            _permitjnt = "??"

        # is a 3-bit value representing the neighbouring node’s relationship to the local node
        if _relationshp == 0x00:
            _relationshp = "Parent"
        elif _relationshp == 0x01:
            _relationshp = "Child"
        elif _relationshp == 0x02:
            _relationshp = "Sibling"
        elif _relationshp == 0x03:
            _relationshp = "None"
        elif _relationshp == 0x04:
            _relationshp = "Former Child"

        if _rxonwhenidl == 0x00:
            _rxonwhenidl = "Rx-Off"
        elif _rxonwhenidl == 0x01:
            _rxonwhenidl = "Rx-On"
        elif _rxonwhenidl == 0x02:
            _rxonwhenidl = "??"

        self.logging("Debug", "--- --mgtLQIresp - capture a new neighbour %s from %s" % (_nwkid, NwkIdSource))
        self.logging("Debug", "--- -----> _nwkid: %s" % (_nwkid))
        self.logging("Debug", "--- -----> _extPANID: %s" % _extPANID)
        self.logging("Debug", "--- -----> _ieee: %s" % _ieee)
        self.logging("Debug", "--- -----> _depth: %s" % _depth)
        self.logging("Debug", "--- -----> _lnkqty: %s" % _lnkqty)
        self.logging("Debug", "--- -----> _devicetype: %s" % _devicetype)
        self.logging("Debug", "--- -----> _permitjnt: %s" % _permitjnt)
        self.logging("Debug", "--- -----> _relationshp: %s" % _relationshp)
        self.logging("Debug", "--- -----> _rxonwhenidl: %s" % _rxonwhenidl)

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
                "Debug",
                "      - _extPANID:    %s  versus %s"
                % (_extPANID, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_extPANID"]),
            )
            self.logging(
                "Debug",
                "      - _ieee:        %s  versus %s"
                % (_ieee, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_ieee"]),
            )
            self.logging(
                "Debug",
                "      - _depth:       %s  versus %s"
                % (_depth, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_depth"]),
            )
            self.logging(
                "Debug",
                "      - _lnkqty:      %s  versus %s"
                % (_lnkqty, self.Neighbours[NwkIdSource]["Neighbours"][_nwkid]["_lnkqty"]),
            )
            self.logging(
                "Debug",
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
