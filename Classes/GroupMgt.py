#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

"""
ListOfGroups[group id]['Name']    - Group Name as it will be created in Domoticz
ListOfGroups[group id]['Devices'] - List of Devices associed to this group on Zigate
ListOfGroups[group id]['Imported']- List of Devices to be associated to the group. We might have some removal, or some addiional from previous run

self.ListOfDevices[nwkid]['GroupMgt'][Ep][GroupID]['Phase'] = 'OK-Membership' / 'REQ-Membership' / 'DEL-Membership'
self.ListOfDevices[nwkid]['GroupMgt'][Ep][GroupID]['Phase-Stamp'] = time()
"""

import Domoticz
import json
import pickle
import os.path

from time import time

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.consts import ADDRESS_MODE

GROUPS_CONFIG_FILENAME = "ZigateGroupsConfig"
MAX_LOAD = 2
TIMEOUT = 12
MAX_CYCLE = 3

class GroupsManagement(object):

    def __init__( self, PluginConf, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):
        Domoticz.Debug("GroupsManagement __init__")
        self.StartupPhase = 'init'
        self.ListOfGroups = {}      # Data structutre to store all groups
        self.TobeAdded = []         # List of IEEE/NWKID/EP/GROUP to be added
        self.TobeRemoved = []       # List of NWKID/EP/GROUP to be removed
        self.UpdatedGroups = []     # List of Groups to be updated and so trigger the Identify at the end.
        self.Cycle = 0              # Cycle count
        self.stillWIP = True

        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK            # Point to the List of IEEE to NWKID
        self.Devices = Devices              # Point to the List of Domoticz Devices

        self.ZigateComm = ZigateComm        # Point to the ZigateComm object

        self.pluginconf = PluginConf

        self.Firmware = None
        self.homeDirectory = HomeDirectory

        self.groupsConfigFilename = self.pluginconf.pluginConfig + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".txt"
        if not os.path.isfile(self.groupsConfigFilename) :
            self.groupsConfigFilename = self.pluginconf.pluginConfig + GROUPS_CONFIG_FILENAME + ".txt"
            if not os.path.isfile(self.groupsConfigFilename):
                Domoticz.Debug("No Groups Configuration File")
                self.groupsConfigFilename = None

        self.groupListFileName = self.pluginconf.pluginData + "/GroupsList-%02d" %hardwareID + ".pck"


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
    
        Domoticz.Debug("Identify effect for Group: %s" %nwkid)
        identify = False
        if effect not in effect_command:
            effect = 'Okay'
        datas = "%02d" %ADDRESS_MODE['group'] + "%s"%(nwkid) + "01" + ep + "%02x"%(effect_command[effect])  + "%02x" %0
        self.ZigateComm.sendData( "00E0", datas)

    def _write_GroupList(self):
        ' serialize pickle format the ListOfGrups '

        Domoticz.Debug("Write %s" %self.groupListFileName)
        with open( self.groupListFileName , 'wb') as handle:
            pickle.dump( self.ListOfGroups, handle, protocol=pickle.HIGHEST_PROTOCOL)
        self.HBcount=0


    def _load_GroupList(self):
        ' unserialized (load) ListOfGroup from file'

        with open( self.groupListFileName , 'rb') as handle:
            self.ListOfGroups = pickle.load( handle )


    def load_ZigateGroupConfiguration(self):
        """ This is to import User Defined/Modified Groups of Devices for processing in the hearbeatGroupMgt
        Syntax is : <groupid>,<group name>,<list of device IEEE
        """

        if self.groupsConfigFilename is None:
            return
        if not os.path.isfile( self.groupsConfigFilename ) :
            Domoticz.Debug("GroupMgt - Nothing to import")
            return
                

        myfile = open( self.groupsConfigFilename, 'r')
        Domoticz.Debug("load_ZigateGroupConfiguration. Reading the file")
        while True:
            tmpread = myfile.readline().replace('\n', '')
            Domoticz.Debug("line: %s" %tmpread )
            if not tmpread:
                break
            if tmpread[0] == '#':
                continue
            group_id = group_name = None
            for token in tmpread.split(','):
                if group_id is None:
                    # 1st item: group id
                    group_id = str(token)
                    if group_id not in self.ListOfGroups:
                        Domoticz.Debug("  - Init ListOfGroups")
                        self.ListOfGroups[group_id] = {}
                        self.ListOfGroups[group_id]['Name'] = ''
                        self.ListOfGroups[group_id]['Devices'] = []
                        self.ListOfGroups[group_id]['Imported'] = []
                    if 'Imported' not in self.ListOfGroups[group_id]:
                        self.ListOfGroups[group_id]['Imported'] = []
                    if 'Devices' not in self.ListOfGroups[group_id]:
                        self.ListOfGroups[group_id]['Devices'] = []
                    Domoticz.Debug(" )> Group ID: %s" %group_id)
                    continue
                elif group_id and group_name is None:
                    # 2nd item: group name
                    group_name = str(token)
                    if 'Name' not in self.ListOfGroups[group_id]:
                        self.ListOfGroups[group_id]['Name'] = group_name
                    else:
                        if self.ListOfGroups[group_id]['Name'] == '':
                            self.ListOfGroups[group_id]['Name'] = group_name
                    Domoticz.Debug(" )> Group Name: %s" %group_name)
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
                            Domoticz("load_ZigateGroupConfiguration - Error in ZigateGroupConfig: %s" %( _ieeetoken))
                            continue
                        if _ieee not in self.IEEE2NWK:
                            # Check if this is not the Zigate itself
                            Domoticz.Error("load_ZigateGroupConfiguration - Unknown address %s to be imported" %_ieee )
                            continue
                        # Let's check if we don't have the EP included as well
                        self.ListOfGroups[group_id]['Imported'].append( (_ieee, _ieeeEp) )

                    Domoticz.Debug(" )> Group Imported: %s" %group_name)
            if group_id :
                Domoticz.Debug("load_ZigateGroupConfiguration - Group[%s]: %s List of Devices: %s to be processed" 
                    %( group_id, self.ListOfGroups[group_id]['Name'], str(self.ListOfGroups[group_id]['Imported'])))
        myfile.close()

    # Zigate group related commands
    def _addGroup( self, device_ieee, device_addr, device_ep, grpid):

        if grpid not in self.ListOfGroups:
            Domoticz.Error("_addGroup - skip as %s is not in %s" %(grpid, str(self.ListOfGroups)))
            return

        if grpid not in self.UpdatedGroups:
            self.UpdatedGroups.append(grpid)

        Domoticz.Debug("_addGroup - Adding device: %s/%s into group: %s" \
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
            Domoticz.Log("statusGroupRequest - Status: %s for Command: %s" %(Status, PacketType))
        return

    def addGroupResponse(self, MsgData):
        ' decoding 0x8060 '

        Domoticz.Debug("addGroupResponse - MsgData: %s (%s)" %(MsgData,len(MsgData)))
        # search for the Group/dev
        if len(MsgData) == 14:  # Firmware < 030f
            MsgSrcAddr = None
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            Domoticz.Log("addGroupResponse < 3.0f- [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

        elif len(MsgData) == 18:    # Firmware >= 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            MsgSrcAddr = MsgData[14:18]
            Domoticz.Log("addGroupResponse >= 3.0f - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
        else:
            Domoticz.Log("addGroupResponse - uncomplete message %s" %MsgData)
            
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
                Domoticz.Log("addGroupResponse - Status: %s - Remove the device from Group" %MsgStatus)
                self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]['Phase'] = 'DEL-Membership'
                self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]['Phase-Stamp'] = int(time())
                self._removeGroup(  MsgSrcAddr, MsgEP, MsgGroupID )
        return

    def _viewGroup( self, device_addr, device_ep, goup_addr ):

        Domoticz.Log("_viewGroup - addr: %s ep: %s group: %s" %(device_addr, device_ep, goup_addr))
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

        Domoticz.Log("Decode8061 - SEQ: %s, Source: %s EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgSrcAddr, MsgEP, MsgClusterID, MsgGroupID, MsgDataStatus))
        return


    def _getGroupMembership(self, device_addr, device_ep, group_list=None):

        Domoticz.Debug("_getGroupMembership - %s/%s from %s" %(device_addr, device_ep, group_list))
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

        Domoticz.Debug("_getGroupMembership - Addr: %s Ep: %s to Group: %s" %(device_addr, device_ep, group_list))
        Domoticz.Debug("_getGroupMembership - 0062/%s" %datas)
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

        Domoticz.Debug("getGroupMembershipResponse - SEQ: %s, EP: %s, ClusterID: %s, sAddr: %s, Capacity: %s, Count: %s"
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
            #groupID = MsgData[16+(idx*4):16+(4+(idx*4))]
            groupID = MsgData[12+(idx*4):12+(4+(idx*4))]

            #if groupID in ( '0000' , 'ffff'): 
            #    idx += 1
            #    continue
            #if groupID == 'ffff':
            #    groupID = '0000'

            if groupID not in self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]:
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID] = {}
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase'] = {}
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase-Stamp'] = {}

            if self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP][groupID]['Phase'] not in ( {}, 'REQ-Membership') :
                Domoticz.Debug("getGroupMembershipResponse - not in the expected Phase : %s for %s/%s - %s" 
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

            Domoticz.Log("getGroupMembershipResponse - ( %s,%s ) is part of Group %s"
                    %( MsgSourceAddress, MsgEP, groupID))
                
            idx += 1
        return

    def _removeGroup(self,  device_addr, device_ep, goup_addr ):

        if goup_addr not in self.UpdatedGroups:
            self.UpdatedGroups.append(goup_addr)

        Domoticz.Log("_removeGroup - %s/%s on %s" %(device_addr, device_ep, goup_addr))
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
            Domoticz.Log("removeGroupResponse < 3.0f - [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

        elif len(MsgData) == 18:    # Firmware >= 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            MsgSrcAddr = MsgData[14:18]
            Domoticz.Log("removeGroupResponse >= 3.0f - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
        else:
            Domoticz.Log("removeGroupResponse - uncomplete message %s" %MsgData)

        Domoticz.Debug("Decode8063 - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgStatus))

        if MsgStatus in ( '00' ) :
            if MsgSrcAddr : # 3.0f
                if 'GroupMgt' in self.ListOfDevices[MsgSrcAddr]:
                    if MsgEP in self.ListOfDevices[MsgSrcAddr]['GroupMgt']:
                        if MsgGroupID in self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP]:
                            del  self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP][MsgGroupID]

                Domoticz.Log("removeGroupResponse - Devices: %s" %(str(self.ListOfGroups[MsgGroupID]['Devices'])))

                if (MsgSrcAddr, MsgEP) in self.ListOfGroups[MsgGroupID]['Devices']:
                    Domoticz.Log("removeGroupResponse - removing %s from %s" %( str(( MsgSrcAddr, MsgEP)), str(self.ListOfGroups[MsgGroupID]['Devices'])))
                    self.ListOfGroups[MsgGroupID]['Devices'].remove( ( MsgSrcAddr, MsgEP) )
            else: # < 3.0e should not happen
                Domoticz.Log("Group Member removed from unknown device")
                unique = 0
                delDev = ''
                for iterDev in self.ListOfDevices:
                    if 'GroupMgt' in self.ListOfDevices[iterDev]:
                        if MsgEP in self.ListOfDevices[iterDev]['GroupMgt']:
                            if MsgGroupID in self.ListOfDevices[iterDev]['GroupMgt'][MsgEP]:
                                if 'Phase' in self.ListOfDevices[iterDev]['GroupMgt'][MsgEP][MsgGroupID]:
                                    if self.ListOfDevices[iterDev]['GroupMgt'][MsgEP][MsgGroupID]['Phase'] == 'DEL-Membership':
                                        Domoticz.Log('Dev: %s is a possible candidate to be removed from %s' %(iterDev, MsgGroupID))
                                        unique += 1
                                        delDev = iterDev
                if unique == 1:
                    del self.ListOfDevices[delDev]['GroupMgt'][MsgEP][MsgGroupID]
        else:
            Domoticz.Log("removeGroupResponse - GroupID: %s unexpected Status: %s" %(MsgGroupID, MsgStatus))

        return

    def _removeAllGroups(self, device_addr, device_ep ):

        Domoticz.Log("_removeAllGroups - %s/%s " %(device_addr, device_ep))
        datas = "02" + device_addr + "01" + device_ep
        self.ZigateComm.sendData( "0064", datas)
        return

    def _addGroupifIdentify(self, device_addr, device_ep, goup_addr = "0000"):
        datas = "02" + device_addr + "01" + device_ep + goup_addr
        self.ZigateComm.sendData( "0065", datas)
        return

    def FreeUnit(self, Devices):
        '''
        FreeUnit
        Look for a Free Unit number.
        '''
        FreeUnit = ""
        for x in range(1, 255):
            if x not in Devices:
                Domoticz.Debug("FreeUnit - device " + str(x) + " available")
                return x
        else:
            Domoticz.Debug("FreeUnit - device " + str(len(Devices) + 1))
            return len(Devices) + 1


    # Domoticz relaed
    def _createDomoGroupDevice(self, groupname, group_nwkid):
        ' Create Device for just created group in Domoticz. '

        if groupname == '' or group_nwkid == '':
            Domoticz.Log("createDomoGroupDevice - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

        for x in self.Devices:
            if self.Devices[x].DeviceID == group_nwkid:
                Domoticz.Log("_createDomoGroupDevice - existing group %s" %(self.Devices[x].Name))
                return

        unit = self.FreeUnit( self.Devices )
        Domoticz.Debug("_createDomoGroupDevice - Unit: %s" %unit)
        myDev = Domoticz.Device(DeviceID=str(group_nwkid), Name=str(groupname), Unit=unit, Type=241, Subtype=7, Switchtype=7)
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1 :
            Domoticz.Log("CreateDomoGroupDevice - failed to create Group device.")

    def updateDomoGroupDevice( self, group_nwkid):
        """ 
        Update the Group status On/Off and Level , based on the attached devices
        """

        if group_nwkid not in self.ListOfGroups:
            Domoticz.Error("updateDomoGroupDevice - unknown group: %s" %group_nwkid)
            return
        if 'Devices' not in self.ListOfGroups[group_nwkid]:
            Domoticz.Debug("updateDomoGroupDevice - no Devices for that group: %s" %self.ListOfGroups[group_nwkid])
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
            Domoticz.Debug("updateDomoGroupDevice - %s, %s" %(dev_nwkid, dev_ep))
            if dev_nwkid in self.ListOfDevices:
                if 'Ep' in  self.ListOfDevices[dev_nwkid]:
                    if dev_ep in self.ListOfDevices[dev_nwkid]['Ep']:
                        if '0006' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                            if str(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']).isdigit():
                                if int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']) != 0:
                                    Domoticz.Debug("updateDomoGroupDevice - Device: %s OnOff: %s" \
                                            %(dev_nwkid, (self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006'])))
                                    nValue = 1
                        if '0008' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                            Domoticz.Debug("updateDomoGroupDevice - Cluster 0008 value: %s" %self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'])
                            if self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'] != '' and self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'] != {}:
                                if level is None:
                                    level = int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'],16)
                                else:
                                    level = ( level +  int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'],16)) // 2
                                Domoticz.Debug("updateDomoGroupDevice - Device: %s level: %s" \
                                        %(dev_nwkid, (self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'])))

            Domoticz.Debug("updateDomoGroupDevice - OnOff: %s, Level: %s" %( nValue, level))
                                
        if level:
            sValue = str(int((level*100)/255))
            # Let's check if this is Shutter or a Color Bulb (as for Color Bulb we need nValue = 1
            if nValue == 1 and self.Devices[unit].SwitchType == 16 :
                nValue = 2
        else:
            sValue = "Off"
        Domoticz.Debug("UpdateDeviceGroup Values %s : %s '(%s)'" %(nValue, sValue, self.Devices[unit].Name))
        if nValue != self.Devices[unit].nValue or sValue != self.Devices[unit].sValue:
            Domoticz.Log("UpdateDeviceGroup Values %s:%s '(%s)'" %(nValue, sValue, self.Devices[unit].Name))
            self.Devices[unit].Update( nValue, sValue)


    def _removeDomoGroupDevice(self, group_nwkid):
        ' User has remove dthe Domoticz Device corresponding to this group'

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
        Domoticz.Debug("_removeDomoGroupDevice - removing Domoticz Widget %s" %self.Devices[unit].Name)
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
                    Domoticz.Log("processRemoveGroup - remove %s %s %s" 
                            %(iterDev, iterEP, grpid))
                    self._removeGroup(iterDev, iterEP, grpid )
                    _toremove.append( (iterDev,iterEP) )
        for removeDev, removeEp in _toremove:
            del self.ListOfDevices[removeDev]['GroupMgt'][removeEp][grpid]

        del self.ListOfGroups[grpid]

        return

    def processCommand( self, unit, nwkid, Command, Level, Color_ ) : 

        Domoticz.Log("processCommand - unit: %s, nwkid: %s, cmd: %s, level: %s, color: %s" %(unit, nwkid, Command, Level, Color_))

        if nwkid not in self.ListOfGroups:
            return
        for iterDev, iterEp in self.ListOfGroups[nwkid]['Devices']:
            Domoticz.Debug('processCommand - reset heartbeat for device : %s' %iterDev)
            self.ListOfDevices[iterDev]['Heartbeat'] = '0'

        EPin = EPout = '01'

        if Command == 'Off' :
            zigate_cmd = "0092"
            zigate_param = '00'
            nValue = 0
            sValue = 'Off'
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            Domoticz.Debug("Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

        elif Command == 'On' :
            zigate_cmd = "0092"
            zigate_param = '01'
            nValue = '1'
            sValue = 'On'
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            Domoticz.Debug("Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

        elif Command == 'Set Level':
            zigate_cmd = "0081"
            OnOff = "01"
            value=int(Level*255/100)
            zigate_param = OnOff + "%02x" %value + "0010"
            nValue = '1'
            sValue = str(Level)
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            Domoticz.Debug("Command: %s" %datas)
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
            Domoticz.Debug("Command: %s - data: %s" %(zigate_cmd,datas))
            self.ZigateComm.sendData( zigate_cmd, datas)

            if Hue_List['m'] == 1:
                ww = int(Hue_List['ww']) # Can be used as level for monochrome white
                #TODO : Jamais vu un device avec ca encore
                Domoticz.Debug("Not implemented device color 1")
            #ColorModeTemp = 2   // White with color temperature. Valid fields: t
            if Hue_List['m'] == 2:
                #Value is in mireds (not kelvin)
                #Correct values are from 153 (6500K) up to 588 (1700K)
                # t is 0 > 255
                TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700);
                TempMired = 1000000 // TempKelvin
                zigate_cmd = "00C0"
                zigate_param = Hex_Format(4,TempMired) + "0000"
                datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Debug("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

            #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
            elif Hue_List['m'] == 3:
                x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                #Convert 0>1 to 0>FFFF
                x = int(x*65536)
                y = int(y*65536)
                strxy = Hex_Format(4,x) + Hex_Format(4,y)
                zigate_cmd = "00B7"
                zigate_param = strxy + "0000"
                datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Debug("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

            #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
            elif Hue_List['m'] == 4:
                ww = int(Hue_List['ww'])
                cw = int(Hue_List['cw'])
                x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                #TODO, Pas trouve de device avec ca encore ...
                Domoticz.Debug("Not implemented device color 2")

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
                Domoticz.Debug("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                zigate_cmd = "0081"
                zigate_param = OnOff + Hex_Format(2,value) + "0010"
                datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Debug("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                #Update Device
                nValue = 1
                sValue = str(value)
                self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_) 
                return

    def hearbeatGroupMgt( self ):
        ' hearbeat to process Group Management actions '
        # Groups Management
        # self.pluginconf.enablegroupmanagement 
        # self.pluginconf.discoverZigateGroups 
        # self.pluginconf.enableConfigGroups

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
            Domoticz.Log("Init phase")
            self.StartupPhase = 'discovery'
            if os.path.isfile( self.groupListFileName ) :
                Domoticz.Debug("GroupList.pck exists")
                last_update_GroupList = modification_date( self.groupListFileName )
                Domoticz.Debug("Last Update of GroupList: %s" %last_update_GroupList)

                if self.groupsConfigFilename:
                    if os.path.isfile( self.groupsConfigFilename ):
                        Domoticz.Debug("Config file exists")
                        last_update_ConfigFile = modification_date( self.groupsConfigFilename )
                        Domoticz.Debug("Last Update of Config File: %s" %last_update_ConfigFile)
                        if last_update_GroupList > last_update_ConfigFile :
                            # GroupList is newer , just reload the file and exit
                            Domoticz.Status("No update of Groups needed")
                            self.StartupPhase = 'end of group startup'
                            self._load_GroupList()
                    else:   # No config file, so let's move on
                        Domoticz.Debug("No Config file, let's use the GroupList")
                        Domoticz.Debug("switch to end of Group Startup")
                        self._load_GroupList()
                        self.StartupPhase = 'end of group startup'

        elif self.StartupPhase == 'discovery':
            # We will send a Request for Group memebership to each active device
            # In case a device doesn't belo,ng to any group, no response is provided.
            Domoticz.Log("Discovery mode - Searching for Group Membership")
            self.stillWIP = True
            _workcompleted = True
            listofdevices = list(self.ListOfDevices)
            for iterDev in listofdevices:
                if 'PowerSource' in self.ListOfDevices[iterDev]:
                    if self.ListOfDevices[iterDev]['PowerSource'] != 'Main':
                        continue
                if 'Ep' in self.ListOfDevices[iterDev]:
                    for iterEp in self.ListOfDevices[iterDev]['Ep']:
                        if iterEp == 'ClusterType': continue
                        if  ( iterDev == '0000' or 'ClusterType' in self.ListOfDevices[iterDev] or 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] ) and \
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

                            if  len(self.ZigateComm._normalQueue) > MAX_LOAD:
                                Domoticz.Debug("normalQueue: %s" %len(self.ZigateComm._normalQueue))
                                Domoticz.Debug("normalQueue: %s" %(str(self.ZigateComm._normalQueue)))
                                Domoticz.Log("too busy, will try again ...%s" %len(self.ZigateComm._normalQueue))
                                _workcompleted = False
                                break # will continue in the next cycle

                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase'] = 'REQ-Membership'
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] = int(time())
                            self._getGroupMembership(iterDev, iterEp)   # We request MemberShip List
                            Domoticz.Debug(" - request group membership for %s/%s" %(iterDev, iterEp))
            else:
                if _workcompleted:
                    Domoticz.Log("hearbeatGroupMgt - Finish Discovery Phase" )
                    self.StartupPhase = 'finish discovery'

        elif self.StartupPhase in ( 'finish discovery', 'finish discovery continue') :
            # Check for completness or Timeout
            if self.StartupPhase ==  'finish discovery':
                Domoticz.Log("Membership gathering")
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

                            Domoticz.Debug('Checking if process is done for %s/%s - %s -> %s' 
                                    %(iterDev,iterEp,iterGrp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))

                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] == 'OK-Membership':
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] + TIMEOUT > now:
                                _completed = False
                                break # Need to wait a couple of sec.

                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'TimeOut'
                            Domoticz.Debug(" - No response receive for %s/%s - assuming no group membership for %s " %(iterDev,iterEp, iterGrp))
                        else:
                            if 'XXXX' in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                                Domoticz.Debug('Checking if process is done for %s/%s - XXXX -> %s' 
                                    %(iterDev,iterEp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX'])))
                                if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] + TIMEOUT > now:
                                    _completed = False
                                    break
                                del  self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']
            else:
                if _completed:
                    for iterGrp in self.ListOfGroups:
                        Domoticz.Log("Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
                        Domoticz.Debug("Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
                        for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                            Domoticz.Log("  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))
                    Domoticz.Log("hearbeatGroupMgt - Discovery Completed" )
                    self.StartupPhase = 'load config'

        elif  self.StartupPhase == 'load config':
            self.load_ZigateGroupConfiguration()
            Domoticz.Log("Loading Zigate Group Configuration file")
            self.TobeAdded = []
            self.TobeRemoved = []
            self.StartupPhase = 'process config'

        elif self.StartupPhase == 'process config':
            self.stillWIP = True
            for iterGrp in self.ListOfGroups:
                if 'Imported' not in self.ListOfGroups[iterGrp]:
                    continue
                if len(self.ListOfGroups[iterGrp]['Imported']) == 0 and len(self.ListOfGroups[iterGrp]['Devices']) == 0 :
                    continue

                Domoticz.Debug("Processing Group: %s - Checking Removal" %iterGrp)
                # Remove group membership
                Domoticz.Debug(" - %s" %self.ListOfGroups[iterGrp]['Devices'])
                Domoticz.Debug(" - %s" %self.ListOfGroups[iterGrp]['Imported'])

                for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                    iterIEEE = self.ListOfDevices[iterDev]['IEEE']

                    Domoticz.Debug("    - checking device: %s / %s to be removed " %(iterDev, iterEp))
                    Domoticz.Debug("    - checking device: %s " %self.ListOfGroups[iterGrp]['Imported'])
                    Domoticz.Debug("    - checking device: IEEE: %s " %iterIEEE)

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
                    Domoticz.Log("Adding %s/%s to be removed from %s" 
                            %(removeNKWID, iterEp, iterGrp))
                    self.TobeRemoved.append( ( removeNKWID, iterEp, iterGrp ) )

                Domoticz.Debug("Processing Group: %s - Checking Adding" %iterGrp)
                # Add group membership
                for iterIEEE, import_iterEp in self.ListOfGroups[iterGrp]['Imported']:
                    iterDev = self.IEEE2NWK[iterIEEE]
                    Domoticz.Debug("    - checking device: %s to be added " %iterDev)
                    if iterDev in self.ListOfGroups[iterGrp]['Devices']:
                        Domoticz.Debug("%s already in group %s" %(iterDev, iterGrp))
                        continue

                    Domoticz.Debug("       - checking device: %s " %iterDev)
                    if 'Ep' in self.ListOfDevices[iterDev]:
                        _listDevEp = []
                        if import_iterEp:
                            _listDevEp.append(import_iterEp)
                        else:
                            _listDevEp = list(self.ListOfDevices[iterDev]['Ep'])
                        Domoticz.Debug('List of Ep: %s' %_listDevEp)

                        for iterEp in _listDevEp:
                            Domoticz.Debug("       - Check existing Membership %s/%s" %(iterDev,iterEp))

                            if 'GroupMgt' in self.ListOfDevices[iterDev]:
                                if iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                                    if iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                                        if  self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] == 'OK-Membership':
                                            Domoticz.Debug("       - %s/%s already in group %s" %(iterDev, iterEp, iterGrp))
                                            continue
                            if iterEp not in self.ListOfDevices[iterDev]['Ep']:
                                Domoticz.Error("whearbeatGroupMgt - unknown EP %s for %s against (%s)" %(iterEp, iterDev, self.ListOfDevices[iterDev]['Ep']))
                                continue

                            if  ( iterDev == '0000' or 'ClusterType' in self.ListOfDevices[iterDev] or 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] ) and \
                                    '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                                    ( '0006' in self.ListOfDevices[iterDev]['Ep'][iterEp] or '0008' in self.ListOfDevices[iterDev]['Ep'][iterEp] ):
                                Domoticz.Debug("Adding %s/%s to be added to %s"
                                        %( iterDev, iterEp, iterGrp))
                                self.TobeAdded.append( ( iterIEEE, iterDev, iterEp, iterGrp ) )

            Domoticz.Log("hearbeatGroupMgt - End of Configuration processing" )
            Domoticz.Log("  - To be removed : %s" %self.TobeRemoved)
            Domoticz.Log("  - To be added : %s" %self.TobeAdded)
            if len(self.TobeAdded) == 0 and len(self.TobeRemoved) == 0:
                self.StartupPhase = 'check group list'
                Domoticz.Debug("Updated Groups are : %s" %self.UpdatedGroups)
                self._write_GroupList()
                for iterGroup in self.UpdatedGroups:
                    self._identifyEffect( iterGroup, '01', effect='Okay' )
            else:
                self.StartupPhase = 'perform command'

        elif self.StartupPhase == 'perform command':
            self.stillWIP = True
            _completed = True
            Domoticz.Log("hearbeatGroupMgt - Perform Zigate commands")
            Domoticz.Log(" - Removal to be performed: %s" %str(self.TobeRemoved))
            for iterDev, iterEp, iterGrp in list(self.TobeRemoved):
                if  len(self.ZigateComm._normalQueue) > MAX_LOAD:
                    Domoticz.Debug("normalQueue: %s" %len(self.ZigateComm._normalQueue))
                    Domoticz.Debug("normalQueue: %s" %(str(self.ZigateComm._normalQueue)))
                    _completed = False
                    Domoticz.Log("Too buys, will come back later")
                    break # will continue in the next cycle
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'DEL-Membership'
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = int(time())
                self._removeGroup( iterDev, iterEp, iterGrp )
                self.TobeRemoved.remove( (iterDev, iterEp, iterGrp) )

            Domoticz.Log(" - Add to be performed: %s" %str(self.TobeAdded))
            for iterIEEE, iterDev, iterEp, iterGrp in list(self.TobeAdded):
                if  len(self.ZigateComm._normalQueue) > MAX_LOAD:
                    Domoticz.Debug("normalQueue: %s" %len(self.ZigateComm._normalQueue))
                    Domoticz.Debug("normalQueue: %s" %(str(self.ZigateComm._normalQueue)))
                    _completed = False
                    Domoticz.Log("Too buys, will come back later")
                    break # will continue in the next cycle

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

                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'ADD-Membership'
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = int(time())
                self._addGroup( iterIEEE, iterDev, iterEp, iterGrp )
                self.TobeAdded.remove( (iterIEEE, iterDev, iterEp, iterGrp) )

            if _completed:
                self.StartupPhase = 'finish configuration'

        elif self.StartupPhase == 'finish configuration':
            # Check for completness or Timeout
            Domoticz.Log("Finishing configuration mode")
            self.stillWIP = True
            now = time()
            _completed = True
            for iterDev in self.ListOfDevices:
                if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                    continue
                if 'Ep' in self.ListOfDevices[iterDev]:
                    for iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                        for iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                            if iterDev == '0000' and iterGrp in ( '0000' ):
                                #Adding Zigate to group 0x0000 or 0xffff
                                # We do not get any response
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'OK-Membership'

                            if iterGrp == 'XXXX': continue

                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] in ( 'OK-Membership', 'TimmeOut'):
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] not in ( 'DEL-Membership' ,'ADD-Membership' ):
                                Domoticz.Debug("Unexpected phase for %s/%s in group %s : phase!: %s"
                                %( iterDev, iterEp, iterGrp,  str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] + TIMEOUT > now:
                                _completed = False
                                break # Wait a couple of Sec

                            Domoticz.Debug('Checking if process is done for %s/%s - %s -> %s' 
                                    %(iterDev,iterEp,iterGrp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))

                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'TimeOut'
                            Domoticz.Debug(" - No response receive for %s/%s - assuming no group membership to %s" %(iterDev,iterEp, iterGrp))
            else:
                if _completed:
                    Domoticz.Log("hearbeatGroupMgt - Configuration mode completed" )
                    self.Cycle += 1
                    if self.Cycle > MAX_CYCLE:
                        Domoticz.Log("We reach the max number of Cycle and didn't succeed in the Group Creation")
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
            Domoticz.Log("Checking Group list")
            self.stillWIP = True
            for iterGrp in list(self.ListOfGroups):
                Domoticz.Debug("Checking %s " %iterGrp)
                Domoticz.Debug("  - Devices: %s" %len(self.ListOfGroups[iterGrp]['Devices']))
                for x in self.Devices:
                    if self.Devices[x].DeviceID == iterGrp:
                        if len(self.ListOfGroups[iterGrp]['Devices']) == 0:
                            Domoticz.Log("hearbeatGroupMgt - Remove Domotticz Device : %s for Group: %s " %(self.Devices[x].Name, iterGrp))
                            self._removeDomoGroupDevice( iterGrp)
                            del self.ListOfGroups[iterGrp] 
                        else:
                            self.ListOfGroups[iterGrp]['Name'] = self.Devices[x].Name
                        break
                else:
                    # Unknown group in Domoticz. Create it
                    if len(self.ListOfGroups[iterGrp]['Devices']) == 0:
                        del self.ListOfGroups[iterGrp] 
                        continue
                    if self.ListOfGroups[iterGrp]['Name'] == '':
                        self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                    Domoticz.Log("hearbeatGroupMgt - create Domotciz Widget for %s " %self.ListOfGroups[iterGrp]['Name'])
                    self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)
            self.StartupPhase = 'end of group startup'

        elif self.StartupPhase == 'end of group startup':
            for iterGrp in self.ListOfGroups:
                Domoticz.Log("Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
                Domoticz.Log("Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
                for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                    if iterDev in self.ListOfDevices:
                        Domoticz.Log("  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))

            Domoticz.Log("Ready for working")
            self.StartupPhase = 'ready'
            self.stillWIP = False
        return
