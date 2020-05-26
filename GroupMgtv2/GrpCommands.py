# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
# All operations to and from Zigate

import Domoticz

from time import time

from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl

# Group Management Command
def add_group_member_ship( self, NwkId, DeviceEp, GrpId):
    """
    Add Group Membership GrpId to NwkId
    """
    self.logging( 'Debug', "add_group_member_ship GrpId: %s, NwkId: %s, Ep: %s" %(GrpId, NwkId, DeviceEp ))
    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + GrpId
    self.ZigateComm.sendData( "0060", datas)

def check_group_member_ship( self, NwkId, DeviceEp, goup_addr ):
    """
    Check group Membership
    """
    self.logging( 'Debug', "check_group_member_ship - addr: %s ep: %s group: %s" %(NwkId, DeviceEp, goup_addr))  
    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + goup_addr
    self.ZigateComm.sendData( "0061", datas)
  
def look_for_group_member_ship(self, NwkId, DeviceEp, group_list = None):
    """
    Request to a device what are its group membership
    """
    datas = "02" + NwkId + ZIGATE_EP + DeviceEp
    if group_list is None:
        lenGrpLst = 0
        datas += "00"
    else:
        if isinstance(group_list, list):
            lenGrpLst = len(group_list)
            for x in group_list:
                group_list_ += "%04x" %(x)
        else:
            # We received only 1 group
            group_list_ = "%04x" %(group_list)
            lenGrpLst = 1
        datas += "%02.x" %(lenGrpLst) + group_list_
 
    self.logging( 'Debug', "look_for_group_member_ship - %s/%s from %s" %(NwkId, DeviceEp, group_list))
    self.ZigateComm.sendData( "0062", datas)

def remove_group_member_ship(self,  NwkId, DeviceEp, GrpId ):

    self.logging( 'Debug', "remove_group_member_ship GrpId: %s NwkId: %s Ep: %s" %(GrpId, NwkId, DeviceEp))
    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + GrpId
    self.ZigateComm.sendData( "0063", datas)

# Operating commands on groups
def send_group_member_ship_identify(self, NwkId, DeviceEp, goup_addr = "0000"):

    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + goup_addr
    self.ZigateComm.sendData( "0065", datas)

def send_group_member_ship_identify_effect( self, GrpId, Ep='01', effect = 'Okay' ):
    '''
        Blink   / Light is switched on and then off (once)
        Breathe / Light is switched on and off by smoothly increasing and
                then decreasing its brightness over a one-second period,
                and then this is repeated 15 times
        Okay    / •  Colour light goes green for one second
                •  Monochrome light flashes twice in one second
    '''

    effect_command = { 'Blink': 0x00 ,
            'Breathe': 0x01,
            'Okay': 0x02,
            'ChannelChange': 0x0b,
            'FinishEffect': 0xfe,
            'StopEffect': 0xff }

    self.logging( 'Debug', "Identify effect for Group: %s" %GrpId)
    identify = False
    if effect not in effect_command:
        effect = 'Okay'

    datas = "%02d" %ADDRESS_MODE['group'] + "%s"%(GrpId) + ZIGATE_EP + Ep + "%02x"%(effect_command[effect])  + "%02x" %0
    self.ZigateComm.sendData( "00E0", datas)

def set_kelvin_color( self, mode, addr, EPin, EPout, t, transit = None):
    #Value is in mireds (not kelvin)
    #Correct values are from 153 (6500K) up to 588 (1700K)
    # t is 0 > 255

    transit = '0001' if transit is None else '%04x' % transit
    TempKelvin = int(((255 - int(t))*(6500-1700)/255)+1700)
    TempMired = 1000000 // TempKelvin
    zigate_cmd = "00C0"
    zigate_param = Hex_Format(4, TempMired) + transit
    datas = "%02d" %mode + addr + EPin + EPout + zigate_param

    self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
    self.ZigateComm.sendData( zigate_cmd, datas)

def set_rgb_color( self, mode, addr, EPin, EPout, r, g, b, transit = None):

    transit = '0001' if transit is None else '%04x' % transit
    x, y = rgb_to_xy((int(r), int(g), int(b)))
    #Convert 0 > 1 to 0 > FFFF
    x = int(x*65536)
    y = int(y*65536)
    strxy = Hex_Format(4, x) + Hex_Format(4, y)
    zigate_cmd = "00B7"
    zigate_param = strxy + transit
    datas = "%02d" %mode + addr + ZIGATE_EP + EPout + zigate_param

    self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
    self.ZigateComm.sendData( zigate_cmd, datas)