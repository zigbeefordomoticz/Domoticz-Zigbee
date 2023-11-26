import struct

from Modules.sendZigateCommand import raw_APS_request


def Decode0041(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0041 - IEEE_addr_req: %s' % MsgData)
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    nwkid = MsgData[8:12]
    reqType = MsgData[12:14]
    startIndex = MsgData[14:16]
    self.log.logging('Input', 'Debug', '      source req nwkid: %s' % srcNwkId)
    self.log.logging('Input', 'Debug', '      request NwkId    : %s' % nwkid)
    self.log.logging('Input', 'Debug', '      request Type    : %s' % reqType)
    self.log.logging('Input', 'Debug', '      request Idx     : %s' % startIndex)
    Cluster = '8001'
    if nwkid == self.ControllerNWKID:
        status = '00'
        controller_ieee = '%016x' % struct.unpack('Q', struct.pack('>Q', int(self.ControllerIEEE, 16)))[0]
        controller_nwkid = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ControllerNWKID, 16)))[0]
        payload = sqn + status + controller_ieee + controller_nwkid + '00'
    elif nwkid in self.ListOfDevices:
        status = '00'
        device_ieee = '%016x' % struct.unpack('Q', struct.pack('>Q', int(self.ListOfDevices[nwkid]['IEEE'], 16)))[0]
        device_nwkid = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ControllerNWKID, 16)))[0]
        payload = sqn + status + device_ieee + device_nwkid + '00'
    else:
        status = '81'
        payload = sqn + status + nwkid
    self.log.logging('Input', 'Debug', 'Decode0041 - response payload: %s' % payload)
    raw_APS_request(self, srcNwkId, '00', Cluster, '0000', payload, zigpyzqn=sqn, zigate_ep='00')