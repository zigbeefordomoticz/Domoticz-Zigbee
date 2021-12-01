# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#



from Classes.Transport.zclDecoders import zcl_decoders
from Classes.Transport.zdpDecoders import zdp_decoders
from Modules.zigateConsts import ADDRESS_MODE


def decode8002_and_process(self, frame):

    ProfileId, SrcNwkId, SrcEndPoint, ClusterId, Payload = extract_nwk_infos_from_8002(frame)
    self.logging_8002( 'Debug', "decode8002_and_process NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))

    if SrcNwkId is None:
        return frame

    if ProfileId == "0000":
        frame = zdp_decoders( self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame )
        return frame
    
    if ProfileId == "0104":
        frame = zcl_decoders( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame )
        return frame
    
    return frame
    


def extract_nwk_infos_from_8002(frame):

    MsgType = frame[2:6]
    MsgLength = frame[6:10]
    MsgCRC = frame[10:12]

    if len(frame) < 18:
        return (None, None, None, None, None)

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
            return (None, None, None, None, None)

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
            return (None, None, None, None, None)
    else:
        return (None, None, None, None, None)

    return (ProfileId, SrcNwkId, SrcEndPoint, ClusterId, Payload)


