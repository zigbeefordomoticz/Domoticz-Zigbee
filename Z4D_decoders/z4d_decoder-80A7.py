def Decode80A7(self, Devices, MsgData, MsgLQI):
    """Remote button pressed (LEFT/RIGHT)"""
    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgCmd = MsgData[8:10]
    MsgDirection = MsgData[10:12]
    unkown_ = MsgData[12:18]
    MsgSrcAddr = MsgData[18:22]
    _ModelName = self.ListOfDevices[MsgSrcAddr]['Model']
    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    if self.ListOfDevices[MsgSrcAddr]['Status'] != 'inDB':
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    updLQI(self, MsgSrcAddr, MsgLQI)
    check_duplicate_sqn(self, MsgSrcAddr, MsgEP, MsgClusterId, MsgSQN)
    timeStamped(self, MsgSrcAddr, 32935)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if _ModelName in ('TRADFRI remote control',):
        ikea_remote_control_80A7(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_)
    elif _ModelName in ('Remote Control N2',):
        ikea_remoteN2_control_80A7(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_)
    else:
        self.log.logging('Input', 'Log', 'Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, Direction: %s, %s' % (MsgCmd, MsgDirection, unkown_)