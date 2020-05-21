#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

from datetime import datetime
from time import time

from Modules.basicOutputs import raw_APS_request, write_attribute
from Modules.readAttributes import ReadAttributeRequest_0006_0000, ReadAttributeRequest_0008_0000


def pollingGledopto( self, key ):

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    rescheduleAction = False

    #if  ( self.busy or len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE):
    #    return True

    ReadAttributeRequest_0006_0000( self, key)
    ReadAttributeRequest_0008_0000( self, key)

    return rescheduleAction


def callbackDeviceAwake_Gledopto(self, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    Domoticz.Log("callbackDeviceAwake_Legrand - Nwkid: %s, EndPoint: %s cluster: %s" \
            %(NwkId, EndPoint, cluster))

    return

