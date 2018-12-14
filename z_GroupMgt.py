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

import z_consts

GROUPS_CONFIG_FILENAME = "ZigateGroupsConfig.txt"

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
        self.groupsConfigFilename = HomeDirectory + GROUPS_CONFIG_FILENAME

        self._loadListOfGroups()
        self.load_groupsConfig()

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

        if MsgStatus == "00":
            # We need to find which Device was requested to be add to this group
            if MsgGroupID not in self.ListOfGroups:
                Domoticz.Log("addGroupResponse - unknown GroupID: %s " %MsgGroupID)
                return
            idx = 0
            for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[MsgGroupID]['Devices']:
                if dev_status == 'Wip':
                    self.ListOfGroups[MsgGroupID]['Devices'][idx][2] = 'Ok' 
                    break
                idx += 1
        return

    def _updateGroup(  self, device_ieee, device_addr, device_ep, goup_addr ):
        # Called when a Device came with a new Network@

        # We have to remove the all NwkId and add the New Nwkid to the Group

        return

    def _viewGroup( self, device_addr, device_ep, goup_addr ):

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

        idx = 0
        while idx < int(MsgGroupCount,16):
            groupID = MsgData[16+(idx*4):16+(4+(idx*4))]
            Domoticz.Debug("        - GroupID: %s" %groupID)
            if groupID not in self.ListOfGroups:
                self.ListOfGroups[groupID] ={}
                self.ListOfGroups[groupID]['Grp Status'] = 'Discover'
                self.ListOfGroups[groupID]['Name'] = ''
                self.ListOfGroups[groupID]['Devices'] = []
                self.ListOfGroups[groupID]['Devices'].append( [ MsgSourceAddress, MsgEP, 'Ok' ] ) 
            else:
                if 'Devices' in self.ListOfGroups[groupID]:
                    for iterDev in self.ListOfGroups[groupID]['Devices']:
                        if MsgSourceAddress == iterDev[0] and MsgEP == iterDev[1]:
                            break
                    else:
                        Domoticz.Debug("getGroupMembershipResponse - Didn't find this entry, let's add it. %s/%s " %(MsgSourceAddress, MsgEP))
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

        if MsgStatus == "00":
            # We need to find which Device was requested to be add to this group
            if MsgGroupID not in self.ListOfGroups:
                Domoticz.Log("addGroupResponse - unknown GroupID: %s " %MsgGroupID)
                return
            idx = 0
            for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[MsgGroupID]['Devices']:
                if dev_status == 'Wip':
                    self.ListOfGroups[MsgGroupID]['Devices'][idx][2] = 'Ok' 
                    break
                idx += 1
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

        unit = self.FreeUnit( self.Devices )
        Domoticz.Log("_createDomoGroupDevice - Unit: %s" %unit)
        myDev = Domoticz.Device(DeviceID=str(group_nwkid), Name=str(groupname), Unit=unit, Type=241, Subtype=7, Switchtype=7)
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1 :
            Domoticz.Log("CreateDomoGroupDevice - failed to create Group device.")

    def _removeDomoGroupDevice(self, group_nwkid):

        return

    def updateDomoGroupDevice( self, group_nwkid):
        ' Update the Group status On/Off , based on the attached devices'

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


    def domGroupDeviceRemoved(self, groupname, group_nwkid):
        ' User has remove dthe Domoticz Device corresponding to this group'

        # Remove all device attached to that group
        

    # Group Management methods
    def add_device_to_group(self, device_nwkid, group):

        # Find the Ep or the List of EP active for this Nwkid. Have a look
        # in ListOfDevices to see which Ep got a Domoticz Device
        if device_nwkid not in self.ListOfDevices:
            return

        return

    def remove_device_from_group(self):
        pass

    def remove_device_from_all_group(self):
        pass

    def processRemoveGroup( self, unit, grpid):

        # Remove all devices from the corresponding group
        if grpid not in self.ListOfGroups:
            return

        # Remove the Domo Device
        idx = 0
        for iterDev in self.ListOfGroups[grpid]['Devices']:
            for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[grpid]['Devices']:
                Domoticz.Log("_processListOfGroups - %s, %s, %s " %(dev_nwkid, dev_ep, dev_status))
                self.ListOfGroups[grpid]['Devices'][idx][2] = 'Remove' 
        self.ListOfGroups[grpid]['Grp Status'] = 'Remove'
        self.stillWIP = True
        return


    def load_groupsConfig(self):
        ' This is to import User Defined/Modified Groups of Devices for processing in the hearbeatGroupMgt'

        if not os.path.isfile( self.groupsConfigFilename ) :
            Domoticz.Debug("GroupMgt - Nothing to import")
            return

        self.toBeImported = {}
        myfile = open( self.groupsConfigFilename, 'r')
        Domoticz.Debug("load_groupsConfig. Reading the file")
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
                Domoticz.Log("load_groupsConfig - Group[%s]: %s List of Devices: %s to be processed" \
                    %( group_id, self.toBeImported[group_id]['Name'], str(self.toBeImported[group_id]['List of Devices'])))

        # Empty the file to confirm the full import
        #myfile = open(self.groupsConfigFilename, 'w')
        #myfile.truncate(0)
        #myfile.close()
    
    def _processGroupConfig( self ):
        'Load the Group to be created/Updated into ListOfGroups'

        Domoticz.Log("_processGroupConfig - ListOfGroups: %s" %str(self.ListOfGroups))
        for grpid in self.toBeImported:
            Domoticz.Debug("_processGroupConfig - process: %s - %s" %(grpid, str(self.toBeImported[grpid])))
            if grpid in self.ListOfGroups:
                Domoticz.Debug("_processGroupConfig - existing group: len: %s" \
                        %len(self.toBeImported[grpid]['List of Devices']))

                if self.ListOfGroups[grpid]['Grp Status'] == 'Discover':
                    Domoticz.Debug("_processGroupConfig - Name: >%s<, newName: >%s<" %(self.ListOfGroups[grpid]['Name'], self.toBeImported[grpid]['Name']))
                    if self.ListOfGroups[grpid]['Name'] == '':
                        self.ListOfGroups[grpid]['Name'] = self.toBeImported[grpid]['Name']

                # If this is an existing one, lets see if there are any updates
                if len(self.toBeImported[grpid]['List of Devices']) == 0:
                    Domoticz.Debug("_processGroupConfig - remove group: %s" %grpid)
                    # We have to remove this Group and so remove all devices attached to the group
                    idx = 0
                    self.ListOfGroups[grpid]['Grp Status'] = 'Remove'
                    for devid, iterep, status  in self.ListOfGroups[grpid]['Devices']:
                        # Remove that one from group
                        self.ListOfGroups[grpid]['Devices'][idx][2] = 'Remove' 
                        idx += 1
                    continue # Go to next group

                # We have to update, add or remove some devices !
                self.ListOfGroups[grpid]['Grp Status'] = 'Update'
                if  self.ListOfGroups[grpid]['Name'] != self.ListOfGroups[grpid]['Name']:
                    Domoticz.Log("_processGroupConfig - Different group name: %s vs. %s, skip " %(self.ListOfGroups[grpid]['Name'], self.ListOfGroups[grpid]['Name']))
                    continue

                # Let's check if we don't have any Device to remove
                idx = 0
                for iternwkid,iterep, iterstatus in self.ListOfGroups[grpid]['Devices']:
                    for impDev in self.toBeImported[grpid]['List of Devices']:
                        if self.IEEE2NWK[impDev] == iternwkid:
                            break
                    else:
                        # NOt found in the device to Importe
                        # We need to remove that device
                        Domoticz.Log("_processGroupConfig - %s not found in ImportGroups.txt, so remove" %iternwkid)
                        self.ListOfGroups[grpid]['Devices'][idx][2] = 'Remove' 
                    idx += 1

                # Let's check what are the new devices for this group
                for iterDev in  self.toBeImported[grpid]['List of Devices']:
                    if iterDev not in self.IEEE2NWK:
                        # Unknown device
                        Domoticz.Log("_processGroupConfig - unknown device: %s, skip" %iterDev)
                        continue
                    for iterLoG in self.ListOfGroups[grpid]['Devices']:
                        Domoticz.Debug("_processGroupConfig - %s versus %s" %(iterDev, iterLoG))
                        if self.IEEE2NWK[iterDev] == iterLoG[0]:
                            Domoticz.Log("_processGroupConfig - %s found in ListOFGroup[%s] " %(iterDev, grpid))
                            break
                    else: # For loop went to the end , so we didn't find a matching iterDev
                        Domoticz.Log("_processGroupConfig - New device: %s to be added to the group %s " %(iterDev, grpid))
                        if iterDev in self.IEEE2NWK:
                            nwkidDev = self.IEEE2NWK[iterDev]
                            if 'Ep' in self.ListOfDevices[nwkidDev]:
                                for iterEp in self.ListOfDevices[nwkidDev]['Ep']:
                                    if 'ClusterType' in self.ListOfDevices[nwkidDev]['Ep'][iterEp] and \
                                            '0004' in self.ListOfDevices[nwkidDev]['Ep'][iterEp]:
                                        self.ListOfGroups[grpid]['Devices'].append( [nwkidDev, iterEp, 'New'] )

            else:
                Domoticz.Log("_processGroupConfig - New group to create %s" %grpid)
                # If this is an unknwon group, start the creation.
                if len(self.toBeImported[grpid]['List of Devices']) == 0:
                    # Nothing to do, Create a group but no device attached !
                    continue
                self.ListOfGroups[grpid] ={}
                self.ListOfGroups[grpid]['Grp Status'] = 'New'
                self.ListOfGroups[grpid]['Name'] = self.toBeImported[grpid]['Name']
                self.ListOfGroups[grpid]['Devices'] = {}
                for iterDev in self.toBeImported[grpid]['List of Devices']:
                    Domoticz.Log("_processGroupConfig - process: %s/%s" %(grpid, iterDev))
                    if iterDev in self.IEEE2NWK:
                        nwkidDev = self.IEEE2NWK[iterDev]
                        self.ListOfGroups[grpid]['Devices'] = []
                        if 'Ep' in self.ListOfDevices[nwkidDev]:
                            for iterEp in self.ListOfDevices[nwkidDev]['Ep']:
                                if 'ClusterType' in self.ListOfDevices[nwkidDev]['Ep'][iterEp] and\
                                        '0004' in self.ListOfDevices[nwkidDev]['Ep'][iterEp]:
                                    self.ListOfGroups[grpid]['Devices'].append( [nwkidDev, iterEp, 'New'] )
                    else:
                        Domoticz.Log("hearbeatGroupMgt - unknow device to be imported >%s<" %iterDev)
                self.ListOfGroups[grpid]['Grp Status'] = 'New'
                Domoticz.Log("hearbeatGroupMgt - Ready to processgroup %s " %self.ListOfGroups[grpid]['Name'])
                for iter in self.ListOfGroups[grpid]['Devices']:
                    Domoticz.Log("                -  %s  " %iter)
                self.toBeImported[grpid]['List of Devices'] = []
        self.toBeImported = {}
        Domoticz.Log("_processGroupConfig - ListOfGroups: %s" %str(self.ListOfGroups))
        self.StartupPhase = 'step2'

    def _processListOfGroups( self ):
        ''' 
        browse the ListOfGroups and trigger the needed actions.
        Only 1 action at a time, in order to receive the response of Creation and the go to the next one.
        '''

        Domoticz.Log("_processListOfGroups: %s" %str(self.ListOfGroups))
        self.stillWIP = False
        toBeRemoved = []
        for iterGrp in self.ListOfGroups:
            Domoticz.Log("_processListOfGroups - Group: %s" %iterGrp)
            if self.ListOfGroups[iterGrp]['Grp Status'] in ('Ok'):
                Domoticz.Debug('_processListOfGroups - Nothing to do')
                continue

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Discover'):
                # Group retreived from the Zigate
                Domoticz.Log("_processListOfGroups - Discover, Name: %s and Devices: %s " %(self.ListOfGroups[iterGrp]['Name'],self.ListOfGroups[iterGrp]['Devices']))
                # Do we have a name for this Group, if yes, let's create a Domo Widget
                self.stillWIP = True     # In order to force going to Wip_xxx
                self.ListOfGroups[iterGrp]['Grp Status'] = 'Update'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('New', 'Remove', 'Update'):
                Domoticz.Log("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                self.stillWIP = True     # In order to force going to Wip_xxx
                idx = 0
                self.ListOfGroups[iterGrp]['Grp Status'] = 'Wip_' + self.ListOfGroups[iterGrp]['Grp Status']
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    Domoticz.Log("_processListOfGroups - %s, %s, %s " %(dev_nwkid, dev_ep, dev_status))
                    if dev_status == 'Ok':
                        pass
                    elif dev_status == 'New':
                        dev_ieee = self.ListOfDevices[dev_nwkid]['IEEE']
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip' 
                        Domoticz.Log("_processListOfGroups - _addGroup %s %s %s %s" %(dev_ieee, dev_nwkid, dev_ep, iterGrp))
                        self._addGroup( dev_ieee, dev_nwkid, dev_ep, iterGrp )
                    elif dev_status == 'Remove':
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip' 
                        Domoticz.Log("_processListOfGroups - _removeGroup %s %s %s" %( dev_nwkid, dev_ep, iterGrp))
                        self._removeGroup(dev_nwkid, dev_ep, iterGrp )
                    idx += 1

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_New'):
                Domoticz.Log("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                # Let's check that all devices have been created
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break
                else:
                    Domoticz.Log("_processListOfGroups - All devices attached to the Zigate Group. Let's create the Widget")
                    if self.ListOfGroups[iterGrp]['Name'] == '':
                        self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                    self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_Remove'):
                Domoticz.Log("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                # Let's check that all Devices have been removed from the Zigate Group
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        # Might do one more remove
                        break
                else:
                    toBeRemoved.append( iterGrp )    # Remove the element from ListOfGroup and Remove the Domoticz Device
                    self._removeDomoGroupDevice(iterGrp )
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_Update'):
                Domoticz.Log("_processListOfGroups - self.ListOfGroups[%s]['Grp Status']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Grp Status']))
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break
                else:
                    Domoticz.Log("_processListOfGroups - Set group %s to Ok" %iterGrp)
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'
                    for iterUnit in self.Devices:
                        if iterGrp == self.Devices[iterUnit].DeviceID:
                            Domoticz.Log("_processListOfGroups - found %s in Domoticz." %iterGrp)
                            # Update the group name if required
                            self.ListOfGroups[iterGrp]['Name'] = self.Devices[iterUnit].Name
                            break
                    else:
                        #DO not exist in Domoticz, let's create a widget
                        if self.ListOfGroups[iterGrp]['Name'] == '':
                            self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                        Domoticz.Log("_processListOfGroups - create Domotciz Widget for %s " %self.ListOfGroups[iterGrp]['Name'])
                        self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)
            else:
                Domoticz.Log("_processListOfGroups - unknown status: %s for group: %s." \
                        %(self.ListOfGroups[iterGrp]['Grp Status'], iterGrp))

        for iter in toBeRemoved:
            del self.ListOfGroups[iter]

        Domoticz.Log("_processListOfGroups - WIP: %s ListOfGroups: %s " %( self.stillWIP, str(self.ListOfGroups)))
        self.StartupPhase = 'step3'

        return 

    def _constructGroupList( self ):

        self.getGMS_count = 0
        for iterDev in self.ListOfDevices:
            if 'PowerSource' in self.ListOfDevices[iterDev]:
                if self.ListOfDevices[iterDev]['PowerSource'] != 'Main':
                    continue
            if 'Ep' in self.ListOfDevices[iterDev]:
                for iterEp in self.ListOfDevices[iterDev]['Ep']:
                    if 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                        '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp]:
                        Domoticz.Debug("_constructGroupList - req membership for %s/%s " %(iterDev, iterEp))
                        self._getGroupMembership(iterDev, iterEp)
                        self.getGMS_count += 1
        self.StartupPhase = 'step1'

    def hearbeatGroupMgt( self ):
        ' hearbeat to process Group Management actions '

        Domoticz.Debug("hearbeatGroupMgt - Phase: %s HB: %s WIP: %s" %(self.StartupPhase, self.HB, self.stillWIP))
        self.HB += 1

        if self.StartupPhase == 'ready':
            if not self.stillWIP:
                for group_nwkid in self.ListOfGroups:
                    self.updateDomoGroupDevice( group_nwkid)

        elif self.StartupPhase == 'init':
            Domoticz.Log("hearbeatGroupMgt - STEP1 %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            self._constructGroupList( )

        elif self.StartupPhase == 'step1':
            Domoticz.Log("hearbeatGroupMgt - STEP2 %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            self._processGroupConfig()

        elif self.StartupPhase == 'step2':
            Domoticz.Log("hearbeatGroupMgt - STEP3 %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
            self._processListOfGroups()

        elif self.StartupPhase == 'step3':
            Domoticz.Log("hearbeatGroupMgt - READY %s self.getGMS_count: %s, WIP: %s HB: %s" %(self.HB, self.getGMS_count, self.stillWIP, self.HB))
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

        elif Command == 'On' :
            zigate_cmd = "0092"
            zigate_param = '01'
            nValue = '1'
            sValue = 'On'

        elif Command == 'Set Level':
            zigate_cmd = "0081"
            OnOff = "01"
            value=int(Level*255/100)
            zigate_param = OnOff + "%02x" %value + "0010"
            nValue = '1'
            sValue = str(Level)
        else:
            return

        if Color_:
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_) 
        else: 
            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
        #datas = "01" + nwkid + EPin + EPout + zigate_param
        datas = "%02d" %z_consts.ADDRESS_MODE['group'] + nwkid + EPin + EPout + zigate_param
        Domoticz.Log("Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)
        return


