
from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL,
                                             sqn_get_internal_sqn_from_app_sqn)
from Modules.domoTools import lastSeenUpdate
from Modules.tools import (get_isqn_datastruct, get_list_isqn_attr_datastruct,
                           set_request_phase_datastruct, set_status_datastruct,
                           timeStamped, updLQI, updSQN)


def Decode8110(self, Devices, MsgData, MsgLQI):
    if not self.FirmwareVersion:
        return
    MsgSrcAddr = MsgData[2:6]
    MsgSQN = MsgData[:2]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    if len(MsgData) != 24:
        MsgAttrStatus = MsgData[12:14]
        MsgAttrID = None
    elif self.zigbee_communication == 'native' and int(self.FirmwareVersion, 16) < int('31d', 16):
        MsgAttrID = MsgData[12:16]
        MsgAttrStatus = MsgData[16:18]
    else:
        MsgAttrStatus = MsgData[14:16]
        MsgAttrID = None
    Decode8110_raw(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrStatus, MsgAttrID, MsgLQI)
    
    
def Decode8110_raw(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrStatus, MsgAttrID, MsgLQI):
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.log.logging('Input', 'Debug', 'Decode8110 - WriteAttributeResponse - MsgSQN: %s,  MsgSrcAddr: %s, MsgSrcEp: %s, MsgClusterId: %s MsgAttrID: %s Status: %s' % (MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus), MsgSrcAddr)
    timeStamped(self, MsgSrcAddr, 33040)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if (self.zigbee_communication != 'native' or (self.FirmwareVersion and int(self.FirmwareVersion, 16) >= int('31d', 16))) and MsgAttrID:
        set_status_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus)
        set_request_phase_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, 'fullfilled')
        if MsgAttrStatus != '00':
            self.log.logging('Input', 'Log', 'Decode8110 - Write Attribute Respons response - ClusterID: %s/%s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s' % (MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, MsgAttrStatus), MsgSrcAddr)
        return
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.log.logging('Input', 'Debug', '------- - i_sqn: %0s e_sqn: %s' % (i_sqn, MsgSQN))
    for matchAttributeId in list(get_list_isqn_attr_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId)):
        if get_isqn_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId) != i_sqn:
            continue
        self.log.logging('Input', 'Debug', '------- - Sqn matches for Attribute: %s' % matchAttributeId)
        set_status_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId, MsgAttrStatus)
        set_request_phase_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId, 'fullfilled')
        if MsgAttrStatus != '00':
            self.log.logging('Input', 'Debug', 'Decode8110 - Write Attribute Response response - ClusterID: %s/%s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s' % (MsgClusterId, matchAttributeId, MsgSrcAddr, MsgSrcEp, MsgAttrStatus), MsgSrcAddr)
    if MsgClusterId == '0500':
        self.iaszonemgt.IAS_CIE_write_response(MsgSrcAddr, MsgSrcEp, MsgAttrStatus)
