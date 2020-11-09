#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz

from Classes.LoggingManagement import LoggingManagement

from Modules.basicOutputs import write_attribute
from Modules.tools import get_request_datastruct, set_request_datastruct, get_list_waiting_request_datastruct, is_ack_tobe_disabled
from Modules.zigateConsts import  ZIGATE_EP

FAN_MODE = {
    'Off': 0x00,
    'Low': 0x01,
    'Medium': 0x02,
    'High': 0x03,
    'On': 0x04,
    'Auto': 0x05,
    'Smart': 0x06,
}


def change_fan_mode( self, NwkId, Ep, fan_mode):

    if fan_mode not in FAN_MODE:
        return

    data = '%02x' %FAN_MODE[ fan_mode ]

    write_attribute (self, NwkId, ZIGATE_EP, Ep, '0202', '0000',   '00', '0000', '30', data, ackIsDisabled = is_ack_tobe_disabled(self, NwkId))