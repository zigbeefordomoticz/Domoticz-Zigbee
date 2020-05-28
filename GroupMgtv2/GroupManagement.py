# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

#  This is the Version 2 of Zigate Plugin Group Management.
#  
#  The aim of this Class is to be able to manage groups as they were in the previous version, 
#  but also to have instant groupmembership provisioning instead of the batch approach of the previous version.
#  
#  Important, the aim is not to break any upward compatibility
#  
#  Group management rely on 2 files:
#  
#  - ZigateGroupsConfig -xx.json which contains the Group configuration/definition
#  - GroupsList-xx.pck which contains somehow a cash of what is available on each devices 
#                      (1) will be converted to a JSON format
#  
#  
#  DATA STRUCTURES
#  
#  - Each device knowns its group membership. ( ListOfDevices)
#    Today there is an attribute 'GroupMgt' which is a list of Group with a status
#    V2 attribute 'GroupMembership' which is a dictionary of Group the device is member of.
#      - GroupId
#         - Status: TobeAdd, AddedReq, Ok, Error, ToBeRemoved, RemovedReq
#         - TimeStamp (when the Status has been set)
#  
#  - ListOfGroups is the Data structure supporting Groups
#    ListOfGroups[group id]['Name']            - Group Name as it will be created in Domoticz
#    ListOfGroups[group id]['Devices']         - List of Devices associed to this group on Zigate
#    ListOfGroups[group id]['Tradfri Remote']  - Manage the Tradfri Remote
#  
#  
#  
#  SYNOPSIS
#  
#  - At plugin start, if the group cash file exist, read and populate the data structure.
#                     if the cash doesn't exist, request to each Main Powered device tfor their existing group membership.
#                     collect the information and populate the data structure accordingly.
#  
#  - When the data structure is fully loaded, the object will be full operational and able to handle the following request
#      - adding group  membership to a specific device
#      - removing group membership to a specific device
#      - view group membership
#  
#      - actioning ( On, Off, LevelControl, ColorControl , WindowCovering )
#  
#      - Managing device short address changes ( could be better to store the IEEE )
# 
 
import os
import json
import pickle

import Domoticz

from GroupMgtv2.GrpServices import scan_device_for_grp_membership
from GroupMgtv2.GrpDatabase import build_group_list_from_list_of_devices
from GroupMgtv2.GrpDomoticz import LookForGroupAndCreateIfNeeded
from GroupMgtv2.GrpMigration import GrpMgtv2Migration


class GroupsManagement( object):

    from GroupMgtv2.GrpResponses import statusGroupRequest, remove_group_member_ship_response, look_for_group_member_ship_response, \
    check_group_member_ship_response, add_group_member_ship_response
    
    from GroupMgtv2.GrpDomoticz import update_domoticz_group_device, processCommand
    from GroupMgtv2.GrpDatabase import  write_groups_list, load_groups_list_from_json, update_due_to_nwk_id_change
    from GroupMgtv2.GrpServices import FullRemoveOfGroup, checkAndTriggerIfMajGroupNeeded, addGroupMemberShip, RemoveNwkIdFromAllGroups
    from GroupMgtv2.GrpWebServices import process_web_request, ScanAllDevicesForGroupMemberShip, ScanDevicesForGroupMemberShip
    from GroupMgtv2.GrpLogging import logging
    from GroupMgtv2.GrpIkeaRemote import manageIkeaTradfriRemoteLeftRight
    
    def __init__(self, PluginConf, ZigateComm, adminWidgets, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK , loggingFileHandle):

        self.HB = 0
        self.pluginconf = PluginConf
        self.ZigateComm = ZigateComm                # Point to the ZigateComm object
        self.adminWidgets = adminWidgets
        self.homeDirectory = HomeDirectory
        self.Devices = Devices                               # Point to the List of Domoticz Devices
        self.ListOfDevices = ListOfDevices    # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK                        # Point to the List of IEEE to NWKID
        self.ListOfGroups = {}                            # Data structutre to store all groups
        self.loggingFileHandle = loggingFileHandle
        self.GroupListFileName = None             # Filename of Group cashing file
        self.ZigateIEEE = None
        self.ScanDevicesToBeDone     = []         # List of Devices for which a GrpMemberShip request as to be performed
        self.GroupStatus = 'Starting'   # Used by WebServer to display Status of Group!

        # Check if we have to open the old format
        if os.path.isfile( self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %hardwareID    ):
            # We are in the Migration from Old Group Managemet to new.
            self.GroupStatus = 'Migration'
            with open( self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %hardwareID    , 'rb') as handle:
                self.ListOfGroups = pickle.load( handle )    # nosec

            # Migrate to new Format:
            GrpMgtv2Migration( self )

            # Save it with new format
            self.GroupListFileName = self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.json" %hardwareID
            self.write_groups_list()

            # Remove the old format
            os.remove( self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %hardwareID )
            del self.ListOfGroups
            self.ListOfGroups = {}

        # Open file and load config
        self.GroupListFileName = self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.json" %hardwareID
        self.load_groups_list_from_json()
        self.GroupStatus = 'ready'

    def updateZigateIEEE( self, ZigateIEEE):
        self.ZigateIEEE =     ZigateIEEE

    def hearbeat_group_mgt( self ):

        self.HB += 1

        #self.logging( 'Debug', 'hearbeat_group_mgt -    ScanDevicesToBeDone: %s' %( self.ScanDevicesToBeDone))

        # Check if we have some Scan to be done
        for    NwkId, Ep in self.ScanDevicesToBeDone: 
            self.GroupStatus = 'scan'
            if len(self.ZigateComm.zigateSendingFIFO) < 3:
                    self.ScanDevicesToBeDone.remove ( [ NwkId, Ep ] )
                    scan_device_for_grp_membership( self, NwkId, Ep )

        if len(self.ScanDevicesToBeDone) == 0:
            self.GroupStatus = 'ready'
        else:
            self.GroupStatus = 'scan'
            
        # Group Widget are updated based on Device update
        # Might be good to do the update also on a regular basic
        if (self.HB % 2 ) == 0:
            for GroupId in self.ListOfGroups:
                self.update_domoticz_group_device( GroupId )
