def Decode8005(self, Devices, MsgData, MsgLQI):
    MsgSourceEP = MsgData[:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgCommandList = MsgData[10:]
    commandLst = [MsgCommandList[idx:idx + 4] for idx in range(0, len(MsgCommandList), 4)]
    self.ControllerData['Device Attributs List'] = commandLst
    self.log.logging('Input', 'Status', 'Command list, EP source: ' + MsgSourceEP + ' ProfileID: ' + MsgProfileID + ' ClusterID: ' + MsgClusterID + ' Command List: ' + str(commandLst))