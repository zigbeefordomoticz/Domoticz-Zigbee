# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

# All operations to and from Zigate
import Domoticz

from time import time

from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl

from GroupMgtv2.GrpCallBackResponses import checkToCreateOrUpdateGroup, checkToRemoveGroup
from GroupMgtv2.GrpCommands import check_group_member_ship


# Group Management Command
def statusGroupRequest( self, MsgData):
    """
    This is a 0x8000 message
    """
    Status = MsgData[0:2]
    SEQ = MsgData[2:4]
    PacketType = MsgData[4:8]

    self.logging( 'Debug', "statusOnGrpCommand - Status: %s for Command: %s" %(Status, PacketType))   
    if Status != '00':
        self.logging( 'Log', "statusOnGrpCommand - Status: %s for Command: %s" %(Status, PacketType))

def add_group_member_ship_response(self, MsgData):
    """
    Response after a addGroupMemberShip

    Status:
    0x00:  Ok
    0x8a:  The device does not have storage space to support the requested operation.
    0x8b:  The device is not in the proper state to support the requested operation.
    """

    self.logging( 'Debug', "add_group_member_ship_response - MsgData: %s (%s)" %(MsgData, len(MsgData)))
    # search for the Group/dev
    if len(MsgData) not in [14, 18]:
        Domoticz.Error("add_group_member_ship_response - uncomplete message %s" %MsgData)
        return
    if len(MsgData) == 14:  # Firmware < 030f
        MsgSrcAddr = None
        MsgSequenceNumber = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterID = MsgData[4:8]
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]
        self.logging( 'Debug', "add_group_member_ship_response < 3.0f- [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))
    elif len(MsgData) == 18:    # Firmware >= 030f
        MsgSequenceNumber = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterID = MsgData[4:8]
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]
        MsgSrcAddr = MsgData[14:18]
 
        self.logging( 'Debug', "add_group_member_ship_response - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
 
    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("add_group_member_ship_response Requesting to add group %s membership on non existing device %s" %(MsgGroupID, MsgSrcAddr))
        return

    if MsgStatus == '00':
        # Success
        if 'GroupMemberShip' not in self.ListOfDevices[ MsgSrcAddr ]:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'] = {}

        if MsgEP not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP] = {}

        if MsgGroupID not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP]:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ MsgGroupID ] = {}

        self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ MsgGroupID ]['Status'] = 'OK'  
        checkToCreateOrUpdateGroup(self, MsgSrcAddr, MsgEP, MsgGroupID  )   

    else:
        # Let's check what is the membership ?
        check_group_member_ship( self, MsgSrcAddr, MsgEP , MsgGroupID)
 
def check_group_member_ship_response( self, MsgData):
    ' Decode 0x8061'

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSrcAddr = MsgData[14:18]

    self.logging( 'Debug', "check_group_member_ship_response - SEQ: %s, Source: %s EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
            %( MsgSequenceNumber, MsgSrcAddr, MsgEP, MsgClusterID, MsgGroupID, MsgStatus))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("check_group_member_ship_response Requesting to add group %s membership on non existing device %s" %(MsgGroupID, MsgSrcAddr))
        return

    if MsgStatus == '00':
        if 'GroupMemberShip' not in self.ListOfDevices[ MsgSrcAddr ]:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'] = {}

        if MsgEP not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][ MsgEP ] = {}

        if MsgGroupID not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][ MsgEP ]:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ MsgGroupID ] = {}

        # Success
        self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ MsgGroupID ]['Status'] = 'OK'  
        checkToCreateOrUpdateGroup(self, MsgSrcAddr, MsgEP, MsgGroupID  )

    # If we have receive a MsgStatus error, we cannot conclude, so we consider the membership to that group, not existing

def look_for_group_member_ship_response( self, MsgData):
    """
    Provide the list of Group Membership for the particula device
    """

    lenMsgData = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]

    MsgCapacity = MsgData[8:10]
    MsgGroupCount = MsgData[10:12]
    MsgListOfGroup = MsgData[12:lenMsgData-4]
    MsgSrcAddr = MsgData[lenMsgData-4:lenMsgData]

    self.logging( 'Debug', "look_for_group_member_ship_response - SEQ: %s, EP: %s, ClusterID: %s, sAddr: %s, Capacity: %s, Count: %s"
            %(MsgSequenceNumber, MsgEP, MsgClusterID, MsgSrcAddr, MsgCapacity, MsgGroupCount))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("look_for_group_member_ship_response %s membership on non existing device %s" %( MsgSrcAddr))
        return

    if 'GroupMemberShip' not in self.ListOfDevices[ MsgSrcAddr ]:
        self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'] = {}

    if MsgEP not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']:
        self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][ MsgEP ] = {}

    for idx in range(int(MsgGroupCount, 16)):
        # Let scan eachgroup and update Device data structure
        GrpId = MsgData[12+(idx*4):12+(4+(idx*4))]

        if GrpId not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][ MsgEP ]:
            self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ GrpId ] = {}

        self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ GrpId ]['Status'] = 'OK'
        self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ GrpId ]['TimeStamp'] = 0
        checkToCreateOrUpdateGroup(self, MsgSrcAddr, MsgEP, GrpId  )

def remove_group_member_ship_response( self, MsgData):
    ' Decode 0x8063'

    if len(MsgData) not in [14, 18]:
        Domoticz.Error("removeGroupMemberShipResponse - uncomplete message %s" %MsgData)
        return

    if len(MsgData) == 14:  # Firmware < 030f
        MsgSequenceNumber = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterID = MsgData[4:8]
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]
        MsgSrcAddr = None
        self.logging( 'Debug', "removeGroupMemberShipResponse < 3.0f - [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

    elif len(MsgData) == 18:    # Firmware >= 030f
        MsgSequenceNumber = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterID = MsgData[4:8]
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]
        MsgSrcAddr = MsgData[14:18]
        self.logging( 'Debug', "removeGroupMemberShipResponse - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))

    self.logging( 'Debug', "removeGroupMemberShipResponse - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s"
            %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgStatus))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("removeGroupMemberShipResponse %s membership on non existing device %s" %( MsgGroupID, MsgSrcAddr))
        checkToRemoveGroup( self,MsgSrcAddr, MsgEP, MsgGroupID )
        return

    if 'GroupMemberShip' not in self.ListOfDevices[ MsgSrcAddr ]:
        return
    if MsgEP not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']:
        return

    # This quiet an issue if we reach that part. Basically we have received a Status error for a Remove Group Membership.
    # It is hard to know if this is because we ask to removed a non existing membership, or if we have something else.
    # So the Approach is to consider the Membership removed so we will update the structutre accordinly, but
    # we will request a check_group_member_ship and if it exist, then it will be created in the data structutr
    if MsgGroupID in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP]:
        del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ MsgGroupID ]

    if len(self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP]) == 0:
        del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP]

    if len(self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']) == 0:
        del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']

    checkToRemoveGroup( self,MsgSrcAddr, MsgEP, MsgGroupID )

    if MsgStatus != '00':
        check_group_member_ship( self, MsgSrcAddr, MsgEP , MsgGroupID)