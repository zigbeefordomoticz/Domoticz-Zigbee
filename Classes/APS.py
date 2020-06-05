#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from time import time, ctime

import Domoticz
from Modules.errorCodes import DisplayStatusCode
from Modules.domoTools import timedOutDevice

from datetime import datetime

APS_TIME_WINDOW = 15
MAX_APS_TRACKING_ERROR = 5

APS_FAILURE_CODE = (  'd0', 'd4', 'e9', 'f0' , 'cf' )

CMD_NWK_2NDBytes = { 
        '0060':'Add Group', 
        '0061':'View group', 
        '0062':'Get Group Memberships', 
        '0063':'Remove Group', 
        '0064':'Remove All Groups', 
        '0065':'Add Group if identify', 
        '0070':'Identify Send',
        '0080':'Move to level', 
        '0081':'Move to Level w/o on/off', 
        '0082':'Move Step', 
        '0083':'Move Stop Move', 
        '0084':'Move Stop with On/off', 
        '0092':'On/Off', 
        '0093':'On/Off Timed send', 
        '0094':'On/Off with effect',
        '004A':'Management Network Update request',
        '004E':'Management LQI request',
        '00B0':'Move to Hue', 
        '00B1':'Move Hue',
        '00B2':'Step Hue', 
        '00B3':'Move to saturation', 
        '00B4':'Move saturation', 
        '00B5':'Step saturation', 
        '00B6':'Move to hue and saturation', 
        '00B7':'Move to colour', 
        '00B8':'Move colour', 
        '00B9':'step colour', 
        '00BA':'Enhanced Move to Hue', 
        '00BB':'Enhanced Move Hue', 
        '00BC':'Enhanced Step Hue', 
        '00BD':'Enhanced Move to hue and saturation', 
        '00BE':'Colour Loop set', 
        '00BF':'Stop Move Step', 
        '00C0':'Move to colour temperature', 
        '00C1':'Move colour temperature', 
        '00C2':'Step colour temperature', 
        '00E0':'Identify Trigger Effect', 
        '00F0':'Lock/Unlock Door', 
        '00FA':'Windows covering', 
        '0100':'Read Attribute request', 
        '0110':'Write Attribute request', 
        '0120':'Configure reporting request' 
        }

class APSManagement(object):

    def __init__(self, ListOfDevices, Devices, pluginconf , loggingFileHandle):

        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.pluginconf = pluginconf
        self.loggingFileHandle = loggingFileHandle

        return


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

        self.debugAPS = self.pluginconf.pluginConf['debugAPS']
        if logType == 'Debug' and self.debugAPS:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)
        return
    
    def _errorMgt( self, cmd, nwk, ieee, aps_code):
        """ Process the error """

        if nwk not in self.ListOfDevices:
            return

        if 'ErrorManagement' not in self.ListOfDevices[nwk]: 
            self.ListOfDevices[nwk]['ErrorManagement'] = 0

        if self.ListOfDevices[nwk]['ErrorManagement'] == 0 and cmd in ( '0100', '0110', '0120', '0030'):
            self.logging( 'Log', "_errorMgt - Give a chance of APS recovery for %s/%s on command %s" %(nwk,ieee, cmd))
            self.ListOfDevices[nwk]['ErrorManagement']  = 1
            return

        timedOutDevice( self, self.Devices, NwkId = nwk)
        _deviceName = 'not found'
        for x in self.Devices:
            if self.Devices[x].DeviceID == ieee:
                _deviceName = self.Devices[x].Name
                break

        _cmdTxt = '0x' + cmd
        if cmd in CMD_NWK_2NDBytes:
            _cmdTxt += ':' + CMD_NWK_2NDBytes[cmd]

        ZDeviceName =''
        if 'ZDeviceName' in self.ListOfDevices[nwk]:
            ZDeviceName =  self.ListOfDevices[nwk]['ZDeviceName']

        Domoticz.Error("APS Failure , Command: %s for %s (%s,%s,%s) not correctly transmited. ( %s, %s )" \
                %( _cmdTxt, ZDeviceName, _deviceName, nwk, ieee, aps_code, DisplayStatusCode( aps_code )))
        self.ListOfDevices[nwk]['Health'] = 'Not Reachable'

    def _updateAPSrecord( self, nwk, aps_code):
        """ Update APS Failure record in DeviceList """

        if 'APS Failure' not in self.ListOfDevices[nwk]:
            self.ListOfDevices[nwk]['APS Failure'] = []

        if len(self.ListOfDevices[nwk]['APS Failure']) >= MAX_APS_TRACKING_ERROR:
             self.ListOfDevices[nwk]['APS Failure'].pop(0)
        _tuple = ( time(), aps_code )
        self.ListOfDevices[nwk]['APS Failure'].append( _tuple )

    def processAPSFailure( self, nwk, ieee, aps_code):
        """
        We are receiving a APS Failure code for that particular Device
        - Let's check if we have sent a command in the last window
        """

        self.logging( 'Debug', "processAPSFailure - %s %s %s" %(nwk, ieee, aps_code))
        if nwk not in self.ListOfDevices:
            return
        if 'Last Cmds' not in self.ListOfDevices[nwk]:
            return
        _mainPowered = False
        if 'MacCapa' in self.ListOfDevices[nwk]:
            if self.ListOfDevices[nwk]['MacCapa'] == '8e':
                _mainPowered = True
        elif 'PowerSource' in self.ListOfDevices[nwk]:
            if self.ListOfDevices[nwk]['PowerSource'] == 'Main':
                _mainPowered = True
        ZDeviceName = ''
        if 'ZDeviceName' in  self.ListOfDevices[nwk]:
            ZDeviceName =  self.ListOfDevices[nwk]['ZDeviceName']
        #if self.pluginconf.pluginConf['enableAPSFailureLoging']:
        #    Domoticz.Log("processAPSFailure - Device: %s NwkId: %s, IEEE: %s, Code: %s, Status: %s" \
        #            %( ZDeviceName, nwk, ieee, aps_code, DisplayStatusCode( aps_code )))
        self.logging( 'Debug', "processAPSFailure - Update APS record Device: %s NwkId: %s, IEEE: %s, Code: %s, Status: %s" \
                    %( ZDeviceName, nwk, ieee, aps_code, DisplayStatusCode( aps_code )))

        # Keep track of APS Failure
        self._updateAPSrecord( nwk, aps_code)

        if  not _mainPowered \
                or (aps_code not in APS_FAILURE_CODE) \
                or not self.pluginconf.pluginConf['enableAPSFailureReporting']:
            self.logging( 'Debug', "processAPSFailure - stop: Power: %s aps_code: %s enableAPSFailureReport: %s" \
                    %(_mainPowered, aps_code, self.pluginconf.pluginConf['enableAPSFailureReporting']))
            return

        # We do not want to take action for internal Zigate activities. So we will find if there the saem command use in a short period of time

        _timeAPS = (time())
        # Retreive Last command
        rank = 0
        self.logging( 'Debug', "processAPSFailure - Last Commands Queue for %s" %nwk)
        for command in self.ListOfDevices[nwk]['Last Cmds']:
            if len(command) == 3:
                self.logging( 'Debug', "  [%2s] Command: %s Payload: %-10s TimeStamp:  %24s (%18s)" %(rank, command[1], command[2],  ctime(command[0]), command[0]))
            rank += 1

        _lastCmds = self.ListOfDevices[nwk]['Last Cmds'][::-1]  #Reverse list
        self.logging( 'Debug', "processAPSFailure - %s Last Cmds: %s" %(nwk, _lastCmds))
        iterTime = 0
        iterCmd = iterpayLoad = None
        if len(_lastCmds) < 1:
            return
        if len(_lastCmds[0]) == 2:
            return 
        if len(_lastCmds[0]) == 3:
            iterTime, iterCmd, iterpayLoad = _lastCmds[0]

        self.logging( 'Debug', "processAPSFailure - Nwkid: %s process %18s InPeriod: %s - Cmd: %s Payload: %s" \
                %(nwk, iterTime, (_timeAPS <= ( iterTime + APS_TIME_WINDOW)), iterCmd, iterpayLoad))
        if _timeAPS <= ( iterTime + APS_TIME_WINDOW):
            # That command has been issued in the APS time window
            self.logging( 'Debug', "processAPSFailure - %s found cmd: %s[%s] in the APS time window, age is: %s sec" \
                    %(nwk, iterCmd, iterpayLoad, round((_timeAPS - iterTime),2)))
            self._errorMgt( iterCmd, nwk, ieee, aps_code)
