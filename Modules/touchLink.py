#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module : touchLink.py


    Description: 
"""

from Modules.basicOutputs import raw_APS_request
from Modules.tools import (get_and_inc_ZCL_SQN, getListOfEpForCluster,
                           is_ack_tobe_disabled)
from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_EP


def get_group_identifiers_request( self, nwkid ):
    cluster_frame = "19"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    command = "41"
    start_index = "00"
    cluster = "1000"
    ListOfEp = getListOfEpForCluster(self, nwkid, cluster)
    if len(ListOfEp) != 1:
        return
    payload = cluster_frame + sqn + command + start_index 
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
