
import Domoticz
import binascii
import struct

DELAY = 1   # 1s delay when sending data

class ZigateTransport:

    def __init__(self , transport, serialPort=None, wifiAddress=None, wifiPort=None ):
        Domoticz.Log("Setting Transport object")

        self.__conn = None      # connection handle
        self._highPrioQueue = None     # list if high prioirty commands
        self._normalQueue = None       # list of normal priority commands
        self._waitForStatus = None     # list of command sent and waiting for status 0x8000
        self._waitForData = None      # list of command sent for which status received and waiting for data

        self.__transp = None    # Transport mode USB or Wifi
        self.__serialPort = None # serial port in case of USB
        self.__wifiAddress = None # ip address in case of Wifi
        self.__wifiPort = None  # wifi port
        self.__crcErrors = 0    # count of crc errors
        self.__framesErrors = 0 # count of frames error
        self.__sent = 0         # count of sent messages
        self.__received = 0     # count of received messages
        self.__ReqRcv = bytearray() # on going receive buffer

        if str(transport) == "USB":
            self.__transp = "USB"
            self.__serialPort = serialPort 
        elif str(transport) == "Wifi":
            self.__transp = "Wifi"
            self.__wifiAddress = wifiAddress
            self.__wifiPort = wifiPort
        
        return


    def crcErrors(self):
        ' return the number of crc Errors '
        return self.__crcErrors

    def frameErrors(self):
        ' return the number of frame errors'
        return self.__framesErrors

    def sent( self):
        ' return he number of sent messages'
        return self.__sent

    def received( self):
        ' return the number of received messages'
        return self.__received

    def openConn( self ):
        if self.__transp == "USB":
            Domoticz.Log("USB Connection : %s " %( self.__serialPort))
            self.__conn  = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=self.__serialPort, Baud=115200)
            self.__conn.Connect()
        elif self.__transp == "Wifi":
            Domoticz.Log("Wifi Connection : %s:%s " %( self.__wifiAddress, self.__wifiPort))
            self.__conn = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=self.__wifiAddress, Port=self.__wifiPort)
            self.__conn.Connect()
        return self.__conn

    def closeConn( self ):
        self.__conn.Disconnect()
        self.__conn = None
        return

    def isConn( self ):
        if self.__conn is None:
            return False
        else:
            return True

    def __sendData( self, cmd, datas):
        '''
        send data to Zigate via the communication transport
        '''
        if datas == "":
            length="0000"
        else:
            length = returnlen(4,(str(hex(int(round(len(datas)/2)))).split('x')[-1]))  # by Cortexlegeni 
            Domoticz.Debug("sendZigateCmd - length is: " + str(length) )
        if datas =="":
            checksumCmd = getChecksum(cmd,length,"0")
            if len(checksumCmd)==1:
                strchecksum="0" + str(checksumCmd)
            else:
                strchecksum = checksumCmd
            lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + "03" 
        else:
            checksumCmd = getChecksum(cmd,length,datas)
            if len(checksumCmd)==1:
                strchecksum="0" + str(checksumCmd)
            else:
                strchecksum = checksumCmd
            lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"   
        Domoticz.Debug("sendZigateCmd - Command send: " + str(lineinput))
    
        if self.__conn:
            self.__conn.Send(bytes.fromhex(str(lineinput)), DELAY )
            self.__sent += 1

    def __receiveData( self, Data):
        FrameIsKo = 0                    
        self.__ReqRcv += Data                # Add the incoming data
        Domoticz.Debug("onMessage incoming data : '" + str(binascii.hexlify(self.__ReqRcv).decode('utf-8'))+ "'" )
        # Zigate Frames start with 0x01 and finished with 0x03    
        # It happens that we get some 
        while 1 :                                                  # Loop until we have 0x03
            Zero1=-1
            Zero3=-1
            idx = 0
            for val in self.__ReqRcv[0:len(self.__ReqRcv)] :
                if Zero1 == - 1 and Zero3  == -1 and val == 1 :    # Do we get a 0x01
                    Zero1 = idx                  # we have identify the Frame start
                if Zero1 != -1 and val == 3 :    # If we have already started a Frame and do we get a 0x03
                    Zero3 = idx + 1
                    break                        # If we got 0x03, let process the Frame
                idx += 1
            if Zero3 == -1 :                     # No 0x03 in the Buffer, let's breat and wait to get more data
                return
            Domoticz.Debug("onMessage Frame : Zero1=" + str(Zero1) + " Zero3=" + str(Zero3) )
            if Zero1 != 0 :
                Domoticz.Log("onMessage : we have probably lost some datas, zero1 = " + str(Zero1) )
            # uncode the frame
            BinMsg=bytearray()
            iterReqRcv = iter (self.__ReqRcv[Zero1:Zero3])
            for iByte in iterReqRcv:           # for each received byte
                if iByte == 2 :                # Coded flag ?
                    iByte = next(iterReqRcv) ^ 16    # then uncode the next value
                BinMsg.append(iByte)           # copy
            self.__ReqRcv = self.__ReqRcv[Zero3:]        # What is after 0x03 has to be reworked.
            # Check length
            Zero1, MsgType, Length, ReceivedChecksum = struct.unpack ('>BHHB', BinMsg[0:6])
            ComputedLength = Length + 7
            ReceveidLength = len(BinMsg)
            Domoticz.Debug("onMessage Frame length : " + str(ComputedLength) + " " + str(ReceveidLength) ) # For testing purpose
            if ComputedLength != ReceveidLength :
                FrameIsKo = 1
                self.__frameErrors += 1
                Domoticz.Error("onMessage : Frame size is bad, computed = " + str(ComputedLength) + " received = " + str(ReceveidLength) )
            # Compute checksum
            ComputedChecksum = 0
            for idx, val in enumerate(BinMsg[1:-1]) :
                if idx != 4 :                # Jump the checksum itself
                    ComputedChecksum ^= val
            Domoticz.Debug("onMessage Frame : ComputedChekcum=" + str(ComputedChecksum) + " ReceivedChecksum=" + str(ReceivedChecksum) ) # For testing purpose
            if ComputedChecksum != ReceivedChecksum:
                FrameIsKo = 1
                self.__crcErrors += 1
                Domoticz.Error("onMessage : Frame CRC is bad, computed = " + str(ComputedChecksum) + " received = " + str(ReceivedChecksum) )
            AsciiMsg=binascii.hexlify(BinMsg).decode('utf-8')
            if FrameIsKo == 0 :
                self.__received += 1
                return AsciiMsg
        Domoticz.Debug("onMessage Remaining Frame : " + str(binascii.hexlify(self.__ReqRcv).decode('utf-8') ))
        return


    def sendData(self, cmd, datas):
        self.__sendData( cmd, datas)
        return

    def receiveData( self, Data):
        ''' 
        will return the Frame in the Data if any
        '''

        frame = self.__receiveData(Data)
        if frame == None or frame == '':
            return ''

        # Let's check if that Frame is in response to a Commande
        MsgType=frame[2:6]
        MsgLength=frame[6:10]
        MsgCRC=frame[10:12]

        if MsgType != "8000":
            # It is not a Status Type, so let(s return the frame back for processing
            return frame

        # We have receive a Status code in response to a command.
        Msgframe=frame[12:len(frame)-4]
        Status=Msgframe[0:2]
        SEQ=Msgframe[2:4]
        PacketType=Msgframe[4:8]

        return frame


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

