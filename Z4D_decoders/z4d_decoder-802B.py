def Decode802B(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 802B - User Descriptor Notify, Sequence number: ' + MsgSequenceNumber + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Network address of interest: ' + MsgNetworkAddressInterest)