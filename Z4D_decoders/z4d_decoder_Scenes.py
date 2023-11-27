
from Modules.errorCodes import DisplayStatusCode
from Modules.domoMaj import MajDomoDevice

def Decode80A0(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 80A0 - View Scene response, Sequence number: ' + MsgSequenceNumber + ' EndPoint: ' + MsgEP + ' ClusterID: ' + MsgClusterID + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Group ID: ' + MsgGroupID)
    
    
def Decode80A1(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 80A1 - Add Scene response, Sequence number: ' + MsgSequenceNumber + ' EndPoint: ' + MsgEP + ' ClusterID: ' + MsgClusterID + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Group ID: ' + MsgGroupID + ' Scene ID: ' + MsgSceneID)
    
    
def Decode80A2(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 80A2 - Remove Scene response, Sequence number: ' + MsgSequenceNumber + ' EndPoint: ' + MsgEP + ' ClusterID: ' + MsgClusterID + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Group ID: ' + MsgGroupID + ' Scene ID: ' + MsgSceneID)
    
    
def Decode80A3(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 80A3 - Remove All Scene response, Sequence number: ' + MsgSequenceNumber + ' EndPoint: ' + MsgEP + ' ClusterID: ' + MsgClusterID + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Group ID: ' + MsgGroupID)
    
    
def Decode80A4(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16]
    self.log.logging('Input', 'Log', 'ZigateRead - MsgType 80A4 - Store Scene response, Sequence number: ' + MsgSequenceNumber + ' EndPoint: ' + MsgEP + ' ClusterID: ' + MsgClusterID + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Group ID: ' + MsgGroupID + ' Scene ID: ' + MsgSceneID)
    

def Decode80A5(self, Devices, MsgData, MsgLQI):
    MsgSrcAddr = MsgData[10:14]
    MsgPayload = MsgData[16:]
    GroupID = MsgPayload[:4]
    SceneID = MsgPayload[4:6]
    TransitionTime = 0
    if len(MsgPayload) == 10 and MsgPayload[6:10] != 'ffff':
        TransitionTime = int(MsgPayload[6:10], 16) / 10
    self.log.logging('Input', 'Debug', 'Recall Scene: Group ID: %s Scene ID: %s Transition Time: %ss' % (GroupID, SceneID, str(TransitionTime)), MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices or 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    _ModelName = self.ListOfDevices[MsgSrcAddr]['Model']
    if _ModelName == 'Remote switch Wake up Sleep':
        if GroupID == 'fff4':
            MajDomoDevice(self, Devices, MsgSrcAddr, '01', '0008', '00')
        elif GroupID == 'fff5':
            MajDomoDevice(self, Devices, MsgSrcAddr, '01', '0008', '01')
            
def Decode80A6(self, Devices, MsgData, MsgLQI):
    MsgSrcAddr = MsgData[len(MsgData) - 4:]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgCapacity = int(MsgData[10:12], 16)
    MsgGroupID = MsgData[12:16]
    MsgSceneCount = int(MsgData[16:18], 16)
    self.log.logging('Input', 'Log', 'Decode80A6 - Scene Membership response - MsgSrcAddr: %s MsgEP: %s MsgGroupID: %s MsgClusterID: %s MsgDataStatus: %s MsgCapacity: %s MsgSceneCount: %s' % (MsgSrcAddr, MsgEP, MsgGroupID, MsgClusterID, MsgDataStatus, MsgCapacity, MsgSceneCount))
    if MsgDataStatus != '00':
        self.log.logging('Input', 'Log', 'Decode80A6 - Scene Membership response - MsgSrcAddr: %s MsgEP: %s MsgClusterID: %s MsgDataStatus: %s' % (MsgSrcAddr, MsgEP, MsgClusterID, MsgDataStatus))
        return
    if MsgSceneCount > MsgCapacity:
        self.log.logging('Input', 'Log', 'Decode80A6 - Scene Membership response MsgSceneCount %s > MsgCapacity %s' % (MsgSceneCount, MsgCapacity))
        return
    MsgSceneList = MsgData[18:18 + MsgSceneCount * 2]
    if len(MsgData) > 18 + MsgSceneCount * 2:
        MsgSrcAddr = MsgData[18 + MsgSceneCount * 2:18 + MsgSceneCount * 2 + 4]
    MsgScene = []
    for idx in range(0, MsgSceneCount, 2):
        scene = MsgSceneList[idx:idx + 2]
        if scene not in MsgScene:
            MsgScene.append(scene)
    self.log.logging('Input', 'Log', '           - Scene List: %s' % str(MsgScene))