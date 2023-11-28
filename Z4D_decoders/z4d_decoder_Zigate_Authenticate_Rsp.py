def Decode8028(self, Devices, MsgData, MsgLQI):
    MsgGatewayIEEE = MsgData[:16]
    MsgEncryptKey = MsgData[16:32]
    MsgMic = MsgData[32:40]
    MsgNodeIEEE = MsgData[40:56]
    MsgActiveKeySequenceNumber = MsgData[56:58]
    MsgChannel = MsgData[58:60]
    MsgShortPANid = MsgData[60:64]
    MsgExtPANid = MsgData[64:80]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 8028 - Authenticate response, Gateway IEEE: ' + MsgGatewayIEEE + ' Encrypt Key: ' + MsgEncryptKey + ' Mic: ' + MsgMic + ' Node IEEE: ' + MsgNodeIEEE + ' Active Key Sequence number: ' + MsgActiveKeySequenceNumber + ' Channel: ' + MsgChannel + ' Short PAN id: ' + MsgShortPANid + 'Extended PAN id: ' + MsgExtPANid)