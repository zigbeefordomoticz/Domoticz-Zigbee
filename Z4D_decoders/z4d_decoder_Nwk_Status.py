def Decode8009(self, Devices, MsgData, MsgLQI):
    addr = MsgData[:4]
    extaddr = MsgData[4:20]
    PanID = MsgData[20:24]
    extPanID = MsgData[24:40]
    Channel = MsgData[40:42]
    self.log.logging('Input', 'Debug', 'Decode8009: Network state - Address:' + addr + ' extaddr:' + extaddr + ' PanID: ' + PanID + ' Channel: ' + str(int(Channel, 16)))
    if '0000' in self.ListOfDevices and 'CheckChannel' in self.ListOfDevices['0000'] and (self.ListOfDevices['0000']['CheckChannel'] != 0):
        if self.ListOfDevices['0000']['CheckChannel'] == int(Channel, 16):
            del self.ListOfDevices['0000']['CheckChannel']
    if self.ControllerIEEE != extaddr:
        self.adminWidgets.updateNotificationWidget(Devices, 'Coordinator IEEE: %s' % extaddr)
    self.pluginParameters['CoordinatorIEEE'] = extaddr
    self.ControllerIEEE = extaddr
    self.ControllerNWKID = addr
    if self.ControllerNWKID != '0000':
        self.log.logging('Input', 'Error', 'Coordinator not correctly initialized')
        return
    if extaddr not in self.IEEE2NWK or self.IEEE2NWK[extaddr] != addr or addr not in self.ListOfDevices or (extaddr != self.ListOfDevices[addr]['IEEE']):
        initLODZigate(self, addr, extaddr)
    if self.currentChannel != int(Channel, 16):
        self.adminWidgets.updateNotificationWidget(Devices, 'Coordinator Channel: %s' % str(int(Channel, 16)))
    if 'startZigateNeeded' not in self.ControllerData and (not self.startZigateNeeded) and (str(int(Channel, 16)) != self.pluginconf.pluginConf['channel']):
        self.log.logging('Input', 'Status', 'Updating Channel in Plugin Configuration from: %s to: %s' % (self.pluginconf.pluginConf['channel'], int(Channel, 16)))
        self.pluginconf.pluginConf['channel'] = str(int(Channel, 16))
        self.pluginconf.write_Settings()
    self.currentChannel = int(Channel, 16)
    if self.iaszonemgt:
        self.iaszonemgt.setZigateIEEE(extaddr)
    if self.groupmgt:
        self.groupmgt.updateZigateIEEE(extaddr)
    if self.webserver:
        self.webserver.setZigateIEEE(extaddr)
    self.log.logging('Input', 'Status', 'Zigbee Coordinator ieee: %s , short addr: %s' % (self.ControllerIEEE, self.ControllerNWKID))
    if self.zigbee_communication == 'zigpy':
        self.ErasePDMDone = True
    if str(PanID) == '0':
        self.log.logging('Input', 'Status', 'Network state DOWN ! ')
        self.adminWidgets.updateNotificationWidget(Devices, 'Network down PanID = 0')
        self.adminWidgets.updateStatusWidget(Devices, 'No Connection')
    else:
        self.log.logging('Input', 'Status', 'Network state UP, PANID: %s extPANID: 0x%s Channel: %s' % (PanID, extPanID, int(Channel, 16)))
    self.ControllerData['IEEE'] = extaddr
    self.ControllerData['Short Address'] = addr
    self.ControllerData['Channel'] = int(Channel, 16)
    self.ControllerData['PANID'] = PanID
    self.ControllerData['Extended PANID'] = extPanID
    self.pluginParameters['CoordinatorIEEE'] = extaddr
    
    
    
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
