# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
# All operations to and from Zigate


import Domoticz
from Modules.tools import Hex_Format, rgb_to_hsl, rgb_to_xy
from Zigbee.zclCommands import (zcl_add_group_membership,
                                 zcl_check_group_member_ship,
                                 zcl_group_identify_trigger_effect,
                                 zcl_group_move_hue_and_saturation,
                                 zcl_group_move_to_colour,
                                 zcl_group_move_to_colour_temperature,
                                 zcl_look_for_group_member_ship,
                                 zcl_remove_all_groups,
                                 zcl_remove_group_member_ship,
                                 zcl_send_group_member_ship_identify)
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP

GRP_CMD_WITHOUT_ACK = False
# Group Management Command
def add_group_member_ship(self, NwkId, DeviceEp, GrpId):
    """
    Add Group Membership GrpId to NwkId
    """
    self.logging("Debug", "add_group_member_ship GrpId: %s, NwkId: %s, Ep: %s" % (GrpId, NwkId, DeviceEp))
    #if not GRP_CMD_WITHOUT_ACK:
    #    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + GrpId
    #else:
    #    datas = "07" + NwkId + ZIGATE_EP + DeviceEp + GrpId
    zcl_add_group_membership( self, NwkId , ZIGATE_EP , DeviceEp , GrpId, ackIsDisabled=GRP_CMD_WITHOUT_ACK)
    #self.ControllerLink.sendData("0060", datas, ackIsDisabled=GRP_CMD_WITHOUT_ACK)


def check_group_member_ship(self, NwkId, DeviceEp, goup_addr):
    """
    Check group Membership
    """
    self.logging("Debug", "check_group_member_ship - addr: %s ep: %s group: %s" % (NwkId, DeviceEp, goup_addr))
    zcl_check_group_member_ship(self, NwkId, ZIGATE_EP, DeviceEp, goup_addr, GRP_CMD_WITHOUT_ACK)
    #if not GRP_CMD_WITHOUT_ACK:
    #    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + goup_addr
    #else:
    #    datas = "07" + NwkId + ZIGATE_EP + DeviceEp + goup_addr
    #self.ControllerLink.sendData("0061", datas, ackIsDisabled=GRP_CMD_WITHOUT_ACK)


def look_for_group_member_ship(self, NwkId, DeviceEp, group_list=None):
    """
    Request to a device what are its group membership
    """
    #if not GRP_CMD_WITHOUT_ACK:
    #    datas = "02" + NwkId + ZIGATE_EP + DeviceEp
    #else:
    #    datas = "07" + NwkId + ZIGATE_EP + DeviceEp
    if group_list is None:
        lenGrpLst = 0
        group_list_ = ""
    elif isinstance(group_list, list):
        lenGrpLst = len(group_list)
        group_list_ = "".join("%04x" % (x) for x in group_list)
    else:
        # We received only 1 group
        group_list_ = "%04x" % (group_list)
        lenGrpLst = 1
    zcl_look_for_group_member_ship(self, NwkId, ZIGATE_EP, DeviceEp, "%02.x" % (lenGrpLst), group_list_, GRP_CMD_WITHOUT_ACK)
    self.logging("Debug", "look_for_group_member_ship - %s/%s from %s" % (NwkId, DeviceEp, group_list))
    #self.ControllerLink.sendData("0062", datas, ackIsDisabled=GRP_CMD_WITHOUT_ACK)


def remove_group_member_ship(self, NwkId, DeviceEp, GrpId):

    self.logging("Debug", "remove_group_member_ship GrpId: %s NwkId: %s Ep: %s" % (GrpId, NwkId, DeviceEp))
    zcl_remove_group_member_ship(self, NwkId, ZIGATE_EP, DeviceEp, GrpId, GRP_CMD_WITHOUT_ACK)
    #if not GRP_CMD_WITHOUT_ACK:
    #    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + GrpId
    #else:
    #    datas = "07" + NwkId + ZIGATE_EP + DeviceEp + GrpId
    #self.ControllerLink.sendData("0063", datas, ackIsDisabled=GRP_CMD_WITHOUT_ACK)

def remove_all_groups( self, NwkId, DeviceEp):
    self.logging("Debug", "remove_all_groups  NwkId: %s Ep: %s" % ( NwkId, DeviceEp))
    zcl_remove_all_groups( self, NwkId, ZIGATE_EP, DeviceEp, GRP_CMD_WITHOUT_ACK)
    #if not GRP_CMD_WITHOUT_ACK:
    #    datas = "02" + NwkId + ZIGATE_EP + DeviceEp
    #else:
    #    datas = "07" + NwkId + ZIGATE_EP + DeviceEp
    #self.ControllerLink.sendData("0064", datas, ackIsDisabled=GRP_CMD_WITHOUT_ACK)


# Operating commands on groups
def send_group_member_ship_identify(self, NwkId, DeviceEp, goup_addr="0000"):

    zcl_send_group_member_ship_identify(self, NwkId, ZIGATE_EP, DeviceEp, goup_addr, GRP_CMD_WITHOUT_ACK)
    #if not GRP_CMD_WITHOUT_ACK:
    #    datas = "02" + NwkId + ZIGATE_EP + DeviceEp + goup_addr
    #else:
    #    datas = "07" + NwkId + ZIGATE_EP + DeviceEp + goup_addr
    #self.ControllerLink.sendData("0065", datas, ackIsDisabled=GRP_CMD_WITHOUT_ACK)


def send_group_member_ship_identify_effect(self, GrpId, Ep="01", effect="Okay"):
    """
    Blink   / Light is switched on and then off (once)
    Breathe / Light is switched on and off by smoothly increasing and
            then decreasing its brightness over a one-second period,
            and then this is repeated 15 times
    Okay    / •  Colour light goes green for one second
            •  Monochrome light flashes twice in one second
    """

    effect_command = {
        "Blink": 0x00,
        "Breathe": 0x01,
        "Okay": 0x02,
        "ChannelChange": 0x0B,
        "FinishEffect": 0xFE,
        "StopEffect": 0xFF,
    }

    self.logging("Debug", "Identify effect for Group: %s" % GrpId)
    identify = False
    if effect not in effect_command:
        effect = "Okay"

    #datas = (
    #    "%02d" % ADDRESS_MODE["group"]
    #    + "%s" % (GrpId)
    #    + ZIGATE_EP
    #    + Ep
    #    + "%02x" % (effect_command[effect])
    #    + "%02x" % 0
    #)
    #self.ControllerLink.sendData("00E0", datas)
    zcl_group_identify_trigger_effect(self, "%s" % (GrpId), ZIGATE_EP, Ep, "%02x" % (effect_command[effect]), "%02x" % 0)


def set_kelvin_color(self, mode, addr, EPin, EPout, t, transit="0000"):
    # Value is in mireds (not kelvin)
    # Correct values are from 153 (6500K) up to 588 (1700K)
    # t is 0 > 255

    TempKelvin = int(((255 - int(t)) * (6500 - 1700) / 255) + 1700)
    TempMired = 1000000 // TempKelvin
    #zigate_cmd = "00C0"
    #zigate_param = Hex_Format(4, TempMired) + transit
    #datas = "%02d" % mode + addr + EPin + EPout + zigate_param

    #self.logging("Debug", "Command: %s - data: %s" % (zigate_cmd, datas))
    #self.ControllerLink.sendData(zigate_cmd, datas)
    zcl_group_move_to_colour_temperature( self, addr, EPin, EPout, Hex_Format(4, TempMired), transit)


def set_rgb_color(self, mode, addr, EPin, EPout, r, g, b, transit="0000"):

    x, y = rgb_to_xy((int(r), int(g), int(b)))
    # Convert 0 > 1 to 0 > FFFF
    x = int(x * 65536)
    y = int(y * 65536)
    #strxy = Hex_Format(4, x) + Hex_Format(4, y)
    #zigate_cmd = "00B7"
    #zigate_param = strxy + transit
    #datas = "%02d" % mode + addr + ZIGATE_EP + EPout + zigate_param

    #self.logging("Debug", "Command: %s - data: %s" % (zigate_cmd, datas))
    #self.ControllerLink.sendData(zigate_cmd, datas)
    zcl_group_move_to_colour(self, addr, ZIGATE_EP, EPout, Hex_Format(4, x), Hex_Format(4, y), transit)


def set_hue_saturation(self, mode, addr, EPin, EPout, r, g, b, transit=None):

    h, s, l = rgb_to_hsl((int(r), int(g), int(b)))

    saturation = s * 100  # r
    hue = h * 360  # 0 > 360
    hue = int(hue * 254 // 360)
    saturation = int(saturation * 254 // 100)
    self.logging("Log", "---------- Set Hue X: %s Saturation: %s" % (hue, saturation))
    #self.ControllerLink.sendData(
    #    "00B6",
    #    "%02d" % ADDRESS_MODE["group"]
    #    + addr
    #    + ZIGATE_EP
    #    + EPout
    #    + Hex_Format(2, hue)
    #    + Hex_Format(2, saturation)
    #    + transit,
    #)
    zcl_group_move_hue_and_saturation(self, addr, ZIGATE_EP, EPout, Hex_Format(2, hue), Hex_Format(2, saturation), transit)
    return l
