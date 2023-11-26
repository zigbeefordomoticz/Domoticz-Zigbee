def Decode8048(self, Devices, MsgData, MsgLQI):
    MsgExtAddress = MsgData[:16]
    MsgDataStatus = MsgData[16:18]
    loggingMessages(self, '8048', None, MsgExtAddress, int(MsgLQI, 16), None)
    if MsgExtAddress not in self.IEEE2NWK:
        device_leave_annoucement(self, Devices, MsgExtAddress)
        return
    sAddr = getSaddrfromIEEE(self, MsgExtAddress)
    if sAddr not in self.ListOfDevices:
        return
    timeStamped(self, sAddr, 32840)
    if self.ListOfDevices[sAddr]['Status'] == 'Removed':
        if sAddr in self.ListOfDevices:
            del self.ListOfDevices[sAddr]
            self.log.logging('Input', 'Status', 'Removing Device entry %s from plugin Db' % sAddr)
        if MsgExtAddress in self.IEEE2NWK:
            del self.IEEE2NWK[MsgExtAddress]
            self.log.logging('Input', 'Status', 'Removing Device entry %s from plugin IEEE2NWK' % MsgExtAddress)
    elif self.ListOfDevices[sAddr]['Status'] == 'inDB':
        self.ListOfDevices[sAddr]['Status'] = 'Leave'
        self.ListOfDevices[sAddr]['Heartbeat'] = 0
    elif self.ListOfDevices[sAddr]['Status'] in ('004d', '0043', '8043', '0045', '8045'):
        if MsgExtAddress in self.IEEE2NWK:
            del self.IEEE2NWK[MsgExtAddress]
        del self.ListOfDevices[sAddr]
        self.log.logging('Input', 'Log', 'Removing this not completly provisioned device due to a leave ( %s , %s )' % (sAddr, MsgExtAddress))
    elif self.ListOfDevices[sAddr]['Status'] == 'Leave':
        self.ListOfDevices[sAddr]['Status'] = 'Leave'
        self.ListOfDevices[sAddr]['Heartbeat'] = 0
        self.log.logging('Input', 'Error', "Receiving a leave from %s/%s while device is '%s' status." % (sAddr, MsgExtAddress, self.ListOfDevices[sAddr]['Status']))
    zdevname = ''
    if sAddr in self.ListOfDevices and 'ZDeviceName' in self.ListOfDevices[sAddr]:
        zdevname = self.ListOfDevices[sAddr]['ZDeviceName']
    self.log.logging('Input', 'Status', '%s (%s/%s) sent a Leave indication and will be outside of the network. LQI: %s' % (zdevname, sAddr, MsgExtAddress, int(MsgLQI, 16)))
    device_reset(self, sAddr)
    self.log.logging('Input', 'Status', '%s (%s/%s) cleanup key plugin data informations' % (zdevname, sAddr, MsgExtAddress))
    self.log.logging('Input', 'Debug', 'Leave indication from IEEE: %s , Status: %s ' % (MsgExtAddress, MsgDataStatus), sAddr)
    updLQI(self, sAddr, MsgLQI)