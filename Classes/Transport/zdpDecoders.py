
# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import struct 
from Modules.tools import retreive_cmd_payload_from_8002
from Modules.zigateConsts import ADDRESS_MODE, SIZE_DATA_TYPE


def zdp_decoders( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    self.logging_8002( 'Debug', "zdp_decoders NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))
    
    if ClusterId == "0013":
        return buildframe_device_annoucement( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8004":
        return buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8005":
        return buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    return frame


def buildframe_device_annoucement( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # Device Annoucement
    #    if len(MsgData) > 22:  # Firmware 3.1b
    #        RejoinFlag = MsgData[22:24]
    #
    #    NwkId = MsgData[0:4]
    #    Ieee = MsgData[4:20]
    #    MacCapa = MsgData[20:22]
    # Reception Data indication, Source Address: 1735 Destination Address: fffd ProfilID: 0000 ClusterID: 0013 Message 
    # Payload: 81/3517/a1c786feff9ffd90/8e

    sqn = Payload[0:2]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[2:6], 16)))[0]
    ieee = "%016x" %struct.unpack("Q", struct.pack(">Q", int(Payload[6:32], 16)))[0]
    maccapa = Payload[32:34]
    
    self.logging_8002( 'Debug', "buildframe_device_annoucement sqn: %s nwkid: %s ieee: %s maccapa: %s" %(sqn,nwkid , ieee , maccapa ))
    
    buildPayload = nwkid + ieee + maccapa
    
    newFrame = "01"  # 0:2
    newFrame += "004d"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame



def buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # Active End Point Response
    #    MsgDataSQN = MsgData[0:2]
    #    MsgDataStatus = MsgData[2:4]
    #    MsgDataShAddr = MsgData[4:8]
    #    MsgDataEpCount = MsgData[8:10]
    #
    #    MsgDataEPlist = MsgData[10 : len(MsgData)]

    # Reception Data indication, Source Address: 1735 Destination Address: 0000 ProfilID: 0000 ClusterID: 8005 Message 
    # Payload: 0000/3517/02/01f2
    sqn = Payload[0:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    nbEp = Payload[8:10]
    ep_list = Payload[10:]
    
    self.logging_8002( 'Debug', "buildframe_active_endpoint_response sqn: %s status: %s nwkid: %s nbEp: %s epList: %s" %(
        sqn, status, nwkid , nbEp , ep_list ))
    
    buildPayload = sqn + status + nwkid + nbEp + ep_list
    newFrame = "01"  # 0:2
    newFrame += "004d"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame




def buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # Node Descriptor Response
    #     MsgDataSQN = MsgData[0:2]
    #    # MsgDataStatus = MsgData[2:4]
    #    MsgDataShAddr = MsgData[4:8]
    #    MsgDataLenght = MsgData[8:10]
    #
    #    if int(MsgDataLenght, 16) == 0:
    #        return
    #
    #    MsgDataEp = MsgData[10:12]
    #    MsgDataProfile = MsgData[12:16]
    #    MsgDataDeviceId = MsgData[16:20]
    #    MsgDataBField = MsgData[20:22]
    #    MsgDataInClusterCount = MsgData[22:24]

    # Reception Data indication, Source Address: 1735 Destination Address: 0000 ProfilID: 0000 ClusterID: 8004 Message 
    # Payload: 1b/00/3517/22/   0104 010c 0101 09 0000 0300 0400 0500 0600 0800 0003 0010 7cfc  04 0500 1900 2000 0010

    sqn = Payload[0:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    length = Payload[8:10]
    SimpleDescriptor = Payload[10:]

    ep  = SimpleDescriptor[0:2]
    profileId = "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[2:4], 16)))[0]
    deviceId = "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[4:8], 16)))[0]
    deviceVers = SimpleDescriptor[8:10]
    reserved = SimpleDescriptor[10:12]
    inputCnt = SimpleDescriptor[12:14]

    self.logging_8002( 'Debug', "buildframe_simple_descriptor_response sqn: %s status: %s nwkid: %s " %(
        sqn, status, nwkid ))

    buildPayload = sqn + status + nwkid + length + ep + profileId + deviceId + deviceVers + reserved + inputCnt

    idx = 14
    for x in range(int(inputCnt,16)):
        buildPayload += "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[idx + (4 * x):idx + (4 * x) + 4], 16)))[0]

    idx = 14 + ( 4 * int(inputCnt,16) )
    outputCnt = SimpleDescriptor[idx:idx + 2]
    idx += 2
    for x in range(int(outputCnt,16)):
        buildPayload += "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[idx+(4*x):idx+(4*x)+4], 16)))[0]

    newFrame = "01"  # 0:2
    newFrame += "004d"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame    