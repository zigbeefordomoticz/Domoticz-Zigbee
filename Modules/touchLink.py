

from Modules.basicOutputs import raw_APS_request
from Modules.zigateConsts import ZIGATE_EP, MAX_LOAD_ZIGATE
from Modules.tools import getListOfEpForCluster, is_ack_tobe_disabled, get_and_inc_SQN

def get_group_identifiers_request( self, nwkid ):
    cluster_frame = "11"
    sqn = get_and_inc_SQN(self, nwkid)
    command = "41"
    start_index = "00"
    cluster = "1000"
    ListOfEp = getListOfEpForCluster(self, nwkid, cluster)
    if len(ListOfEp) != 1:
        return
    payload = cluster_frame + sqn +command + start_index 
    ep = ListOfEp[0]
    raw_APS_request(
                self,
                nwkid,
                ep,
                cluster,
                "0104",
                payload,
                zigate_ep=ZIGATE_EP,
                ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
                highpriority=True,
            )