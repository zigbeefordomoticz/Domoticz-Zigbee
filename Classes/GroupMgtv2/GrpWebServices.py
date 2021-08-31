# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
import Domoticz

from time import time

from Modules.tools import getListOfEpForCluster, mainPoweredDevice

from Classes.GroupMgtv2.GrpServices import (
    create_new_group_and_attach_devices,
    update_group_and_add_devices,
    update_group_and_remove_devices,
    scan_all_devices_for_grp_membership,
    submitForGroupMemberShipScaner,
    SendGroupIdentifyEffect,
    updateGroupName,
)


from Classes.GroupMgtv2.GrpIkeaRemote import Ikea5BToBeAddedToListIfExist


def ScanAllDevicesForGroupMemberShip(self):
    self.GroupStatus = "scan"
    scan_all_devices_for_grp_membership(self)


def ScanDevicesForGroupMemberShip(self, DevicesToScan):

    self.logging("Debug", "ScanDevicesForGroupMemberShip : %s " % DevicesToScan)

    for NwkId in DevicesToScan:
        if NwkId == "0000":
            submitForGroupMemberShipScaner(self, NwkId, "01")
            continue
        if NwkId not in self.ListOfDevices:
            self.logging("Debug", "ScanDevicesForGroupMemberShip : Skiping %s not existing" % NwkId)
            continue
        if not mainPoweredDevice:
            self.logging("Debug", "ScanDevicesForGroupMemberShip : Skiping %s not main powered" % NwkId)
            continue

        ListEp = getListOfEpForCluster(self, NwkId, "0004")
        self.logging("Debug", "ScanDevicesForGroupMemberShip : List of Ep %s for  %s" % (str(ListEp), NwkId))

        for Ep in ListEp:
            if [NwkId, Ep] not in self.ScanDevicesToBeDone:
                self.GroupStatus = "scan"
                submitForGroupMemberShipScaner(self, NwkId, Ep)


def process_web_request(self, webInput):
    """
    Receive as GroupInput the json coming from the WebUI
    coordinatorInside:true  means Zigate must be part of the Group
    devicesSelected means a list of { EP and NwkId}
    if '_GroupId' do not exist in the list of groups, then it is about creating a new group

    """

    # Begining
    # self.logging( 'Debug', "processWebRequest %s" %webInput)
    if len(webInput) == 0:
        fullGroupRemove(self)
        return

    # Have at least 1 Item
    # Now from that point we have 3 possibile Scenarios
    # 1- We have a new Group
    # 2- We have updated a group
    # 3- We have Remove a Group

    InitialListOfGroups = list(self.ListOfGroups.keys())
    NewListOfGroups = []
    for item in webInput:
        self.logging("Debug", " -- - > %s " % item)
        GrpName = item["GroupName"]
        self.logging("Debug", " -- - > GrpName: %s " % GrpName)

        # Scenario 1 - We have a new Group
        if "_GroupId" not in item:
            newGroup(self, GrpName, item)
            return

        # Scenario 2 we have to check if there is an update
        self.logging("Debug", " -- - > Update GrpName: %s " % GrpName)
        GrpId = item["_GroupId"]
        if GrpId not in self.ListOfGroups:
            # Is that possible ?
            # It should be considered as a New group, but in that case, we should not have _GroupId
            continue

        # Check if we have to update the Group Name
        if GrpId in self.ListOfGroups and GrpName != self.ListOfGroups[GrpId]["Name"]:
            self.logging(
                "Debug", " -- - > Require Group Name update from %s to %s" % (self.ListOfGroups[GrpId]["Name"], GrpName)
            )
            updateGroupName(self, GrpId, GrpName)

        NewListOfGroups.append(GrpId)
        updateGroup(self, GrpId, item)

    # Finaly, let checks if we have Scenario 3
    self.logging("Debug", " -- - > Initial Group List: %s " % str(InitialListOfGroups))
    self.logging("Debug", " -- - > Updated Group List: %s " % str(NewListOfGroups))

    GroupToBeRemoved = diff(InitialListOfGroups, NewListOfGroups)
    self.logging("Debug", " -- - > Groups to be removed: %s " % str(GroupToBeRemoved))
    for GrpId in GroupToBeRemoved:
        delGroup(self, GrpId)


def get_group_id(self):
    for x in range(0x0001, 0x0999):
        GrpId = "%04x" % x
        if GrpId not in self.ListOfGroups:
            return GrpId


def diff(first, second):
    """
    Diff between first and second
    returns what is in first and not in second
    """

    return [item for item in first if item not in second]


def compare_exitsing_with_new_list(self, first, second):
    """
    Compare 2 lists of devices and will return a dict with toBeAdded and toBeRemoved
    """
    # self.logging( 'Debug', " --  --  --  --  --  > compareExitsingWithNewList ")
    report = {"ToBeAdded": diff(second, first)}
    report["ToBeRemoved"] = diff(first, second)
    return report


def transform_web_to_group_devices_list(self, WebDeviceList):
    # self.logging( 'Debug', "TransformWebToGroupDevicesList ")
    DeviceList = []
    for item in WebDeviceList:
        Nwkid = item["_NwkId"]
        if Nwkid in self.ListOfDevices:
            IEEE = self.ListOfDevices[Nwkid]["IEEE"]
            Ep = item["Ep"]
            DeviceList.append([Nwkid, Ep, IEEE])
    return DeviceList


def newGroup(self, GrpName, item):

    self.logging("Debug", " --  -- - > Creation of Group: %s " % GrpName)
    # New Group to be added
    GrpId = get_group_id(self)
    self.logging("Debug", " --  --  -- - > GroupId: %s " % GrpId)
    self.logging("Debug", " --  --  -- - > DevicesSelected: %s " % item["devicesSelected"])
    DevicesList = []
    IEEE = ""
    for dev in item["devicesSelected"]:
        NwkId = dev["_NwkId"]
        Ep = dev["Ep"]
        if "IEEE" in dev:
            IEEE = dev["IEEE"]
        else:
            if NwkId in self.ListOfDevices:
                IEEE = self.ListOfDevices[NwkId]["IEEE"]

        # Add Device ( NwkID, Ep, IEEE) to Group GrpId
        if [NwkId, Ep, IEEE] not in DevicesList:
            DevicesList.append([NwkId, Ep, IEEE])
        self.logging("Debug", " --  --  --  -- - > Tuple to add: %s " % str([NwkId, Ep, IEEE]))
    self.logging("Debug", " --  --  -- - > GroupCreation")
    create_new_group_and_attach_devices(self, GrpId, GrpName, DevicesList)
    SendGroupIdentifyEffect(self, GrpId)


def updateGroup(self, GrpId, item):

    self.logging("Debug", " --  -- - > Update GrpId: %s " % GrpId)
    self.logging("Debug", " --  -- - > DeviceList from Web: %s " % item["devicesSelected"])

    TargetedDevices = transform_web_to_group_devices_list(self, item["devicesSelected"])
    self.logging("Debug", " --  -- - > Target DeviceList: %s " % TargetedDevices)

    ExistingDevices = self.ListOfGroups[GrpId]["Devices"]
    # Let's check if we have also Tradfri Remote 5 to be added

    ikea5b = Ikea5BToBeAddedToListIfExist(self, GrpId)
    if ikea5b and ikea5b not in self.ListOfGroups[GrpId]["Devices"]:
        self.ListOfGroups[GrpId]["Devices"].append(ikea5b)
    self.logging("Debug", " --  -- - > Existing DeviceList: %s " % ExistingDevices)

    WhatToDo = compare_exitsing_with_new_list(self, ExistingDevices, TargetedDevices)
    sendIdentify = len(WhatToDo["ToBeAdded"]) + len(WhatToDo["ToBeRemoved"])
    self.logging("Debug", " --  -- - > Devices to be added: %s " % WhatToDo["ToBeAdded"])
    update_group_and_add_devices(self, GrpId, WhatToDo["ToBeAdded"])

    self.logging("Debug", " --  -- - > Devices to be removed: %s " % WhatToDo["ToBeRemoved"])
    update_group_and_remove_devices(self, GrpId, WhatToDo["ToBeRemoved"])
    if sendIdentify > 0:
        SendGroupIdentifyEffect(self, GrpId)


def delGroup(self, GrpId):
    if GrpId not in self.ListOfGroups:
        return
    TobeRemovedDevices = self.ListOfGroups[GrpId]["Devices"]
    update_group_and_remove_devices(self, GrpId, TobeRemovedDevices)
    SendGroupIdentifyEffect(self, GrpId)


def fullGroupRemove(self):
    # Everything has to be removed.
    for GrpId in list(self.ListOfGroups.keys()):
        delGroup(self, GrpId)
