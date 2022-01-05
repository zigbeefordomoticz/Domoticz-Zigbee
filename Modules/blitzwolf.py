#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

from Modules.readAttributes import ReadAttributeRequest_0b04_050b_0505_0508
from Modules.zigateConsts import MAX_LOAD_ZIGATE


def pollingBlitzwolfPower(self, key):
    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
        return True

    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] == "TS0121":
        ReadAttributeRequest_0b04_050b_0505_0508(self, key)
        # ReadAttributeRequest_0702_0000(self, key)

    return False
