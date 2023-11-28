import struct

from Modules.sendZigateCommand import raw_APS_request


def Decode0040(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0040 - NWK_addr_req: %s' % MsgData)
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    ieee = MsgData[8:24]
    reqType = MsgData[24:26]
    startIndex = MsgData[26:28]
    self.log.logging('Input', 'Debug', '      source req nwkid: %s' % srcNwkId)
    self.log.logging('Input', 'Debug', '      request IEEE    : %s' % ieee)
    self.log.logging('Input', 'Debug', '      request Type    : %s' % reqType)
    self.log.logging('Input', 'Debug', '      request Idx     : %s' % startIndex)
    Cluster = '8000'
    if ieee == self.ControllerIEEE:
        controller_ieee = '%016x' % struct.unpack('Q', struct.pack('>Q', int(self.ControllerIEEE, 16)))[0]
        controller_nwkid = '%04x' % struct.unpack('H', struct.pack('>H', int(self.ControllerNWKID, 16)))[0]
        status = '00'
        payload = sqn + status + controller_ieee + controller_nwkid + '00'
    elif ieee in self.IEEE2NWK:
        device_ieee = '%016x' % struct.unpack('Q', struct.pack('>Q', int(ieee, 16)))[0]
        device_nwkid = '%04x' % struct.unpack('H', struct.pack('>H', int(self.IEEE2NWK[ieee], 16)))[0]
        status = '00'
        payload = sqn + status + device_ieee + device_nwkid + '00'
    else:
        status = '81'
        payload = sqn + status + ieee
    self.log.logging('Input', 'Debug', 'Decode0040 - response payload: %s' % payload)
    raw_APS_request(self, srcNwkId, '00', Cluster, '0000', payload, zigpyzqn=sqn, zigate_ep='00')