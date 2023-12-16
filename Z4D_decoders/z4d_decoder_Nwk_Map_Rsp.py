def Decode804E(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode804E - Receive message')
    if self.networkmap:
        self.networkmap.LQIresp(MsgData)