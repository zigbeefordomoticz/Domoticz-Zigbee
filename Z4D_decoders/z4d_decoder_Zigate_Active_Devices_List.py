from Modules.tools import DeviceExist

def Decode8015(self, Devices, MsgData, MsgLQI):
    numberofdev = len(MsgData)
    self.log.logging('Input', 'Status', 'Number of devices recently active in Coordinator = %s' % str(round(numberofdev / 26)))
    for idx in range(0, len(MsgData), 26):
        saddr = MsgData[idx + 2:idx + 6]
        ieee = MsgData[idx + 6:idx + 22]
        if int(ieee, 16) == 0:
            continue
        DevID = MsgData[idx:idx + 2]
        power = MsgData[idx + 22:idx + 24]
        rssi = MsgData[idx + 24:idx + 26]
        if saddr == '0000':
            continue
        if DeviceExist(self, Devices, saddr, ieee):
            nickName = modelName = ''
            if 'ZDeviceName' in self.ListOfDevices[saddr] and self.ListOfDevices[saddr]['ZDeviceName'] != {}:
                nickName = '( ' + self.ListOfDevices[saddr]['ZDeviceName'] + ' ) '
            if 'Model' in self.ListOfDevices[saddr] and self.ListOfDevices[saddr]['Model'] != {}:
                modelName = self.ListOfDevices[saddr]['Model']
            self.log.logging('Input', 'Status', '[%02d] DevID: %s Network addr: %s IEEE: %s LQI: %03d power: %s Model: %s %s' % (round(idx / 26), DevID, saddr, ieee, int(rssi, 16), power, modelName, nickName))
            self.ListOfDevices[saddr]['LQI'] = int(rssi, 16) if rssi != '00' else 0
            self.log.logging('Input', 'Debug', 'Decode8015: LQI set to %s / %s for %s' % (self.ListOfDevices[saddr]['LQI'], str(int(rssi, 16)), saddr))
        else:
            self.log.logging('Input', 'Status', '[%02d] DevID: %s Network addr: %s IEEE: %s LQI: %03d power: %s not found in plugin database!' % (round(idx / 26), DevID, saddr, ieee, int(rssi, 16), power))
    self.log.logging('Input', 'Debug', 'Decode8015 - IEEE2NWK      : ' + str(self.IEEE2NWK))