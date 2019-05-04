
"""

    'List Cmds' = [ { 'cmd':'Time Stamps', ... } ]

"""

from time import time

import Domoticz


MAX_CMD_PER_DEVICE = 5
APS_TIME_WINDOW = 5 

class APSManagement(object):


    def __init__(self, ListOfDevices ):

        self.ListOfDevices = ListOfDevices
        return

    def addNewCmdtoDevice(self, nwk, cmd):

        """ Add Cmd to the nwk list of Command FIFO mode """

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

        return


    def processAPSFailure( self, nwk, ieee, aps_code):

        """
        We are receiving a APS Failure code for that particular Device
        - Let's check if we have sent a command in the last window
        """

        Domoticz.Debug("processAPSFailure - %s %s %s" %(nwk, ieee, aps_code))
        if nwk not in self.ListOfDevices:
            return
        if 'Last Cmds' not in self.ListOfDevices[nwk]:
            return

        _timeAPS = (time())
        _lastCmds = self.ListOfDevices[nwk]['Last Cmds']

        Domoticz.Debug("processAPSFailure - %s Last Cmds: %s" %(nwk, _lastCmds))

        for iterTime, iterCmd in _lastCmds:
            Domoticz.Debug("processAPSFailure - %s process %s - %s" %(nwk, iterTime, iterCmd))
            if _timeAPS >= ( iterTime + APS_TIME_WINDOW):
                # That command has been issued in the APS time window
                Domoticz.Debug("processAPSFailure - %s found cmd: %s in the APS time window" %(nwk, iterCmd))
