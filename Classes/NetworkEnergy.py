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


from datetime import datetime
from time import time
import os.path
import json

import Domoticz
from Modules.basicOutputs import sendZigateCmd, maskChannel
from Classes.AdminWidgets import AdminWidgets

CHANNELS = [ '11', '12', '13','14','15','16','17','18','19','20','21','22','23','24','25','26']
DURATION = 0x03

class NetworkEnergy():

    def __init__( self, PluginConf, ZigateComm, ListOfDevices, Devices, HardwareID, loggingFileHandle):

        self.pluginconf = PluginConf
        self.ZigateComm = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.HardwareID = HardwareID
        self.loggingFileHandle = loggingFileHandle

        self.EnergyLevel = None
        self.ScanInProgress = False
        self.nwkidInQueue = []
        self.ticks = 0

    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Status( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Status( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Status( message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Log( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def _loggingDebug( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def logging( self, logType, message):

        self.debugNetworkEnergy = self.pluginconf.pluginConf['debugNetworkEnergy']
        if logType == 'Debug' and self.debugNetworkEnergy:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)
        return


    def _initNwkEnrgy( self, root=None, target=None, channels=0):

        def isRouter( nwkid ):
            router = False
            if nwkid == '0000': 
                router = True
            else:
                if 'LogicalType' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['LogicalType'] == 'Router':
                        router = True
                if 'DeviceType' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['DeviceType'] == 'FFD':
                        router = True
                if 'MacCapa' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['MacCapa'] == '8e':
                        router = True
            return router


        self.logging( 'Debug', "_initNwkEnrgy - root: %s target: %s, channels: %s" %(root, target, channels))
        if self.EnergyLevel:
            del self.EnergyLevel

        self.EnergyLevel = {}
        
        if target == root == '0000':
            lstdev = list(self.ListOfDevices)
            if '0000' not in lstdev:
                lstdev.append( '0000' )
            for r in lstdev:
                if isRouter( r ):
                    self.EnergyLevel[ r ] = {}
                    for nwkid in self.ListOfDevices:
                        if nwkid == '0000': continue
                        if nwkid == r: continue
                        if 'Health' in self.ListOfDevices[nwkid]:
                            Domoticz.Log("_initNwkEnrgy %s - >%s<" %(nwkid, self.ListOfDevices[nwkid]['Health']))
                            if self.ListOfDevices[nwkid]['Health'] == 'Not Reachable':
                                self.logging( 'Log', "_initNwkEnrgy - skiping device %s which is Not Reachable" %nwkid)
                                continue
                        if not isRouter( nwkid ):
                            continue
                        self._initNwkEnrgyRecord( r, nwkid , channels)
        elif target == '0000':
            # We do a full scan but only for the Zigate controller
            root = '0000'
            self.EnergyLevel[root] = {}
            for nwkid in self.ListOfDevices:
                if nwkid == '0000': continue
                if not isRouter( nwkid ):
                    continue
                self._initNwkEnrgyRecord( root, nwkid , channels)
        elif target is not None and root is not None:
            # We target only this target
            if target in self.ListOfDevices:
                if isRouter( target ):
                    self._initNwkEnrgyRecord( root, target, channels )
        return


    def _initNwkEnrgyRecord( self, root, nwkid, channels):

        self.logging( 'Debug', "_initNwkEnrgyRecord %s <-> %s" %(root, nwkid))

        if nwkid not in self.EnergyLevel[root]:
            self.EnergyLevel[ root ][ nwkid ] = {}
        self.EnergyLevel[ root ][ nwkid ][ 'Status' ]  = 'ScanRequired'
        self.EnergyLevel[ root ][ nwkid ][ 'Tx' ]  =  None
        self.EnergyLevel[ root ][ nwkid ][ 'Failure' ]  = None
        self.EnergyLevel[ root ][ nwkid ][ 'Channels' ]  = {}
        for i in channels:
            self.EnergyLevel[ root ][ nwkid ][ 'Channels' ][ i ]  = None

    def prettyPrintNwkEnrgy( self ):

        for r in self.EnergyLevel:
            for i in self.EnergyLevel[ r ]:
                Domoticz.Log("%s <-> %s : %s" %(r, i, self.EnergyLevel[r][i]['Status']))
                if self.EnergyLevel[i]['Status'] == 'Completed':
                    Domoticz.Log("---> Tx: %s" %(self.EnergyLevel[r][i]['Tx']))
                    Domoticz.Log("---> Failure: %s" %(self.EnergyLevel[r][i]['Failure']))
                    for c in self.EnergyLevel[r][i]['Channels']:
                        Domoticz.Log("---> %s: %s" %(c, self.EnergyLevel[r][i]['Channels'][c]))
        self.logging( 'Debug', "")

    def NwkScanReq(self, root, target, channels):

        # Scan Duration
        scanDuration = DURATION
        scanCount = 1

        mask = maskChannel( channels )
        datas = target + "%08.x" %(mask) + "%02.x" %(scanDuration) + "%02.x" %(scanCount)  + "00" + root
    
        if len(self.nwkidInQueue) == 0:
            self.logging( 'Debug', "NwkScanReq - request a scan on channels %s for duration %s an count %s" \
                %( channels, scanDuration, scanCount))
            self.logging( 'Debug', "NwkScan - %s %s" %("004A", datas))
            self.nwkidInQueue.append( ( root, target) )
            sendZigateCmd(self, "004A", datas )
            self.EnergyLevel[ root ][ target ]['Status'] = 'WaitResponse'
            self.ticks = 0


    def start_scan( self, root=None, target=None, channels=None):

        self.logging( 'Debug', "start_scan")
        if self.ScanInProgress:
            Domoticz.Log("a Scan is already in progress")
            return
        self.ScanInProgress = True

        if channels is None:
            # All channels
            channels = CHANNELS
        if root == target == '0000':
            # We will do a full cross-scan
            self._initNwkEnrgy( root, target, channels)

        elif root is None and target is None:
            # Default
            # Target will be all Routers with Zigate
            self._initNwkEnrgy( None, '0000', channels)

        self._next_scan()

    def do_scan(self, root=None, target=None, channels=None):

        if self.ScanInProgress:
            self._next_scan()

    def _next_scan( self ):

        self.logging( 'Debug', "_next_scan")
        self.ticks += 1
        allRootCompleted = True
        self.logging( 'Debug', "_next_scan - To be scan: %s" %list(self.EnergyLevel))
        for r in self.EnergyLevel:
            waitResponse = False
            breakfromabove = False
            self.logging( 'Debug', "_next_scan - %s against %s" %(r, list(self.EnergyLevel[ r ])))
            for i in self.EnergyLevel[ r ]:
                self.logging( 'Debug', "--> _next_scan - %s <-> %s %s" %(r,i,self.EnergyLevel[ r ][ i ]['Status']))
                if self.EnergyLevel[ r ][ i ]['Status'] == 'Completed':
                    continue
                elif self.EnergyLevel[ r ][ i ]['Status'] == 'TimedOut':
                    continue
                elif self.EnergyLevel[ r ][ i ]['Status'] == 'WaitResponse':
                    waitResponse = True
                    allRootCompleted = False
                    if self.ticks > 2:
                        self.logging( 'Debug', "--> _next_scan - %s <-> %s %s --> TimedOut" %(r,i,self.EnergyLevel[ r ][ i ]['Status']))
                        self.EnergyLevel[ r ][ i ]['Status'] = 'TimedOut'
                        if len(self.nwkidInQueue) > 0:
                            root, entry = self.nwkidInQueue.pop()
                            if r != root and i != entry:
                                Domoticz.Error("Mismatch %s versus %s" %(i, entry))
                    continue
                elif self.EnergyLevel[ r ][ i ]['Status'] == 'ScanRequired':
                    _channels = []
                    for c in self.EnergyLevel[ r ][ i ]['Channels']:
                        _channels.append( c )
                    self.NwkScanReq( r, i, _channels)
                    breakfromabove = True
                    allRootCompleted = False
                    break
            else:
                if not waitResponse:
                    continue
            if breakfromabove:
                break
        else:
            if allRootCompleted:
                self.finish_scan()


    def finish_scan( self ):

        self.logging( 'Debug', "Finish_scan")
        self.ScanInProgress = False

        stamp = int(time())
        storeEnergy = {}
        storeEnergy[stamp] = []
        for r in self.EnergyLevel:
            Domoticz.Status("Network Energy Level Report: %s" %r)
            Domoticz.Status("-----------------------------------------------")
            Domoticz.Status("%6s <- %5s %6s %8s %4s %4s %4s %4s %4s %4s" %('router', 'nwkid', 'Tx', 'Failure', '11','15','19','20','25','26'))
            router = {}
            router['_NwkId'] = r
            router['MeshRouters'] = []
            for nwkid in self.EnergyLevel[ r ]:
                entry = {}
                entry['_NwkId'] = nwkid
                if nwkid not in self.ListOfDevices:
                    continue
                if 'ZDeviceName' in self.ListOfDevices[nwkid]:
                    if self.ListOfDevices[nwkid]['ZDeviceName'] != {}:
                        entry['ZDeviceName'] = self.ListOfDevices[nwkid]['ZDeviceName']
                    else:
                        entry['ZDeviceName'] = nwkid
                if self.EnergyLevel[ r ][nwkid]['Status'] != 'Completed':
                    entry['Tx'] = 0
                    entry['Failure'] = 0
                    entry['Channels'] = []
                    toprint = "%6s <- %5s %6s %8s" %(r, nwkid, self.EnergyLevel[ r ][ nwkid ][ 'Tx' ], self.EnergyLevel[ r ][ nwkid ][ 'Failure' ])
                    for c in CHANNELS:
                        channels = {}
                        channels['Channel'] = c
                        channels['Level'] = 0
                        entry['Channels'].append( channels )
                        toprint += " %4s" %0
                else:
                    entry['Tx'] = self.EnergyLevel[ r ][ nwkid ][ 'Tx' ]
                    entry['Failure'] = self.EnergyLevel[ r ][ nwkid ][ 'Failure' ]
                    entry['Channels'] = []
    
                    toprint = "%6s <- %5s %6s %8s" %(r, nwkid, self.EnergyLevel[ r ][ nwkid ][ 'Tx' ], self.EnergyLevel[ r ][ nwkid ][ 'Failure' ])
                    for c in self.EnergyLevel[ r ][ nwkid ]['Channels']:
                        channels = {}
                        if c not in CHANNELS:
                            continue
                        channels['Channel'] = c
                        channels['Level'] = self.EnergyLevel[ r ][ nwkid ]['Channels'][ c ]
                        entry['Channels'].append( channels )
                        toprint += " %4s" %self.EnergyLevel[ r ][ nwkid ]['Channels'][ c ]
                router['MeshRouters'].append ( entry )
                Domoticz.Status(toprint)
            storeEnergy[stamp].append( router )

        self.logging( 'Debug', "Network Energly Level Report: %s" %storeEnergy)

        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkEnergy-v3-' + '%02d' %self.HardwareID + '.json'
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
                json.dump( storeEnergy, fout)
        else:
            Domoticz.Error("Unable to get access to directory %s, please check PluginConf.txt" %(self.pluginconf.pluginConf['pluginReports']))

        return


    def NwkScanResponse(self, MsgData):

        self.logging( 'Debug', "NwkScanResponse >%s<" %MsgData)

        MsgSrc = None
        MsgSequenceNumber=MsgData[0:2]
        MsgDataStatus=MsgData[2:4]
        MsgTotalTransmission=MsgData[4:8]
        MsgTransmissionFailures=MsgData[8:12]
        MsgScannedChannel=MsgData[12:20]
        MsgScannedChannelListCount=MsgData[20:22]
        MsgChannelListInterference=MsgData[22:22+(2*int(MsgScannedChannelListCount,16))]

        self.logging( 'Debug', "NwkScanResponse Channels: %s, Len: %s " %( MsgScannedChannelListCount, len(MsgData) ))
        if len(MsgData) == ( 22 + 2*int(MsgScannedChannelListCount,16) + 4 ):
            # Firmware 3.1a and aboce
            MsgSrc = MsgData[ 22 + (2*int(MsgScannedChannelListCount,16)): 22 + (2*int(MsgScannedChannelListCount,16)) + 4]
            self.logging( 'Debug', "NwkScanResponse - Firmware 3.1a - MsgSrc: %s" %MsgSrc)

        #Decode the Channel mask received
        CHANNELS = { 11: 0x00000800, 12: 0x00001000, 13: 0x00002000, 14: 0x00004000,
                15: 0x00008000, 16: 0x00010000, 17: 0x00020000, 18: 0x00040000,
                19: 0x00080000, 20: 0x00100000, 21: 0x00200000, 22: 0x00400000,
                23: 0x00800000, 24: 0x01000000, 25: 0x02000000, 26: 0x04000000 }

        if MsgDataStatus != '00':
            Domoticz.Error("NwkScanResponse - Status: %s with Data: %s" %(MsgDataStatus, MsgData))
            return

        if len(self.nwkidInQueue) == 0 and MsgSrc:
            self.logging( 'Log', "NwkScanResponse - Empty Queue, Receive infos from %s" %MsgSrc)
            return

        if len(self.nwkidInQueue) == 0:
            self.logging( 'Log', "NwkScanResponse - Empty Queue ")
            return

        if len(self.nwkidInQueue) > 0 and MsgSrc:
            root, entry = self.nwkidInQueue.pop()
            self.logging( 'Debug', "NwkScanResponse - Root: %s, Entry: %s, MsgSrc: %s" %(root, entry, MsgSrc))
            if entry != MsgSrc:
                Domoticz.Log("NwkScanResponse - Unexpected message >%s< from %s, expecting %s" %( MsgData, MsgSrc, entry))

        elif  len(self.nwkidInQueue) > 0 :
            root, entry = self.nwkidInQueue.pop()
            self.logging( 'Debug', "NwkScanResponse - Root: %s, Entry: %s" %(root, entry))
            
        else:
            self.logging( 'Log', "NwkScanResponse - Unexpected: len: %s, MsgSrc: %s" %(len(self.nwkidInQueue), MsgSrc))
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

        self.logging( 'Debug', "NwkScanResponse - SQN: %s, Tx: %s , Failures: %s , Status: %s) " \
                %(MsgSequenceNumber, int(MsgTotalTransmission,16), int(MsgTransmissionFailures,16), MsgDataStatus) )

        self.EnergyLevel[ root ][ entry ][ 'Tx' ]  =   int(MsgTotalTransmission,16)
        self.EnergyLevel[ root ][ entry ][ 'Failure' ]  =  int(MsgTransmissionFailures,16)

        for chan, inter in zip( channelList, channelListInterferences ):
            if chan in CHANNELS:
                self.EnergyLevel[ root ][ entry ]['Channels'][ str(chan) ] = int(inter,16)
                self.logging( 'Debug', "     %s <- %s Channel: %s Interference: : %s " %(root, entry, chan, int(inter,16)))

        self.EnergyLevel[ root ][ entry ]['Status'] = 'Completed'
        return

