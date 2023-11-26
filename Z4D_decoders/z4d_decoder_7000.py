def Decode7000(self, Devices, MsgData, MsgLQI):
    uSrcAddress = MsgData[:4]
    u8SrcEndpoint = MsgData[4:6]
    u16ClusterId = MsgData[6:10]
    bDirection = MsgData[10:12]
    bDisableDefaultResponse = MsgData[12:14]
    bManufacturerSpecific = MsgData[14:16]
    eFrameType = MsgData[16:18]
    u16ManufacturerCode = MsgData[18:22]
    u8CommandIdentifier = MsgData[22:24]
    u8TransactionSequenceNumber = MsgData[24:26]
    if uSrcAddress not in self.ListOfDevices:
        return
    self.log.logging('Input', 'Debug', 'Decode7000 - Default Response Notification [%s] %s/%s Cluster: %s DefaultReponse: %s ManufSpec: %s ManufCode: %s Command: %s Direction: %s FrameType: %s' % (u8TransactionSequenceNumber, uSrcAddress, u8SrcEndpoint, u16ClusterId, bDisableDefaultResponse, bManufacturerSpecific, u16ManufacturerCode, u8CommandIdentifier, bDirection, eFrameType))
    if bDisableDefaultResponse == '00':
        send_default_response(self, uSrcAddress, u8SrcEndpoint, u16ClusterId, bDirection, bDisableDefaultResponse, bManufacturerSpecific, u16ManufacturerCode, eFrameType, u8CommandIdentifier, u8TransactionSequenceNumber)