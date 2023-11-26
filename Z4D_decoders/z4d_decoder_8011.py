def Decode8011(self, Devices, MsgData, MsgLQI, TransportInfos=None):
    self.log.logging('Input', 'Debug2', 'Decode8011 - APS ACK: %s' % MsgData)
    MsgLen = len(MsgData)
    MsgStatus = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSEQ = MsgData[12:14] if MsgLen > 12 else None
    i_sqn = sqn_get_internal_sqn_from_aps_sqn(self.ControllerLink, MsgSEQ)
    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    updLQI(self, MsgSrcAddr, MsgLQI)
    _powered = mainPoweredDevice(self, MsgSrcAddr)
    if self.pluginconf.pluginConf['coordinatorCmd']:
        if MsgSEQ:
            self.log.logging('Input', 'Log', 'Decod8011 Received [%s] for Nwkid: %s with status: %s e_sqn: 0x%02x/%s' % (i_sqn, MsgSrcAddr, MsgStatus, int(MsgSEQ, 16), int(MsgSEQ, 16)), MsgSrcAddr)
        else:
            self.log.logging('Input', 'Log', 'Decod8011 Received [%s] for Nwkid: %s with status: %s' % (i_sqn, MsgSrcAddr, MsgStatus), MsgSrcAddr)
    if MsgStatus == '00':
        timeStamped(self, MsgSrcAddr, 32785)
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
        if 'Health' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Health'] not in ('Live', 'Disabled'):
            self.log.logging('Input', 'Log', "Receive an APS Ack from %s, let's put the device back to Live" % MsgSrcAddr, MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
        return
    if not _powered:
        return
    timedOutDevice(self, Devices, NwkId=MsgSrcAddr)
    set_health_state(self, MsgSrcAddr, MsgData[8:12], MsgStatus)