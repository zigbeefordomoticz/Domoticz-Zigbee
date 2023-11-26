def Decode0110(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0110 - message: %s' % MsgData)
    if len(MsgData) < 24:
        self.log.logging('Input', 'Error', 'Decode0110 - Message too short %s' % MsgData)
        return
    MsgSqn = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgDstEp = MsgData[8:10]
    MsgClusterId = MsgData[10:14]
    MsgDirection = MsgData[14:16]
    MsgManufFlag = MsgData[16:18]
    MsgManufCode = MsgData[18:22]
    nbAttribute = MsgData[22:24]
    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 272)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    idx = 24
    while idx < len(MsgData):
        Attribute = MsgData[idx:idx + 4]
        idx += 4
        DataType = MsgData[idx:idx + 2]
        idx += 2
        lendata = MsgData[idx:idx + 4]
        idx += 4
        DataValue = MsgData[idx:idx + int(lendata, 16) * 2]
        idx += int(lendata, 16) * 2
        self.log.logging('Input', 'Debug', 'Decode0110 - Sqn: %s NwkId: %s Ep: %s Cluster: %s Manuf: %s Attribute: %s Type: %s Value: %s' % (MsgSqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgManufCode, Attribute, DataType, DataValue))