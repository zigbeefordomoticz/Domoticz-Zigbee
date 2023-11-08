

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN


def adeo_fip(self, NwkId, EpOut, fip_level):
    
    # https://github.com/Koenkk/zigbee2mqtt/issues/19169#issuecomment-1801181411
    ADEO_FIP_ONOFF_COMMAND = {
        "Off": 0,
        "Confort": 1,
        "Eco": 2,
        "Frost Protection": 3,
        "Confort -1": 4,
        "Confort -2": 5
    }
    self.log.logging( "Command", "Log", "adeo_fip : Fil Pilote mode: %s - %s" % ( 
        fip_level, ADEO_FIP_ONOFF_COMMAND[fip_level]), NwkId, )

    Cluster = "fc00"
    cmd = "00"
    fcf = "15"
    manufcode = "128b"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = fcf + manufcode[2:4] + manufcode[:2] + sqn + cmd + "%02x" % ADEO_FIP_ONOFF_COMMAND[fip_level]

    raw_APS_request(self, NwkId, EpOut, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep="01", groupaddrmode=False, ackIsDisabled=False)