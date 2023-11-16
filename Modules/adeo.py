

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN


def adeo_fip(self, NwkId, EpOut, fip_level):
    # Thanks to Nodon support

    if fip_level not in ( 0x00, 0x01, 0x02, 0x03, 0x04, 0x05 ):
        self.log.logging( "Command", "Log", "adeo_fip : Fil Pilote mode error %s" %fip_level)
    self.log.logging( "Command", "Log", "adeo_fip : Fil Pilote mode: %s " % ( fip_level, ), NwkId, )

    Cluster = "fc00"
    cmd = "00"
    fcf = "15"
    manufcode = "128b"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = fcf + manufcode[2:4] + manufcode[:2] + sqn + cmd + "%02x" % fip_level

    raw_APS_request(self, NwkId, EpOut, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep="01", groupaddrmode=False, ackIsDisabled=False)