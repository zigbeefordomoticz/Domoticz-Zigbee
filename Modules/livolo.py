#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate

"""

import Domoticz
import binascii
import struct
import json

from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import sendZigateCmd
from Modules.logging import loggingLivolo

"""
Livolo commands.

- looks like when Livolo switch is comming it is sending a Read Attribute to the Zigate on cluster 0x0001 Attributes: 0x895e, 0x1802, 0x4b00, 0x0012, 0x0021. In a malformed packet

- In order to bind the Livolo do:
(1) Send a Toggle
(2) Move to level 108 with transition 0.1 seconds
(3) Move to level 108 with transition 0.1 seconds
(4) Move to level 108 with transition 0.1 seconds

- When receiving 0x0001/0x0007 we must update the MacCapa attributes, accordingly to Mains (Single Phase)

"""


def livolo_bind( self, nwkid, EPout):

    livolo_OnOff(self, nwkid, EPout, 'All', 'Toggle')
    livolo_OnOff(self, nwkid, EPout, 'Left', 'On')
    livolo_OnOff(self, nwkid, EPout, 'Left', 'On')
    livolo_OnOff(self, nwkid, EPout, 'Left', 'On')


def livolo_OnOff( self, nwkid , EPout, devunit, onoff):
    """
    Levolo On/Off command are based on Level Control cluster
    Level: 108/0x6C  -> On
    Level: 1/0x01 -> Off
    Left Unit: Timing 1
    Right Unit: Timing 2
    """

    loggingLivolo( self, 'Debug', "livolo_OnOff - devunit: %s, onoff: %s" %(devunit, onoff), nwkid=nwkid)

    if onoff not in ( 'On', 'Off', 'Toggle'): return
    if devunit not in ( 'Left', 'Right', 'All'): return

    if onoff == 'Toggle' and devunit == 'All':
        loggingLivolo( self, 'Debug', "livolo_toggle" , nwkid=nwkid)
        sendZigateCmd(self, "0092","02" + nwkid + ZIGATE_EP + EPout + '02')
    else:
        level_value = timing_value = None
        if onoff == 'On': 
            level_value = '%02x' %108
        elif onoff == 'Off': 
            level_value = '%02x' %1

        if devunit == 'Left': 
            timing_value = '0001'
        elif devunit == 'Right': 
            timing_value = '0002'

        if level_value is not None and timing_value is not None:
            loggingLivolo( self, 'Debug', "livolo_OnOff - %s/%s Level: %s, Timing: %s" %( nwkid, EPout, level_value, timing_value), nwkid=nwkid)
            sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + '00' + level_value + timing_value)
        else:
            Domoticz.Error( "livolo_OnOff - Wrong parameters sent ! onoff: %s devunit: %s" %(onoff, devunit))
