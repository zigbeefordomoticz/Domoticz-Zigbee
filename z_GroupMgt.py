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


class GroupsManagement(object):

    def __init__( self, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):
        Domoticz.Log("GroupsManagement __init__")
        self.HB = 0
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
        self.importGroupFileName = HomeDirectory + "/ImportGroups.txt"

        self._loadListOfGroups()
        self.import_GroupConfig()

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
            Domoticz.Log("_loadListOfGroups - File doesn't exist. First start")
            return
        with open(  self.groupListFileName, 'rb') as handle:
            self.ListOfGroups = pickle.loads( handle.read() )
        Domoticz.Log("loadListOfGroups - ListOfGroups loaded: %s" %self.ListOfGroups)

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

        Domoticz.Log("_addGroup - Adding device: %s/%s into group: %s" \
                %( device_addr, device_ep, grpid))

        datas = "02" + device_addr + "01" + device_ep + grpid
        self.ZigateComm.sendData( "0060", datas)
        return

    def statusGroupRequest( self, MsgData):
        Status=MsgData[0:2]
        SEQ=MsgData[2:4]
        PacketType=MsgData[4:8]

        Domoticz.Log("statusGroupRequest - Status: %s for Command: %s" %(Status, PacketType))

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

        Domoticz.Log("addGroupResponse - MsgData: %s (%s)" %(MsgData,len(MsgData)))

        # search for the Group/dev
        if len(MsgData) != 14:
            Domoticz.Log("addGroupResponse - uncomplete message %s" %MsgData)

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

        Domoticz.Log("_getGroupMembership - %s/%s " %(device_addr, device_ep))
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

        Domoticz.Log("Decode8062 - SEQ: %s, EP: %s, ClusterID: %s, sAddr: %s, Capacity: %s, Count: %s"
                %(MsgSequenceNumber, MsgEP, MsgClusterID, MsgSourceAddress, MsgCapacity, MsgGroupCount))

        self.getGMS_count  -= 1

        idx = 0
        while idx < int(MsgGroupCount,16):
            groupID = MsgData[16+(idx*4):16+(4+(idx*4))]
            Domoticz.Log("        - GroupID: %s" %groupID)
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
                        Domoticz.Log("getGroupMembershipResponse - Didn't find this entry, let's add it. %s/%s " %(MsgSourceAddress, MsgEP))
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

    def import_GroupConfig(self):
        ' This is to import User Defined/Modified Groups of Devices for processing in the hearbeatGroupMgt'

        if not os.path.isfile( self.importGroupFileName ) :
            Domoticz.Log("GroupMgt - Nothing to import")
            return

        self.toBeImported = {}
        myfile = open( self.importGroupFileName, 'r')
        Domoticz.Log("import_GroupConfig. Reading the file")
        while True:
            tmpread = myfile.readline().replace('\n', '')
            Domoticz.Log("line: %s" %tmpread )
            if not tmpread: 
                break

            group_id = group_name = None

            for token in tmpread.split(','):
                Domoticz.Log("%s" %str(token))
                if group_id is None:
                    group_id = token
                    Domoticz.Log("GroupID: %s" %token)
                    self.toBeImported[group_id]= {}
                    self.toBeImported[group_id]['Name'] = ''
                    self.toBeImported[group_id]['List of Devices'] = []
                    continue
                elif group_name is None:
                    group_name = token
                    Domoticz.Log("GroupName: %s" %token)
                    self.toBeImported[group_id]['Name'] = group_name
                    continue
                else:
                    Domoticz.Log("device:%s" %token)
                    if token.strip() != '':
                        self.toBeImported[group_id]['List of Devices'].append(token.strip())

            if group_id :
                Domoticz.Log("import_GroupConfig - Group[%s]: %s List of Devices: %s to be processed" \
                    %( group_id, self.toBeImported[group_id]['Name'], str(self.toBeImported[group_id]['List of Devices'])))

        # Empty the file to confirm the full import
        #myfile = open(self.importGroupFileName, 'w')
        #myfile.truncate(0)
        #myfile.close()
    
    def _processGroupConfig( self ):
        'Load the Group to be created/Updated into ListOfGroups'

        Domoticz.Log("_processGroupConfig")
        for grpid in self.toBeImported:
            Domoticz.Log("_processGroupConfig - process: %s - %s" %(grpid, str(self.toBeImported[grpid])))
            if grpid in self.ListOfGroups:
                Domoticz.Log("_processGroupConfig - existing group: len: %s" \
                        %len(self.toBeImported[grpid]['List of Devices']))

                if self.ListOfGroups[grpid]['Grp Status'] == 'Discover':
                    Domoticz.Log("_processGroupConfig - Name: >%s<, newName: >%s<" %(self.ListOfGroups[grpid]['Name'], self.toBeImported[grpid]['Name']))
                    if self.ListOfGroups[grpid]['Name'] == '':
                        self.ListOfGroups[grpid]['Name'] = self.toBeImported[grpid]['Name']
                        self.ListOfGroups[grpid]['Grp Status'] = 'Update'

                # If this is an existing one, lets see if there are any updates
                if len(self.toBeImported[grpid]['List of Devices']) == 0:
                    Domoticz.Log("_processGroupConfig - remove group: %s" %grpid)
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
                    Domoticz("_processGroupConfig - Different group name: %s vs. %s, skip " %(self.ListOfGroups[grpid]['Name'], self.ListOfGroups[grpid]['Name']))
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
                        Domoticz.Log("_processGroupConfig - %s versus %s" %(iterDev, iterLoG))
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
                Domoticz.Log('_processListOfGroups - Nothing to do')
                continue

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Discover'):
                # Group retreived from the Zigate
                # At that stage the group is not in ImportGroup.txt, so simply cleanup
                Domoticz.Log("_processListOfGroups - Discover")
                self.ListOfGroups[iterGrp]['Grp Status'] = 'Remove'
                idx =0
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Remove'
                    idx += 1
                toBeRemoved.append( iterGrp )    # Remove the element from ListOfGroup and Remove the Domoticz Device

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('New', 'Remove', 'Update'):
                Domoticz.Log("_processListOfGroups - New/Remove/Update")
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
                        self.stillWIP = True
                    elif dev_status == 'Remove':
                        self.ListOfGroups[iterGrp]['Devices'][idx][2] = 'Wip' 
                        Domoticz.Log("_processListOfGroups - _removeGroup %s %s %s" %( dev_nwkid, dev_ep, iterGrp))
                        self._removeGroup(dev_nwkid, dev_ep, iterGrp )
                        self.stillWIP = True
                    idx += 1

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_New'):
                # Let's check that all devices have been created
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break
                else:
                    Domoticz.Log("_processListOfGroups - All devices attached to the Zigate Group. Let's create the Widget")
                    self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_Remove'):
                # Let's check that all Devices have been removed from the Zigate Group
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break
                else:
                    toBeRemoved.append( iterGrp )    # Remove the element from ListOfGroup and Remove the Domoticz Device
                    self._removeDomoGroupDevice(iterGrp )
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'

            elif self.ListOfGroups[iterGrp]['Grp Status'] in ('Wip_Update'):
                for dev_nwkid, dev_ep, dev_status in self.ListOfGroups[iterGrp]['Devices']:
                    if dev_status == 'Wip':
                        self.stillWIP = True
                        break
                else:
                    self.ListOfGroups[iterGrp]['Grp Status'] = 'Ok'


            else:
                Domoticz.Log("hearbeatGroupMgt - unknown status: %s for group: %s." \
                        %(self.ListOfGroups[iterGrp]['Grp Status'], iterGrp))

        for iter in toBeRemoved:
            del self.ListOfGroups[iter]

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
                        Domoticz.Log("_constructGroupList - req membership for %s/%s " %(iterDev, iterEp))
                        self._getGroupMembership(iterDev, iterEp)
                        self.getGMS_count += 1

    def hearbeatGroupMgt( self ):
        ' hearbeat to process Group Management actions '

        self.HB += 1

        Domoticz.Log("hearbeatGroupMgt - %s self.getGMS_count: %s, WIP: %s " %(self.HB, self.getGMS_count, self.stillWIP))
        if self.HB == 1: 
            self._constructGroupList( )

        if self.HB == 3:
            self._processGroupConfig()

        if self.stillWIP and self.HB > 3:
            self._processListOfGroups()

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


    def processRemoveGroup( self, unit, nwkid):


        # Remove all devices from the corresponding group

        # Remove the Domo Device

        return
