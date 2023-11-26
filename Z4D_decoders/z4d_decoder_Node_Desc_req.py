def Decode0042(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0042 - Node_Desc_req: %s' % MsgData)
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    nwkid = MsgData[8:12]
    Cluster = '8002'
    if nwkid != '0000':
        status = '80'
        payload = sqn + status + nwkid
    elif '0000' not in self.ListOfDevices:
        status = '81'
        payload = sqn + status + nwkid
    elif 'Manufacturer' not in self.ListOfDevices['0000']:
        status = '89'
        payload = sqn + status + nwkid
    else:
        status = '00'
        controllerManufacturerCode = self.ListOfDevices['0000']['Manufacturer']
        controllerManufacturerCode = '0000'
        self.log.logging('Input', 'Log', 'Decode0042 - %s/%s requested manuf code -responding with Manufacturer: %s' % (srcNwkId, srcEp, controllerManufacturerCode))
        manuf_code16 = '%04x' % struct.unpack('H', struct.pack('>H', int(controllerManufacturerCode, 16)))[0]
        max_in_size16 = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ListOfDevices['0000']['Max Rx'], 16)))[0]
        max_out_size16 = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ListOfDevices['0000']['Max Tx'], 16)))[0]
        server_mask16 = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ListOfDevices['0000']['server_mask'], 16)))[0]
        descriptor_capability8 = self.ListOfDevices['0000']['descriptor_capability']
        mac_capa8 = self.ListOfDevices['0000']['macapa']
        max_buf_size8 = self.ListOfDevices['0000']['Max Buffer Size']
        bitfield16 = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ListOfDevices['0000']['bitfield'], 16)))[0]
        payload = sqn + status + nwkid + manuf_code16 + max_in_size16 + max_out_size16 + server_mask16 + descriptor_capability8
        payload += mac_capa8 + max_buf_size8 + bitfield16
    self.log.logging('Input', 'Debug', 'Decode0042 - response payload: %s' % payload)
    raw_APS_request(self, srcNwkId, '00', Cluster, '0000', payload, zigate_ep='00', zigpyzqn=sqn)