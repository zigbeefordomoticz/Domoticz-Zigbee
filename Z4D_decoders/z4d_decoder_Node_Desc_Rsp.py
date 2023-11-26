from Modules.tools import (ReArrangeMacCapaBasedOnModel, decodeMacCapa, updLQI)

def Decode8042(self, Devices, MsgData, MsgLQI):
    sequence = MsgData[:2]
    status = MsgData[2:4]
    addr = MsgData[4:8]
    if status == '00':
        manufacturer = MsgData[8:12]
        max_rx = MsgData[12:16]
        max_tx = MsgData[16:20]
        server_mask = MsgData[20:24]
        descriptor_capability = MsgData[24:26]
        mac_capability = MsgData[26:28]
        max_buffer = MsgData[28:30]
        bit_field = MsgData[30:34]
    if status != '00':
        self.log.logging('Input', 'Debug', 'Decode8042 - Reception of Node Descriptor for %s with status %s' % (addr, status))
        return
    
    self.log.logging('Input', 'Debug', 'Decode8042 - Reception Node Descriptor for: ' + addr + ' SEQ: ' + sequence + ' Status: ' + status + ' manufacturer:' + manufacturer + ' mac_capability: ' + str(mac_capability) + ' bit_field: ' + str(bit_field), addr)
    if addr == '0000' and addr not in self.ListOfDevices:
        self.ListOfDevices[addr] = {}
        self.ListOfDevices[addr]['Ep'] = {}
    if addr not in self.ListOfDevices:
        self.log.logging('Input', 'Log', 'Decode8042 receives a message from a non existing device %s' % addr)
        return
    
    updLQI(self, addr, MsgLQI)
    
    self.ListOfDevices[addr]['_rawNodeDescriptor'] = MsgData[8:]
    self.ListOfDevices[addr]['Max Buffer Size'] = max_buffer
    self.ListOfDevices[addr]['Max Rx'] = max_rx
    self.ListOfDevices[addr]['Max Tx'] = max_tx
    self.ListOfDevices[addr]['macapa'] = mac_capability
    self.ListOfDevices[addr]['bitfield'] = bit_field
    self.ListOfDevices[addr]['server_mask'] = server_mask
    self.ListOfDevices[addr]['descriptor_capability'] = descriptor_capability
    mac_capability = ReArrangeMacCapaBasedOnModel(self, addr, mac_capability)
    capabilities = decodeMacCapa(mac_capability)
    
    if 'Able to act Coordinator' in capabilities:
        AltPAN = 1
        
    else:
        AltPAN = 0
        
    if 'Main Powered' in capabilities:
        PowerSource = 'Main'
        
    else:
        PowerSource = 'Battery'
        
    if 'Full-Function Device' in capabilities:
        DeviceType = 'FFD'
        
    else:
        DeviceType = 'RFD'
        
    if 'Receiver during Idle' in capabilities:
        ReceiveonIdle = 'On'
        
    else:
        ReceiveonIdle = 'Off'
        
    self.log.logging('Input', 'Debug', 'Decode8042 - Alternate PAN Coordinator = ' + str(AltPAN), addr)
    self.log.logging('Input', 'Debug', 'Decode8042 - Receiver on Idle = ' + str(ReceiveonIdle), addr)
    self.log.logging('Input', 'Debug', 'Decode8042 - Power Source = ' + str(PowerSource), addr)
    self.log.logging('Input', 'Debug', 'Decode8042 - Device type  = ' + str(DeviceType), addr)
    bit_fieldL = int(bit_field[2:4], 16)
    bit_fieldH = int(bit_field[:2], 16)
    self.log.logging('Input', 'Debug', 'Decode8042 - bit_fieldL  = %s bit_fieldH = %s' % (bit_fieldL, bit_fieldH))
    LogicalType = bit_fieldL & 15
    
    if LogicalType == 0:
        LogicalType = 'Coordinator'
        
    elif LogicalType == 1:
        LogicalType = 'Router'
        
    elif LogicalType == 2:
        LogicalType = 'End Device'
        
    self.log.logging('Input', 'Debug', 'Decode8042 - bit_field = ' + str(bit_fieldL) + ': ' + str(bit_fieldH), addr)
    self.log.logging('Input', 'Debug', 'Decode8042 - Logical Type = ' + str(LogicalType), addr)
    
    if 'Manufacturer' not in self.ListOfDevices[addr] or self.ListOfDevices[addr]['Manufacturer'] in ('', {}):
        self.ListOfDevices[addr]['Manufacturer'] = manufacturer
        
    if 'Status' not in self.ListOfDevices[addr] or self.ListOfDevices[addr]['Status'] != 'inDB':
        self.ListOfDevices[addr]['Manufacturer'] = manufacturer
        self.ListOfDevices[addr]['DeviceType'] = str(DeviceType)
        self.ListOfDevices[addr]['LogicalType'] = str(LogicalType)
        self.ListOfDevices[addr]['PowerSource'] = str(PowerSource)
        self.ListOfDevices[addr]['ReceiveOnIdle'] = str(ReceiveonIdle)