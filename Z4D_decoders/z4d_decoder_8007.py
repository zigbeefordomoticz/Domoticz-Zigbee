def Decode8007(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8007 - MsgData: %s' % MsgData)
    Status = MsgData[:2]
    if Status == '00':
        Status = 'STARTUP'
    elif Status == '01' or (Status != '02' and Status == '06'):
        Status = 'RUNNING'
    elif Status == '02':
        Status = 'NFN_START'
    self.ErasePDMDone = True
    self.log.logging('Input', 'Status', "'Factory new' Restart status: %s" % Status)