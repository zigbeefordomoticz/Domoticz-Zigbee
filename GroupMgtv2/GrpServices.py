# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

from time import time

from GroupMgtv2.GrpDomoticz import create_domoticz_group_device, remove_domoticz_group_device
from GroupMgtv2.GrpCommands import add_group_member_ship, remove_group_member_ship, look_for_group_member_ship, check_group_member_ship
from GroupMgtv2.GrpDatabase import create_group, add_device_to_group, remove_device_from_group


def GroupManagementCheckActions( self ):

    for NwkId in self.ListOfDevices:
        if 'GroupMemberShip' not in self.ListOfDevices[NwkId]:
            continue

        for ep in self.ListOfDevices[NwkId]['GroupMemberShip']:
            for GrpId in self.ListOfDevices[NwkId]['GroupMemberShip'][ ep ]:
                if self.ListOfDevices[NwkId]['GroupMemberShip'][ ep ][ GrpId ]['Status'] == 'OK':
                    continue

                if self.ListOfDevices[NwkId]['GroupMemberShip'][ ep ][ GrpId ]['TimeStamp'] + 5 > time():
                    continue

                if self.ListOfDevices[NwkId]['GroupMemberShip'][ ep ][ GrpId ]['Phase'] in 'addGroupMembeShip':
                    add_group_member_ship( self, NwkId, ep, GrpId)

                if self.ListOfDevices[NwkId]['GroupMemberShip'][ ep ][ GrpId ]['Phase'] in 'CheckgroupMemberShip':
                    check_group_member_ship( self, NwkId, ep, GrpId)

                if self.ListOfDevices[NwkId]['GroupMemberShip'][ ep ][ GrpId ]['Phase'] in 'removeGroupMemberShip':
                    remove_group_member_ship( self, NwkId, ep, GrpId)


def process_remove_group( self, unit, GroupId):
    # Call by onRemove call from Domoticz
    # The widget has been removed by Domoticz, we have to cleanup
    
    self.logging( 'Debug', "process_remove_group Unit: %s GroupId: %s" %(unit, GroupId))

    if GroupId not in self.ListOfGroups:
        return

    for NwkId, Ep, IEEE in self.ListOfGroups[ GroupId ]['Devices']:
        remove_group_member_ship( self,NwkId, Ep, GroupId )


def provision_Manufacturer_Group( self, GrpId, NwkId, Ep, Ieee):
    pass

def scan_device_for_grp_membership( self, NwkId, Ep ):
    # Ask this device for list of Group membership

    if NwkId not in self.ListOfDevices:
        return

    if 'GroupMemberShip' in self.ListOfDevices[ NwkId ]:
        del self.ListOfDevices[ NwkId ]['GroupMemberShip']

    look_for_group_member_ship(self, NwkId, Ep)

def scan_all_devices_for_grp_membership( self ):
    pass

def process_web_request( self, webInput):
    """
    Receive as GroupInput the json coming from the WebUI
    coordinatorInside:true  means Zigate must be part of the Group
    devicesSelected means a list of { EP and NwkId}
    if '_GroupId' do not exist in the list of groups, then it is about creating a new group

    """

    def get_group_id():
       for x in range( 0x0001, 0x0999):
            GrpId = '%04X' %x
            if GrpId not in self.ListOfGroups:
                return GrpId

    def create_new_group_and_attach_devices( self, GrpId, GrpName, DevicesList ):

        self.logging( 'Debug', " --  --  --  --  --  > CreateNewGroupAndAttachDevices ")
        create_group( self, GrpId, GrpName )
        create_domoticz_group_device(self, GrpName, GrpId)
        for NwkId, ep, ieee in DevicesList:
            add_group_member_ship( self, NwkId, ep, GrpId)
            add_device_to_group( self, (NwkId, ep, ieee), GrpId)

    def update_group_and_add_devices( self, GrpId, ToBeAddedDevices):

        self.logging( 'Debug', " --  --  --  --  --  > UpdateGroupAndAddDevices ")
        for NwkId, ep, ieee in ToBeAddedDevices:
            add_group_member_ship( self, NwkId, ep, GrpId)
            add_device_to_group( self, (NwkId, ep, ieee), GrpId)

    def update_group_and_remove_devices( self, GrpId, ToBeRemoveDevices):

        self.logging( 'Debug', " --  --  --  --  --  > UpdateGroupAndRemoveDevices ")
        for NwkId, ep, ieee in ToBeRemoveDevices:
            remove_device_from_group(self, (NwkId, ep, ieee), GrpId)
            remove_group_member_ship(self,  NwkId, ep, GrpId )

    def compare_exitsing_with_new_list( self, first, second):
        """
        Compare 2 lists of devices and will return a dict with toBeAdded and toBeRemoved
        """
        def diff(first, second):
            """
            Diff between first and second
            returns what is in first and not in second
            """
            Domoticz.Log("------> First: %s" %first)
            Domoticz.Log("------> Second: %s" %second)
            #second = set(second)
            return [item for item in first if item not in second]

        self.logging( 'Debug', " --  --  --  --  --  > compareExitsingWithNewList ")
        report = {}
        report['ToBeAdded'] = diff( second, first )
        report['ToBeRemoved'] = diff( first, second)
        return report

    def transform_web_to_group_devices_list( WebDeviceList ):
        self.logging( 'Debug', "TransformWebToGroupDevicesList ")
        DeviceList = []
        for item in WebDeviceList:
            Nwkid = item['_NwkId']
            if Nwkid in self.ListOfDevices:
                IEEE = self.ListOfDevices[ Nwkid ]['IEEE']
                Ep = item['Ep']
                DeviceList.append( [Nwkid, Ep, IEEE ] )
        return DeviceList

    # Begining

    self.logging( 'Debug', "processWebRequest ")
    for item in webInput:
        self.logging( 'Debug', " -- - > %s " %item)

        GrpName = item['GroupName']
        self.logging( 'Debug', " -- - > GrpName: %s " %GrpName)
        if '_GroupId' not in item:
            self.logging( 'Debug', " --  -- - > Creation of Group: %s " %GrpName)
            # New Group to be added
            GrpId = get_group_id()
            self.logging( 'Debug', " --  --  -- - > GroupId: %s " %GrpId)
            self.logging( 'Debug', " --  --  -- - > DevicesSelected: %s " %item['devicesSelected'])
            DevicesList = []
            for dev in item['devicesSelected']:
                NwkId = dev['_NwkId']
                Ep    = dev['Ep']
                if 'IEEE' in dev:
                    IEEE  = dev['IEEE']
                else:
                    if NwkId in self.ListOfDevices:
                       IEEE = self.ListOfDevices[ NwkId ]['IEEE'] 

                # Add Device ( NwkID, Ep, IEEE) to Group GrpId
                if [ NwkId, Ep, IEEE]  not in DevicesList:
                    DevicesList.append( [ NwkId, Ep, IEEE] )
                self.logging( 'Debug', " --  --  --  -- - > Tuple to add: %s " % str([NwkId, Ep, IEEE] ))
            self.logging( 'Debug', " --  --  -- - > GroupCreation" )
            create_new_group_and_attach_devices( self, GrpId, GrpName, DevicesList)
            return

        # we have to see if any groupmembership have to be added or removed
        self.logging( 'Debug', " -- - > Update GrpName: %s " %GrpName)
        GrpId = item['_GroupId']
        if GrpId not in self.ListOfGroups:
            return
        self.logging( 'Debug', " --  -- - > Update GrpId: %s " %GrpId)
        self.logging( 'Debug', " --  -- - > DeviceList from Web: %s " %item[ 'devicesSelected' ])

        TargetedDevices = transform_web_to_group_devices_list( item[ 'devicesSelected' ] )
        self.logging( 'Debug', " --  -- - > Target DeviceList: %s " %TargetedDevices)

        #if item[ 'coordinatorInside' ]:
        #    self.logging( 'Debug', " --  -- - > ZigateMemberShip ")
        #    TargetedDevices.append ( ['0000', '01', self.ZigateIEEE] )
        #    self.logging( 'Debug', " --  --  -- - > Target DeviceList Updated: %s " %TargetedDevices)

        ExistingDevices = self.ListOfGroups[ GrpId ]['Devices']
        self.logging( 'Debug', " --  -- - > Existing DeviceList: %s " %ExistingDevices)

        WhatToDo = compare_exitsing_with_new_list( self, ExistingDevices, TargetedDevices)
        self.logging( 'Debug', " --  -- - > Devices to be added: %s " %WhatToDo['ToBeAdded'])
        update_group_and_add_devices( self, GrpId, WhatToDo['ToBeAdded'])

        self.logging( 'Debug', " --  -- - > Devices to be removed: %s " %WhatToDo['ToBeRemoved'])
        update_group_and_remove_devices( self, GrpId, WhatToDo['ToBeRemoved'])