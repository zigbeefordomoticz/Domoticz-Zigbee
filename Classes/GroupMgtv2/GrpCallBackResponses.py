#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

from Classes.GroupMgtv2.GrpDatabase import (add_device_to_group, create_group,
                                            remove_device_from_group,
                                            write_groups_list)
from Classes.GroupMgtv2.GrpDomoticz import (
    LookForGroupAndCreateIfNeeded, create_domoticz_group_device,
    remove_domoticz_group_device, update_domoticz_group_device,
    update_domoticz_group_device_widget)


def checkToCreateOrUpdateGroup(self, NwkId, Ep, GroupId):
    """
    Trigger from addGroupMemberShipResponse or checkGroupMemberShip
    (1) Update ListOfGroups datastructutre
    (2) check if a Group has to be created in the Database and in Domoticz
    """

    self.logging("Debug", "checkToCreateGroup NwkId: %s Ep: %s GrouId: %s" % (NwkId, Ep, GroupId), GroupId)
    if "IEEE" not in self.ListOfDevices[NwkId]:
        return

    Ieee = self.ListOfDevices[NwkId]["IEEE"]

    if GroupId not in self.ListOfGroups:
        self.logging("Debug", "-------> Needs to Create a Group GrouId: %s" % (GroupId), GroupId)
        GrpName = "Zigate Group " + GroupId
        create_group(self, GroupId, GrpName)
        create_domoticz_group_device(self, GrpName, GroupId)

    self.logging("Debug", "-------> Adding Device %s to Group GrouId: %s" % (NwkId, GroupId), GroupId)
    add_device_to_group(self, [NwkId, Ep, Ieee], GroupId)
    # A group already known can have lost its widget: a scan is what brings it back
    LookForGroupAndCreateIfNeeded(self, GroupId)
    self.write_groups_list()


def checkToRemoveGroup(self, NwkId, Ep, GroupId):
    """
    Trigger from removeGroupMemberShip
    (1) Update ListOgGroups dataStructutre
    (2) check if a Group has to be created in the Database and in Domoticz
    """

    self.logging("Debug", "checkToRemoveGroup NwkId: %s Ep: %s GrouId: %s" % (NwkId, Ep, GroupId), GroupId)
    if NwkId not in self.ListOfDevices:
        return
    if "IEEE" not in self.ListOfDevices[NwkId]:
        return
    Ieee = self.ListOfDevices[NwkId]["IEEE"]
    self.logging("Debug", "-------> Removing Device %s from Group GrouId: %s" % (NwkId, GroupId), GroupId)
    remove_device_from_group(self, [NwkId, Ep, Ieee], GroupId)

    if GroupId in self.ListOfGroups:
        update_domoticz_group_device_widget(self, GroupId)
        self.write_groups_list()
        return

    self.logging("Debug", "-------> Needs to Remove Group GrouId: %s" % (GroupId), GroupId)
    remove_domoticz_group_device(self, GroupId)
    self.write_groups_list()
