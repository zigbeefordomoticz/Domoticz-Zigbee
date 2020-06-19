# !/usr/bin/env python3
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
from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_RESPONSES, ZIGATE_COMMANDS, RETRANSMIT_COMMAND, ADDRESS_MODE
from Modules.sqnMgmt import sqn_init_stack, sqn_generate_new_internal_sqn, sqn_add_external_sqn, sqn_get_internal_sqn, E_SQN_APS, E_SQN_APP

STANDALONE_MESSAGE = []
PDM_COMMANDS = ( '8300', '8200', '8201', '8204', '8205', '8206', '8207', '8208' )
CMD_PDM_ON_HOST = []
CMD_ONLY_STATUS = []
CMD_WITH_ACK = []
CMD_NWK_2NDBytes = {}
CMD_WITH_RESPONSE = {}

class ZigateTransport(object):
    # """
    # Class in charge of Transport mecanishm to and from Zigate
    # Managed also the Command - > Status - > Data sequence
    # """

    def __init__(self, LOD, transport, statistics, pluginconf, F_out, loggingFileHandle, serialPort = None, wifiAddress = None, wifiPort = None):


        # Statistics
        self.statistics = statistics
        self.pluginconf = pluginconf

        # PDM attributes
        self.lock = False   # PDM Lock
        self.PDMCommandOnly = False    # This flag indicate if any command can be sent to Zigate or only PDM related one

        # Queue Management attributes
        self.checkTimedOutFlag = None
        self.ListOfCommands = {}     # List of ( Command, Data ) to be or in process
        self.zigateSendQueue = []    # list of normal priority commands
        self._waitFor8000Queue = []  # list of command sent and waiting for status 0x8000
        self._waitForCmdResponseQueue = []  # list of command sent for which status received and waiting for data
        self._waitForAckNack = []    # Contains list of Command waiting for Ack/Nack

        self.firmware_with_aps_sqn = False

        self.zmode = pluginconf.pluginConf['zmode'].lower()
        self.loggingSend( 'Status', "==> Transport Mode: %s" %self.zmode)

        sqn_init_stack (self)

        # Communication/Transport link attributes
        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port

        # Call back function to send back to plugin
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin

        # Logging
        self.loggingFileHandle = loggingFileHandle

        initMatrix( self)

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
            _logging_debug( self, message )
        elif  logType == 'Log':
            _logging_log( self, message )
        elif logType == 'Status':
            _logging_status( self, message )
        elif logType == 'Error':
            _logging_error( self, message)

    def logging_receive( self, logType, message):
        # Log all activities received from ZiGate
        if self.pluginconf.pluginConf['debugTransportRx'] and logType == 'Debug':
            _logging_debug( self, message )
        elif  logType == 'Log':
            _logging_log( self, message )
        elif logType == 'Status':
            _logging_status( self, message )
        elif logType == 'Error':
            _logging_error( self, message)

    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return len(self.zigateSendQueue)

    # Transport / Opening / Closing Communication
    def set_connection( self ):

        if self._connection is not None:
            del self._connection
            self._connection = None

        if self._transp in ["USB", "DIN", "PI"]:
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" %( self._serialPort ))
                BAUDS = 115200
                self._connection = Domoticz.Connection(Name = "ZiGate", Transport = "Serial", Protocol = "None", 
                         Address = self._serialPort, Baud = BAUDS)

        elif self._transp == "Wifi":
            Domoticz.Status("Connection Name: Zigate, Transport: TCP/IP, Address: %s:%s" %( self._serialPort, self._wifiPort ))
            self._connection = Domoticz.Connection(Name = "Zigate", Transport = "TCP/IP", Protocol = "None ", 
                         Address = self._wifiAddress, Port = self._wifiPort)
        else:
            Domoticz.Error("Unknown Transport Mode: %s" %self._transp)

    def open_conn(self):
        self.set_connection()
        if self._connection:
            self._connection.Connect()
        else:
            Domoticz.Error("openConn _connection note set!")
        Domoticz.Status("Connection open: %s" %self._connection)

    def close_conn(self):
        Domoticz.Status("Connection close: %s" %self._connection)
        self._connection.Disconnect()
        del self._connection
        self._connection = None

    def re_conn(self):
        Domoticz.Status("Reconnection: %s" %self._connection)
        if self._connection.Connected() :
            Domoticz.Log(" --  > still connected!")
            self.close_conn()
        self.open_conn()

    # PDMonhost related
    def pdm_lock( self , lock):
        # Take a Lock to protect all communications from/to ZiGate (PDM on Host)
        self.PDMCommandOnly = lock

    def pdm_lock_status( self ):
        return self.PDMCommandOnly

    def sendData(self, cmd, datas , delay = None):
        self.loggingSend(  'Debug', "sendData - %s %s FIFO: %s" %(cmd, datas, len(self.zigateSendQueue)))
        if datas is None:
            datas = ''
        if datas != '' and not is_hex( datas):
            Domoticz.Error("sendData_internal - receiving a non hexa Data: > %s < " %datas)
            return None

        # Check if the Cmd/Data is not yet in the pipe
        alreadyInQueue = False
        for x in self.ListOfCommands:
            if self.ListOfCommands[ x ]['Cmd'] ==  cmd and self.ListOfCommands[ x ]['Datas'] == datas:
                self.loggingSend(  'Debug', "Cmd: %s Data: %s already in queue." %(cmd, datas))
                alreadyInQueue = True
                break
        if alreadyInQueue:
            for x in self.ListOfCommands:
                Domoticz.Log("Sending Queue: [%s] Cmd: %s Datas: %s Time: %s"
                    %( x, self.ListOfCommands[ x ]['Cmd'], self.ListOfCommands[ x ]['Datas'],
                    self.ListOfCommands[ x ]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S") ))
            return None

        # Let's move on, create an internal Sqn for tracking
        InternalSqn = sqn_generate_new_internal_sqn(self)
        if InternalSqn in self.ListOfCommands:
            # Unexpected !
            Domoticz.Error("sendData - Existing Internal SQN: %s for %s versus new %s/%s" %( InternalSqn, str(self.ListOfCommands[ InternalSqn]), cmd, datas ))
            return None

        self.ListOfCommands[ InternalSqn ] = {}
        self.ListOfCommands[ InternalSqn ]['Cmd']                 = cmd
        self.ListOfCommands[ InternalSqn ]['Datas']               = datas
        self.ListOfCommands[ InternalSqn ]['ReTransmit']          = 0
        self.ListOfCommands[ InternalSqn ]['Status']              = ''
        self.ListOfCommands[ InternalSqn ]['ReceiveTimeStamp']    = datetime.now()
        self.ListOfCommands[ InternalSqn ]['SentTimeStamp']       = None
        self.ListOfCommands[ InternalSqn ]['PDMCommand']          = False
        self.ListOfCommands[ InternalSqn ]['ResponseExpected']    = False
        self.ListOfCommands[ InternalSqn ]['MessageResponse']     = None
        self.ListOfCommands[ InternalSqn ]['ExpectedAck']         = False 

        if int(cmd, 16) in CMD_PDM_ON_HOST:
            self.ListOfCommands[ InternalSqn ]['PDMCommand']      = True
        if int(cmd, 16) in CMD_WITH_RESPONSE:
            self.ListOfCommands[ InternalSqn ]['MessageResponse'] = CMD_WITH_RESPONSE[int(cmd, 16)]
            self.ListOfCommands[ InternalSqn ]['ResponseExpected'] = True
        if int(cmd, 16) in CMD_WITH_ACK:
            self.ListOfCommands[ InternalSqn ]['ExpectedAck']      = True 
        if self.ListOfCommands[ InternalSqn ]['ResponseExpected']:
            self.loggingSend(  'Debug', "sendData - InternalSQN: %s Cmd: %s Data: %s ExpectedCmd: %04x"
                %(InternalSqn, cmd, datas, self.ListOfCommands[ InternalSqn ]['MessageResponse'] ))
        else:
            self.loggingSend(  'Debug', "sendData - InternalSQN: %s Cmd: %s Data: %s"
                %(InternalSqn, cmd, datas ))

        send_data_internal ( self, InternalSqn )
        return InternalSqn

    def on_message(self, Data):
        # Process/Decode Data

        self.logging_receive( 'Debug2', "onMessage - %s" %(Data))
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
                process_frame(self, AsciiMsg)

    def check_timed_out_for_tx_queues(self):
        check_timed_out(self)
      
# Local Functions
def initMatrix( self ):
    for x in ZIGATE_RESPONSES:
        STANDALONE_MESSAGE.append( x )
        
    for x in ZIGATE_COMMANDS:
        self.loggingSend( 'Debug',"Command: %04x Ack: %s Sequence: %s/%s" 
            %( x, ZIGATE_COMMANDS[ x ]['Ack'], len( ZIGATE_COMMANDS[ x ]['Sequence'] ),ZIGATE_COMMANDS[ x ]['Sequence'] ))

        if ZIGATE_COMMANDS[ x ]['NwkId 2nd Bytes']:
            self.loggingSend( 'Debug',"--> 2nd Byte for NwkId")
            CMD_NWK_2NDBytes[ x ] = x

        if ZIGATE_COMMANDS[ x ]['Ack']:
            self.loggingSend( 'Debug',"--> Ack")
            CMD_WITH_ACK.append( x )

        if len( ZIGATE_COMMANDS[ x ]['Sequence'] ) == 0:
            self.loggingSend( 'Debug',"--> PDM")
            CMD_PDM_ON_HOST.append ( x )

        elif len( ZIGATE_COMMANDS[ x ]['Sequence'] ) == 1:
            self.loggingSend( 'Debug',"--> Command Only")
            CMD_ONLY_STATUS.append( x )

        elif len( ZIGATE_COMMANDS[ x ]['Sequence'] ) == 2:
            self.loggingSend( 'Debug',"--> Response Expected for %04x -> %s" %(x,ZIGATE_COMMANDS[ x ]['Sequence'][1] ))
            CMD_WITH_RESPONSE[ x ] = ZIGATE_COMMANDS[ x ]['Sequence'][1]

    #self.loggingSend( 'Debug', "STANDALONE_MESSAGE: %s" %STANDALONE_MESSAGE)
    #self.loggingSend( 'Debug', "CMD_ONLY_STATUS: %s" %CMD_ONLY_STATUS)
    #self.loggingSend( 'Debug', "ZIGATE_COMMANDS: %s" %ZIGATE_COMMANDS)
    #self.loggingSend( 'Debug', "CMD_NWK_2NDBytes: %s" %CMD_NWK_2NDBytes)
    #self.loggingSend( 'Debug', "CMD_WITH_RESPONSE: %s" %CMD_WITH_RESPONSE)
    #self.loggingSend( 'Debug', "CMD_WITH_ACK: %s" %CMD_WITH_ACK)

# Queues Managements
def _add_cmd_to_send_queue(self, InternalSqn ):
    # add a command to the waiting list
    timestamp = int(time())
    # Check if the Cmd+Data is not yet in the Queue. If yes forget that message
    self.loggingSend(  'Debug2', " --  > _add_cmd_to_send_queue - adding to Queue %s %s" %(InternalSqn, timestamp ))
    self.zigateSendQueue.append( (InternalSqn, timestamp))
    # Manage Statistics
    if len(self.zigateSendQueue) > self.statistics._MaxLoad:
        self.statistics._MaxLoad = len(self.zigateSendQueue)
    self.statistics._Load = len(self.zigateSendQueue)

def _next_cmd_from_send_queue(self):
    
    # return the next Command to send (pop)
    ret = ( None, None)
    if len(self.zigateSendQueue) > 0:
        ret = self.zigateSendQueue[0]
        del self.zigateSendQueue[0]
    self.loggingSend(  'Debug2', " --  > _nextCmdFromSendQueue - Unqueue %s " %( str(ret) ))
    return ret

def _add_cmd_to_wait_for8000_queue(self, InternalSqn ):
    # add a command to the waiting list for 0x8000
    timestamp = int(time())
    self.loggingSend(  'Debug2', " --  > _add_cmd_to_wait_for8000_queue - adding to Queue %s %s" %(InternalSqn, timestamp))
    self._waitFor8000Queue.append( (InternalSqn, timestamp) )

def _next_cmd_from_wait_for8000_queue(self):
    # return the entry waiting for a Status 
    ret = ( None, None )
    if len(self._waitFor8000Queue) > 0:
        ret = self._waitFor8000Queue[0]
        del self._waitFor8000Queue[0]
    self.loggingSend(  'Debug2', " --  > _nextCmdFromWaitFor8000Queue - Unqueue %s " %( str(ret) ))
    return ret

def _add_cmd_to_wait_for_ack_nack_queue( self, InternalSqn):
    # add a command to the AckNack waiting list
    timestamp = int(time())
    self.loggingSend(  'Debug2', " --  > _addCmdToWaitForAckNackQueue - adding to Queue  %s %s" %(InternalSqn, timestamp))
    self._waitForAckNack.append( (InternalSqn, timestamp) )

def _next_cmd_to_wait_for_ack_nack_queue( self):
    # return the entry waiting for Data
    ret = ( None, None )
    if len(self._waitForAckNack) > 0:
        ret = self._waitForAckNack[0]
        del self._waitForAckNack[0]
    self.loggingSend(  'Debug2', " --  > _next_cmd_to_wait_for_ack_nack_queue - Unqueue %s " %( str(ret) ))
    return ret    

def _add_cmd_to_wait_for_cmdresponse_queue(self, InternalSqn):
    # add a command to the waiting list
    # _waitForDataQueue [ Expected Response Type, Cmd, Data, TimeStamps ]
    timestamp = int(time())
    self.loggingSend(  'Debug2', " --  > _add_cmd_to_wait_for_cmdresponse_queue - adding to Queue %s %s" %(InternalSqn, timestamp))
    self._waitForCmdResponseQueue.append( (InternalSqn, timestamp) )

def _next_cmd_from_wait_cmdresponse_queue(self):
    # return the entry waiting for Data
    ret = ( None, None )
    if len(self._waitForCmdResponseQueue) > 0:
        ret = self._waitForCmdResponseQueue[0]
        del self._waitForCmdResponseQueue[0]
    self.loggingSend(  'Debug2', " --  > _next_cmd_from_wait_cmdresponse_queue - Unqueue %s " %( str(ret) ))
    return ret

# Sending functions
def send_data_internal(self, InternalSqn):
    # 
    # in charge of sending Data. Call by sendZigateCmd
    # If nothing in the waiting queue, will call _send_data and it will be sent straight to Zigate

    if InternalSqn not in self.ListOfCommands:
        # Unexpected
        Domoticz.Error("send_data_internal - unexpected 1 %s not in ListOfCommands: %s" %(InternalSqn, str(self.ListOfCommands.keys())))
        return

    self.loggingSend(  'Debug2', "--- send_data_internal - %s FIFO: %s" %(InternalSqn, len(self.zigateSendQueue)))

    sendNow = True
    # PDM Management.
    # When PDM traffic is ongoing we cannot interupt, so we need to FIFO all other commands until the PDMLock is released
    if self.pdm_lock_status() and self.ListOfCommands[ InternalSqn ]['Cmd'] not in PDM_COMMANDS:
        # Only PDM related command can go , all others will be dropped.
        Domoticz.Log("PDM not yet ready, FIFO command %s %s" %(self.ListOfCommands[ InternalSqn ]['Cmd'], self.ListOfCommands[ InternalSqn ]['Datas']))
        sendNow = False

    if sendNow and self.zmode in ( 'zigbee31c','zigbee31d'):
        sendNow = (len(self._waitFor8000Queue) == 0 and len(self._waitForCmdResponseQueue) == 0) or self.ListOfCommands[ InternalSqn ]['PDMCommand']
        self.loggingSend(  'Debug2', "--- send_data_internal - Command: %s  Q(0x8000): %s Q(Response): %s sendNow: %s" 
            %(self.ListOfCommands[ InternalSqn ]['Cmd'], len(self._waitFor8000Queue), len(self._waitForCmdResponseQueue), sendNow))

    elif sendNow and self.zmode == 'zigbeeack':
        sendNow = (len(self._waitFor8000Queue) == 0 and len(self._waitForAckNack) == 0) or self.ListOfCommands[ InternalSqn ]['PDMCommand']
        self.loggingSend( 'Debug2', "--- send_data_internal - Command: %s  Q(0x8000): %s Q(Ack/Nack): %s sendNow: %s" 
            %(self.ListOfCommands[ InternalSqn ]['Cmd'], len(self._waitFor8000Queue), len(self._waitForAckNack), sendNow))
    else:
        self.loggingSend( 'Error', "--- send_data_internal - Undefined or unknown zMode: %s" %self.zmode)

    # In case the cmd is part of the PDM on Host commands, that is High Priority and must go through.
    if not sendNow:
        # Put in FIFO
        self.loggingSend( 'Debug2', "--- send_data_internal - put in waiting queue")
        self.ListOfCommands[ InternalSqn ]['Status'] = 'QUEUED'
        _add_cmd_to_send_queue( self, InternalSqn )
        return

    # Sending Command
    self.loggingSend( 'Debug', "--- send_data_internal - sending now")

    if not self.ListOfCommands[ InternalSqn ]['PDMCommand']:
        # That is a Standard command (not PDM on  Host), let's process as usall
        self.ListOfCommands[ InternalSqn ]['Status'] = 'TO-SEND'

        # Add to 0x8000 queue
        _add_cmd_to_wait_for8000_queue( self, InternalSqn )

        # if  self.zmode == 'zigbee31c' and self.ListOfCommands[ InternalSqn ]['Cmd'] == '0100':
        #     # Do not wait on 0x0100 for 0x8100 as it will come as 0x8102 (which is also Report Attributes)
        #     self.ListOfCommands[InternalSqn]['ResponseExpected'] = False
        #     self.ListOfCommands[InternalSqn]['MessageResponse'] = None

        if self.ListOfCommands[InternalSqn]['Cmd'] == '0049' and self.ListOfCommands[InternalSqn]['Datas'] == 'FFFC0000' :
            self.ListOfCommands[InternalSqn]['ResponseExpected'] = False
            self.ListOfCommands[InternalSqn]['MessageResponse'] = None

        if self.zmode in ( 'zigbee31c', 'zigbee31d') and self.ListOfCommands[ InternalSqn ]['ResponseExpected']:
            if not self.pluginconf.pluginConf['CompatibilityMode'] or self.ListOfCommands[ InternalSqn ]['Cmd'] != '0100':
                self.loggingSend( 'Debug', "--- Add to Queue CommandResponse Queue")
                _add_cmd_to_wait_for_cmdresponse_queue( self, InternalSqn )
            else:
                self.loggingSend( 'Debug', "--- Compatibility mode enabled, do not block %s" %self.ListOfCommands[ InternalSqn ]['Cmd'])

        elif self.zmode == 'zigbeeack' and self.ListOfCommands[ InternalSqn ]['ExpectedAck']:
            set_acknack_for_sending( self, InternalSqn)

    # Go!
    _send_data( self, InternalSqn )

def set_acknack_for_sending(self, i_sqn):

    # These are ZiGate commands which doesn't have Ack/Nack with firmware up to 3.1c
    CMD_NOACK_ZDP = (  0x0030, 0x0031, 0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047, 0x0049, 0x004A, 0x004B, 0x004E, 0x0530, 0x0531, 0x0532, 0x0533 )

    # If ZigBeeAck mode and Ack Expected
    if not self.firmware_with_aps_sqn and int(self.ListOfCommands[ i_sqn ]['Cmd'],16) in CMD_NOACK_ZDP:
            self.loggingSend( 'Debug', "--- ZDP command no Ack/Nack with that firmware")
            self.ListOfCommands[ i_sqn ]['ExpectedAck'] = False

    elif int(self.ListOfCommands[ i_sqn ]['Cmd'],16) not in CMD_NWK_2NDBytes:
        if self.ListOfCommands[ i_sqn ]['Cmd'] == '004E' and self.ListOfCommands[ i_sqn ]['Datas'][0:4] == '0000':
            # Do not wait for LQI request to ZiGate
            self.loggingSend( 'Debug', "--- LQI request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[ i_sqn ]['ExpectedAck'] = False
        else:
            # Wait for Ack/Nack 
            self.loggingSend( 'Debug', "--- Add to Queue Ack/Nack")
            _add_cmd_to_wait_for_ack_nack_queue( self, i_sqn)
    else:
        if self.ListOfCommands[ i_sqn ]['Datas'][0:2] == '%02x' %ADDRESS_MODE['group']:
            # Do not wait for Ack/Nack as the command to Groups
            self.loggingSend( 'Debug', "--- Group command to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[ i_sqn ]['ExpectedAck'] = False

        elif self.ListOfCommands[ i_sqn ]['Datas'][2:6] == '0000':
            # Do not wait for Ack/Nack as the command is sent for ZiGate
            self.loggingSend( 'Debug', "--- Cmmand to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[ i_sqn ]['ExpectedAck'] = False

        else:
            # Wait for Ack/Nack if NwkId != '0000' and Address Mode (ZiGate)
            self.loggingSend( 'Debug', "--- Add to Queue Ack/Nack %s %s" %(self.ListOfCommands[ i_sqn ]['Cmd'], self.ListOfCommands[ i_sqn ]['Datas']))
            _add_cmd_to_wait_for_ack_nack_queue( self, i_sqn)

def ready_to_send_if_needed( self ):

    readyToSend = True
    if self.zmode in ( 'zigbee31c','zigbee31d'):
        readyToSend = len(self.zigateSendQueue) != 0 and len(self._waitFor8000Queue) == 0 and len(self._waitForCmdResponseQueue) == 0
        self.loggingSend(  'Debug2', "--- send_data_internal - Q(0x8000): %s Q(Ack/Nack): %s sendNow: %s" 
            %(len(self.zigateSendQueue),len(self._waitFor8000Queue), len(self._waitFor8000Queue) ))

    elif self.zmode == 'zigbeeack':
        readyToSend = len(self.zigateSendQueue) != 0 and len(self._waitFor8000Queue) == 0 and len(self._waitFor8000Queue) == 0
        self.loggingSend(  'Debug2', "--- send_data_internal - Q(0x8000): %s Q(Ack/Nack): %s sendNow: %s" 
            %(len(self.zigateSendQueue),len(self._waitFor8000Queue), len(self._waitFor8000Queue) ))

    if readyToSend:
        send_data_internal( self, _next_cmd_from_send_queue( self )[0] )

def _send_data(self, InternalSqn):
    # send data to Zigate via the communication transport

    cmd = self.ListOfCommands[ InternalSqn ]['Cmd']
    datas = self.ListOfCommands[ InternalSqn ]['Datas']
    self.ListOfCommands[ InternalSqn ]['Status'] = 'SENT'
    self.ListOfCommands[ InternalSqn ]['SentTimeStamp'] = int(time())

    self.loggingSend(  'Debug', "---  --  > _send_data - [%s] %s %s" %(InternalSqn, cmd, datas))

    if datas == "":
        length = "0000"
        checksumCmd = get_checksum(cmd, length, "0")
        strchecksum = '0' + str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(zigate_encode(cmd)) + str(zigate_encode(length)) + \
                    str(zigate_encode(strchecksum)) + "03"
    else:
        #Domoticz.Log("---> datas: %s" %datas)
        length = '%04x' %(len(datas)//2)

        checksumCmd = get_checksum(cmd, length, datas)
        strchecksum = '0' + str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(zigate_encode(cmd)) + str(zigate_encode(length)) + \
                    str(zigate_encode(strchecksum)) + str(zigate_encode(datas)) + "03"

    self.loggingSend(  'Debug', "---  --  > _send_data - sending encoded Cmd: %s length: %s CRC: %s Data: %s" \
                %(str(zigate_encode(cmd)), str(zigate_encode(length)), str(zigate_encode(strchecksum)), str(zigate_encode(datas))))
    self._connection.Send(bytes.fromhex(str(lineinput)), 0)
    self.statistics._sent += 1

def check_timed_out(self):

    def timeout_8000( self ):
        # Timed Out 0x8000
        self.statistics._TOstatus += 1
        entry = _next_cmd_from_wait_for8000_queue( self )
        if entry is None:
            return
        InternalSqn, TimeStamp = entry
        logExpectedCommand( self, '0x8000', now, TimeStamp, InternalSqn)
        if InternalSqn in self.ListOfCommands:
            if self.zmode == 'zigbeeack' and self.ListOfCommands[ InternalSqn ]['ExpectedAck']:
                cleanup_list_of_commands( self, InternalSqn)
            elif self.zmode in ( 'zigbee31c','zigbee31d') and self.ListOfCommands[ InternalSqn ]['ResponseExpected']:
                cleanup_list_of_commands( self, InternalSqn)

    def timeout_acknack( self ):
        self.statistics._TOstatus += 1
        entry = _next_cmd_to_wait_for_ack_nack_queue( self )
        if entry is None:
            return
        InternalSqn, TimeStamp = entry
        logExpectedCommand( self, 'Ack', now, TimeStamp, InternalSqn)
        cleanup_list_of_commands( self, InternalSqn)

    def timeout_cmd_response( self ):
        # No response ! We Timed Out
        self.statistics._TOdata += 1
        InternalSqn, TimeStamp =  _next_cmd_from_wait_cmdresponse_queue( self )
        if InternalSqn not in self.ListOfCommands:
            return
        logExpectedCommand( self, 'CmdResponse', now, TimeStamp, InternalSqn)
        cleanup_list_of_commands( self, InternalSqn)

    def check_and_timeout_listofcommand( self ):
        if len(self.ListOfCommands) == 0:
            return
        
        self.loggingSend( 'Debug', "-- checkTimedOutForTxQueues ListOfCommands size: %s" %len(self.ListOfCommands))
        for x in list(self.ListOfCommands.keys()):
            if  self.ListOfCommands[ x ]['SentTimeStamp'] and  (now - self.ListOfCommands[ x ]['SentTimeStamp']) > TIME_OUT_LISTCMD:
                if self.ListOfCommands[ x ]['MessageResponse']:
                    self.loggingSend( 'Debug', " --  --  --  > - Time Out : [%s] %s %s Flags: %s/%s %04x Status: %s Time: %s"
                        %(x, self.ListOfCommands[ x ]['Cmd'], self.ListOfCommands[ x ]['Datas'], self.ListOfCommands[ x ]['ResponseExpected'], 
                            self.ListOfCommands[ x ]['ExpectedAck'], self.ListOfCommands[ x ]['MessageResponse'],
                            self.ListOfCommands[ x ]['Status'] ,
                            self.ListOfCommands[ x ]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")) )
                else:
                    self.loggingSend( 'Debug', " --  --  --  > - Time Out : [%s] %s %s Flags: %s/%s Status: %s Time: %s "
                        %(x, self.ListOfCommands[ x ]['Cmd'], self.ListOfCommands[ x ]['Datas'], 
                            self.ListOfCommands[ x ]['ResponseExpected'], self.ListOfCommands[ x ]['ExpectedAck'],
                            self.ListOfCommands[ x ]['Status'] ,
                            self.ListOfCommands[ x ]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S") )  )

                del self.ListOfCommands[ x ]

    def logExpectedCommand( self, desc, now, TimeStamp, i_sqn):
        if i_sqn not in self.ListOfCommands:
            self.loggingSend( 'Debug', " --  --  --  > - %s - Time Out %s  " % ( desc, i_sqn ))
            return
        if self.ListOfCommands[ i_sqn ]['MessageResponse']:
            self.loggingSend( 'Debug', " --  --  --  > Time Out %s [%s] %s sec for  %s %s %s/%s %04x Time: %s" \
                % (desc, i_sqn, (now - TimeStamp), self.ListOfCommands[ i_sqn ]['Cmd'], self.ListOfCommands[ i_sqn ]['Datas'], 
                self.ListOfCommands[ i_sqn ]['ResponseExpected'], self.ListOfCommands[ i_sqn ]['ExpectedAck'],
                self.ListOfCommands[ i_sqn ]['MessageResponse'], self.ListOfCommands[ InternalSqn ]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")  ))
        else:
            self.loggingSend( 'Debug', " --  --  --  > Time Out %s [%s] %s sec for  %s %s %s/%s %s Time: %s" \
                % (desc, i_sqn, (now - TimeStamp), self.ListOfCommands[ i_sqn ]['Cmd'], self.ListOfCommands[ i_sqn ]['Datas'], 
                self.ListOfCommands[ i_sqn ]['ResponseExpected'], self.ListOfCommands[ i_sqn ]['ExpectedAck'],
                self.ListOfCommands[ i_sqn ]['MessageResponse'], self.ListOfCommands[ InternalSqn ]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S") ))

    # Begin
    TIME_OUT_8000 = self.pluginconf.pluginConf['TimeOut8000']
    TIME_OUT_RESPONSE = self.pluginconf.pluginConf['TimeOutResponse']
    TIME_OUT_ACK = self.pluginconf.pluginConf['TimeOut8011']
    TIME_OUT_LISTCMD = 10

    if self.checkTimedOutFlag:
        # check_timed_out can be called either by onHeartbeat or from inside the Class. 
        # In case it comes from onHeartbeat we might have a re-entrance issue
        Domoticz.Error("checkTimedOut already ongoing - Re-entrance")
        return

    self.checkTimedOutFlag = True
    now = int(time())

    self.loggingSend( 'Debug', "checkTimedOut  Start - waitQ: %2s ackQ: %2s dataQ: %2s SendingFIFO: %3s"\
                %( len(self._waitFor8000Queue), len(self._waitForAckNack), len(self._waitForCmdResponseQueue), len(self.zigateSendQueue)))

    # Check if we have a Wait for 0x8000 message
    if len(self._waitFor8000Queue) > 0:
        # We are waiting for 0x8000
        InternalSqn, TimeStamp = self._waitFor8000Queue[0]
        if (now - TimeStamp) >= TIME_OUT_8000:
            timeout_8000( self )

    # Check Ack/Nack
    if len(self._waitForAckNack) > 0 and self.zmode == 'zigbeeack':
        # We are waiting for APS Ack/Nack
        InternalSqn, TimeStamp = self._waitForAckNack[0]
        if (now - TimeStamp) >= TIME_OUT_ACK:
            timeout_acknack( self )

    # Check waitForData
    if len(self._waitForCmdResponseQueue) > 0 and self.zmode in ( 'zigbee31c','zigbee31d'):
        # We are waiting for a Response from a Command
        InternalSqn, TimeStamp = self._waitForCmdResponseQueue[0]
        if (now - TimeStamp) >= TIME_OUT_RESPONSE:
            timeout_cmd_response( self )

    # Check if there is no TimedOut on ListOfCommands
    check_and_timeout_listofcommand( self )

    self.checkTimedOutFlag = False
    ready_to_send_if_needed( self )
        
    self.logging_receive( 'Debug', "checkTimedOut  End   - waitQ: %2s ackQ: %2s dataQ: %2s SendingFIFO: %3s" 
        %( len(self._waitFor8000Queue), len(self._waitForAckNack), len(self._waitForCmdResponseQueue), len(self.zigateSendQueue)))


def cleanup_list_of_commands( self, i_sqn):
    
    self.loggingSend(  'Debug', " --  -- - > Cleanup Internal SQN: %s" %i_sqn)
    if i_sqn in self.ListOfCommands:
        self.loggingSend(  'Debug', " --  -- - > Removing ListOfCommand entry")
        del self.ListOfCommands[ i_sqn ]

# Receiving functions
def process_frame(self, frame):

    def cleanup_8000_queues( self, status , isqn):
        # Cleanup if required
        if Status == '00':
            if self.zmode == 'zigbeeack' and not self.ListOfCommands[ isqn ]['ExpectedAck']:
                cleanup_list_of_commands( self, isqn)
            elif self.zmode in ( 'zigbee31c','zigbee31d') and not self.ListOfCommands[ isqn ]['ResponseExpected']:
                cleanup_list_of_commands( self, isqn)
        else:
            # Status != '00
            if self.zmode == 'zigbeeack' and self.ListOfCommands[ isqn ]['ExpectedAck']:
                cleanup_list_of_commands( self, isqn)

            elif self.zmode in ( 'zigbee31c','zigbee31d') and  self.ListOfCommands[ isqn ]['ResponseExpected']:
                cleanup_list_of_commands( self, isqn)

    # will return the Frame in the Data if any
    # process the Data and check if this is a 0x8000 message
    # in case the message contains several frame, receiveData will be recall
    self.logging_receive(  'Debug', "process_frame - Frame: %s" %frame)
    if frame == '' or frame is None or len(frame) < 12:
        return

    Status = None
    MsgData = None
    i_sqn = None
    MsgType = frame[2:6]
    MsgLength = frame[6:10]
    MsgCRC = frame[10:12]
    self.logging_receive( 'Debug', "process_frame - MsgType: %s MsgLength: %s MsgCRC: %s" %(MsgType, MsgLength, MsgCRC))
    
    if len(frame) >= 18:
        #Payload
        MsgData = frame[12:len(frame) - 4]
        RSSI = frame[len(frame) - 4: len(frame) - 2]

    if MsgData and MsgType == "8000":  
        Status = MsgData[0:2]
        sqn_app = MsgData[2:4]
        PacketType = MsgData[4:8] 

        sqn_aps = None  
        Ack_expected = None
        if len(MsgData) == 12:
            # New Firmware 3.1d (get aps sqn)
            Ack_expected = MsgData[8:10]
            sqn_aps = MsgData[10:12]
            if not self.firmware_with_aps_sqn:
                self.firmware_with_aps_sqn = True

        i_sqn = process_msg_type8000(self, Status, PacketType, sqn_app, sqn_aps, Ack_expected)
        self.loggingSend( 'Debug', "0x8000 - [%s] sqn_app: 0x%s/%3s, SQN_APS: 0x%s Ack_expected: %s" %(i_sqn, sqn_app, int(sqn_app,16), sqn_aps, Ack_expected))
        self.F_out(frame, None)

        if i_sqn in self.ListOfCommands:
            self.loggingSend( 'Debug',"--> Check cleanup Status: %s [%s] Cmd: %s Data: %s ExpectedAck: %s ResponseExpected: %s" 
                %( Status, i_sqn, self.ListOfCommands[ i_sqn ]['Cmd'], self.ListOfCommands[ i_sqn ]['Datas'], 
                   self.ListOfCommands[ i_sqn ]['ExpectedAck'], self.ListOfCommands[ i_sqn ]['ResponseExpected']))
            self.ListOfCommands[ i_sqn ]['Status'] = '8000'
            cleanup_8000_queues( self, Status, i_sqn)

        else:
            if i_sqn is not None:
                Domoticz.Error("i_sqn: %s not found in %s" %(i_sqn, str(self.ListOfCommands.keys())))    

        ready_to_send_if_needed( self )
        return

    if  MsgType == '8011':
        if MsgData and self.zmode in ( 'zigbee31c','zigbee31d'):
            if Status == '00':
                # Ack
                self.statistics._APSAck += 1
            else:
                # Nack
                self.statistics._APSNck += 1
            self.F_out(frame, None)
            ready_to_send_if_needed( self )
            return

        if MsgData and self.zmode == 'zigbeeack': 
            # This is Optimum with firmware 3.1d and above
            MsgStatus = MsgData[0:2]
            MsgSrcAddr = MsgData[2:6]
            MsgSrcEp = MsgData[6:8]
            MsgClusterId = MsgData[8:12]
            MsgSEQ = 0
            if len(MsgData) > 12 :
                MsgSEQ = MsgData[12:14]

            if self.firmware_with_aps_sqn:
                i_sqn = process_msg_type8011_above31d( self, MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgSEQ )
            else:
                i_sqn = process_msg_type8011_below31c( self, MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgSEQ )

            ReportingCommand = None
            if i_sqn in self.ListOfCommands:
                self.ListOfCommands[ i_sqn ]['Status'] = '8011'
                ReportingCommand = dict(self.ListOfCommands[ i_sqn ])
            self.F_out(frame, ReportingCommand )  # Forward the message to plugin for further processing

            # We receive Response for Command, let's cleanup
            cleanup_list_of_commands( self, i_sqn )
            ready_to_send_if_needed( self )
        return

    if MsgType == '8701':
        # Route Discovery
        # self.F_out(frame, None)  # for processing
        ready_to_send_if_needed( self )
        return        

    if MsgType == "8702":
        # APS Failure
        # i_sqn = process_msg_type8702( self, MsgData )
        self.statistics._APSFailure += 1
        self.F_out(frame, None)
        ready_to_send_if_needed( self )
        return

    if int(MsgType, 16) in STANDALONE_MESSAGE:  # We receive an async message, just forward it to plugin
        self.F_out(frame, None )  # for processing
        ready_to_send_if_needed( self )
        return

    # We reach that stage: Got a message not 0x8000/0x8011/0x8701/0x8202 an not a standolone message
    # But might be a 0x8102 ( as firmware 3.1c and below are reporting Read Attribute response and Report Attribute with the same MsgType)
    if self.zmode in ( 'zigbee31c','zigbee31d'):
        # If ZigBee Command blocked until response received
        if not self.firmware_with_aps_sqn and MsgType== '8102':
            MsgZclSqn =  MsgData[0:2]
            self.loggingSend( 'Debug', "--> Receive MsgType: %s with ExtSqn: %s" %(MsgType, MsgZclSqn))

            i_sqn = process_other_type_of_message( self, MsgType, MsgZclSqn)
        else:
            i_sqn = process_other_type_of_message( self, MsgType)
        if i_sqn in self.ListOfCommands:
            self.ListOfCommands[ i_sqn ]['Status'] = '8XXX'
            cleanup_list_of_commands( self, _next_cmd_from_wait_cmdresponse_queue( self )[0] )

    ready_to_send_if_needed( self )
    self.F_out(frame, None)  # Forward the message to plugin for further processing
    self.check_timed_out_for_tx_queues()  # Let's take the opportunity to check TimeOut

def process_msg_type8000(self, Status, PacketType, sqn_app, sqn_aps, Ack_expected):

    if PacketType == '':
        return None

    self.loggingSend( 'Debug', "--> process_msg_type8000 - Status: %s PacketType: %s sqn_app:%s sqn_aps: %s Ack_expected: %s" %(Status, PacketType,sqn_app, sqn_aps, Ack_expected))
    # Command Failed, Status != 00

    if Status != '00':
        self.statistics._ackKO += 1
        if self.zmode in ( 'zigbee31c','zigbee31d'):
            # In that case we need to unblock data, as we will never get it !
            if len(self._waitForCmdResponseQueue) > 0:
                InternalSqn, TimeStamp = _next_cmd_from_wait_cmdresponse_queue( self )
                self.loggingSend( 'Debug', " --  --  -- - > - unlock waitForData due to command %s failed, remove %s" %(PacketType, InternalSqn))
                if InternalSqn in self.ListOfCommands:
                    if self.ListOfCommands[ InternalSqn ]['MessageResponse']:
                        self.logging_receive( 'Debug', " - -- Unqueue CmdResponse : [%s] %s %s " 
                        %(InternalSqn, self.ListOfCommands[ InternalSqn ]['Cmd'], self.ListOfCommands[ InternalSqn ]['Datas']))

        elif self.zmode == 'zigbeeack':
            # In that case we need to unblock ack_nack, as we will never get it !
            if len(self._waitForAckNack) > 0:
                InternalSqn, TimeStamp = _next_cmd_to_wait_for_ack_nack_queue( self )
                self.loggingSend( 'Debug', " --  --  -- - > - unlock waitForAckNack due to command %s failed, remove %s" %(PacketType, InternalSqn))
                if InternalSqn in self.ListOfCommands:
                    if self.ListOfCommands[ InternalSqn ]['MessageResponse']:
                        self.logging_receive( 'Debug', " - -- Unqueue CmdResponse : [%s] %s %s " 
                        %(InternalSqn, self.ListOfCommands[ InternalSqn ]['Cmd'], self.ListOfCommands[ InternalSqn ]['Datas']))

        # Finaly freeup the 0x8000 queue
        NextCmdFromWaitFor8000 = _next_cmd_from_wait_for8000_queue( self )
        return None

    # Status is '00' -> Valid command sent !
    self.statistics._ack += 1
    NextCmdFromWaitFor8000 = _next_cmd_from_wait_for8000_queue( self )
    if NextCmdFromWaitFor8000 is None:
        self.loggingSend( 'Debug', " --  --  -- - > - Empty Queue")
        return None

    InternalSqn, TimeStamp = NextCmdFromWaitFor8000
    self.loggingSend( 'Debug', " --  --  -- - > InternSqn: %s ExternalSqn: %s ExternalSqnZCL: %s" %(InternalSqn, sqn_app, sqn_aps))
    if InternalSqn not in self.ListOfCommands:
        return None

    if self.ListOfCommands[ InternalSqn ]['Cmd']:
        IsCommandOk = int(self.ListOfCommands[ InternalSqn ]['Cmd'], 16) == int(PacketType, 16)
        if not IsCommandOk:
            self.loggingSend( 'Error', "process_msg_type8000 - sync error : Expecting %s and Received: %s" \
                    % (self.ListOfCommands[ InternalSqn ]['Cmd'], PacketType))
            return None
    
    if (not self.firmware_with_aps_sqn and self.ListOfCommands[ InternalSqn ]['ExpectedAck']) or (self.firmware_with_aps_sqn and Ack_expected ):
        sqn_add_external_sqn (self, InternalSqn, sqn_app, sqn_aps)

    return InternalSqn

def process_msg_type8011_above31d( self, Status, NwkId, Ep, MsgClusterId, ExternSqn ):

    # Get i_sqn from sqnManagement
    InternSqn = sqn_get_internal_sqn (self, ExternSqn, E_SQN_APS)

    # Let's check that InternalSqn is in the Queue
    item = None
    for x in self._waitForAckNack:
        if x[0] == InternSqn:
            # Item found
            item = x
            break
    
    if item is None:
        # We receive an un expected Ack
        return None

    if Status == '00':
        if InternSqn in self.ListOfCommands:
            self.loggingSend( 'Debug', " - [%s] receive Ack for Cmd: %s - size of SendQueue: %s" %( InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSAck += 1
    else:
        if InternSqn in self.ListOfCommands:
            self.loggingSend( 'Debug', " - [%s] receive Nack for Cmd: %s - size of SendQueue: %s" %( InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSNck += 1 

    self._waitForAckNack.remove( item ) 
   
    return InternSqn

def process_msg_type8011_below31c( self, Status, NwkId, Ep, MsgClusterId, ExternSqn ):

    self.loggingSend( 'Debug',"--> process_msg_type8011_below31c - Status: %s ExternalSqn: %s NwkId: %s Ep: %s ClusterId: %s" %(Status, ExternSqn, NwkId, Ep , MsgClusterId ))
    # Unqueue the Command in order to free for the next
    InternSqn, TimeStamps = _next_cmd_to_wait_for_ack_nack_queue( self ) 

    if (self.firmware_with_aps_sqn):
        InternSqn_from_ExternSqn = sqn_get_internal_sqn (self, ExternSqn, E_SQN_APS)
        if InternSqn != InternSqn_from_ExternSqn:
            Domoticz.Error ("process_msg_type8011_below31c different sqn : InternSqn:%s InternSQN_from_ExternalSQN:%s" %(InternSqn, InternSqn_from_ExternSqn))

    if Status == '00':
        if InternSqn in self.ListOfCommands:
            self.loggingSend( 'Debug', " - [%s] receive Ack for Cmd: %s - size of SendQueue: %s" %( InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSAck += 1
    else:
        if InternSqn in self.ListOfCommands:
            self.loggingSend( 'Debug', " - [%s] receive Nack for Cmd: %s - size of SendQueue: %s" %( InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSNck += 1 
    return InternSqn

def process_msg_type8702( self, MsgData):
    # Status: d4 - Unicast frame does not have a route available but it is buffered for automatic resend
    # Status: e9 - No acknowledgement received when expected
    # Status: f0 - Pending transaction has expired and data discarded
    # Status: cf - Attempt at route discovery has failed due to lack of table space

    # Note: If a message is unicast to a destination for which a route has not already been established, 
    # the message will not be sent and a route discovery will be performed instead. If this is the case, 
    # the unicast function will return ZPS_NWK_ENUM_ROUTE_ERROR. The application must then wait for the
    # stack event ZPS_EVENT_NWK_ROUTE_DISCOVERY_CONFIRM (success or failure) before attempting to re-send
    # the message by calling the same unicast function again.

    self.loggingSend( 'Debug',"--> process_msg_type8702")
    if len(MsgData) == 0 or len(MsgData) < 8:
        Domoticz.Error("process_msg_type8702 - Empty frame: %s" %MsgData)
        return  True

    MsgDataStatus = MsgData[0:2]
    #MsgDataSrcEp = MsgData[2:4]
    MsgDataDestEp = MsgData[4:6]
    MsgDataDestMode = MsgData[6:8]

    NWKID = IEEE = None
    if MsgDataDestMode == '01': # IEEE
        IEEE = MsgData[8:24]
        ExternSqn = MsgData[24:26]
    elif MsgDataDestMode == '02': # Short Address
        NwkId = MsgData[8:12]
        ExternSqn = MsgData[12:14]
    elif MsgDataDestMode == '03': # Group
        MsgDataDestAddr = MsgData[8:12]
        ExternSqn = MsgData[12:14]

    self.loggingSend( 'Debug',"process_msg_type8702 - ExternalSqn: %s NwkId: %s Ep: %s" %(ExternSqn, NwkId, MsgDataDestEp  ))

    InternSqn = sqn_get_internal_sqn (self, ExternSqn)
    self.loggingSend( 'Debug', "----------->  ExternalSqn: %s InternalSqn: %s" %(ExternSqn,InternSqn))

    return InternSqn

def process_other_type_of_message(self, MsgType, MsgSqn = None):
    
    self.statistics._data += 1
    # There is a probability that we get an ASYNC message, which is not related to a Command request.
    # In that case we should just process this message.
    
    # For now we assume that we do only one command at a time, so either it is an Async message, 
    # or it is related to the command
    self.logging_receive(  'Debug', "--> process_other_type_of_message - MsgType: %s" %(MsgType))

    if len(self._waitForCmdResponseQueue) == 0:
        self.logging_receive(  'Debug', " --  -- - > - WaitForDataQueue empty")
        return

    InternalSqn, TimeStamp = self._waitForCmdResponseQueue[0]
    
    if InternalSqn not in self.ListOfCommands:
        Domoticz.Error("process_other_type_of_message - MsgType: %s, InternalSqn: %s not found in ListOfCommands: %s" 
            %( MsgType, InternalSqn, str(self.ListOfCommands.keys())))
        ready_to_send_if_needed( self )
        return None

    expResponse = self.ListOfCommands[ InternalSqn ]['MessageResponse']
    self.loggingSend( 'Debug', " --  -- - > Expecting: %04x Receiving: %s" %(expResponse,MsgType ))
    if expResponse == 0x8100:
        # With 3.1c firmware 0x0100 responses are coming on 0x8102
        self.logging_receive(  'Debug', " --  -- - > - expecting 0x8100 and received: %s with ExtSqn: %s" %(MsgType, MsgSqn))
        if MsgSqn is None:
            Domoticz.Error("process_other_type_of_message - MsgType: %s cannot get i_sqn due to unknown External SQN" %(MsgType))
            return None

        isqn = sqn_get_internal_sqn(self, MsgSqn, E_SQN_APP)
        self.loggingSend( 'Debug', " --  -- - > Expected IntSqn: %s Received ISqn: %s ESqn: %s" %(InternalSqn, isqn, MsgSqn))
        if InternalSqn != isqn:
            # Async message no worry
            return None
 
        ready_to_send_if_needed( self )
        return InternalSqn
    else:
        self.loggingSend( 'Debug', " --  -- - > Internal SQN: %s Received: %s and expecting %04x" %(InternalSqn, MsgType, expResponse  ))
        if int(MsgType, 16) != expResponse:
            self.logging_receive(  'Debug', "         - Async incoming PacketType")
            ready_to_send_if_needed( self )
            return None

    # If we have Still commands in the queue and the WaitforStatus+Data are free
    ready_to_send_if_needed( self )
    return InternalSqn

# Logging functions
def _write_message( self, message):
    message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
    self.loggingFileHandle.write( message )
    self.loggingFileHandle.flush()

def _logging_status( self, message):
    Domoticz.Status( message )
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _write_message( self, message)

def _logging_log( self, message):
    Domoticz.Log( message )
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _write_message( self, message)

def _logging_debug( self, message):
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _write_message( self, message)
    else:
        Domoticz.Log( message )

def _logging_error( self, message):
    if ( not self.pluginconf.pluginConf['useDomoticzLog'] and self.loggingFileHandle ):
        _write_message( self, message)
    else:
        Domoticz.Error( message )

def zigate_encode(Data):
    #The encoding is the following:
    # Let B any byte value of the message. If B is between 0x00 and 0x0f (included) then :
    #    Instead of B, a 2-byte content will be written in the encoded frame
    #    The first byte is a fixed value: 0x02
    #    The second byte is the result of B ^ 0x10

    Out = ''
    Outtmp = ''
    for c in Data:
        Outtmp += c
        if len(Outtmp) == 2:
            if Outtmp[0] == '1' and Outtmp != '10':
                if Outtmp[1] == '0':
                    Outtmp = '0200'
                Out += Outtmp
            elif Outtmp[0] == '0':
                Out += '021' + Outtmp[1]
            else:
                Out += Outtmp
            Outtmp = ""
    return Out

def get_checksum(msgtype, length, datas):
    temp = 0 ^ int(msgtype[0:2], 16)
    temp ^= int(msgtype[2:4], 16)
    temp ^= int(length[0:2], 16)
    temp ^= int(length[2:4], 16)
    for i in range(0, len(datas), 2):
        temp ^= int(datas[i:i + 2], 16)
        chk = hex(temp)
    return chk[2:4]