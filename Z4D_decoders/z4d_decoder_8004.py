def Decode8004(self, Devices, MsgData, MsgLQI):
    MsgSourceEP = MsgData[:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgAttributList = MsgData[10:]
    attributeLst = [MsgAttributList[idx:idx + 4] for idx in range(0, len(MsgAttributList), 4)]
    self.ControllerData['Device Attributs List'] = attributeLst
    self.log.logging('Input', 'Status', 'Device Attribut list, EP source: ' + MsgSourceEP + ' ProfileID: ' + MsgProfileID + ' ClusterID: ' + MsgClusterID + ' Attribut List: ' + str(attributeLst))