def Decode8014(self, Devices, MsgData, MsgLQI):
    Status = MsgData[:2]
    timestamp = int(time.time())
    self.log.logging('Input', 'Debug', 'Decode8014 - Permit Join status: %s' % (Status == '01'), 'ffff')
    if 'Permit' not in self.Ping:
        self.Ping['Permit'] = None
    prev = self.Ping['Permit']
    _to_notify = self.Ping['Permit'] is None or self.permitTojoin['Starttime'] >= timestamp - 240
    if Status == '00':
        if prev != 'Off':
            self.log.logging('Input', 'Status', 'Accepting new Hardware: Disable (Off)')
        self.permitTojoin['Duration'] = 0
        self.Ping['Permit'] = 'Off'
        self.permitTojoin['Starttime'] = timestamp
    elif Status == '01':
        self.Ping['Permit'] = 'On'
        if self.permitTojoin['Duration'] == 0:
            self.permitTojoin['Duration'] = 254
            self.permitTojoin['Starttime'] = timestamp
        if prev != 'On':
            self.log.logging('Input', 'Status', 'Accepting new Hardware: Enable (On)')
    else:
        self.log.logging('Input', 'Error', 'Decode8014 - Unexpected value ' + str(MsgData))
    self.log.logging('Input', 'Debug', "---> self.permitTojoin['Starttime']: %s" % self.permitTojoin['Starttime'], 'ffff')
    self.log.logging('Input', 'Debug', "---> self.permitTojoin['Duration']: %s" % self.permitTojoin['Duration'], 'ffff')
    self.log.logging('Input', 'Debug', '---> Current time                  : %s' % timestamp, 'ffff')
    self.log.logging('Input', 'Debug', "---> self.Ping['Permit']  (prev)   : %s" % prev, 'ffff')
    self.log.logging('Input', 'Debug', "---> self.Ping['Permit']  (new )   : %s" % self.Ping['Permit'], 'ffff')
    self.log.logging('Input', 'Debug', '---> _to_notify                    : %s' % _to_notify, 'ffff')
    self.Ping['TimeStamp'] = int(time.time())
    self.Ping['Status'] = 'Receive'
    self.log.logging('Input', 'Debug', 'Ping - received', 'ffff')