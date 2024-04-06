# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
# All operations to and from Zigate



from Modules.tools import Hex_Format, rgb_to_hsl, rgb_to_xy
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
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

GRP_CMD_WITHOUT_ACK = False
# Group Management Command
def add_group_member_ship(self, NwkId, DeviceEp, GrpId):
    """
    Add Group Membership GrpId to NwkId
    """
    self.logging("Debug", "add_group_member_ship GrpId: %s, NwkId: %s, Ep: %s" % (GrpId, NwkId, DeviceEp))
    zcl_add_group_membership( self, NwkId , ZIGATE_EP , DeviceEp , GrpId, ackIsDisabled=GRP_CMD_WITHOUT_ACK)


def check_group_member_ship(self, NwkId, DeviceEp, goup_addr):
    """
    Check group Membership
    """
    self.logging("Debug", "check_group_member_ship - addr: %s ep: %s group: %s" % (NwkId, DeviceEp, goup_addr))
    zcl_check_group_member_ship(self, NwkId, ZIGATE_EP, DeviceEp, goup_addr, GRP_CMD_WITHOUT_ACK)


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


def remove_group_member_ship(self, NwkId, DeviceEp, GrpId):

    self.logging("Debug", "remove_group_member_ship GrpId: %s NwkId: %s Ep: %s" % (GrpId, NwkId, DeviceEp))
    zcl_remove_group_member_ship(self, NwkId, ZIGATE_EP, DeviceEp, GrpId, GRP_CMD_WITHOUT_ACK)


def remove_all_groups( self, NwkId, DeviceEp):
    self.logging("Debug", "remove_all_groups  NwkId: %s Ep: %s" % ( NwkId, DeviceEp))
    zcl_remove_all_groups( self, NwkId, ZIGATE_EP, DeviceEp, GRP_CMD_WITHOUT_ACK)


# Operating commands on groups
def send_group_member_ship_identify(self, NwkId, DeviceEp, goup_addr="0000"):

    zcl_send_group_member_ship_identify(self, NwkId, ZIGATE_EP, DeviceEp, goup_addr, GRP_CMD_WITHOUT_ACK)


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

    zcl_group_identify_trigger_effect(self, "%s" % (GrpId), ZIGATE_EP, Ep, "%02x" % (effect_command[effect]), "%02x" % 0)


def set_kelvin_color(self, mode, addr, EPin, EPout, t, transit="0000"):
    # Value is in mireds (not kelvin)
    # Correct values are from 153 (6500K) up to 588 (1700K)
    # t is 0 > 255

    TempMired = 1000000 // int(((255 - int(t)) * (6500 - 1700) / 255) + 1700)
    zcl_group_move_to_colour_temperature(self, addr, EPin, EPout, Hex_Format(4, TempMired), transit)


def set_rgb_color(self, mode, addr, EPin, EPout, r, g, b, transit="0000"):
    x, y = rgb_to_xy((int(r), int(g), int(b)))

    # Convert 0-1 range to 0-65535 range (FFFF in hex)
    x = int(x * 65535)
    y = int(y * 65535)

    zcl_group_move_to_colour(self, addr, ZIGATE_EP, EPout, Hex_Format(4, x), Hex_Format(4, y), transit)


def set_hue_saturation(self, mode, addr, EPin, EPout, r, g, b, transit=None):
    hue, sat, lumi = rgb_to_hsl((int(r), int(g), int(b)))

    hue = int(hue * 254 / 360)   # Convert hue to 0-254 range
    sat = int(sat * 254 / 100)   # Convert saturation to 0-254 range

    self.logging("Log", f"---------- Set Hue X: {hue} Saturation: {sat}")
    zcl_group_move_hue_and_saturation(self, addr, ZIGATE_EP, EPout, Hex_Format(2, hue), Hex_Format(2, sat), transit)
    return lumi
