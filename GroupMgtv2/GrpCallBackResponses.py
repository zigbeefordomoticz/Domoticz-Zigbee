# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
from GroupMgtv2.GrpDomoticz import create_domoticz_group_device, remove_domoticz_group_device, update_domoticz_group_device, update_domoticz_group_device_widget
from GroupMgtv2.GrpDatabase import write_groups_list, create_group, add_device_to_group, remove_device_from_group




def checkToCreateOrUpdateGroup( self, NwkId, Ep, GroupId):
    """ 
    Trigger from addGroupMemberShipResponse or checkGroupMemberShip
    (1) Update ListOfGroups datastructutre
    (2) check if a Group has to be created in the Database and in Domoticz
    """

    self.logging( 'Debug', "checkToCreateGroup NwkId: %s Ep: %s GrouId: %s" %(NwkId, Ep, GroupId))
    if 'IEEE' not in self.ListOfDevices[ NwkId]:
        return

    Ieee = self.ListOfDevices[ NwkId]['IEEE']

    if GroupId not in self.ListOfGroups:
        self.logging( 'Debug', "-------> Needs to Create a Group GrouId: %s" %( GroupId))
        GrpName = 'Zigate Group ' + GroupId
        create_group( self, GroupId, GrpName )
        create_domoticz_group_device(self, GrpName, GroupId)

    self.logging( 'Debug', "-------> Adding Device %s to Group GrouId: %s" %(NwkId, GroupId)) 
    add_device_to_group( self, [ NwkId, Ep, Ieee ] , GroupId)
    update_domoticz_group_device_widget( self, GroupId )
    self.write_groups_list()

def checkToRemoveGroup( self, NwkId, Ep, GroupId ):
    """ 
    Trigger from removeGroupMemberShip
    (1) Update ListOgGroups dataStructutre
    (2) check if a Group has to be created in the Database and in Domoticz
    """

    self.logging( 'Debug', "checkToRemoveGroup NwkId: %s Ep: %s GrouId: %s" %(NwkId, Ep, GroupId))
    if 'IEEE' not in self.ListOfDevices[ NwkId]:
        return
    Ieee = self.ListOfDevices[ NwkId]['IEEE']
    self.logging( 'Debug', "-------> Removing Device %s from Group GrouId: %s" %(NwkId, GroupId)) 
    remove_device_from_group(self, [ NwkId, Ep, Ieee ], GroupId)

    if GroupId in self.ListOfGroups:
        update_domoticz_group_device_widget( self, GroupId )
        self.write_groups_list()
        return

    self.logging( 'Debug', "-------> Needs to Remove Group GrouId: %s" %(GroupId))
    remove_domoticz_group_device( self, GroupId )
    self.write_groups_list()