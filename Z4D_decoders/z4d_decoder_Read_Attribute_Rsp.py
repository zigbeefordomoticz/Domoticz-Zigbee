

from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL,
                                             sqn_get_internal_sqn_from_app_sqn)
from Modules.callback import callbackDeviceAwake
from Modules.domoTools import lastSeenUpdate
from Modules.tools import (get_deviceconf_parameter_value, loggingMessages,
                           timeStamped, updLQI)
from Z4D_decoders.z4d_decoder_Read_Report_Attribute_Rsp import \
    scan_attribute_reponse


def Decode8100(self, Devices, MsgData, MsgLQI):
    MsgSQN = MsgData[:2]
    
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    
    MsgSrcAddr = MsgData[2:6]
    
    timeStamped(self, MsgSrcAddr, 33024)
    
    loggingMessages(self, '8100', MsgSrcAddr, None, MsgLQI, MsgSQN)
    
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    
    updLQI(self, MsgSrcAddr, MsgLQI)
    
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    self.statistics._clusterOK += 1
    if MsgClusterId == '0500':
        self.log.logging('Input', 'Debug', 'Read Attributed Request Response on Cluster 0x0500 for %s' % MsgSrcAddr)
        if self.iaszonemgt:
            self.iaszonemgt.IAS_CIE_service_discovery_response(MsgSrcAddr, MsgSrcEp, MsgData)
    
    if get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "NO_READ_ATTRIBUTE_RSP"):
        # Some devices as the Tuya RR400ZB TS0505A-HueSaturation seems to return 00 all the time.
        return
    
    scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, '8100')
    callbackDeviceAwake(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId)
