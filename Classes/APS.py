
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
        '00B0':'Move tço Hue', 
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
        return

    def _addNewCmdtoDevice(self, nwk, cmd):
        """ Add Cmd to the nwk list of Command FIFO mode """

        Domoticz.Debug("addNewCmdtoDevice - %s %s" %(nwk, cmd))
        if 'Last Cmds' not in self.ListOfDevices[nwk]:
            self.ListOfDevices[nwk]['Last Cmds'] = []
        if len(self.ListOfDevices[nwk]['Last Cmds']) >= MAX_CMD_PER_DEVICE:
            # Remove the First element in the list.
            self.ListOfDevices[nwk]['Last Cmds'].pop(0)
        _tuple = ( time(), cmd )
        # Add element at the end of the List
        self.ListOfDevices[nwk]['Last Cmds'].append( _tuple )
        Domoticz.Debug("addNewCmdtoDevice - %s adding cmd: %s into the Last Cmds list %s" \
                %(nwk, cmd, self.ListOfDevices[nwk]['Last Cmds']))

    def processCMD( self, cmd, payload):

        Domoticz.Debug("processCMD - cmd: %s, payload: %s" %(cmd, payload))
        if len(payload) < 7 or cmd not in CMD_NWK_2NDBytes:
            return

        nwkid = payload[2:6]
        Domoticz.Debug("processCMD - Retreive NWKID: %s" %nwkid)
        if nwkid in self.ListOfDevices:
            self._addNewCmdtoDevice( nwkid, cmd )

    def _errorMgt( self, cmd, nwk, ieee, aps_code):

        timedOutDevice( self, self.Devices, NwkId = nwk)
        _deviceName = 'not found'
        for x in self.Devices:
            if self.Devices[x].DeviceID == ieee:
                _deviceName = self.Devices[x].Name
                break
        _cmdTxt = '0x' + cmd
        if cmd in CMD_NWK_2NDBytes:
            _cmdTxt += ':' + CMD_NWK_2NDBytes[cmd]

        Domoticz.Error("Communication error Command: %s" %_cmdTxt) 
        Domoticz.Error("- to Device: %s NwkID: %s IEEE: %s" %( _deviceName, nwk, ieee))
        Domoticz.Error("- Code: %s Status: %s" %( aps_code, DisplayStatusCode( aps_code )))
        if 'Health' in self.ListOfDevices[nwk]:
            self.ListOfDevices[nwk]['Health'] = 'Not Reachable'

    def _updateAPSrecord( self, nwk, aps_code):

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

        APS_FAILURE_CODE = (  'd4', 'e9', 'f0' , 'cf' )

        Domoticz.Debug("processAPSFailure - %s %s %s" %(nwk, ieee, aps_code))
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

        if self.pluginconf.enableAPSFailureLoging:
            Domoticz.Log("processAPSFailure - NwkId: %s, IEEE: %s, Code: %s, Status: %s" \
                    %( nwk, ieee, aps_code, DisplayStatusCode( aps_code )))

        self._updateAPSrecord( nwk, aps_code)

        if  not _mainPowered \
                or (aps_code not in APS_FAILURE_CODE) \
                or not self.pluginconf.enableAPSFailureReporting:
            return

        _timeAPS = (time())
        _lastCmds = self.ListOfDevices[nwk]['Last Cmds']

        Domoticz.Debug("processAPSFailure - %s Last Cmds: %s" %(nwk, _lastCmds))
        for iterTime, iterCmd in reversed(_lastCmds):
            Domoticz.Debug("processAPSFailure - %s process %s - %s" %(nwk, iterTime, iterCmd))
            if _timeAPS <= ( iterTime + APS_TIME_WINDOW):
                # That command has been issued in the APS time window
                Domoticz.Log("processAPSFailure - %s found cmd: %s in the APS time window, age is: %s sec" %(nwk, iterCmd, round((_timeAPS - iterTime),2)))
                self._errorMgt( iterCmd, nwk, ieee, aps_code)

