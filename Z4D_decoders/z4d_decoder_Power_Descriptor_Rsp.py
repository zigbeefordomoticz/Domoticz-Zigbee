def Decode8044(self, Devices, MsgData, MsgLQI):
    SQNum = MsgData[:2]
    Status = MsgData[2:4]
    bit_fields = MsgData[4:8]
    power_mode = bit_fields[0]
    power_source = bit_fields[1]
    current_power_source = bit_fields[2]
    current_power_level = bit_fields[3]
    self.log.logging('Input', 'Debug', 'Decode8044 - SQNum = ' + SQNum + ' Status = ' + Status + ' Power mode = ' + power_mode + ' power_source = ' + power_source + ' current_power_source = ' + current_power_source + ' current_power_level = ' + current_power_level)