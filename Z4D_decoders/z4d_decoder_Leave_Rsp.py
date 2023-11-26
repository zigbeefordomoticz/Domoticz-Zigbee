def Decode8047(self, Devices, MsgData, MsgLQI):
    MsgDataStatus = MsgData[2:4]
    self.log.logging('Input', 'Status', 'Decode8047 - Leave response, LQI: %s Status: %s - %s' % (int(MsgLQI, 16), MsgDataStatus, DisplayStatusCode(MsgDataStatus)))