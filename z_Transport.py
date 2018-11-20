#!/usr/bin/python

import Domoticz
import binascii
import struct
import time
import threading

DELAY = 2

class ZigateTransport(object):
    def __init__(self , transport, serialPort=None, wifiAddress=None, wifiPort=None ):
        Domoticz.Log("Setting Transport object")

        self._connection = None      # connection handle
        self._ReqRcv = bytearray() # on going receive buffer
        self._transp = None    # Transport mode USB or Wifi
        self._serialPort = None # serial port in case of USB
        self._wifiAddress = None # ip address in case of Wifi
        self._wifiPort = None  # wifi port
        if str(transport) == "USB":
            self._transp = "USB"
            self._serialPort = serialPort 
            self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", \
                    Address=self._serialPort, Baud=115200)
        elif str(transport) == "Wifi":
            self._transp = "Wifi"
            self._wifiAddress = wifiAddress
            self._wifiPort = wifiPort
            self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", \
                    Address=self._wifiAddress, Port=self._wifiPort)

        self._highPrioQueue = []     # list if high prioirty commands
        self._normalQueue = []       # list of normal priority commands
        self._waitForStatus = []     # list of command sent and waiting for status 0x8000
        self._waitForData = []      # list of command sent for which status received and waiting for data

        self._crcErrors = 0    # count of crc errors
        self._frameErrors = 0 # count of frames error
        self._sent = 0         # count of sent messages
        self._received = 0     # count of received messages

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

    def openConn(self):
        self._connection.Connect()

    def closeConn(self):
        self._connection.Disconnect()
        self._connection = None

    def reConn(self):
        if self.isConn() != True:
            self.openConn()

    def isConn(self):
        if self._connection == None:
            return False
        else:
            return True

    def _sendData( self, cmd, datas):
        '''
        send data to Zigate via the communication transport
        '''
        if datas == "":
            length = "0000"
        else:
            length = returnlen(4,(str(hex(int(round(len(datas)/2)))).split('x')[-1]))  # by Cortexlegeni 
        if datas == "":
            checksumCmd = getChecksum(cmd,length,"0")
            if len(checksumCmd) == 1:
                strchecksum="0" + str(checksumCmd)
            else:
                strchecksum = checksumCmd
            lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + \
                    str(ZigateEncode(strchecksum)) + "03" 
        else:
            checksumCmd = getChecksum(cmd,length,datas)
            if len(checksumCmd) == 1:
                strchecksum="0" + str(checksumCmd)
            else:
                strchecksum = checksumCmd
            lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + \
                    str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"   
    
        Domoticz.Debug("sendZigateCmd - Command send: " + str(lineinput))
        self._connection.Send(bytes.fromhex(str(lineinput)), DELAY )
        self._sent += 1

    def _receiveData( self, Data):
        Domoticz.Debug("onMessage called on Connection " +str(Data))

        FrameIsKo = 0                    

        self._ReqRcv += Data                # Add the incoming data
        Domoticz.Log("onMessage incoming data : '" + str(binascii.hexlify(self._ReqRcv).decode('utf-8'))+ "'" )

        # Zigate Frames start with 0x01 and finished with 0x03    
        # It happens that we get some 
        while 1 :                    # Loop until we have 0x03
            Zero1=-1
            Zero3=-1
            idx = 0
            for val in self._ReqRcv[0:len(self._ReqRcv)] :
                if Zero1 == - 1 and Zero3  == -1 and val == 1 :    # Do we get a 0x01
                    Zero1 = idx        # we have identify the Frame start

                if Zero1 != -1 and val == 3 :    # If we have already started a Frame and do we get a 0x03
                    Zero3 = idx + 1
                    break            # If we got 0x03, let process the Frame
                idx += 1

            if Zero3 == -1 :            # No 0x03 in the Buffer, let's breat and wait to get more data
                return

            Domoticz.Debug("onMessage Frame : Zero1=" + str(Zero1) + " Zero3=" + str(Zero3) )

            if Zero1 != 0 :
                Domoticz.Debug("onMessage : we have probably lost some datas, zero1 = " + str(Zero1) )

            # uncode the frame
            BinMsg=bytearray()
            iterReqRcv = iter (self._ReqRcv[Zero1:Zero3])

            for iByte in iterReqRcv :            # for each received byte
                if iByte == 2 :                # Coded flag ?
                    iByte = next(iterReqRcv) ^ 16    # then uncode the next value
                BinMsg.append(iByte)            # copy

            self._ReqRcv = self._ReqRcv[Zero3:]                 # What is after 0x03 has to be reworked.

                        # Check length
            Zero1, MsgType, Length, ReceivedChecksum = struct.unpack ('>BHHB', BinMsg[0:6])
            ComputedLength = Length + 7
            ReceveidLength = len(BinMsg)
            Domoticz.Debug("onMessage Frame length : " + str(ComputedLength) + " " + str(ReceveidLength) ) # For testing purpose
            if ComputedLength != ReceveidLength :
                FrameIsKo = 1
                Domoticz.Error("onMessage : Frame size is bad, computed = " + str(ComputedLength) + " received = " + str(ReceveidLength) )

            # Compute checksum
            ComputedChecksum = 0
            for idx, val in enumerate(BinMsg[1:-1]) :
                if idx != 4 :                # Jump the checksum itself
                    ComputedChecksum ^= val
            Domoticz.Debug("onMessage Frame : ComputedChekcum=" + str(ComputedChecksum) + " ReceivedChecksum=" + str(ReceivedChecksum) ) # For testing purpose
            if ComputedChecksum != ReceivedChecksum:
                FrameIsKo = 1
                Domoticz.Error("onMessage : Frame CRC is bad, computed = " + str(ComputedChecksum) + " received = " + str(ReceivedChecksum) )

            AsciiMsg=binascii.hexlify(BinMsg).decode('utf-8')
            if FrameIsKo == 0 :
                self.receiveCompleteFrame( AsciiMsg)

        Domoticz.Log("onMessage Remaining Frame : " + str(binascii.hexlify(self_ReqRcv).decode('utf-8') ))
        return

    def checkCmdTosend( self, cmd, data ):
        ' Check if the Command is not already in the list. Duplicate do not make sense'
    
    def isCmdToSend( self ):
        ' check if there is a Command to send '
    
    def _printSendQueue( self ):
        cnt = 0
        for iter in self._normalQueue:
            Domoticz.Log("normalQueue[%d] = %s " %( cnt, iter[0]))
            cnt += 1

    def _printWaitQueue( self ):
        cnt = 0
        for iter in self._waitForStatus:
            Domoticz.Log("normalQueue[%d] = %s " %( cnt, iter[0]))
            cnt += 1

    def nextCmdtoSend(self ):
        ' return the next Command to send pop'
        ret = self._normalQueue[0]
        del self._normalQueue[0]
        self._printSendQueue()
        return ret
    
    def nextStatusInWait( self ):
        ret = self._waitForStatus[0]
        del self._waitForStatus[0]
        #self._printSendQueue()
        return ret

    def addCmdToWait(self, cmd, data):
        'add a command to the waiting list'
        timestamp = time.time()
        self._waitForStatus.append( ( cmd, data, timestamp) )

    def addCmdToSend(self, cmd, data):
        'add a command to the waiting list'
        timestamp = time.time()
        self._normalQueue.append( ( cmd, data, timestamp) )
        self._printSendQueue()
    
    def sendData(self, cmd, datas):
        # Check if normalQueue is empty. If yes we can send the command straight
        Domoticz.Log("sendData IN - waitForStatus Q: %s" %len(self._waitForStatus))
        Domoticz.Log("sendData IN - addCmdToSend  Q: %s" %len(self._normalQueue))
        if len(self._waitForStatus) == 0:
            self.addCmdToWait( cmd, datas )
            self._sendData( cmd, datas)
        else:
            self.addCmdToSend( cmd, datas )

    def receiveStatusCmd( self, Status, PacketType, frame):
        Domoticz.Log("receiveStatusCmd IN - waitForStatus Q: %s" %len(self._waitForStatus))
        Domoticz.Log("receiveStatusCmd IN - addCmdToSend  Q: %s" %len(self._normalQueue))

        expectedCommand = self.nextStatusInWait()
        Domoticz.Log("received Data - Status for %s received: %s " \
                %( expectedCommand, PacketType))

        if PacketType == '':
            Domoticz.Log("receiveStatusCmd - Empty PacketType: %s" %frame)

        if PacketType != '' and int(expectedCommand[0],16) == int(PacketType,16):
            # we are in sync
            pass
        else:
            Domoticz.Log("receiveData - sync error : Expecting %s and Receveid: %s" \
                    %( expectedCommand[0], PacketType ))

        # Retreive a command to be sent if any
        if len(self._normalQueue) != 0 :
            cmd, datas, timestamps = self.nextCmdtoSend()
            self.sendData( cmd, datas)

        return


    def receiveData( self, Data):
        ''' 
        will return the Frame in the Data if any
        '''
        self._receiveData(Data)


def ZigateEncode(Data):  # ajoute le transcodage
    Domoticz.Debug("ZigateEncode - Encodind data: " + Data)
    Out=""
    Outtmp=""
    Transcode = False
    for c in Data:
        Outtmp+=c
        if len(Outtmp)==2:
            if Outtmp[0] == "1" and Outtmp != "10":
                if Outtmp[1] == "0":
                    Outtmp="0200"
                    Out+=Outtmp
                else:
                    Out+=Outtmp
            elif Outtmp[0] == "0":
                Out+="021" + Outtmp[1]
            else:
                Out+=Outtmp
            Outtmp=""
    Domoticz.Debug("Transcode in: " + str(Data) + "  / out:" + str(Out) )
    return Out

def getChecksum(msgtype,length,datas):
    temp = 0 ^ int(msgtype[0:2],16)
    temp ^= int(msgtype[2:4],16)
    temp ^= int(length[0:2],16)
    temp ^= int(length[2:4],16)
    for i in range(0,len(datas),2):
        temp ^= int(datas[i:i+2],16)
        chk=hex(temp)
    Domoticz.Debug("getChecksum - Checksum: " + str(chk))
    return chk[2:4]

def returnlen( taille , value) :
    while len(value)<taille:
        value="0"+value
    return str(value)


