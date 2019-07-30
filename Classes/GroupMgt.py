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

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.consts import ADDRESS_MODE, MAX_LOAD_ZIGATE

from Classes.AdminWidgets import AdminWidgets


GROUPS_CONFIG_FILENAME = "ZigateGroupsConfig"
TIMEOUT = 12
MAX_CYCLE = 3

class GroupsManagement(object):

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, ScanGroupMembership, Devices, ListOfDevices, IEEE2NWK ):
        self.StartupPhase = 'init'
        self._SaveGroupFile = None
        self.ListOfGroups = {}      # Data structutre to store all groups
        self.TobeAdded = []         # List of IEEE/NWKID/EP/GROUP to be added
        self.TobeRemoved = []       # List of NWKID/EP/GROUP to be removed
        self.UpdatedGroups = []     # List of Groups to be updated and so trigger the Identify at the end.
        self.Cycle = 0              # Cycle count
        self.stillWIP = True
        self.txt_last_update_ConfigFile = self. json_last_update_ConfigFile = 0

        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK            # Point to the List of IEEE to NWKID
        self.Devices = Devices              # Point to the List of Domoticz Devices
        self.adminWidgets = adminWidgets

        self.ScanGroupMembership = ScanGroupMembership

        self.ZigateComm = ZigateComm        # Point to the ZigateComm object

        self.pluginconf = PluginConf

        self.Firmware = None
        self.homeDirectory = HomeDirectory

        self.groupsConfigFilename = self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".txt"
        if not os.path.isfile(self.groupsConfigFilename) :
            self.groupsConfigFilename = self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + ".txt"
            if not os.path.isfile(self.groupsConfigFilename):
                self.groupsConfigFilename = None

        self.json_groupsConfigFilename = self.pluginconf.pluginConf['pluginConfig'] + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".json"
        #if not os.path.isfile( self.json_groupsConfigFilename ):
        #        Domoticz.Debug("No Json Groups Configuration File")
        #        self.json_groupsConfigFilename = None

        self.groupListReport = self.pluginconf.pluginConf['pluginReports'] + "GroupList-%02d.json" %hardwareID
        self.groupListFileName = self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %hardwareID 

        return

    def logging( self, logType, message):

        self.debugGroups = self.pluginconf.pluginConf['debugGroups']
        if logType == 'Debug' and self.debugGroups:
            Domoticz.Log( message)
        elif logType == 'Log':
            Domoticz.Log( message )
        elif logType == 'Status':
            Domoticz.Status( message)
        return

    def updateFirmware( firmware ):
        self.Firmware = firmware

    def _identifyEffect( self, nwkid, ep, effect='Okay' ):
        # Quick and Dirty as this exist already in the Module.

        '''
            Blink   / Light is switched on and then off (once)
            Breathe / Light is switched on and off by smoothly increasing and
                    then decreasing its brightness over a one-second period,
                    and then this is repeated 15 times
            Okay    / •  Colour light goes green for one second
                    •  Monochrome light flashes twice in one second
        '''
    
        effect_command = { 'Blink': 0x00 ,
                'Breathe': 0x01,
                'Okay': 0x02,
                'ChannelChange': 0x0b,
                'FinishEffect': 0xfe,
                'StopEffect': 0xff }
    
        self.logging( 'Debug', "Identify effect for Group: %s" %nwkid)
        identify = False
        if effect not in effect_command:
            effect = 'Okay'
        datas = "%02d" %ADDRESS_MODE['group'] + "%s"%(nwkid) + "01" + ep + "%02x"%(effect_command[effect])  + "%02x" %0
        self.ZigateComm.sendData( "00E0", datas)

    def _write_GroupList(self):
        ' serialize pickle format the ListOfGrups '

        self.logging( 'Debug', "Write %s" %self.groupListFileName)
        self.logging( 'Debug', "Dumping: %s" %self.ListOfGroups)
        with open( self.groupListFileName , 'wb') as handle:
            pickle.dump( self.ListOfGroups, handle, protocol=pickle.HIGHEST_PROTOCOL)
        self.HBcount=0


    def _load_GroupList(self):
        ' unserialized (load) ListOfGroup from file'

        self.ListOfGroups = {}
        if os.path.isfile( self.groupListFileName ):
            with open( self.groupListFileName , 'rb') as handle:
                self.ListOfGroups = pickle.load( handle )
            for grpid in self.ListOfGroups:
                if 'Imported' in self.ListOfGroups[grpid]:
                    del self.ListOfGroups[grpid]['Imported']
                self.ListOfGroups[grpid]['Imported'] = []
        self.logging( 'Debug', "Loading ListOfGroups: %s" %self.ListOfGroups)

    def load_jsonZigateGroupConfig( self ):

        if self.json_groupsConfigFilename is None:
            return
        if not os.path.isfile( self.json_groupsConfigFilename ) :
            self.logging( 'Debug', "GroupMgt - Nothing to import from %s" %self.json_groupsConfigFilename)
            return
                
        with open( self.json_groupsConfigFilename, 'rt') as handle:
            ZigateGroupConfig = json.load( handle)

        for group_id in ZigateGroupConfig:
            self.logging( 'Debug', " )> Group ID: %s" %group_id)
            if group_id not in self.ListOfGroups:
                self.logging( 'Debug', "  - Init ListOfGroups")
                self.ListOfGroups[group_id] = {}
                self.ListOfGroups[group_id]['Name'] = ''
                self.ListOfGroups[group_id]['Devices'] = []
                self.ListOfGroups[group_id]['Imported'] = []
            if 'Imported' not in self.ListOfGroups[group_id]:
                self.ListOfGroups[group_id]['Imported'] = []
            if 'Devices' not in self.ListOfGroups[group_id]:
                self.ListOfGroups[group_id]['Devices'] = []
            if 'Name' not in self.ListOfGroups[group_id]:
                self.ListOfGroups[group_id]['Name'] = ZigateGroupConfig[group_id]['Name']
            else:
                if self.ListOfGroups[group_id]['Name'] == '':
                    self.ListOfGroups[group_id]['Name'] = ZigateGroupConfig[group_id]['Name']
            self.logging( 'Debug', " )> Group Name: %s" %ZigateGroupConfig[group_id]['Name'])
            if 'Tradfri Remote' in ZigateGroupConfig[group_id]:
                self.ListOfGroups[group_id]['Tradfri Remote'] = ZigateGroupConfig[group_id]['Tradfri Remote']
            if 'Imported' in ZigateGroupConfig[group_id]:
                self.ListOfGroups[group_id]['Imported'] = list(ZigateGroupConfig[group_id]['Imported'])

            self.logging( 'Debug', "load_ZigateGroupConfiguration - Group[%s]: %s List of Devices: %s to be processed" 
                %( group_id, self.ListOfGroups[group_id]['Name'], str(self.ListOfGroups[group_id]['Imported'])))


    def write_jsonZigateGroupConfig( self ):

        self.logging( 'Debug', "ListOfGroups: %s" %self.ListOfGroups)
        zigateGroupConfig = {}
        for group_id in self.ListOfGroups:
            zigateGroupConfig[group_id] = {}
            zigateGroupConfig[group_id]['Name'] =  self.ListOfGroups[group_id]['Name']
            if 'Imported' in self.ListOfGroups[group_id]:
                zigateGroupConfig[group_id]['Imported'] = list(self.ListOfGroups[group_id]['Imported'])
            if 'Tradfri Remote' in self.ListOfGroups[group_id]:
                zigateGroupConfig[group_id]['Tradfri Remote'] = self.ListOfGroups[group_id]['Tradfri Remote'] 

        self.logging( 'Debug', "Dumping: %s" %zigateGroupConfig)
        self.logging( 'Debug', "Write to : %s" %self.json_groupsConfigFilename)
        with open( self.json_groupsConfigFilename , 'wt') as handle:
            json.dump( zigateGroupConfig, handle, sort_keys=True, indent=2)


    def load_ZigateGroupConfiguration(self):
        """ This is to import User Defined/Modified Groups of Devices for processing in the hearbeatGroupMgt
        Syntax is : <groupid>,<group name>,<list of device IEEE
        """

        if self.groupsConfigFilename is None:
            return
        if not os.path.isfile( self.groupsConfigFilename ) :
            self.logging( 'Debug', "GroupMgt - Nothing to import")
            return
                
        myfile = open( self.groupsConfigFilename, 'r')
        self.logging( 'Debug', "load_ZigateGroupConfiguration. Reading the file")
        while True:
            tmpread = myfile.readline().replace('\n', '')
            self.logging( 'Debug', "line: %s" %tmpread )
            if not tmpread:
                break
            if tmpread[0] == '#':
                continue
            group_id = group_name = None
            for token in tmpread.split(','):
                if group_id is None:
                    # 1st item: group id
                    group_id = str(token).strip(' ')
                    if group_id not in self.ListOfGroups:
                        self.logging( 'Debug', "  - Init ListOfGroups")
                        self.ListOfGroups[group_id] = {}
                        self.ListOfGroups[group_id]['Name'] = ''
                        self.ListOfGroups[group_id]['Devices'] = []
                        self.ListOfGroups[group_id]['Imported'] = []
                    if 'Imported' not in self.ListOfGroups[group_id]:
                        self.ListOfGroups[group_id]['Imported'] = []
                    if 'Devices' not in self.ListOfGroups[group_id]:
                        self.ListOfGroups[group_id]['Devices'] = []
                    self.logging( 'Debug', " )> Group ID: %s" %group_id)
                    continue
                elif group_id and group_name is None:
                    # 2nd item: group name
                    group_name = str(token)
                    if 'Name' not in self.ListOfGroups[group_id]:
                        self.ListOfGroups[group_id]['Name'] = group_name
                    else:
                        if self.ListOfGroups[group_id]['Name'] == '':
                            self.ListOfGroups[group_id]['Name'] = group_name
                    self.logging( 'Debug', " )> Group Name: %s" %group_name)
                    continue
                else:
                    # Last part, list of IEEE
                    if group_id and group_name and token.strip() != '':
                        _ieeetoken = token.strip()
                        if  len(_ieeetoken.split('/')) == 1 :
                            _ieee = _ieeetoken
                            _ieeeEp = None
                        elif len(_ieeetoken.split('/')) == 2:
                            _ieee, _ieeeEp = _ieeetoken.split('/')
                        else:
                            Domoticz.Error("load_ZigateGroupConfiguration - Error in ZigateGroupConfig: %s" %( _ieeetoken))
                            continue
                        if _ieee not in self.IEEE2NWK:
                            # Check if this is not the Zigate itself
                            Domoticz.Error("load_ZigateGroupConfiguration - Unknown address %s to be imported" %_ieee )
                            continue
                        # Finaly, let's check if this is not an IKEA Tradfri Remote
                        nwkid = self.IEEE2NWK[_ieee]
                        _tradfri_remote = False
                        if 'Ep' in self.ListOfDevices[nwkid]:
                            if '01' in self.ListOfDevices[nwkid]['Ep']:
                                if 'ClusterType' in self.ListOfDevices[nwkid]['Ep']['01']:
                                    for iterDev in self.ListOfDevices[nwkid]['Ep']['01']['ClusterType']:
                                        if self.ListOfDevices[nwkid]['Ep']['01']['ClusterType'][iterDev] == 'Ikea_Round_5b':
                                            # We should not process it through the group.
                                            self.logging( 'Log', "Not processing Ikea Tradfri as part of Group. Will enable the Left/Right actions")
                                            self.ListOfGroups[group_id]['Tradfri Remote'] = {}
                                            self.ListOfGroups[group_id]['Tradfri Remote']['Device Addr'] = nwkid
                                            self.ListOfGroups[group_id]['Tradfri Remote']['Device Id'] = iterDev
                                            _tradfri_remote = True
                        if not _tradfri_remote:
                            # Let's check if we don't have the EP included as well
                            self.ListOfGroups[group_id]['Imported'].append( (_ieee, _ieeeEp) )

                    self.logging( 'Debug', " )> Group Imported: %s" %group_name)
            if group_id :
                self.logging( 'Debug', "load_ZigateGroupConfiguration - Group[%s]: %s List of Devices: %s to be processed" 
                    %( group_id, self.ListOfGroups[group_id]['Name'], str(self.ListOfGroups[group_id]['Imported'])))
        myfile.close()

    # Zigate group related commands
    def _addGroup( self, device_ieee, device_addr, device_ep, grpid):

        if grpid not in self.ListOfGroups:
            Domoticz.Error("_addGroup - skip as %s is not in %s" %(grpid, str(self.ListOfGroups)))
            return

        if grpid not in self.UpdatedGroups:
            self.UpdatedGroups.append(grpid)

        self.logging( 'Debug', "_addGroup - Adding device: %s/%s into group: %s" \
                %( device_addr, device_ep, grpid))
        datas = "02" + device_addr + "01" + device_ep + grpid
        self.ZigateComm.sendData( "0060", datas)

        return

    def statusGroupRequest( self, MsgData):
        """
        This is a 0x8000 message
        """
        Status=MsgData[0:2]
        SEQ=MsgData[2:4]
        PacketType=MsgData[4:8]

        if Status != '00':
            self.logging( 'Log', "statusGroupRequest - Status: %s for Command: %s" %(Status, PacketType))
        return

    def addGroupResponse(self, MsgData):
        ' decoding 0x8060 '

        self.logging( 'Debug', "addGroupResponse - MsgData: %s (%s)" %(MsgData,len(MsgData)))
        # search for the Group/dev
        if len(MsgData) == 14:  # Firmware < 030f
            MsgSrcAddr = None
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            self.logging( 'Debug', "addGroupResponse < 3.0f- [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

        elif len(MsgData) == 18:    # Firmware >= 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            MsgSrcAddr = MsgData[14:18]
            self.logging( 'Debug', "addGroupResponse >= 3.0f - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
        else:
            Domoticz.Error("addGroupResponse - uncomplete message %s" %MsgData)
            
        if MsgSrcAddr not in self.ListOfDevices:
               Domoticz.Error("Requesting to add group %s membership on non existing device %s" %(MsgGroupID, MsgSrcAddr))
               return

        if 'GroupMgt' not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'] = {}
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP] = {}
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID] = {}
        if MsgEP not in self.ListOfDevices[MsgSrcAddr]['GroupMgt']:
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP] = {}
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID] = {}
        if MsgGroupID not in self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP]:
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID] = {}

        self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]['Phase'] = 'OK-Membership'

        if MsgStatus != '00':
            if MsgStatus in ( '8a','8b') :
                self.logging( 'Debug', "addGroupResponse - Status: %s - Remove the device from Group" %MsgStatus)
                self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]['Phase'] = 'DEL-Membership'
                self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]['Phase-Stamp'] = int(time())
                self._removeGroup(  MsgSrcAddr, MsgEP, MsgGroupID )
        return

    def _viewGroup( self, device_addr, device_ep, goup_addr ):

        self.logging( 'Debug', "_viewGroup - addr: %s ep: %s group: %s" %(device_addr, device_ep, goup_addr))
        datas = "02" + device_addr + "01" + device_ep + goup_addr
        self.ZigateComm.sendData( "0061", datas)
        return

    def viewGroupResponse( self, MsgData):
        ' Decode 0x8061'

        MsgSequenceNumber=MsgData[0:2]
        MsgEP=MsgData[2:4]
        MsgClusterID=MsgData[4:8]
        MsgDataStatus=MsgData[8:10]
        MsgGroupID=MsgData[10:14]
        MsgSrcAddr=MsgData[14:18]

        self.logging( 'Debug', "Decode8061 - SEQ: %s, Source: %s EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgSrcAddr, MsgEP, MsgClusterID, MsgGroupID, MsgDataStatus))
        return


    def _getGroupMembership(self, device_addr, device_ep, group_list=None):

        self.logging( 'Debug', "_getGroupMembership - %s/%s from %s" %(device_addr, device_ep, group_list))
        datas = "02" + device_addr + "01" + device_ep 

        if not group_list:
            lenGrpLst = 0
            datas += "00"
        else:
            if not isinstance(group_list, list):
                # We received only 1 group
                group_list_ = "%04x" %(group_list)
                lenGrpLst = 1
            else:
                lenGrpLst = len(goup_list)
                for x in goup_list:
                    group_list_ += "%04x" %(x)
            datas += "%02.x" %(lenGrpLst) + group_list_

        self.logging( 'Debug', "_getGroupMembership - Addr: %s Ep: %s to Group: %s" %(device_addr, device_ep, group_list))
        self.logging( 'Debug', "_getGroupMembership - 0062/%s" %datas)
        self.ZigateComm.sendData( "0062", datas)
        return

    def getGroupMembershipResponse( self, MsgData):
        ' Decode 0x8062 '

        lenMsgData = len(MsgData)

        MsgSequenceNumber=MsgData[0:2]
        MsgEP=MsgData[2:4]
        MsgClusterID=MsgData[4:8]

        MsgCapacity=MsgData[8:10]
        MsgGroupCount=MsgData[10:12]
        MsgListOfGroup=MsgData[12:lenMsgData-4]
        MsgSourceAddress = MsgData[lenMsgData-4:lenMsgData]

        self.logging( 'Debug', "getGroupMembershipResponse - SEQ: %s, EP: %s, ClusterID: %s, sAddr: %s, Capacity: %s, Count: %s"
                %(MsgSequenceNumber, MsgEP, MsgClusterID, MsgSourceAddress, MsgCapacity, MsgGroupCount))

        if MsgSourceAddress not in self.ListOfDevices:
            Domoticz.Error('getGroupMembershipResponse - receiving a group memebership for a non exsiting device')
            Domoticz.Error('getGroupMembershipResponse - %s %s %s' %(MsgSourceAddress, MsgGroupCount, MsgListOfGroup))
            return

        if 'GroupMgt' not in self.ListOfDevices[MsgSourceAddress]:
            self.ListOfDevices[MsgSourceAddress]['GroupMgt'] = {}
            self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP] = {}

        idx =  0
        while idx < int(MsgGroupCount,16):
            groupID = MsgData[12+(idx*4):12+(4+(idx*4))]

            if groupID not in self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]:
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID] = {}
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase'] = {}
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase-Stamp'] = {}

            if self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase'] not in ( {}, 'REQ-Membership') :
                self.logging( 'Debug', "getGroupMembershipResponse - not in the expected Phase : %s for %s/%s - %s" 
                    %(self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase'], MsgSourceAddress, MsgEP, groupID))

            self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase'] = 'OK-Membership'
            self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase-Stamp'] = 0

            if groupID not in self.ListOfGroups:
                self.ListOfGroups[groupID] = {}
                self.ListOfGroups[groupID]['Name'] = ''
                self.ListOfGroups[groupID]['Devices'] = []
                self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP) )
            else:
                if ( MsgSourceAddress,MsgEP) not in self.ListOfGroups[groupID]['Devices']:
                    self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP) )

            self.logging( 'Debug', "getGroupMembershipResponse - ( %s,%s ) is part of Group %s"
                    %( MsgSourceAddress, MsgEP, groupID))
                
            idx += 1
        return

    def _removeGroup(self,  device_addr, device_ep, goup_addr ):

        if goup_addr not in self.UpdatedGroups:
            self.UpdatedGroups.append(goup_addr)

        self.logging( 'Debug', "_removeGroup - %s/%s on %s" %(device_addr, device_ep, goup_addr))
        datas = "02" + device_addr + "01" + device_ep + goup_addr
        self.ZigateComm.sendData( "0063", datas)
        return

    def removeGroupResponse( self, MsgData):
        ' Decode 0x8063'

        if len(MsgData) == 14:  # Firmware < 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            MsgSrcAddr = None
            self.logging( 'Debug', "removeGroupResponse < 3.0f - [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

        elif len(MsgData) == 18:    # Firmware >= 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            MsgSrcAddr = MsgData[14:18]
            self.logging( 'Debug', "removeGroupResponse >= 3.0f - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
        else:
            Domoticz.Error("removeGroupResponse - uncomplete message %s" %MsgData)

        self.logging( 'Debug', "Decode8063 - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgStatus))

        if MsgStatus in ( '00' ) :
            if MsgSrcAddr : # 3.0f
                if 'GroupMgt' in self.ListOfDevices[MsgSrcAddr]:
                    if MsgEP in self.ListOfDevices[MsgSrcAddr]['GroupMgt']:
                        if MsgGroupID in self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP]:
                            del  self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]

                self.logging( 'Debug', "Decode8063 - self.ListOfGroups: %s" %str(self.ListOfGroups))
                if MsgGroupID in self.ListOfGroups:
                    if (MsgSrcAddr, MsgEP) in self.ListOfGroups[MsgGroupID]['Devices']:
                        self.logging( 'Debug', "removeGroupResponse - removing %s from %s" %( str(( MsgSrcAddr, MsgEP)), str(self.ListOfGroups[MsgGroupID]['Devices'])))
                        self.ListOfGroups[MsgGroupID]['Devices'].remove( ( MsgSrcAddr, MsgEP) )
            else: # < 3.0e should not happen
                self.logging( 'Log', "Group Member removed from unknown device")
                unique = 0
                delDev = ''
                for iterDev in self.ListOfDevices:
                    if 'GroupMgt' in self.ListOfDevices[iterDev]:
                        if MsgEP in self.ListOfDevices[iterDev]['GroupMgt']:
                            if MsgGroupID in self.ListOfDevices[iterDev]['GroupMgt'][MsgEP]:
                                if 'Phase' in self.ListOfDevices[iterDev]['GroupMgt'][MsgEP][MsgGroupID]:
                                    if self.ListOfDevices[iterDev]['GroupMgt'][MsgEP][MsgGroupID]['Phase'] == 'DEL-Membership':
                                        self.logging( 'Log', 'Dev: %s is a possible candidate to be removed from %s' %(iterDev, MsgGroupID))
                                        unique += 1
                                        delDev = iterDev
                if unique == 1:
                    del self.ListOfDevices[delDev]['GroupMgt'][MsgEP][MsgGroupID]
        else:
            Domoticz.Error("removeGroupResponse - GroupID: %s unexpected Status: %s" %(MsgGroupID, MsgStatus))

        return

    def _removeAllGroups(self, device_addr, device_ep ):

        self.logging( 'Debug', "_removeAllGroups - %s/%s " %(device_addr, device_ep))
        datas = "02" + device_addr + "01" + device_ep
        self.ZigateComm.sendData( "0064", datas)
        return

    def _addGroupifIdentify(self, device_addr, device_ep, goup_addr = "0000"):
        datas = "02" + device_addr + "01" + device_ep + goup_addr
        self.ZigateComm.sendData( "0065", datas)
        return


    def deviceChangeNetworkID( self, old_nwkid, new_nwkid):
        """
        this method is call whenever a device get a new NetworkId.
        We then if this device is own by a group to update the networkid.
        """

        _update = False
        for iterGrp in self.ListOfGroups:
            self.logging( 'Debug', "deviceChangeNetworkID - ListOfGroups[%s]['Devices']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Devices']))
            old_listDev = list(self.ListOfGroups[iterGrp]['Devices'])
            new_listDev = []
            for iterList in old_listDev:
                if iterList[0] == old_nwkid:
                    _update = True
                    new_listDev.append( (new_nwkid, iterList[1] ) )
                else:
                    new_listDev.append( iterList )

        if _update:
            self.logging( 'Debug', "deviceChangeNetworkID - Change from %s to %s" %( self.ListOfGroups[iterGrp]['Devices'], new_listDev))
            del self.ListOfGroups[iterGrp]['Devices']
            self.ListOfGroups[iterGrp]['Devices'] = new_listDev

            # Store Group in report under json format
            self._write_GroupList()

            json_filename = self.groupListReport
            with open( json_filename, 'wt') as json_file:
                json_file.write('\n')
                json.dump( self.ListOfGroups, json_file, indent=4, sort_keys=True)


    def FreeUnit(self, Devices):
        '''
        FreeUnit
        Look for a Free Unit number.
        '''
        FreeUnit = ""
        for x in range(1, 255):
            if x not in Devices:
                self.logging( 'Debug', "FreeUnit - device " + str(x) + " available")
                return x
        else:
            self.logging( 'Debug', "FreeUnit - device " + str(len(Devices) + 1))
            return len(Devices) + 1


    # Domoticz relaed
    def _createDomoGroupDevice(self, groupname, group_nwkid):
        ' Create Device for just created group in Domoticz. '

        if groupname == '' or group_nwkid == '':
            Domoticz.Error("createDomoGroupDevice - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

        for x in self.Devices:
            if self.Devices[x].DeviceID == group_nwkid:
                Domoticz.Error("_createDomoGroupDevice - existing group %s" %(self.Devices[x].Name))
                return

        Type_, Subtype_, SwitchType_ = self._bestGroupWidget( group_nwkid)

        unit = self.FreeUnit( self.Devices )
        self.logging( 'Debug', "_createDomoGroupDevice - Unit: %s" %unit)
        myDev = Domoticz.Device(DeviceID=str(group_nwkid), Name=str(groupname), Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=SwitchType_)
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1 :
            Domoticz.Error("CreateDomoGroupDevice - failed to create Group device.")
        else:
            self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups %s created' %groupname)

    def _updateDomoGroupDeviceWidgetName( self, groupname, group_nwkid ):

        if groupname == '' or group_nwkid == '':
            Domoticz.Error("_updateDomoGroupDeviceWidget - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

        unit = 0
        for x in self.Devices:
            if self.Devices[x].DeviceID == group_nwkid:
                unit = x
                break
        else:
            Domoticz.Error("_updateDomoGroupDeviceWidget - Group doesn't exist %s / %s" %(groupname, group_nwkid))

        nValue = self.Devices[unit].nValue
        sValue = self.Devices[unit].sValue
        self.Devices[unit].Update( nValue, sValue, Name=groupname)

        # Update Group Structure
        self.ListOfGroups[group_nwkid]['Name'] = groupname

        # Write it in the Pickle file
        self._write_GroupList()

    def _updateDomoGroupDeviceWidget( self, groupname, group_nwkid ):

        if groupname == '' or group_nwkid == '':
            Domoticz.Error("_updateDomoGroupDeviceWidget - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

        unit = 0
        for x in self.Devices:
            if self.Devices[x].DeviceID == group_nwkid:
                unit = x
                break
        else:
            Domoticz.Error("_updateDomoGroupDeviceWidget - Group doesn't exist %s / %s" %(groupname, group_nwkid))

        Type_, Subtype_, SwitchType_ = self._bestGroupWidget( group_nwkid)

        if Type_ != self.Devices[unit].Type or Subtype_ != self.Devices[unit].SubType or SwitchType_ != self.Devices[unit].SwitchType :
            self.logging( 'Debug', "_updateDomoGroupDeviceWidget - Update Type:%s, Subtype:%s, Switchtype:%s" %(Type_, Subtype_, SwitchType_))
            self.Devices[unit].Update( 0, 'Off', Type=Type_, Subtype=Subtype_, Switchtype=SwitchType_)

    def _bestGroupWidget( self, group_nwkid):

        WIDGETS = {
                'Plug':1,                 # ( 244, 73, 0)
                'Switch':1,               # ( 244, 73, 0)
                'LvlControl':2,           # ( 244, 73, 7)
                'ColorControlWW':3,       # ( 241, 8, 7) - Cold white + warm white
                'ColorControlRGB':3,      # ( 241, 2, 7) - RGB
                'ColorControlRGBWW':4,    # ( 241, 4, 7) - RGB + cold white + warm white, either RGB or white can be lit
                'ColorControl':5,         # ( 241, 7, 7) - Like RGBWW, but allows combining RGB and white
                'ColorControlFull':5 }    # ( 241, 7, 7) - Like RGBWW, but allows combining RGB and white

        code = 0
        _ikea_colormode = None
        color_widget = None
        widget = ( 241, 7,7 )
        for devNwkid, devEp in self.ListOfGroups[group_nwkid]['Devices']:
            self.logging( 'Debug', "bestGroupWidget - processing %s" %devNwkid)
            if devNwkid not in self.ListOfDevices:
                continue
            if 'ClusterType' not in self.ListOfDevices[devNwkid]['Ep'][devEp]:
                continue
            for iterClusterType in self.ListOfDevices[devNwkid]['Ep'][devEp]['ClusterType']:
                if self.ListOfDevices[devNwkid]['Ep'][devEp]['ClusterType'][iterClusterType] in WIDGETS:
                    devwidget = self.ListOfDevices[devNwkid]['Ep'][devEp]['ClusterType'][iterClusterType]
                    if code <= WIDGETS[devwidget]:
                        code = WIDGETS[devwidget]
                        if code == 1: 
                            widget = ( 244, 73, 0 )
                        elif code == 2: 
                            widget = ( 244, 73, 7 )
                        elif code == 3 :
                            if color_widget is None:
                                if devwidget == 'ColorControlWW': 
                                    widget = ( 241, 8, 7 )
                                    _ikea_colormode = devwidget
                                elif devwidget == 'ColorControlRGB': 
                                    widget = ( 241, 2, 7 )
                                    _ikea_colormode = devwidget
                            elif color_widget == devwidget:
                                continue
                            elif (devwidget == 'ColorControlWW' and color_widget == 'ColorControlRGB') or \
                                    ( color_widget == 'ColorControlWW' and devwidget == 'ColorControlRGB' ) :
                                code = 4
                                color_widget = 'ColorControlRGBWW'
                                widget = ( 241, 4, 7)
                                _ikea_colormode = color_widget
                            elif devwidget == 'ColorControl':
                                code = 5
                                color_widget = 'ColorControlFull'
                                widget = ( 241, 7, 7)
                                _ikea_colormode = color_widget
                        elif code == 4: 
                            color_widget = 'ColorControlRGBWW'
                            widget = ( 241, 4, 7)
                            _ikea_colormode = color_widget
                        elif code == 5:
                            color_widget = 'ColorControlFull'
                            widget = ( 241, 7, 7)
                            _ikea_colormode = color_widget
                    pre_code = code


        # This will be used when receiving left/right click , to know if it is RGB or WW
        if 'Tradfri Remote' in self.ListOfGroups[group_nwkid]:
            self.ListOfGroups[group_nwkid]['Tradfri Remote']['Color Mode'] = _ikea_colormode

        self.logging( 'Debug', "_bestGroupWidget - Code: %s, Color_Widget: %s, widget: %s" %( code, color_widget, widget))
        return widget

    def updateDomoGroupDevice( self, group_nwkid):
        """ 
        Update the Group status On/Off and Level , based on the attached devices
        """

        if group_nwkid not in self.ListOfGroups:
            Domoticz.Error("updateDomoGroupDevice - unknown group: %s" %group_nwkid)
            return
        if 'Devices' not in self.ListOfGroups[group_nwkid]:
            self.logging( 'Debug', "updateDomoGroupDevice - no Devices for that group: %s" %self.ListOfGroups[group_nwkid])
            return

        unit = 0
        for unit in self.Devices:
            if self.Devices[unit].DeviceID == group_nwkid:
                break
        else:
            return

        # If one device is on, then the group is on. If all devices are off, then the group is off
        nValue = 0
        level = None
        for dev_nwkid, dev_ep in self.ListOfGroups[group_nwkid]['Devices']:
            if dev_nwkid in self.ListOfDevices:
                if 'Ep' in  self.ListOfDevices[dev_nwkid]:
                    if dev_ep in self.ListOfDevices[dev_nwkid]['Ep']:
                        if '0006' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                            if str(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']).isdigit():
                                if int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']) != 0:
                                    nValue = 1
                        if '0008' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                            if self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'] != '' and self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'] != {}:
                                if level is None:
                                    level = int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'],16)
                                else:
                                    level = round(( level +  int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'],16)) / 2)
        # At that stage
        # nValue == 0 if Off
        # nValue == 1 if Open/On
        # level is None, so we use nValue/sValue
        # level is not None; so we have a LvlControl
        if level:
            if self.Devices[unit].SwitchType != 16:
                # Not a Shutter/Blind
                analogValue = level
                if analogValue >= 255:
                    sValue = 100
                else:
                    sValue = round((level * 100) / 255)
                    if sValue > 100: sValue = 100
                    if sValue == 0 and analogValue > 0:
                        sValue = 1
            else:
                # Shutter/blind
                if nValue == 0: # we are in an Off mode
                    sValue = 0
                else:
                    # We are on either full or not
                    sValue = round((level * 100) / 255)
                    if sValue >= 100: 
                        sValue = 100
                        nValue = 1
                    elif sValue > 0 and sValue < 100:
                        nValue = 2
                    else:
                        nValue = 0
            sValue = str(sValue)
        else:
            if nValue == 0:
                sValue = 'Off'
            else:
                sValue = 'On'

        if nValue != self.Devices[unit].nValue or sValue != self.Devices[unit].sValue:
            self.logging( 'Log', "UpdateGroup  - (%15s) %s:%s" %( self.Devices[unit].Name, nValue, sValue ))
            self.Devices[unit].Update( nValue, sValue)


    def _removeDomoGroupDevice(self, group_nwkid):
        ' User has removed the Domoticz Device corresponding to this group'

        if group_nwkid not in self.ListOfGroups:
            Domoticz.Error("_removeDomoGroupDevice - unknown group: %s" %group_nwkid)
            return

        unit = 0
        for unit in self.Devices:
            if self.Devices[unit].DeviceID == group_nwkid:
                break
        else:
            Domoticz.Error("_removeDomoGroupDevice - no Devices found in Domoticz: %s" %group_nwkid)
            return
        self.logging( 'Debug', "_removeDomoGroupDevice - removing Domoticz Widget %s" %self.Devices[unit].Name)
        self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups %s deleted' %self.Devices[unit].Name)
        self.Devices[unit].Delete()
        

    # Group Management methods
    def processRemoveGroup( self, unit, grpid):

        # Remove all devices from the corresponding group
        if grpid not in self.ListOfGroups:
            return

        _toremove = []
        for iterDev in list(self.ListOfDevices):
            if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                continue
            for iterEP in self.ListOfDevices[iterDev]['Ep']:
                if iterEP not in self.ListOfDevices[iterDev]['GroupMgt']:
                    continue
                if grpid in self.ListOfDevices[iterDev]['GroupMgt'][iterEP]:
                    self.logging( 'Debug', "processRemoveGroup - remove %s %s %s" 
                            %(iterDev, iterEP, grpid))
                    self._removeGroup(iterDev, iterEP, grpid )
                    _toremove.append( (iterDev,iterEP) )
        for removeDev, removeEp in _toremove:
            del self.ListOfDevices[removeDev]['GroupMgt'][removeEp][grpid]

        del self.ListOfGroups[grpid]

        return

    def set_Kelvin_Color( self, mode, addr, EPin, EPout, t, transit=None):
        #Value is in mireds (not kelvin)
        #Correct values are from 153 (6500K) up to 588 (1700K)
        # t is 0 > 255
    
        if transit is None:
            transit = '0001'
        else:
            transit = '%04x' %transit

        TempKelvin = int(((255 - int(t))*(6500-1700)/255)+1700)
        TempMired = 1000000 // TempKelvin
        zigate_cmd = "00C0"
        zigate_param = Hex_Format(4,TempMired) + transit
        datas = "%02d" %mode + addr + EPin + EPout + zigate_param
        self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
        self.ZigateComm.sendData( zigate_cmd, datas)

    def set_RGB_color( self, mode, addr, EPin, EPout, r, g, b, transit=None):

        if transit is None:
            transit = '0001'
        else:
            transit = '%04x' %transit
        x, y = rgb_to_xy((int(r),int(g),int(b)))
        #Convert 0>1 to 0>FFFF
        x = int(x*65536)
        y = int(y*65536)
        strxy = Hex_Format(4,x) + Hex_Format(4,y)
        zigate_cmd = "00B7"
        zigate_param = strxy + transit
        datas = "%02d" %mode + addr + EPin + EPout + zigate_param
        self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
        self.ZigateComm.sendData( zigate_cmd, datas)

    def _updateDeviceListAttribute( self, grpid, cluster, value):

        if grpid not in self.ListOfGroups:
            return

        # search for all Devices in the group
        for iterDev, iterEp in self.ListOfGroups[grpid]['Devices']:
            if iterDev == '0000': continue
            if iterDev not in self.ListOfDevices:
                Domoticz.Error("_updateDeviceListAttribute - Device: %s of Group: %s not in the list anymore" %(iterDev,grpid))
                continue
            if iterEp not in self.ListOfDevices[iterDev]['Ep']:
                Domoticz.Error("_updateDeviceListAttribute - Not existing Ep: %s for Device: %s in Group: %s" %(iterEp, iterDev, grpid))
                continue
            if 'ClusterType' not in self.ListOfDevices[iterDev]['Ep'][iterEp] and 'ClusterType' not in self.ListOfDevices[iterDev]:
                Domoticz.Error("_updateDeviceListAttribute - No Widget attached to Device: %s/%s in Group: %s" %(iterDev,iterEp,grpid))
                continue
            if cluster not in self.ListOfDevices[iterDev]['Ep'][iterEp]:
                Domoticz.Error("_updateDeviceListAttribute - Cluster: %s doesn't exist for Device: %s/%s in Group: %s" %(cluster,iterDev,iterEp,grpid))
                continue

            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] = value
            self.logging( 'Debug', "_updateDeviceListAttribute - Updating Device: %s/%s of Group: %s Cluster: %s to value: %s" %(iterDev, iterEp, grpid, cluster, value))

        return


    def processCommand( self, unit, nwkid, Command, Level, Color_ ) : 

        self.logging( 'Debug', "processCommand - unit: %s, nwkid: %s, cmd: %s, level: %s, color: %s" %(unit, nwkid, Command, Level, Color_))

        if nwkid not in self.ListOfGroups:
            return
        for iterDev, iterEp in self.ListOfGroups[nwkid]['Devices']:
            self.logging( 'Debug', 'processCommand - reset heartbeat for device : %s' %iterDev)
            if iterDev in self.ListOfDevices:
                if 'Heartbeat' in self.ListOfDevices[iterDev]:
                    self.ListOfDevices[iterDev]['Heartbeat'] = '0'
            else:
                Domoticz.Error("processCommand - Looks like device %s does not exist anymore and you expect to be part of group %s" %(iterDev, nwkid))

        EPin = EPout = '01'

        if Command == 'Off' :
            zigate_cmd = "0092"
            zigate_param = '00'
            nValue = 0
            sValue = 'Off'
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            self._updateDeviceListAttribute( nwkid, '0006', '00')
            self.updateDomoGroupDevice( nwkid)
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            self.logging( 'Debug', "Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

        elif Command == 'On' :
            zigate_cmd = "0092"
            zigate_param = '01'
            nValue = '1'
            sValue = 'On'
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            self._updateDeviceListAttribute( nwkid, '0006', '01')
            self.updateDomoGroupDevice( nwkid)
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            self.logging( 'Debug', "Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

        elif Command == 'Set Level':
            zigate_cmd = "0081"
            OnOff = "01"
            value=int(Level*255//100)
            zigate_param = OnOff + "%02x" %value + "0010"
            nValue = '1'
            sValue = str(Level)
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            self._updateDeviceListAttribute( nwkid, '0008', sValue)
            self.updateDomoGroupDevice( nwkid)
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            self.logging( 'Debug', "Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

        elif Command == "Set Color" :
            Hue_List = json.loads(Color_)
            #First manage level
            OnOff = '01' # 00 = off, 01 = on
            value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state
            zigate_cmd = "0081"
            zigate_param = OnOff + value + "0000"
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
            self.ZigateComm.sendData( zigate_cmd, datas)

            if Hue_List['m'] == 1:
                ww = int(Hue_List['ww']) # Can be used as level for monochrome white
                #TODO : Jamais vu un device avec ca encore
                self.logging( 'Debug', "Not implemented device color 1")
            #ColorModeTemp = 2   // White with color temperature. Valid fields: t
            if Hue_List['m'] == 2:
                self.set_Kelvin_Color( ADDRESS_MODE['group'], nwkid, EPin, EPout, int(Hue_List['t']))

            #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
            elif Hue_List['m'] == 3:

                self.set_RGB_color( ADDRESS_MODE['group'], nwkid, EPin, EPout, \
                        int(Hue_List['r']), int(Hue_List['g']), int(Hue_List['b']))

            #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
            elif Hue_List['m'] == 4:
                ww = int(Hue_List['ww'])
                cw = int(Hue_List['cw'])
                x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                #TODO, Pas trouve de device avec ca encore ...
                self.logging( 'Debug', "Not implemented device color 2")

            #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
            elif Hue_List['m'] == 9998:
                h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                saturation = s * 100   #0 > 100
                hue = h *360           #0 > 360
                hue = int(hue*254//360)
                saturation = int(saturation*254//100)
                value = int(l * 254//100)
                OnOff = '01'
                zigate_cmd = "00B6"
                zigate_param = Hex_Format(2,hue) + Hex_Format(2,saturation) + "0000"
                datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                zigate_cmd = "0081"
                zigate_param = OnOff + Hex_Format(2,value) + "0010"
                datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                #Update Device
                nValue = 1
                sValue = str(value)
                self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_) 
                return

    def manageIkeaTradfriRemoteLeftRight( self, addr, type_dir):

        for iterGrp in self.ListOfGroups:
            if 'Tradfri Remote' not in self.ListOfGroups[iterGrp]:
                continue
            if addr != self.ListOfGroups[iterGrp]['Tradfri Remote']['Device Addr']:
                continue
            _grpid = iterGrp
            break
        else:
            _ieee = self.ListOfDevices[addr]['IEEE']
            Domoticz.Error("manageIkeaTradfriRemoteLeftRight - Remote %s not associated to any group" %_ieee)
            return
            
        _widgetColor = self.ListOfGroups[_grpid]['Tradfri Remote']['Color Mode'] 
        if _widgetColor == None:
            Domoticz.Error("manageIkeaTradfriRemoteLeftRight - undefined Color Mode for %s" %_widgetColor)
            return

        self.logging( 'Debug', "manageIkeaTradfriRemoteLeftRight - Color model : %s" %_widgetColor)

        if _widgetColor in ('ColorControlWW'): # Will work in Kelvin
            if 'Actual T' not in self.ListOfGroups[_grpid]['Tradfri Remote']:
                t = 128
            else:
                t = self.ListOfGroups[_grpid]['Tradfri Remote']['Actual T']

            if type_dir == 'left':
                t -= self.pluginconf.pluginConf['TradfriKelvinStep']
                if t < 0: t = 255
            elif type_dir == 'right':
                t += self.pluginconf.pluginConf['TradfriKelvinStep']
                if t > 255: t = 0
                
            self.logging( 'Debug', "manageIkeaTradfriRemoteLeftRight - Kelvin T %s" %t)
            self.set_Kelvin_Color( ADDRESS_MODE['group'], _grpid, '01', '01', t)
            self.ListOfGroups[_grpid]['Tradfri Remote']['Actual T'] = t

        elif _widgetColor in ('ColorControlRGB','ColorControlRGBWW', 'ColorControl', 'ColorControlFull'): # Work in RGB
            # Here we will scroll R, G and B 

            PRESET_COLOR = (  
                              (  10,  10,  10), # 
                              ( 255,   0,   0), # Red
                              (   0, 255,   0), # Green
                              (   0,   0, 255), # Blue
                              ( 255, 255,   0), # Yello
                              (   0, 255, 255), # Aqua
                              ( 255,   0, 255), # 
                              ( 255, 255, 255)  # Whhite
                           )

            if 'RGB' not in self.ListOfGroups[_grpid]['Tradfri Remote']:
                seq_idx = 0
            else:
                seq_idx = self.ListOfGroups[_grpid]['Tradfri Remote']['RGB']

            r, g, b = PRESET_COLOR[seq_idx]

            if type_dir == 'left': seq_idx -= 1
            elif type_dir == 'right': seq_idx += 1

            if seq_idx >= len(PRESET_COLOR): seq_idx = 0
            if seq_idx < 0: seq_idx = len(PRESET_COLOR) - 1

            self.logging( 'Debug', "manageIkeaTradfriRemoteLeftRight - R %s G %s B %s" %(r,g,b))
            self.set_RGB_color( ADDRESS_MODE['group'], _grpid, '01', '01', r, g, b)
            self.ListOfGroups[_grpid]['Tradfri Remote']['RGB'] = seq_idx

    def hearbeatGroupMgt( self ):
        ' hearbeat to process Group Management actions '
        # Groups Management

        def modification_date( filename ):
            """
            Try to get the date that a file was created, falling back to when it was
            last modified if that isn't possible.
            See http://stackoverflow.com/a/39501288/1709587 for explanation.
            """
            return os.path.getmtime( filename )

        if self.StartupPhase == 'ready':
            for group_nwkid in self.ListOfGroups:
                self.updateDomoGroupDevice( group_nwkid)

        elif self.StartupPhase == 'init':
            # Check if there is an existing Pickle file. If this file is newer than ZigateConf, we can simply load it and finish the Group startup.
            # In case the file is older, this means that ZigateGroupConf is newer and has some changes, do the full process.

            # Check if the DeviceList file exist.
            self.logging( 'Log', "Group Management - Init phase")
            self.StartupPhase = 'discovery'
            last_update_GroupList = 0
            if os.path.isfile( self.groupListFileName ) :
                self.logging( 'Log', "--->GroupList.pck exists")
                last_update_GroupList = modification_date( self.groupListFileName )
                self.logging( 'Log', "--->Last Update of GroupList: %s" %last_update_GroupList)
            else:
                self.logging( 'Log', "--->GroupList.pck doesn't exist")

            if self.groupsConfigFilename or self.json_groupsConfigFilename :
                if self.groupsConfigFilename:
                    if os.path.isfile( self.groupsConfigFilename ):
                        self.logging( 'Log', "------------>Config file exists %s" %self.groupsConfigFilename)
                        self.txt_last_update_ConfigFile = modification_date( self.groupsConfigFilename )
                        self.logging( 'Log', "------------>Last Update of TXT Config File: %s" %self.txt_last_update_ConfigFile)
 
                if self.json_groupsConfigFilename:
                    if os.path.isfile( self.json_groupsConfigFilename):
                        self.logging( 'Log', "------------>Json Config file exists")
                        self.json_last_update_ConfigFile = modification_date( self.json_groupsConfigFilename )
                        self.logging( 'Log', "------------>Last Update of JSON Config File: %s" %self.json_last_update_ConfigFile)
                
                if last_update_GroupList > self.txt_last_update_ConfigFile and last_update_GroupList > self.json_last_update_ConfigFile:
                    # GroupList is newer , just reload the file and exit
                    self.logging( 'Status', "--------->No update of Groups needed")
                    self.StartupPhase = 'end of group startup'
                    self._load_GroupList()
            else:   # No config file, so let's move on
                self.logging( 'Log', "------>No Config file, let's use the GroupList")
                self.logging( 'Log', "------>switch to end of Group Startup")
                self._load_GroupList()
                self.StartupPhase = 'end of group startup'
            
            if self.ScanGroupMembership == 'True' and self.StartupPhase != 'discovery':
                self.StartupPhase = 'discovery'
                self.logging( 'Status', "Going for a full group membership discovery. (User Request)")

        elif self.StartupPhase == 'discovery':
            # We will send a Request for Group memebership to each active device
            # In case a device doesn't belo,ng to any group, no response is provided.
            self.logging( 'Log', "Group Management - Discovery mode - Searching for Group Membership (or continue)")
            self.stillWIP = True
            _workcompleted = True
            listofdevices = list(self.ListOfDevices)
            for iterDev in listofdevices:
                _mainPowered = False
                if 'MacCapa' in self.ListOfDevices[iterDev]:
                    if self.ListOfDevices[iterDev]['MacCapa'] == '8e':
                        _mainPowered = True
                if 'PowerSource' in self.ListOfDevices[iterDev]:
                    if self.ListOfDevices[iterDev]['PowerSource'] == 'Main':
                        _mainPowered = True
                if not _mainPowered:
                    self.logging( 'Debug', " - %s not main Powered" %(iterDev))
                    continue

                if 'Health' in self.ListOfDevices[iterDev]:
                    Domoticz.Log("Group Management - Discovery mode %s - >%s<" %(iterDev, self.ListOfDevices[iterDev]['Health']))
                    if self.ListOfDevices[iterDev]['Health'] == 'Not Reachable':
                        self.logging( 'Log', "Group Management - Discovery mode - skiping device %s which is Not Reachable" %iterDev)
                        continue

                if 'Ep' in self.ListOfDevices[iterDev]:
                    for iterEp in self.ListOfDevices[iterDev]['Ep']:
                        if iterEp == 'ClusterType': continue
                        if  ( iterDev == '0000' or \
                                ( 'ClusterType' in self.ListOfDevices[iterDev] or 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] )) and \
                              '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                             ( '0006' in self.ListOfDevices[iterDev]['Ep'][iterEp] or '0008' in self.ListOfDevices[iterDev]['Ep'][iterEp] ):
                            # As we are looking for Group Membership, we don't know to which Group it could belongs.
                            # XXXX is a special group in the code to be used in that case.
                            if 'GroupMgt' not in  self.ListOfDevices[iterDev]:
                                self.ListOfDevices[iterDev]['GroupMgt'] = {}
                            if iterEp not in  self.ListOfDevices[iterDev]['GroupMgt']:
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp] = {}

                            if 'XXXX' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX'] = {}
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase'] = {}
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] = {}

                            if 'Phase' in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']:
                                if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase'] == 'REQ-Membership':
                                    continue

                            if  len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
                                self.logging( 'Debug', "normalQueue: %s" %len(self.ZigateComm._normalQueue))
                                self.logging( 'Debug', "normalQueue: %s" %(str(self.ZigateComm._normalQueue)))
                                self.logging( 'Debug', "too busy, will try again ...%s" %len(self.ZigateComm._normalQueue))
                                _workcompleted = False
                                break # will continue in the next cycle

                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase'] = 'REQ-Membership'
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] = int(time())
                            self._getGroupMembership(iterDev, iterEp)   # We request MemberShip List
                            self.logging( 'Debug', " - request group membership for %s/%s" %(iterDev, iterEp))
            else:
                if _workcompleted:
                    self.logging( 'Log', "hearbeatGroupMgt - Finish Discovery Phase" )
                    self.StartupPhase = 'finish discovery'

        elif self.StartupPhase in ( 'finish discovery', 'finish discovery continue') :
            # Check for completness or Timeout
            if self.StartupPhase ==  'finish discovery':
                self.logging( 'Log', "Group Management - Membership gathering")
            self.StartupPhase = 'finish discovery continue'
            now = time()
            self.stillWIP = True
            _completed = True
            for iterDev in self.ListOfDevices:
                if 'GroupMgt' in self.ListOfDevices[iterDev]:       # We select only the Device for which we have requested Group membership
                    for iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                        for iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                            if iterGrp == 'XXXX': continue
                            if 'Phase' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]:
                                continue

                            self.logging( 'Debug', 'Checking if process is done for %s/%s - %s -> %s' 
                                    %(iterDev,iterEp,iterGrp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))

                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] == 'OK-Membership':
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] + TIMEOUT > now:
                                _completed = False
                                break # Need to wait a couple of sec.

                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'TimeOut'
                            self.logging( 'Debug', " - No response receive for %s/%s - assuming no group membership for %s " %(iterDev,iterEp, iterGrp))
                        else:
                            if 'XXXX' in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                                self.logging( 'Debug', 'Checking if process is done for %s/%s - XXXX -> %s' 
                                    %(iterDev,iterEp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX'])))
                                if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] + TIMEOUT > now:
                                    _completed = False
                                    break
                                del  self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']
            else:
                if _completed:
                    for iterGrp in self.ListOfGroups:
                        self.logging( 'Log', "Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
                        self.logging( 'Debug', "Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
                        for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                            if iterDev not in self.ListOfDevices:
                                Domoticz.Error("Group Management - seems that Group %s is refering to a non-existing device %s/%s" \
                                        %(self.ListOfGroups[iterGrp]['Name'], iterDev, iterEp))
                                continue
                            if 'IEEE' not in self.ListOfDevices[iterDev]:
                                Domoticz.Error("Group Management - seems that Group %s is refering to a device %s/%s with an unknown IEEE" \
                                        %(self.ListOfGroups[iterGrp]['Name'], iterDev, iterEp))
                                continue

                            self.logging( 'Log', "  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))
                    self.logging( 'Log', "Group Management - Discovery Completed" )
                    self.StartupPhase = 'load config'

        elif  self.StartupPhase == 'load config':



            # Which config file is the newest
            self.logging( 'Debug', "Group Management - Loading Zigate Group Configuration file")
            if self.json_last_update_ConfigFile >= self.txt_last_update_ConfigFile:
                # Take JSON
                self.logging( 'Debug', "Group Management - Loading Zigate Group Configuration file JSON")
                self.load_jsonZigateGroupConfig()
            else:
                #Take TXT
                self.logging( 'Debug', "Group Management - Loading Zigate Group Configuration file TXT")
                self.load_ZigateGroupConfiguration()
            self.TobeAdded = []
            self.TobeRemoved = []
            self.StartupPhase = 'process config'

        elif self.StartupPhase == 'process config':
            self.stillWIP = True
            for iterGrp in self.ListOfGroups:
                if 'Imported' not in self.ListOfGroups[iterGrp]:
                    self.logging( 'Debug', "Nothing to import ...")
                    continue
                if len(self.ListOfGroups[iterGrp]['Imported']) == 0 and len(self.ListOfGroups[iterGrp]['Devices']) == 0 :
                    self.logging( 'Debug', "Nothing to import and no Devices ...")
                    continue

                self.logging( 'Debug', "Processing Group: %s - Checking Removal" %iterGrp)
                # Remove group membership
                self.logging( 'Debug', " - %s" %self.ListOfGroups[iterGrp]['Devices'])
                self.logging( 'Debug', " - %s" %self.ListOfGroups[iterGrp]['Imported'])

                for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                    if iterDev not in self.ListOfDevices:
                        Domoticz.Error("hearbeat Group - Most likely, device %s is not paired anymore ..." %iterDev)
                        continue
                    if 'IEEE' not in self.ListOfDevices[iterDev]:
                        break
                    iterIEEE = self.ListOfDevices[iterDev]['IEEE']

                    self.logging( 'Debug', "    - checking device: %s / %s to be removed " %(iterDev, iterEp))
                    self.logging( 'Debug', "    - checking device: %s " %self.ListOfGroups[iterGrp]['Imported'])
                    self.logging( 'Debug', "    - checking device: IEEE: %s " %iterIEEE)

                    _found = False
                    for iterTuple in self.ListOfGroups[iterGrp]['Imported']:
                        if iterIEEE == iterTuple[0]:
                            if iterTuple[1]: 
                                if iterEp == iterTuple[1]:
                                    _found = True
                                    break
                            else:
                                _found = True
                                break

                    if _found:
                        continue

                    removeIEEE = iterIEEE
                    if iterIEEE not in self.IEEE2NWK:
                        Domoticz.Error("Unknown IEEE to be removed %s" %iterIEEE)
                        continue
                    removeNKWID = self.IEEE2NWK[iterIEEE]
                    if removeNKWID not in self.ListOfDevices:
                        Domoticz.Error("Unknown IEEE to be removed %s" %removeNKWID)
                        continue
                    self.logging( 'Debug', " %s/%s to be removed from %s" 
                            %(removeNKWID, iterEp, iterGrp))
                    self.TobeRemoved.append( ( removeNKWID, iterEp, iterGrp ) )

                self.logging( 'Debug', "Processing Group: %s - Checking Adding" %iterGrp)
                # Add group membership
                for iterIEEE, import_iterEp in self.ListOfGroups[iterGrp]['Imported']:
                    if iterIEEE not in self.IEEE2NWK:
                        Domoticz.Error("heartbeat Group - Unknown IEEE %s" %iterIEEE)
                        continue

                    iterDev = self.IEEE2NWK[iterIEEE]
                    self.logging( 'Debug', "    - checking device: %s to be added " %iterDev)
                    if iterDev in self.ListOfGroups[iterGrp]['Devices']:
                        self.logging( 'Debug', "%s already in group %s" %(iterDev, iterGrp))
                        continue

                    self.logging( 'Debug', "       - checking device: %s " %iterDev)
                    if 'Ep' in self.ListOfDevices[iterDev]:
                        _listDevEp = []
                        if import_iterEp:
                            _listDevEp.append(import_iterEp)
                        else:
                            _listDevEp = list(self.ListOfDevices[iterDev]['Ep'])
                        self.logging( 'Debug', 'List of Ep: %s' %_listDevEp)

                        for iterEp in _listDevEp:
                            self.logging( 'Debug', "       - Check existing Membership %s/%s" %(iterDev,iterEp))

                            if 'GroupMgt' in self.ListOfDevices[iterDev]:
                                if iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                                    if iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                                        if  self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] == 'OK-Membership':
                                            self.logging( 'Debug', "       - %s/%s already in group %s" %(iterDev, iterEp, iterGrp))
                                            continue
                            if iterEp not in self.ListOfDevices[iterDev]['Ep']:
                                Domoticz.Error("whearbeatGroupMgt - unknown EP %s for %s against (%s)" %(iterEp, iterDev, self.ListOfDevices[iterDev]['Ep']))
                                continue

                            if  ( iterDev == '0000' or \
                                    ( 'ClusterType' in self.ListOfDevices[iterDev] or 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] )) and \
                                    '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                                    ( '0006' in self.ListOfDevices[iterDev]['Ep'][iterEp] or '0008' in self.ListOfDevices[iterDev]['Ep'][iterEp] ):
                                self.logging( 'Debug', " %s/%s to be added to %s"
                                        %( iterDev, iterEp, iterGrp))
                                self.TobeAdded.append( ( iterIEEE, iterDev, iterEp, iterGrp ) )

            self.logging( 'Log', "Group Management - End of Configuration processing" )
            self.logging( 'Log', "  - To be removed : %s" %self.TobeRemoved)
            self.logging( 'Log', "  - To be added : %s" %self.TobeAdded)
            if len(self.TobeAdded) == 0 and len(self.TobeRemoved) == 0:
                self.StartupPhase = 'check group list'
                self._SaveGroupFile = True
                self.logging( 'Debug', "Updated Groups are : %s" %self.UpdatedGroups)
                self._write_GroupList()
                for iterGroup in self.UpdatedGroups:
                    self._identifyEffect( iterGroup, '01', effect='Okay' )
                    self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups %s operational' %iterGroup)
            else:
                self.StartupPhase = 'perform command'

        elif self.StartupPhase == 'perform command':
            self.stillWIP = True
            _completed = True
            self.logging( 'Debug', "hearbeatGroupMgt - Perform Zigate commands")
            self.logging( 'Debug', " - Removal to be performed: %s" %str(self.TobeRemoved))
            for iterDev, iterEp, iterGrp in list(self.TobeRemoved):
                if iterDev not in self.ListOfDevices and iterDev != '0000':
                    Domoticz.Error("hearbeatGroupMgt - unconsistency found. %s not found in ListOfDevices." %iterDev)
                    continue
                if iterEp not in self.ListOfDevices[iterDev]['GroupMgt']:
                    Domoticz.Error("hearbeatGroupMgt - unconsistency found. %s/%s not found in ListOfDevices." %(iterDev,iterEp))
                    continue
                if iterGrp not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                    Domoticz.Error("hearbeatGroupMgt - unconsistency found. Group: %s for %s/%s not found in ListOfDevices." \
                            %(iterGrp, iterDev,iterEp))
                    continue

                if  len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
                    self.logging( 'Debug', "normalQueue: %s" %len(self.ZigateComm._normalQueue))
                    self.logging( 'Debug', "normalQueue: %s" %(str(self.ZigateComm._normalQueue)))
                    _completed = False
                    self.logging( 'Debug', "Too busy, will come back later")
                    break # will continue in the next cycle
                self._removeGroup( iterDev, iterEp, iterGrp )
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'DEL-Membership'
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = int(time())
                self.TobeRemoved.remove( (iterDev, iterEp, iterGrp) )

            self.logging( 'Debug', " - Add to be performed: %s" %str(self.TobeAdded))
            for iterIEEE, iterDev, iterEp, iterGrp in list(self.TobeAdded):
                if  len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
                    self.logging( 'Debug', "normalQueue: %s" %len(self.ZigateComm._normalQueue))
                    self.logging( 'Debug', "normalQueue: %s" %(str(self.ZigateComm._normalQueue)))
                    _completed = False
                    self.logging( 'Debug', "Too busy, will come back later")
                    break # will continue in the next cycle
                if iterDev not in self.ListOfDevices and iterDev != '0000':
                    Domoticz.Error("hearbeatGroupMgt - unconsitecy found. %s not for found in ListOfDevices." %iterDev)
                    continue

                if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                    self.ListOfDevices[iterDev]['GroupMgt'] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = {}

                if iterGrp not in self.ListOfDevices[iterDev]['GroupMgt']:
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = {}

                if 'Phase' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]:
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = {}
                    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = {}

                self._addGroup( iterIEEE, iterDev, iterEp, iterGrp )
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'ADD-Membership'
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = int(time())
                self.TobeAdded.remove( (iterIEEE, iterDev, iterEp, iterGrp) )

            if _completed:
                self.StartupPhase = 'finish configuration'

        elif self.StartupPhase == 'finish configuration':
            # Check for completness or Timeout
            self.logging( 'Log', "Group Management - Finishing configuration mode")
            self.stillWIP = True
            now = time()
            _completed = True
            for iterDev in self.ListOfDevices:
                if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                    continue
                if 'Ep' in self.ListOfDevices[iterDev]:
                    for iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                        for iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                            #if iterDev == '0000' and iterGrp in ( '0000' ):
                                #Adding Zigate to group 0x0000 or 0xffff
                                # We do not get any response
                            #    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'OK-Membership'

                            if iterGrp == 'XXXX': continue

                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] in ( 'OK-Membership', 'TimmeOut'):
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] not in ( 'DEL-Membership' ,'ADD-Membership' ):
                                self.logging( 'Debug', "Unexpected phase for %s/%s in group %s : phase!: %s"
                                %( iterDev, iterEp, iterGrp,  str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] + TIMEOUT > now:
                                _completed = False
                                break # Wait a couple of Sec

                            self.logging( 'Debug', 'Checking if process is done for %s/%s - %s -> %s' 
                                    %(iterDev,iterEp,iterGrp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))

                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'TimeOut'
                            self.logging( 'Debug', " - No response receive for %s/%s - assuming no group membership to %s" %(iterDev,iterEp, iterGrp))
            else:
                if _completed:
                    self.logging( 'Log', "hearbeatGroupMgt - Configuration mode completed" )
                    self.Cycle += 1
                    if self.Cycle > MAX_CYCLE:
                        Domoticz.Error("We reach the max number of Cycle and didn't succeed in the Group Creation")
                        self._SaveGroupFile = False
                        self.StartupPhase = 'check group list'
                    else:
                        self.StartupPhase = 'discovery'
                        for iterDev in self.ListOfDevices:
                            if 'GroupMgt' in self.ListOfDevices[iterDev]:
                                del self.ListOfDevices[iterDev]['GroupMgt']
                        for iterGrp in list(self.ListOfGroups):
                            del self.ListOfGroups[iterGrp]

        elif self.StartupPhase == 'check group list':
            # GroupList is build in the germembership response
            self.logging( 'Log', "Group Management - Checking Group list")
            self.stillWIP = True
            for iterGrp in list(self.ListOfGroups):
                self.logging( 'Debug', "Checking %s " %iterGrp)
                self.logging( 'Debug', "  - Devices: %s" %len(self.ListOfGroups[iterGrp]['Devices']))
                for x in self.Devices:
                    if self.Devices[x].DeviceID == iterGrp:
                        if len(self.ListOfGroups[iterGrp]['Devices']) == 0:
                            self.logging( 'Log', "hearbeatGroupMgt - Remove Domotticz Device : %s for Group: %s " %(self.Devices[x].Name, iterGrp))
                            self._removeDomoGroupDevice( iterGrp)
                            del self.ListOfGroups[iterGrp] 
                        else:
                            self.ListOfGroups[iterGrp]['Name'] = self.Devices[x].Name
                            # Check if we need to update the Widget
                            self._updateDomoGroupDeviceWidget(self.ListOfGroups[iterGrp]['Name'], iterGrp)
                            self.logging( 'Log', "hearbeatGroupMgt - _updateDomoGroup done")
                        break
                else:
                    # Unknown group in Domoticz. Create it
                    if len(self.ListOfGroups[iterGrp]['Devices']) == 0:
                        del self.ListOfGroups[iterGrp] 
                        continue
                    if self.ListOfGroups[iterGrp]['Name'] == '':
                        self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                    self.logging( 'Log', "hearbeatGroupMgt - create Domotciz Widget for %s " %self.ListOfGroups[iterGrp]['Name'])
                    self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)

            self.StartupPhase = 'end of group startup'
            # We write GroupList to cash only if in case of success.
            if self._SaveGroupFile:
                self._write_GroupList()

        elif self.StartupPhase == 'end of group startup':
            for iterGrp in self.ListOfGroups:
                self.logging( 'Log', "Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
                self.logging( 'Log', "Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
                for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                    if iterDev in self.ListOfDevices:
                        self.logging( 'Log', "  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))

            # Store Group in report under json format (Debuging purpose)
            json_filename = self.groupListReport
            with open( json_filename, 'wt') as json_file:
                json_file.write('\n')
                json.dump( self.ListOfGroups, json_file, indent=4, sort_keys=True)

            self.logging( 'Status', "Group Management - startup done")
            self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups management startup completed')
            self.StartupPhase = 'ready'
            self.stillWIP = False
        return
