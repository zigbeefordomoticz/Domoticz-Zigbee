def Decode8806(self, Devices, MsgData, MsgLQI):
    ATTENUATION_dBm = {'JN516x': {0: 0, 52: -9, 40: -20, 32: -32}, 'JN516x M05': {0: 9.5, 52: -3, 40: -15, 31: -26}}
    self.log.logging('Input', 'Debug', 'Decode8806 - MsgData: %s' % MsgData)
    TxPower = MsgData[:2]
    self.ControllerData['Tx-Power'] = TxPower
    if int(TxPower, 16) in ATTENUATION_dBm['JN516x']:
        self.ControllerData['Tx-Attenuation'] = ATTENUATION_dBm['JN516x'][int(TxPower, 16)]
        self.log.logging('Input', 'Status', 'TxPower Attenuation: %s dBm' % ATTENUATION_dBm['JN516x'][int(TxPower, 16)])
    else:
        self.log.logging('Input', 'Status', 'Confirming Set TxPower: %s' % int(TxPower, 16))