#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: txPower.py

    Description: TxPower management

"""


import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Modules.basicOutputs import sendZigateCmd

"""
(Zigate) JN5168 standard-power module has a transmission power range of -32 to 0 dBm

Standard power modules of JN516X(Except JN5169) modules have only 4 possible power levels 
(Table 5 JN-UG-3024 v2.6). These levels are based on some kind of hardware registry so 
there is no way to change them in firmware. In ZiGate's case this means:

set/Get tx value  |  Mapped value (dBM)
    0 to 31       |         0
   52 to 63       |        -9
   40 to 51       |       -20
   32 to 39       |       -32

"""

POWER_LEVEL = { 0:00, # Max (Default)
                1:52, # 
                2:40, #
                3:32# Min
              }

def set_TxPower( self, powerlevel):

    if powerlevel not in POWER_LEVEL:
        powerlevel = 0

    setValue = POWER_LEVEL[powerlevel]

    attr_tx_power = '%02x' %setValue
    sendZigateCmd(self, "0806", attr_tx_power)


def get_TxPower( self ):

    """
    Command 0x0807 Get Tx Power doesn't need any parameters. 
    If command is handled successfully response will be first status(0x8000)
    with success status and after that Get Tx Power Response(0x8807). 
    0x8807 has only single parameter which is uint8 power. If 0x0807 fails 
    then response is going to be only status(0x8000) with status 1.
    """


    sendZigateCmd(self, "0807", "")

    return



