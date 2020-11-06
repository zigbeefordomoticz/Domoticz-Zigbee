# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import binascii
import struct

import time

from datetime import datetime

from Classes.LoggingManagement import LoggingManagement

from Modules.tools import is_hex, retreive_cmd_payload_from_8002, is_manufspecific_8002_payload
from Modules.zigateConsts import ZIGATE_RESPONSES, ZIGATE_COMMANDS, ADDRESS_MODE, SIZE_DATA_TYPE
from Modules.sqnMgmt import sqn_init_stack, sqn_generate_new_internal_sqn, sqn_add_external_sqn, sqn_get_internal_sqn_from_aps_sqn, sqn_get_internal_sqn_from_app_sqn, TYPE_APP_ZCL, TYPE_APP_ZDP

import serial
import select
import socket

from threading import Thread, Lock, Event
import queue
from binascii import unhexlify, hexlify

STANDALONE_MESSAGE = []
PDM_COMMANDS = ('8300', '8200', '8201', '8204', '8205', '8206', '8207', '8208')
CMD_PDM_ON_HOST = []
CMD_ONLY_STATUS = []
CMD_WITH_ACK = []
CMD_NWK_2NDBytes = {}
CMD_WITH_RESPONSE = {}
RESPONSE_SQN = []

THREAD_RELAX_TIME_MS = 20 / 1000    # 20ms of waiting time if nothing to do


class ZigateTransport(object):
    # """
    # Class in charge of Transport mecanishm to and from Zigate
    # Managed also the Command - > Status - > Data sequence
    # """

    def __init__(self, transport, statistics, pluginconf, F_out, log, serialPort=None, wifiAddress=None, wifiPort=None):

        # Logging
        self.log = log

        # Statistics
        self.statistics = statistics
        self.pluginconf = pluginconf

        # PDM attributes
        self.lock = False   # PDM Lock
        self.PDMCommandOnly = False # This flag indicate if any command can be sent to Zigate or only PDM related one

        # Queue Management attributes 
        self.ListOfCommands = {}           # List of ( Command, Data ) to be or in process
        self.zigateSendQueue = []          # list of normal priority commands
        self._waitFor8000Queue = []        # list of command sent and waiting for status 0x8000
        self._waitForCmdResponseQueue = [] # list of command sent for which status received and waiting for data
        self._waitForAckNack = []          # Contains list of Command waiting for Ack/Nack


        # ZigBee31c (for  firmware below 31c, when Ack --> WaitForResponse )
        # ZigBeeack ( for firmware above 31d, When Ack --> WaitForAck )

        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None
        self.zmode = pluginconf.pluginConf['Zmode'].lower()
        self.loggingSend('Status', "==> Transport Mode: %s" % self.zmode)
        self.firmware_with_aps_sqn = False

        # Initialise SQN Management
        sqn_init_stack(self)

        # Communication/Transport link attributes
        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port

        # Thread management
        self.running = True
        self.WatchDogThread = None
        self.ListeningThreadevent = None
        self.ListeningThread = None
        self.ListeningMutex = None
        self.messageQueue = queue.Queue()
        self.processFrameThread = []

        # Call back function to send back to plugin
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin

        initMatrix(self)

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
            Domoticz.Error("Unknown Transport Mode: %s" % transport)

    # Thread handling Serial Input/Output
    # Priority on Reading

    def update_ZiGate_Version ( self, FirmwareVersion, FirmwareMajorVersion):
        self.FirmwareVersion = FirmwareVersion
        self.FirmwareMajorVersion = FirmwareMajorVersion

    def start_thread_watchdog( self ):
        if self.WatchDogThread is None:
            Domoticz.Status("Starting Watch dog")
            self.WatchDogThread = Thread( name="ZiGateWatchDog",  target=ZigateTransport.threads_watchdog,  args=(self,))
            self.WatchDogThread.start()

    def threads_watchdog(self):
        def check_thread_alive( thr ):
            thr.join( timeout = 0.0 )
            return thr.is_alive()

        while self.running:
            #Domoticz.Log("Checking if %s alive" %self.ListeningThread.name)
            if self.running and not check_thread_alive( self.ListeningThread):
                Domoticz.Error("Thread %s seems to be dead, restarting" %self.ListeningThread.name)
                self.ListeningThread.start()
            time.sleep ( 60.0) 


    def lock_mutex(self):
        if self.ListeningMutex:
            self.ListeningMutex.acquire()

    def unlock_mutex(self):
        if self.ListeningMutex:
            self.ListeningMutex.release()


    def serial_listen_and_send( self ):

        while self._connection is None:
            #Domoticz.Log("Waiting for serial connection open")
            self.ListeningThreadevent.wait(1.0)
        
        serialConnection = self._connection
        Domoticz.Status("ZigateTransport: Serial Connection open: %s" %serialConnection)

        while self.running:
            nb = serialConnection.in_waiting
            if nb > 0:
                # Readinng messages
                while nb:
                    try:
                        data = serialConnection.read( nb )
                    except serial.SerialException as e:
                        #There is no new data from serial port
                        Domoticz.Error("serial_listen_and_send - error while reading %s" %(e))
                        data = None
                    if data:
                        self.on_message(data)
                    nb = serialConnection.in_waiting

            elif self.messageQueue.qsize() > 0:
                # Sending messages
                while self.messageQueue.qsize() > 0:
                    encoded_data = self.messageQueue.get_nowait()
                    try:
                        serialConnection.write( encoded_data )
                    except TypeError as e:
                        #Disconnect of USB->UART occured
                        Domoticz.Error("serial_listen_and_send - error while writing %s" %(e))

            else:
                if self.lock:
                    # If PDM lock is set, we are currently feeding PDM and we have to be more agressive
                    self.ListeningThreadevent.wait( 0.001 ) # 1ms waiting
                else:
                    self.ListeningThreadevent.wait( THREAD_RELAX_TIME_MS )
        Domoticz.Status("ZigateTransport: ZiGateSerialListen Thread stop.")


    def tcpip_listen_and_send( self ):

        while self._connection  is None:
            Domoticz.Log("Waiting for tcpip connection open")
            self.ListeningThreadevent.wait(1.0)

        Domoticz.Status("ZigateTransport: TcpIp Connection open: %s" %self._connection)
        tcpipConnection = self._connection
        tcpiConnectionList = [ tcpipConnection ]

        inputSocket  = outputSocket = [ tcpipConnection ]
        while self.running:
            readable, writable, exceptional = select.select(inputSocket, outputSocket, inputSocket)
            if readable:
                # We have something to read
                data = tcpipConnection.recv(1024)
                if data: 
                    self.on_message(data)
            elif writable and self.messageQueue.qsize() > 0:
                while self.messageQueue.qsize() > 0:
                    encoded_data = self.messageQueue.get_nowait()
                    try:
                        tcpipConnection.send( encoded_data )
                    except socket.OSError as e:
                        Domoticz.Error("Socket %s error %s" %(tcpipConnection, e))

            elif exceptional:
                Domoticz.Error("We have detected an error .... on %s" %inputSocket)
                self.ListeningThreadevent.wait( THREAD_RELAX_TIME_MS )
            else:
                self.ListeningThreadevent.wait( THREAD_RELAX_TIME_MS )



        Domoticz.Status("ZigateTransport: ZiGateTcpIpListen Thread stop.")


    def loggingSend(self, logType, message):
        # Log all activties towards ZiGate
        self.log.logging('TransportTx', logType, message)


    def logging_receive(self, logType, message):
        # Log all activities received from ZiGate
        self.log.logging('TransportRx', logType, message)


    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return len(self.zigateSendQueue)


    # Transport / Opening / Closing Communication
    def set_connection(self):
        def open_serial( self ):
            try:
                self._connection = serial.Serial(self._serialPort, baudrate = BAUDS, timeout = 0)

            except serial.SerialException as e:
                Domoticz.Error("Cannot open Zigate port %s error: %s" %(self._serialPort, e))
                return
            Domoticz.Status("Starting Listening and Sending Thread")
            if self.ListeningMutex is None:
                self.ListeningMutex= Lock()
            if self.ListeningThreadevent is None:
                self.ListeningThreadevent = Event()
            if self.ListeningThread is None:
                self.ListeningThread = Thread(
                                            name="ZiGate serial line listner", 
                                            target=ZigateTransport.serial_listen_and_send, 
                                            args=(self,))

                self.ListeningThread.start()
            self.start_thread_watchdog( )

        def open_tcpip( self ):
            try:
                self._connection = socket.create_connection( (self._wifiAddress, self._wifiPort) )
                self._connection.setblocking(0)

            except socket.Exception as e:
                Domoticz.Error("Cannot open Zigate Wifi %s Port %s error: %s" %(self._wifiAddress, self._serialPort, e))
                return
            if self.ListeningMutex is None:
                self.ListeningMutex= Lock()
            if self.ListeningThreadevent is None:
                self.ListeningThreadevent = Event()
            if self.ListeningThread is None:
                self.ListeningThread = Thread(
                                            name="ZiGate tcpip listner", 
                                            target=ZigateTransport.tcpip_listen_and_send, 
                                            args=(self,))
                self.ListeningThread.start()
            self.start_thread_watchdog( )

        # Begining
        if self._connection is not None:
            del self._connection
            self._connection = None

        if self._transp in ["USB", "DIN", "PI"]:
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" % (self._serialPort))
                #BAUDS = 460800
                BAUDS = 115200
                if self.pluginconf.pluginConf['MultiThreaded']:
                    open_serial( self)
                else:
                    self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None",
                                                       Address=self._serialPort, Baud=BAUDS)

        elif self._transp == "Wifi":
            Domoticz.Status("Connection Name: Zigate, Transport: TCP/IP, Address: %s:%s" %
                            (self._serialPort, self._wifiPort))
            if self.pluginconf.pluginConf['MultiThreaded']:
                open_tcpip( self )
            else:
                self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ",
                                                   Address=self._wifiAddress, Port=self._wifiPort)

        else:
            Domoticz.Error("Unknown Transport Mode: %s" % self._transp)


    def open_conn(self):
        if not self._connection:
            self.set_connection()

        if not self.pluginconf.pluginConf['MultiThreaded'] and self._connection:
            self._connection.Connect()

        Domoticz.Status("Connection open: %s" % self._connection)


    def close_conn(self):
        Domoticz.Status("Connection close: %s" % self._connection)
        self.running = False # It will shutdown the Thread 
        if self.pluginconf.pluginConf['MultiThreaded']:
            if self._connection:
                self._connection.close()
        else:
            self._connection.Disconnect()

        self._connection = None


    def re_conn(self):
        Domoticz.Status("Reconnection: %s" % self._connection)
        if self.pluginconf.pluginConf['MultiThreaded']:
            if self._connection:
                self._connection.close()
                time.sleep(1.0)
        else:
            if self._connection.Connected():
                self.close_conn()

        self.open_conn()


    # PDMonhost related
    def pdm_lock(self, lock):
        # Take a Lock to protect all communications from/to ZiGate (PDM on Host)
        self.PDMCommandOnly = lock


    def pdm_lock_status(self):
        return self.PDMCommandOnly


    def sendData(self, cmd, datas, ackIsDisabled=False, waitForResponseIn=False):

        waitForResponse = False
        if waitForResponseIn  or self.pluginconf.pluginConf['waitForResponse']:
            waitForResponse = True
        self.loggingSend('Debug2',"   -> waitForResponse: %s waitForResponseIn: %s" %(waitForResponse, waitForResponseIn))

        # If ackIsDisabled is True, it means that usally a Ack is expected ( ZIGATE_COMMANDS), but here it has been disabled via Address Mode
        self.loggingSend('Debug2', "sendData - %s %s ackDisabled: %s FIFO: %s" %
                         (cmd, datas, ackIsDisabled, len(self.zigateSendQueue)))
        if datas is None:
            datas = ''

        if datas != '' and not is_hex(datas):
            Domoticz.Error(
                "sendData_internal - receiving a non hexa Data: > %s < " % datas)
            return None

        # Check if the Cmd/Data is not yet in the pipe
        alreadyInQueue = False
        for x in list(self.ListOfCommands.keys()):
            if x not in self.ListOfCommands:
                continue
            if 'Status' not in self.ListOfCommands[x] or 'Cmd' not in self.ListOfCommands[x] or 'Datas' not in self.ListOfCommands[x]:
                continue
            if self.ListOfCommands[x]['Status'] in ( '', 'TO-SEND', 'QUEUED' ) and self.ListOfCommands[x]['Cmd'] == cmd and self.ListOfCommands[x]['Datas'] == datas:
                self.loggingSend(
                    'Log', "Cmd: %s Data: %s already in queue." % (cmd, datas))
                alreadyInQueue = True
                break
        if alreadyInQueue:
            for x in list(self.ListOfCommands.keys()):
                if x not in self.ListOfCommands:
                    continue
                self.loggingSend('Debug', "-- > Sending Queue: [%s] Cmd: %s Datas: %s Time: %s"
                                % (x, self.ListOfCommands[x]['Cmd'], self.ListOfCommands[x]['Datas'],
                                    self.ListOfCommands[x]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")))
            #return None

        # Let's move on, create an internal Sqn for tracking
        InternalSqn = sqn_generate_new_internal_sqn(self)
        if InternalSqn in self.ListOfCommands:
            # Unexpected !
            Domoticz.Error("sendData - Existing Internal SQN: %s for %s versus new %s/%s" %
                           (InternalSqn, str(self.ListOfCommands[InternalSqn]), cmd, datas))
            return None

        self.ListOfCommands[InternalSqn] = {}
        self.ListOfCommands[InternalSqn]['Cmd'] = cmd
        self.ListOfCommands[InternalSqn]['Datas'] = datas
        self.ListOfCommands[InternalSqn]['ReTransmit'] = 0
        self.ListOfCommands[InternalSqn]['Status'] = ''
        self.ListOfCommands[InternalSqn]['ReceiveTimeStamp'] = datetime.now()
        self.ListOfCommands[InternalSqn]['SentTimeStamp'] = None
        self.ListOfCommands[InternalSqn]['PDMCommand'] = False

        self.ListOfCommands[InternalSqn]['ResponseExpected'] = False
        self.ListOfCommands[InternalSqn]['ExpectedAck'] = False
        self.ListOfCommands[InternalSqn]['WaitForResponse'] = False
        self.ListOfCommands[InternalSqn]['MessageResponse'] = None

        self.ListOfCommands[InternalSqn]['APP_SQN'] = None
        self.ListOfCommands[InternalSqn]['APS_SQN'] = None
        self.ListOfCommands[InternalSqn]['TYP_SQN'] = None

        hexCmd = int(cmd, 16)
        if hexCmd in CMD_PDM_ON_HOST:
            self.ListOfCommands[InternalSqn]['PDMCommand'] = True

        if not ackIsDisabled and hexCmd in CMD_WITH_ACK:
            self.ListOfCommands[InternalSqn]['ExpectedAck'] = True

        if (not ackIsDisabled or waitForResponse) and hexCmd in CMD_WITH_RESPONSE and hexCmd in RESPONSE_SQN:
            self.ListOfCommands[InternalSqn]['MessageResponse'] = CMD_WITH_RESPONSE[hexCmd]
            self.ListOfCommands[InternalSqn]['ResponseExpected'] = True

        #if waitForResponseIn:
        #    self.ListOfCommands[InternalSqn]['WaitForResponse'] = True


        if not self.firmware_with_aps_sqn:
            # We are on firmware <= 31c
            # 0110 and 0113 are always set with Ack. Overwriten by the firmware
            if hexCmd in (0x0110, 0x0113):
                self.loggingSend(
                    'Debug', "-- > Patching %s to Ack due to firmware 31c" % hexCmd)
                self.ListOfCommands[InternalSqn]['MessageResponse'] = CMD_WITH_RESPONSE[hexCmd]
                self.ListOfCommands[InternalSqn]['ResponseExpected'] = True
                self.ListOfCommands[InternalSqn]['ExpectedAck'] = True
                self.ListOfCommands[InternalSqn]['WaitForResponse'] = True

        if hexCmd == 0x0530 and self.FirmwareVersion and int(self.FirmwareVersion,16) <= 0x031d:
            # Starting 0x031e Firmware, the RAW APS command can use address mode to request ACK/NO-ACK
            # below this firmware it is always NO-ACK
            self.ListOfCommands[InternalSqn]['ExpectedAck'] = False

        printListOfCommands(self, 'from sendData', InternalSqn)

        send_data_internal(self, InternalSqn)
        return InternalSqn


    def on_message(self, Data):
        # Process/Decode Data

        #self.logging_receive( 'Log', "onMessage - %s" %(Data))
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
                Domoticz.Error(
                    "onMessage : we have probably lost some datas, zero1 = " + str(Zero1))

            # uncode the frame
            # DEBUG ###_uncoded = str(self._ReqRcv[Zero1:Zero3]) + ''
            BinMsg = bytearray()
            iterReqRcv = iter(self._ReqRcv[Zero1:Zero3])

            for iByte in iterReqRcv:  # for each received byte
                if iByte == 0x02:  # Coded flag ?
                    # then uncode the next value
                    iByte = next(iterReqRcv) ^ 0x10
                BinMsg.append(iByte)  # copy

            if len(BinMsg) <= 6:
                Domoticz.Error(
                    "onMessage error - processing an uncomplet message: %s" % BinMsg)
                return

            # What is after 0x03 has to be reworked.
            self._ReqRcv = self._ReqRcv[Zero3:]

            # Check length
            Zero1, MsgType, Length, ReceivedChecksum = struct.unpack(
                '>BHHB', BinMsg[0:6])
            ComputedLength = Length + 7
            ReceveidLength = len(BinMsg)
            if ComputedLength != ReceveidLength:
                FrameIsKo = 1
                self.statistics._frameErrors += 1
                Domoticz.Error("onMessage : Frame size is bad, computed = " +
                               str(ComputedLength) + " received = " + str(ReceveidLength))

            # Compute checksum
            ComputedChecksum = 0
            for idx, val in enumerate(BinMsg[1:-1]):
                if idx != 4:  # Jump the checksum itself
                    ComputedChecksum ^= val
            if ComputedChecksum != ReceivedChecksum:
                FrameIsKo = 1
                self.statistics._crcErrors += 1
                Domoticz.Error("onMessage : Frame CRC is bad, computed = " + str(ComputedChecksum) +
                               " received = " + str(ReceivedChecksum))

            if FrameIsKo == 0:
                AsciiMsg = binascii.hexlify(BinMsg).decode('utf-8')
                self.statistics._received += 1

                if self.pluginconf.pluginConf['ZiGateReactTime']:
                    start_time = time.time()

                process_frame(self, AsciiMsg)
                
                if self.pluginconf.pluginConf['ZiGateReactTime']:
                    timing = int( (time.time() - start_time )* 1000 )
                    self.statistics.add_rxTiming( timing )


    def check_timed_out_for_tx_queues(self):
        check_timed_out(self)

# Local Functions


def initMatrix(self):
    for x in ZIGATE_RESPONSES:
        STANDALONE_MESSAGE.append(x)

    for x in ZIGATE_COMMANDS:
        self.loggingSend('Debug2', "Command: %04x Ack: %s Sequence: %s/%s"
                         % (x, ZIGATE_COMMANDS[x]['Ack'], len(ZIGATE_COMMANDS[x]['Sequence']), ZIGATE_COMMANDS[x]['Sequence']))

        if ZIGATE_COMMANDS[x]['NwkId 2nd Bytes']:
            self.loggingSend('Debug2', "--> 2nd Byte for NwkId")
            CMD_NWK_2NDBytes[x] = x

        if ZIGATE_COMMANDS[x]['Ack']:
            self.loggingSend('Debug2', "--> Ack")
            CMD_WITH_ACK.append(x)

        if ZIGATE_COMMANDS[x]['SQN']:
            RESPONSE_SQN.append(x)

        if len(ZIGATE_COMMANDS[x]['Sequence']) == 0:
            self.loggingSend('Debug2', "--> PDM")
            CMD_PDM_ON_HOST.append(x)

        elif len(ZIGATE_COMMANDS[x]['Sequence']) == 1:
            self.loggingSend('Debug2', "--> Command Only")
            CMD_ONLY_STATUS.append(x)

        elif len(ZIGATE_COMMANDS[x]['Sequence']) == 2:
            self.loggingSend('Debug2', "--> Response Expected for %04x -> %s" %
                             (x, ZIGATE_COMMANDS[x]['Sequence'][1]))
            CMD_WITH_RESPONSE[x] = ZIGATE_COMMANDS[x]['Sequence'][1]

    #self.loggingSend( 'Debug', "STANDALONE_MESSAGE: %s" %STANDALONE_MESSAGE)
    #self.loggingSend( 'Debug', "CMD_ONLY_STATUS: %s" %CMD_ONLY_STATUS)
    #self.loggingSend( 'Debug', "ZIGATE_COMMANDS: %s" %ZIGATE_COMMANDS)
    #self.loggingSend( 'Debug', "CMD_NWK_2NDBytes: %s" %CMD_NWK_2NDBytes)
    #self.loggingSend( 'Debug', "CMD_WITH_RESPONSE: %s" %CMD_WITH_RESPONSE)
    #self.loggingSend( 'Debug', "CMD_WITH_ACK: %s" %CMD_WITH_ACK)

# Queues Managements


def _add_cmd_to_send_queue(self, InternalSqn):
    # add a command to the waiting list
    timestamp = int(time.time())
    # Check if the Cmd+Data is not yet in the Queue. If yes forget that message
    #self.loggingSend(  'Debug2', " --  > _add_cmd_to_send_queue - adding to Queue %s %s" %(InternalSqn, timestamp ))
    self.zigateSendQueue.append((InternalSqn, timestamp))
    # Manage Statistics
    if len(self.zigateSendQueue) > self.statistics._MaxLoad:
        self.statistics._MaxLoad = len(self.zigateSendQueue)
    self.statistics._Load = len(self.zigateSendQueue)


def _next_cmd_from_send_queue(self):

    # return the next Command to send (pop)
    ret = (None, None)
    if len(self.zigateSendQueue) > 0:
        ret = self.zigateSendQueue[0]
        del self.zigateSendQueue[0]
    #self.loggingSend(  'Debug2', " --  > _nextCmdFromSendQueue - Unqueue %s " %( str(ret) ))
    return ret


def _add_cmd_to_wait_for8000_queue(self, InternalSqn):
    # add a command to the waiting list for 0x8000
    #timestamp = int(time.time())
    timestamp = time.time()
    #self.loggingSend(  'Log', " --  > _add_cmd_to_wait_for8000_queue - adding to Queue %s %s" %(InternalSqn, timestamp))
    self._waitFor8000Queue.append((InternalSqn, timestamp))


def _next_cmd_from_wait_for8000_queue(self):
    # return the entry waiting for a Status
    ret = (None, None)
    if len(self._waitFor8000Queue) > 0:
        ret = self._waitFor8000Queue[0]
        del self._waitFor8000Queue[0]
    #self.loggingSend(  'Debug2', " --  > _nextCmdFromWaitFor8000Queue - Unqueue %s " %( str(ret) ))
    return ret


def _add_cmd_to_wait_for_ack_nack_queue(self, InternalSqn):
    # add a command to the AckNack waiting list
    timestamp = int(time.time())
    #self.loggingSend(  'Log', " --  > _addCmdToWaitForAckNackQueue - adding to Queue  %s %s" %(InternalSqn, timestamp))
    self._waitForAckNack.append((InternalSqn, timestamp))


def _next_cmd_to_wait_for_ack_nack_queue(self):
    # return the entry waiting for Data
    ret = (None, None)
    if len(self._waitForAckNack) > 0:
        ret = self._waitForAckNack[0]
        del self._waitForAckNack[0]
    #self.loggingSend(  'Debug2', " --  > _next_cmd_to_wait_for_ack_nack_queue - Unqueue %s " %( str(ret) ))
    return ret


def _add_cmd_to_wait_for_cmdresponse_queue(self, InternalSqn):
    # add a command to the waiting list

    timestamp = int(time.time())
    #self.loggingSend(  'Log', " --  > _add_cmd_to_wait_for_cmdresponse_queue - adding to Queue %s %s" %(InternalSqn, timestamp))
    self._waitForCmdResponseQueue.append((InternalSqn, timestamp))


def _next_cmd_from_wait_cmdresponse_queue(self):
    # return the entry waiting for Data
    ret = (None, None)
    if len(self._waitForCmdResponseQueue) > 0:
        ret = self._waitForCmdResponseQueue[0]
        del self._waitForCmdResponseQueue[0]
    #self.loggingSend(  'Debug2', " --  > _next_cmd_from_wait_cmdresponse_queue - Unqueue %s " %( str(ret) ))
    return ret

# Sending functions


def send_data_internal(self, InternalSqn):
    #
    # in charge of sending Data. Call by sendZigateCmd
    # If nothing in the waiting queue, will call _send_data and it will be sent straight to Zigate

    if InternalSqn not in self.ListOfCommands:
        # Unexpected
        Domoticz.Error("send_data_internal - unexpected 1 %s not in ListOfCommands: %s" %
                       (InternalSqn, str(self.ListOfCommands.keys())))
        return
    self.loggingSend('Debug2', "--- send_data_internal - %s FIFO: %s" %
                     (InternalSqn, len(self.zigateSendQueue)))

    sendNow = True
    # PDM Management.
    # When PDM traffic is ongoing we cannot interupt, so we need to FIFO all other commands until the PDMLock is released
    if self.pdm_lock_status() and self.ListOfCommands[InternalSqn]['Cmd'] not in PDM_COMMANDS:
        # Only PDM related command can go , all others will be dropped.
        Domoticz.Log("PDM not yet ready, FIFO command %s %s" % (
            self.ListOfCommands[InternalSqn]['Cmd'], self.ListOfCommands[InternalSqn]['Datas']))
        sendNow = False

    if sendNow and self.zmode == 'zigate31c':
        # Wait on 0x8000 and CmdResponse
        if (not self.ListOfCommands[InternalSqn]['PDMCommand'] and (len(self._waitFor8000Queue) > 0 or len(self._waitForCmdResponseQueue) > 0)):
            sendNow = False

        self.loggingSend('Debug', "--- send_data_internal - Command: %s  Q(0x8000): %s Q(Response): %s sendNow: %s"
                         % (self.ListOfCommands[InternalSqn]['Cmd'], len(self._waitFor8000Queue), len(self._waitForCmdResponseQueue), sendNow))

    elif sendNow and self.zmode == 'zigateack':
        # Wait on 0x8000, AckNack and eventually on Response
        if (not self.ListOfCommands[InternalSqn]['PDMCommand'] and (len(self._waitFor8000Queue) > 0 or len(self._waitForAckNack) > 0 or len(self._waitForCmdResponseQueue) > 0)):
            sendNow = False

        self.loggingSend('Debug', "--- send_data_internal - Command: %s  Q(0x8000): %s Q(Ack/Nack): %s Q(Response): %s sendNow: %s"
                         % (self.ListOfCommands[InternalSqn]['Cmd'], len(self._waitFor8000Queue), len(self._waitForAckNack), len(self._waitForCmdResponseQueue), sendNow))

    # In case the cmd is part of the PDM on Host commands, that is High Priority and must go through.
    if not sendNow:
        # Put in FIFO
        self.loggingSend(
            'Debug2', "--- send_data_internal - put in waiting queue")
        self.ListOfCommands[InternalSqn]['Status'] = 'QUEUED'
        _add_cmd_to_send_queue(self, InternalSqn)
        return

    # Sending Command
    self.loggingSend('Debug', "--- send_data_internal - sending now zmode: %s Ack: %s ResponseExpected: %s" %
                     (self.zmode, self.ListOfCommands[InternalSqn]['ExpectedAck'], self.ListOfCommands[InternalSqn]['ResponseExpected']))

    if not self.ListOfCommands[InternalSqn]['PDMCommand']:
        # That is a Standard command (not PDM on  Host), let's process as usall
        self.ListOfCommands[InternalSqn]['Status'] = 'TO-SEND'

        # Add to 0x8000 queue
        _add_cmd_to_wait_for8000_queue(self, InternalSqn)

        if self.ListOfCommands[InternalSqn]['ExpectedAck'] and self.zmode == 'zigateack':
            set_acknack_for_sending(self, InternalSqn)

        if self.zmode in 'zigate31c' and self.ListOfCommands[InternalSqn]['ResponseExpected']:
            set_cmdresponse_for_sending(self, InternalSqn)

        if self.ListOfCommands[InternalSqn]['WaitForResponse'] and self.zmode == 'zigateack':
            set_cmdresponse_for_sending(self, InternalSqn)

    # Go!
    #printListOfCommands( self, 'after correction before sending', InternalSqn )
    _send_data(self, InternalSqn)


def printListOfCommands(self, comment, isqn):
    self.loggingSend('Debug', "=======  %s:" % comment)
    self.loggingSend('Debug', "  - Cmd:              %s" %
                     self.ListOfCommands[isqn]['Cmd'])
    self.loggingSend('Debug', "  - Datas:            %s" %
                     self.ListOfCommands[isqn]['Datas'])
    self.loggingSend('Debug', "  - ReTransmit:       %s" %
                     self.ListOfCommands[isqn]['ReTransmit'])
    self.loggingSend('Debug', "  - Status:           %s" %
                     self.ListOfCommands[isqn]['Status'])
    self.loggingSend('Debug', "  - ReceiveTimeStamp: %s" %
                     self.ListOfCommands[isqn]['ReceiveTimeStamp'])
    self.loggingSend('Debug', "  - SentTimeStamp:    %s" %
                     self.ListOfCommands[isqn]['SentTimeStamp'])
    self.loggingSend('Debug', "  - PDMCommand:       %s" %
                     self.ListOfCommands[isqn]['PDMCommand'])
    self.loggingSend('Debug', "  - ResponseExpected: %s" %
                     self.ListOfCommands[isqn]['ResponseExpected'])
    self.loggingSend('Debug', "  - MessageResponse:  %s" %
                     self.ListOfCommands[isqn]['MessageResponse'])
    self.loggingSend('Debug', "  - ExpectedAck:      %s" %
                     self.ListOfCommands[isqn]['ExpectedAck'])
    self.loggingSend('Debug', "  - WaitForResponse:  %s" %
                     self.ListOfCommands[isqn]['WaitForResponse'])


def set_cmdresponse_for_sending(self, i_sqn):

    if int(self.ListOfCommands[i_sqn]['Cmd'], 16) not in CMD_NWK_2NDBytes:
        if self.ListOfCommands[i_sqn]['Cmd'] == '004E' and self.ListOfCommands[i_sqn]['Datas'][0:4] == '0000':
            # Do not wait for LQI request to ZiGate
            self.loggingSend(
                'Debug', "--- LQI request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False

        elif self.ListOfCommands[i_sqn]['Cmd'] == '0049' and self.ListOfCommands[i_sqn]['Datas'][0:4] == 'FFFC':
            self.loggingSend(
                'Debug', "--- Permit To Join request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False
        else:
            self.loggingSend('Debug', "--- Add to Queue CommandResponse Queue")
            _add_cmd_to_wait_for_cmdresponse_queue(self, i_sqn)
    else:
        if self.ListOfCommands[i_sqn]['Datas'][0:2] == '%02x' % ADDRESS_MODE['group'] and self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            # Do not wait for Response to Groups commands sent to Zigate
            self.loggingSend(
                'Debug', "--- Group command to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False

        elif self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            # Do not wait for Response to commands sent to Zigate
            self.loggingSend(
                'Debug', "--- Cmmand to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False

        elif not self.firmware_with_aps_sqn and self.ListOfCommands[i_sqn]['Cmd'] == '0110':
            #  Compatibility mode with previous Transport version do not wait for Response on command 0x0100
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False
            self.loggingSend('Debug', "--- 31c do not block 0110 even if Ack expected %s" %
                             self.ListOfCommands[i_sqn]['Cmd'])

        else:
            self.loggingSend('Debug', "--- Add to Queue CommandResponse Queue")
            _add_cmd_to_wait_for_cmdresponse_queue(self, i_sqn)


def set_acknack_for_sending(self, i_sqn):

    # These are ZiGate commands which doesn't have Ack/Nack with firmware up to 3.1c
    CMD_NOACK_ZDP = (0x0030, 0x0031, 0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045,
                     0x0046, 0x0047, 0x0049, 0x004A, 0x004B, 0x004E, 0x0530, 0x0531, 0x0532, 0x0533)

    # If ZigBeeAck mode and Ack Expected
    if not self.firmware_with_aps_sqn and int(self.ListOfCommands[i_sqn]['Cmd'], 16) in CMD_NOACK_ZDP:
        # This only apply to firmware on 31c and below
        self.loggingSend(
            'Debug', "--- ZDP command no Ack/Nack with that firmware")
        self.ListOfCommands[i_sqn]['ExpectedAck'] = False

    elif int(self.ListOfCommands[i_sqn]['Cmd'], 16) not in CMD_NWK_2NDBytes:
        if self.ListOfCommands[i_sqn]['Cmd'] == '004E' and self.ListOfCommands[i_sqn]['Datas'][0:4] == '0000':
            # Do not wait for LQI request to ZiGate
            self.loggingSend(
                'Debug', "--- LQI request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False
        else:
            # Wait for Ack/Nack
            self.loggingSend('Debug', "--- Add to Queue Ack/Nack")
            _add_cmd_to_wait_for_ack_nack_queue(self, i_sqn)
    else:
        if self.ListOfCommands[i_sqn]['Datas'][0:2] == '%02x' % ADDRESS_MODE['group']:
            # Do not wait for Ack/Nack as the command to Groups
            self.loggingSend(
                'Debug', "--- Group command to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False

        elif self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            # Do not wait for Ack/Nack as the command is sent for ZiGate
            self.loggingSend(
                'Debug', "--- Cmmand to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['ExpectedAck'] = False

        else:
            # Wait for Ack/Nack if NwkId != '0000' and Address Mode (ZiGate)
            self.loggingSend('Debug', "--- Add to Queue Ack/Nack %s %s" %
                             (self.ListOfCommands[i_sqn]['Cmd'], self.ListOfCommands[i_sqn]['Datas']))
            _add_cmd_to_wait_for_ack_nack_queue(self, i_sqn)


def ready_to_send_if_needed(self):

    readyToSend = True
    if self.zmode == 'zigate31c':
        readyToSend = len(self._waitFor8000Queue) == 0 and len(self._waitForCmdResponseQueue) == 0
        #self.loggingSend('Debug2', "--- send_data_internal - Q(0x8000): %s Q(Ack/Nack): %s sendNow: %s"
        #    % (len(self.zigateSendQueue), len(self._waitFor8000Queue), len(self._waitFor8000Queue)))

    elif self.zmode == 'zigateack':
        readyToSend = len(self._waitFor8000Queue) == 0 and len(self._waitForAckNack) == 0 and len(self._waitForCmdResponseQueue) == 0
        #self.loggingSend('Debug2', "--- send_data_internal - Q(0x8000): %s Q(Ack/Nack): %s sendNow: %s"
        #    % (len(self.zigateSendQueue), len(self._waitFor8000Queue), len(self._waitFor8000Queue)))

    if readyToSend and len(self.zigateSendQueue) > 0:
        send_data_internal(self, _next_cmd_from_send_queue(self)[0])


def _send_data(self, InternalSqn):
    # send data to Zigate via the communication transport

    cmd = self.ListOfCommands[InternalSqn]['Cmd']
    datas = self.ListOfCommands[InternalSqn]['Datas']
    self.ListOfCommands[InternalSqn]['Status'] = 'SENT'
    self.ListOfCommands[InternalSqn]['SentTimeStamp'] = int(time.time())

    self.loggingSend('Debug', "======================== _send_data - [%s] %s %s ExpectAck: %s ExpectResponse: %s" % (
        InternalSqn, cmd, datas, self.ListOfCommands[InternalSqn]['ExpectedAck'], self.ListOfCommands[InternalSqn]['ResponseExpected']))

    if datas == "":
        length = "0000"
        checksumCmd = get_checksum(cmd, length, "0")
        strchecksum = '0' + \
            str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(zigate_encode(cmd)) + str(zigate_encode(length)) + \
                    str(zigate_encode(strchecksum)) + "03"
    else:
        #Domoticz.Log("---> datas: %s" %datas)
        length = '%04x' % (len(datas)//2)

        checksumCmd = get_checksum(cmd, length, datas)
        strchecksum = '0' + \
            str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(zigate_encode(cmd)) + str(zigate_encode(length)) + \
                    str(zigate_encode(strchecksum)) + \
            str(zigate_encode(datas)) + "03"

    # self.loggingSend(  'Debug', "---  --  > _send_data - sending encoded Cmd: %s length: %s CRC: %s Data: %s" \
    #            %(str(zigate_encode(cmd)), str(zigate_encode(length)), str(zigate_encode(strchecksum)), str(zigate_encode(datas))))
    #self._connection.Send(bytes.fromhex(str(lineinput)), 0)

    if self.pluginconf.pluginConf['MultiThreaded'] and self.messageQueue:
        self.messageQueue.put(bytes.fromhex(str(lineinput)))
    else:
        self._connection.Send(bytes.fromhex(str(lineinput)), 0)
    self.statistics._sent += 1


def check_timed_out(self):

    def timeout_8000(self):
        # Timed Out 0x8000
        self.statistics._TOstatus += 1
        entry = _next_cmd_from_wait_for8000_queue(self)
        if entry is None:
            return
        InternalSqn, TimeStamp = entry
        logExpectedCommand(self, '0x8000', now, TimeStamp, InternalSqn)
        if InternalSqn in self.ListOfCommands:
            if self.zmode == 'zigateack' and self.ListOfCommands[InternalSqn]['ExpectedAck']:
                _next_cmd_to_wait_for_ack_nack_queue(self)

            if self.zmode == 'zigateack' and self.ListOfCommands[InternalSqn]['WaitForResponse']:
                _next_cmd_from_wait_cmdresponse_queue(self)

            elif self.zmode == 'zigate31c' and self.ListOfCommands[InternalSqn]['ResponseExpected']:
                _next_cmd_from_wait_cmdresponse_queue(self)

        cleanup_list_of_commands(self, InternalSqn)

    def timeout_acknack(self):
        self.statistics._TOstatus += 1
        entry = _next_cmd_to_wait_for_ack_nack_queue(self)
        if entry is None:
            return
        InternalSqn, TimeStamp = entry
        logExpectedCommand(self, 'Ack', now, TimeStamp, InternalSqn)
        if self.zmode == 'zigateack' and self.ListOfCommands[InternalSqn]['WaitForResponse']:
            _next_cmd_from_wait_cmdresponse_queue(self)

        cleanup_list_of_commands(self, InternalSqn)

    def timeout_cmd_response(self):
        # No response ! We Timed Out
        self.statistics._TOdata += 1
        InternalSqn, TimeStamp = _next_cmd_from_wait_cmdresponse_queue(self)
        if InternalSqn not in self.ListOfCommands:
            return
        logExpectedCommand(self, 'CmdResponse', now, TimeStamp, InternalSqn)
        cleanup_list_of_commands(self, InternalSqn)

    def check_and_timeout_listofcommand(self):
        if len(self.ListOfCommands) == 0:
            return

        self.loggingSend(
            'Debug', "-- checkTimedOutForTxQueues ListOfCommands size: %s" % len(self.ListOfCommands))
        for x in list(self.ListOfCommands.keys()):
            if 'SentTimeStamp' in self.ListOfCommands[x] and self.ListOfCommands[x]['SentTimeStamp'] and (now - self.ListOfCommands[x]['SentTimeStamp']) > TIME_OUT_LISTCMD:
                if self.ListOfCommands[x]['MessageResponse']:
                    self.loggingSend('Debug', " --  --  --  > - Time Out : [%s] %s %s Flags: %s/%s %04x Status: %s Time: %s"
                                     % (x, self.ListOfCommands[x]['Cmd'], self.ListOfCommands[x]['Datas'], self.ListOfCommands[x]['ResponseExpected'],
                                        self.ListOfCommands[x]['ExpectedAck'], self.ListOfCommands[x]['MessageResponse'],
                                        self.ListOfCommands[x]['Status'],
                                        self.ListOfCommands[x]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")))
                else:
                    self.loggingSend('Debug', " --  --  --  > - Time Out : [%s] %s %s Flags: %s/%s Status: %s Time: %s "
                                     % (x, self.ListOfCommands[x]['Cmd'], self.ListOfCommands[x]['Datas'],
                                        self.ListOfCommands[x]['ResponseExpected'], self.ListOfCommands[x]['ExpectedAck'],
                                        self.ListOfCommands[x]['Status'],
                                        self.ListOfCommands[x]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")))

                del self.ListOfCommands[x]

    def logExpectedCommand(self, desc, now, TimeStamp, i_sqn):

        if not self.pluginconf.pluginConf['showTimeOutMsg']:
            return

        if i_sqn not in self.ListOfCommands:
            self.loggingSend(
                'Debug', " --  --  --  > - %s - Time Out %s  " % (desc, i_sqn))
            return

        if self.ListOfCommands[i_sqn]['MessageResponse']:
            self.loggingSend('Log', " --  --  --  > Time Out %s [%s] %s sec for  %s %s %s/%s %04x Time: %s"
                             % (desc, i_sqn, (now - TimeStamp), self.ListOfCommands[i_sqn]['Cmd'], self.ListOfCommands[i_sqn]['Datas'],
                                self.ListOfCommands[i_sqn]['ResponseExpected'], self.ListOfCommands[i_sqn]['ExpectedAck'],
                                self.ListOfCommands[i_sqn]['MessageResponse'], self.ListOfCommands[InternalSqn]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")))
        else:
            self.loggingSend('Log', " --  --  --  > Time Out %s [%s] %s sec for  %s %s %s/%s %s Time: %s"
                             % (desc, i_sqn, (now - TimeStamp), self.ListOfCommands[i_sqn]['Cmd'], self.ListOfCommands[i_sqn]['Datas'],
                                self.ListOfCommands[i_sqn]['ResponseExpected'], self.ListOfCommands[i_sqn]['ExpectedAck'],
                                self.ListOfCommands[i_sqn]['MessageResponse'], self.ListOfCommands[InternalSqn]['ReceiveTimeStamp'].strftime("%m/%d/%Y, %H:%M:%S")))
        self.loggingSend('Debug',"--  --  --  > i_sqn: %s App_Sqn: %s Aps_Sqn: %s Type_Sqn: %s" \
            %( i_sqn, self.ListOfCommands[i_sqn]['APP_SQN'], self.ListOfCommands[i_sqn]['APS_SQN'] , self.ListOfCommands[i_sqn]['TYP_SQN']  ))

    # Begin
    TIME_OUT_8000 = self.pluginconf.pluginConf['TimeOut8000']
    TIME_OUT_RESPONSE = self.pluginconf.pluginConf['TimeOutResponse']
    TIME_OUT_ACK = self.pluginconf.pluginConf['TimeOut8011']
    TIME_OUT_LISTCMD = 10

    now = int(time.time())

    self.loggingSend('Debug2', "checkTimedOut  Start - Aps_Sqn: %s waitQ: %2s ackQ: %2s dataQ: %2s SendingFIFO: %3s"
                     % (self.firmware_with_aps_sqn, len(self._waitFor8000Queue), len(self._waitForAckNack), len(self._waitForCmdResponseQueue), len(self.zigateSendQueue)))

    # Check if we have a Wait for 0x8000 message
    if len(self._waitFor8000Queue) > 0:
        # We are waiting for 0x8000
        InternalSqn, TimeStamp = self._waitFor8000Queue[0]
        if (now - TimeStamp) >= TIME_OUT_8000:
            timeout_8000(self)

    # Check Ack/Nack Queue
    if len(self._waitForAckNack) > 0 and self.zmode == 'zigateack':
        # We are waiting for APS Ack/Nack
        InternalSqn, TimeStamp = self._waitForAckNack[0]
        if (now - TimeStamp) >= TIME_OUT_ACK:
            timeout_acknack(self)

    # Check waitForCommandResponse Queue
    if len(self._waitForCmdResponseQueue) > 0 and self.zmode == 'zigate31c':
        # We are waiting for a Response from a Command
        InternalSqn, TimeStamp = self._waitForCmdResponseQueue[0]
        if (now - TimeStamp) >= TIME_OUT_RESPONSE:
            timeout_cmd_response(self)

    # Check if there is no TimedOut on ListOfCommands
    check_and_timeout_listofcommand(self)

    ready_to_send_if_needed(self)

    self.logging_receive('Debug2', "checkTimedOut  End   - waitQ: %2s ackQ: %2s dataQ: %2s SendingFIFO: %3s"
                         % (len(self._waitFor8000Queue), len(self._waitForAckNack), len(self._waitForCmdResponseQueue), len(self.zigateSendQueue)))


def cleanup_list_of_commands(self, i_sqn):

    self.loggingSend('Debug', " --  -- - > Cleanup Internal SQN: %s" % i_sqn)
    if i_sqn in self.ListOfCommands:
        self.loggingSend('Debug', " --  -- - > Removing ListOfCommand entry")
        del self.ListOfCommands[i_sqn]

# Receiving functions


def process_frame(self, frame):

    def cleanup_8000_queues(self, status, isqn):
        # Cleanup if required
        #self.logging_receive('Log', "Q8000: %s Q8011: %s QResponse: %s QLstCmd: %s zMode: %s ExpectedAck: %s WaitForResponse: %s ResponseExpected: %s" 
        #    %( len(self._waitFor8000Queue),  len(self._waitForAckNack), len(self._waitForCmdResponseQueue), len(self.ListOfCommands),
        #    self.zmode, self.ListOfCommands[isqn]['ExpectedAck'], self.ListOfCommands[isqn]['WaitForResponse'], 
        #    self.ListOfCommands[isqn]['ResponseExpected']))
        #for x in self.ListOfCommands:
        #    self.logging_receive('Log', "---- [%s] Cmd: %s Data: %s" %(x, self.ListOfCommands[x]['Cmd'], self.ListOfCommands[x]['Datas']))

        if Status != '00':
            cleanup_list_of_commands(self, isqn)
            return

        # Status 0x00
        if self.zmode == 'zigateack' and not self.ListOfCommands[isqn]['ExpectedAck'] and not self.ListOfCommands[isqn]['WaitForResponse']:
            cleanup_list_of_commands(self, isqn)
            return

        if self.zmode == 'zigate31c' and not self.ListOfCommands[isqn]['WaitForResponse'] and not self.ListOfCommands[isqn]['ResponseExpected']:

            cleanup_list_of_commands(self, isqn)
            return

    def cleanup_8011_queues(self, status, isqn):
        # Cleanup if required
        if Status != '00':
            cleanup_list_of_commands(self, isqn)
            return

        if self.zmode == 'zigateack' and not self.ListOfCommands[isqn]['WaitForResponse']:
            cleanup_list_of_commands(self, isqn)
            return

    # will return the Frame in the Data if any
    # process the Data and check if this is a 0x8000 message
    # in case the message contains several frame, receiveData will be recall


    self.logging_receive('Debug', "process_frame - Frame: %s" % frame)
    if frame == '' or frame is None or len(frame) < 12:
        return

    Status = None
    MsgData = None
    i_sqn = None
    MsgType = frame[2:6]
    MsgLength = frame[6:10]
    MsgCRC = frame[10:12]
    self.logging_receive(
        'Debug', "process_frame - MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))

    if MsgType == '8701':
        # Route Discovery
        # self.F_out(frame, None)  # for processing
        ready_to_send_if_needed(self)
        return

    if MsgType == "8702":
        # APS Failure
        # i_sqn = process_msg_type8702( self, MsgData )
        self.logging_receive(
            'Debug', "process_frame - APS Failure MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))
        self.statistics._APSFailure += 1
        self.F_out(frame, None)
        ready_to_send_if_needed(self)
        return

    # We receive an async message, just forward it to plugin
    if int(MsgType, 16) in STANDALONE_MESSAGE:
        self.logging_receive(
            'Debug', "process_frame - STANDALONE_MESSAGE MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))    
        self.F_out(frame, None)  # for processing
        ready_to_send_if_needed(self)
        return
        
    if len(frame) >= 18:
        # Payload
        MsgData = frame[12:len(frame) - 4]
        LQI = frame[len(frame) - 4: len(frame) - 2]

    if MsgData and MsgType == "8002":
        self.logging_receive(
            'Debug', "process_frame - 8002 MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))  
        self.F_out( process8002( self, frame ), None)
        ready_to_send_if_needed(self)
        return

    if len(self._waitFor8000Queue) == 0 and len(self._waitForCmdResponseQueue) == 0 and len(self._waitForAckNack) == 0:
        self.F_out(frame, None)
        ready_to_send_if_needed(self)
        return
        
    if MsgData and MsgType == "8000":
        Status = MsgData[0:2]
        sqn_app = MsgData[2:4]
        PacketType = MsgData[4:8]

        sqn_aps = None
        type_sqn = None
        if len(MsgData) == 12:
            # New Firmware 3.1d (get aps sqn)
            type_sqn = MsgData[8:10]
            sqn_aps = MsgData[10:12]
            if not self.firmware_with_aps_sqn:
                if self.zmode == 'auto':
                    self.zmode = 'zigateack'
                self.loggingSend(
                    'Status', "Firmware with APS SQN switching to Mode: ZiGateAck")
                self.firmware_with_aps_sqn = True

        if self.zmode == 'auto':
            self.zmode = 'zigate31c'
            self.loggingSend(
                'Status', "Firmware < 31d switching to Mode: ZiGate31c")

        i_sqn = process_msg_type8000(
            self, Status, PacketType, sqn_app, sqn_aps, type_sqn)
        
        self.loggingSend('Debug', "0x8000 - [%s] sqn_app: 0x%s/%3s, SQN_APS:non 0x%s type_sqn: %s" % (
            i_sqn, sqn_app, int(sqn_app, 16), sqn_aps, type_sqn))
        self.F_out(frame, None)

        if i_sqn in self.ListOfCommands:
            self.ListOfCommands[i_sqn]['APP_SQN'] = sqn_app
            self.ListOfCommands[i_sqn]['APS_SQN'] = sqn_aps
            self.ListOfCommands[i_sqn]['TYP_SQN'] = type_sqn
            self.loggingSend('Debug', "--> Check cleanup Status: %s [%s] Cmd: %s Data: %s ExpectedAck: %s ResponseExpected: %s"
                             % (Status, i_sqn, self.ListOfCommands[i_sqn]['Cmd'], self.ListOfCommands[i_sqn]['Datas'],
                                self.ListOfCommands[i_sqn]['ExpectedAck'], self.ListOfCommands[i_sqn]['ResponseExpected']))
            self.ListOfCommands[i_sqn]['Status'] = '8000'
            cleanup_8000_queues(self, Status, i_sqn)

        else:
            if i_sqn is not None:
                Domoticz.Error("i_sqn: %s not found in %s" %
                               (i_sqn, str(self.ListOfCommands.keys())))

        ready_to_send_if_needed(self)
        return

    if len(self._waitForCmdResponseQueue) == 0 and len(self._waitForAckNack) == 0:
        self.F_out(frame, None)
        ready_to_send_if_needed(self)
        return

    if MsgType == '8011':
        if Status == '00':
            # Ack
            self.statistics._APSAck += 1
        else:
            # Nack
            self.statistics._APSNck += 1

        if MsgData and self.zmode == 'zigate31c':
            # We do not block on Ack for firmware from 31c and below
            self.F_out(frame, None)
            ready_to_send_if_needed(self)
            return

        if MsgData and self.zmode == 'zigateack':
            # This is Optimum with firmware 3.1d and above
            MsgStatus = MsgData[0:2]
            MsgSrcAddr = MsgData[2:6]
            MsgSrcEp = MsgData[6:8]
            MsgClusterId = MsgData[8:12]
            MsgSEQ = 0
            if len(MsgData) > 12:
                MsgSEQ = MsgData[12:14]

            if self.firmware_with_aps_sqn:
                i_sqn = process_msg_type8011_above31d(
                    self, MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgSEQ)
            else:
                i_sqn = process_msg_type8011_below31c(
                    self, MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgSEQ)

            ReportingCommand = None
            if i_sqn in self.ListOfCommands:
                self.ListOfCommands[i_sqn]['Status'] = '8011'
                ReportingCommand = dict(self.ListOfCommands[i_sqn])
                # Forward the message to plugin for further processing
                self.F_out(frame, ReportingCommand)
                # We receive Response for Command, let's cleanup
                if not self.ListOfCommands[i_sqn]['WaitForResponse']:
                    cleanup_list_of_commands(self, i_sqn)

            ready_to_send_if_needed(self)
        return

    if len(self._waitForCmdResponseQueue) == 0:
        # All queues are empty
        self.F_out(frame, None)
        ready_to_send_if_needed(self)
        return

    # We reach that stage: Got a message not 0x8000/0x8011/0x8701/0x8202 an not a standolone message
    # But might be a 0x8102 ( as firmware 3.1c and below are reporting Read Attribute response and Report Attribute with the same MsgType)
    if self.zmode in 'zigate31c':
        # If ZigBee Command blocked until response received
        if not self.firmware_with_aps_sqn and MsgType in ( '8100', '8110', '8102'):
            MsgZclSqn = MsgData[0:2]
            MsgNwkId = MsgData[2:6]
            MsgEp = MsgData[6:8]
            MsgClusterId = MsgData[8:12]

            self.loggingSend(
                'Debug', "--> zigbee31c Receive MsgType: %s with ExtSqn: %s" % (MsgType, MsgZclSqn))

            i_sqn = process_other_type_of_message31c(
                self, MsgType, MsgZclSqn, MsgNwkId, MsgEp, MsgClusterId)
        else:
            i_sqn = process_other_type_of_message31c(self, MsgType)

        if i_sqn in self.ListOfCommands:
            self.ListOfCommands[i_sqn]['Status'] = '8XXX'
            cleanup_list_of_commands(
                self, _next_cmd_from_wait_cmdresponse_queue(self)[0])

    elif self.zmode == 'zigateack':
        # It is assumed that SQN are always on the 1st byte
        MsgZclSqn = MsgData[0:2]
        self.loggingSend(
            'Debug', "--> zigbeeack Receive MsgType: %s with ExtSqn: %s" % (MsgType, MsgZclSqn))
        i_sqn = process_other_type_of_message31d(self, MsgType, MsgZclSqn)
        if i_sqn in self.ListOfCommands:
            self.ListOfCommands[i_sqn]['Status'] = '8XXX'
            cleanup_list_of_commands(
                self, _next_cmd_from_wait_cmdresponse_queue(self)[0])

    # Forward the message to plugin for further processing
    self.F_out(frame, None)

    ready_to_send_if_needed(self)
    # Let's take the opportunity to check TimeOut
    self.check_timed_out_for_tx_queues()


def process_msg_type8000(self, Status, PacketType, sqn_app, sqn_aps, type_sqn):

    def error_8000_log( self, Status, PacketType, InternalSqn):
        if InternalSqn in self.ListOfCommands:
            self.loggingSend(
                "Debug","ZiGate reports error %s on submitted command %s/%s" 
                %( Status, self.ListOfCommands[InternalSqn]['Cmd'], self.ListOfCommands[InternalSqn]['Datas']) 
            )
        else:
            self.loggingSend(
                "Debug",
                "ZiGate reports error %s for PacketType: %s. Unable to find command out of %s commands"
                % (Status, PacketType, len(self.ListOfCommands))
            )




    if PacketType == '':
        return None

    self.loggingSend('Debug', "--> process_msg_type8000 - Status: %s PacketType: %s sqn_app:%s sqn_aps: %s type_sqn: %s" %
                     (Status, PacketType, sqn_app, sqn_aps, type_sqn))
    # Command Failed, Status != 00

    if int(PacketType,16) in CMD_PDM_ON_HOST:
        # No sync on PDM commands
        return None

    if Status != '00':
        self.statistics._ackKO += 1
        if self.zmode == 'zigate31c':
            # In that case we need to unblock data, as we will never get it !
            if len(self._waitForCmdResponseQueue) > 0:
                InternalSqn, TimeStamp = _next_cmd_from_wait_cmdresponse_queue(self)
                error_8000_log( self, Status, PacketType, InternalSqn)

        elif self.zmode == 'zigateack':
            # In that case we need to unblock ack_nack, as we will never get it !
            if len(self._waitForAckNack) > 0:
                InternalSqn, TimeStamp = _next_cmd_to_wait_for_ack_nack_queue(self)
                error_8000_log( self, Status, PacketType, InternalSqn)

        # Finaly freeup the 0x8000 queue
        NextCmdFromWaitFor8000 = _next_cmd_from_wait_for8000_queue(self)
        if NextCmdFromWaitFor8000 is None:
            return None
        InternalSqn, TimeStamp = NextCmdFromWaitFor8000
        return InternalSqn

    # Status is '00' -> Valid command sent !
    self.statistics._ack += 1
    NextCmdFromWaitFor8000 = _next_cmd_from_wait_for8000_queue(self)
    if NextCmdFromWaitFor8000 is None:
        self.loggingSend('Debug', " --  --  -- - > - Empty Queue")
        return None

    InternalSqn, TimeStamp = NextCmdFromWaitFor8000
    self.loggingSend('Debug', " --  --  -- - > InternSqn: %s ExternalSqn: %s ExternalSqnZCL: %s" %
                     (InternalSqn, sqn_app, sqn_aps))
    if InternalSqn not in self.ListOfCommands:
        return None

    # Statistics on ZiGate reacting time to process the command
    if self.pluginconf.pluginConf['ZiGateReactTime']:
        timing = int( ( time.time() - TimeStamp ) * 1000 )
        self.statistics.add_timing8000( timing )
        if self.statistics._averageTiming8000 != 0 and timing >= (3 * self.statistics._averageTiming8000):
            Domoticz.Log("Zigate round trip time seems long. %s ms for %s %s SendingQueue: %s LoC: %s" 
                %( timing , 
                self.ListOfCommands[InternalSqn]['Cmd'], 
                self.ListOfCommands[InternalSqn]['Datas'], 
                self.loadTransmit(), 
                len(self.ListOfCommands)
                ))


    self.loggingSend('Debug', " --  --  0x8000 > Expect: %s Receive: %s" %
                     (self.ListOfCommands[InternalSqn]['Cmd'], PacketType))
    if self.ListOfCommands[InternalSqn]['Cmd']:
        IsCommandOk = int(self.ListOfCommands[InternalSqn]['Cmd'], 16) == int(PacketType, 16)
        if not IsCommandOk:
            self.loggingSend(
                'Log', 
                "Error: process_msg_type8000 - [%s] sync error : Expecting %s Received: %s , lenQ8000: %s Q8000: %s ListOfCommand: %s"
                % (InternalSqn, self.ListOfCommands[InternalSqn]['Cmd'], PacketType, len(self._waitFor8000Queue), str(self._waitFor8000Queue), str(self.ListOfCommands)))
            return None

    if (not self.firmware_with_aps_sqn and self.ListOfCommands[InternalSqn]['ExpectedAck']) or (self.firmware_with_aps_sqn and type_sqn):
        # WARNING WE NEED TO Set TYPE_APP_ZCL or TYPE_APP_ZDP depending on the type of function, dont add it if ZIGATE function
        cmd = int(PacketType, 16)
        if cmd not in ZIGATE_COMMANDS:
            Domoticz.Error(
                "process_msg_type8000 received an unknown packet type: %s" % PacketType)
            return None

        if ZIGATE_COMMANDS[cmd]['Layer'] == 'ZCL':
            sqn_add_external_sqn(
                self, InternalSqn, sqn_app, TYPE_APP_ZCL, sqn_aps)

        elif ZIGATE_COMMANDS[cmd]['Layer'] == 'ZDP':
            sqn_add_external_sqn(
                self, InternalSqn, sqn_app, TYPE_APP_ZDP, sqn_aps)

    return InternalSqn


def process_msg_type8011_below31c(self, Status, NwkId, Ep, MsgClusterId, ExternSqn):

    self.loggingSend('Debug', "--> process_msg_type8011_below31c - Status: %s ExternalSqn: %s NwkId: %s Ep: %s ClusterId: %s" %
                     (Status, ExternSqn, NwkId, Ep, MsgClusterId))
    # Unqueue the Command in order to free for the next
    InternSqn, TimeStamps = _next_cmd_to_wait_for_ack_nack_queue(self)

    if (self.firmware_with_aps_sqn):
        InternSqn_from_ExternSqn = sqn_get_internal_sqn_from_aps_sqn(
            self, ExternSqn)
        if InternSqn != InternSqn_from_ExternSqn:
            Domoticz.Error("process_msg_type8011_below31c different sqn : InternSqn:%s InternSQN_from_ExternalSQN:%s" % (
                InternSqn, InternSqn_from_ExternSqn))

    if Status == '00':
        if InternSqn in self.ListOfCommands:
            self.loggingSend('Debug', " - [%s] receive Ack for Cmd: %s - size of SendQueue: %s" % (
                InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSAck += 1
    else:
        if InternSqn in self.ListOfCommands:
            self.loggingSend('Debug', " - [%s] receive Nack for Cmd: %s - size of SendQueue: %s" % (
                InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSNck += 1
    return InternSqn


def process_msg_type8011_above31d(self, Status, NwkId, Ep, MsgClusterId, ExternSqn):

    # Get i_sqn from sqnManagement
    InternSqn = sqn_get_internal_sqn_from_aps_sqn(self, ExternSqn)

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
            self.loggingSend('Debug', " - Above 3.1d [%s] receive Ack for Cmd: %s - size of SendQueue: %s" % (
                InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSAck += 1
    else:
        if InternSqn in self.ListOfCommands:
            self.loggingSend('Debug', " - Above 3.1d [%s] receive Nack for Cmd: %s - size of SendQueue: %s" % (
                InternSqn,  self.ListOfCommands[InternSqn]['Cmd'], self.loadTransmit()))
        self.statistics._APSNck += 1

    self._waitForAckNack.remove(item)

    return InternSqn


def process_msg_type8702(self, MsgData):
    # Status: d4 - Unicast frame does not have a route available but it is buffered for automatic resend
    # Status: e9 - No acknowledgement received when expected
    # Status: f0 - Pending transaction has expired and data discarded
    # Status: cf - Attempt at route discovery has failed due to lack of table space

    # Note: If a message is unicast to a destination for which a route has not already been established,
    # the message will not be sent and a route discovery will be performed instead. If this is the case,
    # the unicast function will return ZPS_NWK_ENUM_ROUTE_ERROR. The application must then wait for the
    # stack event ZPS_EVENT_NWK_ROUTE_DISCOVERY_CONFIRM (success or failure) before attempting to re-send
    # the message by calling the same unicast function again.

    self.loggingSend('Debug', "--> process_msg_type8702")
    if len(MsgData) == 0 or len(MsgData) < 8:
        Domoticz.Error("process_msg_type8702 - Empty frame: %s" % MsgData)
        return True

    MsgDataStatus = MsgData[0:2]
    #MsgDataSrcEp = MsgData[2:4]
    MsgDataDestEp = MsgData[4:6]
    MsgDataDestMode = MsgData[6:8]

    NWKID = IEEE = None
    if MsgDataDestMode == '01':  # IEEE
        IEEE = MsgData[8:24]
        ExternSqn = MsgData[24:26]
    elif MsgDataDestMode == '02':  # Short Address
        NwkId = MsgData[8:12]
        ExternSqn = MsgData[12:14]
    elif MsgDataDestMode == '03':  # Group
        MsgDataDestAddr = MsgData[8:12]
        ExternSqn = MsgData[12:14]

    self.loggingSend('Debug', "process_msg_type8702 - ExternalSqn: %s NwkId: %s Ep: %s" %
                     (ExternSqn, NwkId, MsgDataDestEp))

    InternSqn = sqn_get_internal_sqn_from_aps_sqn(self, ExternSqn)
    self.loggingSend(
        'Debug', "----------->  ExternalSqn: %s InternalSqn: %s" % (ExternSqn, InternSqn))

    return InternSqn


def process_other_type_of_message31c(self, MsgType, MsgSqn=None, MsgNwkId=None, MsgEp=None, MsgClusterId=None):

    self.statistics._data += 1
    # There is a probability that we get an ASYNC message, which is not related to a Command request.
    # In that case we should just process this message.

    # For now we assume that we do only one command at a time, so either it is an Async message,
    # or it is related to the command
    self.logging_receive(
        'Debug', "--> process_other_type_of_message - MsgType: %s" % (MsgType))

    if len(self._waitForCmdResponseQueue) == 0:
        self.logging_receive('Debug', " --  -- - > - WaitForDataQueue empty")
        return

    InternalSqn, TimeStamp = self._waitForCmdResponseQueue[0]

    if InternalSqn not in self.ListOfCommands:
        Domoticz.Error("process_other_type_of_message - MsgType: %s, InternalSqn: %s not found in ListOfCommands: %s"
                       % (MsgType, InternalSqn, str(self.ListOfCommands.keys())))
        ready_to_send_if_needed(self)
        return None

    expResponse = self.ListOfCommands[InternalSqn]['MessageResponse']
    expCmd = self.ListOfCommands[InternalSqn]['Cmd']
    self.loggingSend( 'Debug', " --  -- - > Expecting: %04x Receiving: %s" % (expResponse, MsgType))
    if ( expResponse ==  MsgType ) or ( expResponse == 0x8100 and MsgType in ( '8100', '8102') ):
        expNwkId = expEp = expCluster = None
        if MsgSqn and MsgNwkId and MsgEp and MsgClusterId:
            expNwkId = self.ListOfCommands[InternalSqn]['Datas'][2:6]
            expEp = self.ListOfCommands[InternalSqn]['Datas'][8:10]
            expCluster = self.ListOfCommands[InternalSqn]['Datas'][10:14]

        self.loggingSend('Debug', " --  -- - > Expecting: %s %s %s receiving %s %s %s" %
                         (expNwkId, expEp, expCluster, MsgNwkId, MsgEp, MsgClusterId))
        if (expNwkId != MsgNwkId) or (expEp != MsgEp) or (expCluster != MsgClusterId):
            self.loggingSend('Debug', " --  -- - > Data do not match")
            return None

        if MsgSqn is None:
            Domoticz.Error(
                "process_other_type_of_message - MsgType: %s cannot get i_sqn due to unknown External SQN" % (MsgType))
            return None

        # WARNING WE NEED TO Set TYPE_APP_ZCL or TYPE_APP_ZDP depending on the type of function, dont call if ZIGATE function
        isqn = None
        # MsgType is 0x8100 or 0x8102 ( Command was 0x0100) So it is a ZCL command
    
        if ZIGATE_COMMANDS[ int(expCmd,16) ]['Layer'] == 'ZCL':
            isqn = sqn_get_internal_sqn_from_app_sqn(
                self, MsgSqn, TYPE_APP_ZCL)

        elif ZIGATE_COMMANDS[ int(expCmd,16) ]['Layer'] == 'ZDP':
            isqn = sqn_get_internal_sqn_from_app_sqn(
                self, MsgSqn, TYPE_APP_ZDP)

        self.loggingSend(
            'Debug', " --  -- - > Expected IntSqn: %s Received ISqn: %s ESqn: %s" % (InternalSqn, isqn, MsgSqn))
        if isqn and InternalSqn != isqn:
            # Async message no worry
            self.loggingSend('Debug', " -- I_SQN do not match E_SQN, break")
            self.loggingSend(
                'Debug', " --  -- - > Expecting: %04x Receiving: %s" % (expResponse, MsgType))
            self.loggingSend(
                'Debug', " --  -- - > Expected IntSqn: %s Received ISqn: %s ESqn: %s" % (InternalSqn, isqn, MsgSqn))
            self.loggingSend('Debug', " --  -- - > Expecting: %s %s %s receiving %s %s %s" %
                             (expNwkId, expEp, expCluster, MsgNwkId, MsgEp, MsgClusterId))
            return None

        ready_to_send_if_needed(self)
        return InternalSqn

    self.loggingSend('Debug', " --  -- - > Internal SQN: %s Received: %s and expecting %04x" %
                     (InternalSqn, MsgType, expResponse))
    if int(MsgType, 16) != expResponse:
        self.logging_receive('Debug', "         - Async incoming PacketType")
        ready_to_send_if_needed(self)
        return None

    # If we have Still commands in the queue and the WaitforStatus+Data are free
    ready_to_send_if_needed(self)
    return InternalSqn


def process_other_type_of_message31d(self, MsgType, MsgSqn):

    self.statistics._data += 1
    # There is a probability that we get an ASYNC message, which is not related to a Command request.
    # In that case we should just process this message.

    # For now we assume that we do only one command at a time, so either it is an Async message,
    # or it is related to the command
    self.logging_receive(
        'Debug', "--> process_other_type_of_message31d - MsgType: %s" % (MsgType))
    if MsgSqn is None:
        Domoticz.Error(
            "process_other_type_of_message31d - MsgType: %s cannot get i_sqn due to unknown External SQN" % (MsgType))
        return None

    if len(self._waitForCmdResponseQueue) == 0:
        self.logging_receive('Debug', " --  -- - > - WaitForDataQueue empty")
        ready_to_send_if_needed(self)
        return

    InternalSqn, TimeStamp = self._waitForCmdResponseQueue[0]

    if InternalSqn not in self.ListOfCommands:
        Domoticz.Error("process_other_type_of_message31d - MsgType: %s, InternalSqn: %s not found in ListOfCommands: %s"
                       % (MsgType, InternalSqn, str(self.ListOfCommands.keys())))
        ready_to_send_if_needed(self)
        return None

    cmd = None
    for x in ZIGATE_COMMANDS:
        if len(ZIGATE_COMMANDS[x]['Sequence']) == 2 and ZIGATE_COMMANDS[x]['Sequence'][1] == int(MsgType, 16):
            cmd = x
            break

    if cmd is None:
        # We drop, unknown Command
        Domoticz.Error(
            "process_other_type_of_message31d - Unknown Message Type: %s" % cmd)
        ready_to_send_if_needed(self)
        return None

    expResponse = self.ListOfCommands[InternalSqn]['MessageResponse']
    # WARNING WE NEED TO Set TYPE_APP_ZCL or TYPE_APP_ZDP depending on the type of function, dont call if ZIGATE function
    isqn = None
    # MsgType is 0x8100 or 0x8102 ( Command was 0x0100) So it is a ZCL command
    if ZIGATE_COMMANDS[cmd]['Layer'] == 'ZCL':
        isqn = sqn_get_internal_sqn_from_app_sqn(self, MsgSqn, TYPE_APP_ZCL)

    elif ZIGATE_COMMANDS[cmd]['Layer'] == 'ZDP':
        isqn = sqn_get_internal_sqn_from_app_sqn(self, MsgSqn, TYPE_APP_ZDP)

    self.loggingSend('Debug', " --  -- - > Expected IntSqn: %s Received ISqn: %s ESqn: %s" %
                     (InternalSqn, isqn, MsgSqn))
    if isqn and InternalSqn != isqn:
        # Async message no worry
        self.loggingSend('Debug', " -- I_SQN do not match E_SQN, break")
        self.loggingSend(
            'Debug', " --  -- - > Expecting: %04x Receiving: %s" % (expResponse, MsgType))
        self.loggingSend(
            'Debug', " --  -- - > Expected IntSqn: %s Received ISqn: %s ESqn: %s" % (InternalSqn, isqn, MsgSqn))
        return None

    self.loggingSend(
        'Debug', " --  -- - > Expecting: %04x Receiving: %s" % (expResponse, MsgType))
    if int(MsgType, 16) != expResponse:
        self.logging_receive('Debug', "         - Async incoming PacketType")
        ready_to_send_if_needed(self)
        return None

    ready_to_send_if_needed(self)
    return InternalSqn


def process8002(self, frame):

    SrcNwkId, SrcEndPoint, ClusterId , Payload = extract_nwk_infos_from_8002( frame )
    self.logging_receive(
        'Debug', "process8002 NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))

    if SrcNwkId is None:
        return frame

    if len(Payload) < 8:
        return frame
        
    GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002( Payload )
    if not GlobalCommand:
        # This is not a Global Command (Read Attribute, Write Attribute and so on)
        return frame

    self.logging_receive(
        'Debug', "process8002 Sqn: %s ManufCode: %s Command: %s Data: %s " %(Sqn, ManufacturerCode, Command, Data))
    if Command == '00': # Read Attribute
        return buildframe_read_attribute_request( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, ManufacturerCode, Data  )

    if Command == '01': # Read Attribute response
        return buildframe_read_attribute_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data )

    if Command == '04': # Write Attribute response
        return buildframe_write_attribute_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data )

    if Command == '07':
        return buildframe_configure_reporting_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data )

    if Command == '0a':
        return buildframe_report_attribute_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data )

    self.logging_receive(
        'Log', "process8002 Unknown Command: %s NwkId: %s Ep: %s Cluster: %s Payload: %s" %(Command, SrcNwkId, SrcEndPoint, ClusterId , Data))
        
    return frame


def extract_nwk_infos_from_8002( frame ):

    MsgType = frame[2:6]
    MsgLength = frame[6:10]
    MsgCRC = frame[10:12]

    if len(frame) >= 18:
        # Payload
        MsgData = frame[12:len(frame) - 4]
        LQI = frame[len(frame) - 4: len(frame) - 2]

    ProfileId = MsgData[2:6]
    ClusterId = MsgData[6:10]
    SrcEndPoint = MsgData[10:12]
    TargetEndPoint = MsgData[12:14]
    SrcAddrMode = MsgData[14:16]

    if ProfileId != '0104':
        Domoticz.Log(
            "extract_nwk_infos_from_8002 - Not an HA Profile, let's drop the packet %s" % MsgData)
        return ( None, None, None , None )

    if int(SrcAddrMode, 16) in [ADDRESS_MODE['short'], ADDRESS_MODE['group']]:
        SrcNwkId = MsgData[16:20]  # uint16_t
        TargetNwkId = MsgData[20:22]

        if int(TargetNwkId, 16) in [ADDRESS_MODE['short'], ADDRESS_MODE['group'], ]:
            # Short Address
            TargetNwkId = MsgData[22:26]  # uint16_t
            Payload = MsgData[26:len(MsgData)]

        elif int(TargetNwkId, 16) == ADDRESS_MODE['ieee']:  # uint32_t
            # IEEE
            TargetNwkId = MsgData[22:38]  # uint32_t
            Payload = MsgData[38:len(MsgData)]

        else:
            Domoticz.Log("Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s"
                         % (TargetNwkId, MsgData))
            return ( None, None, None , None )

    elif int(SrcAddrMode, 16) == ADDRESS_MODE['ieee']:
        SrcNwkId = MsgData[16:32]  # uint32_t
        TargetNwkId = MsgData[32:34]

        if int(TargetNwkId, 16) in [ADDRESS_MODE['short'], ADDRESS_MODE['group'], ]:
            TargetNwkId = MsgData[34:38]  # uint16_t
            Payload = MsgData[38:len(MsgData)]

        elif int(TargetNwkId, 16) == ADDRESS_MODE['ieee']:
            # IEEE
            TargetNwkId = MsgData[34:40]  # uint32_t
            Payload = MsgData[40:len(MsgData)]
        else:
            Domoticz.Log("Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s"
                         % (TargetNwkId, MsgData))
            return ( None, None, None , None )
    else:
        Domoticz.Log("Decode8002 - Unexpected Source ADDR_MOD: %s, drop packet %s"
                     % (SrcAddrMode, MsgData))
        return ( None, None, None , None )

    return ( SrcNwkId, SrcEndPoint, ClusterId , Payload )


def buildframe_read_attribute_request( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, ManufacturerCode, Data  ):

    if len(Data) % 4 != 0:
        #Domoticz.Log("Most Likely Livolo Frame : %s (%s)" %(Data, len(Data)))
        return frame
    
    ManufSpec = '00'
    ManufCode = '0000'
    if ManufacturerCode:
        ManufSpec = '01'
        ManufCode = ManufacturerCode

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + '01' + ClusterId + '01' + ManufSpec + ManufCode
    idx = nbAttribute = 0
    payloadOfAttributes = ''
    while idx < len(Data):
        nbAttribute += 1
        Attribute = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[idx:idx+4],16)))[0]
        idx += 4
        payloadOfAttributes += Attribute

    buildPayload += '%02x' %(nbAttribute) + payloadOfAttributes

    #Domoticz.Log("buildframe_read_attribute_request - NwkId: %s Ep: %s ClusterId: %s nbAttribute: %s Data: %s" 
    #        %(SrcNwkId, SrcEndPoint, ClusterId, nbAttribute, Data))

    newFrame = '01' # 0:2
    newFrame += '0100' # 2:6   MsgType
    newFrame += '%4x' %len(buildPayload) # 6:10  Length
    newFrame += 'ff' # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4: len(frame) - 2] # LQI
    newFrame += '03'
    return  newFrame


def buildframe_write_attribute_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data):

    # This is based on assumption that we only Write 1 attribute at a time
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + '0000' + Data
    newFrame = '01' # 0:2
    newFrame += '8110' # 2:6   MsgType
    newFrame += '%4x' %len(buildPayload) # 6:10  Length
    newFrame += 'ff' # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4: len(frame) - 2] # LQI
    newFrame += '03'

    return  newFrame


def decode_endian_data( data, datatype):
    if datatype in ( '10', '18', '20', '28', '30'):
        value = data

    elif datatype in ('09', '19', '21', '29', '31'):
        value = '%04x' %struct.unpack('>H',struct.pack('H',int(data,16)))[0]

    elif datatype in ( '22', '2a'):
        value= '%06x' %struct.unpack('>I',struct.pack('I',int(data,16)))[0]

    elif datatype in ( '23', '2b', '39'):
        value = '%08x' %struct.unpack('>i',struct.pack('I',int(data,16)))[0]

    elif datatype in ( '00', '41', '42', '4c'):
        value = data

    else:
        value = data
        #Domoticz.Log("-------> Data not decoded Type: %s Value: %s " % (datatype, value))
    return value


def buildframe_read_attribute_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data ):

    nbAttribute = 0
    idx = 0
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
    while idx < len(Data):
        nbAttribute += 1
        Attribute = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[idx:idx+4],16)))[0]
        idx += 4
        Status = Data[idx:idx+2]
        idx += 2
        if Status == '00':
            DType = Data[idx:idx+2]
            idx += 2
            if DType in SIZE_DATA_TYPE:
                size = SIZE_DATA_TYPE[ DType ] * 2
            elif DType == '4c':
                nbElement =Data[ idx+2:idx+4] +  Data[ idx:idx+2 ]
                idx += 4
                # Today found for attribute 0xff02 Xiaomi, just take all data
                size = len(Data) - idx 
                #Domoticz.Log("Data: %s" %Data)
                #Domoticz.Log("Attribute: %s" %Attribute)
                #Domoticz.Log("DType: %s" %DType)
                #Domoticz.Log("size: %s" %size)
                #Domoticz.Log("data: %s" %Data[ idx:idx + size])

            elif DType in ( '41', '42'): # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
                size = int(Data[idx:idx+2],16) * 2
                idx += 2
            else: 
                Domoticz.Error("buildframe_read_attribute_response - Unknown DataType size: >%s< vs. %s " %(DType, str(SIZE_DATA_TYPE)))
                Domoticz.Error("buildframe_read_attribute_response - ClusterId: %s Attribute: %s Data: %s" %(ClusterId, Attribute, Data))
                return frame

            data = Data[idx:idx + size]
            idx += size
            value = decode_endian_data( data, DType)
            lenData = '%04x' %(size // 2 )
            buildPayload += Attribute + Status + DType + lenData + value
        else:
            buildPayload += Attribute + Status 

    #Domoticz.Log("buildframe_read_attribute_response for 0x8100 - NwkId: %s Ep: %s ClusterId: %s nbAttribute: %s Data: %s from frame: %s" %(SrcNwkId, SrcEndPoint, ClusterId, nbAttribute, buildPayload, frame))
    
    newFrame = '01' # 0:2
    newFrame += '8100' # 2:6   MsgType
    newFrame += '%4x' %len(buildPayload) # 6:10  Length
    newFrame += 'ff' # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4: len(frame) - 2] # LQI
    newFrame += '03'

    return  newFrame


def buildframe_report_attribute_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data ):
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
    nbAttribute = 0
    idx = 0
    while idx < len(Data):
        nbAttribute += 1
        Attribute = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[idx:idx+4],16)))[0]
        idx += 4
        DType = Data[idx:idx+2]
        idx += 2
        if DType in SIZE_DATA_TYPE:
            size = SIZE_DATA_TYPE[ DType ] * 2

        elif DType == '4c':
                # Today found for attribute 0xff02 Xiaomi, just take all data
                nbElement =Data[ idx+2:idx+4] +  Data[ idx:idx+2 ]
                idx += 4
                size = len(Data) - idx 
                #Domoticz.Log("Data: %s" %Data)
                #Domoticz.Log("Attribute: %s" %Attribute)
                #Domoticz.Log("DType: %s" %DType)
                #Domoticz.Log("size: %s" %size)
                #Domoticz.Log("data: %s" %Data[ idx:idx + size])

        elif DType in ( '41', '42'): # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
            size = int(Data[idx:idx+2],16) * 2
            idx += 2

        elif DType == '00':
            Domoticz.Error("buildframe_report_attribute_response %s/%s Cluster: %s nbAttribute: %s Attribute: %s DType: %s idx: %s frame: %s" 
                %(SrcNwkId, SrcEndPoint, ClusterId,nbAttribute, Attribute, DType, idx, frame ))
            return frame
            
        else: 
            Domoticz.Error("buildframe_report_attribute_response - Unknown DataType size: >%s< vs. %s " %(DType, str(SIZE_DATA_TYPE)))
            Domoticz.Error("buildframe_report_attribute_response - NwkId: %s ClusterId: %s Attribute: %s Frame: %s" %(SrcNwkId, ClusterId, Attribute, frame))
            return frame

        data = Data[idx:idx + size]
        idx += size
        value = decode_endian_data( data, DType)
        lenData = '%04x' %(size // 2 )
        buildPayload += Attribute + '00' + DType + lenData + value
        #Domoticz.Log("buildframe_report_attribute_response - Attribute: %s DType: %s Size: %s Value: %s"
        #    %(Attribute, DType, lenData, value))

    #Domoticz.Log("buildframe_report_attribute_response - NwkId: %s Ep: %s ClusterId: %s nbAttribute: %s Data: %s" %(SrcNwkId, SrcEndPoint, ClusterId, nbAttribute, buildPayload))

    newFrame = '01' # 0:2
    newFrame += '8102' # 2:6   MsgType
    newFrame += '%4x' %len(buildPayload) # 6:10  Length
    newFrame += 'ff' # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4: len(frame) - 2] # LQI
    newFrame += '03'
    return  newFrame


def buildframe_configure_reporting_response( frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data ):

    if len(Data) == 2:
        nbAttribute = 1
        buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + Data 
    else:
        idx = 0
        nbAttribute = 0
        buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
        while idx < len(Data):
            nbAttribute += 1
            Status = Data[idx:idx+2]
            idx += 2
            Direction = Data[idx:idx+2]
            idx += 2
            Attribute = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[idx:idx+4],16)))[0]
            idx += 4
            buildPayload += Attribute + Status
        return  frame

    #Domoticz.Log("buildframe_configure_reporting_response - NwkId: %s Ep: %s ClusterId: %s nbAttribute: %s Data: %s" %(SrcNwkId, SrcEndPoint, ClusterId, nbAttribute, buildPayload))
    newFrame = '01' # 0:2
    newFrame += '8120' # 2:6   MsgType
    newFrame += '%4x' %len(buildPayload) # 6:10  Length
    newFrame += 'ff' # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4: len(frame) - 2] # LQI
    newFrame += '03'
    return  newFrame



def zigate_encode(Data):
    # The encoding is the following:
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
