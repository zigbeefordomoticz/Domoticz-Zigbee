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

from time import time

from Classes.GroupMgtv2.GrpCallBackResponses import checkToCreateOrUpdateGroup
from Classes.GroupMgtv2.GrpCommands import (
    add_group_member_ship, check_group_member_ship, look_for_group_member_ship,
    remove_group_member_ship, send_group_member_ship_identify_effect)
from Classes.GroupMgtv2.GrpDatabase import (check_if_group_empty,
                                            checkNwkIdAndUpdateIfAny,
                                            create_group, remove_group,
                                            remove_nwkid_from_all_groups)
from Classes.GroupMgtv2.GrpDomoticz import (LookForGroupAndCreateIfNeeded,
                                            create_domoticz_group_device,
                                            remove_domoticz_group_device,
                                            update_domoticz_group_name)
from Classes.GroupMgtv2.GrpIkeaRemote import (checkIfIkeaRound5BToBeAdded,
                                              checkIfIkeaRound5BToBeRemoved)
from Modules.domoticzAbstractLayer import     find_first_unit_widget_from_deviceID
from Modules.tools import mainPoweredDevice
from Modules.zigateConsts import LEGRAND_REMOTES


def SendGroupIdentifyEffect(self, GrpId):

    send_group_member_ship_identify_effect(self, GrpId)


def checkAndTriggerIfMajGroupNeeded(self, NwkId, Ep, ClusterId):
    """
    This method is call from MajDomoDevice and onCommand because there is an update of a particular Device Cluster/Attribute
    We will then check if that impact a group and in that case trigger the update of such group
    """

    if "GroupMemberShip" in self.ListOfDevices[NwkId] and Ep in self.ListOfDevices[NwkId]["GroupMemberShip"]:
        for GrpId in self.ListOfDevices[NwkId]["GroupMemberShip"][Ep]:
            self.update_domoticz_group_device(GrpId)


def check_existing_membership(self):
    # For each group, check the group membership of the identified device
    for GrpId in self.ListOfGroups:
        for NwkId, Ep, Ieee in self.ListOfGroups[GrpId]["Devices"]:
            check_group_member_ship(self, NwkId, Ep, GrpId)


def legrand_gang_endpoint(self, NwkId, gang):
    """
    Endpoint a gang's group membership belongs to.

    RemoteGroup is keyed by the fc01 leftright byte, or "Single" for a one gang
    remote. The byte has the same two digit form as an endpoint and is used as one
    when the device declares it; everything else falls back to endpoint 01.
    """
    if gang in self.ListOfDevices.get(NwkId, {}).get("Ep", {}):
        return gang
    return "01"


def legrand_remote_in_group(self, GrpId, NwkId):
    """Is this remote, by IEEE, already a member of that group."""
    ieee = self.ListOfDevices.get(NwkId, {}).get("IEEE")
    if not ieee:
        return False
    devices = self.ListOfGroups.get(GrpId, {}).get("Devices") or []
    return any(isinstance(device, (list, tuple)) and len(device) >= 3 and device[2] == ieee for device in devices)


def recover_legrand_groups_from_devices(self):
    """
    Put back the groups a Legrand remote owns when they have gone missing.

    A Legrand remote keeps its group assignment internally - it was told so with fc01
    command 0x0c - and there is no way to read it back: this model answers both fc01
    attributes with UNSUPPORTED_ATTRIBUTE. The plugin's own record of it lives in
    ListOfDevices[nwkid]["Legrand"]["RemoteGroup"], one entry per gang.

    So when the group list is lost while the device list survives, the remote keeps
    commanding a group the plugin no longer knows and every press only produces
    "update_domoticz_group_device - unknown group: fefe". The device record holds
    everything needed to rebuild it, which is what this does, at load time.

    Three states are repaired: the group gone from ListOfGroups, the group there but
    without this remote, and the group there without its Domoticz widget. A healthy
    installation does nothing.
    """
    for NwkId in list(self.ListOfDevices):
        device = self.ListOfDevices[NwkId]
        if not isinstance(device, dict):
            continue

        legrand = device.get("Legrand")
        if not isinstance(legrand, dict):
            continue

        remote_group = legrand.get("RemoteGroup")
        if not isinstance(remote_group, dict):
            continue

        for gang, GrpId in sorted(remote_group.items()):
            if not GrpId:
                continue

            Ep = legrand_gang_endpoint(self, NwkId, gang)

            if GrpId not in self.ListOfGroups or not legrand_remote_in_group(self, GrpId, NwkId):
                self.logging(
                    "Status",
                    "Recovering Legrand group %s of remote %s/%s from the device record" % (GrpId, NwkId, Ep),
                )
                checkToCreateOrUpdateGroup(self, NwkId, Ep, GrpId)

            elif find_first_unit_widget_from_deviceID(self, self.Devices, GrpId) is None:
                self.logging("Status", "Recovering the Domoticz widget of Legrand group %s" % GrpId)
                LookForGroupAndCreateIfNeeded(self, GrpId)


def RemoveNwkIdFromAllGroups(self, Nwkid):
    " call my plugin when removing one device"
    self.logging("Debug", "RemoveNwkIdFromAllGroups - Remove Nwk from all groups: %s" % Nwkid)
    remove_nwkid_from_all_groups(self, Nwkid)

    # Check if any groups are empty. If so remove the Domoticz Widget
    self.logging("Debug", "RemoveNwkIdFromAllGroups - ListOfGroups: %s" % str(self.ListOfGroups.keys()))
    for GrpId in list(self.ListOfGroups):
        if check_if_group_empty(self, GrpId):
            self.logging("Debug", "RemoveNwkIdFromAllGroups - Empty Group: %s" % GrpId)
            remove_group(self, GrpId)
            remove_domoticz_group_device(self, GrpId)
    self.write_groups_list()


def FullRemoveOfGroup(self, unit, GroupId):
    # Call by onRemove call from Domoticz
    # The widget has been removed by Domoticz, we have to cleanup
    self.logging("Debug", "process_remove_group Unit: %s GroupId: %s" % (unit, GroupId))
    if GroupId not in self.ListOfGroups:
        return
    for NwkId, Ep, IEEE in self.ListOfGroups[GroupId]["Devices"]:
        NwkId = checkNwkIdAndUpdateIfAny(self, NwkId, IEEE)
        if NwkId:
            remove_group_member_ship(self, NwkId, Ep, GroupId)
    self.write_groups_list()


def provision_Manufacturer_Group(self, GrpId, NwkId, Ep, Ieee):
    pass


def scan_device_for_grp_membership(self, NwkId, Ep):
    # Ask this device for list of Group membership
    self.logging("Debug", " --  --  --  --  --  > scan_device_for_grp_membership ")
    if NwkId not in self.ListOfDevices:
        return

    # Remove Group MemverShip from Device
    if "GroupMemberShip" in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId]["GroupMemberShip"]

    # Remove Group MemberShip from Group, as we will check.
    RemoveNwkIdFromAllGroups(self, NwkId)

    # Finaly submit the request
    look_for_group_member_ship(self, NwkId, Ep)


def submitForGroupMemberShipScaner(self, NwkId, Ep):

    if self.ControllerLink.loadTransmit() >= 1:
        self.ScanDevicesToBeDone.append([NwkId, Ep])
    else:
        scan_device_for_grp_membership(self, NwkId, Ep)


def scan_all_devices_for_grp_membership(self):
    for NwkId in self.ListOfDevices:
        if not mainPoweredDevice(self, NwkId):
            continue
        for Ep in self.ListOfDevices[NwkId]["Ep"]:
            if "0004" not in self.ListOfDevices[NwkId]["Ep"][Ep]:
                continue
            if NwkId == "0000" and Ep != "01":
                continue
            submitForGroupMemberShipScaner(self, NwkId, Ep)


def updateGroupName(self, GrpId, NewGrpName):
    # Update the GroupName
    self.ListOfGroups[GrpId]["Name"] = NewGrpName

    # Update in Dz
    update_domoticz_group_name(self, GrpId, NewGrpName)


def addGroupMemberShip(self, NwkId, Ep, GroupId):
    """
    call from plugin
    """
    add_group_member_ship(self, NwkId, Ep, GroupId)
    self.write_groups_list()


def add_group_member_ship_from_remote(self, NwkId, Ep, GroupId):

    # This is called from a plugin when setting group membership for a Legrand Remote
    group_membership = self.ListOfDevices.setdefault(NwkId, {}).setdefault("GroupMemberShip", {})
    group_membership.setdefault(Ep, {})[GroupId] = {"Status": "OK"}
    checkToCreateOrUpdateGroup(self, NwkId, Ep, GroupId)

def get_available_grp_id(self, start_range, stop_range):
    # Single allocator for both ascending (WebUI) and descending (Legrand reserved
    # band) ranges: the step direction is derived from start_range vs stop_range.
    step = -1 if start_range > stop_range else 1
    for x in range(start_range, stop_range, step):
        GrpId = "%04x" % x
        if GrpId not in self.ListOfGroups:
            return GrpId
    return None


def create_new_group_and_attach_devices(self, GrpId, GrpName, DevicesList):
    self.logging("Debug", " --  --  --  --  --  > CreateNewGroupAndAttachDevices ")
    create_group(self, GrpId, GrpName)
    create_domoticz_group_device(self, GrpName, GrpId)
    for NwkId, ep, ieee in DevicesList:
        add_group_member_ship(self, NwkId, ep, GrpId)
    self.write_groups_list()


def update_group_and_add_devices(self, GrpId, ToBeAddedDevices):
    self.logging("Debug", f" --  --  --  --  --  > UpdateGroupAndAddDevices {GrpId} {ToBeAddedDevices}")
    for NwkId, ep, ieee in ToBeAddedDevices:
        NwkId = checkNwkIdAndUpdateIfAny(self, NwkId, ieee)
        # Ikea Tradfri Round5B will be added if required by checkIfIkeaRound5B
        if NwkId and not checkIfIkeaRound5BToBeAdded(self, NwkId, ep, ieee, GrpId):
            add_group_member_ship(self, NwkId, ep, GrpId)
    self.write_groups_list()


def update_group_and_remove_devices(self, GrpId, ToBeRemoveDevices):
    self.logging("Debug", f" --  --  --  --  --  > UpdateGroupAndRemoveDevices {GrpId} {ToBeRemoveDevices}")
    for NwkId, ep, ieee in ToBeRemoveDevices:
        self.logging("Debug", "-- --  --  --  --  --  > Removing [%s %s %s]" % (NwkId, ep, ieee))
        NwkId = checkNwkIdAndUpdateIfAny(self, NwkId, ieee)
        # Ikea Tradfri Round5B will be removed if required by checkIfIkeaRound5B
        if NwkId and not checkIfIkeaRound5BToBeRemoved(self, NwkId, ep, ieee, GrpId):
            self.logging(
                "Debug", "-- --  --  --  --  --  -- > Calling Remove_group_membership [%s %s %s]" % (NwkId, ep, ieee)
            )
            remove_group_member_ship(self, NwkId, ep, GrpId)
        # if 'Model' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['Model'] in LEGRAND_REMOTES:
        #    from Classes.GroupMgtv2.GrpCallBackResponses import  checkToRemoveGroup
        #    if [NwkId, NwkId, ieee] in self.ListOfGroups[ GrpId]['Devices']:
        #        self.ListOfGroups[ GrpId]['Devices'].remove( [NwkId, NwkId, ieee]  )
        #    checkToRemoveGroup( self,NwkId, NwkId, GrpId )

    self.write_groups_list()
