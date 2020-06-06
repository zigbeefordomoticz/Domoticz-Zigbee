#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import binascii
import struct
from time import time
from datetime import datetime

from Modules.tools import is_hex
from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_RESPONSES, ZIGATE_COMMANDS, RETRANSMIT_COMMAND
from Modules.sqnMgmt import sqn_init_stack, sqn_generate_new_internal_sqn, sqn_add_external_sqn


STANDALONE_MESSAGE =[]
for x in ZIGATE_RESPONSES:
    STANDALONE_MESSAGE.append( x )

CMD_PDM_ON_HOST = []
CMD_ONLY_STATUS = []
CMD_NWK_2NDBytes = {}
CMD_DATA = {}
for x in ZIGATE_COMMANDS:
    if ZIGATE_COMMANDS[ x ]['NwkId 2nd Bytes']:
        CMD_NWK_2NDBytes[ x ] = x
    if len ( ZIGATE_COMMANDS[ x ]['Sequence']) == 1:
            CMD_ONLY_STATUS.append( x )
    elif len ( ZIGATE_COMMANDS[ x ]['Sequence']) == 0:
            CMD_PDM_ON_HOST.append ( x )

    else:
        CMD_DATA[ x ] = ZIGATE_COMMANDS[ x ]['Sequence'][1]



APS_DELAY = 1
APS_MAX_RETRY = 2
APS_TIME_WINDOW = APS_MAX_RETRY * APS_DELAY
APS_ACK = 0

class ZigateTransport(object):
    """
    Class in charge of Transport mecanishm to and from Zigate
    Managed also the Command -> Status -> Data sequence
    """

    def __init__(self, LOD, transport, statistics, pluginconf, F_out, loggingFileHandle, serialPort=None, wifiAddress=None, wifiPort=None):
        ##DEBUG Domoticz.Debug("Setting Transport object")
        self.lock = False

        self.PDMCommandOnly = False    # This flag indicate if any command can be sent to Zigate or only PDM related one

        self.LOD = LOD # Object managing the Plugin Devices
        self.checkTimedOutFlag = None
        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin

        self.ListOfCommands = {}     # List of ( Command, Data ) to be or in process
        self.zigateSendQueue = []    # list of normal priority commands
        self._waitFor8000Queue = []  # list of command sent and waiting for status 0x8000
        self._waitForCmdResponseQueue = []  # list of command sent for which status received and waiting for data
        self._waitForAPS = []        # Contain list of Command waiting for APS ACK or Failure. That one is populated when receiving x8000
        self._waitForAckNack = []    # Contains list of Command waiting for Ack/Nack
        self._waitForRouteDiscoveryConfirm = []

        self.statistics = statistics

        self.pluginconf = pluginconf

        self.zmode = pluginconf.pluginConf['zmode']
        self.zTimeOut = pluginconf.pluginConf['zTimeOut']
        sqn_init_stack (self)

        self.loggingFileHandle = loggingFileHandle

        self.loggingSend(  'Debug',"STANDALONE_MESSAGE: %s" %STANDALONE_MESSAGE)
        self.loggingSend(  'Debug',"CMD_ONLY_STATUS: %s" %CMD_ONLY_STATUS)
        self.loggingSend(  'Debug',"ZIGATE_COMMANDS: %s" %ZIGATE_COMMANDS)
        self.loggingSend(  'Debug',"CMD_NWK_2NDBytes: %s" %CMD_NWK_2NDBytes)

        if str(transport) == "USB":
            self._transp = "USB"
            self._serialPort = serialPort
        elif str(transport) == "DIN":
            self._transp = "DIN"
            self._serialPort = serialPort
        elif str(transport) == "PI":
            self._transp = "PI"
            self._serialPort = serialPort
        elif str(transport) == "Wifi":
            self._transp = "Wifi"
            self._wifiAddress = wifiAddress
            self._wifiPort = wifiPort
        else:
            Domoticz.Error("Unknown Transport Mode: %s" %transport)

    def loggingSend( self, logType, message):
        # Log all activties towards ZiGate
        if self.pluginconf.pluginConf['debugTransportTx'] and logType == 'Debug':
            _loggingDebug( self, message )
        elif  logType == 'Log':
            _loggingLog( self, message )
        elif logType == 'Status':
            _loggingStatus( self, message )

    def loggingReceive( self, logType, message):
        # Log all activities received from ZiGate
        if self.pluginconf.pluginConf['debugTransportRx'] and logType == 'Debug':
            _loggingDebug( self, message )
        elif  logType == 'Log':
            _loggingLog( self, message )
        elif logType == 'Status':
            _loggingStatus.Status( self, message )

    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return len(self.zigateSendQueue)

    # Transport / Opening / Closing Communication
    def setConnection( self ):

        if self._connection is not None:
            del self._connection
            self._connection = None

        if self._transp in ["USB", "DIN", "PI"]:
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" %( self._serialPort ))
                BAUDS = 115200
                self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None",
                         Address=self._serialPort, Baud= BAUDS)

        elif self._transp == "Wifi":
            Domoticz.Status("Connection Name: Zigate, Transport: TCP/IP, Address: %s:%s" %( self._serialPort, self._wifiPort ))
            self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ",
                         Address=self._wifiAddress, Port=self._wifiPort)
        else:
            Domoticz.Error("Unknown Transport Mode: %s" %self._transp)

    def openConn(self):
        self.setConnection()
        if self._connection:
            self._connection.Connect()
        else:
            Domoticz.Error("openConn _connection note set!")
        Domoticz.Status("Connection open: %s" %self._connection)

    def closeConn(self):
        Domoticz.Status("Connection close: %s" %self._connection)
        self._connection.Disconnect()
        del self._connection
        self._connection = None

    def reConn(self):
        Domoticz.Status("Reconnection: %s" %self._connection)
        if self._connection.Connected() :
            Domoticz.Log("--> still connected!")
            self.closeConn()
        self.openConn()

    # PDMonhost related
    def PDMLock( self , lock):
        # Take a Lock to protect all communications from/to ZiGate (PDM on Host)
        self.PDMCommandOnly = lock

    def PDMLockStatus( self ):
        return self.PDMCommandOnly

    def sendData(self, cmd, datas , delay=None):
        self.loggingSend(  'Debug', "sendData - %s %s FIFO: %s" %(cmd, datas, len(self.zigateSendQueue)))
        if datas is None:
            datas = ''
        if datas != '' and not is_hex( datas):
            Domoticz.Error("sendData_internal - receiving a non hexa Data: >%s<" %datas)
            return

        # Check if the Cmd/Data is not yet in the pipe
        #for x in self.ListOfCommands:
        #    if self.ListOfCommands[ x ]['Cmd'] ==  cmd and self.ListOfCommands[ x ]['Datas'] == datas:
        #        self.loggingSend(  'Log',"Do not queue again an existing command in the Pipe, we drop the command %s %s" %(cmd, datas))
        #        return

        InternalSqn = sqn_generate_new_internal_sqn(self)

        if InternalSqn in self.ListOfCommands:
            # Unexpected !
            Domoticz.Error("sendData - Existing Internal SQN: %s for %s versus new %s/%s" %( InternalSqn, str(self.ListOfCommands[ InternalSqn]), cmd, datas ))
            return

        self.ListOfCommands[ InternalSqn ] = {}
        self.ListOfCommands[ InternalSqn ]['Cmd'] = cmd
        self.ListOfCommands[ InternalSqn ]['Datas'] = datas
        self.ListOfCommands[ InternalSqn ]['ReTransmit'] = 0
        self.ListOfCommands[ InternalSqn ]['Status'] = ''
        self.ListOfCommands[ InternalSqn ]['TimeStamp'] = int(time())

        self.ListOfCommands[ InternalSqn ]['PDMCommand'] = False
        self.ListOfCommands[ InternalSqn ]['ResponseExpected'] = False
        self.ListOfCommands[ InternalSqn ]['ResponseExpectedCmd'] = None
        if int(cmd,16) in CMD_PDM_ON_HOST:
            self.ListOfCommands[ InternalSqn ]['PDMCommand'] = True

        elif int(cmd, 16) in CMD_DATA:
            self.ListOfCommands[ InternalSqn ]['ResponseExpectedCmd'] = CMD_DATA[int(cmd, 16)]
            self.ListOfCommands[ InternalSqn ]['ResponseExpected'] = True

        if self.ListOfCommands[ InternalSqn ]['ResponseExpected']:

            self.loggingSend(  'Debug', "sendData - InternalSQN: %s Cmd: %s Data: %s ExpectedCmd: %04x"
                %(InternalSqn, cmd, datas, self.ListOfCommands[ InternalSqn ]['ResponseExpectedCmd'] ))
        else:
            self.loggingSend(  'Debug',"sendData - InternalSQN: %s Cmd: %s Data: %s"
                %(InternalSqn, cmd, datas ))


        self.sendData_internal ( InternalSqn )
        return InternalSqn

    def sendData_internal(self, InternalSqn):
        '''
        in charge of sending Data. Call by sendZigateCmd
        If nothing in the waiting queue, will call _sendData and it will be sent straight to Zigate
        '''
        if InternalSqn not in self.ListOfCommands:
            # Unexpected
            return

        self.loggingSend(  'Debug', "sendData_internal - %s FIFO: %s" %(InternalSqn, len(self.zigateSendQueue)))

        # PDM Management.
        # When PDM traffic is ongoing we cannot interupt, so we need to FIFO all other commands until the PDMLock is released
        #PDM_COMMANDS = ( '8300', '8200', '8201', '8204', '8205', '8206', '8207', '8208' )
        #if self.PDMLockStatus() and cmd not in PDM_COMMANDS:
        #    # Only PDM related command can go , all others will be dropped.
        #    Domoticz.Log("PDM not yet ready, FIFO command %s %s" %(cmd, datas))
        #    sendNow = False
        sendNow = (len(self._waitFor8000Queue) == 0 and len(self._waitForCmdResponseQueue) == 0) or self.ListOfCommands[ InternalSqn ]['PDMCommand']
        self.loggingSend(  'Debug', "sendData_internal - Command: %s  Q(0x8000): %s Q(Response): %s sendNow: %s" %(self.ListOfCommands[ InternalSqn ]['Cmd'], len(self._waitFor8000Queue), len(self._waitForCmdResponseQueue), sendNow))

        # In case the cmd is part of the PDM on Host commands, that is High Priority and must go through.
        if sendNow:
            if not self.ListOfCommands[ InternalSqn ]['PDMCommand']:
                # That is a Standard command (not PDM on  Host), let's process as usall
                _addCmdToWaitFor8000Queue( self, InternalSqn )

                if self.zmode == 'ZigBee' and self.ListOfCommands[ InternalSqn ]['ResponseExpected']:  
                    _addCmdToWaitForDataQueue( self, InternalSqn )
            _sendData( self, InternalSqn )
        else:
            # Put in FIFO
            self.loggingSend(  'Debug', "sendData_internal - put in waiting queue")
            _addCmdToSendQueue( self, InternalSqn )

    # Transport Sending Data

    # Transport / called by plugin 
    def onMessage(self, Data):
        # Process/Decode Data

        self.loggingReceive( 'Debug', "onMessage - %s" %(Data))
        FrameIsKo = 0

        if Data is not None:
            self._ReqRcv += Data  # Add the incoming data
            #Domoticz.Debug("onMessage incoming data : '" + str(binascii.hexlify(self._ReqRcv).decode('utf-8')) + "'")

        # Zigate Frames start with 0x01 and finished with 0x03    
        # It happens that we get some 
        while 1:  # Loop until we have 0x03
            Zero1 = Zero3 = -1
            idx = 0
            for val in self._ReqRcv[0:len(self._ReqRcv)]:
                if Zero1 == - 1 and Zero3 == -1 and val == 1:  # Do we get a 0x01
                    Zero1 = idx  # we have identify the Frame start

                if Zero1 != -1 and val == 3:  # If we have already started a Frame and do we get a 0x03
                    Zero3 = idx + 1
                    break  # If we got 0x03, let process the Frame
                idx += 1

            if Zero3 == -1:  # No 0x03 in the Buffer, let's break and wait to get more data
                return

            if Zero1 != 0:
                Domoticz.Error("onMessage : we have probably lost some datas, zero1 = " + str(Zero1))

            # uncode the frame
            #### DEBUG ###_uncoded = str(self._ReqRcv[Zero1:Zero3]) + ''
            BinMsg = bytearray()
            iterReqRcv = iter(self._ReqRcv[Zero1:Zero3])

            for iByte in iterReqRcv:  # for each received byte
                if iByte == 0x02:  # Coded flag ?
                    iByte = next(iterReqRcv) ^ 0x10  # then uncode the next value
                BinMsg.append(iByte)  # copy

            if len(BinMsg) <= 6:
                Domoticz.Error("onMessage error - processing an uncomplet message: %s" %BinMsg)
                return

            self._ReqRcv = self._ReqRcv[Zero3:]  # What is after 0x03 has to be reworked.

            # Check length
            Zero1, MsgType, Length, ReceivedChecksum = struct.unpack('>BHHB', BinMsg[0:6])
            ComputedLength = Length + 7
            ReceveidLength = len(BinMsg)
            if ComputedLength != ReceveidLength:
                FrameIsKo = 1
                self.statistics._frameErrors += 1
                Domoticz.Error("onMessage : Frame size is bad, computed = " + \
                               str(ComputedLength) + " received = " + str(ReceveidLength))

            # Compute checksum
            ComputedChecksum = 0
            for idx, val in enumerate(BinMsg[1:-1]):
                if idx != 4:  # Jump the checksum itself
                    ComputedChecksum ^= val
            if ComputedChecksum != ReceivedChecksum:
                FrameIsKo = 1
                self.statistics._crcErrors += 1
                Domoticz.Error("onMessage : Frame CRC is bad, computed = " + str(ComputedChecksum) + \
                               " received = " + str(ReceivedChecksum))

            if FrameIsKo == 0:
                AsciiMsg = binascii.hexlify(BinMsg).decode('utf-8')
                self.statistics._received += 1
                self.processFrame(AsciiMsg)

    def processFrame(self, frame):
        # will return the Frame in the Data if any
        # process the Data and check if this is a 0x8000 message
        # in case the message contains several frame, receiveData will be recall

        self.loggingReceive(  'Debug', "processFrame - Frame: %s" %frame)
        if frame == '' or frame is None or len(frame) < 12:
            return

        Status = None
        MsgData = None
        MsgType = frame[2:6]
        MsgLength = frame[6:10]
        MsgCRC = frame[10:12]
        self.loggingReceive(  'Lpg', "         - MsgType: %s MsgLength: %s MsgCRC: %s" %(MsgType, MsgLength, MsgCRC))

        if len(frame) >= 18:
            #Payload
            MsgData = frame[12:len(frame) - 4]
            RSSI = frame[len(frame) - 4: len(frame) - 2]

        if MsgData and MsgType == "8000":  
            Status = MsgData[0:2]
            SQN = MsgData[2:4]
            PacketType = MsgData[4:8] 
            SqnZCL = None  
            if len(MsgData) == 10:
                # New Firmware 3.1d (get a 2nd SQN)
                SqnZCL = MsgData[8:10]

            # We are receiving a Status
            # We have receive a Status code in response to a command.
            # We have the SQN
            if Status:
                sqn_add_external_sqn (self, SQN, SqnZCL)
                ProcessMsgType8000(self, Status, PacketType, frame)

            self.F_out(frame)  # Forward the message to plugin for further processing
            return

        if MsgData and MsgType == '8011': 
            # APS Ack/Nck with Firmware 3.1b
            MsgStatus = MsgData[0:2]
            MsgSrcAddr = MsgData[2:6]
            MsgSrcEp = MsgData[6:8]
            MsgClusterId = MsgData[8:12]
            #Domoticz.Log("processFrame - 0x8011 - APS Ack/Nck - Status: %s for %s/%s on cluster: %s" %(MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId))

            if MsgStatus == '00':
                self.statistics._APSAck += 1
            else:
                self.statistics._APSNck += 1

            # Next step is to look after the last command for SrcAddr/SrcEp and if it matches the ClusterId
            self.F_out(frame)  # Forward the message to plugin for further processing

        elif MsgType == "8702": # APS Failure
            #if self._process8702( frame ):
                self.loggingReceive( 'Debug',"             - detect an APS Failure forward to plugin")
                self.statistics._APSFailure += 1
                self.F_out(frame)  # Forward the message to plugin for further processing

        elif int(MsgType, 16) in STANDALONE_MESSAGE:  # We receive an async message, just forward it to plugin
            self.F_out(frame)  # for processing

        else:
            ProcessOtherTypeOfMessage( self, MsgType)  #
            self.F_out(frame)  # Forward the message to plugin for further processing

        self.checkTimedOutForTxQueues()  # Let's take the opportunity to check TimeOut

    def checkTimedOutForTxQueues(self):
        checkTimedOut(self)

    def _addNewCmdtoDevice(self, nwk, cmd, payload):
        """ Add Cmd to the nwk list of Command FIFO mode """

        if not self.LOD.find( nwk ):
            return
        deviceinfos = self.LOD.retreive( nwk )

        if self.pluginconf.pluginConf['APSreTx'] or self.pluginconf.pluginConf['APSrteError'] :
            _tuple = ( time(), cmd , payload) # Keep Payload as well in order to redo the command
        else:
            _tuple = ( time(), cmd , None)

        # Add element at the end of the List
        self.LOD.add_Last_Cmds( nwk, _tuple )

    def processCMD4APS( self, cmd, payload):

        if len(payload) < 7 or int(cmd,16) not in CMD_NWK_2NDBytes:
            return

        nwkid = payload[2:6]
        if self.LOD.find( nwkid ):
            self._addNewCmdtoDevice( nwkid, cmd , payload)

    def addCmdTowaitForAPS(self, cmd, data):

        timestamp = int(time())
        self._waitForAPS.append((cmd, data, timestamp))
        
    def _process8011( self, MsgData):

        MsgStatus = MsgData[0:2]
        MsgSrcAddr = MsgData[2:6]
        MsgSrcEp = MsgData[6:8]
        MsgClusterId = MsgData[8:12]

        self.loggingSend(  'Debug',"8011 - Status: %s NwkId: %s Ep: %s ClusterId: %s" %( MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId ))
    
    def _process8702( self, frame):

        """
        Status: d4 - Unicast frame does not have a route available but it is buffered for automatic resend
        Status: e9 - No acknowledgement received when expected
        Status: f0 - Pending transaction has expired and data discarded
        Status: cf - Attempt at route discovery has failed due to lack of table spac


        Note: If a message is unicast to a destination for which a route has not already been established,
        the message will not be sent and a route discovery will be performed instead. If this is the case,
        the unicast function will return ZPS_NWK_ENUM_ROUTE_ERROR. The application must then wait for the
        stack event ZPS_EVENT_NWK_ROUTE_DISCOVERY_CONFIRM (success or failure) before attempting to re-send
        the message by calling the same unicast function again.


        """
        # We have Payload : data + rssi
        MsgData=frame[12:len(frame)-4]
        MsgRSSI=frame[len(frame)-4:len(frame)-2]
    
        if len(MsgData) ==0:
            return  True
    
        MsgDataStatus = MsgData[0:2]
        MsgDataSrcEp = MsgData[2:4]
        MsgDataDestEp = MsgData[4:6]
        MsgDataDestMode = MsgData[6:8]
    
        # Assuming that Firmware is above 3.0f
        NWKID = IEEE = None
        if MsgDataDestMode == '01': # IEEE
            IEEE=MsgData[8:24]
            MsgDataSQN=MsgData[24:26]
        elif MsgDataDestMode == '02': # Short Address
            NWKID=MsgData[8:12]
            MsgDataSQN=MsgData[12:14]
        elif MsgDataDestMode == '03': # Group
            MsgDataDestAddr=MsgData[8:12]
            MsgDataSQN=MsgData[12:14]

        NWKID = self.LOD.find( NWKID, IEEE)

        self.loggingReceive( 'Log',"_process8702 - SQN: %s NwkId: %s Ieee: %s Status: %s" %(MsgDataSQN, NWKID, IEEE, MsgDataStatus))
        #if NWKID and ( MsgDataStatus == 'd4' or MsgDataStatus == 'd1'):
        # https://github.com/fairecasoimeme/ZiGate/issues/106#issuecomment-515343571
        if NWKID and ( MsgDataStatus == 'd1'):
            # Let's resend the command
            deviceinfos = self.LOD.retreive( NWKID )
            if 'Last Cmds' not in deviceinfos:
                Domoticz.Error("_process8702 - no 'Last Cmds' in %s" %deviceinfos)
                return  True

            _timeAPS = (time())
            # Retreive Last command
            # Let's check that we have a done  Max 2 retrys
            _lastCmds = deviceinfos['Last Cmds'][::-1]  #Reverse list
            iterTime = 0
            iterCmd = iterpayLoad = None
            if len(_lastCmds) >= 1: # At least we have one command
                if len(_lastCmds[0]) == 2:
                    Domoticz.Error("_process8702 - no payload")
                    return True
                if len(_lastCmds[0]) == 3:
                    iterTime, iterCmd, iterpayLoad = _lastCmds[0]
        
                if _timeAPS <= ( iterTime + APS_TIME_WINDOW):
                    # That command has been issued in the APS time window
                    self.sendData_internal( iterCmd, iterpayLoad, 2)
                    self.statistics._reTx += 1
                    return False

        return True


# Local Functions
def _addCmdToSendQueue(self, InternalSqn ):
    # add a command to the waiting list
    timestamp = int(time())
    # Check if the Cmd+Data is not yet in the Queue. If yes forget that message
    self.loggingSend(  'Debug', "--> _addCmdToSendQueue - adding to Queue %s %s" %(InternalSqn, timestamp ))
    self.zigateSendQueue.append( (InternalSqn, timestamp))
    # Manage Statistics
    if len(self.zigateSendQueue) > self.statistics._MaxLoad:
        self.statistics._MaxLoad = len(self.zigateSendQueue)
    self.statistics._Load = len(self.zigateSendQueue)

def _addCmdToWaitFor8000Queue(self, InternalSqn ):
    # add a command to the waiting list for 0x8000
    timestamp = int(time())
    self.loggingSend(  'Debug', "--> _addCmdToWaitFor8000Queue - adding to Queue %s %s" %(InternalSqn, timestamp))
    self._waitFor8000Queue.append( (InternalSqn, timestamp) )

def _addCmdToWaitForAckNackQueue( self, InternalSqn):
    # add a command to the AckNack waiting list
    timestamp = int(time())
    self.loggingSend(  'Debug', "--> _addCmdToWaitForAckNackQueue - adding to Queue  %s %s" %(InternalSqn, timestamp))
    self._waitForAckNack.append( (InternalSqn, timestamp) )

def _addCmdToWaitForDataQueue(self, InternalSqn):
    # add a command to the waiting list
    # _waitForDataQueue [ Expected Response Type, Cmd, Data, TimeStamps ]
    timestamp = int(time())
    self.loggingSend(  'Debug', "--> _addCmdToWaitForDataQueue - adding to Queue %s %s" %(InternalSqn, timestamp))
    self._waitForCmdResponseQueue.append( (InternalSqn, timestamp) )

def _nextCmdFromSendQueue(self):
    # return the next Command to send (pop)
    ret = ( None, None)
    if len(self.zigateSendQueue) > 0:
        ret = self.zigateSendQueue[0]
        del self.zigateSendQueue[0]
    self.loggingSend(  'Debug', "--> _nextCmdFromSendQueue - Unqueue %s " %( str(ret) ))
    return ret

def _nextCmdFromWaitFor8000Queue(self):
    # return the entry waiting for a Status 
    ret = ( None, None )
    if len(self._waitFor8000Queue) > 0:
        ret = self._waitFor8000Queue[0]
        del self._waitFor8000Queue[0]
    self.loggingSend(  'Debug', "--> _nextCmdFromWaitFor8000Queue - Unqueue %s " %( str(ret) ))
    return ret

def _nextCmdFromWaitForAckNackQueue( self ):
    # return the entry waiting for a Ack/Nack 
    ret = ( None, None )
    if len(self._waitForAckNackQueue) > 0:
        ret = self._waitForAckNackQueue[0]
        del self._waitForAckNackQueue[0]
    self.loggingSend(  'Debug', "--> _nextCmdFromWaitForAckNackQueue - Unqueue %s " %( str(ret) ))
    return ret
    
def _nextCmdFromWaitCmdresponseQueue(self):
    # return the entry waiting for Data
    ret = ( None, None )
    if len(self._waitForCmdResponseQueue) > 0:
        ret = self._waitForCmdResponseQueue[0]
        del self._waitForCmdResponseQueue[0]
    self.loggingSend(  'Debug', "--> _nextCmdFromWaitCmdresponseQueue - Unqueue %s " %( str(ret) ))
    return ret

def ReadyToSendIfNeeded( self ):
    readyToSend = len(self.zigateSendQueue) != 0 and len(self._waitFor8000Queue) == 0 and len(self._waitForCmdResponseQueue) == 0
    if readyToSend:
        self.sendData_internal( _nextCmdFromSendQueue( self )[0] )

def _sendData(self, InternalSqn):
    # send data to Zigate via the communication transport

    cmd = self.ListOfCommands[ InternalSqn ]['Cmd']
    datas = self.ListOfCommands[ InternalSqn ]['Datas']

    self.loggingSend(  'Debug', "--> _sendData - %s %s" %(cmd, datas))

    if datas == "":
        length = "0000"
    else:
        length = returnlen(4, (str(hex(int(round(len(datas) / 2)))).split('x')[-1]))  # by Cortexlegeni

    if datas == "":
        checksumCmd = getChecksum(cmd, length, "0")
        strchecksum = '0' + str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + \
                    str(ZigateEncode(strchecksum)) + "03"
    else:
        checksumCmd = getChecksum(cmd, length, datas)
        strchecksum = '0' + str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + \
                    str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"

    self.processCMD4APS( cmd, datas)
    self.loggingSend(  'Debug', "--> _sendData - sending encoded Cmd: %s length: %s CRC: %s Data: %s" \
                %(str(ZigateEncode(cmd)), str(ZigateEncode(length)), str(ZigateEncode(strchecksum)), str(ZigateEncode(datas))))
    self._connection.Send(bytes.fromhex(str(lineinput)), 0)
    self.statistics._sent += 1

def checkTimedOut(self):
    
    if self.checkTimedOutFlag:
        # checkTimedOutForTxQueues can be called either by onHeartbeat or from inside the Class. 
        # In case it comes from onHeartbeat we might have a re-entrance issue
        Domoticz.Error("checkTimedOut already ongoing - Re-entrance")
        return

    self.checkTimedOutFlag = True
    now = int(time())

    self.loggingReceive( 'Debug',"checkTimedOut   - Cmd: %04.X waitQ: %s dataQ: %s SendingFIFO: %s"\
                %(0x0000, len(self._waitFor8000Queue), len(self._waitForCmdResponseQueue), len(self.zigateSendQueue)))

    # Check if we have a Wait for 0x8000 message
    if len(self._waitFor8000Queue) > 0:
        # We are waiting for 0x8000

        InternalSqn, TimeStamp = self._waitFor8000Queue[0]
        if (now - TimeStamp) > self.zTimeOut:
            # Timed Out 0x8000
            # We might have to Timed Out also on the Data ?

            self.statistics._TOstatus += 1
            entry = _nextCmdFromWaitFor8000Queue( self )
            if entry:
                self.loggingReceive( 'Debug',"------>  0x8000- Timeout %s  " % ( entry[0]))

    # Check waitForData
    if len(self._waitForCmdResponseQueue) > 0:
        # We are waiting for a Response from a Command
        InternalSqn, TimeStamp = self._waitForCmdResponseQueue[0]
        #if (now - TimeStamp) > self.zTimeOut:
        if (now - TimeStamp) > 10:
            # No response ! We Timed Out
            self.statistics._TOdata += 1
            InternalSqn, TimeStamp =  _nextCmdFromWaitCmdresponseQueue( self )
            if InternalSqn in self.ListOfCommands:
                self.loggingReceive( 'Debug',"------> - Timeout %s sec on SQN waiting for %s %s %s %04x" 
                    % (now - TimeStamp, InternalSqn, self.ListOfCommands[ InternalSqn ]['Cmd'], self.ListOfCommands[ InternalSqn ]['Datas'],
                    self.ListOfCommands[ InternalSqn ]['ResponseExpectedCmd'] ))

                del self.ListOfCommands[ InternalSqn ]
    
    # Check if there is no TimedOut on ListOfCommands
    #Domoticz.Log("checkTimedOutForTxQueues ListOfCommands size: %s" %len(self.ListOfCommands))
    for x in list(self.ListOfCommands.keys()):
        if  (now - self.ListOfCommands[ x ]['TimeStamp']) > 10:
            if self.ListOfCommands[ x ]['ResponseExpectedCmd']:
                self.loggingSend(  'Debug',"------> Time Out : %s %s %s %04x"
                    %(self.ListOfCommands[ x ]['Cmd'],self.ListOfCommands[ x ]['Datas'], 
                    self.ListOfCommands[ x ]['ResponseExpected'], self.ListOfCommands[ x ]['ResponseExpectedCmd'] ))
            else:
                    self.loggingSend(  'Debug',"------> Time Out : %s %s %s %s"
                    %(self.ListOfCommands[ x ]['Cmd'],self.ListOfCommands[ x ]['Datas'], 
                    self.ListOfCommands[ x ]['ResponseExpected'], self.ListOfCommands[ x ]['ResponseExpectedCmd'] ))                  
            del self.ListOfCommands[ x ]
    self.checkTimedOutFlag = False

    ReadyToSendIfNeeded( self )

def ProcessOtherTypeOfMessage(self, MsgType):
    self.statistics._data += 1
    # There is a probability that we get an ASYNC message, which is not related to a Command request.
    # In that case we should just process this message.
    
    # For now we assume that we do only one command at a time, so either it is an Async message, 
    # or it is related to the command
    self.loggingReceive(  'Debug', "ProcessOtherTypeOfMessage - MsgType: %s" %(MsgType))

    if len(self._waitForCmdResponseQueue) == 0:
        self.loggingReceive(  'Debug', "-----> - WaitForDataQueue empty")
        return

    FirstTupleWaitForData = self._waitForCmdResponseQueue[0]
    InternalSqn = FirstTupleWaitForData[0]
    expResponse = self.ListOfCommands[ InternalSqn ]['ResponseExpectedCmd']

    if expResponse == 0x8100:
        # In case the expResponse is 0x8100 then we can accept 0x8102
        self.loggingSend(  'Debug',"-----> Internal SQN: %s Received: %s and expecting %s" %(InternalSqn, MsgType, '(0x8100, 0x8102)'  ))
        if int(MsgType, 16) not in ( 0x8100, 0x8102):
            self.loggingReceive(  'Debug', "         - Async incoming PacketType")
            return   
    else:
        self.loggingSend(  'Debug',"-----> Internal SQN: %s Received: %s and expecting %04x" %(InternalSqn, MsgType,expResponse  ))
        if int(MsgType, 16) != expResponse:
            self.loggingReceive(  'Debug', "         - Async incoming PacketType")
            return

    # We receive Response for Command, let's cleanup
    cleanup_list_of_commands( self, _nextCmdFromWaitCmdresponseQueue( self )[0] )

    # If we have Still commands in the queue and the WaitforStatus+Data are free
    ReadyToSendIfNeeded( self )

def cleanup_list_of_commands( self, InternalSqn):
    
    self.loggingSend(  'Debug',"-----> Internal SQN: %s" %InternalSqn)
    if InternalSqn in self.ListOfCommands:
        self.loggingSend(  'Debug',"-----> Removing ListOfCommand entry")
        del self.ListOfCommands[ InternalSqn ]

def ProcessMsgType8000(self, Status, PacketType, frame):

    self.loggingSend( 'Debug', "ProcessMsgType8000 - Status: %s PacketType: %s" %(Status, PacketType))

    self.statistics._ack += 1

    # Command Failed, Status != 00
    if Status != '00':
        self.statistics._ackKO += 1
        # In that case we need to unblock data, as we will never get it !
        if len(self._waitForCmdResponseQueue) > 0:
            InternalSqn, TimeStamp = _nextCmdFromWaitCmdresponseQueue( self )
            self.loggingSend( 'Debug', "-------> - unlock waitForData due to command %s failed, remove %s" %(PacketType, InternalSqn))
            if InternalSqn in self.ListOfCommands:
                del self.ListOfCommands[ InternalSqn ]

    # What to do with the Command
    if PacketType != '':
        NextCmdFromWaitFor8000= _nextCmdFromWaitFor8000Queue( self )

        if NextCmdFromWaitFor8000 is None:
            self.loggingSend( 'Debug',"-------> - Empty Queue")
            ReadyToSendIfNeeded( self )
            return

        InternalSqn, TimeStamp = NextCmdFromWaitFor8000
        self.loggingSend( 'Debug',"-------> InternSqn: %s" %InternalSqn)
        if InternalSqn in self.ListOfCommands:
            if self.ListOfCommands[ InternalSqn ]['Cmd']:
                IsCommandOk = int(self.ListOfCommands[ InternalSqn ]['Cmd'],16) == int(PacketType, 16)
                if not IsCommandOk:
                    self.loggingSend( 'Error',"ProcessMsgType8000 - sync error : Expecting %s and Received: %s" \
                            % (self.ListOfCommands[ InternalSqn ]['Cmd'], PacketType))
                    ReadyToSendIfNeeded( self )
                    return
            
            # Let's check if we are not expecting any CmdResponse. In that case we remove the Entry
            if not self.ListOfCommands[ InternalSqn ]['ResponseExpected']:
                self.loggingSend('Debug', "-------> remove Entry Command[%s]: %s" %( InternalSqn, self.ListOfCommands[ InternalSqn ]['Cmd'] ))
                del self.ListOfCommands[ InternalSqn ]

    ReadyToSendIfNeeded( self )

def ZigateEncode(Data):  # ajoute le transcodage

    Out = ""
    Outtmp = ""
    for c in Data:
        Outtmp += c
        if len(Outtmp) == 2:
            if Outtmp[0] == "1" and Outtmp != "10":
                if Outtmp[1] == "0":
                    Outtmp = "0200"
                Out += Outtmp
            elif Outtmp[0] == "0":
                Out += "021" + Outtmp[1]
            else:
                Out += Outtmp
            Outtmp = ""
    return Out

def getChecksum(msgtype, length, datas):
    temp = 0 ^ int(msgtype[0:2], 16)
    temp ^= int(msgtype[2:4], 16)
    temp ^= int(length[0:2], 16)
    temp ^= int(length[2:4], 16)
    for i in range(0, len(datas), 2):
        temp ^= int(datas[i:i + 2], 16)
        chk = hex(temp)
    return chk[2:4]

def returnlen(taille, value):
    while len(value) < taille:
        value = "0" + value
    return str(value)

# Logging functions
def _writeMessage( self, message):
    message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
    self.loggingFileHandle.write( message )
    self.loggingFileHandle.flush()

def _loggingStatus( self, message):
    Domoticz.Status( message )
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _writeMessage( self, message)

def _loggingLog( self, message):
    Domoticz.Log( message )
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _writeMessage( self, message)

def _loggingDebug( self, message):
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _writeMessage( self, message)
    else:
        Domoticz.Log( message )

