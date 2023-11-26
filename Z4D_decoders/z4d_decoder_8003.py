def Decode8003(self, Devices, MsgData, MsgLQI):
    MsgSourceEP = MsgData[:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:]
    clusterLst = [MsgClusterID[idx:idx + 4] for idx in range(0, len(MsgClusterID), 4)]
    self.ControllerData['Cluster List'] = clusterLst
    self.log.logging('Input', 'Status', 'Device Cluster list, EP source: ' + MsgSourceEP + ' ProfileID: ' + MsgProfileID + ' Cluster List: ' + str(clusterLst))