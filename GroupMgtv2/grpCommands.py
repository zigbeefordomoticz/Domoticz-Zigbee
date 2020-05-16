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

# Group Management Command
def status_on_grp_command( self, MsgData):
    """
    This is a 0x8000 message
    """
    Status = MsgData[0:2]
    SEQ = MsgData[2:4]
    PacketType = MsgData[4:8]

    if Status != '00':
        self.logging( 'Log', "statusOnGrpCommand - Status: %s for Command: %s" %(Status, PacketType))

def add_group_member_ship( self, device_addr, device_ep, grpid):
    """
    Add Group Membership grpid to device_addr
    """

    if 'GroupMemberShip' not in self.ListOfDevices[ device_addr ]:
        self.ListOfDevices[ device_addr ]['GroupMemberShip'] = {}

     if device_ep not in self.ListOfDevices[ device_addr ]['GroupMemberShip']:
        self.ListOfDevices[ device_addr ]['GroupMemberShip'][ device_ep ] = {}

    if grpid not in self.ListOfDevices[ device_addr ]['GroupMemberShip'][ device_ep ]:
        self.ListOfDevices[ device_addr ]['GroupMemberShip'][device_ep][ grpid ] = {}

    self.ListOfDevices[ device_addr ]['GroupMemberShip'][device_ep][ grpid ]['Status'] = 'addGroupMembeShip'
    self.ListOfDevices[ device_addr ]['GroupMemberShip'][device_ep][ grpid ]['TimeStamp'] = int(time())

    datas = "02" + device_addr + ZIGATE_EP + device_ep + grpid
    self.ZigateComm.sendData( "0060", datas)

def add_group_member_ship_response(self, MsgData):
    """
    Response after a addGroupMemberShip

    Status:
    0x00:  Ok
    0x8a:  The device does not have storage space to support the requested operation.
    0x8b:  The device is not in the proper state to support the requested operation.
    """

    self.logging( 'Debug', "addGroupMembeShipResponse - MsgData: %s (%s)" %(MsgData, len(MsgData)))
    # search for the Group/dev
    if len(MsgData) != 14 and len(MsgData) != 18:
        Domoticz.Error("addGroupMembeShipResponse - uncomplete message %s" %MsgData)
        return

    if len(MsgData) == 14:  # Firmware < 030f
        MsgSrcAddr = None
        MsgSequenceNumber = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterID = MsgData[4:8]
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]
        self.logging( 'Debug', "addGroupMembeShipResponse < 3.0f- [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

    elif len(MsgData) == 18:    # Firmware >= 030f
        MsgSequenceNumber = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterID = MsgData[4:8]
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]
        MsgSrcAddr = MsgData[14:18]
        self.logging( 'Debug', "addGroupMembeShipResponse - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("Requesting to add group %s membership on non existing device %s" %(MsgGroupID, MsgSrcAddr))
        return

    if 'GroupMemberShip' not in self.ListOfDevices[ device_addr ]:
        return
    if grpid not in self.ListOfDevices[ device_addr ]['GroupMemberShip']:
        return
    if MsgEP not in self.ListOfDevices[ device_addr ]['GroupMemberShip']:
        return

    if self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ]['Status'] != 'addGroupMembeShip':
        return

    if MsgStatus == '00':
        # Success
        self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ]['Status'] = 'OK'

def check_group_member_ship( self, device_addr, device_ep, goup_addr ):
    """
    Check group Membership
    """

    self.logging( 'Debug', "checkGroupMemberShip - addr: %s ep: %s group: %s" %(device_addr, device_ep, goup_addr))  
    datas = "02" + device_addr + ZIGATE_EP + device_ep + goup_addr
    self.ZigateComm.sendData( "0061", datas)

def check_group_member_ship_response( self, MsgData):
    ' Decode 0x8061'

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSrcAddr = MsgData[14:18]

    self.logging( 'Debug', "checkGroupMemberShipResponse - SEQ: %s, Source: %s EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
            %( MsgSequenceNumber, MsgSrcAddr, MsgEP, MsgClusterID, MsgGroupID, MsgDataStatus))

def look_for_group_member_ship(self, device_addr, device_ep, group_list = None):
    """
    Request to a device what are its group membership
    """

    self.logging( 'Debug', "lookForGroupMemberShip - %s/%s from %s" %(device_addr, device_ep, group_list))
    datas = "02" + device_addr + ZIGATE_EP + device_ep
    self.ZigateComm.sendData( "0062", datas)

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
    MsgSourceAddress = MsgData[lenMsgData-4:lenMsgData]

    self.logging( 'Debug', "lookForGroupMemberShipResponse - SEQ: %s, EP: %s, ClusterID: %s, sAddr: %s, Capacity: %s, Count: %s"
            %(MsgSequenceNumber, MsgEP, MsgClusterID, MsgSourceAddress, MsgCapacity, MsgGroupCount))

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("lookForGroupMemberShipResponse %s membership on non existing device %s" %( MsgSrcAddr))
        return

    if 'GroupMemberShip' not in self.ListOfDevices[ device_addr ]:
        self.ListOfDevices[ device_addr ]['GroupMemberShip'] = {}

    if MsgEP not in self.ListOfDevices[ device_addr ]['GroupMemberShip']:
        self.ListOfDevices[ device_addr ]['GroupMemberShip'][ MsgEP ] = {}

    for idx in range(int(MsgGroupCount, 16)):
        # Let scan eachgroup and update Device data structure
        grpid = MsgData[12+(idx*4):12+(4+(idx*4))]

        if grpid not in self.ListOfDevices[ device_addr ]['GroupMemberShip'][ MsgEP ]:
            self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ] = {}

        self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ]['Status'] = 'OK'
        self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ]['TimeStamp'] = 0

def remove_group_member_ship(self,  device_addr, device_ep, goup_addr ):

    if device_addr not in self.ListOfDevices:
        Domoticz.Error("removeGroupMemberShip %s membership on non existing device %s" %( device_addr))
        return

    if 'GroupMemberShip' not in self.ListOfDevices[ device_addr ]:
        return

    if MsgEP not in self.ListOfDevices[ device_addr ]['GroupMemberShip']:
        return

    self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ]['Status'] = 'removeGroupMemberShip'
    self.ListOfDevices[ device_addr ]['GroupMemberShip'][MsgEP][ grpid ]['TimeStamp'] = int(time())

    self.logging( 'Debug', "removeGroupMemberShip - %s/%s on %s" %(device_addr, device_ep, goup_addr))

    datas = "02" + device_addr + ZIGATE_EP + device_ep + goup_addr
    self.ZigateComm.sendData( "0063", datas)

def remove_group_member_ship_response( self, MsgData):
    ' Decode 0x8063'

    if len(MsgData) != 14 and len(MsgData) != 18:
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

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("removeGroupMemberShipResponse %s membership on non existing device %s" %( device_addr))
        return

    if 'GroupMemberShip' not in self.ListOfDevices[ MsgSrcAddr ]:
        return

    if MsgEP not in self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']:
        return

    if MsgStatus == '00':
        del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ grpid ]
        if len(self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ grpid ]) == 0:
            del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP][ grpid ]

        if len(self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP]) == 0:
            del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip'][MsgEP]

        if len(self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']) == 0:
            del self.ListOfDevices[ MsgSrcAddr ]['GroupMemberShip']

    self.logging( 'Debug', "removeGroupMemberShipResponse - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s"
            %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgStatus)

# Operating commands on groups
def send_group_member_ship_identify(self, device_addr, device_ep, goup_addr = "0000"):

    datas = "02" + device_addr + ZIGATE_EP + device_ep + goup_addr
    self.ZigateComm.sendData( "0065", datas)

def send_group_member_ship_identify_effect( self, nwkid, ep, effect = 'Okay' ):
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

    datas = "%02d" %ADDRESS_MODE['group'] + "%s"%(nwkid) + ZIGATE_EP + ep + "%02x"%(effect_command[effect])  + "%02x" %0
    self.ZigateComm.sendData( "00E0", datas)

def set_kelvin_color( self, mode, addr, EPin, EPout, t, transit = None):
    #Value is in mireds (not kelvin)
    #Correct values are from 153 (6500K) up to 588 (1700K)
    # t is 0 > 255

    transit = '0001' if transit is None else '%04x' % transit
    TempKelvin = int(((255 - int(t))*(6500-1700)/255)+1700)
    TempMired = 1000000 // TempKelvin
    zigate_cmd = "00C0"
    zigate_param = Hex_Format(4, TempMired) + transit
    datas = "%02d" %mode + addr + EPin + EPout + zigate_param

    self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
    self.ZigateComm.sendData( zigate_cmd, datas)

def set_rgb_color( self, mode, addr, EPin, EPout, r, g, b, transit = None):

    transit = '0001' if transit is None else '%04x' % transit
    x, y = rgb_to_xy((int(r), int(g), int(b)))
    #Convert 0 > 1 to 0 > FFFF
    x = int(x*65536)
    y = int(y*65536)
    strxy = Hex_Format(4, x) + Hex_Format(4, y)
    zigate_cmd = "00B7"
    zigate_param = strxy + transit
    datas = "%02d" %mode + addr + ZIGATE_EP + EPout + zigate_param

    self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
    self.ZigateComm.sendData( zigate_cmd, datas)