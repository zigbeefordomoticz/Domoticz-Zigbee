def Decode8034(self, Devices, MsgData, MsgLQI):
    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]
    MsgXMLTag = MsgData[10:12]
    MsgCountField = MsgData[12:14]
    MsgFieldValues = MsgData[14:]
    self.log.logging('Input', 'Log', 'Decode8034 - Complex Descriptor for: %s xmlTag: %s fieldCount: %s fieldValue: %s, Status: %s' % (MsgNetworkAddressInterest, MsgXMLTag, MsgCountField, MsgFieldValues, MsgDataStatus))