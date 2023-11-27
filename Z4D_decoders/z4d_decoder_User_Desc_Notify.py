from Modules.errorCodes import DisplayStatusCode


def Decode802B(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 802B - User Descriptor Notify, Sequence number: ' + MsgSequenceNumber + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Network address of interest: ' + MsgNetworkAddressInterest)
    
def Decode802C(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]
    MsgLenght = MsgData[8:10]
    MsgMData = MsgData[10:]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 802C - User Descriptor Notify, Sequence number: ' + MsgSequenceNumber + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Network address of interest: ' + MsgNetworkAddressInterest + ' Lenght: ' + MsgLenght + ' Data: ' + MsgMData)
