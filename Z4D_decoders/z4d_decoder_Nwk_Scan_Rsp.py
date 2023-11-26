def Decode804A(self, Devices, MsgData, MsgLQI):
    if self.networkenergy:
        self.networkenergy.NwkScanResponse(MsgData)