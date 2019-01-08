#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import pickle
import json
import os.path

from time import time

from Modules.z_tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.z_consts import ADDRESS_MODE

GROUPS_CONFIG_FILENAME = "ZigateGroupsConfig"

class GroupsManagement(object):

    def __init__( self, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):
        Domoticz.Debug("GroupsManagement __init__")
        self.HB = 0
        self.StartupPhase = 'init'
        self.ListOfGroups = {}      # Data structutre to store all groups
        self.toBeImported = {}
        self.stillWIP = True

        self.SQN = 0
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.groupListFileName = HomeDirectory + "/GroupsList-%02d" %hardwareID + ".pck"
        self.IEEE2NWK = IEEE2NWK
        self.homeDirectory = HomeDirectory
        self.ZigateComm = ZigateComm
        self.groupsConfigFilename = HomeDirectory + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".txt"

        return

    # Zigate group related commands
    def _addGroup( self, device_ieee, device_addr, device_ep, grpid):
        # Address Mode: 0x02
        # Target short addre : uint1- ( device NWKID )
        # Source EndPoint : 0x01
        # Target EndPoint : uint8
        # Group address : uint16 ( 0x0000 for a new one )

        if grpid not in self.ListOfGroups:
            return

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

        Domoticz.Debug("statusGroupRequest - Status: %s for Command: %s" %(Status, PacketType))

        return

    def addGroupResponse(self, MsgData):
        ' decoding 0x8060 '

        Domoticz.Log("addGroupResponse - MsgData: %s (%s)" %(MsgData,len(MsgData)))
        # search for the Group/dev
        if len(MsgData) == 14:  # Firmware < 030f
            MsgSrcAddr = None
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            Domoticz.Log("addGroupResponse - [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))
        elif len(MsgData) == 18:    # Firmware >= 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgSrcAddr = MsgData[8:12]
            MsgStatus = MsgData[12:14]
            MsgGroupID = MsgData[14:18]
            Domoticz.Log("addGroupResponse - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
            self.ListOfDevices[MsgSrcAddr]['GroupMgt'][MsgEP]['Phase'] = 'reqMembership'
            self._getGroupMembership( MsgSrcAddr, MsgEP, MsgGroupID)
        else:
            Domoticz.Log("addGroupResponse - uncomplete message %s" %MsgData)

        if MsgStatus in ( '00', '8b') :
            pass
        else:
            Domoticz.Log("addGroupResponse - GroupID: %s unexpected Status: %s" %(MsgGroupID, MsgStatus))

        return

    def _viewGroup( self, device_addr, device_ep, goup_addr ):

        Domoticz.Debug("_viewGroup - addr: %s ep: %s group: %s" %(device_addr, device_ep, goup_addr))
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

        Domoticz.Log("Decode8061 - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgDataStatus))
        return


    def _getGroupMembership(self, device_addr, device_ep, group_list=None):

        Domoticz.Debug("_getGroupMembership - %s/%s " %(device_addr, device_ep))
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
            datas += "02.x" %(lenGrpLst) + group_list_

        self.ZigateComm.sendData( "0062", datas)
        return

    def getGroupMembershipResponse( self, MsgData):
        ' Decode 0x8062 '

        MsgSequenceNumber=MsgData[0:2]
        MsgEP=MsgData[2:4]
        MsgClusterID=MsgData[4:8]
        MsgSourceAddress=MsgData[8:12]
        MsgCapacity=MsgData[12:14]
        MsgGroupCount=MsgData[14:16]
        MsgListOfGroup=MsgData[16:len(MsgData)]

        Domoticz.Debug("Decode8062 - SEQ: %s, EP: %s, ClusterID: %s, sAddr: %s, Capacity: %s, Count: %s"
                %(MsgSequenceNumber, MsgEP, MsgClusterID, MsgSourceAddress, MsgCapacity, MsgGroupCount))

        if MsgSourceAddress not in self.ListOfDevices:
            Domoticz.Log('getGroupMembershipResponse - receiving a group memebership for a non exsiting device')
            Domoticz.Log('getGroupMembershipResponse - %s %s %s' %(MsgSourceAddress, MsgGroupCount, MsgListOfGroup))

        if 'GroupMgt' not in  self.ListOfDevices[MsgSourceAddress]:
             self.ListOfDevices[MsgSourceAddress]['GroupMgt'] = {}
        if MsgEP not in  self.ListOfDevices[MsgSourceAddress]['GroupMgt']:
             self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP] = {}
        if 'Membership' not in  self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]:
             self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Membership'] = {}
        if 'Phase' in self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]:
            if self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Phase'] != 'reqMembership':
                Domoticz.Log("getGroupMembershipResponse - not in the expected Phase : %s " 
                    %self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Phase'])

        self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Phase'] = 'okMembership'
        idx =  0
        while idx < int(MsgGroupCount,16):
            groupID = MsgData[16+(idx*4):16+(4+(idx*4))]
            if groupID not in self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Membership']:
                self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Membership'][groupID] = {}
            if groupID not in self.ListOfGroups:
                self.ListOfGroups[groupID] = {}
                self.ListOfGroups[groupID]['Name'] = ''
                self.ListOfGroups[groupID]['Devices'] = []
                self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP) )
            else:
                self.ListOfGroups[groupID]['Devices'].append( (MsgSourceAddress, MsgEP) )

            Domoticz.Log("getGroupMembershipResponse - Group Membership : %s for (%s,%s)"
                    %(groupID, MsgSourceAddress, MsgEP))
                
            idx += 1
        return

    def _removeGroup(self,  device_addr, device_ep, goup_addr ):

        Domoticz.Log("_removeGroup - %s/%s on %s" %(device_addr, device_ep, goup_addr))
        datas = "02" + device_addr + "01" + device_ep + goup_addr
        self.ZigateComm.sendData( "0063", datas)
        return

    def removeGroupResponse( self, MsgData):
        ' Decode 0x8063'

        if len(MsgData) != 14:
            return
        if len(MsgData) == 14:  # Firmware < 030f
            MsgSrcAddr = None
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgStatus = MsgData[8:10]
            MsgGroupID = MsgData[10:14]
            Domoticz.Log("removeGroupResponse - [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))
        elif len(MsgData) == 18:    # Firmware >= 030f
            MsgSequenceNumber=MsgData[0:2]
            MsgEP=MsgData[2:4]
            MsgClusterID=MsgData[4:8]  
            MsgSrcAddr = MsgData[8:12]
            MsgStatus = MsgData[12:14]
            MsgGroupID = MsgData[14:18]
            Domoticz.Log("removeGroupResponse - [%s] GroupID: %s adding: %s with Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgSrcAddr, MsgStatus ))
        else:
            Domoticz.Log("removeGroupResponse - uncomplete message %s" %MsgData)

        Domoticz.Log("Decode8063 - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgStatus))

        if MsgStatus in ( '00' ) :
            if 'GroupMgt' in self.ListOfDevices[MsgSourceAddress]:
                if MsgEP in  self.ListOfDevices[MsgSourceAddress]['GroupMgt']:
                    if 'Membership' in self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]:
                        if groupID in self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Membership']:
                            del  self.ListOfDevices[MsgSourceAddress]['GroupMgt'][MsgEP]['Membership'][groupID]
        else:
            Domoticz.Log("removeGroupResponse - GroupID: %s unexpected Status: %s" %(MsgGroupID, MsgStatus))
        # Sanity check. 
        self._getGroupMembership( MsgSrcAddr, MsgEP, MsgGroupID)

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
        Domoticz.Log("_createDomoGroupDevice - Unit: %s" %unit)
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
            Domoticz.Log("updateDomoGroupDevice - unknown group: %s" %group_nwkid)
            return
        if 'Devices' not in self.ListOfGroups[group_nwkid]:
            Domoticz.Log("updateDomoGroupDevice - no Devices for that group: %s" %self.ListOfGroups[group_nwkid])
            return

        unit = 0
        for unit in self.Devices:
            if self.Devices[unit].DeviceID == group_nwkid:
                break
        else:
            Domoticz.Log("updateDomoGroupDevice - no Devices found in Domoticz: %s" %group_nwkid)
            return

        # If one device is on, then the group is on. If all devices are off, then the group is off
        nValue = 0
        level = None
        for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[group_nwkid]['Devices']:
            Domoticz.Debug("updateDomoGroupDevice - %s, %s, %s " %(dev_nwkid, dev_ep, dev_status))
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
        else:
            sValue = "Off"
        Domoticz.Debug("UpdateDeviceGroup Values %s : %s '(%s)'" %(nValue, sValue, self.Devices[unit].Name))
        if nValue != self.Devices[unit].nValue or sValue != self.Devices[unit].sValue:
            Domoticz.Log("UpdateDeviceGroup Values %s : %s '(%s)'" %(nValue, sValue, self.Devices[unit].Name))
            self.Devices[unit].Update( nValue, sValue)


    def _removeDomoGroupDevice(self, group_nwkid):
        ' User has remove dthe Domoticz Device corresponding to this group'

        if group_nwkid not in self.ListOfGroups:
            Domoticz.Log("updateDomoGroupDevice - unknown group: %s" %group_nwkid)
            return
        if 'Devices' not in self.ListOfGroups[group_nwkid]:
            Domoticz.Log("updateDomoGroupDevice - no Devices for that group: %s" %self.ListOfGroups[group_nwkid])
            return

        unit = 0
        for unit in self.Devices:
            if self.Devices[unit].DeviceID == group_nwkid:
                break
        else:
            Domoticz.Log("updateDomoGroupDevice - no Devices found in Domoticz: %s" %group_nwkid)
            return
        Domoticz.Log("domGroupDeviceRemoved - removing Domoticz Widget")
        self.Devices[unit].Delete()
        

    # Group Management methods
    def processRemoveGroup( self, unit, grpid):

        # Remove all devices from the corresponding group
        if grpid not in self.ListOfGroups:
            return

        for iterDev in self.ListOfDevices:
            if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                continue
            for iterEP in self.ListOfDevices[iterDev]['Ep']:
                if iterEP not in self.ListOfDevices[iterDev]['GroupMgt']:
                    continue
                if 'Membership' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEP]:
                    continue
                if grpid in self.ListOfDevices[iterDev]['GroupMgt'][iterEP]['Membership']:
                    Domoticz.Log("processRemoveGroup - remove %s %s %s" 
                            %(iterDev, iterEP, grpid))
                    self._removeGroup(iterDev, iterEP, grpid )
        return




    def processCommand( self, unit, nwkid, Command, Level, Color_ ) : 

        Domoticz.Log("processCommand - unit: %s, nwkid: %s, cmd: %s, level: %s, color: %s" %(unit, nwkid, Command, Level, Color_))
        EPin = EPout = '01'

        if Command == 'Off' :
            zigate_cmd = "0092"
            zigate_param = '00'
            nValue = 0
            sValue = 'Off'
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            #datas = "01" + nwkid + EPin + EPout + zigate_param
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            Domoticz.Log("Command: %s" %datas)
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
            Domoticz.Log("Command: %s" %datas)
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
            Domoticz.Log("Command: %s" %datas)
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
            Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
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
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
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
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
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
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                zigate_cmd = "0081"
                zigate_param = OnOff + Hex_Format(2,value) + "0010"
                datas = "%02d" %ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
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

        self.HB += 1

        if self.StartupPhase == 'ready':
            if not self.stillWIP:
                for group_nwkid in self.ListOfGroups:
                    self.updateDomoGroupDevice( group_nwkid)

        elif self.StartupPhase == 'init' or  self.StartupPhase == 'discovery':
            Domoticz.Log("Entering in discovery mode")
            self.StartupPhase = 'discovery'
            # We will send a Request for Group memebership to each active device
            # In case a device doesn't belo,ng to any group, no response is provided.

            _workcompleted = True
            for iterDev in self.ListOfDevices:
                if 'PowerSource' in self.ListOfDevices[iterDev]:
                    if self.ListOfDevices[iterDev]['PowerSource'] != 'Main':
                        continue
                if 'Ep' in self.ListOfDevices[iterDev]:
                    for iterEp in self.ListOfDevices[iterDev]['Ep']:
                        if iterEp == 'ClusterType': continue
                        if  len(self.ZigateComm._normalQueue) > 2:
                            _workcompleted = False
                            break # will continue in the next cycle
                        if 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                            '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp]:
                            Domoticz.Debug("_discoverZigateGroups - req membership for %s/%s " %(iterDev, iterEp))
                            if 'GroupMgt' not in  self.ListOfDevices[iterDev]:
                                self.ListOfDevices[iterDev]['GroupMgt'] = {}
                            if iterEp not in  self.ListOfDevices[iterDev]['GroupMgt']:
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp] = {}
                            if 'Phase' not in  self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase'] = ''
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase'] not in ('reqMembership' , 'okMembership' ):
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase'] = 'reqMembership'
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase-Stamp'] = time()
                                Domoticz.Log(" - request group membership for %s/%s" %(iterDev, iterEp))
                                self._getGroupMembership(iterDev, iterEp)   # We request MemberShip List
            else:
                if _workcompleted:
                    Domoticz.Log("hearbeatGroupMgt - Finish Discovery Phase" )
                    self.StartupPhase = 'finish discovery'

        elif self.StartupPhase == 'finish discovery':
            # Check for completness or Timeout
            Domoticz.Log("Finishing discovery mode")
            now = time()
            _completedEPs = True
            for iterDev in self.ListOfDevices:
                if 'GroupMgt' in self.ListOfDevices[iterDev]:
                    if 'Ep' in self.ListOfDevices[iterDev]:
                        for iterEp in self.ListOfDevices[iterDev]['Ep']:
                            if iterEp not in self.ListOfDevices[iterDev]['GroupMgt']:
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase'] == 'okMembership':
                                continue
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase-Stamp'] + 10 > now:
                                _completedEPs = False
                                break # Need to wait a couple of sec.
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['Phase'] = 'TimeOut'
                            Domoticz.Log("No response receive for %s/%s - assuming no group membership" %(iterDev,iterEp))
            else:
                if _completedEPs:
                    Domoticz.Log("hearbeatGroupMgt - End of Discovery Phase" )
                    self.StartupPhase = 'check group list'

        elif self.StartupPhase == 'check group list':
            # GroupList is build in the germembership response
            Domoticz.Log("Checking Group list")
            for iterGrp in self.ListOfGroups:
                for x in self.Devices:
                    if self.Devices[x].DeviceID == iterGrp:
                        self.ListOfGroups[iterGrp]['Name'] = self.Devices[x].Name
                        break
                else:
                    # Unknown group in Domoticz. Create it
                    if self.ListOfGroups[iterGrp]['Name'] == '':
                        self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                    Domoticz.Debug("_processListOfGroups - create Domotciz Widget for %s " %self.ListOfGroups[iterGrp]['Name'])
                    self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)

                Domoticz.Log("Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
                Domoticz.Log("Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
                for iterDev, iterEp in self.ListOfGroups[iterGrp]['Devices']:
                    Domoticz.Log("  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))

            Domoticz.Log("Ready for working")
            self.StartupPhase = 'ready'


            # Check that all reqMembership are now received

        return
