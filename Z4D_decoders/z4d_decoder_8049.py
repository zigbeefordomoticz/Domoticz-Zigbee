def Decode8049(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8049 - MsgData: %s' % MsgData)
    Status = MsgData[2:4]
    if Status == '00':
        self.log.logging('Input', 'Status', 'Pairing Command correctly exectued')