def Decode8110(self, Devices, MsgData, MsgLQI):
    if not self.FirmwareVersion:
        return
    MsgSrcAddr = MsgData[2:6]
    MsgSQN = MsgData[:2]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    if len(MsgData) != 24:
        MsgAttrStatus = MsgData[12:14]
        MsgAttrID = None
    elif self.zigbee_communication == 'native' and int(self.FirmwareVersion, 16) < int('31d', 16):
        MsgAttrID = MsgData[12:16]
        MsgAttrStatus = MsgData[16:18]
    else:
        MsgAttrStatus = MsgData[14:16]
        MsgAttrID = None
    Decode8110_raw(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrStatus, MsgAttrID, MsgLQI)