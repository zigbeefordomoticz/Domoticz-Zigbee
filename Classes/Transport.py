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
        self._checkTO_flag = None
        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin

        self.zigateSendingFIFO = []  # list of normal priority commands
        self._waitForStatus = []  # list of command sent and waiting for status 0x8000
        self._waitForData = []  # list of command sent for which status received and waiting for data
        self._waitForAPS = [] # Contain list of Command waiting for APS ACK or Failure. That one is populated when receiving x8000
        self._waitForRouteDiscoveryConfirm = []

        self.statistics = statistics

        self.pluginconf = pluginconf
        self.reTransmit = pluginconf.pluginConf['reTransmit']
        self.zmode = pluginconf.pluginConf['zmode']
        self.sendDelay = pluginconf.pluginConf['sendDelay']
        self.zTimeOut = pluginconf.pluginConf['zTimeOut']

        self.loggingFileHandle = loggingFileHandle

        self.loggingSend('Debug',"STANDALONE_MESSAGE: %s" %STANDALONE_MESSAGE)
        self.loggingSend('Debug',"CMD_ONLY_STATUS: %s" %CMD_ONLY_STATUS)
        self.loggingSend('Debug',"ZIGATE_COMMANDS: %s" %ZIGATE_COMMANDS)
        self.loggingSend('Debug',"CMD_NWK_2NDBytes: %s" %CMD_NWK_2NDBytes)

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


    def loggingSend( self, logType, message):

        if self.pluginconf.pluginConf['debugTransportTx'] and logType == 'Debug':
            self._loggingDebug( message )
        elif  logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message )

    def loggingReceive( self, logType, message):

        if self.pluginconf.pluginConf['debugTransportRx'] and logType == 'Debug':
            self._loggingDebug( message )
        elif  logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus.Status( message )

    # Transport / Opening / Closing Communication
    def setConnection( self ):

        BAUDS = 115200

        if self._connection is not None:
            del self._connection
            self._connection = None

        if self._transp == "USB":
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" %( self._serialPort ))
                self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None",
                         Address=self._serialPort, Baud= BAUDS)
        elif self._transp == "DIN":
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" %( self._serialPort ))
                self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None",
                         Address=self._serialPort, Baud=BAUDS)
        elif self._transp == "PI":
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" %( self._serialPort ))
                self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None",
                         Address=self._serialPort, Baud=BAUDS)
        elif self._transp == "Wifi":
            Domoticz.Status("Connection Name: Zigate, Transport: TCP/IP, Address: %s:%s" %( self._serialPort, self._wifiPort ))
            self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ",
                         Address=self._wifiAddress, Port=self._wifiPort)
        else:
            Domoticz.Error("Unknown Transport Mode: %s" %self._transp)


    def PDMLock( self , lock):

        self.PDMCommandOnly = lock

    def PDMLockStatus( self ):

        return self.PDMCommandOnly

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

    # Transport Sending Data
    def _sendData(self, cmd, datas, delay ):
        """
        send data to Zigate via the communication transport
        """
        self.loggingSend('Debug', "--> _sendData - %s %s %s" %(cmd, datas, delay))

        if datas == "":
            length = "0000"
        else:
            length = returnlen(4, (str(hex(int(round(len(datas) / 2)))).split('x')[-1]))  # by Cortexlegeni

        if datas == "":
            checksumCmd = getChecksum(cmd, length, "0")
            if len(checksumCmd) == 1:
                strchecksum = "0" + str(checksumCmd)
            else:
                strchecksum = checksumCmd
            lineinput = "01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + \
                        str(ZigateEncode(strchecksum)) + "03"
        else:
            checksumCmd = getChecksum(cmd, length, datas)
            if len(checksumCmd) == 1:
                strchecksum = "0" + str(checksumCmd)
            else:
                strchecksum = checksumCmd
            lineinput = "01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + \
                        str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"

        self.processCMD4APS( cmd, datas)
        self.loggingSend('Debug', "--> _sendData - sending encoded Cmd: %s length: %s CRC: %s Data: %s" \
                    %(str(ZigateEncode(cmd)), str(ZigateEncode(length)), str(ZigateEncode(strchecksum)), str(ZigateEncode(datas))))
        self._connection.Send(bytes.fromhex(str(lineinput)), delay)
        self.statistics._sent += 1

    # Transport / called by plugin 
    def onMessage(self, Data):

        self.loggingReceive('Debug', "onMessage - %s" %(Data))
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

    # For debuging purposes print the SendQueue
    def _printSendQueue(self):
        cnt = 0
        lenQ = len(self.zigateSendingFIFO)
        for iterFIFO in self.zigateSendingFIFO:
            if cnt < 5:
                self.loggingSend('Debug',"SendingFIFO[%d:%d] = %s " % (cnt, lenQ, iterFIFO[0]))
                cnt += 1
        self.loggingSend('Debug',"--")


    def _addCmdToSendQueue(self, cmd, data, reTransmit=0):
        """add a command to the waiting list"""
        timestamp = int(time())
        ##DEBUG Domoticz.Debug("_addCmdToSendQueue: cmd: %s data: %s reTransmit: %s" %(cmd, data, reTransmit))
        
        # Check if the Cmd+Data is not yet in the Queue. If yes forget that message
        for iterCmd, iterData, iterTS, iterreTx in self.zigateSendingFIFO:
            if cmd == iterCmd and data == iterCmd:
                self.loggingSend('Debug',"Do not queue again an existing command in the Pipe, we drop the command %s %s" %(cmd, data))
                return
        self.loggingSend('Debug', "--> _addCmdToSendQueue - adding to Queue %s %s %s %s" %(cmd, data, timestamp, reTransmit))
        self.zigateSendingFIFO.append((cmd, data, timestamp, reTransmit))
        if len(self.zigateSendingFIFO) > self.statistics._MaxLoad:
            self.statistics._MaxLoad = len(self.zigateSendingFIFO)
        self.statistics._Load = len(self.zigateSendingFIFO)

        #self._printSendQueue()

    def _addCmdToWaitQueue(self, cmd, data, reTransmit=0):
        'add a command to the waiting list'
        timestamp = int(time())
        self.loggingSend('Debug', "--> _addCmdToWaitQueue - adding to Queue %s %s %s %s" %(cmd, data, timestamp, reTransmit))
        self._waitForStatus.append((cmd, data, timestamp, reTransmit))

    def _addCmdToWaitDataQueue(self, expResponse, cmd, data, reTransmit=0):
        'add a command to the waiting list'
        timestamp = int(time())
        self.loggingSend('Debug', "--> _addCmdToWaitDataQueue - adding to Queue %s %s %s %s" %(cmd, data, timestamp, reTransmit))
        self._waitForData.append((expResponse, cmd, data, timestamp, reTransmit))

    def loadTransmit(self):
        return len(self.zigateSendingFIFO)

    def _nextCmdFromSendingFIFO(self):
        ' return the next Command to send pop'
        if len(self.zigateSendingFIFO) > 0:
            ret = self.zigateSendingFIFO[0]
            del self.zigateSendingFIFO[0]
            self.loggingSend('Debug', "--> _nextCmdFromSendingFIFO - Unqueue %s %s %s %s" %(ret[0], ret[1], ret[2], ret[3]))
            # self._printSendQueue()
            return ret
        return (None, None, None, None)

    def _nextCmdFromWaitQueue(self):
        ' return the entry waiting for a Status '
        if len(self._waitForStatus) > 0:
            ret = self._waitForStatus[0]
            del self._waitForStatus[0]
            return ret
        return None

    def _nextCmdFromWaitDataQueue(self):
        ' return the entry waiting for Data '
        if len(self._waitForData) > 0:
            ret = self._waitForData[0]
            del self._waitForData[0]
            return ret
        return ( None, None, None, None, None)

    def sendData(self, cmd, datas , delay=None):
        '''
        in charge of sending Data. Call by sendZigateCmd
        If nothing in the waiting queue, will call _sendData and it will be sent straight to Zigate
        '''
        self.loggingSend('Debug', "sendData - %s %s %s FIFO: %s" %(cmd, datas, delay, len(self.zigateSendingFIFO)))

        # Before to anything, let's check that the cmd and datas are HEXA information.
        if datas is None:
            datas = ''
        if datas != '' and not is_hex( datas):
            Domoticz.Error("sendData - receiving a non hexa Data: >%s<" %datas)
            return

        if self.zmode == 'Agressive':
            sendNow = (len(self._waitForStatus) == 0) or int(cmd,16) in CMD_PDM_ON_HOST
        else:
            sendNow = (len(self._waitForStatus) == 0 and len(self._waitForData) == 0) or int(cmd,16) in CMD_PDM_ON_HOST

        # PDM Management.
        # When PDM traffic is ongoing we cannot interupt, so we need to FIFO all other commands until the PDMLock is released
        PDM_COMMANDS = ( '8300', '8200', '8201', '8204', '8205', '8206', '8207', '8208' )
        if self.PDMLockStatus() and cmd not in PDM_COMMANDS:
            # Only PDM related command can go , all others will be dropped.
            Domoticz.Log("PDM not yet ready, FIFO command %s %s" %(cmd, datas))
            sendNow = False

        self.loggingSend('Debug', "sendData - Command: %s zMode: %s Q(Status): %s Q(Data): %s sendNow: %s" %(cmd, self.zmode, len(self._waitForStatus), len(self._waitForData), sendNow))

        # In case the cmd is part of the PDM on Host commands, that is High Priority and must go through.
        if sendNow:
            if int(cmd,16) not in CMD_PDM_ON_HOST:
                # That is a Standard command (not PDM on  Host), let's process as usall
                self._addCmdToWaitQueue(cmd, datas)
                if self.zmode == 'ZigBee' and int(cmd, 16) in CMD_DATA:  # We do wait only if required and if not in AGGRESSIVE mode
                    self._addCmdToWaitDataQueue(CMD_DATA[int(cmd, 16)], cmd, datas)
            if delay is None:
                self._sendData(cmd, datas, self.sendDelay )
            else:
                self._sendData(cmd, datas, delay )

        else:
            # Put in FIFO
            self.loggingSend('Debug', "sendData - put in waiting queue")
            self._addCmdToSendQueue(cmd, datas)

    def processFrame(self, frame):
        ''' 
        will return the Frame in the Data if any
        process the Data and check if this is a 0x8000 message
        in case the message contains several frame, receiveData will be recall
        '''

        self.loggingReceive( 'Debug', "processFrame - Frame: %s" %frame)
        if frame == '' or frame is None or len(frame) < 12:
            return

        Status = None
        MsgType = frame[2:6]
        MsgLength = frame[6:10]
        MsgCRC = frame[10:12]
        self.loggingReceive( 'Debug', "         - MsgType: %s MsgLength: %s MsgCRC: %s" %(MsgType, MsgLength, MsgCRC))

        if len(frame) >= 18:
            #Payload
            MsgData = frame[12:len(frame) - 4]
            Status = MsgData[0:2]
            SEQ = MsgData[2:4]
            PacketType = MsgData[4:8]
            RSSI = frame[len(frame) - 4: len(frame) - 2]
            self.loggingReceive( 'Debug', "         - Status: %s SEQ: %s PacketType: %s RSSI: %s" %(Status, SEQ, PacketType, RSSI))

        if MsgType == "8000":  # We are receiving a Status
            # We have receive a Status code in response to a command.
            if Status:
                self._process8000(Status, PacketType, frame)
            self.F_out(frame)  # Forward the message to plugin for further processing
            return

        if MsgType == '8011': # APS Ack/Nck with Firmware 3.1b

            MsgStatus = MsgData[0:2]
            MsgSrcAddr = MsgData[2:6]
            MsgSrcEp = MsgData[6:8]
            MsgClusterId = MsgData[8:12]

            #Domoticz.Log("processFrame - 0x8011 - APS Ack/Nck - Status: %s for %s/%s on cluster: %s" %(MsgStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId))

            if MsgStatus == '00':
                self.statistics._APSAck += 1
                
            elif MsgStatus == 'a7':
                self.statistics._APSNck += 1

            # Next step is to look after the last command for SrcAddr/SrcEp and if it matches the ClusterId

            self.F_out(frame)  # Forward the message to plugin for further processing

        elif MsgType == "8701": # Router Discovery Confirm
            if self.pluginconf.pluginConf['APSrteError']:
                if self.lock:
                    Domoticz.Debug("processFrame - passing the 0x8701 frame (lock)")
                    self.F_out(frame)  # Forward the message to plugin for further processing
                else:
                    self.lock = True
                    NwkStatus = MsgData[0:2]
                    Status = MsgData[2:4]
                    MsgSrc = ''
                    # https://github.com/fairecasoimeme/ZiGate/pull/231/commits/9a206779050fbce3bd464cad9bd65affb91d1720
                    if len(MsgData) == 8:
                        MsgSrc = MsgData[4:8]
                        self.loggingReceive('Log',"             - New Route Discovery for %s" %(MsgSrc))
    
                    if len(self._waitForRouteDiscoveryConfirm) > 0:
                        # We have some pending Command for re-submition
                        tupleCommands = list(self._waitForRouteDiscoveryConfirm)
                        for cmd, payload, frame8702 in tupleCommands:
                            if Status == NwkStatus == '00':
                                self.loggingReceive('Debug',"             - New Route Discovery OK, resend %s %s" %(cmd, payload))
                                self.sendData(cmd, payload)
                            else:
                                self.loggingReceive('Debug',"             - New Route Discovery KO, drop %s %s" %(cmd, payload))
                                self.F_out( frame8702 )  # Forward the old frame in the pipe. str() is used to make a physical copy
    
                            self._waitForRouteDiscoveryConfirm.remove( ( cmd, payload, frame8702)  )
    
                        del self._waitForRouteDiscoveryConfirm 
                        self._waitForRouteDiscoveryConfirm = []
                self.lock = False
            else:
                self.F_out(frame)  # Forward the message to plugin for further processing


        elif MsgType == "8702": # APS Failure
            #if self._process8702( frame ):
                self.loggingReceive('Debug',"             - detect an APS Failure forward to plugin")
                self.statistics._APSFailure += 1
                self.F_out(frame)  # Forward the message to plugin for further processing

        elif int(MsgType, 16) in STANDALONE_MESSAGE:  # We receive an async message, just forward it to plugin
            self.F_out(frame)  # for processing

        else:
            self.receiveDataCmd(MsgType)  #
            self.F_out(frame)  # Forward the message to plugin for further processing

        self.checkTOwaitFor()  # Let's take the opportunity to check TimeOut


    def receiveDataCmd(self, MsgType):
        self.statistics._data += 1
        # There is a probability that we get an ASYNC message, which is not related to a Command request.
        # In that case we should just process this message.

        self.loggingReceive( 'Debug', "receiveDataCmd - MsgType: %s" %(MsgType))

        if len(self._waitForData) != 0:
            if int(MsgType, 16) != self._waitForData[0][0]:
                self.loggingReceive( 'Debug', "         - not waiting Data")
                return

        expResponse, cmd, datas, pTime, reTx = self._nextCmdFromWaitDataQueue()

        self.loggingReceive( 'Debug', "         - Expecting: Response: %s, Cmd: %s, Datas: %s, Time: %s reTx: %s" \
                %(expResponse, cmd, datas, pTime, reTx))

        # If we have Still commands in the queue and the WaitforStatus+Data are free
        if len(self.zigateSendingFIFO) != 0 \
                and len(self._waitForStatus) == 0 and len(self._waitForData) == 0:
            cmd, datas, timestamps, reTx = self._nextCmdFromSendingFIFO()
            self.sendData(cmd, datas)


    def _process8000(self, Status, PacketType, frame):
        self.statistics._ack += 1

        # Command Failed, Status != 00
        if Status != '00':
            self.statistics._ackKO += 1
            # In that case we need to unblock data, as we will never get it !
            if len(self._waitForData) > 0:
                expResponse, pCmd, pData, pTime, reTx =  self._nextCmdFromWaitDataQueue()
                self.loggingReceive( 'Debug', "waitForData - unlock waitForData due to command %s failed, remove %s/%s" %(PacketType, expResponse, pCmd))

        # What to do with the Command
        if PacketType != '':
            expectedCommand = self._nextCmdFromWaitQueue()
            if expectedCommand is None:
                self.loggingReceive( 'Debug',"_process8000 - Empty Queue")
            else:
                if int(expectedCommand[0], 16) != int(PacketType, 16):
                    self.loggingReceive( 'Debug',"receiveData - sync error : Expecting %s and Received: %s" \
                            % (expectedCommand[0], PacketType))
            
            # If we have a APS Ack firmware, then we will push the Cmd/Data tfor APS Ack/Failure
            if APS_ACK:
                cmd, data, timestamp, reTransmit = expectedCommand
                if cmd == PacketType:
                    self.loggingReceive('Debug',"_process8000 - APS Ack push Cmd: %s Data: %s for APS Ack/Failure" %(cmd, data))
                    self.addCmdTowaitForAPS( cmd, data )
                else:
                    Domoticz.Error("_process8000 - APS Ack push receive Cmd %s status doesn't match Cmd %s in FIFO!" %(PacketType, cmd))
        # Let's check if we cannot send a command from teh Queue
        if len(self.zigateSendingFIFO) != 0 and len(self._waitForStatus) == 0 and len(self._waitForData) == 0:
            cmd, datas, timestamps, reTx = self._nextCmdFromSendingFIFO()
            self.sendData(cmd, datas)


    def checkTOwaitFor(self):
        'look at the waitForStatus, and in case of TimeOut delete the entry'

        if self._checkTO_flag:  # checkTOwaitFor can be called either by onHeartbeat or from inside the Class. 
                                # In case it comes from onHeartbeat we might have a re-entrance issue
            ##Domoticz.Debug("checkTOwaitFor already ongoing")
            return
        self._checkTO_flag = True
        self.loggingReceive('Debug',"checkTOwaitFor   - Cmd: %04.X waitQ: %s dataQ: %s SendingFIFO: %s"\
                 %(0x0000, len(self._waitForStatus), len(self._waitForData), len(self.zigateSendingFIFO)))

        # Check waitForStatus
        if len(self._waitForStatus) > 0:
            now = int(time())
            pCmd, pDatas, pTime, reTx = self._waitForStatus[0]
            ## DEBUG Domoticz.Debug("checkTOwaitForStatus - %04.x enter at: %s delta: %s" % (int(pCmd, 16), pTime, now - pTime))
            if (now - pTime) > self.zTimeOut:
                self.statistics._TOstatus += 1
                entry = self._nextCmdFromWaitQueue()
                if entry:
                   self.loggingReceive('Debug',"waitForStatus - Timeout %s on %04.x " % (now - pTime, int(entry[0], 16)))

        # Check waitForData
        if len(self._waitForData) > 0:
            now = int(time())
            expResponse, pCmd, pData, pTime, reTx = self._waitForData[0]
            if (now - pTime) > self.zTimeOut:
                self.statistics._TOdata += 1
                expResponse, pCmd, pData, pTime, reTx =  self._nextCmdFromWaitDataQueue()
                self.loggingReceive('Debug',"waitForData - Timeout %s sec on %04.x Command waiting for %04.x " % (now - pTime, expResponse, int(pCmd,16)))
                # If we allow reTransmit, let's resend the command
                if self.reTransmit:
                    if int(pCmd, 16) in RETRANSMIT_COMMAND and reTx <= self.reTransmit:
                        self.statistics._reTx += 1
                        self.loggingReceive('Debug',"checkTOwaitForStatus - Request a reTransmit of Command : %s/%s (%s) " % (
                            pCmd, pData, reTx))
                        # waitForData should be 0 as well as waitForCmd
                        if  len(self._waitForData) == len(self._waitForStatus) == 0 :
                            reTx += 1
                            self._addCmdToWaitQueue(pCmd, pData, reTransmit=reTx)
                            self._addCmdToWaitDataQueue(CMD_DATA[int(pCmd, 16)],pCmd, pData, reTransmit=reTx)
                            self._sendData( pCmd, pData , self.sendDelay)
                        else:
                            Domoticz.Error("Unable to retransmit message %s/%s Queue was not free anymore !" %(pCmd, pData))

        if len(self.zigateSendingFIFO) != 0 \
                and len(self._waitForStatus) == 0 and len(self._waitForData) == 0:
            cmd, datas, timestamps, reTx = self._nextCmdFromSendingFIFO()
            self.loggingReceive('Debug', "checkTOwaitForStatus - Unqueue %s %s" %(cmd, datas))
            self.sendData(cmd, datas)

        # self._printSendQueue()
        self._checkTO_flag = False


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
        MsgSQN = MsgData[2:4]
        MsgSrcEp = MsgData[4:6]
        MsgDstEp = MsgData[6:8]
        MsgProfileID = MsgData[8:12]
        MsgClusterId = MsgData[12:16]
    
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

        self.loggingReceive('Debug',"_process8702 - NwkId: %s Ieee: %s Status: %s" %(NWKID, IEEE, MsgDataStatus))
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

            if self.pluginconf.pluginConf['APSrteError'] and len(_lastCmds[0]) == 3:
                self.loggingReceive('Debug',"_process8702 - WARNING - Queue Size: %s received APSFailure %s %s %s, will wait for a Route Discoverys" %( len(self._waitForRouteDiscoveryConfirm), NWKID, iterCmd, iterpayLoad))
                tupleCommand = ( iterCmd, iterpayLoad, frame)
                if (  tupleCommand ) not in self._waitForRouteDiscoveryConfirm:
                    self.loggingReceive('Debug',"      -> Add %s %s to Queue" %( iterCmd, iterpayLoad))
                    self._waitForRouteDiscoveryConfirm.append( tupleCommand )
                else:
                    self.loggingReceive('Debug',"      -> Do not add to Queue %s %s , already in" %(iterCmd, iterpayLoad))
                return False

            if self.pluginconf.pluginConf['APSreTx'] and len(_lastCmds[1]) == 3:
                iterTime2 = 0
                iterCmd2 = iterpayLoad2 = None
                if len(_lastCmds) >= 2: # At least we have 2 Commands
                    # Retreive command -1
                    iterTime2, iterCmd2, iterpayLoad2 = _lastCmds[1]
    
                if APS_MAX_RETRY == 2:
                    if iterCmd2 == iterCmd and iterpayLoad2 == iterpayLoad and \
                            iterTime  <= (iterTime2 + APS_TIME_WINDOW):
                        return True
     
                elif APS_MAX_RETRY == 3:
                    iterTime2 = 0
                    iterCmd2 = iterpayLoad2 = None
                    if len(_lastCmds) >= 3: # At least we have 3 commands
                        # Retreive command -1
                        iterTime3, iterCmd3, iterpayLoad3 = _lastCmds[2]
                    if iterCmd3 == iterCmd2 == iterCmd and iterpayLoad3 == iterpayLoad2 == iterpayLoad and \
                            iterTime  <= (iterTime3 + APS_TIME_WINDOW):
                        return True
        
                if _timeAPS <= ( iterTime + APS_TIME_WINDOW):
                    # That command has been issued in the APS time window
                    self.sendData( iterCmd, iterpayLoad, 2)
                    self.statistics._reTx += 1
                    return False

        return True

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
                else:
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