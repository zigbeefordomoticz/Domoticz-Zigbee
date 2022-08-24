# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


from Modules.tools import lookupForIEEE
from Modules.zigateConsts import ADDRESS_MODE

from Zigbee.zclDecoders import zcl_decoders
from Zigbee.zdpDecoders import zdp_decoders


def decode8002_and_process(self, frame):

    ProfileId, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Payload = extract_nwk_infos_from_8002(frame)
    
    self.log.logging("Transport8002", "Debug", "decode8002_and_process ProfileId: %04x %s %s" % (
        int(ProfileId,16), SrcNwkId, frame))
    self.log.logging("Transport8002", "Debug", "decode8002_and_process ProfileID: %04x NwkId: %s Ep: %s Cluster: %s Payload: %s" % (
        int(ProfileId,16), SrcNwkId, SrcEndPoint, ClusterId, Payload))

    if SrcNwkId is None:
        return frame

    if ProfileId == "0000":
        frame = zdp_decoders(self, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Payload, frame)
        self.log.logging("Transport8002", "Debug", "decode8002_and_process return ZDP frame: %s" % frame)
        return frame

    if self.zigbee_communication == "zigpy" and SrcNwkId not in self.ListOfDevices:
        if lookupForIEEE(self, SrcNwkId, reconnect=True):
            return frame
            
        self.log.logging("Transport8002", "Log", "decode8002_and_process unknown NwkId: %s for ZCL frame %s" % (SrcNwkId,frame))
        return None
    
    # Z-Stack doesn't provide Profile Information, so we should assumed that if it is not 0x0000 (ZDP) it is then ZCL
    frame = zcl_decoders(self, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Payload, frame)
    self.log.logging("Transport8002", "Debug", "decode8002_and_process return ZCL frame: %s" % frame)
    return frame


def extract_nwk_infos_from_8002(frame):

    MsgType = frame[2:6]
    MsgLength = frame[6:10]
    MsgCRC = frame[10:12]

    if len(frame) < 18:
        return (None, None, None, None, None, None)

    # Payload
    MsgData = frame[12 : len(frame) - 4]
    LQI = frame[len(frame) - 4 : len(frame) - 2]

    ProfileId = MsgData[2:6]
    ClusterId = MsgData[6:10]
    SrcEndPoint = MsgData[10:12]
    TargetEndPoint = MsgData[12:14]
    SrcAddrMode = MsgData[14:16]

    if int(SrcAddrMode, 16) in [ADDRESS_MODE["short"], ADDRESS_MODE["group"]]:
        SrcNwkId = MsgData[16:20]  # uint16_t
        TargetNwkId = MsgData[20:22]

        if int(TargetNwkId, 16) in [
            ADDRESS_MODE["short"],
            ADDRESS_MODE["group"],
        ]:
            # Short Address
            TargetNwkId = MsgData[22:26]  # uint16_t
            Payload = MsgData[26 : len(MsgData)]

        elif int(TargetNwkId, 16) == ADDRESS_MODE["ieee"]:  # uint32_t
            # IEEE
            TargetNwkId = MsgData[22:38]  # uint32_t
            Payload = MsgData[38 : len(MsgData)]

        else:
            return (None, None, None, None, None, None)

    elif int(SrcAddrMode, 16) == ADDRESS_MODE["ieee"]:
        SrcNwkId = MsgData[16:32]  # uint32_t
        TargetNwkId = MsgData[32:34]

        if int(TargetNwkId, 16) in [
            ADDRESS_MODE["short"],
            ADDRESS_MODE["group"],
        ]:
            TargetNwkId = MsgData[34:38]  # uint16_t
            Payload = MsgData[38 : len(MsgData)]

        elif int(TargetNwkId, 16) == ADDRESS_MODE["ieee"]:
            # IEEE
            TargetNwkId = MsgData[34:40]  # uint32_t
            Payload = MsgData[40 : len(MsgData)]
        else:
            return (None, None, None, None, None, None)
    else:
        return (None, None, None, None, None, None)

    return (ProfileId, SrcNwkId, SrcEndPoint, TargetEndPoint, ClusterId, Payload)
