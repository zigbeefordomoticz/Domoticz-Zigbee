#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

"""
ListOfGroups[group id]['Name']    - Group Name as it will be created in Domoticz
ListOfGroups[group id]['Devices'] - List of Devices associed to this group on Zigate
ListOfGroups[group id]['Imported']- List of Devices to be associated to the group. We might have some removal, or some addiional from previous run
ListOfGroups[group id]['Tradfri Remote']- Manage the Tradfri Remote

self.ListOfDevices[nwkid]['GroupMgt'][Ep][GroupID]['Phase'] = 'OK-Membership' / 'REQ-Membership' / 'DEL-Membership'
self.ListOfDevices[nwkid]['GroupMgt'][Ep][GroupID]['Phase-Stamp'] = time()
"""

import Domoticz
import json
import pickle
import os.path

from time import time
from datetime import datetime

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.zigateConsts import ADDRESS_MODE, MAX_LOAD_ZIGATE, ZIGATE_EP

from Classes.AdminWidgets import AdminWidgets


GROUPS_CONFIG_FILENAME = "ZigateGroupsConfig"
TIMEOUT = 12
MAX_CYCLE = 3

def _copyfile( source, dest, move=True ):
    
    try:
        import shutil
        if move:
            shutil.move( source, dest)
        else:
            shutil.copy( source, dest)
    except:
        with open(source, 'r') as src, open(dest, 'wt') as dst:
            for line in src:
                dst.write(line)
        return


class GroupsManagement(object):

    from GroupMgt.heartbeat import hearbeatGroupMgt
    from GroupMgt.logging import logging
    from GroupMgt.domoticz import deviceChangeNetworkID,  _createDomoGroupDevice, _updateDeviceListAttribute, _updateDomoGroupDeviceWidget, _updateDomoGroupDeviceWidgetName, \
                            _bestGroupWidget, updateDomoGroupDevice, _removeDomoGroupDevice, processCommand, processRemoveGroup
    from GroupMgt.config import _write_GroupList, _load_GroupList, load_ZigateGroupConfiguration, load_jsonZigateGroupConfig, write_jsonZigateGroupConfig, _write_GroupList
    from GroupMgt.com import _addGroup, statusGroupRequest, addGroupResponse, _viewGroup, viewGroupResponse, _getGroupMembership, getGroupMembershipResponse,\
                            _removeGroup, _getGroupMembership, _removeAllGroups, _addGroupifIdentify, removeGroupResponse, _identifyEffect, set_Kelvin_Color, set_RGB_color

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK , loggingFileHandle):
        self.StartupPhase = 'start'
        self._SaveGroupFile = None
        self.ListOfGroups = {}      # Data structutre to store all groups
        self.TobeAdded = []         # List of IEEE/NWKID/EP/GROUP to be added
        self.TobeRemoved = []       # List of NWKID/EP/GROUP to be removed
        self.UpdatedGroups = []     # List of Groups to be updated and so trigger the Identify at the end.
        self.Cycle = 0              # Cycle count
        self.HB = 0
        self.stillWIP = True
        self.txt_last_update_ConfigFile = self. json_last_update_ConfigFile = 0

        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK            # Point to the List of IEEE to NWKID
        self.Devices = Devices              # Point to the List of Domoticz Devices
        self.adminWidgets = adminWidgets

        self.fullScan = True
        self.targetDevices = []
        self.ZigateComm = ZigateComm        # Point to the ZigateComm object
        self.pluginconf = PluginConf
        self.loggingFileHandle = loggingFileHandle

        self.Firmware = None
        self.homeDirectory = HomeDirectory

        self.groupsConfigFilename = self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".txt"
        if not os.path.isfile(self.groupsConfigFilename) :
            self.groupsConfigFilename = self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + ".txt"
            if not os.path.isfile(self.groupsConfigFilename):
                self.groupsConfigFilename = None

        # Starting 4.6 GROUPS_CONFIG_FILENAME must be store under Data and not Conf folder
        self.json_groupsConfigFilename = self.pluginconf.pluginConf['pluginData'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".json"
        if os.path.isfile( self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".json" ):
            # Let's move it to Data
            self.logging( 'Status', "Moving %s to Data %s" %(self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".json",
                self.json_groupsConfigFilename))
            _copyfile( self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".json", self.json_groupsConfigFilename, move=True)

        self.groupListReport = self.pluginconf.pluginConf['pluginReports'] + "GroupList-%02d.json" %hardwareID
        self.groupListFileName = self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %hardwareID 


    def addGroupMembership( self, device_addr, device_ep, grp_id):
    
        if device_addr not in self.ListOfDevices:
            return
        if 'IEEE' not in self.ListOfDevices[device_addr]:
            return
        device_ieee = self.ListOfDevices[device_addr]['IEEE']
        if grp_id not in self.ListOfGroups:
            self.ListOfGroups[grp_id] = {}
            self.ListOfGroups[grp_id]['Name'] = 'Group ' + str(grp_id)
            self.ListOfGroups[grp_id]['Devices'] = []

        if ( device_addr, device_ep, device_ieee) not in self.ListOfGroups[grp_id]['Devices']:
            self.ListOfGroups[grp_id]['Devices'].append( ( device_addr, device_ep, device_ieee) )
            self.logging( 'Log', "Adding %s groupmembership to device: %s/%s" %(grp_id, device_addr, device_ep))
            self._addGroup( device_ieee, device_addr, device_ep, grp_id)

            for filename in ( self.json_groupsConfigFilename, self.groupListFileName ):
                if os.path.isfile( filename ):
                    self.logging( 'Log', "rest_rescan_group - Removing file: %s" %filename )
                    os.remove( filename )