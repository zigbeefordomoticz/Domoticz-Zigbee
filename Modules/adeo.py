

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN


def adeo_fip(self, NwkId, EpOut, fip_level):
    
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

    Cluster = "0006"
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "%02x" % cluster_frame + sqn + "%02x" % ADEO_FIP_ONOFF_COMMAND[fip_level] 

    raw_APS_request(self, NwkId, EpOut, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep="01", groupaddrmode=False, ackIsDisabled=False)