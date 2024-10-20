from Modules.basicOutputs import handle_unknow_device
from Modules.domoTools import lastSeenUpdate
from Modules.tools import (timeStamped, updLQI, updSQN,
                           zigpy_plugin_sanity_check)


def Decode8120(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8120 - Configure reporting response: %s' % MsgData)
    if len(MsgData) < 14:
        self.log.logging('Input', 'Error', 'Decode8120 - uncomplet message %s ' % MsgData)
        return
    MsgSQN = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    if MsgSrcAddr not in self.ListOfDevices:
        self.log.logging('Input', 'Error', 'Decode8120 - receiving Configure reporting response from unknown %s' % MsgSrcAddr)
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    timeStamped(self, MsgSrcAddr, 33056)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    if len(MsgData) == 14:
        MsgStatus = MsgData[12:14]
        Decode8120_attribute(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, None, MsgStatus)
    else:
        idx = 12
        while idx < len(MsgData):
            MsgAttributeId = MsgData[idx:idx + 4]
            idx += 4
            MsgStatus = MsgData[idx:idx + 2]
            idx += 2
            Decode8120_attribute(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus)
            
def Decode8122(self, Devices, MsgData, MsgLQI):
    if self.configureReporting:
        self.configureReporting.read_report_configure_response(MsgData, MsgLQI)
    
def Decode8120_attribute(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus):
    self.log.logging('Input', 'Debug', 'Decode8120 --> SQN: [%s], SrcAddr: %s, SrcEP: %s, ClusterID: %s, Attribute: %s Status: %s' % (MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus), MsgSrcAddr)
    if self.configureReporting:
        self.configureReporting.read_configure_reporting_response(MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus)