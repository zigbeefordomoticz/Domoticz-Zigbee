#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: NetworkEnergy.py

    Description: Network Energy/Interferences 

"""
"""
    self.EnergyLevel[ nwkid ]
                            ['Status'] ( 'Completed' /* table is completd (all entries collected */
                                         'WaitResponse' /* Waiting for response */
                                         'WaitResponse2' /* Waiting for response */
                                         'ScanRequired' /* A scan is required to get more entries */
                                         'ScanRequired2' /* A scan is required to get more entries */
                            ['Channels'][ Num ] /* Energy Level by Channel for corresponding nwkid
"""


import datetime
from time import time
import os.path
import json

import Domoticz
from Modules.output import sendZigateCmd, maskChannel
from Classes.AdminWidgets import AdminWidgets

CHANNELS = [ '11','15','19','20','25','26']

class NetworkEnergy():

    def __init__( self, PluginConf, ZigateComm, ListOfDevices, Devices, HardwareID):

        self.pluginconf = PluginConf
        self.ZigateComm = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.HardwareID = HardwareID

        self.EnergyLevel = None
        self.ScanInProgress = False
        self.nwkidInQueue = []
        self.ticks = 0


    def _initNwkEnrgy( self, target='0000', channels=0):

        Domoticz.Debug("_initNwkEnrgy - target: %s, channels: %s" %(target, channels))

        if self.EnergyLevel:
            del self.EnergyLevel

        self.EnergyLevel = {}


        if target == '0000':
            # We do a full scan
            for nwkid in self.ListOfDevices:

                router = False
                if nwkid == '0000':
                    continue
                if 'LogicalType' in self.ListOfDevices[nwkid]:
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
                self._initNwkEnrgyRecord( nwkid , channels)
        else:
            # We target only this target
            router = False
            if target in self.ListOfDevices:
                if 'LogicalType' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['LogicalType'] == 'Router':
                        router = True
                if 'DeviceType' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['DeviceType'] == 'FFD':
                        router = True
                if 'MacCapa' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['MacCapa'] == '8e':
                        router = True
                if router:
                    self._initNwkEnrgyRecord( target, channels )
        return


    def _initNwkEnrgyRecord( self, nwkid, channels):

        self.EnergyLevel[ nwkid ] = {}
        self.EnergyLevel[ nwkid ][ 'Status' ]  = 'ScanRequired'
        self.EnergyLevel[ nwkid ][ 'Tx' ]  =  None
        self.EnergyLevel[ nwkid ][ 'Failure' ]  = None
        self.EnergyLevel[ nwkid ][ 'Channels' ]  = {}
        for i in channels:
            self.EnergyLevel[ nwkid ][ 'Channels' ][ i ]  = None


    def prettyPrintNwkEnrgy( self ):

        for i in self.EnergyLevel:
            Domoticz.Log("%s : %s" %(i, self.EnergyLevel[i]['Status']))
            if self.EnergyLevel[i]['Status'] == 'Completed':
                Domoticz.Log("---> Tx: %s" %(self.EnergyLevel[i]['Tx']))
                Domoticz.Log("---> Failure: %s" %(self.EnergyLevel[i]['Failure']))
                for c in self.EnergyLevel[i]['Channels']:
                    Domoticz.Log("---> %s: %s" %(c, self.EnergyLevel[i]['Channels'][c]))
        Domoticz.Debug("")

    def NwkScanReq(self, target, channels):

        # Scan Duration
        scanDuration = 0x04 #
        scanCount = 1

        mask = maskChannel( channels )
        datas = target + "%08.x" %(mask) + "%02.x" %(scanDuration) + "%02.x" %(scanCount) 
    
        if len(self.nwkidInQueue) == 0:
            Domoticz.Debug("NwkScanReq - request a scan on channels %s for duration %s an count %s" \
                %( channels, scanDuration, scanCount))
            Domoticz.Debug("NwkScan - %s %s" %("004A", datas))
            self.nwkidInQueue.append( target )
            sendZigateCmd(self, "004A", datas )
            self.EnergyLevel[ target ]['Status'] = 'WaitResponse'
            self.ticks = 0


    def start_scan( self, target=None, channels=None):

        Domoticz.Debug("start_scan")
        if self.ScanInProgress:
            Domoticz.Log("a Scan is already in progress")
            return
        self.ScanInProgress = True

        if target is None:
            # Target will be all Routers
            target = '0000'
        if channels is None:
            # All channels
            channels = CHANNELS
        self._initNwkEnrgy( target, channels)
        self._next_scan()

    def do_scan(self, target=None, channels=None):

        if self.ScanInProgress:
            self._next_scan()

    def _next_scan( self ):

        self.ticks += 1
        waitResponse = False
        for i in self.EnergyLevel:
            if self.EnergyLevel[ i ]['Status'] == 'Completed':
                continue
            elif self.EnergyLevel[ i ]['Status'] == 'TimedOut':
                continue
            elif self.EnergyLevel[ i ]['Status'] == 'WaitResponse':
                waitResponse = True
                if self.ticks > 2:
                    self.EnergyLevel[ i ]['Status'] = 'TimedOut'
                    if len(self.nwkidInQueue) > 0:
                        entry = self.nwkidInQueue.pop()
                        if i != entry:
                            Domoticz.Error("Mismatch %s versus %s" %(i, entry))
                continue
            elif self.EnergyLevel[ i ]['Status'] == 'ScanRequired':
                _channels = []
                for c in self.EnergyLevel[ i ]['Channels']:
                    _channels.append( c )
                self.NwkScanReq( i, _channels)
                break
        else:
            #No more to Scan
            if not waitResponse:
                self.finish_scan()

            

    def finish_scan( self ):

        Domoticz.Debug("Finish_scan")
        self.ScanInProgress = False

        stamp = int(time())
        storeEnergy = {}
        storeEnergy[stamp] = []
        Domoticz.Status("Network Energy Level Report")
        Domoticz.Status("-----------------------------------------------")
        Domoticz.Status("%5s %6s %8s %4s %4s %4s %4s %4s %4s" %('nwkid', 'Tx', 'Failure', '11','15','19','20','25','26'))
        for nwkid in self.EnergyLevel:
            if self.EnergyLevel[nwkid]['Status'] != 'Completed':
                continue
            entry = {}
            entry['_NwkId'] = nwkid
            entry['Tx'] = self.EnergyLevel[ nwkid ][ 'Tx' ]
            entry['Failure'] = self.EnergyLevel[ nwkid ][ 'Failure' ]
            entry['Channels'] = []
            if 'ZDeviceName' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['ZDeviceName'] != {}:
                    entry['ZDeviceName'] = self.ListOfDevices[nwkid]['ZDeviceName']
                else:
                    entry['ZDeviceName'] = nwkid

            toprint = "%5s %6s %8s" %(nwkid, self.EnergyLevel[ nwkid ][ 'Tx' ], self.EnergyLevel[ nwkid ][ 'Failure' ])
            for c in self.EnergyLevel[ nwkid ]['Channels']:
               channels = {}
               channels['Channel'] = c
               channels['Level'] = self.EnergyLevel[ nwkid ]['Channels'][ c ]
               entry['Channels'].append( channels )
               toprint += " %4s" %self.EnergyLevel[ nwkid ]['Channels'][ c ]
            storeEnergy[stamp].append( entry )
            Domoticz.Status(toprint)

        Domoticz.Debug("Network Energly Level Report: %s" %storeEnergy)

        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkEnergy-' + '%02d' %self.HardwareID + '.json'
        if os.path.isdir( self.pluginconf.pluginConf['pluginReports'] ):
            with open( _filename, 'at') as json_file:
                json_file.write('\n')
                json.dump( storeEnergy, json_file)
        else:
            Domoticz.Error("Unable to get access to directory %s, please check PluginConf.txt" %(self.pluginconf.pluginConf['pluginReports']))

        return


    def NwkScanResponse(self, MsgData):

        MsgSequenceNumber=MsgData[0:2]
        MsgDataStatus=MsgData[2:4]
        MsgTotalTransmission=MsgData[4:8]
        MsgTransmissionFailures=MsgData[8:12]
        MsgScannedChannel=MsgData[12:20]
        MsgScannedChannelListCount=MsgData[20:22]
        MsgChannelListInterference=MsgData[22:len(MsgData)]

        #Decode the Channel mask received
        CHANNELS = { 11: 0x00000800, 12: 0x00001000, 13: 0x00002000, 14: 0x00004000,
                15: 0x00008000, 16: 0x00010000, 17: 0x00020000, 18: 0x00040000,
                19: 0x00080000, 20: 0x00100000, 21: 0x00200000, 22: 0x00400000,
                23: 0x00800000, 24: 0x01000000, 25: 0x02000000, 26: 0x04000000 }

        if MsgDataStatus != '00':
            Domoticz.Error("NwkScanResponse - Status: %s with Data: %s" %(MsgDataStatus, MsgData))

        if len(self.nwkidInQueue) > 0:
            entry = self.nwkidInQueue.pop()
        else:
            Domoticz.Error("NwkScanResponse - unexected message %s" %MsgData)
            return

        channelList = []
        for channel in CHANNELS:
            if int(MsgScannedChannel,16) & CHANNELS[channel]:
                channelList.append( channel )

        channelListInterferences = []
        idx = 0
        while idx < len(MsgChannelListInterference):
            channelListInterferences.append( "%X" %(int(MsgChannelListInterference[idx:idx+2],16)))
            idx += 2

        Domoticz.Debug("NwkScanResponse - SQN: %s, Tx: %s , Failures: %s , Status: %s) " \
                %(MsgSequenceNumber, int(MsgTotalTransmission,16), int(MsgTransmissionFailures,16), MsgDataStatus) )

        self.EnergyLevel[ entry ][ 'Tx' ]  =   int(MsgTotalTransmission,16)
        self.EnergyLevel[ entry ][ 'Failure' ]  =  int(MsgTransmissionFailures,16)

        for chan, inter in zip( channelList, channelListInterferences ):
            if chan in CHANNELS:
                self.EnergyLevel[ entry ]['Channels'][ str(chan) ] = int(inter,16)
                Domoticz.Debug("     Channel: %s Interference: : %s " %(chan, int(inter,16)))

        self.EnergyLevel[ entry ]['Status'] = 'Completed'
        return

