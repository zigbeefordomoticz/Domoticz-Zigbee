#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

# Zigate group related commands


import Domoticz
import json
import pickle
import os.path

from time import time
from datetime import datetime

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.zigateConsts import ADDRESS_MODE, MAX_LOAD_ZIGATE, ZIGATE_EP

from Classes.AdminWidgets import AdminWidgets


def _addGroup( self, device_ieee, device_addr, device_ep, grpid):

    if device_addr == '0000' and device_ep != '01':
        return

    if grpid not in self.ListOfGroups:
        Domoticz.Error("_addGroup - skip as %s is not in %s" %(grpid, str(self.ListOfGroups)))
        return

    if grpid not in self.UpdatedGroups:
        self.UpdatedGroups.append(grpid)

    self.logging( 'Debug', "_addGroup - Adding device: %s/%s into group: %s" \
            %( device_addr, device_ep, grpid))
    datas = "02" + device_addr + ZIGATE_EP + device_ep + grpid
    self.ZigateComm.sendData( "0060", datas)

def statusGroupRequest( self, MsgData):
    """
    This is a 0x8000 message
    """
    Status=MsgData[0:2]
    SEQ=MsgData[2:4]
    PacketType=MsgData[4:8]

    if Status != '00':
        self.logging( 'Log', "statusGroupRequest - Status: %s for Command: %s" %(Status, PacketType))

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

def _viewGroup( self, device_addr, device_ep, goup_addr ):

    self.logging( 'Debug', "_viewGroup - addr: %s ep: %s group: %s" %(device_addr, device_ep, goup_addr))
    datas = "02" + device_addr + ZIGATE_EP + device_ep + goup_addr
    self.ZigateComm.sendData( "0061", datas)

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

def _getGroupMembership(self, device_addr, device_ep, group_list=None):

    self.logging( 'Debug', "_getGroupMembership - %s/%s from %s" %(device_addr, device_ep, group_list))
    datas = "02" + device_addr + ZIGATE_EP + device_ep 

    if not group_list:
        lenGrpLst = 0
        datas += "00"
    else:
        if not isinstance(group_list, list):
            # We received only 1 group
            group_list_ = "%04x" %(group_list)
            lenGrpLst = 1
        else:
            lenGrpLst = len(group_list)
            for x in group_list:
                group_list_ += "%04x" %(x)
        datas += "%02.x" %(lenGrpLst) + group_list_

    self.logging( 'Debug', "_getGroupMembership - Addr: %s Ep: %s to Group: %s" %(device_addr, device_ep, group_list))
    self.logging( 'Debug', "_getGroupMembership - 0062/%s" %datas)
    self.ZigateComm.sendData( "0062", datas)

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
    if MsgSourceAddress == '0000' and MsgEP != '01':
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
            #self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP) )
            self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP, self.ListOfDevices[MsgSourceAddress]['IEEE']) )
        else:
            if ( MsgSourceAddress,MsgEP) not in self.ListOfGroups[groupID]['Devices']:
                self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP, self.ListOfDevices[MsgSourceAddress]['IEEE']) )
                #self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP ) )

        self.logging( 'Debug', "getGroupMembershipResponse - ( %s,%s ) is part of Group %s" %( MsgSourceAddress, MsgEP, groupID))
            
        idx += 1

def _removeGroup(self,  device_addr, device_ep, goup_addr ):

    if goup_addr not in self.UpdatedGroups:
        self.UpdatedGroups.append(goup_addr)

    self.logging( 'Debug', "_removeGroup - %s/%s on %s" %(device_addr, device_ep, goup_addr))
    datas = "02" + device_addr + ZIGATE_EP + device_ep + goup_addr
    self.ZigateComm.sendData( "0063", datas)

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

def _removeAllGroups(self, device_addr, device_ep ):

    self.logging( 'Debug', "_removeAllGroups - %s/%s " %(device_addr, device_ep))
    datas = "02" + device_addr + ZIGATE_EP + device_ep
    self.ZigateComm.sendData( "0064", datas)

def _addGroupifIdentify(self, device_addr, device_ep, goup_addr = "0000"):
    datas = "02" + device_addr + ZIGATE_EP + device_ep + goup_addr
    self.ZigateComm.sendData( "0065", datas)
