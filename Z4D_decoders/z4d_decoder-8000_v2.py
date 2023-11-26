def Decode8000_v2(self, Devices, MsgData, MsgLQI):
    if len(MsgData) < 8:
        self.log.logging('Input', 'Log', 'Decode8000 - uncomplete message: %s' % MsgData)
        return
    Status = MsgData[:2]
    sqn_app = MsgData[2:4]
    dsqn_app = int(sqn_app, 16)
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