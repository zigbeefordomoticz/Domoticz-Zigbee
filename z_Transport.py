#!/usr/bin/python

import Domoticz
import binascii
import struct
import time

AGGRESSIVE = 0
DELAY = 0
TIMEOUT = 20  # Timeout after which we unblock

# Standalone message. They are receive and do not belongs to a command
STANDALONE_MESSAGE = (0x8101, 0x8102, 0x8003, 0x804, 0x8005, 0x8006, 0x8701, 0x8702, 0x004D)

# Command message followed by a Status
CMD_ONLY_STATUS = (0x0012, 0x0016, 0x0020, 0x0021, 0x0022, 0x0023, 0x0027, 0x0049,
                   # Group
                   0x0064, 0x0065,
                   # Identify
                   0x0070, 0x0071,
                   # Action Move
                   0x0080, 0x0081, 0x0082, 0x0083, 0x0084,
                   # On Off
                   0x0092, 0x0093, 0x0094,
                   # Action Touchlink
                   0x00D0, 0x00D2,
                   # IAS Zone
                   0x0400, 0x0401,
                   # Request APS
                   0x0530)

# Commands/Answers
CMD_DATA = {0x0009: 0x8009, 0x0010: 0x8010, 0x0014: 0x8014, 0x0015: 0x8015,
            0x0017: 0x8017, 0x0024: 0x8024, 0x0026: 0x8048, 0x0028: 0x8028,
            0x002B: 0x802B, 0x002C: 0x802C, 0x0030: 0x8030, 0x0031: 0x8031,
            0x0034: 0x8034, 0x0040: 0x8040, 0x0041: 0x8041, 0x0042: 0x8042,
            0x0043: 0x8043, 0x0044: 0x8044, 0x0045: 0x8045, 0x0046: 0x8046,
            0x0047: 0x8047, 0x004A: 0x804A, 0x004B: 0x804B, 0x004E: 0x804E,
            # groups
            0x0060: 0x8060, 0x0061: 0x8061, 0x0062: 0x8062, 0x0063: 0x8063,
            # Scenes
            0x00A0: 0x80A0, 0x00A1: 0x80A1, 0x00A2: 0x80A2, 0x00A3: 0x80A3,
            0x00A4: 0x80A4, 0x00A5: 0x80A5, 0x00A6: 0x80A6, 0x00A7: 0x80A7,
            0x00A8: 0x80A8, 0x00A9: 0x80A9,
            # Action Hue
            0x00B0: 0x8002, 0x00B1: 0x8002, 0x00B2: 0x8002, 0x00B3: 0x8002,
            0x00B4: 0x8002, 0x00B5: 0x8002, 0x00B6: 0x8002, 0x00B7: 0x8002,
            0x00B8: 0x8002, 0x00B9: 0x8002, 0x00BA: 0x8002, 0x00BB: 0x8002,
            0x00BC: 0x8002, 0x00BD: 0x8002, 0x00BE: 0x8002, 0x00BF: 0x8002,
            # Action Color
            0x00C0: 0x8002, 0x00C1: 0x8002, 0x00C2: 0x8002,
            # Action Lock/Unlock Door
            0x00F0: 0x8002,
            # Action Attribute
            0x0100: 0x8100, 0x0110: 0x8110, 0x0120: 0x8120, 0x0140: 0x8140
            }


class ZigateTransport(object):
    """
    Class in charge of Transport mecanishm to and from Zigate
    Managed also the Command -> Status -> Data sequence
    """

    def __init__(self, transport, F_out, serialPort=None, wifiAddress=None, wifiPort=None):
        Domoticz.Log("Setting Transport object")

        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin

        if str(transport) == "USB":
            self._transp = "USB"
            self._serialPort = serialPort
            self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None",
                                                   Address=self._serialPort, Baud=115200)
        elif str(transport) == "Wifi":
            self._transp = "Wifi"
            self._wifiAddress = wifiAddress
            self._wifiPort = wifiPort
            self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ",
                                                   Address=self._wifiAddress, Port=self._wifiPort)

        self._normalQueue = []  # list of normal priority commands
        self._waitForStatus = []  # list of command sent and waiting for status 0x8000
        self._waitForData = []  # list of command sent for which status received and waiting for data

        self._crcErrors = 0  # count of crc errors
        self._frameErrors = 0  # count of frames error
        self._sent = 0  # count of sent messages
        self._received = 0  # count of received messages
        self._ack = 0  # count number of 0x8000
        self._ackKO = 0  # count Ack with status != 0
        self._data = 0  # count data messages
        self._TOstatus = 0  # count the number of TO trigger while waiting for status
        self._TOdata = 0  # count the number of TO triggered while waiting for data

    # Statistics methods 
    def crcErrors(self):
        ' return the number of crc Errors '
        return self._crcErrors

    def frameErrors(self):
        ' return the number of frame errors'
        return self._frameErrors

    def sent(self):
        ' return he number of sent messages'
        return self._sent

    def received(self):
        ' return the number of received messages'
        return self._received

    def ackReceived(self):
        ' return the number of ack 0x8000 '
        return self._ack

    def ackKOReceived(self):
        ' return the number of ack 0x8000 '
        return self._ackKO

    def dataReceived(self):
        ' return the number of ack 0x8000 '
        return self._data

    def TOstatus(self):
        ' return the number of ack 0x8000 '
        return self._TOstatus

    def TOdata(self):
        ' return the number of ack 0x8000 '
        return self._TOdata

    # Transport / Opening / Closing Communication
    def openConn(self):
        self._connection.Connect()

    def closeConn(self):
        self._connection.Disconnect()
        self._connection = None

    def reConn(self):
        if not self.isConn():
            self.openConn()

    def isConn(self):
        if self._connection is None:
            return False
        else:
            return True

    # Transport Sending Data
    def _sendData(self, cmd, datas, delay):
        '''
        send data to Zigate via the communication transport
        '''
        Domoticz.Log("_sendData %s" % cmd)

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

        self._connection.Send(bytes.fromhex(str(lineinput)), delay)
        self._sent += 1

    # Transport / called by plugin 
    def onMessage(self, Data):
        Domoticz.Debug("onMessage called on Connection " + str(Data))

        FrameIsKo = 0

        if Data is not None:
            self._ReqRcv += Data  # Add the incoming data
            Domoticz.Debug("onMessage incoming data : '" + \
                           str(binascii.hexlify(self._ReqRcv).decode('utf-8')) + "'")

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
                Domoticz.Debug("onMessage : we have probably lost some datas, zero1 = " + str(Zero1))

            # uncode the frame
            BinMsg = bytearray()
            iterReqRcv = iter(self._ReqRcv[Zero1:Zero3])

            for iByte in iterReqRcv:  # for each received byte
                if iByte == 2:  # Coded flag ?
                    iByte = next(iterReqRcv) ^ 16  # then uncode the next value
                BinMsg.append(iByte)  # copy

            self._ReqRcv = self._ReqRcv[Zero3:]  # What is after 0x03 has to be reworked.

            # Check length
            Zero1, MsgType, Length, ReceivedChecksum = struct.unpack('>BHHB', BinMsg[0:6])
            ComputedLength = Length + 7
            ReceveidLength = len(BinMsg)
            if ComputedLength != ReceveidLength:
                FrameIsKo = 1
                self._frameErrors += 1
                Domoticz.Error("onMessage : Frame size is bad, computed = " + \
                               str(ComputedLength) + " received = " + str(ReceveidLength))

            # Compute checksum
            ComputedChecksum = 0
            for idx, val in enumerate(BinMsg[1:-1]):
                if idx != 4:  # Jump the checksum itself
                    ComputedChecksum ^= val
            if ComputedChecksum != ReceivedChecksum:
                FrameIsKo = 1
                self._crcErrors += 1
                Domoticz.Error("onMessage : Frame CRC is bad, computed = " + str(ComputedChecksum) + \
                               " received = " + str(ReceivedChecksum))

            if FrameIsKo == 0:
                AsciiMsg = binascii.hexlify(BinMsg).decode('utf-8')
                self._received += 1
                self.processFrame(AsciiMsg)

    # For debuging purposes print the SendQueue
    def _printSendQueue(self):
        cnt = 0
        for iter in self._normalQueue:
            Domoticz.Log("normalQueue[%d] = %s " % (cnt, iter[0]))
            cnt += 1

    def addCmdToSend(self, cmd, data):
        'add a command to the waiting list'
        timestamp = int(time.time())
        self._normalQueue.append((cmd, data, timestamp))
        # self._printSendQueue()

    def nextCmdtoSend(self):
        ' return the next Command to send pop'
        if len(self._normalQueue) > 0:
            ret = self._normalQueue[0]
            del self._normalQueue[0]
            # self._printSendQueue()
            return ret
        return None

    def nextStatusInWait(self):
        ' return the entry waiting for a Status '
        if len(self._waitForStatus) > 0:
            ret = self._waitForStatus[0]
            del self._waitForStatus[0]
            return ret
        return None

    def addCmdToWait(self, cmd, data):
        'add a command to the waiting list'
        timestamp = int(time.time())
        self._waitForStatus.append((cmd, data, timestamp))

    def nextDataInWait(self):
        ' return the entry waiting for Data '
        if len(self._waitForData) > 0:
            ret = self._waitForData[0]
            del self._waitForData[0]
            return ret
        return None

    def addDataToWait(self, cmd):
        'add a command to the waiting list'
        timestamp = int(time.time())
        self._waitForData.append((cmd, timestamp))

    def sendData(self, cmd, datas, delay=DELAY):
        '''
        in charge of sending Data. Call by sendZigateCmd
        If nothing in the waiting queue, will call _sendData and it will be sent straight to Zigate
        '''
        # Check if normalQueue is empty. If yes we can send the command straight
        Domoticz.Debug("sendData         - waitQ: %s dataQ: %s normalQ: %s" \
                       % (len(self._waitForStatus), len(self._waitForData), len(self._normalQueue)))
        if len(self._waitForStatus) != 0:
            Domoticz.Debug("sendData - waitQ: %04.X" % (int(self._waitForStatus[0][0], 16)))
        if len(self._waitForData) != 0:
            Domoticz.Debug("sendData - waitD: %04.X" % (int(self._waitForData[0][0])))

        # Let's check if we don't have something waiting for ages !
        self.checkTOwaitFor()

        # We can enable an aggressive version , where we queue ONLY for Status, but we consider that the data will come and so we don't wait for data.

        # If no wait on Status nor on Data, gooooooo
        if AGGRESSIVE:
            waitIsRequired = len(self._waitForStatus) == 0 
        else:
            waitIsRequired = len(self._waitForStatus) == 0 and len(self._waitForData) == 0

        if waitIsRequired:
            self.addCmdToWait(cmd, datas)
            if not AGGRESSIVE and int(cmd, 16) in CMD_DATA:     # We do wait only if required and if not in AGGRESSIVE mode
                self.addDataToWait(CMD_DATA[int(cmd, 16)])
            self._sendData(cmd, datas, delay)
        else:
            # Put in FIFO
            self.addCmdToSend(cmd, datas)

    def processFrame(self, frame):
        ''' 
        will return the Frame in the Data if any
        process the Data and check if this is a 0x8000 message
        in case the message contains several frame, receiveData will be recall
        '''

        Domoticz.Debug("receiveData - new Data coming")
        if frame == '' or frame is None:
            return

        MsgType = frame[2:6]
        MsgLength = frame[6:10]
        MsgCRC = frame[10:12]

        Domoticz.Debug("receiveData - MsgType: %s" % MsgType)

        if MsgType == "8000":  # We are receiving a Status
            if len(frame) > 12:
                # We have Payload : data + rssi
                MsgData = frame[12:len(frame) - 4]
                if len(MsgData) < 8:
                    Domoticz.Debug("receiveData - empty Frame payload: %s" % frame)
                    return
            else:
                Domoticz.Debug("receiveData - empty Frame payload: %s" % frame)
                return

            # Here we have all information to decode the status
            Status = MsgData[0:2]
            SEQ = MsgData[2:4]
            PacketType = MsgData[4:8]
            Domoticz.Debug("receivedData - MsgType: %s PacketType: %s" % (MsgType, PacketType))

            # We have receive a Status code in response to a command.
            self.receiveStatusCmd(Status, PacketType, frame)
            # We do not send this message for further processing as it is a pure internal to ack the command.
            return

        elif int(MsgType, 16) in STANDALONE_MESSAGE:  # We receive an async message, just forward it to plugin
            self.F_out(frame)  # for processing
        else:
            self.receiveDataCmd(MsgType)  #
            self.F_out(frame)  # Forward the message to plugin for further processing
        self.checkTOwaitFor()  # Let's take the opportunity to check TimeOut
        return

    def receiveDataCmd(self, MsgType):
        self._data += 1
        Domoticz.Debug("receiveDataCmd - MsgType: %s" % MsgType)
        if len(self._waitForData) != 0:
            if int(MsgType, 16) == self._waitForData[0][0]:
                cmd, pTime = self.nextDataInWait()
                if int(MsgType, 16) != cmd:
                    Domoticz.Log("receiveDataCmd - unexpected message Type: %s Expecting: %04.x" % (MsgType, cmd))
            else:
                Domoticz.Log("receiveDataCmd - unexpected message Type: %s Expecting: %04.x" \
                             % (MsgType, self._waitForData[0][0]))

        Domoticz.Debug("receiveDataCmd   - waitQ: %s dataQ: %s normalQ: %s" \
                       % (len(self._waitForStatus), len(self._waitForData), len(self._normalQueue)))

        if len(self._normalQueue) != 0 \
                and len(self._waitForStatus) == 0 and len(self._waitForData) == 0:
            cmd, datas, timestamps = self.nextCmdtoSend()
            self.sendData(cmd, datas)
        return

    def receiveStatusCmd(self, Status, PacketType, frame):
        self._ack += 1
        if Status != '00':
            self._ackKO += 1
        Domoticz.Debug("receiveStatusCmd - waitQ: %s dataQ: %s normalQ: %s" \
                       % (len(self._waitForStatus), len(self._waitForData), len(self._normalQueue)))
        expectedCommand = self.nextStatusInWait()
        if PacketType == '':
            Domoticz.Debug("receiveStatusCmd - Empty PacketType: %s" % frame)
        if PacketType != '' and int(expectedCommand[0], 16) != int(PacketType, 16):
            Domoticz.Debug("receiveData - sync error : Expecting %s and Received: %s" \
                           % (expectedCommand[0], PacketType))

        if len(self._normalQueue) != 0 \
                and len(self._waitForStatus) == 0 and len(self._waitForData) == 0:
            cmd, datas, timestamps = self.nextCmdtoSend()
            self.sendData(cmd, datas)

        return

    def checkTOwaitFor(self):
        'look at the waitForStatus, and in case of TimeOut delete the entry'
        # Check waitForStatus
        if len(self._waitForStatus) > 0:
            now = int(time.time())
            pCmd, pDatas, pTime = self._waitForStatus[0]
            Domoticz.Debug("checkTOwaitForStatus - %04.x enter at: %s delta: %s" % (int(pCmd, 16), pTime, now - pTime))
            if (now - pTime) > TIMEOUT:
                self._TOstatus += 1
                entry = self.nextStatusInWait()
                Domoticz.Error("waitForStatus - Timeout %s on %04.x " % (now - pTime, int(entry[0], 16)))

        # Check waitForData
        if len(self._waitForData) > 0:
            now = int(time.time())
            pCmd, pTime = self._waitForData[0]
            Domoticz.Debug("checkTOwaitForStatus - %04.xs enter at: %s delta: %s" % (pCmd, pTime, now - pTime))
            if (now - pTime) > TIMEOUT:
                self._TOdata += 1
                entry = self.nextDataInWait()
                Domoticz.Error("waitForData - Timeout %s on %04.x " % (now - pTime, entry[0]))
        return

def ZigateEncode(Data):  # ajoute le transcodage
    Domoticz.Debug("ZigateEncode - Encodind data: " + Data)
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
    Domoticz.Debug("Transcode in: " + str(Data) + "  / out:" + str(Out))
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
