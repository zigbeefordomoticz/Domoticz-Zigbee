
from Modules.errorCodes import DisplayStatusCode
from Modules.domoMaj import MajDomoDevice

SCENE_LOG = ['Input', 'Scene']

def Decode80A0(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    self.log.logging(SCENE_LOG, 'Log', 'ZigateRead - MsgType 80A0 - View Scene response, Sequence number: ' + MsgSequenceNumber + ' EndPoint: ' + MsgEP + ' ClusterID: ' + MsgClusterID + ' Status: ' + DisplayStatusCode(MsgDataStatus) + ' Group ID: ' + MsgGroupID)
    
    
def _scene_response(self, name, MsgData, has_scene=True):
    """
    Log an Add, Remove, Remove All or Store Scene response, as built by
    Zigbee.zclDecoders.buildframe_scene_response: a failure is worth a Log, as
    the scene is then not on this device.
    """
    MsgEP = MsgData[2:4]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16] if has_scene else None
    MsgSrcAddr = MsgData[16:20] if has_scene else MsgData[14:18]
    self.log.logging(
        SCENE_LOG, 'Debug' if MsgDataStatus == '00' else 'Log',
        '%s Scene response - %s/%s Status: %s Group ID: %s Scene ID: %s' % (
            name, MsgSrcAddr, MsgEP, DisplayStatusCode(MsgDataStatus), MsgGroupID, MsgSceneID),
        MsgSrcAddr)


def Decode80A1(self, Devices, MsgData, MsgLQI):
    _scene_response(self, 'Add', MsgData)


def Decode80A2(self, Devices, MsgData, MsgLQI):
    _scene_response(self, 'Remove', MsgData)


def Decode80A3(self, Devices, MsgData, MsgLQI):
    _scene_response(self, 'Remove All', MsgData, has_scene=False)


def Decode80A4(self, Devices, MsgData, MsgLQI):
    _scene_response(self, 'Store', MsgData)


def Decode80A5(self, Devices, MsgData, MsgLQI):
    MsgSrcAddr = MsgData[10:14]
    MsgPayload = MsgData[16:]
    GroupID = MsgPayload[:4]
    SceneID = MsgPayload[4:6]
    TransitionTime = 0
    if len(MsgPayload) == 10 and MsgPayload[6:10] != 'ffff':
        TransitionTime = int(MsgPayload[6:10], 16) / 10
    self.log.logging(SCENE_LOG, 'Debug', 'Recall Scene: Group ID: %s Scene ID: %s Transition Time: %ss' % (GroupID, SceneID, str(TransitionTime)), MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices or 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    _ModelName = self.ListOfDevices[MsgSrcAddr]['Model']
    if _ModelName == 'Remote switch Wake up Sleep':
        if GroupID == 'fff4':
            MajDomoDevice(self, Devices, MsgSrcAddr, '01', '0008', '00')
        elif GroupID == 'fff5':
            MajDomoDevice(self, Devices, MsgSrcAddr, '01', '0008', '01')
            
def Decode80A6(self, Devices, MsgData, MsgLQI):
    """
    Get Scene Membership response, as built by
    Zigbee.zclDecoders.buildframe_scene_response.

    Capacity is what the device has left, not its table size: 0xfe is "at least
    one more", 0xff is unknown.
    """
    MsgSrcAddr = MsgData[-4:]
    MsgEP = MsgData[2:4]
    MsgDataStatus = MsgData[8:10]
    MsgCapacity = int(MsgData[10:12], 16)
    MsgGroupID = MsgData[12:16]
    MsgSceneCount = int(MsgData[16:18], 16)
    if MsgDataStatus != '00':
        self.log.logging(SCENE_LOG, 'Log', 'Decode80A6 - Scene Membership response - %s/%s Group ID: %s Status: %s' % (
            MsgSrcAddr, MsgEP, MsgGroupID, DisplayStatusCode(MsgDataStatus)), MsgSrcAddr)
        return
    MsgSceneList = MsgData[18:18 + MsgSceneCount * 2]
    MsgScene = [MsgSceneList[idx:idx + 2] for idx in range(0, MsgSceneCount * 2, 2)]
    self.log.logging(SCENE_LOG, 'Debug', 'Decode80A6 - Scene Membership response - %s/%s Group ID: %s Capacity: %s Scene List: %s' % (
        MsgSrcAddr, MsgEP, MsgGroupID, MsgCapacity, MsgScene), MsgSrcAddr)
