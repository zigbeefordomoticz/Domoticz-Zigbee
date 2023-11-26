def Decode8024(self, Devices, MsgData, MsgLQI):
    MsgLen = len(MsgData)
    MsgDataStatus = MsgData[:2]
    self.log.logging('Input', 'Log', 'Decode8024: Status: %s' % MsgDataStatus)
    if MsgDataStatus == '00':
        self.log.logging('Input', 'Status', 'Start Network - Success')
        Status = 'Success'
    elif MsgDataStatus == '01':
        self.log.logging('Input', 'Status', 'Start Network - Formed new network')
        Status = 'Success'
    elif MsgDataStatus == '02':
        self.log.logging('Input', 'Status', 'Start Network: Error invalid parameter.')
        Status = 'Start Network: Error invalid parameter.'
    elif MsgDataStatus == '04':
        self.log.logging('Input', 'Status', 'Start Network: Node is on network. Coordinator is already in network so network is already formed')
        Status = 'Start Network: Node is on network. Coordinator is already in network so network is already formed'
    elif MsgDataStatus == '06':
        self.log.logging('Input', 'Status', 'Start Network: Commissioning in progress. If network forming is already in progress')
        Status = 'Start Network: Commissioning in progress. If network forming is already in progress'
    else:
        Status = DisplayStatusCode(MsgDataStatus)
        self.log.logging('Input', 'Log', 'Start Network: Network joined / formed Status: %s' % MsgDataStatus)
    if MsgLen != 24:
        self.log.logging('Input', 'Debug', 'Decode8024 - uncomplete frame, MsgData: %s, Len: %s out of 24, data received: >%s<' % (MsgData, MsgLen, MsgData))
        return
    MsgShortAddress = MsgData[2:6]
    MsgExtendedAddress = MsgData[6:22]
    MsgChannel = MsgData[22:24]
    if MsgExtendedAddress != '' and MsgShortAddress != '' and (MsgShortAddress == '0000'):
        if 'startZigateNeeded' not in self.ControllerData and (not self.startZigateNeeded) and (str(int(MsgChannel, 16)) != self.pluginconf.pluginConf['channel']):
            self.log.logging('Input', 'Status', 'Updating Channel in Plugin Configuration from: %s to: %s' % (self.pluginconf.pluginConf['channel'], int(MsgChannel, 16)))
            self.pluginconf.pluginConf['channel'] = str(int(MsgChannel, 16))
            self.pluginconf.write_Settings()
        self.currentChannel = int(MsgChannel, 16)
        self.ControllerIEEE = MsgExtendedAddress
        self.ControllerNWKID = MsgShortAddress
        self.pluginParameters['CoordinatorIEEE'] = MsgExtendedAddress
        if self.iaszonemgt:
            self.iaszonemgt.setZigateIEEE(MsgExtendedAddress)
        if self.groupmgt:
            self.groupmgt.updateZigateIEEE(MsgExtendedAddress)
        self.ControllerData['IEEE'] = MsgExtendedAddress
        self.ControllerData['Short Address'] = MsgShortAddress
        self.ControllerData['Channel'] = int(MsgChannel, 16)
        self.log.logging('Input', 'Status', 'Coordinator details IEEE: %s, NetworkID: %s, Channel: %s, Status: %s: %s' % (MsgExtendedAddress, MsgShortAddress, int(MsgChannel, 16), MsgDataStatus, Status))
    else:
        self.log.logging('Input', 'Error', 'Coordinator initialisation failed IEEE: %s, Nwkid: %s, Channel: %s' % (MsgExtendedAddress, MsgShortAddress, MsgChannel))