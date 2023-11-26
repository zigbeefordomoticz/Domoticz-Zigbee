def Decode8003(self, Devices, MsgData, MsgLQI):
    MsgSourceEP = MsgData[:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:]
    clusterLst = [MsgClusterID[idx:idx + 4] for idx in range(0, len(MsgClusterID), 4)]
    self.ControllerData['Cluster List'] = clusterLst
    self.log.logging('Input', 'Status', 'Device Cluster list, EP source: ' + MsgSourceEP + ' ProfileID: ' + MsgProfileID + ' Cluster List: ' + str(clusterLst))
    
def Decode8004(self, Devices, MsgData, MsgLQI):
    MsgSourceEP = MsgData[:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgAttributList = MsgData[10:]
    attributeLst = [MsgAttributList[idx:idx + 4] for idx in range(0, len(MsgAttributList), 4)]
    self.ControllerData['Device Attributs List'] = attributeLst
    self.log.logging('Input', 'Status', 'Device Attribut list, EP source: ' + MsgSourceEP + ' ProfileID: ' + MsgProfileID + ' ClusterID: ' + MsgClusterID + ' Attribut List: ' + str(attributeLst))
    
def Decode8005(self, Devices, MsgData, MsgLQI):
    MsgSourceEP = MsgData[:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgCommandList = MsgData[10:]
    commandLst = [MsgCommandList[idx:idx + 4] for idx in range(0, len(MsgCommandList), 4)]
    self.ControllerData['Device Attributs List'] = commandLst
    self.log.logging('Input', 'Status', 'Command list, EP source: ' + MsgSourceEP + ' ProfileID: ' + MsgProfileID + ' ClusterID: ' + MsgClusterID + ' Command List: ' + str(commandLst))