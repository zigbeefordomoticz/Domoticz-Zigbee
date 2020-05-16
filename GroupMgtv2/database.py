# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

"""
Methodes which manipulate the Groups Data Structure
- ListOfGroups is the Data structure supporting Groups
  ListOfGroups[group id]['Name']            - Group Name as it will be created in Domoticz
  ListOfGroups[group id]['Devices']         - List of Devices associed to this group on Zigate
  ListOfGroups[group id]['Tradfri Remote']  - Manage the Tradfri Remote
'WidgetStyle'
'Cluster'
'Tradfri Remote'
"Device Addr"]

"""
import os
import json

def write_groups_list( self):
    """
    write GroupsList into Disk
    """
    self.logging( 'Debug', "Dumping: %s" %self.GroupListFileName)

    with open( self.GroupListFileName , 'wt') as handle:
        json.dump( self.ListOfGroups, handle, sort_keys = True, indent = 2)

def load_groups_list_from_json( self ):
    """
    Load GroupsList into memory
    """
    if self.GroupListFileName is None:
        return

    if not os.path.isfile( self.GroupListFileName ) :
        self.logging( 'Debug', "GroupMgt - Nothing to import from %s" %self.GroupListFileName)
        return

    with open( self.GroupListFileName, 'rt') as handle:
        self.ListOfGroups = json.load( handle)

def build_group_list_from_list_of_devices( self ):
    """"
    Build the ListOfGroups from the ListOfDevices
    """
    for NwkId in self.ListOfDevices:
        if 'GroupMemberShip' not in self.ListOfDevices[ NwkId ]:
            continue
        for Ep in self.ListOfDevices[ NwkId ]['GroupMemberShip']:
            for GrpId in self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ]:
                if self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ][GrpId]['Status'] == 'OK':
                    ieee = self.ListOfDevices[ NwkId ]['IEEE']
                    device = ( NwkId, Ep, ieee)
                    self.addDeviceToGroup( device, GrpId )

def update_due_to_nwk_id_change( self, OldNwkId, NewNwkId):
    """
    Short Id of the device has changed, we need to update ListOfGroups accordingly
    """

    for GrpId in self.ListOfGroups:
        for device in self.ListOfGroups[ GrpId ]['Devices']:
            if device[0] != OldNwkId:
                continue
            # We have to update the NwkId ( update + add )
            newdevice = [ NewNwkId, device[1], device[2] ]
            self.ListOfGroups[ GrpId ]['Devices'].remove ( device )
            self.ListOfGroups[ GrpId ]['Devices'].append( newdevice )

def create_group( self, GrpId, GrpName ):

    if GrpId not in self.ListOfGroups:
        self.ListOfGroups[ GrpId ] = {}
        self.ListOfGroups[ GrpId ]['Name'] = GrpName
        self.ListOfGroups[ GrpId ]['Devices'] = []

def add_device_to_group( self, device, GrpId):
    """
    add a device ( NwkId, ep, ieee) to a group
    """

    if GrpId not in self.ListOfGroups:
        self.ListOfGroups[ GrpId ] = {}
        self.ListOfGroups[ GrpId ]['Name'] = ''
        self.ListOfGroups[ GrpId ]['Devices'] = []

    if device not in self.ListOfGroups[ GrpId ]['Devices']:
        self.ListOfGroups[ GrpId ]['Devices'].append( device )

def remove_device_from_group(self, device, GrpId):
    """
    remove a device from a group
    """

    if GrpId not in self.ListOfGroups:
        return

    if device not in self.ListOfGroups[ GrpId ]['Devices']:
        return

    self.ListOfGroups[ GrpId ]['Devices'].remove( device )

def device_list_for_group( self, GrpId):
    """
    return a list of tuples ( devices, ep, ieee) for a particular group
    """

    if GrpId not in self.ListOfGroups:
        return []
    return self.ListOfGroups[ GrpId ]['Devices']















