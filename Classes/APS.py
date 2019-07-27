
"""

    'List Cmds' = [ { 'cmd':'Time Stamps', ... } ]

"""

from time import time

import Domoticz
from Modules.status import DisplayStatusCode
from Modules.domoticz import timedOutDevice

MAX_CMD_PER_DEVICE = 5
APS_TIME_WINDOW = 1.5
MAX_APS_TRACKING_ERROR = 5

APS_FAILURE_CODE = (  'd4', 'e9', 'f0' , 'cf' )

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

    def __init__(self, ListOfDevices, Devices, pluginconf ):

        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.pluginconf = pluginconf
        self.ZigateComm = None        # Point to the ZigateComm object

        return

    def logging( self, logType, message):

        self.debugAPS = self.pluginconf.pluginConf['debugAPS']
        if logType == 'Debug' and self.debugAPS:
            Domoticz.Log( message)
        elif logType == 'Log':
            Domoticz.Log( message )
        elif logType == 'Status':
            Domoticz.Status( message)
        return
    
    def updateZigateComm( self, ZigateComm):

        self.ZigateComm = ZigateComm

    def _errorMgt( self, cmd, nwk, ieee, aps_code):
        """ Process the error """

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

        Domoticz.Error("Command: %s failed on %s" %(_cmdTxt, ZDeviceName)) 
        Domoticz.Error("- Device: %s NwkID: %s IEEE: %s" %( _deviceName, nwk, ieee))
        Domoticz.Error("- Code: %s Status: %s" %( aps_code, DisplayStatusCode( aps_code )))
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

        if self.pluginconf.pluginConf['enableAPSFailureLoging']:
            Domoticz.Log("processAPSFailure - Device: %s NwkId: %s, IEEE: %s, Code: %s, Status: %s" \
                    %( ZDeviceName, nwk, ieee, aps_code, DisplayStatusCode( aps_code )))

        self.logging( 'Debug', "processAPSFailure - Update APS record Device: %s NwkId: %s, IEEE: %s, Code: %s, Status: %s" \
                    %( ZDeviceName, nwk, ieee, aps_code, DisplayStatusCode( aps_code )))
        self._updateAPSrecord( nwk, aps_code)

        if  not _mainPowered \
                or (aps_code not in APS_FAILURE_CODE) \
                or not self.pluginconf.pluginConf['enableAPSFailureReporting']:
            self.logging( 'Debug', "processAPSFailure - stop: Power: %s aps_code: %s enableAPSFailureReport: %s" \
                    %(_mainPowered, aps_code, self.pluginconf.pluginConf['enableAPSFailureReporting']))
            return

        self.logging( 'Debug', "processAPSFailure - Error Reporting")

        _timeAPS = (time())
        _lastCmds = self.ListOfDevices[nwk]['Last Cmds']

        self.logging( 'Debug', "processAPSFailure - %s Last Cmds: %s" %(nwk, _lastCmds))
        for iterItem in reversed(_lastCmds):
            iterTime = iterItem[0]
            iterCmd =iterItem[1]
            iterpayLoad = None
            if len(iterItem) == 3:
                iterpayLoad =iterItem[2]
            
            self.logging( 'Debug', "processAPSFailure - %s process %18s %s - %s[%s]" %(nwk, iterTime, (_timeAPS <= ( iterTime + APS_TIME_WINDOW)), iterCmd, iterpayLoad))
            if _timeAPS <= ( iterTime + APS_TIME_WINDOW):
                # That command has been issued in the APS time window
                self.logging( 'Debug', "processAPSFailure - %s found cmd: %s[%s] in the APS time window, age is: %s sec" %(nwk, iterCmd, iterpayLoad, round((_timeAPS - iterTime),2)))
                self._errorMgt( iterCmd, nwk, ieee, aps_code)
