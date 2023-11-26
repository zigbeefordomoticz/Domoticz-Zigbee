def Decode8701(self, Devices, MsgData, MsgLQI):
    MsgLen = len(MsgData)
    self.log.logging('Input', 'Debug', 'Decode8701 - MsgData: %s MsgLen: %s' % (MsgData, MsgLen))
    if MsgLen < 4:
        return
    NwkStatus = MsgData[:2]
    Status = MsgData[2:4]
    MsgSrcAddr = ''
    MsgSrcIEEE = ''
    if MsgLen >= 8:
        MsgSrcAddr = MsgData[4:8]
        if MsgSrcAddr in self.ListOfDevices:
            MsgSrcIEEE = self.ListOfDevices[MsgSrcAddr]['IEEE']
    if NwkStatus != '00':
        self.log.logging('Input', 'Log', 'Decode8701 - Route discovery has been performed for %s, status: %s - %s Nwk Status: %s - %s ' % (MsgSrcAddr, Status, DisplayStatusCode(Status), NwkStatus, DisplayStatusCode(NwkStatus)))
    self.log.logging('Input', 'Debug', 'Decode8701 - Route discovery has been performed for %s %s, status: %s Nwk Status: %s ' % (MsgSrcAddr, MsgSrcIEEE, Status, NwkStatus))