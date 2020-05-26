# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
import Domoticz

from time import time

from Modules.tools import mainPoweredDevice

from GroupMgtv2.GrpDomoticz import create_domoticz_group_device, remove_domoticz_group_device

from GroupMgtv2.GrpIkeaRemote import checkIfIkeaRound5BToBeAdded, checkIfIkeaRound5BToBeRemoved

# remove_domoticz_group_device, update_domoticz_group_device
from GroupMgtv2.GrpDatabase import create_group, checkNwkIdAndUpdateIfAny, remove_nwkid_from_all_groups, check_if_group_empty, remove_group
from GroupMgtv2.GrpCommands import remove_group_member_ship, add_group_member_ship, check_group_member_ship, look_for_group_member_ship, send_group_member_ship_identify_effect


def checkAndTriggerIfMajGroupNeeded( self, NwkId, Ep, ClusterId):
    """
    This method is call from MajDomoDevice and onCommand because there is an update of a particular Device Cluster/Attribute
    We will then check if that impact a group and in that case trigger the update of such group
    """

    if ( 'GroupMemberShip' in self.ListOfDevices[NwkId] and Ep in self.ListOfDevices[NwkId]['GroupMemberShip'] ):
        for GrpId in self.ListOfDevices[ NwkId ]['GroupMemberShip'][Ep]:
            self.update_domoticz_group_device( GrpId )

def check_existing_membership( self):
    # For each group, check the group membership of the identified device
    for GrpId in self.ListOfGroups:
        for NwkId, Ep, Ieee in self.ListOfGroups[ GrpId ]['Devices']:
            check_group_member_ship( self, NwkId, Ep, GrpId )

def RemoveNwkIdFromAllGroups( self, Nwkid):
    " call my plugin when removing one device"
    self.logging( 'Debug', "RemoveNwkIdFromAllGroups - Remove Nwk from all groups: %s" %Nwkid)
    remove_nwkid_from_all_groups( self, Nwkid)

    # Check if any groups are empty. If so remove the Domoticz Widget
    self.logging( 'Debug', "RemoveNwkIdFromAllGroups - ListOfGroups: %s" %str(self.ListOfGroups.keys()))
    for GrpId in self.ListOfGroups:
        if check_if_group_empty( self, GrpId):
            self.logging( 'Debug', "RemoveNwkIdFromAllGroups - Empty Group: %s" %GrpId)
            remove_group( self, GrpId)
            remove_domoticz_group_device( self, GrpId)
    self.write_groups_list()

def FullRemoveOfGroup( self, unit, GroupId):
    # Call by onRemove call from Domoticz
    # The widget has been removed by Domoticz, we have to cleanup
    self.logging( 'Debug', "process_remove_group Unit: %s GroupId: %s" %(unit, GroupId))
    if GroupId not in self.ListOfGroups:
        return
    for NwkId, Ep, IEEE in self.ListOfGroups[ GroupId ]['Devices']:
        NwkId = checkNwkIdAndUpdateIfAny( self, NwkId, IEEE )
        if NwkId:
            remove_group_member_ship( self,NwkId, Ep, GroupId )
    self.write_groups_list()

def provision_Manufacturer_Group( self, GrpId, NwkId, Ep, Ieee):
    pass

def scan_device_for_grp_membership( self, NwkId, Ep ):
    # Ask this device for list of Group membership
    self.logging( 'Debug', " --  --  --  --  --  > scan_device_for_grp_membership ")
    if NwkId not in self.ListOfDevices:
        return
    
    # Remove Group MemverShip from Device
    if 'GroupMemberShip' in self.ListOfDevices[ NwkId ]:
        del self.ListOfDevices[ NwkId ]['GroupMemberShip']

    # Remove Group MemberShip from Group, as we will check.
    RemoveNwkIdFromAllGroups( self, NwkId )

    # Finaly submit the request
    look_for_group_member_ship(self, NwkId, Ep)

def submitForGroupMemberShipScaner( self, NwkId, Ep):
    
    if len(self.ZigateComm.zigateSendingFIFO) >= 1:
        self.ScanDevicesToBeDone.append ( [ NwkId, Ep ] )
    else:
        scan_device_for_grp_membership( self, NwkId, Ep )

def scan_all_devices_for_grp_membership( self ):
    for NwkId in self.ListOfDevices:
        if not mainPoweredDevice( self, NwkId):
            continue
        for Ep in self.ListOfDevices[ NwkId ]['Ep']:
            if '0004' not in self.ListOfDevices[ NwkId ]['Ep'][Ep]:
                continue
            submitForGroupMemberShipScaner( self, NwkId, Ep)

def addGroupMemberShip( self, NwkId, Ep, GroupId):
    """
    call from plugin
    """
    add_group_member_ship( self, NwkId, Ep, GroupId)
    self.write_groups_list()

def create_new_group_and_attach_devices( self, GrpId, GrpName, DevicesList ):
    self.logging( 'Debug', " --  --  --  --  --  > CreateNewGroupAndAttachDevices ")
    create_group( self, GrpId, GrpName )
    create_domoticz_group_device(self, GrpName, GrpId)
    for NwkId, ep, ieee in DevicesList:
        add_group_member_ship( self, NwkId, ep, GrpId)
    send_group_member_ship_identify_effect( self, GrpId )
    self.write_groups_list()

def update_group_and_add_devices( self, GrpId, ToBeAddedDevices):
    self.logging( 'Debug', " --  --  --  --  --  > UpdateGroupAndAddDevices ")
    for NwkId, ep, ieee in ToBeAddedDevices:
        NwkId = checkNwkIdAndUpdateIfAny( self, NwkId, ieee )
        # Ikea Tradfri Round5B will be added if required by checkIfIkeaRound5B
        if NwkId and not checkIfIkeaRound5BToBeAdded( self, NwkId, ep, ieee, GrpId):
            add_group_member_ship( self, NwkId, ep, GrpId)
    send_group_member_ship_identify_effect( self, GrpId )
    self.write_groups_list()

def update_group_and_remove_devices( self, GrpId, ToBeRemoveDevices):
    self.logging( 'Debug', " --  --  --  --  --  > UpdateGroupAndRemoveDevices ")
    for NwkId, ep, ieee in ToBeRemoveDevices:
        self.logging( 'Debug', "-- --  --  --  --  --  > Removing [%s %s %s]" %(NwkId, ep, ieee ))
        NwkId = checkNwkIdAndUpdateIfAny( self, NwkId, ieee )
        # Ikea Tradfri Round5B will be removed if required by checkIfIkeaRound5B
        if NwkId and not checkIfIkeaRound5BToBeRemoved( self, NwkId, ep, ieee, GrpId):
            self.logging( 'Debug', "-- --  --  --  --  --  -- > Calling Remove_group_membership [%s %s %s]" %(NwkId, ep, ieee ))
            remove_group_member_ship(self,  NwkId, ep, GrpId )
    send_group_member_ship_identify_effect( self, GrpId )
    self.write_groups_list()