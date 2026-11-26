import struct

from Modules.sendZigateCommand import raw_APS_request


def _le16(value):
    # The ListOfDevices fields are big-endian hex strings, ZDP sends 16-bit values little-endian
    return '%04x' % struct.unpack('H', struct.pack('>H', int(value, 16)))[0]


def Decode0042(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0042 - Node_Desc_req: %s' % MsgData)
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    nwkid = MsgData[8:12]
    Cluster = '8002'

    if nwkid != '0000':
        status = '80'
        payload = sqn + status + _le16(nwkid)

    elif '0000' not in self.ListOfDevices:
        status = '81'
        payload = sqn + status + _le16(nwkid)

    elif 'Manufacturer' not in self.ListOfDevices['0000']:
        status = '89'
        payload = sqn + status + _le16(nwkid)

    else:
        status = '00'

        controllerManufacturerCode = self.ListOfDevices['0000']['Manufacturer']
        controllerManufacturerCode = '0000'
        self.log.logging('Input', 'Debug', 'Decode0042 - %s/%s requested manuf code -responding with Manufacturer: %s' % (srcNwkId, srcEp, controllerManufacturerCode))
        manuf_code16 = _le16(controllerManufacturerCode)
        max_in_size16 = _le16(self.ListOfDevices['0000']['Max Rx'])
        max_out_size16 = _le16(self.ListOfDevices['0000']['Max Tx'])
        server_mask16 = _le16(self.ListOfDevices['0000']['server_mask'])
        descriptor_capability8 = self.ListOfDevices['0000']['descriptor_capability']
        mac_capa8 = self.ListOfDevices['0000']['macapa']
        max_buf_size8 = self.ListOfDevices['0000']['Max Buffer Size']
        # bitfield low byte = logical type, high byte = APS flags + frequency band: on air, low byte first
        bitfield16 = _le16(self.ListOfDevices['0000']['bitfield'])
        # Node_Desc_rsp, Zigbee spec 2.4.4.2.3: Status, NWKAddrOfInterest, then the Node Descriptor (2.3.2.3)
        # in its own order. The ListOfDevices fields come in the ZiGate 0x8042 order, which differs.
        payload = sqn + status + _le16(nwkid)
        payload += bitfield16 + mac_capa8 + manuf_code16 + max_buf_size8 + max_in_size16 + server_mask16 + max_out_size16
        payload += descriptor_capability8
    self.log.logging('Input', 'Debug', 'Decode0042 - response payload: %s' % payload)
    raw_APS_request(self, srcNwkId, '00', Cluster, '0000', payload, zigate_ep='00', zigpyzqn=sqn)