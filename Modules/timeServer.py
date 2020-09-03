#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz

from Modules.basicInputs import read_attribute_response



def timeserver_read_attribute_request( self, sqn, nwkid, ep, cluster, manuf_spec, manuf_code , attribute):
    Domoticz.Log("timeserver_read_attribute_request %s/%s Cluster: %s Attribute: %s" %(nwkid, ep, cluster,attribute))

    data_type = value = None
    if attribute == '0000': # Time (should be probded by ZiGate)
        pass
    elif attribute == '0002': # Timezone

        #int32
        pass
    elif attribute == '0007': # LocalTime
        #uint32
        pass

    status = '86'

    read_attribute_response( self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code='0000')