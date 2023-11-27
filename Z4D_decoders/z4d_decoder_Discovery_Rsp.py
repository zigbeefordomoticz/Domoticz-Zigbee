from Modules.errorCodes import DisplayStatusCode

def Decode804B(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgServerMask = MsgData[4:8]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 804B - System Server Discovery response, Sequence number: ' + MsgSequenceNumber + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Server Mask: ' + MsgServerMask)