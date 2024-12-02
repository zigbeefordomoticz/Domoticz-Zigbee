from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL, TYPE_APP_ZDP,
                                             sqn_get_internal_sqn_from_app_sqn,
                                             sqn_get_internal_sqn_from_aps_sqn)
from Modules.errorCodes import DisplayStatusCode
from Modules.tools import (DeviceExist, ReArrangeMacCapaBasedOnModel,
                           checkAndStoreAttributeValue, decodeMacCapa,
                           extract_info_from_8085,
                           get_deviceconf_parameter_value, get_isqn_datastruct,
                           get_list_isqn_attr_datastruct, getSaddrfromIEEE,
                           loggingMessages, lookupForIEEE, mainPoweredDevice,
                           retreive_cmd_payload_from_8002,
                           set_request_phase_datastruct, set_status_datastruct,
                           timeStamped, updLQI, updSQN,
                           zigpy_plugin_sanity_check)
from Modules.domoTools import lastSeenUpdate, timedOutDevice
from Modules.basicOutputs import (getListofAttribute, handle_unknow_device,
                                  send_default_response, setTimeServer)
from Z4D_decoders.z4d_decoder_helpers import set_health_state

def Decode8000_v2(self, Devices, MsgData, MsgLQI):
    if len(MsgData) < 8:
        self.log.logging('Input', 'Log', 'Decode8000 - uncomplete message: %s' % MsgData)
        return
    Status = MsgData[:2]
    sqn_app = MsgData[2:4]
    PacketType = MsgData[4:8]
    type_sqn = sqn_aps = None
    dsqn_aps = 0
    npdu = apdu = None
    if len(MsgData) >= 12:
        type_sqn = MsgData[8:10]
        sqn_aps = MsgData[10:12]
        dsqn_aps = int(sqn_aps, 16)
        if len(MsgData) == 16:
            npdu = MsgData[12:14]
            apdu = MsgData[14:16]
    if self.pluginconf.pluginConf['coordinatorCmd']:
        i_sqn = None
        if PacketType in ('0100', '0120', '0110'):
            i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, sqn_app, TYPE_APP_ZCL)
        dsqn_app = int(sqn_app, 16)
        if i_sqn:
            self.log.logging('Input', 'Log', 'Decod8000 Received         [%s] PacketType:  %s TypeSqn: %s sqn_app: %s/%s sqn_aps: %s/%s Status: [%s] npdu: %s apdu: %s ' % (i_sqn, PacketType, type_sqn, sqn_app, dsqn_app, sqn_aps, dsqn_aps, Status, npdu, apdu))
        else:
            self.log.logging('Input', 'Log', 'Decod8000 Received         [  ] PacketType:  %s TypeSqn: %s sqn_app: %s/%s sqn_aps: %s/%s Status: [%s] npdu: %s apdu: %s ' % (PacketType, type_sqn, sqn_app, dsqn_app, sqn_aps, dsqn_aps, Status, npdu, apdu))
    STATUS_CODE = {'00': 'Success', '01': 'Incorrect Parameters', '02': 'Unhandled Command', '03': 'Command Failed', '04': 'Busy', '05': 'Stack Already Started', '14': 'E_ZCL_ERR_ZBUFFER_FAIL', '15': 'E_ZCL_ERR_ZTRANSMIT_FAIL'}
    if Status in STATUS_CODE:
        Status = STATUS_CODE[Status]
    elif int(Status, 16) >= 128 and int(Status, 16) <= 244:
        Status = 'ZigBee Error Code ' + DisplayStatusCode(Status)
    SPECIFIC_PACKET_TYPE = {'0012': 'Erase Persistent Data cmd status', '0024': 'Start Network status', '0026': 'Remove Device cmd status', '0044': 'request Power Descriptor status'}
    if PacketType in SPECIFIC_PACKET_TYPE:
        self.log.logging('Input', 'Log', SPECIFIC_PACKET_TYPE[PacketType] + Status)
    if PacketType in ('0060', '0061', '0062', '0063', '0064', '0065') and self.groupmgt:
        self.groupmgt.statusGroupRequest(MsgData)
    if MsgData[:2] != '00':
        self.log.logging('Input', 'Error', 'Decode8000 - PacketType: %s TypeSqn: %s sqn_app: %s sqn_aps: %s Status: [%s] ' % (PacketType, type_sqn, sqn_app, sqn_aps, Status))
        if MsgData[:2] not in ('01', '02', '03', '04', '05'):
            self.internalError += 1
    else:
        self.internalError = 0
        
def Decode8011(self, Devices, MsgData, MsgLQI, TransportInfos=None):
    self.log.logging('Input', 'Debug', 'Decode8011 - APS ACK: %s' % MsgData)
    MsgLen = len(MsgData)
    if MsgLen > 6:
        self.log.logging('Input', 'Error', f"Decode8011 - unexpected payload received {MsgData}")
    MsgStatus = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]

    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            self.log.logging('Input', 'Debug', f"Decode8011 - not zigpy_plugin_sanity_check {MsgSrcAddr} {MsgStatus}")
            handle_unknow_device(self, MsgSrcAddr)
        return

    MsgSEQ = MsgData[12:14] if MsgLen > 12 else None
    i_sqn = sqn_get_internal_sqn_from_aps_sqn(self.ControllerLink, MsgSEQ)

    self.log.logging('Input', 'Debug', f"Decode8011 - {MsgSrcAddr} {MsgStatus}")

    if self.pluginconf.pluginConf['coordinatorCmd']:
        if MsgSEQ:
            self.log.logging('Input', 'Log', 'Decod8011 Received [%s] for Nwkid: %s with status: %s e_sqn: 0x%02x/%s' % (i_sqn, MsgSrcAddr, MsgStatus, int(MsgSEQ, 16), int(MsgSEQ, 16)), MsgSrcAddr)
        else:
            self.log.logging('Input', 'Log', 'Decod8011 Received [%s] for Nwkid: %s with status: %s' % (i_sqn, MsgSrcAddr, MsgStatus), MsgSrcAddr)

    if MsgStatus == '00':
        updLQI(self, MsgSrcAddr, MsgLQI)
        timeStamped(self, MsgSrcAddr, 32785)
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
        if 'Health' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Health'] not in ('Live', 'Disabled'):
            self.log.logging('Input', 'Log', "Receive an APS Ack from %s, let's put the device back to Live" % MsgSrcAddr, MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
        return

    _powered = mainPoweredDevice(self, MsgSrcAddr)
    self.log.logging('Input', 'Debug', f"Decode8011 - {MsgSrcAddr} MainPowered: {_powered}")

    if not _powered:
        return

    self.log.logging('Input', 'Debug', f"Decode8011 - Timedout {MsgSrcAddr}")

    timedOutDevice(self, Devices, NwkId=MsgSrcAddr)
    set_health_state(self, MsgSrcAddr, MsgData[8:12], MsgStatus)
    
    
def Decode8012(self, Devices, MsgData, MsgLQI):
    """
    confirms that a data packet sent by the local node has been successfully
    passed down the stack to the MAC layer and has made its first hop towards
    its destination (an acknowledgment has been received from the next hop node).
    """
    return


def Decode8702(self, Devices, MsgData, MsgLQI):
    return
