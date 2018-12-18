#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import random
import pickle
import json

import os.path
import z_tools
import z_consts

GROUPS_CONFIG_FILENAME = "ZigateGroupsConfig"

class GroupsManagement(object):

    def __init__( self, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):
        Domoticz.Debug("GroupsManagement __init__")
        self.HB = 0
        self.StartupPhase = 'init'
        self.ListOfGroups = {}      # Data structutre to store all groups
        self.toBeImported = {}
        self.stillWIP = True
        self.getGMS_count = 0

        self.SQN = 0
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.groupListFileName = HomeDirectory + "/GroupsList-%02d" %hardwareID + ".pck"
        self.IEEE2NWK = IEEE2NWK
        self.homeDirectory = HomeDirectory
        self.ZigateComm = ZigateComm
        self.groupsConfigFilename = HomeDirectory + GROUPS_CONFIG_FILENAME + "-%02d" %hardwareID + ".txt"

        self._loadListOfGroups()
        self.load_ZigateGroupConfiguration()

        return

    def storeListOfGroups(self):
        ' Serialize with Pickle'
        Domoticz.Debug("storeListOfGroups - Saving %s" %self.ListOfGroups)
        with open( self.groupListFileName, 'wb') as handle:
            pickle.dump( self.ListOfGroups, handle)
        return

    def _loadListOfGroups( self ):
        ' Desrialize with Pickle'
        if not os.path.isfile( self.groupListFileName ) :
            Domoticz.Debug("_loadListOfGroups - File doesn't exist. no quick start")
            return
        with open(  self.groupListFileName, 'rb') as handle:
            self.ListOfGroups = pickle.loads( handle.read() )
        Domoticz.Debug("loadListOfGroups - ListOfGroups loaded: %s" %self.ListOfGroups)

        return 

    def _newGroupAddr( self ):
        ' Provide a random non existing Groupe Address '
        while True:
            addr = "04.x" % random.randrange(int("ffee",16))
            if addr not in self.ListOfGroup:
                return addr
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
        if PacketType == '0062' and Status != '00':
            self.getGMS_count  -= 1

        return

    def addGroupResponse(self, MsgData):
        ' decoding 0x8060 '
        # ZNC_BUF_U8_UPD   ( &au8LinkTxBuffer [u16Length],pCustom->uMessage.psAddGroupResponsePayload->eStatus,       u16Length );
        # ZNC_BUF_U16_UPD  ( &au8LinkTxBuffer [u16Length],pCustom->uMessage.psAddGroupResponsePayload->u16GroupId,    u16Length );

        # 0180600008a98d0100048a00014203
        # Start: 01
        # Command: 8060
        # Leght: 0008
        # Checksum: a9
        # SQN: 8d
        # EP:        01
        # ClusterID        0004
        # Status:        8a
        # GroupID        0001
        # RSSI: 42
        # End: 03

        Domoticz.Debug("addGroupResponse - MsgData: %s (%s)" %(MsgData,len(MsgData)))

        # search for the Group/dev
        if len(MsgData) != 14:
            Domoticz.Debug("addGroupResponse - uncomplete message %s" %MsgData)

        MsgSequenceNumber=MsgData[0:2]
        MsgEP=MsgData[2:4]
        MsgClusterID=MsgData[4:8]  
        MsgStatus = MsgData[8:10]
        MsgGroupID = MsgData[10:14]

        Domoticz.Log("addGroupResponse - [%s] GroupID: %s Status: %s " %(MsgSequenceNumber, MsgGroupID, MsgStatus ))

        if MsgStatus in ( '00', '8a'):
            # We need to find which Device was requested to be add to this group
            if MsgGroupID not in self.ListOfGroups:
                Domoticz.Log("addGroupResponse - unknown GroupID: %s " %MsgGroupID)
                return
            idx = -1
            for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[MsgGroupID]['Devices']:
                idx += 1
                if dev_status == 'Wip':
                    self.ListOfGroups[MsgGroupID]['Devices'][idx][2] = 'Ok' 
                    break
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

        self.getGMS_count  -= 1

        idx =  0
        while idx < int(MsgGroupCount,16):
            groupID = MsgData[16+(idx*4):16+(4+(idx*4))]
            Domoticz.Log("        - GroupID: %s" %groupID)
            if groupID not in self.ListOfGroups:
                #Create the Group
                self.ListOfGroups[groupID] ={}
                self.ListOfGroups[groupID]['Grp Status'] = 'Discover'
                self.ListOfGroups[groupID]['Name'] = ''
                self.ListOfGroups[groupID]['Devices'] = []
                self.ListOfGroups[groupID]['Devices'].append( [ MsgSourceAddress, MsgEP, 'Ok' ] ) 
            else:
                if 'Devices' in self.ListOfGroups[groupID]:
                    for iterDev in self.ListOfGroups[groupID]['Devices']:
                        if MsgSourceAddress == iterDev[0] and MsgEP == iterDev[1]:
                            # Already in the list
                            Domoticz.Debug("getGroupMembershipResponse - %s alreday known in Grooup: %s" %( MsgSourceAddress, groupID))
                            break
                    else:
                        Domoticz.Debug("getGroupMembershipResponse - Didn't find this entry, let's add it. %s/%s " %(MsgSourceAddress, MsgEP))
                        self.ListOfGroups[groupID]['Grp Status'] = 'Discover'
                        self.ListOfGroups[groupID]['Devices'].append( [MsgSourceAddress, MsgEP, 'Ok'] )
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
        MsgSequenceNumber=MsgData[0:2]
        MsgEP=MsgData[2:4]
        MsgClusterID=MsgData[4:8]
        MsgStatus=MsgData[8:10]
        MsgGroupID=MsgData[10:14]

        Domoticz.Log("Decode8063 - SEQ: %s, EP: %s, ClusterID: %s, GroupID: %s, Status: %s" 
                %( MsgSequenceNumber, MsgEP, MsgClusterID, MsgGroupID, MsgStatus))

        # MsgStatus: 00 - Ok, 8b - moste likely it was not in the group
        if MsgStatus in ( '00', '8b') :
            # We need to find which Device was requested to be add to this group
            if MsgGroupID not in self.ListOfGroups:
                Domoticz.Log("addGroupResponse - unknown GroupID: %s " %MsgGroupID)
                return
            idx = -1
            for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[MsgGroupID]['Devices']:
                idx += 1
                if dev_status == 'Wip':
                    self.ListOfGroups[MsgGroupID]['Devices'][idx][2] = 'Ok' 
                    break
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
                                    Domoticz.Debug("updateDomoGroupDevice - Device: %s OnOff: %s" %(dev_nwkid, (self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006'])))
                                    nValue = 1
                        if '0008' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                            Domoticz.Debug("updateDomoGroupDevice - Cluster 0008 value: %s" %self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'])
                            if self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'] != '' and self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'] != {}:
                                if level is None:
                                    level = int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'],16)
                                else:
                                    level = ( level +  int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'],16)) // 2
                                Domoticz.Debug("updateDomoGroupDevice - Device: %s level: %s" %(dev_nwkid, (self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008'])))
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

        # Remove the Domo Device
        for iterDev in self.ListOfGroups[grpid]['Devices']:
            idx = -1
            for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[grpid]['Devices']:
                idx += 1
                Domoticz.Log("processRemoveGroup - %s, %s, %s " %(dev_nwkid, dev_ep, dev_status))
                self.ListOfGroups[grpid]['Devices'][idx][2] = 'Remove' 
        self.ListOfGroups[grpid]['Grp Status'] = 'Remove'
        self.stillWIP = True
        self.StartupPhase = 'step2'
        return


    def load_ZigateGroupConfiguration(self):
        ' This is to import User Defined/Modified Groups of Devices for processing in the hearbeatGroupMgt'

        if not os.path.isfile( self.groupsConfigFilename ) :
            Domoticz.Debug("GroupMgt - Nothing to import")
            return

        self.toBeImported = {}
        myfile = open( self.groupsConfigFilename, 'r')
        Domoticz.Debug("load_ZigateGroupConfiguration. Reading the file")
        while True:
            tmpread = myfile.readline().replace('\n', '')
            Domoticz.Debug("line: %s" %tmpread )
            if not tmpread: 
                break
            group_id = group_name = None
            for token in tmpread.split(','):
                Domoticz.Debug("%s" %str(token))
                if group_id is None:
                    group_id = token
                    Domoticz.Debug("GroupID: %s" %token)
                    self.toBeImported[group_id]= {}
                    self.toBeImported[group_id]['Name'] = ''
                    self.toBeImported[group_id]['List of Devices'] = []
                    continue
                elif group_name is None:
                    group_name = token
                    Domoticz.Debug("GroupName: %s" %token)
                    self.toBeImported[group_id]['Name'] = group_name
                    continue
                else:
                    Domoticz.Debug("device:%s" %token)
                    if token.strip() != '':
                        self.toBeImported[group_id]['List of Devices'].append(token.strip())
            if group_id :
                Domoticz.Debug("load_ZigateGroupConfiguration - Group[%s]: %s List of Devices: %s to be processed" \
                    %( group_id, self.toBeImported[group_id]['Name'], str(self.toBeImported[group_id]['List of Devices'])))
        myfile.close()
    
    def _processGroupConfig( self ):
        """
        Process the loaded Group Configuration file.
            - If the groupID is new then Create the group and add the associated Device
            - If the GroupID is alone ( no device associated ), then remove the group and the device membership
            - If the GroupID exists, check if there is any additional devices or if some device have been removed. In that case update the membership
        """

        Domoticz.Debug("_processGroupConfig - ListOfGroups: %s" %str(self.ListOfGroups))
        for grpid in self.toBeImported:
            Domoticz.Debug("_processGroupConfig - process: %s - %s" %(grpid, str(self.toBeImported[grpid])))
            if grpid in self.ListOfGroups:
                if self.ListOfGroups[grpid]['Grp Status'] == 'Discover':
                    Domoticz.Debug("_processGroupConfig - Name: >%s<, newName: >%s<" %(self.ListOfGroups[grpid]['Name'], self.toBeImported[grpid]['Name']))
                    if self.ListOfGroups[grpid]['Name'] == '':
                        self.ListOfGroups[grpid]['Name'] = self.toBeImported[grpid]['Name']

                # If this is an existing one, lets see if there are any updates
                if len(self.toBeImported[grpid]['List of Devices']) == 0:
                    Domoticz.Debug("_processGroupConfig - remove group: %s" %grpid)
                    # We have to remove this Group and so remove all devices attached to the group
                    idx = -1
                    self.ListOfGroups[grpid]['Grp Status'] = 'Remove'
                    for devid, iterep, status  in self.ListOfGroups[grpid]['Devices']:
                        idx += 1
                        # Remove that one from group
                        self.ListOfGroups[grpid]['Devices'][idx][2] = 'Remove' 
                    continue # Go to next group

                # We have to update, add or remove some devices !
                self.ListOfGroups[grpid]['Grp Status'] = 'Update'
                if  self.ListOfGroups[grpid]['Name'] != self.ListOfGroups[grpid]['Name']:
                    Domoticz.Log("_processGroupConfig - Different group name: %s vs. %s, skip " %(self.ListOfGroups[grpid]['Name'], self.ListOfGroups[grpid]['Name']))
                    continue

                # Let's check what are the new devices for this group
                for iterDev in  self.toBeImported[grpid]['List of Devices']:
                    if iterDev not in self.IEEE2NWK:
                        # Unknown device
                        Domoticz.Log("_processGroupConfig - unknown device: %s, skip" %iterDev)
                        continue
                    idx = -1
                    for iterLoG in self.ListOfGroups[grpid]['Devices']:
                        idx += 1
                        Domoticz.Debug("_processGroupConfig - %s versus %s" %(iterDev, iterLoG))
                        if self.IEEE2NWK[iterDev] == iterLoG[0]:
                            Domoticz.Debug("_processGroupConfig - %s found in ListOFGroup[%s] " %(iterDev, grpid))
                            self.ListOfGroups[grpid]['Devices'][idx][2] = 'Ok'
                            break
                    else: # For loop went to the end , so we didn't find a matching iterDev
                        Domoticz.Log("_processGroupConfig - New device: %s to be added to the group %s " %(iterDev, grpid))
                        nwkidDev = self.IEEE2NWK[iterDev]
                        if 'Ep' in self.ListOfDevices[nwkidDev]:
                            for iterEp in self.ListOfDevices[nwkidDev]['Ep']:
                                if ( 'ClusterType' in self.ListOfDevices[nwkidDev] or 'ClusterType' in self.ListOfDevices[nwkidDev]['Ep'][iterEp]) and \
                                        '0004' in self.ListOfDevices[nwkidDev]['Ep'][iterEp]:
                                    self.ListOfGroups[grpid]['Devices'].append( [nwkidDev, iterEp, 'New'] )
                                    Domoticz.Debug("_processGroupConfig - found 'ClusterType' and '0004' for %s/%s in %s" \
                                        %(nwkidDev, iterEp, str(self.ListOfDevices[nwkidDev]['Ep'][iterEp])))
                                    break
                                else:
                                    Domoticz.Debug("_processGroupConfig - not found 'ClusterType' or '0004' for %s/%s in %s" \
                                        %(nwkidDev, iterEp, str(self.ListOfDevices[nwkidDev]['Ep'][iterEp])))
                    #end for else iterLog:
                # end for loop checking if we got new devices

                # Let's check if we don't have any Device to remove
                idx = -1
                for iternwkid,iterep, iterstatus in self.ListOfGroups[grpid]['Devices']:
                    idx += 1
                    for impDev in self.toBeImported[grpid]['List of Devices']:
                        if impDev not in self.IEEE2NWK:
                            Domoticz.Log("_processGroupConfig - unknown IEEE: %s" %(impDev))
                            continue
                        if self.IEEE2NWK[impDev] == iternwkid:
                            self.ListOfGroups[grpid]['Devices'][idx][2] = 'Ok'
                            break
                    else:
                        # NOt found in the device to Importe
                        # We need to remove that device
                        Domoticz.Log("_processGroupConfig - %s not found in ImportGroups.txt, so remove" %iternwkid)
                        self.ListOfGroups[grpid]['Devices'][idx][2] = 'Remove' 

                # end for iterDev
                Domoticz.Debug("_processGroupConfig - ListOfGroups: %s" %str(self.ListOfGroups))
            else:
                Domoticz.Debug("_processGroupConfig - New group to create %s" %grpid)
                # If this is an unknwon group, start the creation.
                if len(self.toBeImported[grpid]['List of Devices']) == 0:
                    # Nothing to do, Create a group but no device attached !
                    continue
                self.ListOfGroups[grpid] ={}
                self.ListOfGroups[grpid]['Grp Status'] = 'New'
                self.ListOfGroups[grpid]['Name'] = self.toBeImported[grpid]['Name']
                self.ListOfGroups[grpid]['Devices'] = []
                for iterDev in self.toBeImported[grpid]['List of Devices']:
                    Domoticz.Debug("_processGroupConfig - process: %s/%s" %(grpid, iterDev))
                    if iterDev in self.IEEE2NWK:
                        nwkidDev = self.IEEE2NWK[iterDev]
                        if 'Ep' in self.ListOfDevices[nwkidDev]:
                            for iterEp in self.ListOfDevices[nwkidDev]['Ep']:
                                if ( 'ClusterType' in self.ListOfDevices[nwkidDev] or 'ClusterType' in self.ListOfDevices[nwkidDev]['Ep'][iterEp]) and \
                                        '0004' in self.ListOfDevices[nwkidDev]['Ep'][iterEp]:
                                    self.ListOfGroups[grpid]['Devices'].append( [nwkidDev, iterEp, 'New'] )
                                    Domoticz.Debug("_processGroupConfig - found 'ClusterType'andr '0004' for %s/%s in %s" \
                                            %(nwkidDev, iterEp, str(self.ListOfDevices[nwkidDev]['Ep'][iterEp])))
                                    break
                                else:
                                    Domoticz.Debug("_processGroupConfig - not found 'ClusterType' or '0004' for %s/%s in %s" \
                                            %(nwkidDev, iterEp, str(self.ListOfDevices[nwkidDev]['Ep'][iterEp])))
                    else:
                        Domoticz.Log("hearbeatGroupMgt - unknow device to be imported >%s<" %iterDev)
                self.ListOfGroups[grpid]['Grp Status'] = 'New'
                Domoticz.Debug("hearbeatGroupMgt - Ready to processgroup %s " %self.ListOfGroups[grpid]['Name'])
                for iter in self.ListOfGroups[grpid]['Devices']:
                    Domoticz.Debug("                -  %s  " %iter)
                self.toBeImported[grpid]['List of Devices'] = []
            #end else:
        # end for grpid
        self.toBeImported = {}
        Domoticz.Debug("_processGroupConfig - ListOfGroups: %s" %str(self.ListOfGroups))
        self.StartupPhase = 'step2'

    def _processListOfGroups( self ):
        ''' 
        browse the ListOfGroups and trigger the needed actions.
        Only 1 action at a time, in order to receive the response of Creation and the go to the next one.
        '''

        Domoticz.Debug("_processListOfGroups: %s" %str(self.ListOfGroups))
        self.stillWIP = False
        toBeRemoved = []
        for iterGrp in self.ListOfGroups:
            Domoticz.Log("_processListOfGroups - Group: %s" %iterGrp)
            if self.ListOfGroups[iterGrp]['Grp Status'] in ('Ok'):
                Domoticz.Debug('_processListOfGroups - Nothing to do')
                continue

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Discover'):
                # Group retreived from the Zigate
                Domoticz.Debug("_processListOfGroups - Discover, Name: %s and Devices: %s " %(self.ListOfGroups[iterGrp]['Name'],self.ListOfGroups[iterGrp]['Devices']))
                # Do we have a name for this Group, if yes, let's create a Domo Widget
                self.stillWIP = True     # In order to force going to Wip_xxx
                self.ListOfGroups[iterGrp]['Grp Status'] = 'Update'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('New', 'Remove', 'Update'):
                Domoticz.Debug("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                self.stillWIP = True     # In order to force going to Wip_xxx
                idx = -1
                self.ListOfGroups[iterGrp]['Grp Status'] = 'Wip_' + self.ListOfGroups[iterGrp]['Grp Status']
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    idx += 1
                    Domoticz.Debug("_processListOfGroups - %s, %s, %s " %(dev_nwkid, dev_ep, dev_status))
                    if dev_status == 'Ok':
                        pass
                    elif dev_status == 'New':
                        self.stillWIP = True
                        dev_ieee = self.ListOfDevices[dev_nwkid]['IEEE']
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip' 
                        Domoticz.Debug("_processListOfGroups - _addGroup %s %s %s %s" %(dev_ieee, dev_nwkid, dev_ep, iterGrp))
                        self._addGroup( dev_ieee, dev_nwkid, dev_ep, iterGrp )
                        break   # Break from the inside Loop. We will process the next Group
                    elif dev_status == 'Remove':
                        self.stillWIP = True
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip' 
                        Domoticz.Debug("_processListOfGroups - _removeGroup %s %s %s" %( dev_nwkid, dev_ep, iterGrp))
                        self._removeGroup(dev_nwkid, dev_ep, iterGrp )
                        break   # Break from the inside Loop. We will process the next Group

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_New'):
                Domoticz.Debug("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                # Let's check that all devices have been created
                idx = -1
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    idx += 1
                    Domoticz.Debug("_processListOfGroups - %s, %s, %s " %(dev_nwkid, dev_ep, dev_status))
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        continue
                    elif dev_status == 'Ok':
                        continue
                    elif dev_status == 'New':
                        self.stillWIP = True
                        dev_ieee = self.ListOfDevices[dev_nwkid]['IEEE']
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip'
                        Domoticz.Debug("_processListOfGroups - _addGroup %s %s %s %s" %(dev_ieee, dev_nwkid, dev_ep, iterGrp))
                        self._addGroup( dev_ieee, dev_nwkid, dev_ep, iterGrp )
                        break   # Break from the inside Loop. We will process the next Group
                    elif dev_status == 'Remove':
                        self.stillWIP = True
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip'
                        Domoticz.Debug("_processListOfGroups - _removeGroup %s %s %s" %( dev_nwkid, dev_ep, iterGrp))
                        self._removeGroup(dev_nwkid, dev_ep, iterGrp )
                        break   # Break from the inside Loop. We will process the next Group

                else:
                    Domoticz.Debug("_processListOfGroups - All devices attached to the Zigate Group. Let's create the Widget")
                    if iterGrp != '':
                        if self.ListOfGroups[iterGrp]['Name'] == '':
                            self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                        self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)
                        self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_Remove'):
                Domoticz.Debug("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                # Let's check that all Devices have been removed from the Zigate Group
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break   # Break from the inside Loop. We will process the next Group
                else:
                    toBeRemoved.append( iterGrp )    # Remove the element from ListOfGroup and Remove the Domoticz Device
                    self._removeDomoGroupDevice(iterGrp )
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_Update'):
                Domoticz.Debug("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break   # Break from the inside Loop. We will process the next Group
                else:
                    Domoticz.Debug("_processListOfGroups - Set group %s to Ok" %iterGrp)
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'
                    for iterUnit in self.Devices:
                        if iterGrp == self.Devices[iterUnit].DeviceID:
                            Domoticz.Debug("_processListOfGroups - found %s in Domoticz." %iterGrp)
                            # Update the group name if required
                            self.ListOfGroups[iterGrp]['Name'] = self.Devices[iterUnit].Name
                            break   # Break from the inside Loop. We will process the next Group
                    else:
                        #DO not exist in Domoticz, let's create a widget
                        if self.ListOfGroups[iterGrp]['Name'] == '':
                            self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                        Domoticz.Debug("_processListOfGroups - create Domotciz Widget for %s " %self.ListOfGroups[iterGrp]['Name'])
                        self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)
            else:
                Domoticz.Log("_processListOfGroups - unknown status: %s for group: %s." \
                        %(self.ListOfGroups[iterGrp]['Grp Status'], iterGrp))

        for iter in toBeRemoved:
            del self.ListOfGroups[iter]

        Domoticz.Debug("_processListOfGroups - WIP: %s ListOfGroups: %s " %( self.stillWIP, str(self.ListOfGroups)))
        if not self.stillWIP:
            self.StartupPhase = 'step3'

        return 

    def _discoverZigateGroups( self ):

        self.getGMS_count = 0
        for iterDev in self.ListOfDevices:
            if 'PowerSource' in self.ListOfDevices[iterDev]:
                if self.ListOfDevices[iterDev]['PowerSource'] != 'Main':
                    continue
            if 'Ep' in self.ListOfDevices[iterDev]:
                for iterEp in self.ListOfDevices[iterDev]['Ep']:
                    if 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                        '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp]:
                        Domoticz.Debug("_discoverZigateGroups - req membership for %s/%s " %(iterDev, iterEp))
                        self._getGroupMembership(iterDev, iterEp)   # We request MemberShip List
                                                                    # We will manage it in the getGroupMembershipResponse
                        self.getGMS_count += 1                      # However sometime we don't tget response at all.
        self.StartupPhase = 'step1'

    def hearbeatGroupMgt( self ):
        ' hearbeat to process Group Management actions '

        self.HB += 1

        if self.StartupPhase == 'ready':
            if not self.stillWIP:
                for group_nwkid in self.ListOfGroups:
                    self.updateDomoGroupDevice( group_nwkid)

        elif self.StartupPhase == 'init':
            Domoticz.Log("hearbeatGroupMgt - STEP1 %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            Domoticz.Log("hearbeatGroupMgt - ListOfGrousp: %s " %(str(self.ListOfGroups)))
            self._discoverZigateGroups( )

        elif self.StartupPhase == 'step1' and ( self.getGMS_count == 0 or self.HB > 6 ):
            Domoticz.Log("hearbeatGroupMgt - STEP3 %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            Domoticz.Log("hearbeatGroupMgt - ListOfGrousp: %s " %(str(self.ListOfGroups)))
            self._processGroupConfig()

        elif self.StartupPhase == 'step2':
            Domoticz.Log("hearbeatGroupMgt - STEP4 %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            Domoticz.Log("hearbeatGroupMgt - ListOfGrousp: %s " %(str(self.ListOfGroups)))
            self._processListOfGroups()

        elif self.StartupPhase == 'step3':
            Domoticz.Log("hearbeatGroupMgt - READY %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            Domoticz.Log("hearbeatGroupMgt - ListOfGrousp: %s " %(str(self.ListOfGroups)))
            self.StartupPhase = 'ready'


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
            datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
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
            datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
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
            datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
            Domoticz.Log("Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

        elif Command == "Set Color" :
            Hue_List = json.loads(Color_)
            #First manage level
            OnOff = '01' # 00 = off, 01 = on
            value=z_tools.Hex_Format(2,round(1+Level*254/100)) #To prevent off state
            zigate_cmd = "0081"
            zigate_param = OnOff + value + "0000"
            datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
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
                zigate_param = z_tools.Hex_Format(4,TempMired) + "0000"
                datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

            #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
            elif Hue_List['m'] == 3:
                x, y = z_tools.rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                #Convert 0>1 to 0>FFFF
                x = int(x*65536)
                y = int(y*65536)
                strxy = z_tools.Hex_Format(4,x) + z_tools.Hex_Format(4,y)
                zigate_cmd = "00B7"
                zigate_param = strxy + "0000"
                datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

            #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
            elif Hue_List['m'] == 4:
                ww = int(Hue_List['ww'])
                cw = int(Hue_List['cw'])
                x, y = z_tools.rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                #TODO, Pas trouve de device avec ca encore ...
                Domoticz.Debug("Not implemented device color 2")

            #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
            elif Hue_List['m'] == 9998:
                h,l,s = z_tools.rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
                saturation = s * 100   #0 > 100
                hue = h *360           #0 > 360
                hue = int(hue*254//360)
                saturation = int(saturation*254//100)
                value = int(l * 254//100)
                OnOff = '01'
                zigate_cmd = "00B6"
                zigate_param = z_tools.Hex_Format(2,hue) + z_tools.Hex_Format(2,saturation) + "0000"
                datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                zigate_cmd = "0081"
                zigate_param = OnOff + z_tools.Hex_Format(2,value) + "0010"
                datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
                Domoticz.Log("Command: %s - data: %s" %(zigate_cmd,datas))
                self.ZigateComm.sendData( zigate_cmd, datas)

                #Update Device
                nValue = 1
                sValue = str(value)
                self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_) 
                return
